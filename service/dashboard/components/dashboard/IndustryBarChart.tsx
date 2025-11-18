'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { IndustryDefaultRate } from '@/lib/types';

interface IndustryBarChartProps {
  data: IndustryDefaultRate[];
}

const COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
  '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788',
];

export default function IndustryBarChart({ data }: IndustryBarChartProps) {
  // Sort by default rate descending
  const sortedData = [...data].sort((a, b) => b.default_rate - a.default_rate);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        대분류 업종별 부도율
      </h3>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={sortedData} layout="horizontal">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="industry_code"
            tick={{ fontSize: 11 }}
          />
          <YAxis
            label={{ value: '부도율 (%)', angle: -90, position: 'insideLeft' }}
            tick={{ fontSize: 11 }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload as IndustryDefaultRate;
                return (
                  <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
                    <p className="font-semibold text-sm">{data.industry_name}</p>
                    <p className="text-sm text-gray-600">
                      부도율: <span className="font-medium">{data.default_rate.toFixed(2)}%</span>
                    </p>
                    <p className="text-xs text-gray-500">
                      총 기업 수: {data.total_companies.toLocaleString()}
                    </p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar dataKey="default_rate" radius={[4, 4, 0, 0]}>
            {sortedData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
