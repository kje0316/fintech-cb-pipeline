'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import type {
  FullAnalysisResponse,
} from '@/lib/types';

// Tab Types
type TabId = 'diagnosis' | 'analysis' | 'partners';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const tabs: Tab[] = [
  {
    id: 'diagnosis',
    label: 'AI 리스크 진단',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    id: 'analysis',
    label: 'AI 분석 & 시뮬레이션',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
  {
    id: 'partners',
    label: '협력사 추천',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
  },
];

export default function ResultPage() {
  const [result, setResult] = useState<FullAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('diagnosis');

  // What-if 시뮬레이션 상태
  const [simDebtRatio, setSimDebtRatio] = useState<number>(0);
  const [simPrediction, setSimPrediction] = useState<number | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const storedResult = localStorage.getItem('analysisResult');
        if (!storedResult) {
          setError('분석 결과가 없습니다. 먼저 파일을 업로드해주세요.');
          setLoading(false);
          return;
        }

        const parsed = JSON.parse(storedResult);
        setResult(parsed);

        // 초기 부채비율 설정
        const debtRatio = parsed.derived_ratios?.R006 || parsed.benchmark?.metrics?.find((m: any) => m.key === 'R006')?.company_value || 200;
        setSimDebtRatio(Math.round(debtRatio));
      } catch (err) {
        console.error('Error loading data:', err);
        setError('데이터를 불러오는 중 오류가 발생했습니다.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // What-if 시뮬레이션 효과
  useEffect(() => {
    if (result && simDebtRatio > 0) {
      // 간단한 시뮬레이션: 부채비율이 낮을수록 부도확률 감소
      const baseProb = result.default_prediction.default_probability;
      const originalDebtRatio = result.derived_ratios?.R006 || 200;
      const change = (simDebtRatio - originalDebtRatio) / originalDebtRatio;
      const newProb = Math.max(0.01, Math.min(0.99, baseProb * (1 + change * 0.5)));
      setSimPrediction(newProb);
    }
  }, [simDebtRatio, result]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">분석 결과를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-600 font-semibold mb-4">{error || '결과를 찾을 수 없습니다.'}</p>
          <Link
            href="/upload"
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            기업 진단하기
          </Link>
        </div>
      </div>
    );
  }

  const { default_prediction, shap_values, clustering, benchmark, partners = [], diagnosis } = result;

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'Low': return 'text-green-600';
      case 'Medium': return 'text-yellow-600';
      case 'High': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getRiskBgColor = (level: string) => {
    switch (level) {
      case 'Low': return 'from-green-500 to-green-600';
      case 'Medium': return 'from-yellow-500 to-yellow-600';
      case 'High': return 'from-red-500 to-red-600';
      default: return 'from-gray-500 to-gray-600';
    }
  };

  const getRiskLabel = (level: string) => {
    switch (level) {
      case 'Low': return '안전';
      case 'Medium': return '주의';
      case 'High': return '위험';
      default: return level;
    }
  };

  const getSimRiskLevel = (prob: number) => {
    if (prob < 0.3) return 'Low';
    if (prob < 0.6) return 'Medium';
    return 'High';
  };

  // 레이더 차트에 상위 10% 라인 추가
  const enhancedRadarData = benchmark.radar_data.map(item => ({
    ...item,
    top10: Math.min(100, item.cluster_avg * 1.3), // 상위 10% 추정
  }));

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/upload"
                className="text-gray-500 hover:text-gray-700"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </Link>
              <div>
                <h1 className="text-xl font-bold text-gray-900">AI 경영 진단 리포트</h1>
                <p className="text-sm text-gray-500">분석 완료</p>
              </div>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-1 border-b border-gray-200 -mb-px">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Tab 1: AI 리스크 진단 */}
        {activeTab === 'diagnosis' && (
          <div className="space-y-6">
            {/* 종합 부도 위험도 Gauge */}
            <div className={`bg-gradient-to-r ${getRiskBgColor(default_prediction.risk_level)} rounded-2xl p-8 text-white shadow-xl`}>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-center">
                <div className="lg:col-span-1">
                  <h2 className="text-2xl font-bold mb-2">종합 부도 위험도</h2>
                  <p className="text-white/80 text-sm">AI 모델 기반 분석</p>
                </div>
                <div className="lg:col-span-1 text-center">
                  <div className="relative inline-block">
                    <svg className="w-40 h-40" viewBox="0 0 100 50">
                      {/* 게이지 배경 */}
                      <path
                        d="M10 50 A40 40 0 0 1 90 50"
                        fill="none"
                        stroke="rgba(255,255,255,0.2)"
                        strokeWidth="8"
                        strokeLinecap="round"
                      />
                      {/* 게이지 값 */}
                      <path
                        d="M10 50 A40 40 0 0 1 90 50"
                        fill="none"
                        stroke="white"
                        strokeWidth="8"
                        strokeLinecap="round"
                        strokeDasharray={`${default_prediction.default_probability * 126} 126`}
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-end justify-center pb-2">
                      <span className="text-4xl font-bold">
                        {(default_prediction.default_probability * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  <div className="mt-2">
                    <span className="inline-block px-4 py-1 bg-white/20 rounded-full text-sm font-semibold">
                      {getRiskLabel(default_prediction.risk_level)} 단계
                    </span>
                  </div>
                </div>
                <div className="lg:col-span-1 text-right">
                  <div className="inline-block bg-white/10 rounded-lg p-4">
                    <div className="text-sm text-white/70 mb-1">클러스터</div>
                    <div className="text-xl font-bold">
                      {clustering.cluster_name}
                    </div>
                    <div className="text-xs text-white/60 mt-1">{clustering.cluster_description?.slice(0, 20) || '동종 업계 비교 그룹'}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* SHAP 위험 요인 분석 */}
            {shap_values && shap_values.contributions && (
              <div className="bg-white rounded-2xl shadow-lg p-6">
                <h3 className="text-lg font-bold text-gray-800 mb-2">위험 요인 분석</h3>
                <p className="text-sm text-gray-500 mb-6">
                  부도 확률에 영향을 미치는 주요 요인 (영향력 순)
                </p>

                {/* 위험 증가 요인 */}
                <div className="mb-6">
                  <h4 className="text-sm font-semibold text-red-600 mb-3 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    위험 증가 요인
                  </h4>
                  <div className="space-y-2">
                    {shap_values.contributions
                      .filter(c => c.shap_value > 0)
                      .slice(0, 4)
                      .map((factor, idx) => {
                        const maxPositive = Math.max(...shap_values.contributions.filter(c => c.shap_value > 0).map(c => c.contribution_pct));
                        const barWidth = Math.min(100, (factor.contribution_pct / maxPositive) * 100);
                        return (
                          <div key={idx} className="flex items-center gap-3">
                            <div className="w-28 text-sm text-gray-700 font-medium truncate" title={factor.feature_name}>
                              {factor.feature_name}
                            </div>
                            <div className="flex-1 bg-red-100 rounded-full h-5 overflow-hidden">
                              <div
                                className="h-full bg-red-500 rounded-full flex items-center justify-end pr-2"
                                style={{ width: `${barWidth}%`, minWidth: '40px' }}
                              >
                                <span className="text-xs text-white font-semibold">
                                  +{factor.contribution_pct.toFixed(1)}%
                                </span>
                              </div>
                            </div>
                            <div className="w-20 text-right text-xs text-gray-500">
                              {factor.feature_value.toLocaleString()}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>

                {/* 위험 감소 요인 */}
                <div>
                  <h4 className="text-sm font-semibold text-green-600 mb-3 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    위험 감소 요인
                  </h4>
                  <div className="space-y-2">
                    {shap_values.contributions
                      .filter(c => c.shap_value < 0)
                      .slice(0, 4)
                      .map((factor, idx) => {
                        const maxNegative = Math.max(...shap_values.contributions.filter(c => c.shap_value < 0).map(c => Math.abs(c.contribution_pct)));
                        const barWidth = Math.min(100, (Math.abs(factor.contribution_pct) / maxNegative) * 100);
                        return (
                          <div key={idx} className="flex items-center gap-3">
                            <div className="w-28 text-sm text-gray-700 font-medium truncate" title={factor.feature_name}>
                              {factor.feature_name}
                            </div>
                            <div className="flex-1 bg-green-100 rounded-full h-5 overflow-hidden">
                              <div
                                className="h-full bg-green-500 rounded-full flex items-center justify-end pr-2"
                                style={{ width: `${barWidth}%`, minWidth: '40px' }}
                              >
                                <span className="text-xs text-white font-semibold">
                                  {factor.contribution_pct.toFixed(1)}%
                                </span>
                              </div>
                            </div>
                            <div className="w-20 text-right text-xs text-gray-500">
                              {factor.feature_value.toLocaleString()}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              </div>
            )}

            {/* 레이더 차트 - 클러스터 벤치마킹 */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-lg font-bold text-gray-800">동적 벤치마킹</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                      {clustering.cluster_name}
                    </span>
                    <span className="text-sm text-gray-500">클러스터 내 비교</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={enhancedRadarData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
                      <Radar
                        name="귀사"
                        dataKey="company"
                        stroke="#3B82F6"
                        fill="#3B82F6"
                        fillOpacity={0.5}
                        strokeWidth={2}
                      />
                      <Radar
                        name="클러스터 평균"
                        dataKey="cluster_avg"
                        stroke="#9CA3AF"
                        fill="#9CA3AF"
                        fillOpacity={0.2}
                        strokeWidth={2}
                      />
                      <Radar
                        name="상위 10%"
                        dataKey="top10"
                        stroke="#10B981"
                        fill="none"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                      />
                      <Legend />
                      <Tooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>

                <div className="space-y-3">
                  <h4 className="font-semibold text-gray-700 mb-4">세부 지표 비교</h4>
                  {benchmark.metrics.slice(0, 6).map((metric, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <span className="font-medium text-gray-700">{metric.name}</span>
                        <div className="text-xs text-gray-500">
                          평균: {metric.cluster_avg.toLocaleString()} {metric.unit}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-gray-800">
                          {metric.company_value.toLocaleString()} {metric.unit}
                        </div>
                        <div className={`text-xs ${
                          metric.comparison === 'above' ? 'text-green-600' :
                          metric.comparison === 'below' ? 'text-red-600' : 'text-gray-600'
                        }`}>
                          상위 {100 - metric.percentile}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: AI 분석 & 시뮬레이션 */}
        {activeTab === 'analysis' && (
          <div className="space-y-6">
            {/* Executive Summary */}
            <div className={`bg-gradient-to-r ${getRiskBgColor(default_prediction.risk_level)} rounded-2xl p-8 text-white shadow-xl`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h2 className="text-2xl font-bold mb-2">경영진단 Executive Summary</h2>
                  <p className="text-white/80 text-sm mb-4">AI 기반 종합 재무 분석 리포트</p>
                  <div className="bg-white/10 rounded-xl p-4 backdrop-blur-sm">
                    <p className="leading-relaxed">
                      귀사는 <span className="font-bold">{clustering.cluster_name}</span> 클러스터에 속하며,
                      현재 부도 위험도는 <span className="font-bold">{(default_prediction.default_probability * 100).toFixed(1)}%</span>로
                      <span className="font-bold"> {getRiskLabel(default_prediction.risk_level)} 단계</span>입니다.
                      {default_prediction.risk_level === 'High' && ' 즉각적인 재무 구조 개선 조치가 필요합니다.'}
                      {default_prediction.risk_level === 'Medium' && ' 일부 핵심 지표의 선제적 관리가 권장됩니다.'}
                      {default_prediction.risk_level === 'Low' && ' 현재 재무 상태를 유지하며 성장 전략에 집중할 수 있습니다.'}
                    </p>
                  </div>
                </div>
                <div className="ml-6 text-center bg-white/20 rounded-xl p-4">
                  <div className="text-4xl font-bold">{(default_prediction.default_probability * 100).toFixed(0)}%</div>
                  <div className="text-sm text-white/80">부도 위험</div>
                </div>
              </div>
            </div>

            {/* 현황 진단 섹션 */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                1. 현황 진단
              </h3>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 강점 분석 */}
                <div className="border border-green-200 rounded-xl p-5 bg-green-50/50">
                  <h4 className="font-bold text-green-800 mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    강점 (Strengths)
                  </h4>
                  <ul className="space-y-3">
                    {shap_values?.contributions?.filter(c => c.shap_value < 0).slice(0, 3).map((factor, idx) => (
                      <li key={idx} className="flex items-start gap-3">
                        <span className="w-6 h-6 bg-green-200 text-green-700 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0">
                          {idx + 1}
                        </span>
                        <div>
                          <span className="font-semibold text-gray-800">{factor.feature_name}</span>
                          <p className="text-sm text-gray-600 mt-1">
                            현재 {factor.feature_value.toLocaleString()}으로 부도 위험을 {Math.abs(factor.contribution_pct).toFixed(1)}%p 낮추고 있습니다.
                            동종 업계 대비 우수한 수준입니다.
                          </p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* 약점 분석 */}
                <div className="border border-red-200 rounded-xl p-5 bg-red-50/50">
                  <h4 className="font-bold text-red-800 mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    약점 (Weaknesses)
                  </h4>
                  <ul className="space-y-3">
                    {shap_values?.contributions?.filter(c => c.shap_value > 0).slice(0, 3).map((factor, idx) => (
                      <li key={idx} className="flex items-start gap-3">
                        <span className="w-6 h-6 bg-red-200 text-red-700 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0">
                          {idx + 1}
                        </span>
                        <div>
                          <span className="font-semibold text-gray-800">{factor.feature_name}</span>
                          <p className="text-sm text-gray-600 mt-1">
                            현재 {factor.feature_value.toLocaleString()}으로 부도 위험을 {factor.contribution_pct.toFixed(1)}%p 높이고 있습니다.
                            개선이 필요한 영역입니다.
                          </p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* 우선 개선 영역 */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2">
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                2. 우선 개선 영역 (Priority Actions)
              </h3>

              <div className="space-y-4">
                {shap_values?.contributions?.filter(c => c.shap_value > 0).slice(0, 3).map((factor, idx) => {
                  const urgency = idx === 0 ? '긴급' : idx === 1 ? '높음' : '보통';
                  const urgencyColor = idx === 0 ? 'bg-red-100 text-red-700' : idx === 1 ? 'bg-orange-100 text-orange-700' : 'bg-yellow-100 text-yellow-700';

                  // 지표별 개선 가이드 생성
                  const getImprovementGuide = (featureName: string) => {
                    if (featureName.includes('부채') || featureName.includes('차입')) {
                      return {
                        action: '부채 구조 최적화',
                        detail: '단기 차입금을 장기로 전환하고, 불필요한 부채를 상환하여 재무 안정성을 확보하세요.',
                        target: '업계 평균 수준까지 단계적 감축',
                        timeline: '6-12개월'
                      };
                    } else if (featureName.includes('유동') || featureName.includes('당좌')) {
                      return {
                        action: '유동성 관리 강화',
                        detail: '매출채권 회수 기간을 단축하고, 재고 회전율을 개선하여 현금 흐름을 확보하세요.',
                        target: '유동비율 150% 이상 유지',
                        timeline: '3-6개월'
                      };
                    } else if (featureName.includes('수익') || featureName.includes('이익')) {
                      return {
                        action: '수익성 개선',
                        detail: '원가 절감, 고마진 제품 비중 확대, 운영 효율화를 통해 수익성을 높이세요.',
                        target: '영업이익률 업계 상위 30% 진입',
                        timeline: '12-18개월'
                      };
                    } else if (featureName.includes('자본') || featureName.includes('자기')) {
                      return {
                        action: '자본 확충',
                        detail: '유보이익 축적, 필요시 증자 검토를 통해 자기자본을 강화하세요.',
                        target: '자기자본비율 30% 이상',
                        timeline: '12-24개월'
                      };
                    }
                    return {
                      action: '해당 지표 개선',
                      detail: '해당 지표의 구성 요소를 분석하고 개선 방안을 수립하세요.',
                      target: '업계 평균 이상',
                      timeline: '6-12개월'
                    };
                  };

                  const guide = getImprovementGuide(factor.feature_name);

                  return (
                    <div key={idx} className="border border-gray-200 rounded-xl p-5 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <span className="w-8 h-8 bg-gray-100 text-gray-700 rounded-full flex items-center justify-center font-bold">
                            {idx + 1}
                          </span>
                          <div>
                            <h4 className="font-bold text-gray-800">{guide.action}</h4>
                            <p className="text-sm text-gray-500">대상 지표: {factor.feature_name}</p>
                          </div>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${urgencyColor}`}>
                          우선순위: {urgency}
                        </span>
                      </div>

                      <p className="text-gray-700 mb-4">{guide.detail}</p>

                      <div className="grid grid-cols-3 gap-4 bg-gray-50 rounded-lg p-4">
                        <div>
                          <div className="text-xs text-gray-500 mb-1">현재 값</div>
                          <div className="font-semibold text-gray-800">{factor.feature_value.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-500 mb-1">목표</div>
                          <div className="font-semibold text-blue-600">{guide.target}</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-500 mb-1">권장 기간</div>
                          <div className="font-semibold text-gray-800">{guide.timeline}</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 단기/장기 전략 로드맵 */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
                3. 전략 로드맵
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* 단기 전략 */}
                <div className="border-2 border-blue-200 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-semibold">단기</span>
                    <span className="text-gray-500 text-sm">0-6개월</span>
                  </div>
                  <h4 className="font-bold text-gray-800 mb-4">즉시 실행 과제</h4>
                  <ul className="space-y-3">
                    <li className="flex items-start gap-2">
                      <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-gray-700">
                        {default_prediction.risk_level === 'High'
                          ? '긴급 유동성 확보: 매출채권 회수 가속화, 불필요 재고 처분'
                          : '현금흐름 모니터링 체계 구축 및 주간 점검'}
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-gray-700">비용 구조 분석 및 불필요 비용 절감 (목표: 10% 이상)</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-gray-700">주거래 은행과 차입금 조건 재협상 검토</span>
                    </li>
                  </ul>
                </div>

                {/* 장기 전략 */}
                <div className="border-2 border-purple-200 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-semibold">장기</span>
                    <span className="text-gray-500 text-sm">6-24개월</span>
                  </div>
                  <h4 className="font-bold text-gray-800 mb-4">구조적 개선 과제</h4>
                  <ul className="space-y-3">
                    <li className="flex items-start gap-2">
                      <svg className="w-5 h-5 text-purple-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-gray-700">사업 포트폴리오 재검토 및 저수익 사업 구조조정</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="w-5 h-5 text-purple-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-gray-700">
                        {default_prediction.risk_level === 'Low'
                          ? '성장 투자를 위한 자본 구조 최적화 (레버리지 활용 검토)'
                          : '자기자본 확충 방안 검토 (유보이익 축적, 증자 등)'}
                      </span>
                    </li>
                    <li className="flex items-start gap-2">
                      <svg className="w-5 h-5 text-purple-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-gray-700">디지털 전환을 통한 운영 효율성 제고</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            {/* 기대 효과 */}
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl shadow-lg p-6 border border-green-200">
              <h3 className="text-xl font-bold text-green-800 mb-6 flex items-center gap-2">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                4. 기대 효과
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-xl p-5 text-center">
                  <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                  </div>
                  <div className="text-2xl font-bold text-green-600 mb-1">
                    {Math.max(5, Math.round((default_prediction.default_probability * 100) * 0.4))}%p ↓
                  </div>
                  <div className="text-sm text-gray-600">예상 부도확률 감소</div>
                  <div className="text-xs text-gray-400 mt-1">권고안 이행 시</div>
                </div>

                <div className="bg-white rounded-xl p-5 text-center">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="text-2xl font-bold text-blue-600 mb-1">신용등급 개선</div>
                  <div className="text-sm text-gray-600">금융비용 절감 효과</div>
                  <div className="text-xs text-gray-400 mt-1">조달금리 0.5~1% 인하 기대</div>
                </div>

                <div className="bg-white rounded-xl p-5 text-center">
                  <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                  <div className="text-2xl font-bold text-purple-600 mb-1">거래처 신뢰↑</div>
                  <div className="text-sm text-gray-600">공급망 안정성 확보</div>
                  <div className="text-xs text-gray-400 mt-1">협력사 네트워크 강화</div>
                </div>
              </div>
            </div>

            {/* What-if 시뮬레이터 */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-2 flex items-center gap-2">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                5. What-if 시뮬레이터
              </h3>
              <p className="text-gray-500 text-sm mb-6">
                부채비율을 조정하여 예상 부도 확률 변화를 미리 확인해보세요.
                실제 재무 구조 개선 시 기대할 수 있는 효과를 시뮬레이션합니다.
              </p>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="space-y-6">
                  {/* 부채비율 슬라이더 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      부채비율 조정 (%)
                    </label>
                    <input
                      type="range"
                      min="50"
                      max="500"
                      value={simDebtRatio}
                      onChange={(e) => setSimDebtRatio(Number(e.target.value))}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                    <div className="flex justify-between text-sm text-gray-500 mt-1">
                      <span>50% (우량)</span>
                      <span className="font-semibold text-blue-600">{simDebtRatio}%</span>
                      <span>500% (고위험)</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="text-sm text-gray-600 mb-2">현재 부채비율</div>
                      <div className="text-2xl font-bold text-gray-800">
                        {(result.derived_ratios?.R006 || 200).toFixed(0)}%
                      </div>
                    </div>
                    <div className="bg-blue-50 rounded-lg p-4">
                      <div className="text-sm text-gray-600 mb-2">시뮬레이션 값</div>
                      <div className="text-2xl font-bold text-blue-600">
                        {simDebtRatio}%
                      </div>
                    </div>
                  </div>

                  {simDebtRatio < (result.derived_ratios?.R006 || 200) && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <div className="flex items-start gap-2">
                        <svg className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div className="text-sm text-green-800">
                          <strong>개선 방향:</strong> 부채비율을 {((result.derived_ratios?.R006 || 200) - simDebtRatio).toFixed(0)}%p 낮추면
                          재무 건전성이 개선됩니다.
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6">
                  <div className="text-center">
                    <div className="text-sm text-gray-600 mb-2">예상 부도 확률</div>
                    <div className="text-5xl font-bold mb-2">
                      <span className={getRiskColor(getSimRiskLevel(simPrediction || default_prediction.default_probability))}>
                        {((simPrediction || default_prediction.default_probability) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className={`inline-block px-4 py-1 rounded-full text-sm font-medium ${
                      getSimRiskLevel(simPrediction || 0) === 'Low' ? 'bg-green-100 text-green-700' :
                      getSimRiskLevel(simPrediction || 0) === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {getRiskLabel(getSimRiskLevel(simPrediction || default_prediction.default_probability))} 등급
                    </div>

                    {simPrediction && simPrediction !== default_prediction.default_probability && (
                      <div className="mt-4 text-sm">
                        <span className={simPrediction < default_prediction.default_probability ? 'text-green-600' : 'text-red-600'}>
                          {simPrediction < default_prediction.default_probability ? '▼' : '▲'}
                          {' '}{Math.abs((simPrediction - default_prediction.default_probability) * 100).toFixed(1)}%p
                          {simPrediction < default_prediction.default_probability ? ' 감소 예상' : ' 증가 예상'}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* LLM 상세 리포트 (있는 경우) */}
            {diagnosis?.report_text && (
              <div className="bg-white rounded-2xl shadow-lg p-6">
                <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                  <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  6. AI 상세 분석 리포트
                </h3>
                <div className="bg-gradient-to-br from-slate-50 to-gray-100 rounded-xl p-6 border border-gray-200">
                  <div className="prose prose-slate max-w-none
                    prose-headings:text-gray-800 prose-headings:font-bold prose-headings:border-b prose-headings:border-gray-200 prose-headings:pb-2 prose-headings:mb-4
                    prose-h2:text-xl prose-h2:mt-6 prose-h2:text-blue-800
                    prose-h3:text-lg prose-h3:mt-4 prose-h3:text-gray-700
                    prose-p:text-gray-600 prose-p:leading-relaxed prose-p:my-3
                    prose-strong:text-gray-800 prose-strong:font-semibold
                    prose-ul:my-3 prose-ul:list-disc prose-ul:pl-5
                    prose-ol:my-3 prose-ol:list-decimal prose-ol:pl-5
                    prose-li:text-gray-600 prose-li:my-1
                    prose-blockquote:border-l-4 prose-blockquote:border-blue-500 prose-blockquote:bg-blue-50 prose-blockquote:px-4 prose-blockquote:py-2 prose-blockquote:italic prose-blockquote:text-blue-800
                  ">
                    <ReactMarkdown>{diagnosis.report_text}</ReactMarkdown>
                  </div>
                </div>
                {diagnosis.risk_interpretation && (
                  <div className="mt-4 p-4 bg-amber-50 border-l-4 border-amber-500 rounded-r-lg">
                    <div className="flex items-start gap-3">
                      <svg className="w-6 h-6 text-amber-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                      <div>
                        <h4 className="font-semibold text-amber-800 mb-1">AI 핵심 인사이트</h4>
                        <p className="text-amber-700 text-sm leading-relaxed">{diagnosis.risk_interpretation}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: 협력사 추천 */}
        {activeTab === 'partners' && (
          <div className="space-y-6">
            {/* 공급망 리스크 요약 */}
            <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6">
              <h3 className="text-lg font-bold text-blue-800 mb-4 flex items-center gap-2">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                협력사 추천 기준
              </h3>
              <p className="text-blue-700">
                <span className="font-bold">{clustering.cluster_name}</span> 클러스터 내에서
                귀사와 <span className="font-bold">유사도가 높고</span> 재무 건전성이 우수한 기업을 추천합니다.
                기업 ID는 데이터 적재 시 부여된 고유 식별자입니다.
              </p>
            </div>

            {/* 협력사 추천 */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-xl font-bold text-gray-800">추천 협력사</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {clustering.cluster_name} 클러스터 내 우량 기업
                  </p>
                </div>
                <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                  {partners.length}개 기업
                </span>
              </div>

              {(!partners || partners.length === 0) ? (
                <div className="text-center py-12 bg-gray-50 rounded-xl">
                  <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <h4 className="text-lg font-semibold text-gray-600 mb-2">협력사 데이터를 불러올 수 없습니다</h4>
                  <p className="text-gray-500 text-sm max-w-md mx-auto">
                    클러스터링 데이터가 로드되지 않았거나, 해당 클러스터 내 추천 가능한 기업이 없습니다.
                    시스템 관리자에게 문의하거나 나중에 다시 시도해주세요.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200">
                        <th className="text-left py-4 px-4 text-sm font-semibold text-gray-600">순위</th>
                        <th className="text-left py-4 px-4 text-sm font-semibold text-gray-600">기업명</th>
                        <th className="text-left py-4 px-4 text-sm font-semibold text-gray-600">업종</th>
                        <th className="text-center py-4 px-4 text-sm font-semibold text-gray-600">유사도</th>
                        <th className="text-center py-4 px-4 text-sm font-semibold text-gray-600">부도확률</th>
                        <th className="text-center py-4 px-4 text-sm font-semibold text-gray-600">위험등급</th>
                        <th className="text-left py-4 px-4 text-sm font-semibold text-gray-600">핵심 강점</th>
                      </tr>
                    </thead>
                    <tbody>
                      {partners.slice(0, 10).map((partner, idx) => (
                        <tr
                          key={idx}
                          className="border-b border-gray-100 hover:bg-blue-50/50 transition-colors cursor-pointer"
                        >
                          <td className="py-4 px-4">
                            <span className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold ${
                              idx === 0 ? 'bg-yellow-100 text-yellow-700' :
                              idx === 1 ? 'bg-gray-200 text-gray-600' :
                              idx === 2 ? 'bg-orange-100 text-orange-700' :
                              'bg-gray-100 text-gray-500'
                            }`}>
                              {idx + 1}
                            </span>
                          </td>
                          <td className="py-4 px-4">
                            <div>
                              <div className="font-semibold text-gray-800">{partner.company_name}</div>
                              <div className="text-xs text-gray-400 font-mono">{partner.company_id?.slice(-8)}</div>
                            </div>
                          </td>
                          <td className="py-4 px-4 text-sm text-gray-600">{partner.industry}</td>
                          <td className="py-4 px-4 text-center">
                            <div className="flex items-center justify-center gap-2">
                              <div className="w-16 bg-gray-200 rounded-full h-2">
                                <div
                                  className="bg-blue-500 h-2 rounded-full"
                                  style={{ width: `${partner.similarity_score * 100}%` }}
                                />
                              </div>
                              <span className="text-sm font-medium text-gray-700">
                                {(partner.similarity_score * 100).toFixed(0)}%
                              </span>
                            </div>
                          </td>
                          <td className="py-4 px-4 text-center">
                            <span className="text-sm font-medium text-gray-700">
                              {(partner.default_probability * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td className="py-4 px-4 text-center">
                            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                              partner.risk_level === 'Low' ? 'bg-green-100 text-green-700' :
                              partner.risk_level === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-red-100 text-red-700'
                            }`}>
                              {getRiskLabel(partner.risk_level)}
                            </span>
                          </td>
                          <td className="py-4 px-4">
                            <div className="flex flex-wrap gap-1">
                              {partner.key_strengths.slice(0, 2).map((strength, sIdx) => (
                                <span
                                  key={sIdx}
                                  className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs"
                                >
                                  {strength}
                                </span>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {partners.length > 10 && (
                    <div className="text-center mt-6 pt-4 border-t border-gray-100">
                      <button className="px-6 py-2 text-blue-600 font-medium hover:text-blue-700 transition-colors">
                        더 많은 협력사 보기 ({partners.length - 10}개 더) →
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
