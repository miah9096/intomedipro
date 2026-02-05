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
        st.sidebar.error("❌ 키를 입력해주세요.")
    else:
        with st.spinner("데이터 조회 중..."):
            try:
                # 1. 토큰 발급
                res = requests.post("https://api.imweb.me/v2/auth", json={"key": api_key, "secret": secret_key})
                
                if res.status_code != 200:
                    st.sidebar.error(f"❌ 로그인 실패! (코드: {res.status_code})")
                    st.sidebar.write(res.json()) # 에러 내용 보여주기
                else:
                    token = res.json().get('access_token')
                    
                    # 2. 주문 가져오기 (상태 필터 제거 -> 전체 조회)
                    headers = {"access-token": token}
                    params = {
                        "limit": 100  # 최근 100건 무조건 조회
                    }
                    
                    res_orders = requests.get("https://api.imweb.me/v2/shop/orders", headers=headers, params=params)
                    
                    if res_orders.status_code == 200:
                        raw_data = res_orders.json().get('data', {}).get('list', [])
                        
                        if not raw_data:
                            st.warning("⚠️ 가져온 데이터가 0건입니다.")
                            # 디버깅용: 왜 0건인지 원본 응답 확인
                            with st.expander("🔍 상세 응답 확인 (클릭)"):
                                st.write(res_orders.json())
                            st.session_state['df'] = pd.DataFrame()
                        else:
                            # 3. 데이터 가공
                            rows = []
                            for o in raw_data:
                                date = datetime.fromtimestamp(o['order_date']).strftime('%Y-%m-%d')
                                # 상태 확인용 (어떤 상태인지 출력)
                                status = o.get('status', 'Unknown')
                                
                                for i in o['items']:
                                    rows.append({
                                        "주문번호": o['order_no'], 
                                        "주문상태": status, # 상태 추가
                                        "주문일자": date, 
                                        "상품명": i['prod_name'], 
                                        "옵션명": i['options_str'], 
                                        "수량": int(i['ea']), 
                                        "결제금액": float(i['price_total']),
                                        "주문자": o['orderer']['name'], 
                                        "연락처": o['orderer']['call'],
                                        "수령인": o['shipping']['name'], 
                                        "수령인연락처": o['shipping']['call'],
                                        "주소": f"{o['shipping'].get('address','')} {o['shipping'].get('address_detail','')}",
                                        "우편번호": o['shipping']['zipcode'], 
                                        "배송메시지": o['shipping']['memo']
                                    })
                            
                            st.session_state['df'] = pd.DataFrame(rows)
                            st.success(f"✅ 성공! 총 {len(rows)}개의 상품 내역을 가져왔습니다.")
                    else:
                        st.error(f"주문 목록 조회 실패 (코드: {res_orders.status_code})")
                        st.write(res_orders.json())

            except Exception as e:
                st.error(f"오류 발생: {e}")

# --------------------------------------------------------------------------
# 3. 메인 화면
# --------------------------------------------------------------------------
st.title("📦 Janytree 통합 대시보드 (Debug Ver.)")

if 'df' in st.session_state and not st.session_state['df'].empty:
    df = st.session_state['df']
    
    # 상태별 건수 확인 (진단용)
    st.info(f"💡 조회된 주문 상태 분포: {df['주문상태'].value_counts().to_dict()}")

    tab1, tab2 = st.tabs(["📊 매출/현황", "📦 송장 생성"])
    
    with tab1:
        st.dataframe(df) # 원본 데이터 바로 보여주기
        
    with tab2:
        if st.button("송장 엑셀 생성"):
            inv_rows = []
            for no, g in df.groupby('주문번호'):
                opts = []
                for _, r in g.iterrows():
                    for _ in range(int(r['수량'])): 
                        opts.append(f"[{r['상품명']}] {r['옵션명']}")
                opts.sort()
                
                f = g.iloc[0]
                inv_rows.append({
                    "주문번호": f['주문번호'], "수령인": f['수령인'], 
                    "상품명": " // ".join(opts), "총수량": len(opts),
                    "주소": f['주소'], "연락처": f['수령인연락처'], "메시지": f['배송메시지']
                })
            
            inv_df = pd.DataFrame(inv_rows)
            st.dataframe(inv_df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                inv_df.to_excel(writer, index=False)
            st.download_button("📥 엑셀 다운로드", output.getvalue(), "송장.xlsx")

else:
    st.info("👈 왼쪽 사이드바에 API 키를 입력하고 버튼을 눌러보세요.")
