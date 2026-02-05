import React from 'react';
import { RefreshCw, Lock, Calendar, Database } from 'lucide-react';
import { DashboardState } from '../types';

interface SidebarProps {
  state: DashboardState;
  setState: React.Dispatch<React.SetStateAction<DashboardState>>;
  onSync: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ state, setState, onSync }) => {
  const handleChange = (field: keyof DashboardState, value: any) => {
    setState(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="w-80 bg-slate-900 text-white min-h-screen p-6 flex flex-col shadow-xl fixed left-0 top-0 z-10 overflow-y-auto">
      <div className="mb-8 flex items-center space-x-2">
        <Database className="w-8 h-8 text-indigo-400" />
        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
          Janytree
        </h1>
      </div>

      <div className="space-y-6 flex-1">
        {/* API Authentication */}
        <div className="space-y-3">
          <div className="flex items-center text-sm font-semibold text-slate-400 mb-2">
            <Lock className="w-4 h-4 mr-2" /> API 인증 (Authentication)
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">API 키 ('DEMO' 입력 시 테스트 모드)</label>
            <input
              type="password"
              value={state.apiKey}
              onChange={(e) => handleChange('apiKey', e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              placeholder="API Key 입력"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Secret 키</label>
            <input
              type="password"
              value={state.apiSecret}
              onChange={(e) => handleChange('apiSecret', e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              placeholder="Secret Key 입력"
            />
          </div>
        </div>

        <hr className="border-slate-700" />

        {/* Date Settings */}
        <div className="space-y-3">
          <div className="flex items-center text-sm font-semibold text-slate-400 mb-2">
            <Calendar className="w-4 h-4 mr-2" /> 기간 설정
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">시작일</label>
            <input
              type="date"
              value={state.startDate}
              onChange={(e) => handleChange('startDate', e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 text-white-scheme"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">종료일</label>
            <input
              type="date"
              value={state.endDate}
              onChange={(e) => handleChange('endDate', e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>
      </div>

      <div className="mt-8">
        <button
          onClick={onSync}
          disabled={state.isLoading}
          className={`w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-lg font-bold text-white transition-all shadow-lg
            ${state.isLoading 
              ? 'bg-slate-700 cursor-not-allowed' 
              : 'bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 hover:shadow-indigo-500/25'
            }`}
        >
          <RefreshCw className={`w-5 h-5 ${state.isLoading ? 'animate-spin' : ''}`} />
          <span>{state.isLoading ? '동기화 중...' : '데이터 불러오기'}</span>
        </button>
        {state.lastSyncTime && (
          <p className="text-xs text-center text-slate-500 mt-2">
            마지막 동기화: {state.lastSyncTime.toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  );
};

export default Sidebar;