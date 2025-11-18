'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { IndustryTrendData } from '@/lib/types';

interface DefaultTrendChartProps {
  data: IndustryTrendData[];
}

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#a28fd0'];

export default function DefaultTrendChart({ data }: DefaultTrendChartProps) {
  // Group data by month and pivot by industry
  const groupedData = data.reduce((acc: any, item) => {
    const month = item.bs_dt.substring(0, 7); // YYYY-MM format

    if (!acc[month]) {
      acc[month] = { month };
    }

    acc[month][item.industry_code] = item.default_rate;

    return acc;
  }, {});

  const chartData = Object.values(groupedData).sort((a: any, b: any) =>
    a.month.localeCompare(b.month)
  );

  // Get unique industries (fix: use Map to properly deduplicate)
  const industryMap = new Map<string, { code: string; name: string }>();
  data.forEach(item => {
    if (!industryMap.has(item.industry_code)) {
      industryMap.set(item.industry_code, {
        code: item.industry_code,
        name: item.industry_name
      });
    }
  });
  const industries = Array.from(industryMap.values());

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        상위 5개 업종 월별 부도율 추세
      </h3>
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12 }}
          />
          <YAxis
            label={{ value: '부도율 (%)', angle: -90, position: 'insideLeft' }}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(value: number) => `${value.toFixed(2)}%`}
          />
          <Legend />
          {industries.map((industry, index) => (
            <Line
              key={industry.code}
              type="monotone"
              dataKey={industry.code}
              name={industry.name}
              stroke={COLORS[index % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
