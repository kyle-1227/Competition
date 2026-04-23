import type { CarbonHistoryPoint, PredictSeriesPoint } from '@/api/modules/dashboard-carbon-predict';

export interface CarbonPredictTooltipCtx {
  firstFutureYear: number;
  entityLabel: string;
  compareName: string;
  viewModeLabel: string;
  methodLabel: string;
  sourceNotice: string;
  boundaryNotice: string;
  isCustomView?: boolean;
  customBaseLabel?: string | null;
  customApplied?: boolean;
  customSummary?: string | null;
  preferredEntitySeriesName?: string | null;
  historyByYear: Map<number, CarbonHistoryPoint>;
  compareByYear: Map<number, number>;
}

type AxisTooltipParam = {
  axisValue?: string | number;
  seriesName?: string;
  value?: unknown;
  data?: unknown;
};

function toNumericValue(data: unknown) {
  if (typeof data === 'number') return data;
  if (data && typeof data === 'object' && 'value' in (data as Record<string, unknown>)) {
    const raw = (data as PredictSeriesPoint).value;
    return typeof raw === 'number' ? raw : Number(raw);
  }
  const num = Number(data);
  return Number.isFinite(num) ? num : null;
}

function fmt(value: number | null | undefined, digits = 4) {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toFixed(digits);
}

function pickCurrentParam(list: AxisTooltipParam[], ctx: CarbonPredictTooltipCtx) {
  if (ctx.preferredEntitySeriesName) {
    const preferred = list.find((item) => item.seriesName === ctx.preferredEntitySeriesName && toNumericValue(item.data ?? item.value) != null);
    if (preferred) return preferred;
  }
  return list.find((item) => (item.seriesName || '').startsWith(ctx.entityLabel) && toNumericValue(item.data ?? item.value) != null);
}

function renderPredictDetail(ctx: CarbonPredictTooltipCtx) {
  return `
    <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;">
      <span style="color:#94a3b8;">当前模式</span>
      <span style="color:#2dd4bf;">${ctx.viewModeLabel}</span>
    </div>
    <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;">
      <span style="color:#94a3b8;">预测方法</span>
      <span style="color:#cbd5e1;">${ctx.methodLabel}</span>
    </div>
    ${ctx.isCustomView ? `
      <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;">
        <span style="color:#94a3b8;">自定义基线</span>
        <span style="color:#cbd5e1;">${ctx.customBaseLabel || '基准'}</span>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;">
        <span style="color:#94a3b8;">参数状态</span>
        <span style="color:#cbd5e1;">${ctx.customApplied ? '已应用' : '未调整'}</span>
      </div>
      ${ctx.customSummary ? `
        <div style="margin-top:6px;color:#cbd5e1;font-size:11px;line-height:1.6;">
          ${ctx.customSummary}
        </div>
      ` : ''}
    ` : `
      <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;">
        <span style="color:#94a3b8;">展示口径</span>
        <span style="color:#cbd5e1;">官方情景</span>
      </div>
    `}
    <div style="margin-top:8px;color:#94a3b8;font-size:11px;line-height:1.6;">
      ${ctx.boundaryNotice}
    </div>
  `;
}

function renderHistoryDetail(historyRow: CarbonHistoryPoint | undefined) {
  return `
    <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;">
      <span style="color:#94a3b8;">绿色金融指数</span>
      <span style="color:#2dd4bf;">${fmt(historyRow?.gfi_std)}</span>
    </div>
    <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;">
      <span style="color:#94a3b8;">能源强度</span>
      <span style="color:#cbd5e1;">${fmt(historyRow?.energy_intensity)}</span>
    </div>
    <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;">
      <span style="color:#94a3b8;">人均能源消耗</span>
      <span style="color:#cbd5e1;">${fmt(historyRow?.energy_per_capita)}</span>
    </div>
    ${historyRow?.ln_pop != null ? `
      <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;">
        <span style="color:#94a3b8;">人口对数</span>
        <span style="color:#cbd5e1;">${fmt(historyRow.ln_pop)}</span>
      </div>
    ` : ''}
  `;
}

export function getCarbonPredictTooltipHtml(params: unknown, ctx: CarbonPredictTooltipCtx): string {
  const list = Array.isArray(params) ? (params as AxisTooltipParam[]) : [];
  const year = Number(list[0]?.axisValue ?? 0);
  const isPredictYear = year >= ctx.firstFutureYear;
  const currentParam = pickCurrentParam(list, ctx);
  const compareParam = list.find((item) => (item.seriesName || '').startsWith(ctx.compareName) && toNumericValue(item.data ?? item.value) != null);
  const currentValue = toNumericValue(currentParam?.data ?? currentParam?.value);
  const compareValue = toNumericValue(compareParam?.data ?? compareParam?.value);
  const historyRow = ctx.historyByYear.get(year);
  const detailHtml = isPredictYear ? renderPredictDetail(ctx) : renderHistoryDetail(historyRow);

  return `
    <div style="
      min-width:240px;
      padding:12px 14px;
      border-radius:12px;
      border:1px solid rgba(34,211,238,0.38);
      background:rgba(7,15,32,0.94);
      box-shadow:0 0 22px rgba(34,211,238,0.18);
      color:#f8fafc;
      font-family:sans-serif;
    ">
      <div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:8px;margin-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.08);">
        <span style="color:#22d3ee;font-weight:700;font-size:14px;">${ctx.entityLabel}</span>
        <span style="color:#cbd5e1;font-size:12px;">${year} 年</span>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:13px;">
        <span style="color:#94a3b8;">碳排放强度</span>
        <span style="color:#ffffff;font-weight:700;">${fmt(currentValue)}</span>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;">
        <span style="color:#94a3b8;">${ctx.compareName}</span>
        <span style="color:#cbd5e1;">${fmt(compareValue)}</span>
      </div>
      ${detailHtml}
      <div style="margin-top:8px;color:#64748b;font-size:11px;line-height:1.6;">
        ${ctx.sourceNotice}
      </div>
    </div>
  `;
}
