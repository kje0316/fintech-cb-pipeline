'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { IndustryComposition } from '@/lib/types';

interface IndustryPieChartProps {
  data: IndustryComposition[];
}

const COLORS = [
  '#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8',
  '#82CA9D', '#FFC658', '#FF7C7C', '#A28FD0', '#F87171',
  '#34D399', '#FBBF24', '#60A5FA', '#A78BFA', '#F472B6',
  '#FB923C', '#4ADE80', '#2DD4BF', '#C084FC', '#E879F9'
];

export default function IndustryPieChart({ data }: IndustryPieChartProps) {
  // Take top 10 industries by company count
  const topIndustries = [...data]
    .sort((a, b) => b.company_count - a.company_count)
    .slice(0, 10);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        업종별 구성비 (상위 10개)
      </h3>
      <div className="flex flex-col h-[350px]">
        <div className="flex-1">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={topIndustries}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ industry_code, percentage }) =>
                  `${industry_code}: ${percentage.toFixed(1)}%`
                }
                outerRadius={80}
                fill="#8884d8"
                dataKey="company_count"
              >
                {topIndustries.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number, name: string, props: any) => [
                  `${props.payload.company_count.toLocaleString()} 기업 (${props.payload.percentage.toFixed(1)}%)`,
                  props.payload.industry_name
                ]}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 max-h-24 overflow-y-auto text-xs">
          <div className="grid grid-cols-1 gap-1">
            {topIndustries.map((item, index) => (
              <div key={item.industry_code} className="flex items-center">
                <span
                  className="w-2 h-2 rounded-full mr-1 flex-shrink-0"
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                ></span>
                <span className="font-medium">{item.industry_code}:</span>
                <span className="ml-1 text-gray-600 truncate">{item.industry_name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
