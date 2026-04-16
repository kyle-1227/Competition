/**
 * SDM 自定义情景推演：根据当前滑块和离线系数生成未来序列。
 */

export type PredictControlKey = 'core' | 'control' | 'policy' | 'spatial' | 'mediator';

export interface SdmSliderControlItem {
  name: string;
  hint: string;
  value: number;
}

export type SdmSliderControls = Record<PredictControlKey, SdmSliderControlItem>;

export interface SdmCoefficients {
  core: number;
  control: number;
  policy: number;
  spatial: number;
  mediator: number;
  rho: number;
}

export interface PredictContributionBreakdown {
  baselineTrend: number;
  core: number;
  control: number;
  policy: number;
  spatial: number;
  mediator: number;
}

export const DEFAULT_PREDICT_CONTROLS: Readonly<
Record<PredictControlKey, { name: string; hint: string; value: number }>
> = {
  core: {
    name: '绿色金融',
    hint: '绿色金融上升通常预期有助于降低碳强度。',
    value: 1,
  },
  control: {
    name: '能源相关',
    hint: '能源相关变量上升通常会抬高碳强度压力。',
    value: 1,
  },
  policy: {
    name: '政策变量',
    hint: '政策变量用于表示政策实施强度的变化。',
    value: 1,
  },
  spatial: {
    name: '空间溢出',
    hint: '空间溢出增强意味着周边地区联动影响更强。',
    value: 1,
  },
  mediator: {
    name: '中介结构',
    hint: '中介变量用于模拟产业结构或中介机制变化。',
    value: 1,
  },
};

export function createDefaultSdmSliderControls(): SdmSliderControls {
  return {
    core: { ...DEFAULT_PREDICT_CONTROLS.core },
    control: { ...DEFAULT_PREDICT_CONTROLS.control },
    policy: { ...DEFAULT_PREDICT_CONTROLS.policy },
    spatial: { ...DEFAULT_PREDICT_CONTROLS.spatial },
    mediator: { ...DEFAULT_PREDICT_CONTROLS.mediator },
  };
}

function normalizeValue(value: number) {
  return Number(Math.max(value, 0.1).toFixed(4));
}

export function computeSdmPredictedSeries(
  hist: number[],
  coefficients: SdmCoefficients,
  controls: SdmSliderControls,
  futureCount: number,
): number[] {
  if (!hist.length || futureCount <= 0) return [];

  let currentVal = hist[hist.length - 1]!;
  const predicted: number[] = [];

  for (let index = 0; index < futureCount; index += 1) {
    const deltaCore = (controls.core.value - 1) * coefficients.core;
    const deltaControl = (controls.control.value - 1) * coefficients.control * 0.1;
    const deltaPolicy = (controls.policy.value - 1) * coefficients.policy;
    const deltaSpatial = (controls.spatial.value - 1) * coefficients.spatial;
    const deltaMediator = (controls.mediator.value - 1) * coefficients.mediator;
    const netEffect = -(deltaCore + deltaPolicy + deltaMediator - deltaControl - deltaSpatial);

    currentVal = currentVal + netEffect - 0.015;
    predicted.push(normalizeValue(currentVal));
  }

  return predicted;
}

function cloneControls(controls: SdmSliderControls): SdmSliderControls {
  return {
    core: { ...controls.core },
    control: { ...controls.control },
    policy: { ...controls.policy },
    spatial: { ...controls.spatial },
    mediator: { ...controls.mediator },
  };
}

export function resetSdmSliderControls(controls: SdmSliderControls) {
  (Object.keys(controls) as PredictControlKey[]).forEach((key) => {
    controls[key].value = 1;
  });
}

export function computeContributionBreakdown(
  hist: number[],
  coefficients: SdmCoefficients,
  controls: SdmSliderControls,
  futureCount: number,
): PredictContributionBreakdown {
  if (!hist.length || futureCount <= 0) {
    return {
      baselineTrend: 0,
      core: 0,
      control: 0,
      policy: 0,
      spatial: 0,
      mediator: 0,
    };
  }

  const baselineControls = createDefaultSdmSliderControls();
  const baselineSeries = computeSdmPredictedSeries(hist, coefficients, baselineControls, futureCount);
  const currentSeries = computeSdmPredictedSeries(hist, coefficients, controls, futureCount);
  const currentFinal = currentSeries[currentSeries.length - 1] ?? hist[hist.length - 1] ?? 0;
  const baselineFinal = baselineSeries[baselineSeries.length - 1] ?? hist[hist.length - 1] ?? 0;
  const observedFinal = hist[hist.length - 1] ?? 0;

  const breakdown: PredictContributionBreakdown = {
    baselineTrend: Number((baselineFinal - observedFinal).toFixed(4)),
    core: 0,
    control: 0,
    policy: 0,
    spatial: 0,
    mediator: 0,
  };

  (Object.keys(controls) as PredictControlKey[]).forEach((key) => {
    const nextControls = cloneControls(controls);
    nextControls[key].value = 1;
    const resetSeries = computeSdmPredictedSeries(hist, coefficients, nextControls, futureCount);
    const resetFinal = resetSeries[resetSeries.length - 1] ?? baselineFinal;
    breakdown[key] = Number((currentFinal - resetFinal).toFixed(4));
  });

  return breakdown;
}
