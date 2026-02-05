import React, { useState, useMemo } from 'react';
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell 
} from 'recharts';
import { LayoutDashboard, FileText, ShoppingBag, Box, Users, Activity, Download, Search, AlertCircle } from 'lucide-react';

import Sidebar from './components/Sidebar';
import { DashboardState, TabType, ImwebOrder } from './types';
import { fetchImwebOrders } from './services/imwebService';
import * as Analytics from './utils/analytics';

// Initial State
const initialState: DashboardState = {
  orders: [],
  apiKey: '',
  apiSecret: '',
  startDate: new Date(new Date().setDate(new Date().getDate() - 30)).toISOString().split('T')[0],
  endDate: new Date().toISOString().split('T')[0],
  isLoading: false,
  error: null,
  lastSyncTime: null,
};

// Colors for charts
const COLORS = ['#6366f1', '#3b82f6', '#0ea5e9', '#06b6d4', '#14b8a6', '#8b5cf6'];

const App: React.FC = () => {
  const [state, setState] = useState<DashboardState>(initialState);
  const [activeTab, setActiveTab] = useState<TabType>(TabType.SALES);
  const [groupBuyFilter, setGroupBuyFilter] = useState('');

  // Handle Data Sync
  const handleSync = async () => {
    if (!state.apiKey) {
      setState(prev => ({ ...prev, error: 'API 키를 입력해주세요 (또는 "DEMO").' }));
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const orders = await fetchImwebOrders(state.apiKey, state.apiSecret, state.startDate, state.endDate);
      setState(prev => ({
        ...prev,
        orders,
        isLoading: false,
        lastSyncTime: new Date(),
        error: null
      }));
    } catch (err: any) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: err.message
      }));
    }
  };

  // --- Derived Data for UI ---
  const kpi = useMemo(() => Analytics.calculateKPIs(state.orders), [state.orders]);
  const dailyData = useMemo(() => Analytics.getDailyRevenue(state.orders), [state.orders]);
  const productData = useMemo(() => Analytics.getProductRevenue(state.orders), [state.orders]);
  const topOptions = useMemo(() => Analytics.getTopOptions(state.orders), [state.orders]);
  const vipCustomers = useMemo(() => Analytics.getVipCustomers(state.orders), [state.orders]);
  const cityStats = useMemo(() => Analytics.getCityStats(state.orders), [state.orders]);

  const filteredGroupBuyOrders = useMemo(() => {
    if (!groupBuyFilter) return state.orders;
    return state.orders.filter(o => 
      o.items.some(i => i.product_name.includes(groupBuyFilter) || i.option_name.includes(groupBuyFilter))
    );
  }, [state.orders, groupBuyFilter]);

  const groupBuyKpi = useMemo(() => Analytics.calculateKPIs(filteredGroupBuyOrders), [filteredGroupBuyOrders]);

  const invoiceData = useMemo(() => Analytics.generateInvoiceData(state.orders), [state.orders]);

  const downloadInvoices = () => {
    Analytics.downloadExcel(invoiceData, `invoices_${state.startDate}_${state.endDate}`);
  };

  // --- TAB CONTENT COMPONENTS ---

  const renderSalesTab = () => (
    <div className="space-y-6 animate-fadeIn">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: '총 매출액', value: `₩${kpi.totalRevenue.toLocaleString()}`, color: 'bg-indigo-50', text: 'text-indigo-600' },
          { label: '총 주문 건수', value: kpi.totalOrders.toLocaleString(), color: 'bg-blue-50', text: 'text-blue-600' },
          { label: '평균 주문단가 (객단가)', value: `₩${Math.floor(kpi.averageOrderValue).toLocaleString()}`, color: 'bg-emerald-50', text: 'text-emerald-600' },
          { label: '총 판매 수량', value: kpi.totalItemsSold.toLocaleString(), color: 'bg-purple-50', text: 'text-purple-600' },
        ].map((stat, i) => (
          <div key={i} className={`p-6 rounded-xl shadow-sm border border-slate-100 ${stat.color}`}>
            <p className="text-sm font-medium text-slate-500">{stat.label}</p>
            <p className={`text-2xl font-bold mt-2 ${stat.text}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Line Chart */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-lg font-bold text-slate-800 mb-4">일별 매출 추이</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} tickFormatter={(val) => val.slice(5)} />
                <YAxis stroke="#94a3b8" fontSize={12} tickFormatter={(val) => `₩${val/1000}k`} />
                <RechartsTooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                <Line type="monotone" dataKey="amount" stroke="#6366f1" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Donut Chart */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-lg font-bold text-slate-800 mb-4">상품별 판매 비중</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={productData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {productData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip formatter={(value: number) => `₩${value.toLocaleString()}`} />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );

  const renderInvoiceTab = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-slate-100">
        <div>
          <h3 className="text-lg font-bold text-slate-800">송장 데이터 생성기 (Invoice Generator)</h3>
          <p className="text-sm text-slate-500">주문 상품을 수량만큼 반복하여 합배송/포장 실수를 방지하는 송장 포맷으로 변환합니다.</p>
        </div>
        <button 
          onClick={downloadInvoices}
          className="flex items-center space-x-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors shadow-sm"
        >
          <Download className="w-4 h-4" />
          <span>엑셀 다운로드</span>
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left text-slate-600">
            <thead className="text-xs text-slate-700 uppercase bg-slate-50 border-b">
              <tr>
                <th className="px-6 py-3">주문번호</th>
                <th className="px-6 py-3">수령인</th>
                <th className="px-6 py-3">주문 상품 (포맷 변환됨)</th>
                <th className="px-6 py-3">결제 금액</th>
              </tr>
            </thead>
            <tbody>
              {invoiceData.slice(0, 50).map((row: any, idx) => (
                <tr key={idx} className="bg-white border-b hover:bg-slate-50">
                  <td className="px-6 py-4 font-medium">{row['주문번호']}</td>
                  <td className="px-6 py-4">{row['수령인']}</td>
                  <td className="px-6 py-4 font-mono text-xs text-indigo-600 bg-indigo-50 rounded px-2 py-1 inline-block m-2">
                    {row['상품명(변환됨)']}
                  </td>
                  <td className="px-6 py-4">₩{row['결제금액'].toLocaleString()}</td>
                </tr>
              ))}
              {invoiceData.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-6 py-10 text-center text-slate-400">데이터가 없습니다. 먼저 데이터를 불러오세요.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {invoiceData.length > 50 && (
          <div className="p-4 text-center text-sm text-slate-500 border-t bg-slate-50">
            전체 {invoiceData.length}건 중 상위 50건만 표시됩니다. 전체 데이터는 엑셀을 다운로드하세요.
          </div>
        )}
      </div>
    </div>
  );

  const renderGroupBuyTab = () => (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
        <div className="flex items-center space-x-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
            <input 
              type="text" 
              placeholder="키워드로 필터링 (예: '1차', '공구')"
              value={groupBuyFilter}
              onChange={(e) => setGroupBuyFilter(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="p-4 bg-orange-50 rounded-lg border border-orange-100">
            <p className="text-sm text-orange-600 font-medium">필터링 매출</p>
            <p className="text-2xl font-bold text-orange-700">₩{groupBuyKpi.totalRevenue.toLocaleString()}</p>
          </div>
          <div className="p-4 bg-orange-50 rounded-lg border border-orange-100">
            <p className="text-sm text-orange-600 font-medium">필터링 판매량</p>
            <p className="text-2xl font-bold text-orange-700">{groupBuyKpi.totalItemsSold.toLocaleString()} ea</p>
          </div>
        </div>

        <h4 className="font-bold text-slate-700 mb-4">필터링된 주문 목록</h4>
        <div className="overflow-x-auto border rounded-lg">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 border-b">
              <tr>
                <th className="px-4 py-2">주문번호</th>
                <th className="px-4 py-2">상품 정보</th>
                <th className="px-4 py-2">금액</th>
              </tr>
            </thead>
            <tbody>
              {filteredGroupBuyOrders.slice(0, 10).map((order) => (
                <tr key={order.order_no} className="border-b">
                  <td className="px-4 py-2">{order.order_no}</td>
                  <td className="px-4 py-2">
                    {order.items.map(i => (
                      <div key={i.item_no} className="text-xs text-slate-600">
                        {i.product_name} - {i.option_name} (x{i.amount})
                      </div>
                    ))}
                  </td>
                  <td className="px-4 py-2 font-medium">₩{order.pay_price.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  const renderInventoryTab = () => (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
        <h3 className="text-lg font-bold text-slate-800 mb-6">재고 인사이트: 옵션별 판매 순위</h3>
        <p className="text-slate-500 text-sm mb-4">선택한 기간 동안 가장 많이 팔린 옵션 순위입니다.</p>
        
        <div className="h-[500px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart layout="vertical" data={topOptions} margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
              <XAxis type="number" stroke="#94a3b8" />
              <YAxis dataKey="name" type="category" width={150} stroke="#475569" fontSize={11} />
              <RechartsTooltip cursor={{ fill: '#f8fafc' }} formatter={(val: number) => [val, '개 판매']} />
              <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={20} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );

  const renderCustomerTab = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-lg font-bold text-slate-800 mb-4">VIP 고객 리스트 (구매왕)</h3>
          <div className="overflow-y-auto max-h-80">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">고객명</th>
                  <th className="px-4 py-2 text-left">지역</th>
                  <th className="px-4 py-2 text-right">주문 횟수</th>
                  <th className="px-4 py-2 text-right">총 구매액</th>
                </tr>
              </thead>
              <tbody>
                {vipCustomers.map((vip, idx) => (
                  <tr key={idx} className="border-b hover:bg-slate-50">
                    <td className="px-4 py-2 font-medium">{vip.name}</td>
                    <td className="px-4 py-2 text-slate-500">{vip.city}</td>
                    <td className="px-4 py-2 text-right">{vip.count}</td>
                    <td className="px-4 py-2 text-right font-bold text-indigo-600">₩{vip.totalSpent.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-lg font-bold text-slate-800 mb-4">지역별 주문 현황</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={cityStats.slice(0, 10)}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" />
                <RechartsTooltip />
                <Bar dataKey="value" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );

  const renderDataSyncTab = () => (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 h-full overflow-hidden flex flex-col">
      <h3 className="text-lg font-bold text-slate-800 mb-4">원본 데이터 뷰어 (Raw Data)</h3>
      <div className="bg-slate-900 text-slate-300 p-4 rounded-lg font-mono text-xs overflow-auto flex-1">
        {state.orders.length > 0 
          ? JSON.stringify(state.orders.slice(0, 5), null, 2) + (state.orders.length > 5 ? `\n\n... ${state.orders.length - 5} more items` : '')
          : "// 데이터가 없습니다. 사이드바에서 '데이터 불러오기'를 클릭하세요."}
      </div>
      <div className="mt-4 p-3 bg-blue-50 text-blue-800 rounded text-sm flex items-center">
        <Activity className="w-4 h-4 mr-2" />
        상태: {state.isLoading ? '동기화 중...' : state.lastSyncTime ? '완료' : '대기'} | 건수: {state.orders.length}
      </div>
    </div>
  );

  return (
    <div className="flex bg-slate-50 min-h-screen">
      <Sidebar state={state} setState={setState} onSync={handleSync} />
      
      <main className="ml-80 flex-1 p-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Janytree 통합 운영 대시보드</h2>
            <p className="text-slate-500">매출 모니터링, 물류 자동화 및 고객 분석을 위한 대시보드입니다.</p>
          </div>
          {state.error && (
            <div className="flex items-center bg-red-100 text-red-700 px-4 py-2 rounded-lg text-sm">
              <AlertCircle className="w-4 h-4 mr-2" />
              {state.error}
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-1 mb-6 bg-white p-1 rounded-xl shadow-sm w-fit border border-slate-100">
          {[
            { id: TabType.SALES, icon: LayoutDashboard, label: '매출 대시보드' },
            { id: TabType.INVOICE, icon: FileText, label: '송장 생성기' },
            { id: TabType.GROUP_BUY, icon: ShoppingBag, label: '공구 관리' },
            { id: TabType.INVENTORY, icon: Box, label: '재고 인사이트' },
            { id: TabType.CUSTOMER, icon: Users, label: '고객 분석' },
            { id: TabType.DATA_SYNC, icon: Activity, label: '데이터 연동' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                ${activeTab === tab.id 
                  ? 'bg-indigo-600 text-white shadow-md' 
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'
                }`}
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="min-h-[500px]">
          {activeTab === TabType.SALES && renderSalesTab()}
          {activeTab === TabType.INVOICE && renderInvoiceTab()}
          {activeTab === TabType.GROUP_BUY && renderGroupBuyTab()}
          {activeTab === TabType.INVENTORY && renderInventoryTab()}
          {activeTab === TabType.CUSTOMER && renderCustomerTab()}
          {activeTab === TabType.DATA_SYNC && renderDataSyncTab()}
        </div>
      </main>
    </div>
  );
};

export default App;