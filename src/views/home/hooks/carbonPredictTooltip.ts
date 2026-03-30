import type { CarbonHistoryPoint } from '@/api/modules/dashboard';

export interface CarbonPredictTooltipCtx {
  firstFutureYear: number;
  selectedProvince: string;
  controls: {
    core: { value: number };
    policy: { value: number };
  };
  yearToData: Map<number, CarbonHistoryPoint>;
}

type AxisTooltipParam = {
  axisValue?: string | number;
  value?: unknown;
};

/**
 * ECharts axis tooltip：历史年展示面板变量，预测年展示情景预设
 */
export function getCarbonPredictTooltipHtml(params: unknown, ctx: CarbonPredictTooltipCtx): string {
  const list = params as AxisTooltipParam[];
  const year = list[0]?.axisValue;
  const isPredict = Number(year) >= ctx.firstFutureYear;
  const rawVal =
    list.find((p) => p.value !== null && p.value !== undefined)?.value ?? 0;
  const numVal = typeof rawVal === 'number' ? rawVal : Number(rawVal);
  const rowData = ctx.yearToData.get(Number(year));

  let detailsHtml = '';
  if (isPredict) {
    detailsHtml = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px;">
              <span style="color: #888;">绿色金融强度预设</span>
              <span style="color: #00ffcc;">${(ctx.controls.core.value * 100).toFixed(0)}%</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px;">
              <span style="color: #888;">政策及结构效能预设</span>
              <span style="color: #ffaa00;">${(ctx.controls.policy.value * 100).toFixed(0)}%</span>
            </div>
          `;
  } else {
    const gfi = rowData?.gfi_std != null ? rowData.gfi_std.toFixed(4) : '—';
    const lnPop = rowData?.ln_pop != null ? rowData.ln_pop.toFixed(4) : '—';
    const ei = rowData?.energy_intensity != null ? rowData.energy_intensity.toFixed(4) : '—';
    const epc = rowData?.energy_per_capita != null ? rowData.energy_per_capita.toFixed(4) : '—';
    detailsHtml = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px;">
              <span style="color: #888;">绿色金融综合指数(X)</span>
              <span style="color: #00ffcc;">${gfi}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px;">
              <span style="color: #888;">人口对数(ln_pop)</span>
              <span style="color: #cbd5e1;">${lnPop}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px;">
              <span style="color: #888;">实际能源强度(Control)</span>
              <span style="color: #cbd5e1;">${ei}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px;">
              <span style="color: #888;">人均能源消耗(Control)</span>
              <span style="color: #cbd5e1;">${epc}</span>
            </div>
          `;
  }

  return `
          <div style="
            background: rgba(13, 20, 36, 0.75);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 255, 204, 0.4);
            box-shadow: 0 0 20px rgba(0, 255, 204, 0.3), inset 0 0 10px rgba(0,255,204,0.1);
            border-radius: 8px;
            padding: 12px 16px;
            color: #fff;
            font-family: sans-serif;
            min-width: 230px;
          ">
            <div style="border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 8px; margin-bottom: 8px; font-weight: bold; color: #00ffcc; font-size: 15px;">
              📍 ${ctx.selectedProvince} | ${year}年 ${isPredict ? '(预测沙盘推演)' : '(历史真实实证)'}
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
              <span style="color: #aaa;">碳排放强度 (因变量Y)</span>
              <span style="color: #fff; font-weight: bold; font-size: 14px;">${Number.isFinite(numVal) ? numVal.toFixed(4) : String(rawVal)}</span>
            </div>
            ${detailsHtml}
          </div>
        `;
}
