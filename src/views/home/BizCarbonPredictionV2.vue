<template>
  <div class="predict-page">
    <div class="predict-top">
      <div>
        <div class="predict-top__eyebrow">碳排放强度预测</div>
        <div class="predict-top__title">历史观测 + 三情景推演 + 自定义沙盘</div>
        <div class="predict-top__desc">{{ boundaryNotice }}</div>
      </div>

      <div class="predict-top__actions">
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

        <div class="selectors">
          <div class="field">
            <span>{{ selectedLevel === 'province' ? '分析区域' : '所属省份' }}</span>
            <el-select v-model="selectedProvince" popper-class="dark-popper">
              <el-option
                v-for="item in provinceOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </div>
          <div v-if="selectedLevel === 'city'" class="field">
            <span>地级市</span>
            <el-select v-model="selectedCity" popper-class="dark-popper" :disabled="!cityOptions.length">
              <el-option v-for="city in cityOptions" :key="city" :label="city" :value="city" />
            </el-select>
          </div>
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
          <span>对比线：{{ compareSeriesName }}</span>
          <span>权重类型：{{ currentData?.weightType || '—' }}</span>
        </div>
        <div ref="chartRef" class="chart" />
      </section>

      <aside class="side">
        <section class="panel">
          <div class="panel__title">{{ currentEntityLabel }} · 2027 结论卡</div>
          <div class="stat-grid">
            <div class="stat">
              <span>2027 预测值</span>
              <b>{{ formatMetric(finalPrediction) }}</b>
            </div>
            <div class="stat">
              <span>较 2024 变化</span>
              <b :class="predictionChangeClass">{{ formatPercent(predictionChangePct) }}</b>
            </div>
            <div class="stat">
              <span>变化方向</span>
              <b>{{ directionLabel }}</b>
            </div>
            <div class="stat">
              <span>相对对比线</span>
              <b>{{ formatGap(compareGap) }}</b>
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
            <div class="info-row"><span>样本期</span><b>{{ sampleRangeText }}</b></div>
            <div class="info-row"><span>预测期</span><b>{{ forecastRangeText }}</b></div>
            <div class="info-row"><span>覆盖数量</span><b>{{ currentData?.sampleMeta.coverageCount ?? 0 }}</b></div>
            <div class="info-note">{{ currentData?.sampleMeta.coverageNote || '—' }}</div>
          </div>
        </section>

        <section class="panel">
          <div class="panel__title">模型说明</div>
          <div class="coef-grid">
            <div class="coef"><span>gfi_std</span><b>{{ formatMetric(modelCoefficients.core) }}</b></div>
            <div class="coef"><span>能源相关</span><b>{{ formatMetric(modelCoefficients.control) }}</b></div>
            <div class="coef"><span>W_gfi_std</span><b>{{ formatMetric(modelCoefficients.spatial) }}</b></div>
            <div class="coef"><span>rho</span><b>{{ formatMetric(modelCoefficients.rho) }}</b></div>
          </div>
          <div class="info-note">系数表示模型关系，不等同于绝对因果。</div>
        </section>

        <section v-if="isCustomMode" class="panel">
          <div class="panel__title">参数贡献估算</div>
          <div class="info-list">
            <div class="info-row"><span>基准趋势</span><b>{{ formatContribution(contributionBreakdown.baselineTrend) }}</b></div>
            <div v-for="item in contributionItems" :key="item.key" class="info-row">
              <span>{{ item.label }}</span>
              <b>{{ formatContribution(item.value) }}</b>
            </div>
          </div>
        </section>

        <section class="panel" :class="{ 'panel--disabled': !isCustomMode }">
          <div class="panel__title">
            自定义参数
            <button type="button" class="reset-btn" :disabled="!isCustomMode" @click="handleResetControls">重置参数</button>
          </div>
          <div class="control-list">
            <div v-for="(control, key) in controls" :key="key" class="control">
              <div class="control__head">
                <span>{{ control.name }}</span>
                <b>{{ Math.round(control.value * 100) }}%</b>
              </div>
              <div class="control__hint">{{ control.hint }}</div>
              <input v-model.number="control.value" type="range" min="0.5" max="1.5" step="0.05" :disabled="!isCustomMode" @input="handleControlInput">
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
  type CarbonPredictDataPayload,
  type CarbonPredictMetaPayload,
  type PredictLevel,
  type PredictScenarioKey,
  type PredictSeriesPoint,
  type PredictViewMode,
} from '@/api/modules/dashboard-carbon-predict';
import { useAiAssistant } from './hooks/aiAssistant';
import { getCarbonPredictTooltipHtml } from './hooks/carbonPredictTooltipV2';
import {
  computeContributionBreakdown,
  computeSdmPredictedSeries,
  createDefaultSdmSliderControls,
  resetSdmSliderControls,
  type SdmCoefficients,
} from './hooks/useCarbonPredictV2';

echarts.use([GridComponent, TitleComponent, TooltipComponent, LineChart, CanvasRenderer]);

const FUTURE_YEARS = [2025, 2026, 2027];
const CUSTOM_MODE: PredictViewMode = 'custom';
const chartRef = ref<HTMLElement | null>(null);
const chart = shallowRef<EChartsType | null>(null);
const metaPayload = ref<CarbonPredictMetaPayload | null>(null);
const currentData = ref<CarbonPredictDataPayload | null>(null);
const selectedLevel = ref<PredictLevel>('province');
const selectedProvince = ref('全国');
const selectedCity = ref('');
const selectedMode = ref<PredictViewMode>('baseline');
const controls = reactive(createDefaultSdmSliderControls());
const { registerPageContext } = useAiAssistant();
let requestSeed = 0;
let resizeObserver: ResizeObserver | null = null;

const levelOptions = computed(() => metaPayload.value?.levels ?? []);
const provinceOptions = computed(() => {
  const provinces = metaPayload.value?.provinces ?? [];
  return selectedLevel.value === 'province'
    ? [{ value: '全国', label: '全国（样本均值）' }, ...provinces.map((item) => ({ value: item, label: item }))]
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
  { key: CUSTOM_MODE, label: '自定义', disabled: false },
]);
const currentEntityLabel = computed(() => currentData.value?.entityLabel || (selectedLevel.value === 'city' ? selectedCity.value : selectedProvince.value));
const compareSeriesName = computed(() => currentData.value?.compareSeries.name || '对比线');
const selectedModeLabel = computed(() => selectedMode.value === CUSTOM_MODE ? '自定义' : metaPayload.value?.scenarios.find((item) => item.key === selectedMode.value)?.label ?? '基准');
const sourceModeLabel = computed(() => selectedMode.value === CUSTOM_MODE ? '自定义参数推演' : '离线情景结果');
const boundaryNotice = computed(() => currentData.value?.sampleMeta.boundaryNotice || metaPayload.value?.sampleMeta.boundaryNotice || '2000-2024 为历史观测，2025-2027 为模型推演；情景区间不是统计置信区间。');
const sourceNotice = computed(() => currentData.value?.sourceNotice || '正在加载预测结果…');
const historySeries = computed(() => currentData.value?.historySeries ?? []);
const allYears = computed(() => [...historySeries.value.map((item) => item.year), ...FUTURE_YEARS]);
const modelCoefficients = computed<SdmCoefficients>(() => ({
  core: currentData.value?.coefficients.core ?? 0,
  control: currentData.value?.coefficients.control ?? 0,
  policy: currentData.value?.coefficients.policy ?? 0,
  spatial: currentData.value?.coefficients.spatial ?? 0,
  mediator: currentData.value?.coefficients.mediator ?? 0,
  rho: currentData.value?.coefficients.rho ?? 0,
}));
const customFuture = computed(() => computeSdmPredictedSeries(historySeries.value.map((item) => item.value), modelCoefficients.value, controls, FUTURE_YEARS.length));
const compareCustomFuture = computed(() => computeSdmPredictedSeries((currentData.value?.compareSeries.historyPoints ?? []).map((item) => item.value ?? 0), modelCoefficients.value, controls, FUTURE_YEARS.length));
const selectedFutureSeries = computed(() => selectedMode.value === CUSTOM_MODE
  ? FUTURE_YEARS.map((year, index) => ({ year, value: customFuture.value[index] ?? null }))
  : currentData.value?.scenarios.find((item) => item.key === selectedMode.value)?.points ?? []);
const compareFutureSeries = computed(() => {
  if (selectedMode.value === CUSTOM_MODE) {
    return FUTURE_YEARS.map((year, index) => ({ year, value: compareCustomFuture.value[index] ?? null }));
  }
  return currentData.value?.compareSeries.scenarioPoints[selectedMode.value as PredictScenarioKey] ?? [];
});
const contributionBreakdown = computed(() => computeContributionBreakdown(historySeries.value.map((item) => item.value), modelCoefficients.value, controls, FUTURE_YEARS.length));
const contributionItems = computed(() => [
  { key: 'core', label: '绿色金融', value: contributionBreakdown.value.core },
  { key: 'control', label: '能源相关', value: contributionBreakdown.value.control },
  { key: 'policy', label: '政策变量', value: contributionBreakdown.value.policy },
  { key: 'spatial', label: '空间溢出', value: contributionBreakdown.value.spatial },
  { key: 'mediator', label: '中介结构', value: contributionBreakdown.value.mediator },
]);
const latestObserved = computed(() => historySeries.value.at(-1)?.value ?? 0);
const finalPrediction = computed(() => selectedFutureSeries.value.at(-1)?.value ?? latestObserved.value);
const compareGap = computed(() => finalPrediction.value - (compareFutureSeries.value.at(-1)?.value ?? currentData.value?.compareSeries.historyPoints.at(-1)?.value ?? 0));
const predictionChangePct = computed(() => latestObserved.value ? (finalPrediction.value - latestObserved.value) / Math.abs(latestObserved.value) : 0);
const directionLabel = computed(() => Math.abs(predictionChangePct.value) < 0.01 ? '基本持平' : predictionChangePct.value > 0 ? '上升' : '下降');
const predictionChangeClass = computed(() => ({ positive: predictionChangePct.value > 0.01, negative: predictionChangePct.value < -0.01 }));
const isCustomMode = computed(() => selectedMode.value === CUSTOM_MODE);
const sampleRangeText = computed(() => `${currentData.value?.sampleMeta.historyStartYear ?? '—'} - ${currentData.value?.sampleMeta.historyEndYear ?? '—'}`);
const forecastRangeText = computed(() => `${currentData.value?.sampleMeta.forecastStartYear ?? '—'} - ${currentData.value?.sampleMeta.forecastEndYear ?? '—'}`);

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
    compareSummary: `${selectedModeLabel.value}下，${currentEntityLabel.value} 相对 ${compareSeriesName.value}${formatGap(compareGap.value)}。`,
    scenarioBand: currentData.value?.scenarioBand ?? [],
    customContributionBreakdown: isCustomMode.value ? contributionBreakdown.value : null,
    sampleMeta: currentData.value?.sampleMeta ?? null,
    boundaryNotice: boundaryNotice.value,
    sourceNotice: sourceNotice.value,
    entityLabel: currentEntityLabel.value,
    finalPrediction: Number(finalPrediction.value.toFixed(4)),
    predictionChangePct: Number((predictionChangePct.value * 100).toFixed(2)),
    historySeries: historySeries.value.map((item) => ({ year: item.year, value: item.value })),
    currentFutureSeries: selectedFutureSeries.value,
  },
}));

function ensureSelectionConsistency() {
  if (!metaPayload.value) return;
  if (selectedLevel.value === 'province') {
    if (!selectedProvince.value || (selectedProvince.value !== '全国' && !metaPayload.value.provinces.includes(selectedProvince.value))) {
      selectedProvince.value = '全国';
    }
    selectedCity.value = '';
    return;
  }
  if (!selectedProvince.value || selectedProvince.value === '全国' || !metaPayload.value.provinces.includes(selectedProvince.value)) {
    selectedProvince.value = metaPayload.value.provinces[0] || '';
  }
  const cities = metaPayload.value.citiesByProvince[selectedProvince.value] ?? [];
  if (!selectedCity.value || !cities.includes(selectedCity.value)) {
    selectedCity.value = cities[0] || '';
  }
}

function formatMetric(value: number | null | undefined) {
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
function formatContribution(value: number) {
  return Number.isFinite(value) ? `${value > 0 ? '+' : ''}${value.toFixed(4)}` : '—';
}
function lineData(
  points: Array<{ year: number; value: number | null }>,
  includeLastObserved: boolean,
  anchorYear?: number | null,
  anchorValue?: number | null,
) {
  const map = new Map(points.map((item) => [item.year, item.value]));
  const lastHistoryYear = anchorYear ?? historySeries.value.at(-1)?.year;
  const lastHistoryValue = anchorValue ?? historySeries.value.at(-1)?.value ?? null;
  return allYears.value.map((year) => {
    if (includeLastObserved && year === lastHistoryYear) return lastHistoryValue;
    return map.get(year) ?? null;
  });
}
function updateChart() {
  if (!chart.value) return;
  if (!historySeries.value.length) {
    chart.value.setOption({ title: { text: '暂无预测数据', left: 'center', top: 'middle', textStyle: { color: '#94a3b8', fontSize: 14 } }, xAxis: { type: 'category', data: [] }, yAxis: { type: 'value' }, series: [] });
    return;
  }
  const bandMap = new Map((currentData.value?.scenarioBand ?? []).map((item) => [item.year, item]));
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
        entityLabel: currentEntityLabel.value,
        compareName: compareSeriesName.value,
        selectedModeLabel: selectedModeLabel.value,
        sourceModeLabel: sourceModeLabel.value,
        sourceNotice: sourceNotice.value,
        boundaryNotice: boundaryNotice.value,
        historyByYear: new Map(historySeries.value.map((item) => [item.year, item])),
        compareByYear: new Map([
          ...(currentData.value?.compareSeries.historyPoints ?? []).filter((item) => item.value != null).map((item) => [item.year, item.value as number]),
          ...compareFutureSeries.value.filter((item) => item.value != null).map((item) => [item.year, item.value as number]),
        ]),
        contributionBreakdown: isCustomMode.value ? contributionBreakdown.value : null,
      }),
    },
    grid: { top: 24, right: 18, bottom: 30, left: 18, containLabel: true },
    xAxis: { type: 'category', data: allYears.value, axisLabel: { color: '#94a3b8', fontSize: 11, interval: 2 }, axisLine: { lineStyle: { color: 'rgba(148,163,184,0.18)' } } },
    yAxis: { type: 'value', name: '碳排放强度', nameTextStyle: { color: '#94a3b8', padding: [0, 0, 0, 10] }, axisLabel: { color: '#94a3b8', fontSize: 11 }, splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)', type: 'dashed' } } },
    series: [
      { name: '情景区间下界', type: 'line', stack: 'band', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, tooltip: { show: false }, data: allYears.value.map((year) => bandMap.get(year)?.min ?? null) },
      { name: '情景区间', type: 'line', stack: 'band', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(45,212,191,0.14)' }, tooltip: { show: false }, data: allYears.value.map((year) => { const band = bandMap.get(year); return band && band.max != null && band.min != null ? Number((band.max - band.min).toFixed(4)) : null; }) },
      { name: `${currentEntityLabel.value}·历史`, type: 'line', symbol: 'circle', symbolSize: 6, lineStyle: { color: '#38bdf8', width: 3 }, itemStyle: { color: '#38bdf8' }, data: lineData(historySeries.value, false) },
      { name: `${currentEntityLabel.value}·推演`, type: 'line', symbol: 'circle', symbolSize: 7, lineStyle: { color: '#2dd4bf', width: 3, type: 'dashed' }, itemStyle: { color: '#2dd4bf' }, data: lineData(selectedFutureSeries.value, true, historySeries.value.at(-1)?.year, historySeries.value.at(-1)?.value ?? null) },
      { name: `${compareSeriesName.value}·历史`, type: 'line', symbol: 'none', lineStyle: { color: 'rgba(203,213,225,0.42)', width: 2 }, data: selectedProvince.value === '全国' && selectedLevel.value === 'province' ? [] : lineData(currentData.value?.compareSeries.historyPoints ?? [], false) },
      {
        name: `${compareSeriesName.value}·推演`,
        type: 'line',
        symbol: 'none',
        lineStyle: { color: 'rgba(203,213,225,0.42)', width: 2, type: 'dashed' },
        data: selectedProvince.value === '全国' && selectedLevel.value === 'province'
          ? []
          : lineData(
            compareFutureSeries.value,
            true,
            currentData.value?.compareSeries.historyPoints.at(-1)?.year,
            currentData.value?.compareSeries.historyPoints.at(-1)?.value ?? null,
          ),
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
      ensureSelectionConsistency();
    } else {
      ElMessage.error(res.msg || '预测元数据加载失败');
    }
  } catch (error) {
    console.error(error);
    ElMessage.error('无法连接预测元数据接口');
  }
}
async function loadData() {
  if (!metaPayload.value) return;
  ensureSelectionConsistency();
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
    if (res.code === 200 && res.data) {
      currentData.value = res.data;
      if (selectedMode.value !== CUSTOM_MODE && !res.data.availableScenarios.includes(selectedMode.value as PredictScenarioKey)) {
        selectedMode.value = res.data.availableScenarios[0] ?? CUSTOM_MODE;
      }
      nextTick(() => updateChart());
    } else {
      ElMessage.error(res.msg || '预测数据加载失败');
    }
  } catch (error) {
    if (seed !== requestSeed) return;
    console.error(error);
    ElMessage.error('无法连接预测数据接口');
  }
}
function handleResetControls() {
  resetSdmSliderControls(controls);
}
function handleControlInput() {
  if (selectedMode.value !== CUSTOM_MODE) selectedMode.value = CUSTOM_MODE;
}
const resizeHandler = () => chart.value?.resize();

watch([selectedLevel, selectedProvince, selectedCity], () => {
  if (!metaPayload.value) return;
  ensureSelectionConsistency();
  loadData();
});
watch([selectedMode, currentData], () => nextTick(() => updateChart()));
watch(() => Object.values(controls).map((item) => item.value).join('|'), () => {
  if (selectedMode.value === CUSTOM_MODE) nextTick(() => updateChart());
});

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
.predict-top__eyebrow { color: rgba($tech-cyan, 0.84); font-size: 14px; letter-spacing: 0.16em; }
.predict-top__title { margin-top: 6px; font-size: 24px; font-family: $font-title; color: rgba(235, 246, 255, 0.96); }
.predict-top__desc, .predict-bar__text, .info-note, .control__hint { color: rgba(148, 163, 184, 0.76); font-size: 13px; line-height: 1.7; }
.predict-top__actions, .side, .control-list, .info-list { display: grid; gap: 12px; }
.chip-group { display: flex; flex-wrap: wrap; gap: 8px; }
.chip, .reset-btn { min-height: 36px; padding: 0 14px; border-radius: 999px; border: 1px solid rgba($tech-cyan, 0.18); background: rgba(255,255,255,0.04); color: rgba(226, 232, 240, 0.9); cursor: pointer; }
.chip.active { border-color: rgba($tech-cyan, 0.5); background: rgba($tech-cyan, 0.14); color: #fff; }
.chip.disabled, .chip:disabled, .reset-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.selectors { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; min-width: 420px; }
.field { display: grid; gap: 6px; }
.field span, .panel__title { color: rgba($tech-cyan, 0.92); font-size: 15px; }
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
@media (max-width: 980px) { .predict-top { grid-template-columns: minmax(0, 1fr); } .selectors, .stat-grid, .coef-grid, .side { grid-template-columns: minmax(0, 1fr); min-width: 0; } .predict-bar { flex-direction: column; } }
</style>
