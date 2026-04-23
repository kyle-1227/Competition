<template>
  <div class="predict-page">
    <div class="predict-bar">
      <div class="predict-controls-row">
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

        <div class="predict-copy predict-copy--inline">
          <div class="predict-copy__title">碳排放强度预测 · 2000-2027</div>
        </div>

        <div class="predict-actions-right">
          <button
            type="button"
            class="export-btn"
            :disabled="!canExport"
            @click="handleExport"
          >
            导出预测结果
          </button>

          <div class="chip-group">
            <button
              v-for="item in viewModeOptions"
              :key="item.key"
              type="button"
              class="chip"
              :class="{ active: selectedViewMode === item.key, disabled: item.disabled }"
              :disabled="item.disabled"
              @click="selectedViewMode = item.key"
            >
              {{ item.label }}
            </button>
          </div>

          <div v-if="customDisabledReason" class="predict-actions-right__hint">
            {{ customDisabledReason }}
          </div>
        </div>
      </div>

      <div class="predict-meta-row">
        <div class="predict-copy__desc">
          历史观测为 2000-2024，预测展示为 2025-2027；页面统一展示组合预测，并支持自定义参数推演。
        </div>
      </div>
    </div>

    <div class="predict-main">
      <section class="panel chart-panel">
        <div class="chart-meta">
          <span>预测方法：{{ methodLabel }}</span>
          <span>当前模式：{{ selectedViewModeLabel }}</span>
          <span v-if="isCustomView">自定义基线：{{ customBaseLabel }}</span>
          <span>展示口径：{{ viewModeStatusLabel }}</span>
          <span>对比线：{{ compareName }}</span>
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
            <div v-if="isCustomView" class="stat">
              <span>基准官方 2027</span>
              <b>{{ formatNumber(baseOfficialFinalPredictionDisplay) }}</b>
            </div>
            <div class="stat stat--wide">
              <span>{{ isCustomView ? '自定义状态' : '当前模式' }}</span>
              <b>{{ modeHeadline }}</b>
            </div>
          </div>
        </section>

        <section v-if="isCustomView" class="panel">
          <div class="panel__header">
            <div class="panel__title">自定义参数</div>
            <div class="panel__actions">
              <button
                type="button"
                class="reset-btn"
                :disabled="!hasCustomDraft"
                @click="handleResetCustom"
              >
                重置参数
              </button>
            </div>
          </div>

          <div class="info-list">
            <div class="info-row"><span>调节口径</span><b>{{ customBasisLabel }}</b></div>
            <div class="info-row"><span>基线情景</span><b>{{ customBaseLabel }}</b></div>
            <div class="info-row"><span>参数状态</span><b>{{ customStatusLabel }}</b></div>
            <div v-if="customChangedSummary" class="info-note">已启用项：{{ customChangedSummary }}</div>
            <div class="info-note">
              自定义只影响当前实体未来曲线；对比线与官方情景区间保持官方组合预测结果不变。
            </div>
            <div v-if="customNotice" class="info-note">{{ customNotice }}</div>
          </div>

          <div class="control-list">
            <div
              v-for="driver in customDriverCards"
              :key="driver.key"
              class="control"
              :class="{ 'panel--disabled': !driver.active }"
            >
              <div class="control__head">
                <span>{{ driver.label }}</span>
                <b>{{ formatMultiplier(customControls[driver.key].value) }}</b>
              </div>
              <div class="control__meta">
                <span>{{ driver.active ? `弹性 ${formatSigned(driver.coefficient, 3)}` : '当前层级无有效弹性' }}</span>
                <span>{{ driver.featureLabel || '—' }}</span>
              </div>
              <input
                v-model.number="customControls[driver.key].value"
                type="range"
                :min="CUSTOM_RANGE_MIN"
                :max="CUSTOM_RANGE_MAX"
                :step="CUSTOM_RANGE_STEP"
                :disabled="!driver.active"
              >
              <div class="info-note">{{ driver.hint }}</div>
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
            <div class="info-note">{{ boundaryNotice }}</div>
          </div>
        </section>

        <section class="panel">
          <div class="panel__title">模型说明</div>
          <div class="info-list">
            <div class="info-row"><span>展示方法</span><b>{{ methodLabel }}</b></div>
            <div class="info-row"><span>当前模式</span><b>{{ selectedViewModeLabel }}</b></div>
            <div class="info-row"><span>参数依据</span><b>{{ customBasisLabel }}</b></div>
            <div class="info-note">
              页面仍然只展示组合预测结果；“自定义”是基于 STIRPAT 弹性的前端近似推演，不是后端正式重算。
            </div>
            <div v-if="hasCustomDraft && !isCustomView" class="info-note">
              已保留自定义参数草稿，切回“自定义”后会继续沿用当前设置。
            </div>
            <div class="info-note">{{ sourceNotice }}</div>
            <div v-if="customNotice" class="info-note">{{ customNotice }}</div>
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
import { GridComponent, LegendComponent, TitleComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import {
  getCarbonPredictData,
  getCarbonPredictMeta,
  type CarbonHistoryPoint,
  type CarbonPredictDataPayload,
  type CarbonPredictMetaPayload,
  type PredictCustomDriver,
  type PredictLevel,
  type PredictScenarioBandPoint,
  type PredictScenarioKey,
  type PredictSeriesPoint,
  type PredictViewMode,
} from '@/api/modules/dashboard-carbon-predict';
import { useAiAssistant } from './hooks/aiAssistant';
import { getCarbonPredictTooltipHtml } from './hooks/carbonPredictTooltipV3';
import { exportPredictCsv, type PredictExportSeriesPoint, type PredictExportSummaryRow } from './hooks/predictExport';
import {
  buildComboControlSnapshot,
  computeComboAdjustedSeries,
  createDefaultComboCustomControls,
  CUSTOM_RANGE_MAX,
  CUSTOM_RANGE_MIN,
  CUSTOM_RANGE_STEP,
  DEFAULT_DRIVER_META,
  DRIVER_KEYS,
  hasCustomAdjustments,
  resetComboCustomControls,
  summarizeChangedDrivers,
} from './hooks/useCarbonPredictComboCustom';

echarts.use([GridComponent, LegendComponent, TitleComponent, TooltipComponent, LineChart, CanvasRenderer]);

const FUTURE_YEARS = [2025, 2026, 2027];
const COMBO_SOURCE = 'combo' as const;
const CUSTOM_BASE_SCENARIO: PredictScenarioKey = 'baseline';
const OFFICIAL_SCENARIOS: PredictScenarioKey[] = ['lowCarbon', 'baseline', 'optimized'];
const VIEW_MODE_LABELS: Record<PredictViewMode, string> = {
  lowCarbon: '保守',
  baseline: '基准',
  optimized: '乐观',
  custom: '自定义',
};

const TEXT = {
  nationwide: '全国',
  nationwideLabel: '全国（样本均值）',
  compareFallback: '对比线',
  defaultBoundary: '2000-2024 为历史观测，2025-2027 为离线模型推演；官方情景区间不是统计置信区间。',
  loadingSource: '正在加载组合预测结果…',
  noData: '暂无预测数据',
  chartName: '碳排放强度',
  bandLower: '官方情景区间下界',
  band: '官方情景区间',
  historySuffix: '·历史',
  methodLabel: '组合预测',
} as const;

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

function formatNumber(value: number | null | undefined) {
  return value == null || Number.isNaN(value) ? '—' : value.toFixed(4);
}

function formatPercent(value: number) {
  return Number.isFinite(value) ? `${value > 0 ? '+' : ''}${(value * 100).toFixed(2)}%` : '—';
}

function formatGap(value: number) {
  if (!Number.isFinite(value)) return '—';
  if (Math.abs(value) < 0.0001) return '基本持平';
  return `${value > 0 ? '高于' : '低于'} ${Math.abs(value).toFixed(4)}`;
}

function formatSigned(value: number | null | undefined, digits = 2) {
  if (value == null || !Number.isFinite(value)) return '—';
  return `${value > 0 ? '+' : ''}${value.toFixed(digits)}`;
}

function formatMultiplier(value: number) {
  return `${Math.round(value * 100)}%`;
}

function toExportSeriesPoints(
  displayPoints: Array<{ year: number; value: number | null }>,
  rawPoints: Array<{ year: number; value: number | null }>,
): PredictExportSeriesPoint[] {
  const rawMap = new Map<number, number | null>(rawPoints.map((item) => [item.year, item.value]));
  return displayPoints.map((item) => ({
    year: item.year,
    displayValue: item.value,
    rawValue: rawMap.get(item.year) ?? null,
  }));
}

function buildLineData(points: Array<{ year: number; value: number | null }>, years: number[], anchor?: { year?: number | null; value?: number | null }) {
  const pointMap = new Map<number, number | null>(points.map((item) => [item.year, item.value]));
  return years.map((year) => {
    if (anchor?.year === year) return anchor.value ?? null;
    return pointMap.get(year) ?? null;
  });
}

function buildBandDelta(year: number, bandMap: Map<number, { min: number | null; max: number | null }>) {
  const band = bandMap.get(year);
  if (!band || band.min == null || band.max == null) return null;
  return Number((band.max - band.min).toFixed(4));
}

function fallbackOfficialMode(available: PredictScenarioKey[]): PredictScenarioKey {
  if (available.includes('baseline')) return 'baseline';
  if (available.includes('lowCarbon')) return 'lowCarbon';
  if (available.includes('optimized')) return 'optimized';
  return available[0] ?? 'baseline';
}

function getScenarioDisplayLabel(key: PredictScenarioKey) {
  return VIEW_MODE_LABELS[key];
}

const chartRef = ref<HTMLElement | null>(null);
const chart = shallowRef<EChartsType | null>(null);
const metaPayload = ref<CarbonPredictMetaPayload | null>(null);
const currentData = ref<CarbonPredictDataPayload | null>(null);
const selectedLevel = ref<PredictLevel>('province');
const selectedProvince = ref<string>(TEXT.nationwide);
const selectedCity = ref<string>('');
const selectedViewMode = ref<PredictViewMode>('baseline');
const customControls = reactive(createDefaultComboCustomControls());
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
const canCustomize = computed(() => Boolean(currentData.value?.supportsCustom));
const canCustomView = computed(() => canCustomize.value && availableScenarioSet.value.has(CUSTOM_BASE_SCENARIO));
const customDisabledReason = computed(() => {
  if (canCustomView.value) return '';
  if (!canCustomize.value) return '自定义需要 STIRPAT 弹性元数据';
  if (!availableScenarioSet.value.has(CUSTOM_BASE_SCENARIO)) return '自定义需要基准官方情景';
  return '自定义需要基准官方情景和 STIRPAT 弹性元数据';
});
const viewModeOptions = computed(() => ([
  { key: 'lowCarbon' as PredictViewMode, label: VIEW_MODE_LABELS.lowCarbon, disabled: !availableScenarioSet.value.has('lowCarbon') },
  { key: 'baseline' as PredictViewMode, label: VIEW_MODE_LABELS.baseline, disabled: !availableScenarioSet.value.has('baseline') },
  { key: 'optimized' as PredictViewMode, label: VIEW_MODE_LABELS.optimized, disabled: !availableScenarioSet.value.has('optimized') },
  { key: 'custom' as PredictViewMode, label: VIEW_MODE_LABELS.custom, disabled: !canCustomView.value },
]));

const entityLabel = computed(() => currentData.value?.entityLabel || (selectedLevel.value === 'city' ? selectedCity.value : selectedProvince.value));
const compareName = computed(() => currentData.value?.compareSeries.name || TEXT.compareFallback);
const methodLabel = computed(() => currentData.value?.sourceLabel || TEXT.methodLabel);
const selectedViewModeLabel = computed(() => VIEW_MODE_LABELS[selectedViewMode.value]);
const isCustomView = computed(() => selectedViewMode.value === 'custom');
const effectiveScenarioKey = computed<PredictScenarioKey>(() => (
  isCustomView.value ? CUSTOM_BASE_SCENARIO : (selectedViewMode.value as PredictScenarioKey)
));
const effectiveScenarioLabel = computed(() => getScenarioDisplayLabel(effectiveScenarioKey.value));
const customBaseLabel = computed(() => getScenarioDisplayLabel(CUSTOM_BASE_SCENARIO));
const boundaryNotice = computed(() => currentData.value?.sampleMeta.boundaryNotice || metaPayload.value?.sampleMeta.boundaryNotice || TEXT.defaultBoundary);
const sourceNotice = computed(() => currentData.value?.sourceNotice || TEXT.loadingSource);
const customNotice = computed(() => currentData.value?.customNotice || '');
const historySeries = computed(() => currentData.value?.historySeries ?? []);
const compareHistorySeries = computed(() => currentData.value?.compareSeries.historyPoints ?? []);
const scenarioBand = computed(() => currentData.value?.scenarioBand ?? []);
const allYears = computed(() => Array.from(new Set([...historySeries.value.map((item) => item.year), ...FUTURE_YEARS])).sort((left, right) => left - right));

const baseOfficialFutureSeries = computed<PredictSeriesPoint[]>(() => (
  currentData.value?.scenarios.find((item) => item.key === effectiveScenarioKey.value)?.points ?? []
));
const compareFutureSeries = computed<PredictSeriesPoint[]>(() => (
  currentData.value?.compareSeries.scenarioPoints[effectiveScenarioKey.value] ?? []
));

const customDriverCards = computed<PredictCustomDriver[]>(() => DRIVER_KEYS.map((key) => {
  const existing = currentData.value?.customDrivers.find((item) => item.key === key);
  return existing ?? {
    key,
    label: DEFAULT_DRIVER_META[key].label,
    hint: DEFAULT_DRIVER_META[key].hint,
    coefficient: 0,
    featureLabel: null,
    active: false,
  };
}));
const customChangedDrivers = computed(() => summarizeChangedDrivers(customDriverCards.value, customControls));
const hasCustomDraft = computed(() => canCustomize.value && hasCustomAdjustments(customControls, customDriverCards.value));
const customApplied = computed(() => isCustomView.value && hasCustomDraft.value);
const customChangedSummary = computed(() => customChangedDrivers.value.map((item) => `${item.label} ${formatMultiplier(item.multiplier)}`).join('、'));
const customStatusLabel = computed(() => {
  if (!canCustomView.value) return '当前层级无有效弹性';
  if (!hasCustomDraft.value) return '未调整';
  return isCustomView.value ? '已应用' : '已保存（未应用）';
});
const customStatusHeadline = computed(() => {
  if (!canCustomView.value) return '当前层级无有效弹性';
  if (!hasCustomDraft.value) return '自定义未调整（与基准重合）';
  return `已应用（${customChangedSummary.value}）`;
});
const customBasisLabel = computed(() => {
  if (currentData.value?.customBasis === 'stirpat') return 'STIRPAT 弹性';
  return '组合预测官方值';
});
const viewModeStatusLabel = computed(() => {
  if (!isCustomView.value) return `官方${selectedViewModeLabel.value}情景`;
  return customApplied.value ? '自定义调节已应用' : '自定义未调整';
});
const modeHeadline = computed(() => (
  isCustomView.value ? customStatusHeadline.value : `官方${selectedViewModeLabel.value}情景`
));
const currentFutureSeries = computed<PredictSeriesPoint[]>(() => {
  if (!isCustomView.value) return baseOfficialFutureSeries.value;
  return computeComboAdjustedSeries(
    baseOfficialFutureSeries.value,
    currentData.value?.stirpatElasticities ?? null,
    customControls,
    customDriverCards.value,
  );
});

const entityLegendBase = computed(() => {
  if (selectedLevel.value === 'city') return `${entityLabel.value}（当前城市）`;
  if (selectedProvince.value === TEXT.nationwide) return TEXT.nationwide;
  return `${entityLabel.value}（当前省份）`;
});
const compareLegendBase = computed(() => {
  if (selectedLevel.value === 'city') return `${compareName.value}（所属省市级均值）`;
  return `${compareName.value}（全国均值）`;
});
const entityHistoryLegend = computed(() => `${entityLegendBase.value}${TEXT.historySuffix}`);
const entityOfficialFutureLegend = computed(() => (
  isCustomView.value
    ? `${entityLegendBase.value}·${customBaseLabel.value}官方预测`
    : `${entityLegendBase.value}·${selectedViewModeLabel.value}`
));
const entityCustomFutureLegend = computed(() => `${entityLegendBase.value}·自定义调节`);
const compareHistoryLegend = computed(() => `${compareLegendBase.value}${TEXT.historySuffix}`);
const compareFutureLegend = computed(() => (
  isCustomView.value
    ? `${compareLegendBase.value}·${customBaseLabel.value}官方预测`
    : `${compareLegendBase.value}·${selectedViewModeLabel.value}`
));

const latestObserved = computed(() => historySeries.value.at(-1)?.value ?? 0);
const finalPrediction = computed(() => currentFutureSeries.value.at(-1)?.value ?? latestObserved.value);
const baseOfficialFinalPrediction = computed(() => baseOfficialFutureSeries.value.at(-1)?.value ?? latestObserved.value);
const compareFinal = computed(() => compareFutureSeries.value.at(-1)?.value ?? compareHistorySeries.value.at(-1)?.value ?? 0);
const compareGap = computed(() => finalPrediction.value - compareFinal.value);
const changePct = computed(() => (latestObserved.value ? (finalPrediction.value - latestObserved.value) / Math.abs(latestObserved.value) : 0));

const historySeriesDisplay = computed(() => toDisplayHistorySeries(historySeries.value));
const compareHistorySeriesDisplay = computed(() => toDisplaySeries(compareHistorySeries.value));
const currentFutureSeriesDisplay = computed(() => toDisplaySeries(currentFutureSeries.value));
const baseOfficialFutureSeriesDisplay = computed(() => toDisplaySeries(baseOfficialFutureSeries.value));
const compareFutureSeriesDisplay = computed(() => toDisplaySeries(compareFutureSeries.value));
const scenarioBandDisplay = computed(() => scenarioBand.value.map(toDisplayBandPoint));
const latestObservedDisplay = computed(() => toDisplayCarbonIntensity(latestObserved.value) ?? 0);
const finalPredictionDisplay = computed(() => currentFutureSeriesDisplay.value.at(-1)?.value ?? latestObservedDisplay.value);
const baseOfficialFinalPredictionDisplay = computed(() => baseOfficialFutureSeriesDisplay.value.at(-1)?.value ?? latestObservedDisplay.value);
const compareFinalDisplay = computed(() => compareFutureSeriesDisplay.value.at(-1)?.value ?? compareHistorySeriesDisplay.value.at(-1)?.value ?? 0);
const compareGapDisplay = computed(() => finalPredictionDisplay.value - compareFinalDisplay.value);
const changePctDisplay = computed(() => (
  latestObservedDisplay.value
    ? (finalPredictionDisplay.value - latestObservedDisplay.value) / Math.abs(latestObservedDisplay.value)
    : 0
));

const directionLabel = computed(() => {
  if (Math.abs(changePctDisplay.value) < 0.01) return '基本持平';
  return changePctDisplay.value > 0 ? '上升' : '下降';
});
const changeClass = computed(() => ({
  positive: changePctDisplay.value > 0.01,
  negative: changePctDisplay.value < -0.01,
}));
const canExport = computed(() => {
  if (!currentData.value) return false;
  if (selectedLevel.value === 'city' && !selectedCity.value) return false;
  return historySeries.value.length > 0 || currentFutureSeries.value.length > 0;
});
const sampleRange = computed(() => `${currentData.value?.sampleMeta.historyStartYear ?? '—'} - ${currentData.value?.sampleMeta.historyEndYear ?? '—'}`);
const forecastRange = computed(() => `${currentData.value?.sampleMeta.forecastStartYear ?? '—'} - ${currentData.value?.sampleMeta.forecastEndYear ?? '—'}`);

const unregisterAiContext = registerPageContext('energy', () => ({
  year: currentData.value?.sampleMeta.forecastEndYear ?? FUTURE_YEARS[2],
  selectedProvince: selectedProvince.value,
  drillProvince: selectedLevel.value === 'city' ? selectedProvince.value : undefined,
  drillCity: selectedLevel.value === 'city' ? selectedCity.value : undefined,
  snapshot: {
    level: selectedLevel.value,
    source: COMBO_SOURCE,
    sourceLabel: methodLabel.value,
    province: selectedProvince.value,
    city: selectedLevel.value === 'city' ? selectedCity.value : null,
    selectedViewMode: selectedViewMode.value,
    selectedViewLabel: selectedViewModeLabel.value,
    selectedScenarioKey: effectiveScenarioKey.value,
    selectedScenarioLabel: effectiveScenarioLabel.value,
    customBaseScenarioKey: isCustomView.value ? CUSTOM_BASE_SCENARIO : null,
    customBaseScenarioLabel: isCustomView.value ? customBaseLabel.value : null,
    availableScenarios: currentData.value?.availableScenarios ?? [],
    sourceMode: methodLabel.value,
    sourceNotice: sourceNotice.value,
    isCustomView: isCustomView.value,
    customDraftEnabled: hasCustomDraft.value,
    customApplied: customApplied.value,
    customBasis: currentData.value?.customBasis ?? null,
    customNotice: customNotice.value || null,
    customControlSnapshot: buildComboControlSnapshot(customControls),
    customChangedDrivers: customChangedDrivers.value.map((item) => ({
      key: item.key,
      label: item.label,
      multiplier: Number(item.multiplier.toFixed(2)),
      coefficient: item.coefficient,
    })),
    customSummary: customChangedSummary.value || null,
    displayValueMode: 'absoluteCarbonIntensityRawForecast',
    displayValueNote: '页面展示的碳排放强度保持绝对值口径；自定义仅作用于当前实体未来曲线，对比线和官方情景区间保持官方组合预测结果。',
    compareSummary: `${selectedViewModeLabel.value}下，${entityLabel.value} 相对 ${compareName.value}${formatGap(compareGapDisplay.value)}。`,
    compareGap: toRoundedNumber(compareGapDisplay.value),
    scenarioBand: scenarioBandDisplay.value.map((item) => ({ ...item })),
    sampleMeta: currentData.value?.sampleMeta ?? null,
    boundaryNotice: boundaryNotice.value,
    entityLabel: entityLabel.value,
    finalPrediction: toRoundedNumber(finalPredictionDisplay.value),
    officialFinalPrediction: toRoundedNumber(baseOfficialFinalPredictionDisplay.value),
    predictionChangePct: toRoundedNumber(changePctDisplay.value * 100, 2),
    historySeries: historySeriesDisplay.value.map((item) => ({ year: item.year, value: item.value })),
    currentFutureSeries: currentFutureSeriesDisplay.value.map((item) => ({ ...item })),
    officialCurrentFutureSeries: baseOfficialFutureSeriesDisplay.value.map((item) => ({ ...item })),
    rawFinalPrediction: toRoundedNumber(finalPrediction.value),
    rawOfficialFinalPrediction: toRoundedNumber(baseOfficialFinalPrediction.value),
    rawPredictionChangePct: toRoundedNumber(changePct.value * 100, 2),
    rawCompareGap: toRoundedNumber(compareGap.value),
    rawHistorySeries: historySeries.value.map((item) => ({ year: item.year, value: item.value })),
    rawCurrentFutureSeries: currentFutureSeries.value.map((item) => ({ ...item })),
    rawOfficialCurrentFutureSeries: baseOfficialFutureSeries.value.map((item) => ({ ...item })),
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

function handleResetCustom() {
  resetComboCustomControls(customControls);
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

  const years = allYears.value;
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
  const legendItems = [
    entityHistoryLegend.value,
    ...(isCustomView.value ? [entityOfficialFutureLegend.value, entityCustomFutureLegend.value] : [entityOfficialFutureLegend.value]),
    ...(hideCompare ? [] : [compareHistoryLegend.value, compareFutureLegend.value]),
    TEXT.band,
  ];

  const series: EChartsCoreOption['series'] = [
    {
      name: TEXT.bandLower,
      type: 'line',
      stack: 'band',
      symbol: 'none',
      lineStyle: { opacity: 0 },
      areaStyle: { opacity: 0 },
      tooltip: { show: false },
      data: years.map((year) => bandMap.get(year)?.min ?? null),
    },
    {
      name: TEXT.band,
      type: 'line',
      stack: 'band',
      symbol: 'none',
      lineStyle: { opacity: 0 },
      areaStyle: { color: 'rgba(45,212,191,0.14)' },
      tooltip: { show: false },
      data: years.map((year) => buildBandDelta(year, bandMap)),
    },
    {
      name: entityHistoryLegend.value,
      type: 'line',
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#38bdf8', width: 3 },
      itemStyle: { color: '#38bdf8' },
      data: buildLineData(historySeriesDisplay.value, years),
    },
    ...(isCustomView.value
      ? [
          {
            name: entityOfficialFutureLegend.value,
            type: 'line',
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: { color: '#22d3ee', width: 2, type: 'dashed' },
            itemStyle: { color: '#22d3ee' },
            data: buildLineData(baseOfficialFutureSeriesDisplay.value, years, entityAnchor),
          },
          {
            name: entityCustomFutureLegend.value,
            type: 'line',
            symbol: 'circle',
            symbolSize: 7,
            lineStyle: { color: '#2dd4bf', width: 3 },
            itemStyle: { color: '#2dd4bf' },
            data: buildLineData(currentFutureSeriesDisplay.value, years, entityAnchor),
          },
        ]
      : [
          {
            name: entityOfficialFutureLegend.value,
            type: 'line',
            symbol: 'circle',
            symbolSize: 7,
            lineStyle: { color: '#2dd4bf', width: 3, type: 'dashed' },
            itemStyle: { color: '#2dd4bf' },
            data: buildLineData(currentFutureSeriesDisplay.value, years, entityAnchor),
          },
        ]),
    {
      name: compareHistoryLegend.value,
      type: 'line',
      symbol: 'none',
      lineStyle: { color: 'rgba(203,213,225,0.42)', width: 2 },
      data: hideCompare ? [] : buildLineData(compareHistorySeriesDisplay.value, years),
    },
    {
      name: compareFutureLegend.value,
      type: 'line',
      symbol: 'none',
      lineStyle: { color: 'rgba(203,213,225,0.42)', width: 2, type: 'dashed' },
      data: hideCompare ? [] : buildLineData(compareFutureSeriesDisplay.value, years, compareAnchor),
    },
  ];

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
        viewModeLabel: selectedViewModeLabel.value,
        methodLabel: methodLabel.value,
        sourceNotice: sourceNotice.value,
        boundaryNotice: boundaryNotice.value,
        isCustomView: isCustomView.value,
        customBaseLabel: isCustomView.value ? customBaseLabel.value : null,
        customApplied: customApplied.value,
        customSummary: customChangedSummary.value || null,
        preferredEntitySeriesName: isCustomView.value ? entityCustomFutureLegend.value : entityOfficialFutureLegend.value,
        historyByYear: new Map<number, CarbonHistoryPoint>(historySeriesDisplay.value.map((item) => [item.year, item])),
        compareByYear: buildCompareMap(),
      }),
    },
    legend: {
      top: 0,
      left: 18,
      right: 18,
      itemWidth: 18,
      itemHeight: 10,
      textStyle: {
        color: 'rgba(226,232,240,0.88)',
        fontSize: 12,
      },
      data: legendItems,
    },
    grid: { top: 72, right: 18, bottom: 30, left: 18, containLabel: true },
    xAxis: {
      type: 'category',
      data: years,
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
    series,
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
    ElMessage.error(res.msg || '预测元数据加载失败');
  } catch (error) {
    console.error(error);
    ElMessage.error('无法连接预测元数据接口');
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
      source: COMBO_SOURCE,
      province: selectedProvince.value,
      city: selectedLevel.value === 'city' ? selectedCity.value : undefined,
    });
    if (seed !== requestSeed) return;
    if (res.code !== 200 || !res.data) {
      ElMessage.error(res.msg || '预测数据加载失败');
      return;
    }

    currentData.value = res.data;
    if (selectedViewMode.value === 'custom') {
      if (!res.data.supportsCustom || !res.data.availableScenarios.includes(CUSTOM_BASE_SCENARIO)) {
        selectedViewMode.value = fallbackOfficialMode(res.data.availableScenarios);
      }
    } else if (!res.data.availableScenarios.includes(selectedViewMode.value)) {
      selectedViewMode.value = fallbackOfficialMode(res.data.availableScenarios);
    }
    nextTick(() => updateChart());
  } catch (error) {
    if (seed !== requestSeed) return;
    console.error(error);
    ElMessage.error('无法连接预测数据接口');
  }
}

function buildSummaryRows(): PredictExportSummaryRow[] {
  const rows: PredictExportSummaryRow[] = [
    {
      label: '2027预测值',
      year: currentData.value?.sampleMeta.forecastEndYear ?? '',
      displayValue: finalPredictionDisplay.value,
      rawValue: finalPrediction.value,
      unit: '吨/万元',
    },
    {
      label: '较2024变化',
      year: currentData.value?.sampleMeta.forecastEndYear ?? '',
      displayValue: Number((changePctDisplay.value * 100).toFixed(2)),
      rawValue: Number((changePct.value * 100).toFixed(2)),
      unit: '%',
    },
    {
      label: '变化方向',
      year: currentData.value?.sampleMeta.forecastEndYear ?? '',
      displayValue: directionLabel.value,
      rawValue: '',
      unit: '',
    },
    {
      label: '相对对比线差距',
      year: currentData.value?.sampleMeta.forecastEndYear ?? '',
      displayValue: compareGapDisplay.value,
      rawValue: compareGap.value,
      unit: '同图表展示口径',
    },
    {
      label: '当前模式',
      displayValue: selectedViewModeLabel.value,
      rawValue: effectiveScenarioKey.value,
      unit: '',
    },
    {
      label: '预测方法',
      displayValue: methodLabel.value,
      rawValue: '',
      unit: '',
      note: sourceNotice.value,
    },
    {
      label: '样本期',
      displayValue: sampleRange.value,
      rawValue: '',
      unit: '',
    },
    {
      label: '预测期',
      displayValue: forecastRange.value,
      rawValue: '',
      unit: '',
    },
    {
      label: '边界说明',
      displayValue: boundaryNotice.value,
      rawValue: '',
      unit: '',
    },
  ];

  if (isCustomView.value) {
    rows.splice(1, 0,
      {
        label: '基准官方2027',
        year: currentData.value?.sampleMeta.forecastEndYear ?? '',
        displayValue: baseOfficialFinalPredictionDisplay.value,
        rawValue: baseOfficialFinalPrediction.value,
        unit: '吨/万元',
        note: '基准官方曲线，未叠加自定义调节。',
      },
      {
        label: '自定义状态',
        displayValue: customStatusLabel.value,
        rawValue: customChangedSummary.value || '',
        unit: '',
        note: customNotice.value || '',
      },
    );

    customDriverCards.value.forEach((driver) => {
      rows.push({
        label: `参数-${driver.label}`,
        displayValue: formatMultiplier(customControls[driver.key].value),
        rawValue: Number(customControls[driver.key].value.toFixed(2)),
        unit: '',
        note: driver.active ? `弹性 ${formatSigned(driver.coefficient, 3)} / ${driver.featureLabel || 'STIRPAT'}` : '当前层级无有效弹性',
      });
    });
  }

  return rows;
}

function handleExport() {
  if (!canExport.value || !currentData.value) {
    ElMessage.warning('当前暂无可导出的预测结果');
    return;
  }

  try {
    const hideCompare = selectedLevel.value === 'province' && selectedProvince.value === TEXT.nationwide;
    const exportFilename = exportPredictCsv({
      level: selectedLevel.value,
      province: selectedProvince.value,
      city: selectedLevel.value === 'city' ? selectedCity.value : null,
      entityLabel: entityLabel.value,
      compareLabel: compareName.value,
      target: 'carbonIntensity',
      selectedMode: selectedViewMode.value,
      selectedModeLabel: selectedViewModeLabel.value,
      methodLabel: methodLabel.value,
      historySeries: toExportSeriesPoints(historySeriesDisplay.value, historySeries.value),
      scenarios: OFFICIAL_SCENARIOS
        .map((key) => {
          const scenario = currentData.value?.scenarios.find((item) => item.key === key);
          if (!scenario) return null;
          return {
            key: scenario.key,
            label: getScenarioDisplayLabel(scenario.key),
            points: toExportSeriesPoints(toDisplaySeries(scenario.points), scenario.points),
          };
        })
        .filter((item): item is NonNullable<typeof item> => Boolean(item)),
      selectedModeSeries: {
        key: selectedViewMode.value,
        label: isCustomView.value ? '自定义调节曲线' : `${selectedViewModeLabel.value}·当前展示`,
        points: toExportSeriesPoints(currentFutureSeriesDisplay.value, currentFutureSeries.value),
      },
      officialSelectedModeSeries: isCustomView.value
        ? {
            key: `${CUSTOM_BASE_SCENARIO}_official`,
            label: `${customBaseLabel.value}·官方组合预测`,
            points: toExportSeriesPoints(baseOfficialFutureSeriesDisplay.value, baseOfficialFutureSeries.value),
          }
        : null,
      compareHistorySeries: hideCompare ? [] : toExportSeriesPoints(compareHistorySeriesDisplay.value, compareHistorySeries.value),
      compareSelectedModeSeries: hideCompare ? [] : toExportSeriesPoints(compareFutureSeriesDisplay.value, compareFutureSeries.value),
      scenarioBand: scenarioBandDisplay.value.map((item) => {
        const rawBand = scenarioBand.value.find((raw) => raw.year === item.year);
        return {
          year: item.year,
          displayMin: item.min,
          displayMax: item.max,
          rawMin: rawBand?.min ?? null,
          rawMax: rawBand?.max ?? null,
        };
      }),
      summaryRows: buildSummaryRows(),
    });
    ElMessage.success(`预测结果已导出：${exportFilename}`);
  } catch (error) {
    console.error(error);
    ElMessage.error('导出预测结果失败');
  }
}

const resizeHandler = () => chart.value?.resize();

watch(selectedLevel, () => {
  if (!metaPayload.value) return;
  ensureSelection();
  loadData();
});

watch(selectedProvince, () => {
  if (!metaPayload.value) return;
  if (selectedLevel.value === 'city') {
    const cities = metaPayload.value.citiesByProvince[selectedProvince.value] ?? [];
    if (!cities.includes(selectedCity.value)) {
      selectedCity.value = cities[0] || '';
      return;
    }
  }
  loadData();
});

watch(selectedCity, () => {
  if (!metaPayload.value || selectedLevel.value !== 'city') return;
  loadData();
});

watch([selectedViewMode, currentData, currentFutureSeries, baseOfficialFutureSeries, compareFutureSeries], () => nextTick(() => updateChart()));

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
.predict-copy { display: grid; justify-items: center; text-align: center; }
.predict-copy--inline { align-self: center; min-width: 0; padding: 0 6px; }
.predict-copy__title {
  margin-top: 0;
  font-size: clamp(18px, 1.1vw, 22px);
  font-family: $font-title;
  color: rgba($tech-cyan, 0.88);
  line-height: 1.1;
  letter-spacing: 0.14em;
  text-shadow: 0 0 10px rgba($tech-cyan, 0.16);
  white-space: nowrap;
}
.predict-copy__desc, .info-note { color: rgba(148, 163, 184, 0.76); font-size: 13px; line-height: 1.7; }
.predict-copy__desc {
  color: rgba(200, 220, 255, 0.4);
  font-size: 14px;
  letter-spacing: 0.04em;
  line-height: 1.5;
  text-align: center;
  white-space: nowrap;
  justify-self: center;
}
.predict-actions, .side, .control-list, .info-list, .predict-actions-right { display: grid; gap: 12px; }
.predict-actions { display: flex; align-items: end; justify-content: flex-start; gap: 12px; width: auto; min-width: 0; }
.predict-actions-right { justify-items: end; align-self: end; min-width: 0; }
.predict-actions-right__hint {
  max-width: min(360px, 100%);
  color: rgba(248, 113, 113, 0.82);
  font-size: 12px;
  line-height: 1.5;
  text-align: right;
}
.predict-actions .chip-group, .predict-bar .chip-group { display: flex; flex-wrap: nowrap; gap: 8px; }
.predict-actions-right .chip-group { justify-content: flex-end; }
.predict-controls-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: end;
  gap: 18px;
}
.chip-group { display: flex; flex-wrap: wrap; gap: 8px; }
.chip, .reset-btn, .export-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba($tech-cyan, 0.18);
  background: rgba(255,255,255,0.04);
  color: rgba(226, 232, 240, 0.9);
  cursor: pointer;
}
.chip.active { border-color: rgba($tech-cyan, 0.5); background: rgba($tech-cyan, 0.14); color: #fff; }
.export-btn {
  min-width: 138px;
  border-color: rgba($tech-cyan, 0.42);
  background: linear-gradient(135deg, rgba($tech-cyan, 0.16), rgba(45, 212, 191, 0.08));
  box-shadow: 0 0 16px rgba($tech-cyan, 0.12);
}
.chip.disabled, .chip:disabled, .reset-btn:disabled, .export-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.selector-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; min-width: 420px; }
.field { display: grid; gap: 6px; }
.field__label, .panel__title { color: rgba($tech-cyan, 0.92); font-size: 15px; }
.field :deep(.el-select__wrapper) {
  min-height: 40px;
  border-radius: 10px;
  background: rgba(8, 17, 36, 0.78);
  border: 1px solid rgba($tech-cyan, 0.26);
  box-shadow:
    inset 0 0 16px rgba($tech-cyan, 0.05),
    0 0 0 1px rgba(255, 255, 255, 0.02);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}
.field :deep(.el-select__wrapper.is-focused),
.field :deep(.el-select__wrapper:hover) {
  background: rgba(10, 22, 46, 0.92);
  border-color: rgba($tech-cyan, 0.62);
  box-shadow:
    0 0 18px rgba($tech-cyan, 0.18),
    inset 0 0 18px rgba($tech-cyan, 0.08);
}
.field :deep(.el-select__placeholder),
.field :deep(.el-select__selected-item) {
  color: rgba(235, 246, 255, 0.92);
  font-size: 15px;
  font-weight: 600;
}
.field :deep(.el-select__caret) { color: rgba($tech-cyan, 0.78); }
.predict-bar { display: grid; gap: 10px; padding: 12px 14px; border-radius: 16px; border: 1px solid rgba($tech-cyan, 0.14); background: rgba(255,255,255,0.03); }
.predict-meta-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: center;
  gap: 16px;
}
.predict-main { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 16px; }
.panel {
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba($tech-cyan, 0.14);
  background: rgba(5,12,28,0.52);
  box-shadow: inset 0 0 18px rgba($tech-cyan,0.04);
}
.panel__header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.panel__actions { display: flex; flex-wrap: wrap; gap: 8px; }
.chart-panel { display: grid; grid-template-rows: auto minmax(0, 1fr); }
.chart-meta { display: flex; flex-wrap: wrap; gap: 12px; color: rgba(148, 163, 184, 0.76); font-size: 13px; margin-bottom: 8px; }
.chart { min-height: 0; width: 100%; height: 100%; }
.side { min-height: 0; overflow-y: auto; padding-right: 4px; }
.side::-webkit-scrollbar { width: 6px; }
.side::-webkit-scrollbar-thumb { background: rgba($tech-cyan, 0.28); border-radius: 999px; }
.stat-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 10px; }
.stat, .control { padding: 12px; border-radius: 14px; background: rgba(255,255,255,0.04); }
.stat--wide { grid-column: 1 / -1; }
.stat span, .info-row span, .control__head span, .control__meta span {
  color: rgba(148, 163, 184, 0.78);
  font-size: 13px;
}
.stat b, .info-row b, .control__head b {
  display: block;
  margin-top: 6px;
  color: rgba(248,250,252,0.96);
  font-size: 18px;
  font-family: $font-title;
}
.stat b.positive { color: #fbbf24; }
.stat b.negative { color: #34d399; }
.info-row { display: flex; justify-content: space-between; gap: 12px; }
.panel--disabled { opacity: 0.56; }
.control__head { display: flex; justify-content: space-between; gap: 10px; align-items: start; }
.control__meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 4px;
  font-size: 12px;
}
.control input[type='range'] {
  width: 100%;
  margin-top: 8px;
  appearance: none;
  height: 5px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba($tech-green, 0.24), rgba($tech-cyan, 0.18));
}
.control input[type='range']::-webkit-slider-thumb {
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, $tech-cyan, #00bf79);
  box-shadow: 0 0 0 2px rgba(15,23,42,0.82), 0 0 12px rgba($tech-cyan,0.4);
  cursor: pointer;
}
@media (max-width: 1320px) {
  .predict-main { grid-template-columns: minmax(0, 1fr); }
  .side { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 980px) {
  .predict-controls-row { grid-template-columns: minmax(0, 1fr); }
  .predict-meta-row { grid-template-columns: minmax(0, 1fr); }
  .predict-actions, .predict-actions-right { justify-self: stretch; }
  .predict-actions, .predict-actions-right { justify-items: stretch; }
  .predict-actions { flex-direction: column; align-items: stretch; }
  .predict-copy--inline { order: -1; padding: 0; }
  .predict-copy__desc { grid-column: auto; justify-self: stretch; max-width: none; text-align: left; white-space: normal; }
  .predict-actions-right__hint { justify-self: stretch; max-width: none; text-align: left; }
  .predict-actions .chip-group, .predict-bar .chip-group { flex-wrap: wrap; }
  .predict-actions-right .chip-group { justify-content: flex-start; }
  .selector-grid, .stat-grid, .side { grid-template-columns: minmax(0, 1fr); min-width: 0; }
  .panel__header { flex-direction: column; align-items: stretch; }
}
</style>

<style lang="scss">
.dark-popper.el-select__popper {
  border: 1px solid rgba($tech-cyan, 0.28);
  border-radius: 10px;
  background: rgba(8, 17, 36, 0.96);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.42), 0 0 18px rgba($tech-cyan, 0.12);

  .el-popper__arrow::before {
    background: rgba(8, 17, 36, 0.96);
    border-color: rgba($tech-cyan, 0.28);
  }

  .el-select-dropdown {
    background: transparent;
  }

  .el-select-dropdown__item {
    color: rgba(226, 232, 240, 0.82);
    font-weight: 600;

    &.hover,
    &:hover {
      background: rgba($tech-cyan, 0.12);
      color: #fff;
    }

    &.selected {
      color: $tech-cyan;
      background: rgba($tech-cyan, 0.08);
    }
  }
}
</style>
