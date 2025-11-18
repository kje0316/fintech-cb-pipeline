'use client';

import { useState } from 'react';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { IndustryRiskRadar } from '@/lib/types';

interface IndustryRiskRadarProps {
  data: IndustryRiskRadar[];
}

export default function IndustryRiskRadarChart({ data }: IndustryRiskRadarProps) {
  // 상위 5개 산업 선택 (부도 위험도 기준)
  const topIndustries = [...data]
    .sort((a, b) => b.default_risk_score - a.default_risk_score)
    .slice(0, 5);

  const [selectedIndustries, setSelectedIndustries] = useState<string[]>(
    topIndustries.slice(0, 3).map(i => i.industry_code)
  );

  // 레이더 차트 데이터 변환
  const radarData = [
    { subject: '신용건전성', fullMark: 100 },
    { subject: '부도위험도', fullMark: 100 },
    { subject: '시장점유율', fullMark: 100 },
    { subject: '재무안정성', fullMark: 100 },
    { subject: '종합건전성', fullMark: 100 },
    { subject: '성장잠재력', fullMark: 100 },
  ];

  // 선택된 산업의 점수를 radarData에 추가
  selectedIndustries.forEach(code => {
    const industry = data.find(d => d.industry_code === code);
    if (industry) {
      radarData[0][code] = industry.credit_health_score;
      radarData[1][code] = industry.default_risk_score;
      radarData[2][code] = industry.market_presence_score;
      radarData[3][code] = industry.financial_stability_score;
      radarData[4][code] = industry.overall_health_score;
      radarData[5][code] = industry.growth_potential_score;
    }
  });

  const colors = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#a28fd0'];

  const toggleIndustry = (code: string) => {
    if (selectedIndustries.includes(code)) {
      setSelectedIndustries(selectedIndustries.filter(c => c !== code));
    } else if (selectedIndustries.length < 5) {
      setSelectedIndustries([...selectedIndustries, code]);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 h-full flex flex-col">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        산업별 위험 프로파일 레이더 차트
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        6가지 차원으로 산업별 리스크를 비교합니다 (최대 3개 선택)
      </p>

      {/* Industry Selection */}
      <div className="mb-4 flex flex-wrap gap-2">
        {topIndustries.map((industry, idx) => (
          <button
            key={industry.industry_code}
            onClick={() => toggleIndustry(industry.industry_code)}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              selectedIndustries.includes(industry.industry_code)
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
            disabled={!selectedIndustries.includes(industry.industry_code) && selectedIndustries.length >= 3}
          >
            {industry.industry_code}: {industry.industry_name}
          </button>
        ))}
      </div>

      {selectedIndustries.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          산업을 선택해주세요 (최대 3개)
        </div>
      ) : (
        <div className="flex-1 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12 }} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
              <Tooltip
                formatter={(value: number) => value.toFixed(1)}
              />
              <Legend />
              {selectedIndustries.map((code, idx) => {
                const industry = data.find(d => d.industry_code === code);
                return (
                  <Radar
                    key={code}
                    name={`${code}: ${industry?.industry_name || ''}`}
                    dataKey={code}
                    stroke={colors[idx % colors.length]}
                    fill={colors[idx % colors.length]}
                    fillOpacity={0.3}
                  />
                );
              })}
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-600">
        <p className="font-semibold mb-1">점수 해석:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>모든 점수는 0-100 범위로 정규화 (높을수록 양호)</li>
          <li>신용건전성: 평균 신용등급 기반</li>
          <li>부도위험도: 낮은 부도율일수록 높은 점수</li>
          <li>시장점유율: 해당 산업의 기업 수 기반</li>
        </ul>
      </div>
    </div>
  );
}
