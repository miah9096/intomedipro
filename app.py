import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
import io

# 1. 페이지 설정
st.set_page_config(page_title="Janytree 대시보드", layout="wide")

# 2. 사이드바 설정
st.sidebar.title("🔧 설정")
api_key = st.sidebar.text_input("API Key", type="password")
secret_key = st.sidebar.text_input("Secret Key", type="password")

if st.sidebar.button("데이터 불러오기"):
    if not api_key or not secret_key:
        st.error("API Key와 Secret Key를 입력하세요.")
    else:
        try:
            res = requests.post("https://api.imweb.me/v2/auth", json={"key": api_key, "secret": secret_key})
            if res.status_code == 200:
                token = res.json().get('access_token')
                headers = {"access-token": token}
                res_orders = requests.get("https://api.imweb.me/v2/shop/orders", headers=headers, params={"limit": 100, "status": "PAYMENT"})
                
                if res_orders.status_code == 200:
                    data = res_orders.json().get('data', {}).get('list', [])
                    if not data:
                        st.warning("데이터가 없습니다.")
                        st.session_state['df'] = pd.DataFrame()
                    else:
                        rows = []
                        for o in data:
                            date = datetime.fromtimestamp(o['order_date']).strftime('%Y-%m-%d')
                            for i in o['items']:
                                rows.append({
                                    "주문번호": o['order_no'], "주문일자": date, 
                                    "상품명": i['prod_name'], "옵션명": i['options_str'], 
                                    "수량": int(i['ea']), "결제금액": float(i['price_total']),
                                    "주문자": o['orderer']['name'], "연락처": o['orderer']['call'],
                                    "수령인": o['shipping']['name'], "수령인연락처": o['shipping']['call'],
                                    "주소": f"{o['shipping'].get('address','')} {o['shipping'].get('address_detail','')}",
                                    "우편번호": o['shipping']['zipcode'], "배송메시지": o['shipping']['memo']
                                })
                        st.session_state['df'] = pd.DataFrame(rows)
                        st.success(f"성공! {len(rows)}건 가져옴")
                else:
                    st.error("주문 목록 실패")
            else:
                st.error("로그인 실패")
        except Exception as e:
            st.error(f"오류: {e}")

# 3. 메인 화면
st.title("📦 Janytree 통합 대시보드")

if 'df' in st.session_state and not st.session_state['df'].empty:
    df = st.session_state['df']
    tab1, tab2 = st.tabs(["📊 매출", "📦 송장"])
    
    with tab1:
        st.metric("총 매출", f"{df['결제금액'].sum():,.0f}원")
        fig = px.line(df.groupby('주문일자')['결제금액'].sum().reset_index(), x='주문일자', y='결제금액')
        st.plotly_chart(fig)
        
    with tab2:
        if st.button("송장 엑셀 생성"):
            inv_rows = []
            for no, g in df.groupby('주문번호'):
                opts = []
                for _, r in g.iterrows():
                    for _ in range(int(r['수량'])): opts.append(f"[{r['상품명']}] {r['옵션명']}")
                opts.sort()
                
                f = g.iloc[0]
                inv_rows.append({
                    "주문번호": f['주문번호'], "수령인": f['수령인'], "주소": f['주소'],
                    "상품명": " // ".join(opts), "총수량": len(opts),
                    "우편번호": f['우편번호'], "연락처": f['수령인연락처'], "메시지": f['배송메시지']
                })
            
            inv_df = pd.DataFrame(inv_rows)
            st.dataframe(inv_df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                inv_df.to_excel(writer, index=False)
            st.download_button("📥 엑셀 다운로드", output.getvalue(), "송장.xlsx")
else:
    st.info("왼쪽 사이드바에서 데이터 불러오기를 해주세요.")