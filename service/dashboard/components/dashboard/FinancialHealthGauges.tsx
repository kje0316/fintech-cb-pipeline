'use client';

import { RadialBarChart, RadialBar, Legend, ResponsiveContainer } from 'recharts';
import type { FinancialBenchmarks } from '@/lib/types';

interface FinancialHealthGaugesProps {
  data: FinancialBenchmarks;
}

export default function FinancialHealthGauges({ data }: FinancialHealthGaugesProps) {
  // 4가지 지표를 0-100 스케일로 정규화
  const normalizeScore = (value: number, metric: 'leverage' | 'liquidity' | 'profitability' | 'efficiency') => {
    switch (metric) {
      case 'leverage': // 낮을수록 좋음 (부채비율)
        if (value <= 50) return 100;
        if (value <= 100) return 100 - (value - 50);
        if (value <= 200) return 50 - (value - 100) / 2;
        return Math.max(0, 25 - (value - 200) / 12);

      case 'liquidity': // 높을수록 좋음 (유동비율)
        if (value >= 200) return 100;
        if (value >= 150) return 80 + (value - 150) / 2.5;
        if (value >= 100) return 60 + (value - 100) * 0.4;
        return Math.max(0, value * 0.6);

      case 'profitability': // 높을수록 좋음 (영업이익률)
        if (value >= 10) return 100;
        if (value >= 5) return 80 + (value - 5) * 4;
        if (value >= 0) return 60 + value * 4;
        if (value >= -5) return 40 + (value + 5) * 4;
        return Math.max(0, 20 + (value + 10) * 2);

      case 'efficiency': // 0-100 범위
        return Math.min(100, Math.max(0, value));

      default:
        return 50;
    }
  };

  const getColor = (score: number) => {
    if (score >= 80) return '#10b981'; // green
    if (score >= 60) return '#84cc16'; // lime
    if (score >= 40) return '#f59e0b'; // orange
    return '#ef4444'; // red
  };

  const getStatus = (score: number) => {
    if (score >= 80) return '우수';
    if (score >= 60) return '양호';
    if (score >= 40) return '보통';
    return '주의';
  };

  const gauges = [
    {
      name: '레버리지',
      subtitle: '부채비율',
      value: data.leverage.median,
      score: normalizeScore(data.leverage.median, 'leverage'),
      unit: '%',
      description: '낮을수록 재무 안정성이 높음',
    },
    {
      name: '유동성',
      subtitle: '유동비율',
      value: data.liquidity.median,
      score: normalizeScore(data.liquidity.median, 'liquidity'),
      unit: '%',
      description: '높을수록 단기 지급능력이 높음',
    },
    {
      name: '수익성',
      subtitle: '영업이익률',
      value: data.profitability.median,
      score: normalizeScore(data.profitability.median, 'profitability'),
      unit: '%',
      description: '높을수록 수익 창출 능력이 높음',
    },
    {
      name: '효율성',
      subtitle: '자산 활용도',
      value: data.efficiency.median,
      score: normalizeScore(data.efficiency.median, 'efficiency'),
      unit: '',
      description: '높을수록 자산 운용 효율이 높음',
    },
  ];

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        시장 재무 건전성 스코어카드
      </h3>
      <p className="text-sm text-gray-600 mb-6">
        전체 산업 평균 기준 4대 재무 지표 (중위값 기준)
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {gauges.map((gauge) => {
          const color = getColor(gauge.score);
          const status = getStatus(gauge.score);

          const chartData = [{
            name: gauge.name,
            value: gauge.score,
            fill: color,
          }];

          return (
            <div key={gauge.name} className="flex flex-col items-center">
              <div className="relative w-full h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadialBarChart
                    innerRadius="60%"
                    outerRadius="90%"
                    data={chartData}
                    startAngle={180}
                    endAngle={0}
                  >
                    <RadialBar
                      background
                      dataKey="value"
                      cornerRadius={10}
                    />
                  </RadialBarChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex flex-col items-center justify-center pt-8">
                  <div className="text-3xl font-bold" style={{ color }}>
                    {gauge.score.toFixed(0)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">{status}</div>
                </div>
              </div>

              <div className="text-center mt-2">
                <div className="font-semibold text-gray-900">{gauge.name}</div>
                <div className="text-xs text-gray-500">{gauge.subtitle}</div>
                <div className="text-sm text-gray-700 mt-1">
                  {gauge.value.toFixed(1)}{gauge.unit}
                </div>
                <div className="text-xs text-gray-400 mt-1">{gauge.description}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 p-4 bg-gray-50 rounded text-xs text-gray-600">
        <p className="font-semibold mb-2">점수 기준:</p>
        <div className="grid grid-cols-4 gap-2">
          <div><span className="inline-block w-3 h-3 bg-green-500 rounded mr-1"></span>80+ 우수</div>
          <div><span className="inline-block w-3 h-3 bg-lime-500 rounded mr-1"></span>60-79 양호</div>
          <div><span className="inline-block w-3 h-3 bg-orange-500 rounded mr-1"></span>40-59 보통</div>
          <div><span className="inline-block w-3 h-3 bg-red-500 rounded mr-1"></span>0-39 주의</div>
        </div>
      </div>
    </div>
  );
}
