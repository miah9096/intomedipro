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
# 기간을 넉넉하게 기본값 설정 (1월 1일 ~ 현재)
start_date = st.sidebar.date_input("시작일", datetime(2026, 1, 1))
end_date = st.sidebar.date_input("종료일", datetime.now())

# 데이터 불러오기 버튼 로직
if st.sidebar.button("🔄 데이터 불러오기", type="primary"):
    if not api_key or not secret_key:
        st.sidebar.error("API Key와 Secret Key를 입력해주세요.")
    else:
        with st.spinner("모든 상태의 주문을 가져오는 중입니다..."):
            try:
                # [단계 1] 토큰 발급
                res = requests.post("https://api.imweb.me/v2/auth", json={"key": api_key, "secret": secret_key})
                
                if res.status_code != 200:
                    st.error(f"로그인 실패! (코드: {res.status_code})")
                else:
                    access_token = res.json().get('access_token')
                    
                    # [단계 2] 주문 목록 가져오기 (상태 필터 제거! 전체 조회)
                    headers = {"access-token": access_token}
                    params = {
                        "limit": 500, # 최근 500건
                        # "status": "PAYMENT"  <-- 이 줄을 삭제해서 모든 주문을 가져오게 변경함
                    }
                    
                    res_orders = requests.get("https://api.imweb.me/v2/shop/orders", headers=headers, params=params)
                    
                    if res_orders.status_code == 200:
                        raw_data = res_orders.json().get('data', {}).get('list', [])
                        
                        if not raw_data:
                            st.warning("가져올 데이터가 없습니다. (API 응답 0건)")
                            st.session_state['df'] = pd.DataFrame()
                        else:
                            # [단계 3] 데이터 가공
                            clean_data = []
                            for o in raw_data:
                                # 날짜 변환
                                ts = o.get('order_time', 0)
                                order_dt = datetime.fromtimestamp(ts)
                                order_date_str = order_dt.strftime('%Y-%m-%d')
                                
                                # 기간 필터링 (사이드바 날짜 기준)
                                if start_date <= order_dt.date() <= end_date:
                                    
                                    # 배송지 정보
                                    delivery = o.get('delivery', {})
                                    addr_info = delivery.get('address', {})
                                    
                                    # 상태 정보 (한글로 변환해주면 더 좋음)
