import http from '@/api/http';

export interface CityCarbonRow {
  year: number;
  province: string;
  city: string;
  cityCode: number | string;
  carbonEmission: number;
  carbonEmissionWanTon: number;
  gdp: number;
  energyConsumption?: number | null;
  energyPerCapita?: number | null;
  energyIntensity?: number | null;
  primaryIndustry?: number | null;
  secondaryIndustry?: number | null;
  tertiaryIndustry?: number | null;
  primaryIndustryRatio?: number | null;
  secondaryIndustryRatio?: number | null;
  tertiaryIndustryRatio?: number | null;
}

export interface CityCarbonPayload {
  province: string;
  year: number;
  cityCount: number;
  carbonEmission: number;
  carbonEmissionWanTon: number;
  rows: CityCarbonRow[];
}

export const getCityCarbonDataApi = (province: string, year = 2024, signal?: AbortSignal) => {
  return http.get<{ code: number; msg: string; data: CityCarbonPayload | null }>(
    'api/city-carbon/data',
    { province, year },
    signal ? { signal } : undefined,
  );
};
