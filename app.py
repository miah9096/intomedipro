import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
import io
import time

# --------------------------------------------------------------------------
# 1. 페이지 설정
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Janytree 통합 운영 대시보드",
    page_icon="📦",
    layout="wide"
)

# --------------------------------------------------------------------------
# 2. 사이드바
# --------------------------------------------------------------------------
st.sidebar.header("🔒 API 인증")
api_key = st.sidebar.text_input("API Key 입력", type="password")
secret_key = st.sidebar.text_input("Secret Key 입력", type="password")

st.sidebar.markdown("---")
st.sidebar.header("📅 기간 설정")
start_date = st.sidebar.date_input("시작일", datetime(2026, 1, 1))
end_date = st.sidebar.date_input("종료일", datetime.now())

# 데이터 불러오기 버튼
if st.sidebar.button("🔄 데이터 불러오기 (최대 500건)", type="primary"):
    if not api_key or not secret_key:
        st.sidebar.error("API Key와 Secret Key를 입력해주세요.")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        try:
            # 1. 로그인
            status_text.text("🔑 로그인 중...")
            res = requests.post("https://api.imweb.me/v2/auth", json={"key": api_key, "secret": secret_key})
            
            if res.status_code != 200:
                st.error("로그인 실패! 키 값을 확인해주세요.")
                st.stop()
            
            access_token = res.json().get('access_token')
            headers = {"access-token": access_token}
            
            # 2. 주문 목록 가져오기 (50 -> 500건으로 증가!)
            status_text.text("📂 주문 목록(껍데기)을 가져오는 중...")
            params = {"limit": 500}  # <--- 건수 제한 해제 (500건)
            res_orders = requests.get("https://api.imweb.me/v2/shop/orders", headers=headers, params=params)
            
            if res_orders.status_code != 200:
                st.error("주문 목록 조회 실패")
                st.stop()

            raw_list = res_orders.json().get('data', {}).get('list', [])
            
            if not raw_list:
                st.warning("기간 내 주문이 0건입니다.")
                progress_bar.empty()
            else:
                clean_data = []
                total_count = len(raw_list)
                
                # 3. 상세 조회 (Detail Fetching)
                for idx, simple_order in enumerate(raw_list):
                    # 진행률 표시
                    progress = (idx + 1) / total_count
                    progress_bar.progress(progress)
                    status_text.text(f"📦 ({idx+1}/{total_count}) 주문번호 {simple_order.get('order_no')} 상세 내용 뜯어보는 중...")
                    
                    # 상세 데이터 가져오기
                    order_no = simple_order.get('order_no')
                    detail_res = requests.get(f"https://api.imweb.me/v2/shop/orders/{order_no}", headers=headers)
                    
                    # 상세 정보가 있으면 덮어쓰기
                    if detail_res.status_code == 200:
                        o = detail_res.json().get('data', simple_order)
                    else:
                        o = simple_order

                    # --- 데이터 가공 ---
                    ts = o.get('order_time', 0)
                    order_dt = datetime.fromtimestamp(ts)
                    order_date_str = order_dt.strftime('%Y-%m-%d')
                    
                    # 날짜 필터링
                    if not (start_date <= order_dt.date() <= end_date):
                        continue
                        
                    # 배송지
                    delivery = o.get('delivery', {})
                    addr_info = delivery.get('address', {})
                    
                    # 상태 한글 변환
                    status_map = {
                        "PAY_WAIT": "입금대기", "PAYMENT": "결제완료", 
                        "PREPARE": "배송준비", "DELIV_WAIT": "배송대기",
                        "DELIV_ING": "배송중", "DELIV_COMP": "배송완료",
                        "CANCEL": "취소", "EXCHANGE": "교환", "RETURN": "반품",
                        "CONFIRM": "구매확정"
                    }
                    raw_status = o.get('status', 'UNKNOWN')
                    kor_status = status_map.get(raw_status, raw_status)

                    # 상품 정보 (여기가 핵심!)
                    items = o.get('items', [])
                    
                    if not items:
                        # 아이템이 없으면 '정보없음'으로 일단 저장
                        clean_data.append({
                            "주문번호": o.get('order_no'),
                            "주문상태": kor_status,
                            "주문일자": order_date_str,
                            "상품명": "정보없음(진단필요)", 
                            "옵션명": "-",
                            "수량": 1, 
                            "결제금액": float(o.get('payment', {}).get('total_price', 0)),
                            "주문자": o.get('orderer', {}).get('name'),
                            "수령인": addr_info.get('name', '-'),
                            "연락처": addr_info.get('phone', '-'),
                            "주소": f"{addr_info.get('address', '')} {addr_info.get('address_detail', '')}",
                            "우편번호": addr_info.get('postcode', '-'),
                            "배송메시지": "-"
                        })
                    else:
                        for i in items:
                            clean_data.append({
                                "주문번호": o.get('order_no'),
                                "주문상태": kor_status,
                                "주문일자": order_date_str,
                                "상품명": i.get('prod_name', '-'),
                                "옵션명": i.get('options_str', '-'),
                                "수량": int(i.get('ea', 0)),
                                "결제금액": float(i.get('price_total', 0)),
                                "주문자": o.get('orderer', {}).get('name'),
                                "수령인": addr_info.get('name', '-'),
                                "연락처": addr_info.get('phone', '-'),
                                "주소": f"{addr_info.get('address', '')} {addr_info.get('address_detail', '')}",
                                "우편번호": addr_info.get('postcode', '-'),
                                "배송메시지": "-"
                            })
                    # -----------------

                st.session_state['df'] = pd.DataFrame(clean_data)
                status_text.success(f"✅ 총 {len(clean_data)}건 분석 완료!")
                progress_bar.empty()
                time.sleep(1)
                st.rerun()

        except Exception as e:
            st.error(f"오류 발생: {e}")

# --------------------------------------------------------------------------
# 3. 메인 콘텐츠
# --------------------------------------------------------------------------
st.title("Janytree 통합 운영 대시보드")

if 'df' in st.session_state and not st.session_state['df'].empty:
    df = st.session_state['df']
    
    # 탭 메뉴 (마지막에 진단 탭 추가)
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 매출", "📄 송장", "📦 공구", 
        "💎 재고", "👥 고객", "🔌 원본", "🔧 데이터 정밀진단(DEBUG)"
    ])

    # [Tab 1~6: 기존과 동일]
    with tab1:
        total_sales = df['결제금액'].sum()
        total_orders = df['주문번호'].nunique()
        c1, c2 = st.columns(2)
        c1.metric("총 매출액", f"₩{total_sales:,.0f}")
        c2.metric("주문 건수", f"{total_orders}건")
    
    with tab2:
        st.subheader("송장 생성기")
        if st.button("🚀 송장 엑셀 만들기"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 엑셀 다운로드", output.getvalue(), "송장.xlsx")
            st.dataframe(df)

    with tab3: st.dataframe(df)
    with tab4: st.dataframe(df)
    with tab5: st.dataframe(df)
    with tab6: st.dataframe(df)

    # === [Tab 7] 여기가 제일 중요합니다! ===
    with tab7:
        st.subheader("🕵️‍♀️ 상품명이 안 나올 때 쓰는 진단 도구")
        st.write("상품명이 '정보없음'으로 나온다면, 아래에 **주문번호 하나**를 입력하고 버튼을 눌러주세요.")
        st.write("그 주문의 **진짜 상세 데이터**를 뜯어서 보여줍니다. (검은 화면을 캡쳐해서 보여주세요!)")
        
        debug_order_no = st.text_input("확인할 주문번호 입력 (예: 20260205...)", "")
        
        if st.button("이 주문의 원본 데이터 뜯어보기"):
            if not api_key or not secret_key:
                st.error("왼쪽 사이드바에 API 키 먼저 입력해주세요.")
            elif not debug_order_no:
                st.error("주문번호를 입력해주세요.")
            else:
                try:
                    # 토큰 재발급 (안전하게)
                    auth_res = requests.post("https://api.imweb.me/v2/auth", json={"key": api_key, "secret": secret_key})
                    token = auth_res.json().get('access_token')
                    headers = {"access-token": token}
                    
                    # 상세 조회
                    d_res = requests.get(f"https://api.imweb.me/v2/shop/orders/{debug_order_no}", headers=headers)
                    
                    if d_res.status_code == 200:
                        full_data = d_res.json()
                        st.success("데이터 조회 성공! 아래 내용을 확인해주세요.")
                        st.json(full_data) # JSON 전체 출력
                    else:
                        st.error(f"조회 실패 (코드: {d_res.status_code})")
                        st.write(d_res.text)
                except Exception as e:
                    st.error(f"오류: {e}")

else:
    st.info("👈 왼쪽 사이드바에서 [데이터 불러오기]를 눌러주세요. (500건 조회라 조금 걸립니다!)")
