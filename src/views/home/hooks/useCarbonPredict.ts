/**
 * SDM 沙盘：未来若干年碳排放强度推演（与 BizCarbonPrediction 原 computed 一致）
 */

export interface SdmSliderControls {
  core: { value: number };
  control: { value: number };
  policy: { value: number };
  spatial: { value: number };
  mediator: { value: number };
}

export interface SdmCoefficients {
  core: number;
  control: number;
  policy: number;
  spatial: number;
  mediator: number;
  rho: number;
}

export function computeSdmPredictedSeries(
  hist: number[],
  mc: SdmCoefficients,
  controls: SdmSliderControls,
  futureCount: number,
): number[] {
  if (!hist.length || futureCount <= 0) return [];
  let currentVal = hist[hist.length - 1]!;
  const predicted: number[] = [];
  for (let i = 0; i < futureCount; i++) {
    const deltaCore = (controls.core.value - 1) * mc.core;
    const deltaControl = (controls.control.value - 1) * mc.control * 0.1;
    const deltaPolicy = (controls.policy.value - 1) * mc.policy;
    const deltaSpatial = (controls.spatial.value - 1) * mc.spatial;
    const deltaMediator = (controls.mediator.value - 1) * mc.mediator;
    const netEffect = -(deltaCore + deltaPolicy + deltaMediator - deltaControl - deltaSpatial);
    currentVal = currentVal + netEffect - 0.015;
    predicted.push(Number(Math.max(currentVal, 0.1).toFixed(4)));
  }
  return predicted;
}
