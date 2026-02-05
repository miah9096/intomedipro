import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
import io

# --------------------------------------------------------------------------
# 1. 페이지 설정
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Janytree 통합 운영 대시보드",
    page_icon="📦",
    layout="wide"
)

# --------------------------------------------------------------------------
# 2. 사이드바: 설정 및 데이터 가져오기
# --------------------------------------------------------------------------
st.sidebar.header("🔒 API 인증 (Authentication)")
api_key = st.sidebar.text_input("API Key 입력", type="password")
secret_key = st.sidebar.text_input("Secret Key 입력", type="password")

st.sidebar.markdown("---")
st.sidebar.header("📅 기간 설정")
start_date = st.sidebar.date_input("시작일", datetime(2026, 1, 6))
end_date = st.sidebar.date_input("종료일", datetime(2026, 2, 5))

# 데이터 불러오기 버튼 로직
if st.sidebar.button("🔄 데이터 불러오기", type="primary"):
    if not api_key or not secret_key:
        st.sidebar.error("API Key와 Secret Key를 입력해주세요.")
    else:
        with st.spinner("아임웹 데이터를 가져오는 중입니다..."):
            try:
                # [단계 1] 토큰 발급
                res = requests.post("https://api.imweb.me/v2/auth", json={"key": api_key, "secret": secret_key})
                
                if res.status_code != 200:
                    st.error(f"로그인 실패! 키 값을 확인해주세요. (코드: {res.status_code})")
                else:
                    access_token = res.json().get('access_token')
                    
                    # [단계 2] 주문 목록 가져오기 (최대 500건 조회)
                    headers = {"access-token": access_token}
                    params = {
                        "limit": 500, # 넉넉하게 조회
                        "status": "PAYMENT" # 결제완료 기준
                    }
                    
                    res_orders = requests.get("https://api.imweb.me/v2/shop/orders", headers=headers, params=params)
                    
                    if res_orders.status_code == 200:
                        raw_data = res_orders.json().get('data', {}).get('list', [])
                        
                        if not raw_data:
                            st.warning("설정된 기간 내 주문 데이터가 없습니다.")
                            st.session_state['df'] = pd.DataFrame()
                        else:
                            # [단계 3] 데이터 가공 (수리된 엔진 적용!)
                            clean_data = []
                            for o in raw_data:
                                # 날짜 변환 (수정됨: order_time 사용)
                                ts = o.get('order_time', 0)
                                order_dt = datetime.fromtimestamp(ts)
                                order_date_str = order_dt.strftime('%Y-%m-%d')
                                
                                # 기간 필터링 (사이드바 날짜 기준)
                                if start_date <= order_dt.date() <= end_date:
                                    
                                    # 배송지 정보 (수정됨: delivery > address 사용)
                                    delivery = o.get('delivery', {})
                                    addr_info = delivery.get('address', {})
                                    
                                    # 상품 정보 처리
                                    items = o.get('items', [])
                                    if not items:
                                        # 상품 정보가 없는 경우 기본값
                                        clean_data.append({
                                            "주문번호": o.get('order_no'),
                                            "주문일자": order_date_str,
                                            "상품명": "정보없음", "옵션명": "-",
                                            "수량": 1, "결제금액": float(o.get('payment', {}
