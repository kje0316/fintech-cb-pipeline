'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Line, ComposedChart } from 'recharts';
import type { CreditDistribution } from '@/lib/types';

interface CreditGradeDistributionProps {
  data: CreditDistribution[];
}

export default function CreditGradeDistribution({ data }: CreditGradeDistributionProps) {
  // 색상 그라데이션: 초록 → 노랑 → 주황 → 빨강
  const getBarColor = (grade: number) => {
    if (grade <= 3) return '#10b981'; // 초록 (excellent)
    if (grade <= 5) return '#84cc16'; // 연두 (good)
    if (grade <= 7) return '#f59e0b'; // 주황 (fair)
    return '#ef4444'; // 빨강 (poor)
  };

  // 막대 차트용 데이터 변환
  const chartData = data.map(item => ({
    grade: `${item.credit_grade}등급`,
    기업수: item.company_count,
    부도율: item.default_rate,
    color: getBarColor(item.credit_grade),
  }));

  return (
    <div className="bg-white rounded-lg shadow-md p-6 h-full flex flex-col">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        신용등급별 기업 분포 및 부도율
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        등급이 낮을수록 부도율이 급증합니다 (1-3등급: 0.14% → 8-10등급: 8.35%)
      </p>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="grade"
              tick={{ fontSize: 12 }}
            />
            <YAxis
              yAxisId="left"
              label={{ value: '기업 수', angle: -90, position: 'insideLeft' }}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              label={{ value: '부도율 (%)', angle: 90, position: 'insideRight' }}
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === '기업수') return [value.toLocaleString(), name];
                return [`${value.toFixed(2)}%`, name];
              }}
            />
            <Legend />
            <Bar
              yAxisId="left"
              dataKey="기업수"
              fill="#8884d8"
              shape={(props: any) => {
                const { x, y, width, height, payload } = props;
                return (
                  <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    fill={payload.color}
                  />
                );
              }}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="부도율"
              stroke="#dc2626"
              strokeWidth={2}
              dot={{ r: 4 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
