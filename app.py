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
if st.sidebar.button("🔄 데이터 불러오기 (상품연동)", type="primary"):
    if not api_key or not secret_key:
        st.sidebar.error("API Key와 Secret Key를 입력해주세요.")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        try:
            # [단계 1] 로그인
            status_text.text("🔑 로그인 중...")
            res = requests.post("https://api.imweb.me/v2/auth", json={"key": api_key, "secret": secret_key})
            
            if res.status_code != 200:
                st.error("로그인 실패! 키 값을 확인해주세요.")
                st.stop()
            
            access_token = res.json().get('access_token')
            headers = {"access-token": access_token}
            
            # ---------------------------------------------------------
            # [단계 2] '주문서(껍데기)' 가져오기 (배송지, 주문자 정보용)
            # ---------------------------------------------------------
            status_text.text("📂 주문 정보(주소/연락처) 가져오는 중...")
            progress_bar.progress(20)
            
            # 넉넉하게 1000건 조회
            params_orders = {"limit": 1000} 
            res_orders = requests.get("https://api.imweb.me/v2/shop/orders", headers=headers, params=params_orders)
            orders_list = res_orders.json().get('data', {}).get('list', [])
            
            # 주문 정보를 '주문번호'를 열쇠로 하는 사전(Dictionary)으로 변환 (빠른 찾기 위해)
            orders_map = {}
            for o in orders_list:
                # 날짜 처리
                ts = o.get('order_time', 0)
                dt = datetime.fromtimestamp(ts)
                
                # 배송지 처리
                delivery = o.get('delivery', {})
                addr = delivery.get('address', {})
                
                orders_map[o['order_no']] = {
                    'order_date': dt,
                    'order_date_str': dt.strftime('%Y-%m-%d'),
                    'orderer_name': o.get('orderer', {}).get('name'),
                    'orderer_call': o.get('orderer', {}).get('call'),
                    'receiver_name': addr.get('name'),
                    'receiver_call': addr.get('phone'),
                    'address': f"{addr.get('address', '')} {addr.get('address_detail', '')}",
                    'zipcode': addr.get('postcode'),
                    'memo': addr.get('memo', '-')
                }

            # ---------------------------------------------------------
            # [단계 3] '상품 목록(알맹이)' 가져오기 (prod-orders 엔드포인트 사용!)
            # ---------------------------------------------------------
            status_text.text("📦 진짜 상품 목록(prod-orders) 가져오는 중...")
            progress_bar.progress(50)
            
            # 여기가 핵심입니다! /shop/orders 대신 /shop/prod-orders를 씁니다.
            params_prod = {"limit": 1000}
            res_items = requests.get("https://api.imweb.me/v2/shop/prod-orders", headers=headers, params=params_prod)
            
            if res_items.status_code != 200:
                st.error("상품 목록 조회 실패. API 권한을 확인해주세요.")
                st.write(res_items.text) # 에러 메시지 보여주기
                st.stop()
                
            items_list = res_items.json().get('data', {}).get('list', [])
            
            if not items_list:
                st.warning("상품 데이터가 없습니다.")
                st.stop()

            # ---------------------------------------------------------
            # [단계 4] 두 데이터 합체하기 (Merge)
            # ---------------------------------------------------------
            status_text.text("🔗 주문정보와 상품정보 연결 중...")
            progress_bar.progress(80)
            
            clean_data = []
            
            for item in items_list:
                # 이 상품의 주문번호 찾기
                order_no = item.get('order_no')
                
                # 미리 정리해둔 주문서(orders_map)에 이 주문번호가 있는지 확인
                if order_no in orders_map:
                    order_info = orders_map[order_no]
                    
                    # 날짜 필터링
                    if start_date <= order_info['order_date'].date() <= end_date:
                        
                        # 상태 한글 변환
                        status_map = {
                            "PAY_WAIT": "입금대기", "PAYMENT": "결제완료", 
                            "PREPARE": "배송준비", "DELIV_WAIT": "배송대기",
                            "DELIV_ING": "배송중", "DELIV_COMP": "배송완료",
                            "CANCEL": "취소", "EXCHANGE": "교환", "RETURN": "반품",
                            "CONFIRM": "구매확정"
                        }
                        raw_status = item.get('status', 'UNKNOWN')
                        kor_status = status_map.get(raw_status, raw_status)

                        # 최종 데이터 한 줄 생성
                        clean_data.append({
                            "주문번호": order_no,
                            "주문상태": kor_status,
                            "주문일자": order_info['order_date_str'],
                            "상품명": item.get('prod_name', '상품명없음'), # 여기서 상품명을 가져옵니다
                            "옵션명": item.get('options_str', item.get('option_name', '-')),
                            "수량": int(float(item.get('ea', 1))), # ea가 실수형일 경우 대비
                            "결제금액": float(item.get('payment_price', item.get('price', 0))),
                            "주문자": order_info['orderer_name'],
                            "연락처": order_info['orderer_call'],
                            "수령인": order_info['receiver_name'],
                            "수령인연락처": order_info['receiver_call'],
                            "우편번호": order_info['zipcode'],
                            "주소": order_info['address'],
                            "배송메시지": order_info['memo']
                        })
            
            # 데이터프레임 생성
            st.session_state['df'] = pd.DataFrame(clean_data)
            
            progress_bar.progress(100)
            status_text.success(f"✅ 성공! 총 {len(clean_data)}개의 상품 데이터를 완벽하게 연결했습니다.")
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
    
    # 탭 메뉴
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 매출", "📄 송장", "📦 공구", 
        "💎 재고", "👥 고객", "🔌 원본"
    ])

    # [Tab 1] 매출
    with tab1:
        total_sales = df['결제금액'].sum()
        total_qty = df['수량'].sum()
        c1, c2 = st.columns(2)
        c1.metric("총 매출액", f"₩{total_sales:,.0f}")
        c2.metric("총 판매 수량", f"{total_qty}개")
        
        st.divider()
        st.write("📈 상품별 판매량")
        st.bar_chart(df.groupby('상품명')['수량'].sum())

    # [Tab 2] 송장
    with tab2:
        st.subheader("송장 생성기")
        st.caption("결제완료/배송준비 상태인 주문만 골라서 송장을 만듭니다.")
        
        # 송장 생성 대상 상태 (기본값: 결제완료, 배송준비)
        target_statuses = st.multiselect(
            "송장 만들 상태 선택", 
            df['주문상태'].unique(), 
            default=[s for s in df['주문상태'].unique() if s in ['결제완료', '배송준비']]
        )
        
        if st.button("🚀 선택한 상태로 송장 만들기"):
            target_df = df[df['주문상태'].isin(target_statuses)]
            
            if target_df.empty:
                st.warning("선택한 상태의 주문이 없습니다.")
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
                        "합포장내역": " // ".join(opts), "총수량": len(opts),
                        "주소": f['주소'], "연락처": f['수령인연락처'], "우편번호": f['우편번호']
                    })
                
                res_df = pd.DataFrame(rows)
                st.dataframe(res_df)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    res_df.to_excel(writer, index=False)
                st.download_button("📥 엑셀 다운로드", output.getvalue(), "Janytree_송장.xlsx")

    # [나머지 탭]
    with tab3:
        st.subheader("공구 차수 검색")
        k = st.text_input("검색어 (예: 1차)")
        if k: st.dataframe(df[df['상품명'].str.contains(k)])
        else: st.dataframe(df)
        
    with tab4:
        st.subheader("옵션별 재고 현황 (판매량 기준)")
        st.dataframe(df.groupby(['상품명', '옵션명'])['수량'].sum().sort_values(ascending=False))
        
    with tab5:
        st.subheader("VIP 고객")
        st.dataframe(df.groupby('주문자')['결제금액'].sum().sort_values(ascending=False).head(10))
        
    with tab6:
        st.dataframe(df)

else:
    st.info("👈 왼쪽 사이드바에서 [데이터 불러오기]를 눌러주세요.")
