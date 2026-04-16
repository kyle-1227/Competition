import http from '@/api/http';

export type PredictLevel = 'province' | 'city';
export type PredictTargetKey = 'carbonIntensity';
export type PredictScenarioKey = 'conservative' | 'baseline' | 'optimistic';
export type PredictViewMode = PredictScenarioKey | 'custom';

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
  gfi_std?: number | null;
  ln_pop?: number | null;
  energy_intensity?: number | null;
  energy_per_capita?: number | null;
  population?: number | null;
  gdp_growth?: number | null;
  per_capita_gdp?: number | null;
}

export interface PredictSeriesPoint {
  year: number;
  value: number | null;
}

export interface PredictScenarioSeries {
  key: PredictScenarioKey;
  label: string;
  points: PredictSeriesPoint[];
}

export interface PredictScenarioBandPoint {
  year: number;
  min: number | null;
  max: number | null;
}

export interface PredictCompareSeries {
  name: string;
  historyPoints: PredictSeriesPoint[];
  scenarioPoints: Partial<Record<PredictScenarioKey, PredictSeriesPoint[]>>;
}

export interface PredictSampleMeta {
  historyStartYear: number | null;
  historyEndYear: number | null;
  forecastStartYear: number | null;
  forecastEndYear: number | null;
  coverageCount: number;
  coverageNote: string;
  boundaryNotice: string;
}

export interface CarbonPredictDataPayload {
  level: PredictLevel;
  target: PredictTargetKey;
  entityLabel: string;
  province: string;
  city?: string | null;
  coefficients: CarbonPredictCoefficients;
  historySeries: CarbonHistoryPoint[];
  compareSeries: PredictCompareSeries;
  scenarios: PredictScenarioSeries[];
  scenarioBand: PredictScenarioBandPoint[];
  sampleMeta: PredictSampleMeta;
  sourceNotice: string;
  weightType: string;
  availableScenarios: PredictScenarioKey[];
}

export interface CarbonPredictMetaPayload {
  levels: Array<{ key: PredictLevel; label: string }>;
  targets: Array<{ key: PredictTargetKey; label: string }>;
  scenarios: Array<{ key: PredictScenarioKey; label: string; sourceLabel: string }>;
  provinces: string[];
  citiesByProvince: Record<string, string[]>;
  sampleMeta: {
    province: Omit<PredictSampleMeta, 'boundaryNotice'>;
    city: Omit<PredictSampleMeta, 'boundaryNotice'>;
    boundaryNotice: string;
  };
}

export interface CarbonPredictQuery {
  level: PredictLevel;
  target?: PredictTargetKey;
  province?: string;
  city?: string;
}

export const getCarbonPredictMeta = (signal?: AbortSignal) => {
  return http.get<{ code: number; msg: string; data: CarbonPredictMetaPayload | null }>(
    'api/dashboard/predict-meta',
    undefined,
    signal ? { signal } : undefined,
  );
};

export const getCarbonPredictData = (query: CarbonPredictQuery, signal?: AbortSignal) => {
  return http.get<{ code: number; msg: string; data: CarbonPredictDataPayload | null }>(
    'api/dashboard/predict-data',
    {
      ...query,
      target: query.target ?? 'carbonIntensity',
    },
    signal ? { signal } : undefined,
  );
};
