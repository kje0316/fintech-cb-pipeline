'use client';

import type { HeatmapData } from '@/lib/types';

interface DefaultHeatmapProps {
  data: HeatmapData[];
}

export default function DefaultHeatmap({ data }: DefaultHeatmapProps) {
  // Get unique months and industries
  const months = [...new Set(data.map(item => item.bs_dt.substring(0, 7)))].sort();

  // Get unique industries by code (fix: use Map to properly deduplicate)
  const industryMap = new Map<string, { code: string; name: string }>();
  data.forEach(item => {
    if (!industryMap.has(item.industry_code)) {
      industryMap.set(item.industry_code, {
        code: item.industry_code,
        name: item.industry_name
      });
    }
  });
  const industries = Array.from(industryMap.values()).sort((a, b) =>
    a.code.localeCompare(b.code)
  );

  // Create a map for quick lookup
  const dataMap = new Map(
    data.map(item => [
      `${item.bs_dt.substring(0, 7)}-${item.industry_code}`,
      item.default_rate
    ])
  );

  // Get max default rate for color scaling
  const maxRate = Math.max(...data.map(item => item.default_rate));

  const getColor = (rate: number | undefined) => {
    if (!rate || rate === 0) return 'bg-gray-50';
    const intensity = Math.min((rate / maxRate) * 100, 100);
    if (intensity < 20) return 'bg-green-100';
    if (intensity < 40) return 'bg-yellow-100';
    if (intensity < 60) return 'bg-orange-200';
    if (intensity < 80) return 'bg-red-200';
    return 'bg-red-400';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 h-[480px] flex flex-col">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        월별 × 업종별 부도율 히트맵
      </h3>
      <div className="overflow-auto flex-1">
        <table className="min-w-full text-xs">
          <thead>
            <tr>
              <th className="border border-gray-300 p-2 bg-gray-50 sticky left-0">업종</th>
              {months.map(month => (
                <th key={month} className="border border-gray-300 p-2 bg-gray-50">
                  {month}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {industries.map(industry => (
              <tr key={industry.code}>
                <td className="border border-gray-300 p-2 font-medium sticky left-0 bg-white">
                  {industry.code}
                </td>
                {months.map(month => {
                  const rate = dataMap.get(`${month}-${industry.code}`);
                  return (
                    <td
                      key={`${month}-${industry.code}`}
                      className={`border border-gray-300 p-2 text-center ${getColor(rate)}`}
                      title={`${industry.name} - ${month}: ${rate?.toFixed(3) || 'N/A'}%`}
                    >
                      {rate ? rate.toFixed(3) : '-'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex items-center gap-2 text-xs text-gray-600">
        <span>부도율:</span>
        <div className="flex items-center gap-1">
          <span className="w-4 h-4 bg-green-100 border border-gray-300"></span>
          <span>낮음</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-4 h-4 bg-yellow-100 border border-gray-300"></span>
          <span>보통</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-4 h-4 bg-red-200 border border-gray-300"></span>
          <span>높음</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-4 h-4 bg-red-400 border border-gray-300"></span>
          <span>매우 높음</span>
        </div>
      </div>
    </div>
  );
}
