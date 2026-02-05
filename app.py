import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime

st.set_page_config(page_title="Janytree 대시보드", layout="wide")

st.sidebar.title("🔧 설정")
api_key = st.sidebar.text_input("API Key", type="password")
secret_key = st.sidebar.text_input("Secret Key", type="password")

if st.sidebar.button("데이터 불러오기"):
    if not api_key or not secret_key:
        st.error("키를 입력하세요.")
    else:
        with st.spinner("데이터 분석 중..."):
            try:
                # 1. 토큰 발급
                res = requests.post("https://api.imweb.me/v2/auth", json={"key": api_key, "secret": secret_key})
                token = res.json().get('access_token')
                
                # 2. 데이터 가져오기 (전체 조회)
                headers = {"access-token": token}
                res_orders = requests.get("https://api.imweb.me/v2/shop/orders", headers=headers, params={"limit": 100})
                raw_data = res_orders.json().get('data', {}).get('list', [])

                if not raw_data:
                    st.warning("데이터가 0건입니다.")
                else:
                    # 🔍 [진단] 첫 번째 데이터의 '진짜 이름표(Key)'들을 화면에 보여줌
                    first_item = raw_data[0]
                    st.subheader("🔍 데이터 구조 뜯어보기 (첫 번째 주문)")
                    st.json(first_item) # 여기서 실제 날짜 필드명이 뭔지 확인 가능!

                    # 3. 데이터 가공 (안전 모드: 없으면 빈칸 처리)
                    rows = []
                    for o in raw_data:
                        # 날짜 처리 (에러 방지: .get 사용)
                        ts = o.get('order_date') 
                        if ts:
                            date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                        else:
                            # order_date가 없으면 다른 후보들을 찾아봄
                            date = o.get('date', '날짜모름')

                        items = o.get('items', [])
                        for i in items:
                            rows.append({
                                "주문번호": o.get('order_no', '-'),
                                "주문일자": date,
                                "상품명": i.get('prod_name', '-'),
                                "옵션명": i.get('options_str', '-'),
                                "수량": int(i.get('ea', 0)),
                                "결제금액": float(i.get('price_total', 0)),
                                "주문자": o.get('orderer', {}).get('name', '-'),
                                "수령인": o.get('shipping', {}).get('name', '-'),
                                "주소": o.get('shipping', {}).get('address', '-'),
                                "연락처": o.get('shipping', {}).get('call', '-')
                            })
                    
                    st.session_state['df'] = pd.DataFrame(rows)
                    st.success("데이터 불러오기 성공!")

            except Exception as e:
                st.error(f"오류: {e}")

# 메인 화면
st.title("📦 Janytree 대시보드")

if 'df' in st.session_state and not st.session_state['df'].empty:
    df = st.session_state['df']
    st.dataframe(df)
    
    # 송장 생성 버튼
    if st.button("송장 엑셀 만들기"):
        # (여기에 엑셀 생성 로직...)
        st.write("엑셀 생성 기능 준비 완료")
