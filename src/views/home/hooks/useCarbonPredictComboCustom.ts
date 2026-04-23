import type {
  CarbonPredictStirpatElasticities,
  PredictCustomDriver,
  PredictCustomDriverKey,
  PredictSeriesPoint,
} from '@/api/modules/dashboard-carbon-predict';

export interface ComboCustomControlState {
  value: number;
}

export type ComboCustomControlMap = Record<PredictCustomDriverKey, ComboCustomControlState>;

export interface ComboCustomChangedDriver extends PredictCustomDriver {
  multiplier: number;
}

export const DEFAULT_DRIVER_META: Record<PredictCustomDriverKey, { label: string; hint: string }> = {
  population: {
    label: '人口',
    hint: '调节人口规模变化对未来碳排放强度的弹性影响。',
  },
  affluence: {
    label: '富裕度',
    hint: '调节人均 GDP 变化对未来碳排放强度的弹性影响。',
  },
  technology: {
    label: '技术或能耗',
    hint: '优先使用人均能源消耗弹性，反映技术进步或能耗变化。',
  },
  industry: {
    label: '产业结构',
    hint: '使用产业结构相关弹性，模拟产业升级或回摆的影响。',
  },
  energyStructure: {
    label: '能源结构',
    hint: '优先使用天然气占比；若缺失则退化为能源强度相关弹性。',
  },
  greenFinance: {
    label: '绿色金融',
    hint: '模拟绿色金融投入变化对未来碳排放强度的影响。',
  },
};

export const DRIVER_KEYS = Object.keys(DEFAULT_DRIVER_META) as PredictCustomDriverKey[];
export const CUSTOM_RANGE_MIN = 0.8;
export const CUSTOM_RANGE_MAX = 1.2;
export const CUSTOM_RANGE_STEP = 0.05;

const DEFAULT_MULTIPLIER = 1;
const EPSILON = 0.001;
const YEAR_RAMP: Record<number, number> = {
  2025: 0.35,
  2026: 0.7,
  2027: 1,
};
const MIN_LOG_SHIFT = -0.35;
const MAX_LOG_SHIFT = 0.35;

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function getDriverCoefficient(
  key: PredictCustomDriverKey,
  elasticities: CarbonPredictStirpatElasticities | null | undefined,
): number {
  const raw = elasticities?.[key];
  return Number.isFinite(raw) ? Number(raw) : 0;
}

export function createDefaultComboCustomControls(): ComboCustomControlMap {
  return {
    population: { value: DEFAULT_MULTIPLIER },
    affluence: { value: DEFAULT_MULTIPLIER },
    technology: { value: DEFAULT_MULTIPLIER },
    industry: { value: DEFAULT_MULTIPLIER },
    energyStructure: { value: DEFAULT_MULTIPLIER },
    greenFinance: { value: DEFAULT_MULTIPLIER },
  };
}

export function resetComboCustomControls(controls: ComboCustomControlMap) {
  DRIVER_KEYS.forEach((key) => {
    controls[key].value = DEFAULT_MULTIPLIER;
  });
}

export function buildComboControlSnapshot(controls: ComboCustomControlMap) {
  return Object.fromEntries(
    DRIVER_KEYS.map((key) => [key, Number(controls[key].value.toFixed(2))]),
  ) as Record<PredictCustomDriverKey, number>;
}

export function summarizeChangedDrivers(
  drivers: PredictCustomDriver[],
  controls: ComboCustomControlMap,
): ComboCustomChangedDriver[] {
  return drivers
    .filter((driver) => driver.active && Math.abs((controls[driver.key]?.value ?? DEFAULT_MULTIPLIER) - DEFAULT_MULTIPLIER) > EPSILON)
    .map((driver) => ({
      ...driver,
      multiplier: controls[driver.key].value,
    }));
}

export function hasCustomAdjustments(
  controls: ComboCustomControlMap,
  drivers: PredictCustomDriver[],
): boolean {
  return summarizeChangedDrivers(drivers, controls).length > 0;
}

export function computeComboAdjustedSeries(
  baseSeries: PredictSeriesPoint[],
  elasticities: CarbonPredictStirpatElasticities | null | undefined,
  controls: ComboCustomControlMap,
  drivers: PredictCustomDriver[],
): PredictSeriesPoint[] {
  if (!baseSeries.length) return [];

  const logShift = clamp(
    drivers.reduce((sum, driver) => {
      if (!driver.active) return sum;
      const multiplier = controls[driver.key]?.value ?? DEFAULT_MULTIPLIER;
      if (!Number.isFinite(multiplier) || multiplier <= 0) return sum;
      if (Math.abs(multiplier - DEFAULT_MULTIPLIER) <= EPSILON) return sum;
      const coefficient = getDriverCoefficient(driver.key, elasticities);
      if (!Number.isFinite(coefficient) || Math.abs(coefficient) <= EPSILON) return sum;
      return sum + coefficient * Math.log(multiplier);
    }, 0),
    MIN_LOG_SHIFT,
    MAX_LOG_SHIFT,
  );

  if (Math.abs(logShift) <= EPSILON) return baseSeries.map((item) => ({ ...item }));

  return baseSeries.map((point) => {
    if (point.value == null || !Number.isFinite(point.value)) {
      return { ...point, value: null };
    }
    const ramp = YEAR_RAMP[point.year] ?? 1;
    const adjusted = point.value * Math.exp(ramp * logShift);
    return {
      ...point,
      value: Number.isFinite(adjusted) ? Number(adjusted.toFixed(6)) : null,
    };
  });
}
