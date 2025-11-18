import type { KPICardProps } from '@/lib/types';

export default function KPICard({
  title,
  value,
  subtitle,
  trend,
  trendLabel,
  status,
  description
}: KPICardProps) {
  // 상태별 색상 및 배경색 설정
  const getStatusColors = () => {
    switch (status) {
      case 'safe':
        return {
          border: 'border-green-200',
          bg: 'bg-green-50',
          badge: 'bg-green-100 text-green-700',
          text: 'text-green-600',
        };
      case 'moderate':
        return {
          border: 'border-yellow-200',
          bg: 'bg-yellow-50',
          badge: 'bg-yellow-100 text-yellow-700',
          text: 'text-yellow-600',
        };
      case 'high':
        return {
          border: 'border-red-200',
          bg: 'bg-red-50',
          badge: 'bg-red-100 text-red-700',
          text: 'text-red-600',
        };
      case 'improving':
        return {
          border: 'border-blue-200',
          bg: 'bg-blue-50',
          badge: 'bg-blue-100 text-blue-700',
          text: 'text-blue-600',
        };
      case 'worsening':
        return {
          border: 'border-orange-200',
          bg: 'bg-orange-50',
          badge: 'bg-orange-100 text-orange-700',
          text: 'text-orange-600',
        };
      default:
        return {
          border: 'border-gray-200',
          bg: 'bg-white',
          badge: 'bg-gray-100 text-gray-700',
          text: 'text-gray-600',
        };
    }
  };

  const colors = getStatusColors();

  // 트렌드 색상 및 심볼 (기존 로직 유지)
  const getTrendColor = () => {
    if (trend === undefined || trend === 0) return 'text-gray-500';
    return trend > 0 ? 'text-red-500' : 'text-green-500';
  };

  const getTrendSymbol = () => {
    if (trend === undefined || trend === 0) return '—';
    return trend > 0 ? '↑' : '↓';
  };

  const trendColor = getTrendColor();
  const trendSymbol = getTrendSymbol();

  return (
    <div
      className={`rounded-lg shadow-md p-6 hover:shadow-lg transition-all border-2 ${colors.border} ${colors.bg}`}
    >
      <h3 className="text-sm font-medium text-gray-600 mb-2">{title}</h3>

      <div className="flex items-end justify-between mb-3">
        <div>
          <p className="text-3xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
        </div>

        {trend !== undefined && (
          <div className="text-right">
            <div className={`text-sm font-semibold ${trendColor}`}>
              {trendSymbol} {Math.abs(trend).toFixed(2)}{trendLabel || '%'}
            </div>
            {trendLabel && (
              <p className="text-xs text-gray-500 mt-0.5">전월 대비</p>
            )}
          </div>
        )}
      </div>

      {description && (
        <div className={`mt-3 pt-3 border-t ${colors.border}`}>
          <p className={`text-xs ${colors.text} leading-relaxed`}>
            {description}
          </p>
        </div>
      )}
    </div>
  );
}
