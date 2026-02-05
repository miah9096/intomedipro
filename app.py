import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
import io

# --------------------------------------------------------------------------
# 1. 페이지 설정
# --------------------------------------------------------------------------
st.set_page_config(page_title="Janytree 대시보드", layout="wide")

# --------------------------------------------------------------------------
# 2. 사이드바
# --------------------------------------------------------------------------
st.sidebar.title("🔧 설정")
api_key = st.sidebar.text_input("API Key", type="password")
secret_key = st.sidebar.text_input("Secret Key", type="password")

if st.sidebar.button("데이터 불러오기"):
    if not api_key or not secret_key:
        st.sidebar.error("❌ API Key와 Secret Key를 입력해주세요.")
    else:
        with st.spinner("데이터를 분석하고 있습니다..."):
            try:
                # 1. 토큰 발급
                res = requests.post("https://api.imweb.me/v2/auth", json={"key": api_key, "secret": secret_key})
                
                if res.status_code != 200:
                    st.error("로그인 실패! 키 값을 확인해주세요.")
                else:
                    token = res.json().get('access_token')
                    
                    # 2. 주문 목록 가져오기
                    headers = {"access-token": token}
                    params = {"limit": 100} # 최근 100건 조회
                    
                    res_orders = requests.get("https://api.imweb.me/v2/shop/orders", headers=headers, params=params)
                    
                    if res_orders.status_code == 200:
                        raw_data = res_orders.json().get('data', {}).get('list', [])
                        
                        if not raw_data:
                            st.warning("데이터가 0건입니다.")
                            st.session_state['df'] = pd.DataFrame()
                        else:
                            # 3. 데이터 가공 (이름표 수정 완료!)
                            rows = []
                            for o in raw_data:
                                # [수정 1] 날짜: order_date -> order_time
                                ts = o.get('order_time', 0)
                                date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                                
                                # [수정 2] 배송지: shipping -> delivery > address
                                delivery = o.get('delivery', {})
                                addr_info = delivery.get('address', {})
                                
                                # 상품 목록 (items가 없는 경우 대비)
                                items = o.get('items', [])
                                if not items:
                                    # 상품 정보가 없으면 주문 정보만이라도 담기
                                    rows.append({
                                        "주문번호": o.get('order_no'),
                                        "주문일자": date,
                                        "상품명": "상품정보 없음",
                                        "옵션명": "-",
                                        "수량": 1,
                                        "결제금액": float(o.get('payment', {}).get('total_price', 0)),
                                        "주문자": o.get('orderer', {}).get('name'),
                                        "연락처": o.get('orderer', {}).get('call'),
                                        "수령인": addr_info.get('name', '-'),
                                        "수령인연락처": addr_info.get('phone', '-'),
                                        "우편번호": addr_info.get('postcode', '-'),
                                        "주소": f"{addr_info.get('address', '')} {addr_info.get('address_detail', '')}",
                                        "배송메시지": "-" # 메시지는 delivery 안에 없을 수 있음
                                    })
                                else:
                                    for i in items:
                                        rows.append({
                                            "주문번호": o.get('order_no'),
                                            "주문일자": date,
                                            "상품명": i.get('prod_name', '-'),
                                            "옵션명": i.get('options_str', '-'),
                                            "수량": int(i.get('ea', 0)),
                                            "결제금액": float(i.get('price_total', 0)),
                                            "주문자": o.get('orderer', {}).get('name'),
                                            "연락처": o.get('orderer', {}).get('call'),
                                            "수령인": addr_info.get('name', '-'),
                                            "수령인연락처": addr_info.get('phone', '-'),
                                            "우편번호": addr_info.get('postcode', '-'),
                                            "주소": f"{addr_info.get('address', '')} {addr_info.get('address_detail', '')}",
                                            "배송메시지": "-"
                                        })
                            
                            st.session_state['df'] = pd.DataFrame(rows)
                            st.success(f"✅ 분석 완료! 총 {len(rows)}개의 데이터를 가져왔습니다.")
                    else:
                        st.error("데이터 조회 실패")
            except Exception as e:
                st.error(f"시스템 오류: {e}")

# --------------------------------------------------------------------------
# 3. 메인 화면 구성
# --------------------------------------------------------------------------
st.title("📦 Janytree 통합 대시보드")

if 'df' in st.session_state and not st.session_state['df'].empty:
    df = st.session_state['df']
    
    tab1, tab2, tab3 = st.tabs(["📊 매출 현황", "📦 송장 생성", "💾 원본 데이터"])
    
    # [탭 1] 매출
    with tab1:
        total_sales = df['결제금액'].sum()
        st.metric("총 매출액 (최근 100건)", f"{total_sales:,.0f}원")
        
        # 일별 그래프
        daily = df.groupby('주문일자')['결제금액'].sum().reset_index()
        fig = px.line(daily, x='주문일자', y='결제금액', title='일별 매출 추이')
        st.plotly_chart(fig, use_container_width=True)

    # [탭 2] 송장
    with tab2:
        st.info("💡 '상품명 // 상품명' 형식으로 변환하여 엑셀로 다운로드합니다.")
        if st.button("송장 엑셀 만들기"):
            inv_rows = []
            for order_no, group in df.groupby('주문번호'):
                opts = []
                for _, row in group.iterrows():
                    # 수량만큼 반복
                    qty = int(row['수량']) if row['수량'] > 0 else 1
                    for _ in range(qty):
                        opts.append(f"[{row['상품명']}] {row['옵션명']}")
                opts.sort()
                
                f = group.iloc[0]
                inv_rows.append({
                    "주문번호": f['주문번호'],
                    "수령인": f['수령인'],
                    "연락처": f['수령인연락처'],
                    "우편번호": f['우편번호'],
                    "주소": f['주소'],
                    "합포장내역": " // ".join(opts),
                    "총수량": len(opts)
                })
            
            inv_df = pd.DataFrame(inv_rows)
            st.dataframe(inv_df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                inv_df.to_excel(writer, index=False)
            st.download_button("📥 엑셀 다운로드", output.getvalue(), "Janytree_송장.xlsx")
            
    # [탭 3] 원본 데이터 (확인용)
    with tab3:
        st.dataframe(df)

else:
    st.info("👈 왼쪽 사이드바에 API 키를 입력하고 버튼을 눌러주세요.")
