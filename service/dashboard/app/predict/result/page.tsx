'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { PredictionResponse, FeatureContribution } from '@/lib/types';

export default function PredictionResultPage() {
  const router = useRouter();
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedResult = localStorage.getItem('predictionResult');
    if (storedResult) {
      setResult(JSON.parse(storedResult));
      setLoading(false);
    } else {
      // 결과가 없으면 입력 페이지로 리다이렉트
      router.push('/predict');
    }
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">결과를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return null;
  }

  const { prediction, company_info, shap_values } = result;
  const riskColor =
    prediction.risk_level === 'High' ? 'text-red-600 bg-red-100' :
    prediction.risk_level === 'Medium' ? 'text-yellow-600 bg-yellow-100' :
    'text-green-600 bg-green-100';

  const probabilityPercentage = (prediction.default_probability * 100).toFixed(2);

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.push('/predict')}
            className="text-blue-600 hover:text-blue-800 flex items-center gap-2 mb-4"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            새로운 예측하기
          </button>
          <h1 className="text-3xl font-bold text-gray-900">부도 예측 결과</h1>
        </div>

        {/* Main Result Card */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Left: Probability Gauge */}
            <div className="flex flex-col items-center justify-center">
              <h2 className="text-lg font-semibold text-gray-700 mb-6">부도 확률</h2>
              <div className="relative w-48 h-48">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="96"
                    cy="96"
                    r="80"
                    stroke="#e5e7eb"
                    strokeWidth="16"
                    fill="none"
                  />
                  <circle
                    cx="96"
                    cy="96"
                    r="80"
                    stroke={
                      prediction.risk_level === 'High' ? '#dc2626' :
                      prediction.risk_level === 'Medium' ? '#d97706' :
                      '#16a34a'
                    }
                    strokeWidth="16"
                    fill="none"
                    strokeDasharray={`${prediction.default_probability * 502.4} 502.4`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-4xl font-bold text-gray-900">
                    {probabilityPercentage}%
                  </span>
                  <span className="text-sm text-gray-500">부도 확률</span>
                </div>
              </div>
              <div className={`mt-6 px-6 py-3 rounded-full ${riskColor} font-semibold text-lg`}>
                위험도: {prediction.risk_level}
              </div>
            </div>

            {/* Right: Company Info */}
            <div>
              <h2 className="text-lg font-semibold text-gray-700 mb-4">기업 정보</h2>
              <div className="space-y-3">
                <div className="flex justify-between border-b pb-2">
                  <span className="text-gray-600">회계연도:</span>
                  <span className="font-medium">{company_info?.bs_dt || 'N/A'}</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-gray-600">업종 코드:</span>
                  <span className="font-medium">{company_info?.sic_cd_3 || 'N/A'}</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-gray-600">임금 구분:</span>
                  <span className="font-medium">{company_info?.wg_gb || 'N/A'}</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-gray-600">종업원 수:</span>
                  <span className="font-medium">{company_info?.empe_cnt || 'N/A'}</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-gray-600">예측 신뢰도:</span>
                  <span className="font-medium">{(prediction.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">예측 결과:</span>
                  <span className={`font-bold ${prediction.default_prediction === 1 ? 'text-red-600' : 'text-green-600'}`}>
                    {prediction.default_prediction === 1 ? '부도 위험' : '정상'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* SHAP Explanation */}
        {shap_values && shap_values.contributions && shap_values.contributions.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              예측 설명 (SHAP Analysis)
            </h2>

            <div className="mb-6 bg-blue-50 border border-blue-200 rounded-md p-4">
              <p className="text-sm text-blue-900">
                <strong>기준값:</strong> {shap_values.base_value?.toFixed(4)} →
                <strong> 예측값:</strong> {shap_values.expected_value?.toFixed(4)}
              </p>
              <p className="text-xs text-blue-700 mt-2">
                각 피처가 부도 확률 예측에 얼마나 기여했는지 보여줍니다.
                빨간색은 부도 위험을 높이는 요인, 파란색은 낮추는 요인입니다.
              </p>
            </div>

            <div className="space-y-3">
              <h3 className="text-lg font-semibold text-gray-700 mb-4">
                주요 기여 피처 (Top 20)
              </h3>
              {shap_values.contributions.slice(0, 20).map((contrib: any, idx: number) => {
                // shap_value (전체 모델) 또는 importance (사용자 친화 모델) 중 하나를 사용
                const shapValue = contrib.shap_value ?? contrib.importance ?? 0;
                const isPositive = shapValue > 0;
                const barWidth = Math.min(Math.abs(contrib.contribution_pct || 0), 100);

                return (
                  <div key={idx} className="border-b pb-3">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">
                        {idx + 1}. {contrib.feature_name}
                      </span>
                      <span className="text-xs text-gray-500">
                        값: {(contrib.feature_value || 0).toFixed(4)}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 bg-gray-200 rounded-full h-6 relative">
                        <div
                          className={`h-6 rounded-full ${isPositive ? 'bg-red-500' : 'bg-blue-500'}`}
                          style={{ width: `${barWidth}%` }}
                        >
                          <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-white">
                            {(contrib.contribution_pct || 0).toFixed(2)}%
                          </span>
                        </div>
                      </div>
                      <span className={`text-sm font-medium ${isPositive ? 'text-red-600' : 'text-blue-600'} w-24 text-right`}>
                        {isPositive ? '+' : ''}{shapValue.toFixed(4)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* SHAP Error Message */}
        {shap_values?.error && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mt-6">
            <p className="text-sm text-yellow-800">
              <strong>SHAP 분석 오류:</strong> {shap_values.error}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
