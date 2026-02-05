import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import time

# --------------------------------------------------------------------------
# 1. 페이지 설정
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Janytree 통합 대시보드",
    page_icon="📦",
    layout="wide"
)

# --------------------------------------------------------------------------
# 2. 사이드바: 설정 및 API 연동
# --------------------------------------------------------------------------
st.sidebar.title("🔧 설정 및 연동")

# API 키 입력 (세션에 저장되거나 Secrets에서 가져옴)
if "imweb_api_key" in st.secrets:
    api_key = st.secrets["imweb_api_key"]
    st.sidebar.success("✅ 저장된 API 키를 사용합니다.")
else:
    api_key = st.sidebar.text_input("API Key", type="password")

if "imweb_secret_key" in st.secrets:
    secret_key = st.secrets["imweb_secret_key"]
else:
    secret_key = st.sidebar.text_input("Secret Key", type="password")

# 데이터 불러오기 버튼
if st.sidebar.button("🔄 데이터 불러오기"):
    if not api_key or not secret_key:
        st.sidebar.error("API Key와 Secret Key를 입력해주세요.")
    else:
        with st.spinner("아임웹에서 데이터를 가져오는 중..."):
            try:
                # 1. 토큰 발급
                auth_url = "https://api.imweb.me/v2/auth"
                res = requests.post(auth_url, json={"key": api_key, "secret": secret_key})
                
                if res.status_code == 200:
                    access_token = res.json().get('access_token')
                    
                    # 2. 주문 데이터 가져오기 (PAYMENT 상태, 최근 100건)
                    # 실무에서는 페이지네이션(loop)으로 더 많이 가져와야 함
                    orders_url = "https://api.imweb.me/v2/shop/orders"
                    headers = {"access-token": access_token}
                    params = {"limit": 100, "status": "PAYMENT"}
                    
                    res_orders = requests.get(orders_url, headers=headers, params=params)
                    
                    if res_orders.status_code == 200:
                        raw_data = res_orders.json().get('data', {}).get('list', [])
                        
                        # 3. 데이터 가공 (Flatten)
                        clean_data = []
                        for order in raw_data:
                            order_date = datetime.fromtimestamp(order.get('order_date')).strftime('%Y-%m-%d')
                            for item in order.get('items', []):
                                clean_data.append({
                                    "주문번호": order.get('order_no'),
                                    "주문일자": order_date,
                                    "주문자명": order.get('orderer', {}).get('name'),
                                    "연락처": order.get('orderer', {}).get('call'),
                                    "상품명": item.get('prod_name'),
                                    "옵션명": item.get('options_str'),
                                    "수량": item.get('ea'),
                                    "결제금액": item.get('price_total'),
                                    "주소": order.get('shipping', {}).get('address'),
                                    "상세주소": order.get('shipping', {}).get('address_detail'),
                                    "우편번호": order.get('shipping', {}).get('zipcode'),
                                    "배송메시지": order.get('shipping', {}).get('memo'),
                                    "수령인": order.get('shipping', {}).get('name'),
                                    "수령인연락처": order.get('shipping', {}).get('call')
                                })
                        
                        df = pd.DataFrame(clean_data)
                        st.session_state['df'] = df
                        st.sidebar.success(f"성공! 총 {len(df)}개의 상품 주문을 가져왔습니다.")
                    else:
                        st.sidebar.error("주문 목록을 가져오지 못했습니다.")
                else:
                    st.sidebar.error("인증 실패! 키를 확인해주세요.")
            except Exception as e:
                st.sidebar.error(f"오류 발생: {e}")

# --------------------------------------------------------------------------
# 3. 메인 콘텐츠 (탭 구성)
# --------------------------------------------------------------------------
st.title("📦 Janytree 통합 운영 대시보드")

if 'df' in st.session_state:
    df = st.session_state['df']
    
    # 탭 생성
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 매출 현황", "📦 송장 생성", "📣 공구 관리", "🏭 재고/랭킹", "🔄 데이터 원본"])

    # === Tab 1: 매출 대시보드 ===
    with tab1:
        st.subheader("실시간 매출 현황")
        
        # KPI 지표
        total_sales = df['결제금액'].sum()
        total_qty = df['수량'].sum()
        total_orders = df['주문번호'].nunique()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("총 매출액", f"{total_sales:,.0f}원")
        col2.metric("총 판매 수량", f"{total_qty}개")
        col3.metric("총 주문 건수", f"{total_orders}건")
        
        st.divider()
        
        # 그래프 2개 배치
        c1, c2 = st.columns(2)
        
        # 일별 매출 추이
        daily_sales = df.groupby('주문일자')['결제금액'].sum().reset_index()
        fig_line = px.line(daily_sales, x='주문일자', y='결제금액', title='일별 매출 추이', markers=True)
        c1.plotly_chart(fig_line, use_container_width=True)
        
        # 상품별 판매 비중
        prod_share = df.groupby('상품명')['수량'].sum().reset_index()
        fig_pie = px.pie(prod_share, values='수량', names='상품명', title='상품별 판매 수량 비중', hole=0.4)
        c2.plotly_chart(fig_pie, use_container_width=True)

    # === Tab 2: 송장 생성기 (핵심 로직) ===
    with tab2:
        st.subheader("🚚 로젠택배 송장 변환기")
        st.info("💡 주문 수량만큼 옵션명을 자동으로 반복 출력합니다. (예: 크림 2개 -> '크림 // 크림')")
        
        if st.button("송장 파일 생성하기"):
            invoice_rows = []
            
            # 그룹핑 (주문번호 기준)
            for order_no, group in df.groupby('주문번호'):
                # 옵션명 반복 및 합치기 로직
                combined_options = []
                for _, row in group.iterrows():
                    qty = int(row['수량'])
                    opt_name = str(row['옵션명'])
                    # 수량만큼 리스트에 추가
                    for _ in range(qty):
                        combined_options.append(opt_name)
                
                # 정렬 (숫자 기준 오름차순 시도, 실패시 가나다순)
                combined_options.sort()
                final_option_str = " // ".join(combined_options)
                
                # 대표 정보 (첫 번째 행 기준)
                first = group.iloc[0]
                
                invoice_rows.append({
                    "주문번호": first['주문번호'],
                    "주문자명": first['주문자명'],
                    "주문자전화번호": first['연락처'],
                    "배송송장번호": "", # 공란
                    "수량": len(combined_options), # 총 낱개 수량
                    "상품명": first['상품명'], # 대표 상품명
                    "옵션명": final_option_str, # ✨ 핵심: 반복된 옵션명
                    "수령인": first['수령인'],
                    "수령인연락처": first['수령인연락처'],
                    "우편번호": first['우편번호'],
                    "주소": first['주소'],
                    "상세주소": first['상세주소'],
                    "배송메세지": first['배송메시지'],
                    "택배사명": "지정택배사"
                })
            
            df_invoice = pd.DataFrame(invoice_rows)
            st.dataframe(df_invoice.head())
            
            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_invoice.to_excel(writer, index=False, sheet_name='송장')
            
            st.download_button(
                label="📥 엑셀 송장 다운로드",
                data=output.getvalue(),
                file_name=f"송장_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.ms-excel"
            )

    # === Tab 3: 공구 관리 ===
    with tab3:
        st.subheader("📣 공동구매 성과 분석")
        keyword = st.text_input("공구 키워드 검색 (예: 차수, 공구)", value="공구")
        
        if keyword:
            mask = df['옵션명'].astype(str).str.contains(keyword) | df['상품명'].astype(str).str.contains(keyword)
            gb_df = df[mask]
            
            if not gb_df.empty:
                st.write(f"keyword '{keyword}' 검색 결과: 총 {len(gb_df)}건")
                gb_sales = gb_df.groupby('상품명')['결제금액'].sum().reset_index()
                st.dataframe(gb_sales)
            else:
                st.warning("해당 키워드의 주문이 없습니다.")

    # === Tab 4: 재고/랭킹 ===
    with tab4:
        st.subheader("🏆 상품/옵션 판매 랭킹")
        # 옵션별 많이 팔린 순서
        top_options = df.groupby('옵션명')['수량'].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top_options)

    # === Tab 5: 데이터 원본 ===
    with tab5:
        st.subheader("데이터 원본 (Raw Data)")
        st.dataframe(df)

else:
    st.info("👈 왼쪽 사이드바에 API Key를 입력하고 '데이터 불러오기'를 눌러주세요.")
