<template>
  <div class="predict-page">
    <div class="predict-top">
      <div class="predict-copy">
        <div class="predict-copy__eyebrow">碳排放强度预测</div>
        <div class="predict-copy__title">历史观测 + 三情景推演 + 自定义沙盘</div>
        <div class="predict-copy__desc">{{ boundaryNotice }}</div>
      </div>

      <div class="predict-actions">
        <div class="chip-group">
          <button
            v-for="item in levelOptions"
            :key="item.key"
            type="button"
            class="chip"
            :class="{ active: selectedLevel === item.key }"
            @click="selectedLevel = item.key"
          >
            {{ item.label }}
          </button>
        </div>

        <div class="selector-grid">
          <label class="field">
            <span class="field__label">{{ selectedLevel === 'province' ? '分析区域' : '所属省份' }}</span>
            <el-select v-model="selectedProvince" popper-class="dark-popper">
              <el-option
                v-for="item in provinceOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </label>

          <label v-if="selectedLevel === 'city'" class="field">
            <span class="field__label">地级市</span>
            <el-select v-model="selectedCity" popper-class="dark-popper" :disabled="!cityOptions.length">
              <el-option v-for="city in cityOptions" :key="city" :label="city" :value="city" />
            </el-select>
          </label>
        </div>
      </div>
    </div>

    <div class="predict-bar">
      <div class="chip-group">
        <button
          v-for="item in scenarioOptions"
          :key="item.key"
          type="button"
          class="chip"
          :class="{ active: selectedMode === item.key, disabled: item.disabled }"
          :disabled="item.disabled"
          @click="selectedMode = item.key"
        >
          {{ item.label }}
        </button>
      </div>
      <div class="predict-bar__text">{{ sourceNotice }}</div>
    </div>

    <div class="predict-main">
      <section class="panel chart-panel">
        <div class="chart-meta">
          <span>当前模式：{{ selectedModeLabel }}</span>
          <span>对比线：{{ compareName }}</span>
          <span>权重类型：{{ currentData?.weightType || '—' }}</span>
        </div>
        <div ref="chartRef" class="chart" />
      </section>

      <aside class="side">
        <section class="panel">
          <div class="panel__title">{{ entityLabel }} · 2027 结论卡</div>
          <div class="stat-grid">
            <div class="stat">
              <span>2027 预测值</span>
              <b>{{ formatNumber(finalPredictionDisplay) }}</b>
            </div>
            <div class="stat">
              <span>较 2024 变化</span>
              <b :class="changeClass">{{ formatPercent(changePctDisplay) }}</b>
            </div>
            <div class="stat">
              <span>变化方向</span>
              <b>{{ directionLabel }}</b>
            </div>
            <div class="stat">
              <span>相对对比线</span>
              <b>{{ formatGap(compareGapDisplay) }}</b>
            </div>
            <div class="stat stat--wide">
              <span>数据来源</span>
              <b>{{ sourceModeLabel }}</b>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel__title">样本与边界</div>
          <div class="info-list">
            <div class="info-row"><span>样本期</span><b>{{ sampleRange }}</b></div>
            <div class="info-row"><span>预测期</span><b>{{ forecastRange }}</b></div>
            <div class="info-row"><span>覆盖数量</span><b>{{ currentData?.sampleMeta.coverageCount ?? 0 }}</b></div>
            <div class="info-note">{{ currentData?.sampleMeta.coverageNote || '—' }}</div>
          </div>
        </section>

        <section class="panel">
          <div class="panel__title">模型说明</div>
          <div class="coef-grid">
            <div class="coef"><span>gfi_std</span><b>{{ formatNumber(modelCoefficients.core) }}</b></div>
            <div class="coef"><span>能源相关</span><b>{{ formatNumber(modelCoefficients.control) }}</b></div>
            <div class="coef"><span>W_gfi_std</span><b>{{ formatNumber(modelCoefficients.spatial) }}</b></div>
            <div class="coef"><span>rho</span><b>{{ formatNumber(modelCoefficients.rho) }}</b></div>
          </div>
          <div class="info-note">系数表示模型关系，不等同于绝对因果。</div>
        </section>

        <section v-if="isCustomMode" class="panel">
          <div class="panel__title">参数贡献估算</div>
          <div class="info-list">
            <div class="info-row"><span>基准趋势</span><b>{{ formatSigned(contributionBreakdown.baselineTrend) }}</b></div>
            <div v-for="item in contributionItems" :key="item.key" class="info-row">
              <span>{{ item.label }}</span>
              <b>{{ formatSigned(item.value) }}</b>
            </div>
          </div>
        </section>

        <section class="panel" :class="{ 'panel--disabled': !isCustomMode }">
          <div class="panel__title">
            自定义参数
            <button type="button" class="reset-btn" :disabled="!isCustomMode" @click="resetControls">
              重置参数
            </button>
          </div>
          <div class="control-list">
            <div v-for="(control, key) in controls" :key="key" class="control">
              <div class="control__head">
                <span>{{ control.name }}</span>
                <b>{{ Math.round(control.value * 100) }}%</b>
              </div>
              <div class="info-note">{{ control.hint }}</div>
              <input
                v-model.number="control.value"
                type="range"
                min="0.5"
                max="1.5"
                step="0.05"
                :disabled="!isCustomMode"
                @input="onControlInput"
              >
            </div>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, shallowRef, watch } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts/core';
import type { EChartsCoreOption, EChartsType } from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TitleComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import {
  getCarbonPredictData,
  getCarbonPredictMeta,
  type CarbonHistoryPoint,
  type CarbonPredictDataPayload,
  type CarbonPredictMetaPayload,
  type PredictLevel,
  type PredictScenarioBandPoint,
  type PredictScenarioKey,
  type PredictSeriesPoint,
  type PredictViewMode,
} from '@/api/modules/dashboard-carbon-predict';
import { useAiAssistant } from './hooks/aiAssistant';
import { getCarbonPredictTooltipHtml } from './hooks/carbonPredictTooltipV3';
import {
  computeContributionBreakdown,
  computeSdmPredictedSeries,
  createDefaultSdmSliderControls,
  resetSdmSliderControls,
  type PredictContributionBreakdown,
  type SdmCoefficients,
} from './hooks/useCarbonPredictV2';

echarts.use([GridComponent, TitleComponent, TooltipComponent, LineChart, CanvasRenderer]);

const FUTURE_YEARS = [2025, 2026, 2027];
const CUSTOM_MODE: PredictViewMode = 'custom';
const TEXT = {
  nationwide: '\u5168\u56fd',
  nationwideLabel: '\u5168\u56fd\uff08\u6837\u672c\u5747\u503c\uff09',
  compareFallback: '\u5bf9\u6bd4\u7ebf',
  custom: '\u81ea\u5b9a\u4e49',
  baseline: '\u57fa\u51c6',
  customSource: '\u81ea\u5b9a\u4e49\u53c2\u6570\u63a8\u6f14',
  offlineSource: '\u79bb\u7ebf\u60c5\u666f\u7ed3\u679c',
  defaultBoundary: '2000-2024 \u4e3a\u5386\u53f2\u89c2\u6d4b\uff0c2025-2027 \u4e3a\u6a21\u578b\u63a8\u6f14\uff1b\u60c5\u666f\u533a\u95f4\u4e0d\u662f\u7edf\u8ba1\u7f6e\u4fe1\u533a\u95f4\u3002',
  loadingSource: '\u6b63\u5728\u52a0\u8f7d\u9884\u6d4b\u7ed3\u679c\u2026',
  noData: '\u6682\u65e0\u9884\u6d4b\u6570\u636e',
  chartName: '\u78b3\u6392\u653e\u5f3a\u5ea6',
  bandLower: '\u60c5\u666f\u533a\u95f4\u4e0b\u754c',
  band: '\u60c5\u666f\u533a\u95f4',
  historySuffix: '\u00b7\u5386\u53f2',
  futureSuffix: '\u00b7\u63a8\u6f14',
} as const;

// Display layer only: carbon intensity is shown as a positive magnitude.
// Raw API/model values stay unchanged because model coefficients and contributions
// can legally be negative and must keep their original meaning.
function toDisplayCarbonIntensity(value: number | null | undefined): number | null {
  if (value == null) return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  return Math.abs(parsed);
}

function toDisplayHistorySeries(points: CarbonHistoryPoint[]): CarbonHistoryPoint[] {
  return points.map((item) => ({
    ...item,
    value: toDisplayCarbonIntensity(item.value) ?? item.value,
  }));
}

function toDisplaySeries(points: PredictSeriesPoint[]): PredictSeriesPoint[] {
  return points.map((item) => ({
    ...item,
    value: toDisplayCarbonIntensity(item.value),
  }));
}

function toDisplayBandPoint(point: PredictScenarioBandPoint): PredictScenarioBandPoint {
  const min = toDisplayCarbonIntensity(point.min);
  const max = toDisplayCarbonIntensity(point.max);
  if (min == null || max == null) return { ...point, min, max };
  return { ...point, min: Math.min(min, max), max: Math.max(min, max) };
}

function toRoundedNumber(value: number | null | undefined, digits = 4): number | null {
  if (value == null || !Number.isFinite(value)) return null;
  return Number(value.toFixed(digits));
}

const chartRef = ref<HTMLElement | null>(null);
const chart = shallowRef<EChartsType | null>(null);
const metaPayload = ref<CarbonPredictMetaPayload | null>(null);
const currentData = ref<CarbonPredictDataPayload | null>(null);
const selectedLevel = ref<PredictLevel>('province');
const selectedProvince = ref<string>(TEXT.nationwide);
const selectedCity = ref<string>('');
const selectedMode = ref<PredictViewMode>('baseline');
const controls = reactive(createDefaultSdmSliderControls());
const { registerPageContext } = useAiAssistant();
let requestSeed = 0;
let resizeObserver: ResizeObserver | null = null;

const levelOptions = computed(() => metaPayload.value?.levels ?? []);
const provinceOptions = computed(() => {
  const provinces = metaPayload.value?.provinces ?? [];
  return selectedLevel.value === 'province'
    ? [{ value: TEXT.nationwide, label: TEXT.nationwideLabel }, ...provinces.map((item) => ({ value: item, label: item }))]
    : provinces.map((item) => ({ value: item, label: item }));
});
const cityOptions = computed(() => metaPayload.value?.citiesByProvince[selectedProvince.value] ?? []);
const availableScenarioSet = computed(() => new Set(currentData.value?.availableScenarios ?? []));
const scenarioOptions = computed(() => [
  ...(metaPayload.value?.scenarios ?? []).map((item) => ({
    key: item.key as PredictViewMode,
    label: item.label,
    disabled: !availableScenarioSet.value.has(item.key),
  })),
  { key: CUSTOM_MODE, label: TEXT.custom, disabled: false },
]);
const entityLabel = computed(() => currentData.value?.entityLabel || (selectedLevel.value === 'city' ? selectedCity.value : selectedProvince.value));
const compareName = computed(() => currentData.value?.compareSeries.name || TEXT.compareFallback);
const selectedModeLabel = computed(() => (
  selectedMode.value === CUSTOM_MODE
    ? TEXT.custom
    : metaPayload.value?.scenarios.find((item) => item.key === selectedMode.value)?.label ?? TEXT.baseline
));
const sourceModeLabel = computed(() => (selectedMode.value === CUSTOM_MODE ? TEXT.customSource : TEXT.offlineSource));
const boundaryNotice = computed(() => currentData.value?.sampleMeta.boundaryNotice || metaPayload.value?.sampleMeta.boundaryNotice || TEXT.defaultBoundary);
const sourceNotice = computed(() => currentData.value?.sourceNotice || TEXT.loadingSource);
const historySeries = computed(() => currentData.value?.historySeries ?? []);
const compareHistorySeries = computed(() => currentData.value?.compareSeries.historyPoints ?? []);
const scenarioBand = computed(() => currentData.value?.scenarioBand ?? []);
const allYears = computed(() => [...historySeries.value.map((item) => item.year), ...FUTURE_YEARS]);

const modelCoefficients = computed<SdmCoefficients>(() => ({
  core: currentData.value?.coefficients.core ?? 0,
  control: currentData.value?.coefficients.control ?? 0,
  policy: currentData.value?.coefficients.policy ?? 0,
  spatial: currentData.value?.coefficients.spatial ?? 0,
  mediator: currentData.value?.coefficients.mediator ?? 0,
  rho: currentData.value?.coefficients.rho ?? 0,
}));

const customFutureSeries = computed(() => computeSdmPredictedSeries(
  historySeries.value.map((item) => item.value),
  modelCoefficients.value,
  controls,
  FUTURE_YEARS.length,
));

const customCompareFutureSeries = computed(() => computeSdmPredictedSeries(
  compareHistorySeries.value.map((item) => item.value ?? 0),
  modelCoefficients.value,
  controls,
  FUTURE_YEARS.length,
));

const selectedFutureSeries = computed<PredictSeriesPoint[]>(() => {
  if (selectedMode.value === CUSTOM_MODE) {
    return FUTURE_YEARS.map((year, index) => ({ year, value: customFutureSeries.value[index] ?? null }));
  }
  return currentData.value?.scenarios.find((item) => item.key === selectedMode.value)?.points ?? [];
});

const compareFutureSeries = computed<PredictSeriesPoint[]>(() => {
  if (selectedMode.value === CUSTOM_MODE) {
    return FUTURE_YEARS.map((year, index) => ({ year, value: customCompareFutureSeries.value[index] ?? null }));
  }
  return currentData.value?.compareSeries.scenarioPoints[selectedMode.value as PredictScenarioKey] ?? [];
});

const contributionBreakdown = computed<PredictContributionBreakdown>(() => computeContributionBreakdown(
  historySeries.value.map((item) => item.value),
  modelCoefficients.value,
  controls,
  FUTURE_YEARS.length,
));

const contributionItems = computed(() => [
  { key: 'core', label: '\u7eff\u8272\u91d1\u878d', value: contributionBreakdown.value.core },
  { key: 'control', label: '\u80fd\u6e90\u76f8\u5173', value: contributionBreakdown.value.control },
  { key: 'policy', label: '\u653f\u7b56\u53d8\u91cf', value: contributionBreakdown.value.policy },
  { key: 'spatial', label: '\u7a7a\u95f4\u6ea2\u51fa', value: contributionBreakdown.value.spatial },
  { key: 'mediator', label: '\u4e2d\u4ecb\u7ed3\u6784', value: contributionBreakdown.value.mediator },
]);

const latestObserved = computed(() => historySeries.value.at(-1)?.value ?? 0);
const finalPrediction = computed(() => selectedFutureSeries.value.at(-1)?.value ?? latestObserved.value);
const compareFinal = computed(() => compareFutureSeries.value.at(-1)?.value ?? compareHistorySeries.value.at(-1)?.value ?? 0);
const compareGap = computed(() => finalPrediction.value - compareFinal.value);
const changePct = computed(() => (latestObserved.value ? (finalPrediction.value - latestObserved.value) / Math.abs(latestObserved.value) : 0));
const historySeriesDisplay = computed(() => toDisplayHistorySeries(historySeries.value));
const compareHistorySeriesDisplay = computed(() => toDisplaySeries(compareHistorySeries.value));
const selectedFutureSeriesDisplay = computed(() => toDisplaySeries(selectedFutureSeries.value));
const compareFutureSeriesDisplay = computed(() => toDisplaySeries(compareFutureSeries.value));
const scenarioBandDisplay = computed(() => scenarioBand.value.map(toDisplayBandPoint));
const latestObservedDisplay = computed(() => toDisplayCarbonIntensity(latestObserved.value) ?? 0);
const finalPredictionDisplay = computed(() => toDisplayCarbonIntensity(finalPrediction.value) ?? latestObservedDisplay.value);
const compareFinalDisplay = computed(() => toDisplayCarbonIntensity(compareFinal.value) ?? 0);
const compareGapDisplay = computed(() => finalPredictionDisplay.value - compareFinalDisplay.value);
const changePctDisplay = computed(() => (
  latestObservedDisplay.value
    ? (finalPredictionDisplay.value - latestObservedDisplay.value) / Math.abs(latestObservedDisplay.value)
    : 0
));
const directionLabel = computed(() => {
  if (Math.abs(changePctDisplay.value) < 0.01) return '\u57fa\u672c\u6301\u5e73';
  return changePctDisplay.value > 0 ? '\u4e0a\u5347' : '\u4e0b\u964d';
});
const changeClass = computed(() => ({
  positive: changePctDisplay.value > 0.01,
  negative: changePctDisplay.value < -0.01,
}));
const isCustomMode = computed(() => selectedMode.value === CUSTOM_MODE);
const sampleRange = computed(() => `${currentData.value?.sampleMeta.historyStartYear ?? '—'} - ${currentData.value?.sampleMeta.historyEndYear ?? '—'}`);
const forecastRange = computed(() => `${currentData.value?.sampleMeta.forecastStartYear ?? '—'} - ${currentData.value?.sampleMeta.forecastEndYear ?? '—'}`);

const unregisterAiContext = registerPageContext('energy', () => ({
  year: currentData.value?.sampleMeta.forecastEndYear ?? FUTURE_YEARS[2],
  selectedProvince: selectedProvince.value,
  drillProvince: selectedLevel.value === 'city' ? selectedProvince.value : undefined,
  drillCity: selectedLevel.value === 'city' ? selectedCity.value : undefined,
  snapshot: {
    level: selectedLevel.value,
    province: selectedProvince.value,
    city: selectedLevel.value === 'city' ? selectedCity.value : null,
    selectedScenario: selectedMode.value,
    availableScenarios: currentData.value?.availableScenarios ?? [],
    sourceMode: sourceModeLabel.value,
    sourceNotice: sourceNotice.value,
    displayValueMode: 'absoluteCarbonIntensity',
    displayValueNote: '页面展示的碳排放强度为显示层正向化后的绝对值，原始模型值保留在 raw* 字段。',
    compareSummary: `${selectedModeLabel.value}\u4e0b\uff0c${entityLabel.value} \u76f8\u5bf9 ${compareName.value}${formatGap(compareGapDisplay.value)}\u3002`,
    compareGap: toRoundedNumber(compareGapDisplay.value),
    scenarioBand: scenarioBandDisplay.value.map((item) => ({ ...item })),
    // Contributions are raw model effects: negative values are meaningful and must not be display-flipped.
    customContributionBreakdown: isCustomMode.value ? contributionBreakdown.value : null,
    contributionValueMode: 'rawModelContribution',
    sampleMeta: currentData.value?.sampleMeta ?? null,
    boundaryNotice: boundaryNotice.value,
    entityLabel: entityLabel.value,
    finalPrediction: toRoundedNumber(finalPredictionDisplay.value),
    predictionChangePct: toRoundedNumber(changePctDisplay.value * 100, 2),
    historySeries: historySeriesDisplay.value.map((item) => ({ year: item.year, value: item.value })),
    currentFutureSeries: selectedFutureSeriesDisplay.value.map((item) => ({ ...item })),
    rawFinalPrediction: toRoundedNumber(finalPrediction.value),
    rawPredictionChangePct: toRoundedNumber(changePct.value * 100, 2),
    rawCompareGap: toRoundedNumber(compareGap.value),
    rawHistorySeries: historySeries.value.map((item) => ({ year: item.year, value: item.value })),
    rawCurrentFutureSeries: selectedFutureSeries.value.map((item) => ({ ...item })),
    rawScenarioBand: scenarioBand.value.map((item) => ({ ...item })),
  },
}));

function ensureSelection() {
  if (!metaPayload.value) return;
  if (selectedLevel.value === 'province') {
    if (!selectedProvince.value || (selectedProvince.value !== TEXT.nationwide && !metaPayload.value.provinces.includes(selectedProvince.value))) {
      selectedProvince.value = TEXT.nationwide;
    }
    selectedCity.value = '';
    return;
  }
  if (!selectedProvince.value || selectedProvince.value === TEXT.nationwide || !metaPayload.value.provinces.includes(selectedProvince.value)) {
    selectedProvince.value = metaPayload.value.provinces[0] || '';
  }
  const cities = metaPayload.value.citiesByProvince[selectedProvince.value] ?? [];
  if (!selectedCity.value || !cities.includes(selectedCity.value)) {
    selectedCity.value = cities[0] || '';
  }
}

function formatNumber(value: number | null | undefined) {
  return value == null || Number.isNaN(value) ? '—' : value.toFixed(4);
}

function formatPercent(value: number) {
  return Number.isFinite(value) ? `${value > 0 ? '+' : ''}${(value * 100).toFixed(2)}%` : '—';
}

function formatGap(value: number) {
  if (!Number.isFinite(value)) return '—';
  if (Math.abs(value) < 0.0001) return '\u57fa\u672c\u6301\u5e73';
  return `${value > 0 ? '\u9ad8\u4e8e' : '\u4f4e\u4e8e'} ${Math.abs(value).toFixed(4)}`;
}

function formatSigned(value: number) {
  return Number.isFinite(value) ? `${value > 0 ? '+' : ''}${value.toFixed(4)}` : '—';
}

function buildLineData(points: Array<{ year: number; value: number | null }>, anchor?: { year?: number | null; value?: number | null }) {
  const pointMap = new Map<number, number | null>(points.map((item) => [item.year, item.value]));
  return allYears.value.map((year) => {
    if (anchor?.year === year) return anchor.value ?? null;
    return pointMap.get(year) ?? null;
  });
}

function buildBandDelta(year: number, bandMap: Map<number, { min: number | null; max: number | null }>) {
  const band = bandMap.get(year);
  if (!band || band.min == null || band.max == null) return null;
  return Number((band.max - band.min).toFixed(4));
}

function buildCompareMap() {
  const entries: Array<[number, number]> = [];
  compareHistorySeriesDisplay.value.forEach((item) => {
    if (item.value != null) entries.push([item.year, item.value]);
  });
  compareFutureSeriesDisplay.value.forEach((item) => {
    if (item.value != null) entries.push([item.year, item.value]);
  });
  return new Map<number, number>(entries);
}

function updateChart() {
  if (!chart.value) return;
  if (!historySeries.value.length) {
    chart.value.setOption({
      title: {
        text: TEXT.noData,
        left: 'center',
        top: 'middle',
        textStyle: { color: '#94a3b8', fontSize: 14 },
      },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: [],
    });
    return;
  }

  const bandMap = new Map(scenarioBandDisplay.value.map((item) => [item.year, item]));
  const entityAnchor = {
    year: historySeriesDisplay.value.at(-1)?.year,
    value: historySeriesDisplay.value.at(-1)?.value ?? null,
  };
  const compareAnchor = {
    year: compareHistorySeriesDisplay.value.at(-1)?.year,
    value: compareHistorySeriesDisplay.value.at(-1)?.value ?? null,
  };
  const hideCompare = selectedLevel.value === 'province' && selectedProvince.value === TEXT.nationwide;

  const option: EChartsCoreOption = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'transparent',
      borderWidth: 0,
      padding: 0,
      renderMode: 'html',
      appendToBody: true,
      extraCssText: 'z-index:5000;',
      formatter: (params: unknown) => getCarbonPredictTooltipHtml(params, {
        firstFutureYear: FUTURE_YEARS[0],
        entityLabel: entityLabel.value,
        compareName: compareName.value,
        selectedModeLabel: selectedModeLabel.value,
        sourceModeLabel: sourceModeLabel.value,
        sourceNotice: sourceNotice.value,
        boundaryNotice: boundaryNotice.value,
        historyByYear: new Map<number, CarbonHistoryPoint>(historySeriesDisplay.value.map((item) => [item.year, item])),
        compareByYear: buildCompareMap(),
        contributionBreakdown: isCustomMode.value ? contributionBreakdown.value : null,
      }),
    },
    grid: { top: 24, right: 18, bottom: 30, left: 18, containLabel: true },
    xAxis: {
      type: 'category',
      data: allYears.value,
      axisLabel: { color: '#94a3b8', fontSize: 11, interval: 2 },
      axisLine: { lineStyle: { color: 'rgba(148,163,184,0.18)' } },
    },
    yAxis: {
      type: 'value',
      name: TEXT.chartName,
      nameTextStyle: { color: '#94a3b8', padding: [0, 0, 0, 10] },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)', type: 'dashed' } },
    },
    series: [
      {
        name: TEXT.bandLower,
        type: 'line',
        stack: 'band',
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
        tooltip: { show: false },
        data: allYears.value.map((year) => bandMap.get(year)?.min ?? null),
      },
      {
        name: TEXT.band,
        type: 'line',
        stack: 'band',
        symbol: 'none',
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(45,212,191,0.14)' },
        tooltip: { show: false },
        data: allYears.value.map((year) => buildBandDelta(year, bandMap)),
      },
      {
        name: `${entityLabel.value}${TEXT.historySuffix}`,
        type: 'line',
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#38bdf8', width: 3 },
        itemStyle: { color: '#38bdf8' },
        data: buildLineData(historySeriesDisplay.value),
      },
      {
        name: `${entityLabel.value}${TEXT.futureSuffix}`,
        type: 'line',
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { color: '#2dd4bf', width: 3, type: 'dashed' },
        itemStyle: { color: '#2dd4bf' },
        data: buildLineData(selectedFutureSeriesDisplay.value, entityAnchor),
      },
      {
        name: `${compareName.value}${TEXT.historySuffix}`,
        type: 'line',
        symbol: 'none',
        lineStyle: { color: 'rgba(203,213,225,0.42)', width: 2 },
        data: hideCompare ? [] : buildLineData(compareHistorySeriesDisplay.value),
      },
      {
        name: `${compareName.value}${TEXT.futureSuffix}`,
        type: 'line',
        symbol: 'none',
        lineStyle: { color: 'rgba(203,213,225,0.42)', width: 2, type: 'dashed' },
        data: hideCompare ? [] : buildLineData(compareFutureSeriesDisplay.value, compareAnchor),
      },
    ],
  };

  chart.value.setOption(option, true);
}

async function loadMeta() {
  try {
    const res = await getCarbonPredictMeta();
    if (res.code === 200 && res.data) {
      metaPayload.value = res.data;
      ensureSelection();
      return;
    }
    ElMessage.error(res.msg || '\u9884\u6d4b\u5143\u6570\u636e\u52a0\u8f7d\u5931\u8d25');
  } catch (error) {
    console.error(error);
    ElMessage.error('\u65e0\u6cd5\u8fde\u63a5\u9884\u6d4b\u5143\u6570\u636e\u63a5\u53e3');
  }
}

async function loadData() {
  if (!metaPayload.value) return;
  ensureSelection();
  if (selectedLevel.value === 'city' && (!selectedProvince.value || !selectedCity.value)) return;

  const seed = requestSeed + 1;
  requestSeed = seed;

  try {
    const res = await getCarbonPredictData({
      level: selectedLevel.value,
      province: selectedProvince.value,
      city: selectedLevel.value === 'city' ? selectedCity.value : undefined,
    });
    if (seed !== requestSeed) return;
    if (res.code !== 200 || !res.data) {
      ElMessage.error(res.msg || '\u9884\u6d4b\u6570\u636e\u52a0\u8f7d\u5931\u8d25');
      return;
    }
    currentData.value = res.data;
    if (selectedMode.value !== CUSTOM_MODE && !res.data.availableScenarios.includes(selectedMode.value as PredictScenarioKey)) {
      selectedMode.value = res.data.availableScenarios[0] ?? CUSTOM_MODE;
    }
    nextTick(() => updateChart());
  } catch (error) {
    if (seed !== requestSeed) return;
    console.error(error);
    ElMessage.error('\u65e0\u6cd5\u8fde\u63a5\u9884\u6d4b\u6570\u636e\u63a5\u53e3');
  }
}

function onControlInput() {
  if (selectedMode.value !== CUSTOM_MODE) {
    selectedMode.value = CUSTOM_MODE;
  }
}

function resetControls() {
  resetSdmSliderControls(controls);
}

const resizeHandler = () => chart.value?.resize();

watch([selectedLevel, selectedProvince, selectedCity], () => {
  if (!metaPayload.value) return;
  ensureSelection();
  loadData();
});

watch([selectedMode, currentData], () => nextTick(() => updateChart()));

watch(
  () => Object.values(controls).map((item) => item.value).join('|'),
  () => {
    if (selectedMode.value === CUSTOM_MODE) nextTick(() => updateChart());
  },
);

onMounted(async () => {
  await loadMeta();
  if (chartRef.value) {
    chart.value = echarts.init(chartRef.value);
    window.addEventListener('resize', resizeHandler);
    resizeObserver = new ResizeObserver(() => resizeHandler());
    resizeObserver.observe(chartRef.value);
  }
  await loadData();
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler);
  resizeObserver?.disconnect();
  resizeObserver = null;
  chart.value?.dispose();
  unregisterAiContext();
});
</script>

<style scoped lang="scss">
.predict-page { height: 100%; display: flex; flex-direction: column; gap: 14px; color: #f8fafc; }
.predict-top { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 16px; }
.predict-copy__eyebrow { color: rgba($tech-cyan, 0.84); font-size: 14px; letter-spacing: 0.16em; }
.predict-copy__title { margin-top: 6px; font-size: 24px; font-family: $font-title; color: rgba(235, 246, 255, 0.96); }
.predict-copy__desc, .predict-bar__text, .info-note { color: rgba(148, 163, 184, 0.76); font-size: 13px; line-height: 1.7; }
.predict-actions, .side, .control-list, .info-list { display: grid; gap: 12px; }
.chip-group { display: flex; flex-wrap: wrap; gap: 8px; }
.chip, .reset-btn { min-height: 36px; padding: 0 14px; border-radius: 999px; border: 1px solid rgba($tech-cyan, 0.18); background: rgba(255,255,255,0.04); color: rgba(226, 232, 240, 0.9); cursor: pointer; }
.chip.active { border-color: rgba($tech-cyan, 0.5); background: rgba($tech-cyan, 0.14); color: #fff; }
.chip.disabled, .chip:disabled, .reset-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.selector-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; min-width: 420px; }
.field { display: grid; gap: 6px; }
.field__label, .panel__title { color: rgba($tech-cyan, 0.92); font-size: 15px; }
.predict-bar { display: flex; justify-content: space-between; gap: 12px; padding: 12px 14px; border-radius: 16px; border: 1px solid rgba($tech-cyan, 0.14); background: rgba(255,255,255,0.03); }
.predict-main { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 16px; }
.panel { padding: 14px 16px; border-radius: 18px; border: 1px solid rgba($tech-cyan, 0.14); background: rgba(5,12,28,0.52); box-shadow: inset 0 0 18px rgba($tech-cyan,0.04); }
.chart-panel { display: grid; grid-template-rows: auto minmax(0, 1fr); }
.chart-meta { display: flex; flex-wrap: wrap; gap: 12px; color: rgba(148, 163, 184, 0.76); font-size: 13px; margin-bottom: 8px; }
.chart { min-height: 0; width: 100%; height: 100%; }
.side { min-height: 0; overflow-y: auto; padding-right: 4px; }
.side::-webkit-scrollbar { width: 6px; }
.side::-webkit-scrollbar-thumb { background: rgba($tech-cyan, 0.28); border-radius: 999px; }
.stat-grid, .coef-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 10px; }
.stat, .coef, .control { padding: 12px; border-radius: 14px; background: rgba(255,255,255,0.04); }
.stat--wide { grid-column: 1 / -1; }
.stat span, .coef span, .info-row span, .control__head span { color: rgba(148, 163, 184, 0.78); font-size: 13px; }
.stat b, .coef b, .info-row b, .control__head b { display: block; margin-top: 6px; color: rgba(248,250,252,0.96); font-size: 18px; font-family: $font-title; }
.stat b.positive { color: #fbbf24; }
.stat b.negative { color: #34d399; }
.coef b { color: rgba($tech-cyan, 0.94); }
.info-row { display: flex; justify-content: space-between; gap: 12px; }
.panel--disabled { opacity: 0.56; }
.control__head { display: flex; justify-content: space-between; gap: 10px; }
.control input[type='range'] { width: 100%; margin-top: 8px; appearance: none; height: 5px; border-radius: 999px; background: linear-gradient(90deg, rgba($tech-green, 0.24), rgba($tech-cyan, 0.18)); }
.control input[type='range']::-webkit-slider-thumb { appearance: none; width: 18px; height: 18px; border-radius: 50%; background: radial-gradient(circle at 35% 35%, $tech-cyan, #00bf79); box-shadow: 0 0 0 2px rgba(15,23,42,0.82), 0 0 12px rgba($tech-cyan,0.4); cursor: pointer; }
@media (max-width: 1320px) { .predict-main { grid-template-columns: minmax(0, 1fr); } .side { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 980px) { .predict-top { grid-template-columns: minmax(0, 1fr); } .selector-grid, .stat-grid, .coef-grid, .side { grid-template-columns: minmax(0, 1fr); min-width: 0; } .predict-bar { flex-direction: column; } }
</style>
