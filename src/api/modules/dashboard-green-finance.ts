import http from '@/api/http';

export const getProvinceDataApi = (year = 2024, signal?: AbortSignal) => {
  return http.get<unknown>('api/province/data', { year }, signal ? { signal } : undefined);
};

export const getCityDataApi = (province: string, year = 2024, signal?: AbortSignal) => {
  return http.get<unknown>(
    'api/city/data',
    {
      province,
      year,
    },
    signal ? { signal } : undefined,
  );
};
