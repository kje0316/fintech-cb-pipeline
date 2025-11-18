import axios from 'axios';
import type {
  KPIData,
  IndustryTrendData,
  IndustryComposition,
  HeatmapData,
  IndustryDefaultRate,
  CreditDistribution,
  IndustryRiskRadar,
  FinancialBenchmarks,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Dashboard API calls

export const fetchKPIData = async (): Promise<KPIData> => {
  const response = await api.get('/api/v1/dashboard/kpi');
  return response.data;
};

export const fetchTopIndustriesTrend = async (): Promise<IndustryTrendData[]> => {
  const response = await api.get('/api/v1/dashboard/top-industries-trend');
  return response.data;
};

export const fetchIndustryComposition = async (): Promise<IndustryComposition[]> => {
  const response = await api.get('/api/v1/dashboard/industry-composition');
  return response.data;
};

export const fetchHeatmapData = async (): Promise<HeatmapData[]> => {
  const response = await api.get('/api/v1/dashboard/heatmap');
  return response.data;
};

export const fetchIndustryDefaultRates = async (): Promise<IndustryDefaultRate[]> => {
  const response = await api.get('/api/v1/dashboard/industry-default-rates');
  return response.data;
};

export const fetchCreditDistribution = async (): Promise<CreditDistribution[]> => {
  const response = await api.get('/api/v1/dashboard/credit-distribution');
  return response.data;
};

export const fetchIndustryRiskRadar = async (): Promise<IndustryRiskRadar[]> => {
  const response = await api.get('/api/v1/dashboard/industry-risk-radar');
  return response.data;
};

export const fetchFinancialBenchmarks = async (): Promise<FinancialBenchmarks> => {
  const response = await api.get('/api/v1/dashboard/industry-benchmarks');
  return response.data;
};
