import http from '@/api/http';

/** 省级 / 地级市接口（路径相对 BASE_URL，开发时走 vite proxy → 本机 8000） */
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
