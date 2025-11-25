'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { predictQuick } from '@/lib/api';
import type { LightweightPredictionRequest } from '@/lib/types';

export default function QuickPredictPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 폼 상태 (13개 필드)
  const [formData, setFormData] = useState<LightweightPredictionRequest>({
    // 연체 정보
    da0d00029: 0,
    da0d00029_1: 0,
    da0d00026_1: 0,
    da0d00035_2: 0,
    da0d00035_3_2: 0,
    da0d00035_4_1: 0,
    da0d00035_4_2: 0,
    // 신용사건
    d2b000002: 0,
    d2b000003: 0,
    // 재무 정보
    fn1_1: 0,
    fn1_4: 0,
    fn3_11_1: 0,
    // 재무 비율
    r007: 0,
  });

  const handleInputChange = (field: keyof LightweightPredictionRequest, value: string) => {
    const numValue = parseFloat(value) || 0;
    setFormData(prev => ({ ...prev, [field]: numValue }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await predictQuick(formData);

      if (result.success) {
        // 결과를 localStorage에 저장
        localStorage.setItem('predictionResult', JSON.stringify(result));
        router.push('/predict/result');
      } else {
        setError(result.message || '예측에 실패했습니다.');
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

  const handleLoadSample = () => {
    setFormData({
      da0d00029: 0,
      da0d00029_1: 0,
      da0d00026_1: 0,
      da0d00035_2: 0,
      da0d00035_3_2: 0,
      da0d00035_4_1: 0,
      da0d00035_4_2: 0,
      d2b000002: 764,
      d2b000003: 1046,
      fn1_1: 12017,
      fn1_4: 30979,
      fn3_11_1: 22020,
      r007: 26884,
    });
  };

  const handleReset = () => {
    setFormData({
      da0d00029: 0,
      da0d00029_1: 0,
      da0d00026_1: 0,
      da0d00035_2: 0,
      da0d00035_3_2: 0,
      da0d00035_4_1: 0,
      da0d00035_4_2: 0,
      d2b000002: 0,
      d2b000003: 0,
      fn1_1: 0,
      fn1_4: 0,
      fn3_11_1: 0,
      r007: 0,
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.push('/predict')}
            className="text-blue-600 hover:text-blue-800 flex items-center gap-2 mb-4"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            일반 예측으로 돌아가기
          </button>
          <h1 className="text-3xl font-bold text-gray-900">빠른 부도 예측 (경량 모델)</h1>
          <p className="mt-2 text-gray-600">
            13개 입력 컬럼만으로 빠르게 부도 확률을 예측합니다
          </p>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="text-blue-900 font-semibold text-sm">입력 컬럼</div>
            <div className="text-2xl font-bold text-blue-700">13개</div>
            <div className="text-xs text-blue-600 mt-1">전체 모델 대비 85% 감소</div>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="text-green-900 font-semibold text-sm">모델 성능</div>
            <div className="text-2xl font-bold text-green-700">91.7%</div>
            <div className="text-xs text-green-600 mt-1">전체 모델 성능 유지율</div>
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <div className="text-purple-900 font-semibold text-sm">AUC-ROC</div>
            <div className="text-2xl font-bold text-purple-700">73.6%</div>
            <div className="text-xs text-purple-600 mt-1">신뢰할 수 있는 성능</div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-lg p-6 mb-6">
          {/* 연체 정보 섹션 */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b">
              📋 연체 정보 (7개)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  연체과목수 (1년내발생)
                </label>
                <input
                  type="number"
                  value={formData.da0d00029}
                  onChange={(e) => handleInputChange('da0d00029', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  연체과목수 (1년내발생)_1
                </label>
                <input
                  type="number"
                  value={formData.da0d00029_1}
                  onChange={(e) => handleInputChange('da0d00029_1', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  연체과목수 (1년내유지)_1
                </label>
                <input
                  type="number"
                  value={formData.da0d00026_1}
                  onChange={(e) => handleInputChange('da0d00026_1', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  최장연체일수 (1년)_2
                </label>
                <input
                  type="number"
                  value={formData.da0d00035_2}
                  onChange={(e) => handleInputChange('da0d00035_2', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  최장연체일수 (1년)_3_2
                </label>
                <input
                  type="number"
                  value={formData.da0d00035_3_2}
                  onChange={(e) => handleInputChange('da0d00035_3_2', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  최장연체일수 (1년)_4_1
                </label>
                <input
                  type="number"
                  value={formData.da0d00035_4_1}
                  onChange={(e) => handleInputChange('da0d00035_4_1', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  최장연체일수 (1년)_4_2
                </label>
                <input
                  type="number"
                  value={formData.da0d00035_4_2}
                  onChange={(e) => handleInputChange('da0d00035_4_2', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
              </div>
            </div>
          </div>

          {/* 신용사건 섹션 */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b">
              ⚠️ 신용사건 정보 (2개)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  공공신용정보 (유형2)
                </label>
                <input
                  type="number"
                  value={formData.d2b000002}
                  onChange={(e) => handleInputChange('d2b000002', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  공공신용정보 (유형3)
                </label>
                <input
                  type="number"
                  value={formData.d2b000003}
                  onChange={(e) => handleInputChange('d2b000003', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
              </div>
            </div>
          </div>

          {/* 재무 정보 섹션 */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b">
              💰 재무 정보 (3개)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  유동자산 (fn1_1) - 천원
                </label>
                <input
                  type="number"
                  value={formData.fn1_1}
                  onChange={(e) => handleInputChange('fn1_1', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
                <p className="text-xs text-gray-500 mt-1">재고자산/유동자산 계산에 사용</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  재고자산 (fn1_4) - 천원
                </label>
                <input
                  type="number"
                  value={formData.fn1_4}
                  onChange={(e) => handleInputChange('fn1_4', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
                <p className="text-xs text-gray-500 mt-1">재고자산/유동자산 계산에 사용</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  순차입금_1 (fn3_11_1) - 천원
                </label>
                <input
                  type="number"
                  value={formData.fn3_11_1}
                  onChange={(e) => handleInputChange('fn3_11_1', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
              </div>
            </div>
          </div>

          {/* 재무 비율 섹션 */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4 pb-2 border-b">
              📊 재무 비율 (1개)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  자기자본비율 (r007) - %
                </label>
                <input
                  type="number"
                  value={formData.r007}
                  onChange={(e) => handleInputChange('r007', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  step="any"
                />
              </div>
            </div>
          </div>

          {/* 파생 변수 안내 */}
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-md p-4">
            <h3 className="text-sm font-semibold text-blue-900 mb-2">자동 계산 피처</h3>
            <p className="text-sm text-blue-800">
              • <strong>inventory_to_current_asset</strong> = fn1_4 / fn1_1 (재고자산/유동자산)
            </p>
            <p className="text-xs text-blue-600 mt-2">
              위 피처는 입력값을 기반으로 자동으로 계산됩니다.
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 rounded-md bg-red-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">{error}</h3>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  예측 중...
                </span>
              ) : (
                '부도 확률 예측'
              )}
            </button>
            <button
              type="button"
              onClick={handleLoadSample}
              className="py-3 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              샘플 데이터
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="py-3 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              초기화
            </button>
          </div>
        </form>

        {/* 모델 정보 */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">경량 모델 정보</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h3 className="font-semibold text-gray-700 mb-2">모델 사양</h3>
              <ul className="space-y-1 text-gray-600">
                <li>• 알고리즘: Random Forest</li>
                <li>• 학습 피처: 12개</li>
                <li>• 입력 컬럼: 13개 (1개 자동 계산)</li>
                <li>• 학습 데이터: 50,000건</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-gray-700 mb-2">성능 지표</h3>
              <ul className="space-y-1 text-gray-600">
                <li>• AUC-ROC: 73.56%</li>
                <li>• Accuracy: 96.11%</li>
                <li>• Precision: 17.53%</li>
                <li>• Recall: 42.11%</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
