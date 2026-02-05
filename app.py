import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import io

# --------------------------------------------------------------------------
# 1. 페이지 설정
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Janytree 통합 운영 대시보드 (정밀모드)",
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
if st.sidebar.button("🔄 데이터 불러오기 (정밀 조회)", type="primary"):
    if not api_key or not secret_key:
        st.sidebar.error("API Key와 Secret Key를 입력해주세요.")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        try:
            # [1] 로그인
            status_box.info("🔑 로그인 시도 중...")
            auth_res = requests.post("https://api.imweb.me/v2/auth", json={"key": api_key, "secret": secret_key})
            
            if auth_res.status_code != 200:
                st.error(f"로그인 실패! (코드: {auth_res.status_code})")
                st.stop()
            
            access_token = auth_res.json().get('access_token')
            headers = {"access-token": access_token}
            
            # [2] 주문 목록(껍데기) 가져오기
            status_box.info("📂 주문 목록을 확보하는 중...")
            
            # 최신 100건만 먼저 조회 (속도 고려)
            params_orders = {"limit": 100} 
            res_orders = requests.get("https://api.imweb.me/v2/shop/orders", headers=headers, params=params_orders)
            
            if res_orders.status_code != 200:
                st.error("주문 목록 조회 실패")
                st.stop()

            raw_orders = res_orders.json().get('data', {}).get('list', [])
            
            if not raw_orders:
                st.warning("기간 내 주문이 없습니다.")
                st.stop()
                
            # [3] 하나씩 순회하며 '상품' 정밀 조회 (Hybrid Fetching)
            clean_data = []
            total_count = len(raw_orders)
            
            for i, order in enumerate(raw_orders):
                # 진행률 업데이트
                progress_bar.progress((i + 1) / total_count)
                status_box.info(f"🔎 ({i+1}/{total_count}) 주문번호 {order['order_no']} 상품 찾는 중...")
                
                # 날짜 필터링
                ts = order.get('order_time', 0)
                order_dt = datetime.fromtimestamp(ts)
                order_date_str = order_dt.strftime('%Y-%m-%d')
                
                if not (start_date <= order_dt.date() <= end_date):
                    continue
                
                # 배송지 정보 미리 확보
                delivery = order.get('delivery', {})
                addr = delivery.get('address', {})
                orderer = order.get('orderer', {})
                
                # --- [핵심] prod-orders에 '주문번호'를 넣어서 직접 물어보기 ---
                # "이 주문번호에 해당하는 상품 내놔!"
                p_res = requests.get(
                    "https://api.imweb.me/v2/shop/prod-orders", 
                    headers=headers, 
                    params={"order_no": order['order_no']} # 주문번호 지정 조회
                )
                
                items_found = []
                if p_res.status_code == 200:
                    items_found = p_res.json().get('data', {}).get('list', [])
                
                # 만약 prod-orders에도 없으면? 원래 items(order 안의) 확인
                if not items_found:
                    items_found = order.get('items', [])
                
                # 상태 한글 변환
                status_map = {
                    "PAY_WAIT": "입금대기", "PAYMENT": "결제완료", "PREPARE": "배송준비", 
                    "DELIV_WAIT": "배송대기", "DELIV_ING": "배송중", "DELIV_COMP": "배송완료",
                    "CANCEL": "취소", "EXCHANGE": "교환", "RETURN": "반품", "CONFIRM": "구매확정"
                }
                
                # 상품 정보가 드디어 있다면!
                if items_found:
                    for item in items_found:
                        raw_status = item.get('status', order.get('status', 'UNKNOWN'))
                        
                        clean_data.append({
                            "주문번호": order['order_no'],
                            "주문상태": status_map.get(raw_status, raw_status),
                            "주문일자": order_date_str,
                            "상품명": item.get('prod_name', item.get('name', '상품명확인불가')), # 여기서 확보!
                            "옵션명": item.get('options_str', item.get('option_name', '-')),
                            "수량": int(float(item.get('ea', 1))),
                            "결제금액": float(item.get('payment_price', item.get('price_total', 0))),
                            "주문자": orderer.get('name', '-'),
                            "수령인": addr.get('name', '-'),
                            "연락처": addr.get('phone', '-'),
                            "주소": f"{addr.get('address', '')} {addr.get('address_detail', '')}",
                            "우편번호": addr.get('postcode', '-'),
                            "배송메시지": addr.get('memo', '-')
                        })
                else:
                    # 끝까지 상품이 안 나오면 '정보없음'으로라도 기록 (누락 방지)
                    clean_data.append({
                        "주문번호": order['order_no'],
                        "주문상태": status_map.get(order.get('status'), order.get('status')),
                        "주문일자": order_date_str,
                        "상품명": "⚠️상품정보 없음(API누락)",
                        "옵션명": "-", "수량": 1, "결제금액": 0,
                        "주문자": orderer.get('name'), "수령인": addr.get('name'),
                        "연락처": addr.get('phone'), "주소": addr.get('address'),
                        "우편번호": addr.get('postcode'), "배송메시지": "-"
                    })

            # 결과 저장
            st.session_state['df'] = pd.DataFrame(clean_data)
            status_box.success(f"✅ 완료! 총 {len(clean_data)}개의 상품 데이터를 찾았습니다.")
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
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 매출", "📄 송장", "📦 공구", "💎 재고", "👥 고객", "🔌 원본"
    ])

    # [Tab 1] 매출
    with tab1:
        c1, c2 = st.columns(2)
        c1.metric("총 매출액", f"₩{df['결제금액'].sum():,.0f}")
        c2.metric("총 판매 수량", f"{df['수량'].sum()}개")
        st.bar_chart(df.groupby('주문일자')['결제금액'].sum())

    # [Tab 2] 송장
    with tab2:
        st.subheader("송장 생성기")
        target_stats = st.multiselect("상태 선택", df['주문상태'].unique(), default=df['주문상태'].unique())
        
        if st.button("🚀 송장 변환"):
            tdf = df[df['주문상태'].isin(target_stats)]
            if tdf.empty:
                st.warning("주문이 없습니다.")
            else:
                rows = []
                for no, g in tdf.groupby('주문번호'):
                    opts = []
                    for _, r in g.iterrows():
                        q = int(r['수량'])
                        for _ in range(q): opts.append(f"[{r['상품명']}] {r['옵션명']}")
                    opts.sort()
                    f = g.iloc[0]
                    rows.append({
                        "주문번호": f['주문번호'], "상태": f['주문상태'], "수령인": f['수령인'],
                        "합포장내역": " // ".join(opts), "총수량": len(opts),
                        "주소": f['주소'], "연락처": f['연락처'], "우편번호": f['우편번호']
                    })
                res_df = pd.DataFrame(rows)
                st.dataframe(res_df)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    res_df.to_excel(writer, index=False)
                st.download_button("📥 엑셀 다운로드", output.getvalue(), "송장.xlsx")

    # [Tab 3~6] (간략화)
    with tab3: st.dataframe(df)
    with tab4: st.dataframe(df.groupby(['상품명', '옵션명'])['수량'].sum().sort_values(ascending=False))
    with tab5: st.dataframe(df)
    with tab6: st.dataframe(df)

else:
    st.info("👈 왼쪽 사이드바에서 [데이터 불러오기]를 눌러주세요. (정밀 조회 모드로 작동합니다)")
