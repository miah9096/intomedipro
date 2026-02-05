import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import BytesIO

# --------------------------------------------------
# Page Config
# --------------------------------------------------
st.set_page_config(
    page_title="Janytree Operations Dashboard",
    layout="wide"
)

st.title("🌿 Janytree Operations Dashboard")

# --------------------------------------------------
# Utils
# --------------------------------------------------
def unix_to_dt(ts):
    if ts:
        return datetime.fromtimestamp(int(ts))
    return None


def safe_get(d, key, default=None):
    return d.get(key, default) if isinstance(d, dict) else default


# --------------------------------------------------
# Imweb API
# --------------------------------------------------
IMWEB_AUTH_URL = "https://api.imweb.me/v2/auth"
IMWEB_PROD_ORDERS_URL = "https://api.imweb.me/v2/shop/prod-orders"


def get_access_token(key, secret):
    res = requests.post(
        IMWEB_AUTH_URL,
        json={"key": key, "secret": secret},
        timeout=10
    )
    res.raise_for_status()
    return res.json()["data"]["access_token"]


def fetch_prod_orders(token, start_ts, end_ts, progress_bar):
    headers = {"Authorization": f"Bearer {token}"}
    page = 1
    all_items = []

    while True:
        params = {
            "page": page,
            "limit": 100,
            "start_time": start_ts,
            "end_time": end_ts,
        }

        r = requests.get(
            IMWEB_PROD_ORDERS_URL,
            headers=headers,
            params=params,
            timeout=20
        )
        r.raise_for_status()
        data = r.json().get("data", [])

        if not data:
            break

        all_items.extend(data)
        page += 1
        progress_bar.progress(min(page * 5, 100))

    return all_items


# --------------------------------------------------
# Sidebar
# --------------------------------------------------
with st.sidebar:
    st.header("🔑 API 설정")

    api_key = st.text_input("Imweb API Key", type="password")
    api_secret = st.text_input("Imweb Secret Key", type="password")

    st.divider()

    st.header("📅 기간 선택")
    start_date = st.date_input("시작일")
    end_date = st.date_input("종료일")

    fetch_btn = st.button("📥 데이터 불러오기")


# --------------------------------------------------
# Data Load
# --------------------------------------------------
df = pd.DataFrame()

if fetch_btn:
    if not api_key or not api_secret:
        st.error("API Key와 Secret을 입력하세요.")
        st.stop()

    with st.spinner("Imweb API 인증 중..."):
        try:
            token = get_access_token(api_key, api_secret)
        except Exception as e:
            st.error(f"인증 실패: {e}")
            st.stop()

    start_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
    end_ts = int(datetime.combine(end_date, datetime.max.time()).timestamp())

    progress = st.progress(0)

    try:
        raw = fetch_prod_orders(token, start_ts, end_ts, progress)
    except Exception as e:
        st.error(f"주문 데이터 조회 실패: {e}")
        st.stop()

    if not raw:
        st.warning("선택한 기간에 주문 데이터가 없습니다.")
        st.stop()

    rows = []
    for r in raw:
        rows.append({
            "order_no": safe_get(r, "order_no"),
            "order_date": unix_to_dt(safe_get(r, "order_time") or safe_get(r, "pay_time")),
            "status": safe_get(r, "status"),
            "buyer": safe_get(r, "orderer_name"),
            "receiver": safe_get(r, "receiver_name"),
            "phone": safe_get(r, "receiver_phone"),
            "address": safe_get(r, "receiver_addr"),
            "product": safe_get(r, "prod_name"),
            "option": safe_get(r, "options_str"),
            "qty": int(safe_get(r, "ea", 0)),
            "price": int(safe_get(r, "payment_price", 0)),
        })

    df = pd.DataFrame(rows)

# --------------------------------------------------
# Tabs
# --------------------------------------------------
if not df.empty:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Sales", "🧾 Invoice", "🔍 Gong-gu", "📦 Inventory", "🧪 Raw Data"]
    )

    # --------------------------------------------------
    # Tab 1: Sales Dashboard
    # --------------------------------------------------
    with tab1:
        c1, c2, c3 = st.columns(3)
        c1.metric("총 매출", f"{df['price'].sum():,} 원")
        c2.metric("총 판매 수량", df["qty"].sum())
        c3.metric("주문 건수", df["order_no"].nunique())

        daily = df.groupby(df["order_date"].dt.date)["price"].sum().reset_index()
        st.plotly_chart(
            px.line(daily, x="order_date", y="price", title="일별 매출"),
            use_container_width=True
        )

        top_prod = (
            df.groupby("product")["qty"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        st.plotly_chart(
            px.bar(top_prod, x="product", y="qty", title="TOP 상품"),
            use_container_width=True
        )

    # --------------------------------------------------
    # Tab 2: Invoice Generator
    # --------------------------------------------------
    with tab2:
        def merge_products(sub):
            result = []
            for _, row in sub.iterrows():
                name = row["product"]
                if row["option"]:
                    name = f"{name} ({row['option']})"
                result.extend([name] * row["qty"])
            return " // ".join(result)

        invoice_df = (
            df.groupby("order_no")
            .apply(lambda x: pd.Series({
                "주문일": x["order_date"].iloc[0],
                "수령인": x["receiver"].iloc[0],
                "주소": x["address"].iloc[0],
                "상품": merge_products(x),
                "결제금액": x["price"].sum()
            }))
            .reset_index()
        )

        st.dataframe(invoice_df, use_container_width=True)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            invoice_df.to_excel(writer, index=False, sheet_name="Invoice")

        st.download_button(
            "📥 엑셀 다운로드",
            data=buffer.getvalue(),
            file_name="invoice.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # --------------------------------------------------
    # Tab 3: Group Buying Search
    # --------------------------------------------------
    with tab3:
        keyword = st.text_input("상품명 키워드 검색")
        if keyword:
            filtered = df[df["product"].str.contains(keyword, case=False, na=False)]
            st.metric("총 판매 수량", filtered["qty"].sum())
            st.dataframe(filtered)

    # --------------------------------------------------
    # Tab 4: Inventory & Ranking
    # --------------------------------------------------
    with tab4:
        inv = (
            df.groupby(["product", "option"])["qty"]
            .sum()
            .reset_index()
            .sort_values("qty", ascending=False)
        )
        st.dataframe(inv, use_container_width=True)

    # --------------------------------------------------
    # Tab 5: Raw Data
    # --------------------------------------------------
    with tab5:
        st.dataframe(df, use_container_width=True)
