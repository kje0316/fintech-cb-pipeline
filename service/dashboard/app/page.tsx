'use client';

import { useEffect, useState } from 'react';
import KPICard from '@/components/dashboard/KPICard';
import DefaultTrendChart from '@/components/dashboard/DefaultTrendChart';
import IndustryPieChart from '@/components/dashboard/IndustryPieChart';
import DefaultHeatmap from '@/components/dashboard/DefaultHeatmap';
import IndustryBarChart from '@/components/dashboard/IndustryBarChart';
import CreditGradeDistribution from '@/components/dashboard/CreditGradeDistribution';
import IndustryRiskRadarChart from '@/components/dashboard/IndustryRiskRadar';
import FinancialHealthGauges from '@/components/dashboard/FinancialHealthGauges';
import {
  fetchKPIData,
  fetchTopIndustriesTrend,
  fetchIndustryComposition,
  fetchHeatmapData,
  fetchIndustryDefaultRates,
  fetchCreditDistribution,
  fetchIndustryRiskRadar,
  fetchFinancialBenchmarks,
} from '@/lib/api';
import type {
  KPIData,
  IndustryTrendData,
  IndustryComposition,
  HeatmapData,
  IndustryDefaultRate,
  CreditDistribution,
  IndustryRiskRadar,
  FinancialBenchmarks,
} from '@/lib/types';

export default function Home() {
  const [kpiData, setKpiData] = useState<KPIData | null>(null);
  const [trendData, setTrendData] = useState<IndustryTrendData[]>([]);
  const [compositionData, setCompositionData] = useState<IndustryComposition[]>([]);
  const [heatmapData, setHeatmapData] = useState<HeatmapData[]>([]);
  const [barData, setBarData] = useState<IndustryDefaultRate[]>([]);
  const [creditData, setCreditData] = useState<CreditDistribution[]>([]);
  const [radarData, setRadarData] = useState<IndustryRiskRadar[]>([]);
  const [benchmarkData, setBenchmarkData] = useState<FinancialBenchmarks | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [kpi, trend, composition, heatmap, bar, credit, radar, benchmark] = await Promise.all([
          fetchKPIData(),
          fetchTopIndustriesTrend(),
          fetchIndustryComposition(),
          fetchHeatmapData(),
          fetchIndustryDefaultRates(),
          fetchCreditDistribution(),
          fetchIndustryRiskRadar(),
          fetchFinancialBenchmarks(),
        ]);

        setKpiData(kpi);
        setTrendData(trend);
        setCompositionData(composition);
        setHeatmapData(heatmap);
        setBarData(bar);
        setCreditData(credit);
        setRadarData(radar);
        setBenchmarkData(benchmark);
      } catch (err) {
        setError('데이터를 불러오는 중 오류가 발생했습니다.');
        console.error('Error loading dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-600 font-semibold">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards - 첫 줄 */}
      {kpiData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* 1. 평균 신용등급 (전월 대비 트렌드) */}
          <KPICard
            title="평균 신용등급"
            value={kpiData.avg_credit_grade.toFixed(2)}
            subtitle="1-10 등급 (낮을수록 우수)"
            trend={kpiData.avg_credit_grade_change}
            trendLabel=""
            status={
              kpiData.avg_credit_grade_change < -0.05
                ? 'improving'
                : kpiData.avg_credit_grade_change > 0.05
                ? 'worsening'
                : 'neutral'
            }
            description={
              kpiData.avg_credit_grade_change < -0.05
                ? '시장 전체 신용 건전성이 개선되고 있습니다'
                : kpiData.avg_credit_grade_change > 0.05
                ? '시장 전체 신용 건전성이 악화되고 있습니다'
                : '시장 신용 건전성이 안정적으로 유지되고 있습니다'
            }
          />

          {/* 2. HHI 위험 집중도 */}
          <KPICard
            title="위험 집중도 (HHI)"
            value={kpiData.hhi_index.toFixed(0)}
            subtitle={
              kpiData.hhi_status === 'safe'
                ? '✓ 양호'
                : kpiData.hhi_status === 'moderate'
                ? '⚠ 주의'
                : '⚠ 위험'
            }
            status={kpiData.hhi_status}
            description={kpiData.hhi_description}
          />

          {/* 3. 고위험군 비율 */}
          <KPICard
            title="고위험군 비율"
            value={`${kpiData.high_risk_ratio.toFixed(2)}%`}
            subtitle="신용등급 8-10"
            trend={kpiData.high_risk_change}
            trendLabel="p"
            status={
              kpiData.high_risk_change < -0.5
                ? 'improving'
                : kpiData.high_risk_change > 0.5
                ? 'worsening'
                : 'neutral'
            }
            description={
              kpiData.high_risk_ratio > 15
                ? '고위험군 비율이 높습니다. 시장 전반의 신용 리스크가 증가했습니다'
                : kpiData.high_risk_ratio > 10
                ? '고위험군 비율이 평균 수준입니다'
                : '고위험군 비율이 낮습니다. 시장 건전성이 양호합니다'
            }
          />

          {/* 4. 우량군/고위험군 배율 */}
          <KPICard
            title="우량군/고위험군 배율"
            value={`${kpiData.premium_to_risk_ratio.toFixed(1)}x`}
            subtitle={`우량군 ${kpiData.premium_ratio.toFixed(1)}%`}
            status={
              kpiData.premium_to_risk_ratio >= 3
                ? 'safe'
                : kpiData.premium_to_risk_ratio >= 2
                ? 'moderate'
                : 'high'
            }
            description={
              kpiData.premium_to_risk_ratio >= 3
                ? '우량 기업이 고위험 기업보다 3배 이상 많습니다. 시장 구조가 건전합니다'
                : kpiData.premium_to_risk_ratio >= 2
                ? '우량 기업이 고위험 기업보다 2배 이상 많습니다'
                : '우량 기업과 고위험 기업의 비율 차이가 작습니다. 시장 경계가 필요합니다'
            }
          />
        </div>
      )}

      {/* 신용등급 분포 (왼쪽) + 레이더 차트 (오른쪽) */}
      {(creditData.length > 0 || radarData.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[600px]">
          {/* Credit Grade Distribution - 왼쪽 50% */}
          {creditData.length > 0 && (
            <div className="h-full">
              <CreditGradeDistribution data={creditData} />
            </div>
          )}

          {/* Industry Risk Radar Chart - 오른쪽 50% */}
          {radarData.length > 0 && (
            <div className="h-full">
              <IndustryRiskRadarChart data={radarData} />
            </div>
          )}
        </div>
      )}

      {/* Financial Health Gauges */}
      {benchmarkData && (
        <FinancialHealthGauges data={benchmarkData} />
      )}

      {/* Trend Chart and Pie Chart in same row */}
      {(trendData.length > 0 || compositionData.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Trend Chart - 3/5 width (60%) */}
          {trendData.length > 0 && (
            <div className="lg:col-span-3">
              <DefaultTrendChart data={trendData} />
            </div>
          )}

          {/* Pie Chart - 2/5 width (40%) */}
          {compositionData.length > 0 && (
            <div className="lg:col-span-2">
              <IndustryPieChart data={compositionData} />
            </div>
          )}
        </div>
      )}

      {/* Heatmap and Bar Chart in same row */}
      {(heatmapData.length > 0 || barData.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Heatmap - 2/5 width (40%) - Left */}
          {heatmapData.length > 0 && (
            <div className="lg:col-span-2">
              <DefaultHeatmap data={heatmapData} />
            </div>
          )}

          {/* Bar Chart - 3/5 width (60%) - Right */}
          {barData.length > 0 && (
            <div className="lg:col-span-3">
              <IndustryBarChart data={barData} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
