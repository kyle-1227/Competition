import http from '@/api/http';

export interface CityCarbonRow {
  year: number;
  province: string;
  city: string;
  cityCode: number | string;
  carbonEmission: number;
  carbonEmissionWanTon: number;
}

export interface CityCarbonPayload {
  province: string;
  year: number;
  cityCount: number;
  carbonEmission: number;
  carbonEmissionWanTon: number;
  rows: CityCarbonRow[];
}

export interface CountyCarbonRow {
  year: number;
  province: string;
  city: string;
  county: string;
  carbonEmission: number;
  carbonEmissionWanTon: number;
}

export interface CountyCarbonPayload {
  province: string;
  city: string;
  year: number;
  countyCount: number;
  carbonEmission: number;
  carbonEmissionWanTon: number;
  rows: CountyCarbonRow[];
}

export const getCityCarbonDataApi = (province: string, year = 2024, signal?: AbortSignal) => {
  return http.get<{ code: number; msg: string; data: CityCarbonPayload | null }>(
    'api/city-carbon/data',
    { province, year },
    signal ? { signal } : undefined,
  );
};

export const getCountyCarbonDataApi = (
  province: string,
  city: string,
  year = 2024,
  signal?: AbortSignal,
) => {
  return http.get<{ code: number; msg: string; data: CountyCarbonPayload | null }>(
    'api/county-carbon/data',
    { province, city, year },
    signal ? { signal } : undefined,
  );
};
