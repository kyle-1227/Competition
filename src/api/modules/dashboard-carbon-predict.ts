import http from '@/api/http';

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
  gfi_std?: number;
  ln_pop?: number;
  energy_intensity?: number;
  energy_per_capita?: number;
}

export interface CarbonPredictDataPayload {
  coefficients: CarbonPredictCoefficients;
  historyData: Record<string, CarbonHistoryPoint[]>;
}

export const getCarbonPredictData = (signal?: AbortSignal) => {
  return http.get<{ code: number; msg: string; data: CarbonPredictDataPayload | null }>(
    'api/dashboard/predict-data',
    undefined,
    signal ? { signal } : undefined,
  );
};
