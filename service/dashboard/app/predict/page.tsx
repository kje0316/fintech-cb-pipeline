'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import type { UserFriendlyPredictionRequest } from '@/lib/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function PredictPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 폼 상태 (19개 입력)
  const [formData, setFormData] = useState<UserFriendlyPredictionRequest>({
    // 재무상태표 (7개)
    fn1_13: 0,
    fn1_1: 0,
    fn1_4: 0,
    fn1_19: 0,
    fn1_24: 0,
    fn1_14: 0,
    fn1_15: 0,
    // 손익계산서 (6개)
    fn2_1: 0,
    fn2_5: 0,
    fn2_5_1: 0,
    fn2_10: 0,
    fn2_10_1: 0,
    fn2_3: 0,
    // 현금흐름 (1개)
    fn3_2: 0,
    // 기업정보 (2개)
    empe_cnt: 0,
    wg_gb: 'N',
    // 간소화 연체 (3개)
    has_delinquency: false,
    delinquency_days: 0,
    has_tax_delinquency: false,
  });

  const handleInputChange = (field: keyof UserFriendlyPredictionRequest, value: string | number | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleLoadSample = () => {
    setFormData({
      fn1_13: 150000,
      fn1_1: 50000,
      fn1_4: 20000,
      fn1_19: 80000,
      fn1_24: 70000,
      fn1_14: 30000,
      fn1_15: 10000,
      fn2_1: 200000,
      fn2_5: 15000,
      fn2_5_1: 12000,
      fn2_10: 10000,
      fn2_10_1: 8000,
      fn2_3: 25000,
      fn3_2: 12000,
      empe_cnt: 50,
      wg_gb: 'Y',
      has_delinquency: false,
      delinquency_days: 0,
      has_tax_delinquency: false,
    });
  };

  const handleNoDelinquency = () => {
    setFormData(prev => ({
      ...prev,
      has_delinquency: false,
      delinquency_days: 0,
      has_tax_delinquency: false,
    }));
  };

  const handleReset = () => {
    setFormData({
      fn1_13: 0, fn1_1: 0, fn1_4: 0, fn1_19: 0, fn1_24: 0, fn1_14: 0, fn1_15: 0,
      fn2_1: 0, fn2_5: 0, fn2_5_1: 0, fn2_10: 0, fn2_10_1: 0, fn2_3: 0,
      fn3_2: 0,
      empe_cnt: 0, wg_gb: 'N',
      has_delinquency: false, delinquency_days: 0, has_tax_delinquency: false,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // 필수 값 검증
    if (formData.fn1_13 <= 0 || formData.fn1_24 <= 0) {
      setError('자산총계와 자본총계는 필수 입력 항목입니다.');
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/predict/user-friendly`, formData);

      if (response.data.success) {
        localStorage.setItem('predictionResult', JSON.stringify(response.data));
        router.push('/predict/result');
      } else {
        setError(response.data.message || '예측에 실패했습니다.');
      }
    } catch (err: any) {
      console.error('Prediction error:', err);
      setError(
        err.response?.data?.detail ||
        err.message ||
        '서버와의 통신 중 오류가 발생했습니다.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.push('/')}
            className="text-blue-600 hover:text-blue-800 flex items-center gap-2 mb-4"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            대시보드로 돌아가기
          </button>
          <h1 className="text-3xl font-bold text-gray-900">기업 리포트 - 부도 위험도 분석</h1>
          <p className="mt-2 text-gray-600">
            재무제표 정보를 입력하여 기업의 부도 확률을 예측합니다 (총 19개 항목)
          </p>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="text-blue-900 font-semibold text-sm">입력 항목</div>
            <div className="text-2xl font-bold text-blue-700">19개</div>
            <div className="text-xs text-blue-600 mt-1">재무 16개 + 간소화 연체 3개</div>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="text-green-900 font-semibold text-sm">모델 성능</div>
            <div className="text-2xl font-bold text-green-700">96.4%</div>
            <div className="text-xs text-green-600 mt-1">전체 모델 성능 유지율</div>
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <div className="text-purple-900 font-semibold text-sm">AUC-ROC</div>
            <div className="text-2xl font-bold text-purple-700">77.3%</div>
            <div className="text-xs text-purple-600 mt-1">신뢰할 수 있는 예측 성능</div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-lg p-6 mb-6">
          {/* 재무상태표 섹션 */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b flex items-center gap-2">
              <span className="text-2xl">💰</span> 재무상태표 (7개)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  자산총계 (천원) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={formData.fn1_13 || ''}
                  onChange={(e) => handleInputChange('fn1_13', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="150000"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  유동자산 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn1_1 || ''}
                  onChange={(e) => handleInputChange('fn1_1', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="50000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  재고자산 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn1_4 || ''}
                  onChange={(e) => handleInputChange('fn1_4', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="20000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  부채총계 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn1_19 || ''}
                  onChange={(e) => handleInputChange('fn1_19', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="80000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  자본총계 (천원) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={formData.fn1_24 || ''}
                  onChange={(e) => handleInputChange('fn1_24', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="70000"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  유동부채 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn1_14 || ''}
                  onChange={(e) => handleInputChange('fn1_14', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="30000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  단기차입금 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn1_15 || ''}
                  onChange={(e) => handleInputChange('fn1_15', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="10000"
                />
              </div>
            </div>

            {/* 자동 계산 비율 표시 */}
            {formData.fn1_1 > 0 && formData.fn1_14 > 0 && (
              <div className="mt-4 p-3 bg-blue-50 rounded-md">
                <div className="text-xs font-medium text-blue-900 mb-1">자동 계산 비율</div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-blue-700">
                  <div>유동비율: {(((formData.fn1_1 || 0) / (formData.fn1_14 || 1)) * 100).toFixed(1)}%</div>
                  {formData.fn1_19 > 0 && formData.fn1_24 > 0 && (
                    <div>부채비율: {(((formData.fn1_19 || 0) / (formData.fn1_24 || 1)) * 100).toFixed(1)}%</div>
                  )}
                  {formData.fn1_24 > 0 && formData.fn1_13 > 0 && (
                    <div>자기자본비율: {(((formData.fn1_24 || 0) / (formData.fn1_13 || 1)) * 100).toFixed(1)}%</div>
                  )}
                  {formData.fn1_4 > 0 && formData.fn1_1 > 0 && (
                    <div>재고비율: {(((formData.fn1_4 || 0) / (formData.fn1_1 || 1)) * 100).toFixed(1)}%</div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* 손익계산서 섹션 */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b flex items-center gap-2">
              <span className="text-2xl">📊</span> 손익계산서 (6개)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  매출액 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn2_1 || ''}
                  onChange={(e) => handleInputChange('fn2_1', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="200000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  영업이익 - 당기 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn2_5 || ''}
                  onChange={(e) => handleInputChange('fn2_5', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="15000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  영업이익 - 전기 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn2_5_1 || ''}
                  onChange={(e) => handleInputChange('fn2_5_1', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="12000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  당기순이익 - 당기 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn2_10 || ''}
                  onChange={(e) => handleInputChange('fn2_10', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="10000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  당기순이익 - 전기 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn2_10_1 || ''}
                  onChange={(e) => handleInputChange('fn2_10_1', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="8000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  판매비와관리비 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn2_3 || ''}
                  onChange={(e) => handleInputChange('fn2_3', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="25000"
                />
              </div>
            </div>

            {/* 자동 계산 수익성 지표 */}
            {formData.fn2_1 > 0 && formData.fn2_5 !== 0 && (
              <div className="mt-4 p-3 bg-green-50 rounded-md">
                <div className="text-xs font-medium text-green-900 mb-1">수익성 지표</div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-green-700">
                  <div>영업이익률: {(((formData.fn2_5 || 0) / (formData.fn2_1 || 1)) * 100).toFixed(1)}%</div>
                  {formData.fn2_10 !== 0 && (
                    <div>순이익률: {(((formData.fn2_10 || 0) / (formData.fn2_1 || 1)) * 100).toFixed(1)}%</div>
                  )}
                  {formData.fn2_5_1 !== 0 && (
                    <div>영업이익 성장률: {((((formData.fn2_5 || 0) - (formData.fn2_5_1 || 0)) / (Math.abs(formData.fn2_5_1) || 1)) * 100).toFixed(1)}%</div>
                  )}
                  {formData.fn2_10_1 !== 0 && (
                    <div>순이익 성장률: {((((formData.fn2_10 || 0) - (formData.fn2_10_1 || 0)) / (Math.abs(formData.fn2_10_1) || 1)) * 100).toFixed(1)}%</div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* 현금흐름 & 기업정보 섹션 */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b flex items-center gap-2">
              <span className="text-2xl">💵</span> 현금흐름 & 기업정보 (3개)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  영업활동현금흐름 (천원)
                </label>
                <input
                  type="number"
                  value={formData.fn3_2 || ''}
                  onChange={(e) => handleInputChange('fn3_2', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="12000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  종업원수 (명)
                </label>
                <input
                  type="number"
                  value={formData.empe_cnt || ''}
                  onChange={(e) => handleInputChange('empe_cnt', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  외부감사 대상 여부
                </label>
                <select
                  value={formData.wg_gb}
                  onChange={(e) => handleInputChange('wg_gb', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="Y">예 (Y)</option>
                  <option value="N">아니오 (N)</option>
                </select>
              </div>
            </div>
          </div>

          {/* 연체 & 신용 정보 섹션 */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4 pb-2 border-b">
              <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <span className="text-2xl">⚠️</span> 간소화 연체 & 신용 정보 (3개)
              </h2>
              <button
                type="button"
                onClick={handleNoDelinquency}
                className="px-3 py-1 bg-green-100 text-green-700 text-sm rounded-md hover:bg-green-200 transition-colors"
              >
                ✅ 연체 없음으로 자동 채우기
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  현재 연체 여부
                </label>
                <select
                  value={formData.has_delinquency ? 'true' : 'false'}
                  onChange={(e) => handleInputChange('has_delinquency', e.target.value === 'true')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="false">없음</option>
                  <option value="true">있음</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  최장 연체일수 (일)
                </label>
                <input
                  type="number"
                  value={formData.delinquency_days || ''}
                  onChange={(e) => handleInputChange('delinquency_days', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  세금 체납 여부
                </label>
                <select
                  value={formData.has_tax_delinquency ? 'true' : 'false'}
                  onChange={(e) => handleInputChange('has_tax_delinquency', e.target.value === 'true')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="false">없음</option>
                  <option value="true">있음</option>
                </select>
              </div>
            </div>
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="mb-6 rounded-md bg-red-50 border border-red-200 p-4">
              <div className="flex">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">{error}</h3>
                </div>
              </div>
            </div>
          )}

          {/* 버튼 그룹 */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleLoadSample}
              className="flex-1 py-3 px-4 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50 transition-colors"
            >
              📝 샘플 데이터 로드
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="flex-1 py-3 px-4 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50 transition-colors"
            >
              🔄 초기화
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-3 px-4 border border-transparent rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  예측 중...
                </div>
              ) : (
                '🎯 부도 확률 예측하기'
              )}
            </button>
          </div>
        </form>

        {/* 모델 정보 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">사용자 친화 모델 정보</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">모델 사양</h4>
              <ul className="text-gray-600 space-y-1">
                <li>• 알고리즘: RandomForestClassifier</li>
                <li>• 입력 피처: 19개 (재무 16개 + 연체 3개)</li>
                <li>• 자동 생성 피처: 15개 (재무 비율)</li>
                <li>• 총 사용 피처: 34개</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">성능 지표</h4>
              <ul className="text-gray-600 space-y-1">
                <li>• AUC-ROC: 77.34%</li>
                <li>• 정확도: 96.92%</li>
                <li>• 정밀도: 21.32%</li>
                <li>• 재현율: 38.16%</li>
              </ul>
            </div>
          </div>
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
            <p className="text-xs text-yellow-800">
              <strong>참고:</strong> 이 모델은 재무제표 중심으로 설계되어 사용자가 쉽게 입력할 수 있으며,
              연체 정보는 3개 간단한 질문으로 간소화되었습니다.
              자동으로 15개의 재무 비율을 계산하여 총 34개 피처로 예측합니다.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
