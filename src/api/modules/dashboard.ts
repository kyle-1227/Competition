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


/** 能耗强度预测接口响应类型 */
export interface PredictEnergyResponse {
  scatter_data: number[][];
  predict_point: number[];
  trendline: number[][];
  predicted_drop_percent: number;
  current_gfi: number;
  current_outcome: number;
  beta_coefficient: number;
  base_province: string;
  base_year: number;
}

/** 能耗强度预测接口参数类型 */
export interface PredictEnergyParams {
  intensity_increment: number;
  year?: number;
  province?: string;
}

/** 能耗强度预测接口 */
export const predictEnergyIntensity = (params: PredictEnergyParams, signal?: AbortSignal) => {
  return http.get<{ code: number; msg: string; data: PredictEnergyResponse }>(
    'api/energy/predict',
    params,
    signal ? { signal } : undefined,
  );
};
