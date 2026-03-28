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

/** 宏观经济数据接口（支持全国和省级） */
export const getMacroDataApi = (province?: string, signal?: AbortSignal) => {
  return http.get<unknown>(
    'api/macro/data',
    province ? { province } : {},
    signal ? { signal } : undefined,
  );
};

/** SDM / 碳强度预测沙盘：后端 coefficients 结构 */
export interface CarbonPredictCoefficients {
  core: number;
  control: number;
  control_ln_pop: number;
  policy: number;
  spatial: number;
  rho: number;
  mediator: number;
  raw?: Record<string, number>;
}

export interface CarbonHistoryPoint {
  year: number;
  value: number;
}

export interface CarbonPredictDataPayload {
  coefficients: CarbonPredictCoefficients;
  /** 省份全称 -> 年序列；含「全国」 */
  historyData: Record<string, CarbonHistoryPoint[]>;
}

export const getCarbonPredictData = (signal?: AbortSignal) => {
  return http.get<{ code: number; msg: string; data: CarbonPredictDataPayload | null }>(
    'api/dashboard/predict-data',
    undefined,
    signal ? { signal } : undefined,
  );
};

/** 描述性统计表（macro-stats） */
export const getMacroStatsData = (signal?: AbortSignal) => {
  return http.get<{ code: number; msg: string; data: Record<string, unknown>[] | null }>(
    'api/dashboard/macro-stats',
    undefined,
    signal ? { signal } : undefined,
  );
};
