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
if st.sidebar.button("🔄 데이터 불러오기", type="primary"):
    if not api_key or not secret_key:
        st.sidebar.error("API Key와 Secret Key를 입력해주세요.")
    else:
        # [수정] 상세 조회가 오래 걸릴 수 있으므로, 상태창을 비웁니다.
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
            
            # 2. 주문 목록 가져오기 (껍데기 조회)
            status_text.text("📂 주문 목록을 가져오는 중...")
            # 속도를 위해 일단 50건만 가져와 봅니다 (필요하면 숫자 늘리세요)
            params = {"limit": 50} 
            res_orders = requests.get("https://api.imweb.me/v2/shop/orders", headers=headers, params=params)
            
            if res_orders.status_code != 200:
                st.error("주문 목록 조회 실패")
                st.stop()

            raw_list = res_orders.json().get('data', {}).get('list', [])
            
            if not raw_list:
                st.warning("주문이 0건입니다.")
                progress_bar.empty()
            else:
                clean_data = []
                total_count = len(raw_list)
                
                # 3. [핵심] 하나씩 상세 조회 (Detail Fetching)
                for idx, simple_order in enumerate(raw_list):
                    # 진행률 업데이트
                    progress = (idx + 1) / total_count
                    progress_bar.progress(progress)
                    status_text.text(f"📦 상세 정보 조회 중... ({idx+1}/{total_count})")
                    
                    # 상세 데이터 가져오기 (여기에 상품/상태 정보가 있음)
                    order_no = simple_order.get('order_no')
                    detail_res = requests.get(f"https://api.imweb.me/v2/shop/orders/{order_no}", headers=headers)
                    
                    # 상세 조회 성공하면 그걸 쓰고, 실패하면 목록 정보(껍데기)라도 씀
                    if detail_res.status_code == 200:
                        o = detail_res.json().get('data', simple_order)
                    else:
                        o = simple_order

                    # --- 데이터 가공 시작 ---
                    ts = o.get('order_time', 0)
                    order_dt = datetime.fromtimestamp(ts)
                    order_date_str = order_dt.strftime('%Y-%m-%d')
                    
                    # 기간 필터
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

                    items = o.get('items', [])
                    
                    if not items:
                        # 아이템 없으면 기본 정보만
                        clean_data.append({
                            "주문번호": o.get('order_no'),
                            "주문상태": kor_status,
                            "주문일자": order_date_str,
                            "상품명": "정보없음", "옵션명": "-",
                            "수량": 1, 
                            "결제금액": float(o.get('payment', {}).get('total_price', 0)),
                            "주문자": o.get('orderer', {}).get('name'),
                            "지역": addr_info.get('address', '').split(' ')[0] if addr_info.get('address') else '-',
                            "수령인": addr_info.get('name', '-'),
                            "연락처": addr_info.get('phone', '-'),
                            "우편번호": addr_info.get('postcode', '-'),
                            "주소": f"{addr_info.get('address', '')} {addr_info.get('address_detail', '')}",
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
                                "지역": addr_info.get('address', '').split(' ')[0] if addr_info.get('address') else '-',
                                "수령인": addr_info.get('name', '-'),
                                "연락처": addr_info.get('phone', '-'),
                                "우편번호": addr_info.get('postcode', '-'),
                                "주소": f"{addr_info.get('address', '')} {addr_info.get('address_detail', '')}",
                                "배송메시지": "-"
                            })
                    # --- 데이터 가공 끝 ---

                st.session_state['df'] = pd.DataFrame(clean_data)
                status_text.success("✅ 모든 데이터 불러오기 완료!")
                progress_bar.empty()
                time.sleep(1) # 잠시 대기 후 리프레시 효과
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
        "📊 매출 대시보드", "📄 송장 생성기", "📦 공구 관리", 
        "💎 재고 인사이트", "👥 고객 분석", "🔌 데이터 연동"
    ])

    # [Tab 1] 매출
    with tab1:
        total_sales = df['결제금액'].sum()
        total_orders = df['주문번호'].nunique()
        c1, c2, c3 = st.columns(3)
        c1.metric("총 매출액", f"₩{total_sales:,.0f}")
        c2.metric("주문 건수", f"{total_orders}건")
        
        # 상태별 건수
        if '주문상태' in df.columns:
            st.write("주문 상태 현황")
            st.bar_chart(df['주문상태'].value_counts())

    # [Tab 2] 송장
    with tab2:
        st.subheader("송장 데이터 생성기")
        st.info("💡 이제 정확한 상품명과 옵션이 표시됩니다.")
        
        all_statuses = df['주문상태'].unique()
        target_status = st.multiselect("상태 필터", all_statuses, default=all_statuses)
        
        if st.button("🚀 송장 변환 실행"):
            target_df = df[df['주문상태'].isin(target_status)]
            if target_df.empty:
                st.warning("해당하는 주문이 없습니다.")
            else:
                rows = []
                for no, g in target_df.groupby('주문번호'):
                    opts = []
                    for _, r in g.iterrows():
                        q = int(r['수량'])
                        for _ in range(q): opts.append(f"[{r['상품명']}] {r['옵션명']}")
                    opts.sort()
                    f = g.iloc[0]
                    rows.append({
                        "주문번호": f['주문번호'], "상태": f['주문상태'], "수령인": f['수령인'],
                        "상품내역": " // ".join(opts), "총수량": len(opts),
                        "주소": f['주소'], "연락처": f['연락처'], "우편번호": f['우편번호']
                    })
                
                res_df = pd.DataFrame(rows)
                st.dataframe(res_df)
                
                # 엑셀 다운로드
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    res_df.to_excel(writer, index=False)
                st.download_button("📥 엑셀 다운로드", output.getvalue(), "Janytree_송장.xlsx")

    # [Tab 3~6] 나머지 탭 (기능 동일)
    with tab3:
        st.dataframe(df) # 공구 관리 (간략화)
    with tab4:
        st.dataframe(df) # 재고 (간략화)
    with tab5:
        st.dataframe(df) # 고객 (간략화)
    with tab6:
        st.dataframe(df) # 원본

else:
    st.info("👈 왼쪽 사이드바에서 [데이터 불러오기]를 눌러주세요. (상세 조회로 인해 시간이 조금 걸릴 수 있습니다.)")
