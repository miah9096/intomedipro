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
                            # [단계 3] 데이터 가공
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
                                    
                                    # 상품 정보가 없는 경우 (에러 방지용)
                                    if not items:
                                        clean_data.append({
                                            "주문번호": o.get('order_no'),
                                            "주문일자": order_date_str,
                                            "상품명": "정보없음",
                                            "옵션명": "-",
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
                                        # 상품 정보가 있는 경우
                                        for i in items:
                                            clean_data.append({
                                                "주문번호": o.get('order_no'),
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
                            
                            st.session_state['df'] = pd.DataFrame(clean_data)
                            st.success(f"✅ 데이터 연동 성공! 총 {len(clean_data)}건의 데이터를 가져왔습니다.")
                    else:
                        st.error("데이터 조회 실패")
            except Exception as e:
                st.error(f"오류 발생: {e}")

# --------------------------------------------------------------------------
# 3. 메인 콘텐츠 (6개 탭 구현)
# --------------------------------------------------------------------------
st.title("Janytree 통합 운영 대시보드")
st.markdown("매출 모니터링, 물류 자동화 및 고객 분석을 위한 대시보드입니다.")

# 데이터 유무 확인
if 'df' in st.session_state and not st.session_state['df'].empty:
    df = st.session_state['df']
    
    # 탭 구성
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 매출 대시보드", "📄 송장 생성기", "📦 공구 관리", "💎 재고 인사이트", "👥 고객 분석", "🔌 데이터 연동"
    ])

    # === [Tab 1] 매출 대시보드 ===
    with tab1:
        # KPI 카드
        total_sales = df['결제금액'].sum()
        total_orders = df['주문번호'].nunique()
        total_qty = df['수량'].sum()
        
        # 0으로 나누기 방지
        if total_orders > 0:
            avg_price = total_sales / total_orders
        else:
            avg_price = 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 매출액", f"₩{total_sales:,.0f}")
        c2.metric("총 주문 건수", f"{total_orders:,}건")
        c3.metric("평균 주문단가", f"₩{avg_price:,.0f}")
        c4.metric("총 판매 수량", f"{total_qty:,}개")
        
        st.divider()
        
        col_left, col_right = st.columns([2, 1])
        with col_left:
            # 일별 매출 추이
            daily_sales = df.groupby('주문일자')['결제금액'].sum().reset_index()
            fig_line = px.line(daily_sales, x='주문일자', y='결제금액', title='일별 매출 추이', markers=True)
            st.plotly_chart(fig_line, use_container_width=True)
        with col_right:
            # 상품별 판매 비중
            prod_share = df.groupby('상품명')['수량'].sum().reset_index()
            fig_pie = px.pie(prod_share, values='수량', names='상품명', title='상품별 판매 비중', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

    # === [Tab 2] 송장 생성기 ===
    with tab2:
        st.subheader("송장 데이터 생성기 (Invoice Generator)")
        st.caption("주문 상품을 수량만큼 반복하여 합배송/포장 실수를 방지하는 송장 포맷으로 변환합니다.")
        
        if st.button("🚀 송장 변환 실행", key='btn_invoice'):
            invoice_rows = []
            for order_no, group in df.groupby('주문번호'):
                opts = []
                # 옵션명 반복 로직
                for _, row in group.iterrows():
                    qty = int(row['수량']) if row['수량'] > 0 else 1
                    for _ in range(qty):
                        opts.append(f"[{row['상품명']}] {row['옵션명']}")
                opts.sort()
                
                f = group.iloc[0]
                invoice_rows.append({
                    "주문번호": f['주문번호'],
                    "수령인": f['수령인'],
                    "주문 상품 (포맷 변환됨)": " // ".join(opts),
                    "총수량": len(opts),
                    "결제 금액": f['결제금액'],
                    "연락처": f['연락처'],
                    "주소": f['주소'],
                    "우편번호": f['우편번호'],
                    "배송메시지": f['배송메시지']
                })
            
            inv_df = pd.DataFrame(invoice_rows)
            st.dataframe(inv_df, use_container_width=True)
            
            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                inv_df.to_excel(writer, index=False)
            st.download_button("📥 엑셀 다운로드", output.getvalue(), f"Janytree_송장_{datetime.now().strftime('%Y%m%d')}.xlsx")

    # === [Tab 3] 공구 관리 ===
    with tab3:
        st.subheader("공구 차수별 성과 분석")
        keyword = st.text_input("🔍 키워드로 필터링 (예: '1차', '공구')", placeholder="상품명이나 옵션에 포함된 단어를 입력하세요")
        
        if keyword:
            mask = df['상품명'].str.contains(keyword) | df['옵션명'].str.contains(keyword)
            gb_df = df[mask]
            
            # 필터링 결과 카드
            f_sales = gb_df['결제금액'].sum()
            f_qty = gb_df['수량'].sum()
            
            fc1, fc2 = st.columns(2)
            fc1.metric("필터링 매출", f"₩{f_sales:,.0f}")
            fc2.metric("필터링 판매량", f"{f_qty} ea")
            
            st.write("필터링된 주문 목록:")
            st.dataframe(gb_df[['주문번호', '상품명', '옵션명', '수량', '결제금액']], use_container_width=True)
        else:
            st.info("👆 위 검색창에 '공구' 또는 '차수'를 입력하면 해당 주문만 모아서 보여줍니다.")

    # === [Tab 4] 재고 인사이트 ===
    with tab4:
        st.subheader("재고 인사이트: 옵션별 판매 순위")
        st.caption("선택한 기간 동안 가장 많이 팔린 옵션 순위입니다.")
        
        rank_df = df.groupby(['상품명', '옵션명'])['수량'].sum().reset_index().sort_values(by='수량', ascending=False).head(15)
        fig_bar = px.bar(rank_df, x='수량', y='옵션명', orientation='h', text='수량', title='Top 15 판매 옵션')
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)

    # === [Tab 5] 고객 분석 ===
    with tab5:
        st.subheader("VIP 고객 및 지역 분석")
        
        c_left, c_right = st.columns([1, 1])
        
        with c_left:
            st.write("🏆 VIP 고객 리스트 (구매왕)")
            vip_df = df.groupby(['주문자', '지역']).agg({'주문번호': 'nunique', '결제금액': 'sum'}).reset_index()
            vip_df.columns = ['고객명', '지역', '주문 횟수', '총 구매액']
            vip_df = vip_df.sort_values(by='총 구매액', ascending=False).head(10)
            st.dataframe(vip_df, use_container_width=True)
            
        with c_right:
            st.write("🗺️ 지역별 주문 현황")
            region_df = df['지역'].value_counts().reset_index()
            region_df.columns = ['지역', '주문수']
            fig_map = px.bar(region_df, x='지역', y='주문수', title='지역별 주문 분포')
            st.plotly_chart(fig_map, use_container_width=True)

    # === [Tab 6] 데이터 연동 ===
    with tab6:
        st.subheader("원본 데이터 뷰어 (Raw Data)")
        st.dataframe(df)

# 데이터 없을 때 초기 화면
else:
    # 탭 모양은 보여주되 내용은 비활성
    st.info("👈 왼쪽 사이드바에 API Key를 입력하고 [데이터 불러오기]를 눌러주세요.")
    
    # 빈 화면 예시 (스크린샷 느낌 유지)
    dummy_tabs = st.tabs(["매출 대시보드", "송장 생성기", "공구 관리", "재고 인사이트", "고객 분석", "데이터 연동"])
    with dummy_tabs[0]:
        st.write("데이터가 없습니다. 먼저 데이터를 불러오세요.")
