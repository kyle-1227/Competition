import { onMounted, onUnmounted, watch, inject, nextTick, type Ref } from 'vue';
import * as echarts from 'echarts/core';
import type { EChartsCoreOption, EChartsType } from 'echarts/core';
import { BarChart, LineChart, RadarChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  GraphicComponent,
  RadarComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import {
  selectedYear,
  realProvinceData,
  realCityData,
  gfDrillProvince,
  gfRadarCityHoverGeoName,
  findCityRowByGeoName,
  extractList,
  type ProvinceGreenFinance,
} from './provinceData';
import {
  greenFinanceIndicators,
  type GreenFinanceMonitorRow,
} from './greenFinanceMeta';

echarts.use([
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  GraphicComponent,
  RadarComponent,
  BarChart,
  LineChart,
  RadarChart,
  CanvasRenderer,
]);

type GfValueKey = keyof Omit<GreenFinanceMonitorRow, 'province' | 'score'>;
type ProvinceIndicatorKey =
  | 'greenCredit'
  | 'greenInvest'
  | 'greenInsurance'
  | 'greenBond'
  | 'greenExpend'
  | 'greenFund'
  | 'greenEquity';

type WeightedScoreBreakdown = {
  totalScore: number;
  rawValueByKey: Record<GfValueKey, number>;
  weightedRawByKey: Record<GfValueKey, number>;
  segmentScoreByKey: Record<GfValueKey, number>;
};

const GF_WEIGHT_CONFIG: Array<{
  monitorKey: GfValueKey;
  sourceKey: ProvinceIndicatorKey;
  label: string;
  weight: number;
}> = [
  { monitorKey: 'greenCredit', sourceKey: 'greenCredit', label: '绿色信贷', weight: 0.1236 },
  { monitorKey: 'greenInvest', sourceKey: 'greenInvest', label: '绿色投资', weight: 0.1572 },
  { monitorKey: 'greenInsurance', sourceKey: 'greenInsurance', label: '绿色保险', weight: 0.1303 },
  { monitorKey: 'greenBond', sourceKey: 'greenBond', label: '绿色债券', weight: 0.186 },
  { monitorKey: 'greenSupport', sourceKey: 'greenExpend', label: '绿色支持', weight: 0.1711 },
  { monitorKey: 'greenFund', sourceKey: 'greenFund', label: '绿色基金', weight: 0.1218 },
  { monitorKey: 'greenEquity', sourceKey: 'greenEquity', label: '绿色权益', weight: 0.1099 },
];

function gfVal(item: GreenFinanceMonitorRow, key: string): number {
  return item[key as GfValueKey];
}

function toScorePoints(score: number): number {
  return Number(score ?? 0) * 100;
}

function calcScoreAxisMax(values: number[]): number {
  const maxValue = Math.max(...values, 0);
  if (maxValue <= 10) return 10;
  if (maxValue <= 20) return Math.ceil(maxValue / 2) * 2;
  if (maxValue <= 50) return Math.ceil(maxValue / 5) * 5;
  return Math.ceil(maxValue / 10) * 10;
}

function buildWeightedScoreBreakdown(row: ProvinceGreenFinance): WeightedScoreBreakdown {
  const rawValueByKey = {} as Record<GfValueKey, number>;
  const weightedRawByKey = {} as Record<GfValueKey, number>;
  const segmentScoreByKey = {} as Record<GfValueKey, number>;
  let weightedRawSum = 0;

  GF_WEIGHT_CONFIG.forEach((config) => {
    const rawValue = Number(row[config.sourceKey] ?? 0);
    const weightedRaw = rawValue * config.weight;
    rawValueByKey[config.monitorKey] = rawValue;
    weightedRawByKey[config.monitorKey] = weightedRaw;
    weightedRawSum += weightedRaw;
  });

  const totalScore = Number(row.score ?? 0);
  GF_WEIGHT_CONFIG.forEach((config) => {
    segmentScoreByKey[config.monitorKey] =
      weightedRawSum > 0 ? totalScore * (weightedRawByKey[config.monitorKey] / weightedRawSum) : 0;
  });

  return {
    totalScore,
    rawValueByKey,
    weightedRawByKey,
    segmentScoreByKey,
  };
}

/** 接口省级记录 → 屏二雷达/玫瑰图结构（七维键与 greenFinanceIndicators 一致） */
export function provinceToGfMonitorRow(p: ProvinceGreenFinance): GreenFinanceMonitorRow {
  return {
    province: p.province,
    score: Number(p.score ?? 0),
    greenCredit: p.greenCredit,
    greenInvest: p.greenInvest,
    greenInsurance: p.greenInsurance,
    greenBond: p.greenBond,
    greenSupport: p.greenExpend,
    greenFund: p.greenFund,
    greenEquity: p.greenEquity,
  };
}

export function getGfMonitorRows(): GreenFinanceMonitorRow[] {
  const raw = realProvinceData.value;
  if (raw.length > 0) return raw.map(provinceToGfMonitorRow);
  return [];
}

/** 碳模块：万吨 CO₂（库内为吨级量级，除以 1e4） */
export function getCarbonRowsFromApi(): { province: string; carbonEmission: number }[] {
  const raw = realProvinceData.value;
  if (raw.length > 0) {
    return raw.map((r) => ({
      province: r.province,
      carbonEmission: (r.carbonEmission ?? 0) / 10000,
    }));
  }
  return [];
}

/** 屏二雷达：下钻时优先地图悬停市，否则 Top1 市；全国视角用下拉省 */
function getGreenFinanceChartItem(selectedProv: Ref<string>): GreenFinanceMonitorRow | null {
  if (gfDrillProvince.value && realCityData.value.length > 0) {
    const hovered = gfRadarCityHoverGeoName.value
      ? findCityRowByGeoName(gfRadarCityHoverGeoName.value)
      : undefined;
    if (hovered) return provinceToGfMonitorRow(hovered);
    const top = [...realCityData.value].sort((a, b) => Number(b.score ?? 0) - Number(a.score ?? 0))[0];
    return provinceToGfMonitorRow(top);
  }
  const rows = getGfMonitorRows();
  return rows.find((d) => d.province === selectedProv.value) || rows[0] || null;
}

/* ========================================================================
 * 延迟初始化辅助：解决 v-show 下图表容器 0 尺寸的问题
 * ======================================================================== */
function useDeferredChart(tabKey: string, initFn: () => void) {
  const activeTab = inject<Ref<string>>('activeTab');
  onMounted(() => {
    if (activeTab?.value === tabKey) {
      nextTick(initFn);
    }
    if (activeTab) {
      watch(activeTab, (val) => {
        if (val === tabKey) {
          nextTick(initFn);
        }
      });
    }
  });
}

function shortRegionLabel(name: string): string {
  return name.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, '');
}

/** 七维堆叠横向柱：彩虹色（与 Top10 图例顺序一致） */
const GF_TOP10_RAINBOW = [
  '#ff5252',
  '#ff9800',
  '#ffeb3b',
  '#66bb6a',
  '#00e5ff',
  '#448aff',
  '#ab47bc',
];

export function useGreenFinanceTop10Bar() {
  let chart: EChartsType | null = null;
  let hooksReady = false;
  function render() {
    const drill = gfDrillProvince.value;
    let rows: ProvinceGreenFinance[];
    if (drill && realCityData.value.length > 0) {
      rows = [...realCityData.value].sort((a, b) => Number(b.score ?? 0) - Number(a.score ?? 0)).slice(0, 10);
    } else {
      rows = [...realProvinceData.value].sort((a, b) => Number(b.score ?? 0) - Number(a.score ?? 0)).slice(0, 10);
    }
    if (!rows.length) {
      chart?.clear();
      return;
    }
    const rankedRows = rows.map((row) => ({
      row,
      breakdown: buildWeightedScoreBreakdown(row),
    }));
    const categories = rankedRows.map(({ row }) => shortRegionLabel(row.province));
    const totals = rankedRows.map(({ breakdown }) => toScorePoints(breakdown.totalScore));
    const axisMax = calcScoreAxisMax(totals);
    const series = GF_WEIGHT_CONFIG.map((config, si) => ({
      name: config.label,
      type: 'bar' as const,
      stack: 'gf7',
      emphasis: {
        focus: 'series' as const,
        blurScope: 'coordinateSystem' as const,
      },
      blur: {
        itemStyle: {
          opacity: 0.2,
        },
      },
      itemStyle: {
        color: GF_TOP10_RAINBOW[si % GF_TOP10_RAINBOW.length],
        borderColor: 'rgba(255,255,255,0.22)',
        borderWidth: 0.5,
        shadowBlur: 10,
        shadowColor: GF_TOP10_RAINBOW[si % GF_TOP10_RAINBOW.length],
        borderRadius: [2, 2, 2, 2],
      },
      data: rankedRows.map(({ breakdown }) => ({
        value: toScorePoints(breakdown.segmentScoreByKey[config.monitorKey]),
        rawValue: breakdown.rawValueByKey[config.monitorKey],
        weightedScore: toScorePoints(breakdown.segmentScoreByKey[config.monitorKey]),
        totalScore: toScorePoints(breakdown.totalScore),
      })),
    }));
    if (!chart) {
      const el = document.getElementById('gf-gf-top10-bar');
      if (!el || el.clientWidth === 0) return;
      chart = echarts.init(el, 'dark');
      window.addEventListener('resize', () => chart?.resize());
    }
    chart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(10,15,30,0.92)',
          borderColor: 'rgba(0,229,255,0.35)',
          textStyle: { color: '#fff', fontSize: 12 },
          formatter: (p: unknown) => {
            const payload = p as {
              seriesName?: string;
              name?: string;
              marker?: string;
              data?: {
                rawValue?: number;
                weightedScore?: number;
                totalScore?: number;
              };
            };
            const payloadRegion = payload.name ?? '';
            const payloadDim = payload.seriesName ?? '';
            const rawValue = Number(payload.data?.rawValue ?? 0);
            const weightedScore = Number(payload.data?.weightedScore ?? 0);
            const totalScore = Number(payload.data?.totalScore ?? 0);
            return `
              <div style="font-weight:600;color:#00e5ff;margin-bottom:8px">${payloadRegion}</div>
              <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
                ${payload.marker ?? ''}
                <span style="color:#aaa">${payloadDim}</span>
              </div>
              <div style="display:flex;justify-content:space-between;gap:16px;margin:2px 0">
                <span style="color:rgba(255,255,255,0.6)">原始数据</span>
                <b style="color:#fff">${rawValue.toFixed(4)}</b>
              </div>
              <div style="display:flex;justify-content:space-between;gap:16px;margin:2px 0">
                <span style="color:rgba(255,255,255,0.6)">加权分数</span>
                <b style="color:#fff">${weightedScore.toFixed(2)} 分</b>
              </div>
              <div style="display:flex;justify-content:space-between;gap:16px;margin:2px 0">
                <span style="color:rgba(255,255,255,0.45)">综合分</span>
                <span style="color:#ffd54f">${totalScore.toFixed(2)} 分</span>
              </div>
            `;
            const x = p as { seriesName?: string; name?: string; value?: number; marker?: string };
            const v = Number(typeof x.value === 'number' && Number.isFinite(x.value) ? x.value : 0);
            const points = v.toFixed(2);
            const pct = points;
            const region = x.name ?? '';
            const dim = x.seriesName ?? '';
            return `<div style="font-weight:600;color:#00e5ff;margin-bottom:6px">${region}</div>${x.marker ?? ''}<span style="color:#aaa">${dim}</span> <b style="color:#fff">${points}</b> <span style="color:rgba(255,255,255,0.45)">分</span>`;
            return `<div style="font-weight:600;color:#00e5ff;margin-bottom:6px">${region}</div>${x.marker ?? ''}<span style="color:#aaa">${dim}</span> <b style="color:#fff">${pct}</b> <span style="color:rgba(255,255,255,0.45)">分</span>`;
          },
        },
        grid: { left: 6, right: 14, top: 8, bottom: 4, containLabel: true },
        xAxis: {
          type: 'value',
          min: 0,
          max: axisMax,
          nameLocation: 'end',
          nameGap: 8,
          nameTextStyle: { color: 'rgba(200,220,255,0.45)', fontSize: 9 },
          axisLabel: { color: 'rgba(200,220,255,0.45)', fontSize: 9 },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        },
        yAxis: {
          type: 'category',
          data: categories,
          inverse: true,
          axisLabel: { color: 'rgba(220,235,255,0.82)', fontSize: 10 },
          axisLine: { lineStyle: { color: 'rgba(0,229,255,0.2)' } },
        },
        series,
      },
      true,
    );
  }
  useDeferredChart('greenFinance', () => {
    render();
    if (!hooksReady) {
      hooksReady = true;
      watch(realProvinceData, render, { deep: true });
      watch(realCityData, render, { deep: true });
      watch(gfDrillProvince, render);
      watch(selectedYear, render);
    }
  });
}

/** 通用：基于模板 ref 的 ECharts（懒初始化 + resize；可选 tabKey 与 activeTab 对齐后 resize） */
export interface UseChartOptions {
  theme?: string;
  /** 与 index provide 的 activeTab 一致时，切回该 Tab 会 nextTick resize */
  tabKey?: string;
}

export function useChart(chartRef: Ref<HTMLElement | null>, options?: UseChartOptions) {
  const theme = options?.theme ?? 'dark';
  const tabKey = options?.tabKey;
  const activeTab = inject<Ref<string> | undefined>('activeTab', undefined);
  let chart: EChartsType | null = null;

  function onWindowResize() {
    chart?.resize();
  }

  function tryInit(): boolean {
    const el = chartRef.value;
    if (!el || el.clientWidth === 0) return false;
    if (!chart) {
      chart = echarts.init(el, theme);
      window.addEventListener('resize', onWindowResize);
    }
    return true;
  }

  function dispose() {
    if (chart) {
      window.removeEventListener('resize', onWindowResize);
      chart.dispose();
      chart = null;
    }
  }

  function resize() {
    chart?.resize();
  }

  function setOption(option: EChartsCoreOption, notMerge = true) {
    const apply = () => {
      if (!tryInit()) return false;
      chart!.setOption(option, notMerge);
      return true;
    };
    if (!apply()) {
      nextTick(() => {
        if (tryInit()) {
          chart!.setOption(option, notMerge);
        }
      });
    }
  }

  onMounted(() => {
    if (tabKey && activeTab) {
      watch(
        activeTab,
        (val) => {
          if (val === tabKey) {
            nextTick(() => resize());
          }
        },
        { flush: 'post' },
      );
    }
  });

  onUnmounted(() => {
    dispose();
  });

  return { setOption, resize, dispose };
}

/* ========================================================================
 * 绿色金融监测 - 七维雷达图（增强版）
 * ======================================================================== */
export function useGreenFinanceRadar(selectedProv: Ref<string>) {
  let chart: EChartsType | null = null;
  let hooksReady = false;
  function render() {
    const item = getGreenFinanceChartItem(selectedProv);
    if (!item) return;
    const values = greenFinanceIndicators.map((ind) => gfVal(item, ind.key));
    const totalScore = Number(item.score ?? 0);
    // 动态计算每个维度的最大值，让数据更接近边缘
    const maxValue = Math.max(...values);
    const dynamicMax = maxValue > 0 ? maxValue * 1.05 : 0.18; // 使用1.25倍最大值，让数据更接近边缘
    const indicator = greenFinanceIndicators.map((ind) => ({ name: ind.label, max: dynamicMax }));
    if (!chart) {
      const el = document.getElementById('gf-radar');
      if (!el || el.clientWidth === 0) return;
      chart = echarts.init(el, 'dark');
      window.addEventListener('resize', () => chart?.resize());
    }
    chart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(10,15,30,0.9)',
          borderColor: 'rgba(0,229,255,0.3)',
          textStyle: { color: '#fff', fontSize: 12 },
          position(point: number[], _params: unknown, dom: HTMLElement, _rect: unknown, size: { viewSize: number[] }) {
            const gap = 18;
            const viewWidth = size.viewSize[0];
            const viewHeight = size.viewSize[1];
            const boxWidth = dom.offsetWidth;
            const boxHeight = dom.offsetHeight;
            let left = point[0] + gap;
            let top = point[1] - boxHeight / 2;
            if (left + boxWidth > viewWidth - 8) {
              left = Math.max(8, point[0] - boxWidth - gap);
            }
            if (top < 8) top = 8;
            if (top + boxHeight > viewHeight - 8) {
              top = Math.max(8, viewHeight - boxHeight - 8);
            }
            return [left, top];
          },
          formatter() {
            let s = `<b style="color:#00e5ff">${item.province}</b><br/>`;
            greenFinanceIndicators.forEach((ind, i) => {
              const pct = (values[i] * 100).toFixed(2);
              s += `<div style="display:flex;align-items:center;gap:4px;margin:2px 0">`;
              s += `<span style="color:#aaa;width:56px;font-size:11px">${ind.label}</span>`;
              s += `<div style="flex:1;height:4px;background:rgba(0,255,255,0.1);border-radius:2px">`;
              s += `<div style="width:${(values[i] / 0.18) * 100
                }%;height:100%;background:linear-gradient(90deg,#00e5ff,#00FF00);border-radius:2px"></div></div>`;
              s += `<span style="color:#0f0;font-size:11px;width:40px;text-align:right">${pct}</span></div>`;
            });
            s += `<div style="margin-top:4px;border-top:1px solid rgba(0,229,255,0.2);padding-top:4px;text-align:center;color:#FFD54F;font-weight:bold">综合得分: ${(
              totalScore * 100
            ).toFixed(2)}</div>`;
            return s;
          },
        },
        radar: {
          indicator,
          shape: 'polygon',
          radius: '62%',
          axisName: {
            color: 'rgba(220,240,255,0.75)',
            fontSize: 10,
            fontFamily: '"Microsoft YaHei", sans-serif',
          },
          splitArea: {
            areaStyle: {
              color: [
                'rgba(0,60,120,0.12)',
                'rgba(0,20,50,0.08)',
                'rgba(0,60,120,0.06)',
                'rgba(0,20,50,0.04)',
                'rgba(0,60,120,0.02)',
              ],
            },
          },
          splitLine: {
            lineStyle: {
              color: '#00FFFF',
              opacity: 0.12,
              type: 'dashed',
            },
          },
          axisLine: { lineStyle: { color: 'rgba(0,255,255,0.15)' } },
        },
        series: [
          {
            type: 'radar',
            data: [
              {
                value: values,
                name: item.province,
                lineStyle: {
                  color: '#00FF00',
                  width: 2,
                  shadowColor: 'rgba(0,255,0,0.5)',
                  shadowBlur: 8,
                },
                areaStyle: {
                  color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
                    { offset: 0, color: 'rgba(0,255,255,0.25)' },
                    { offset: 1, color: 'rgba(0,255,255,0.02)' },
                  ]),
                },
                itemStyle: {
                  color: '#00FFFF',
                  borderColor: '#00FF00',
                  borderWidth: 2,
                  shadowColor: 'rgba(0,255,255,0.8)',
                  shadowBlur: 10,
                },
                symbol: 'circle',
                symbolSize: 6,
                emphasis: {
                  itemStyle: {
                    shadowBlur: 20,
                    shadowColor: 'rgba(0,255,0,1)',
                  },
                },
              },
            ],
          },
        ],
        graphic: [
          {
            type: 'circle',
            shape: { r: 4 },
            style: { fill: 'rgba(0,255,255,0.3)', stroke: '#00FFFF', lineWidth: 1 },
            left: 'center',
            top: 'center',
          },
        ],
      },
      true,
    );
  }
  useDeferredChart('greenFinance', () => {
    render();
    if (!hooksReady) {
      hooksReady = true;
      watch(selectedProv, render);
      watch(realProvinceData, render, { deep: true });
      watch(gfDrillProvince, render);
      watch(realCityData, render, { deep: true });
      watch(gfRadarCityHoverGeoName, render);
    }
  });
}
/* ========================================================================
 * 碳排放底色 - 横向柱状图 TOP 10
 * ======================================================================== */
export function useCarbonBar(onProvinceClick?: (provinceName: string) => void) {
  let chart: EChartsType | null = null;
  let hooksReady = false;
  let currentSorted: { province: string; carbonEmission: number }[] = [];
  function render() {
    const source = getCarbonRowsFromApi();
    const sorted = [...source]
      .sort((a, b) => b.carbonEmission - a.carbonEmission)
      .slice(0, 10)
      .reverse();
    currentSorted = sorted;
    const provinces = sorted.map((d) => d.province.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, ''));
    const values = sorted.map((d) => d.carbonEmission);
    if (!chart) {
      const el = document.getElementById('carbon-bar');
      if (!el || el.clientWidth === 0) return;
      chart = echarts.init(el, 'dark');
      chart.on('click', (params: { componentType?: string; dataIndex?: number }) => {
        if (params.componentType !== 'series' || typeof params.dataIndex !== 'number') return;
        const row = currentSorted[params.dataIndex];
        if (row) onProvinceClick?.(row.province);
      });
      window.addEventListener('resize', () => chart?.resize());
    }
    chart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (params: { name: string; value: number }[]) =>
            `<b>${params[0].name}</b><br/>碳排放: ${params[0].value.toLocaleString()} 万吨`,
        },
        grid: { left: 10, right: 30, top: 20, bottom: 10, containLabel: true },
        xAxis: {
          type: 'value',
          axisLabel: { color: '#aaa', fontSize: 9 },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        },
        yAxis: {
          type: 'category',
          data: provinces,
          axisLabel: { color: '#ccc', fontSize: 10 },
          axisLine: { lineStyle: { color: '#333' } },
        },
        series: [
          {
            type: 'bar',
            cursor: 'pointer',
            data: values.map((v, i) => {
              let endColor = '#ffcc80';
              if (i >= 7) endColor = '#ff4444';
              else if (i >= 4) endColor = '#ff9800';
              return {
                value: v,
                itemStyle: {
                  color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                    { offset: 0, color: 'rgba(255,80,80,0.2)' },
                    { offset: 1, color: endColor },
                  ]),
                  borderRadius: [0, 4, 4, 0],
                  shadowColor: 'rgba(255,80,80,0.3)',
                  shadowBlur: 6,
                },
              };
            }),
            barWidth: '55%',
            label: {
              show: true,
              position: 'right',
              color: 'rgba(255,180,180,0.8)',
              fontSize: 10,
              formatter: (p: { value: number }) => p.value.toLocaleString(),
            },
          },
        ],
      },
      true,
    );
  }
  useDeferredChart('carbon', () => {
    render();
    if (!hooksReady) {
      hooksReady = true;
      watch(realProvinceData, render, { deep: true });
    }
  });
}
/* ========================================================================
 * 宏观经济动态 - 双 Y 轴混合图（GDP 柱 + 碳排放折线）
 * ======================================================================== */
export interface UseMacroChartOptions {
  chartId?: string;
  tabKey?: string;
  selectedCity?: Ref<string>;
}

export function useMacroChart(selectedProv: Ref<string>, options: UseMacroChartOptions = {}) {
  let chart: EChartsType | null = null;
  let hooksReady = false;
  let resizeAttached = false;
  const chartId = options.chartId ?? 'macro-chart';
  const tabKey = options.tabKey ?? 'macro';

  function onWindowResize() {
    chart?.resize();
  }

  function ensureChart(): boolean {
    if (chart) return true;
    const el = document.getElementById(chartId);
    if (!el || el.clientWidth === 0) return false;
    chart = echarts.init(el, 'dark');
    if (!resizeAttached) {
      window.addEventListener('resize', onWindowResize);
      resizeAttached = true;
    }
    return true;
  }

  function dispose() {
    if (resizeAttached) {
      window.removeEventListener('resize', onWindowResize);
      resizeAttached = false;
    }
    if (chart) {
      chart.dispose();
      chart = null;
    }
  }

  async function fetchMacroData(province: string, city: string) {
    try {
      const { getMacroDataApi } = await import('@/api/modules/dashboard-macro');
      const res: unknown = await getMacroDataApi({
        province: province === '全国' ? undefined : province,
        city: city || undefined,
      });
      const raw = extractList(res);
      return raw.map((r) => {
        const record = r as Record<string, unknown>;
        return {
          year: Number(record.year || 0),
          gdp: Number(record.gdp || 0),
          carbonEmission: Number(record.carbonEmission || 0),
        };
      });
    } catch (error) {
      console.error('❌ 宏观经济数据拉取失败:', error);
      return null;
    }
  }

  async function render() {
    const province = selectedProv.value;
    const city = options.selectedCity?.value ?? '';

    // 尝试从API获取数据
    const apiData = await fetchMacroData(province, city);
    const data = apiData && apiData.length > 0 ? apiData : [];

    if (!data.length) {
      if (!ensureChart()) return;
      chart?.setOption(
        {
          backgroundColor: 'transparent',
          title: {
            text: '暂无宏观经济数据（请检查数据库或接口）',
            left: 'center',
            top: 'middle',
            textStyle: { color: '#888', fontSize: 14 },
          },
          xAxis: { type: 'category', data: [] },
          yAxis: [{ type: 'value' }, { type: 'value' }],
          series: [],
        },
        true,
      );
      return;
    }

    const years = data.map((d) => d.year);
    const gdps = data.map((d) => d.gdp);
    const carbons = data.map((d) => d.carbonEmission);

    if (!ensureChart()) return;
    const macroChart = chart;
    if (!macroChart) return;

    const title = city || (province === '全国' ? '全国' : province.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, ''));

    macroChart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' },
          formatter: (params: { axisValue: string; marker: string; seriesName: string; value: number }[]) => {
            let s = `<b>${params[0].axisValue}年 · ${title}</b><br/>`;
            params.forEach((row) => {
              s += `${row.marker} ${row.seriesName}: ${row.value.toLocaleString()}<br/>`;
            });
            return s;
          },
        },
        legend: {
          data: ['GDP（亿元）', '碳排放（万吨）'],
          textStyle: { color: '#ccc', fontSize: 11 },
          top: 6,
        },
        grid: { left: 55, right: 55, top: 45, bottom: 30 },
        xAxis: {
          type: 'category',
          data: years,
          axisLabel: { color: '#aaa', fontSize: 10 },
          axisLine: { lineStyle: { color: '#555' } },
        },
        yAxis: [
          {
            type: 'value',
            name: 'GDP（亿元）',
            nameTextStyle: { color: '#FFD54F', fontSize: 10 },
            axisLabel: {
              color: '#aaa',
              fontSize: 9,
              formatter: (v: number) => (v >= 10000 ? `${(v / 10000).toFixed(1)}万` : `${v}`),
            },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
          },
          {
            type: 'value',
            name: '碳排放（万吨）',
            nameTextStyle: { color: '#00e5ff', fontSize: 10 },
            axisLabel: { color: '#aaa', fontSize: 9 },
            splitLine: { show: false },
          },
        ],
        series: [
          {
            name: 'GDP（亿元）',
            type: 'bar',
            yAxisIndex: 0,
            data: gdps,
            barWidth: '50%',
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#FFD54F' },
                { offset: 1, color: 'rgba(255,152,0,0.2)' },
              ]),
              borderRadius: [3, 3, 0, 0],
            },
          },
          {
            name: '碳排放（万吨）',
            type: 'line',
            yAxisIndex: 1,
            data: carbons,
            smooth: true,
            lineStyle: { color: '#00e5ff', width: 3, shadowBlur: 8, shadowColor: 'rgba(0,229,255,0.4)' },
            itemStyle: { color: '#00e5ff' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(0,229,255,0.2)' },
                { offset: 1, color: 'rgba(0,229,255,0)' },
              ]),
            },
          },
        ],
      },
      true,
    );
  }

  onUnmounted(dispose);

  useDeferredChart(tabKey, () => {
    render();
    if (!hooksReady) {
      hooksReady = true;
      watch(selectedProv, render);
      if (options.selectedCity) {
        watch(options.selectedCity, render);
      }
      watch(realProvinceData, render, { deep: true });
    }
  });
}
