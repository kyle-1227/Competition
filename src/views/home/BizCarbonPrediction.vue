<template>
  <div class="biz-carbon-prediction">
    <div class="header-section">
      <div class="module-title">
        <span class="icon"></span> 碳排放强度动态预测 (SDM模型)
      </div>
      <div class="province-selector">
        <span class="label">分析区域：</span>
        <select v-model="selectedProvince" @change="onProvinceChange">
          <option value="全国">全国 (平均值)</option>
          <option v-for="prov in provinceList" :key="prov" :value="prov">{{ prov }}</option>
        </select>
      </div>
    </div>

    <div class="main-workspace">
      <div class="chart-column">
        <div class="chart-toolbar">
          <span class="toolbar-hint">历史实线 · 预测虚线（2025–2027）</span>
          <span class="toolbar-legend">
            <span class="lg-item lg-hist"><i class="lg-swatch"></i> 历史</span>
            <span class="lg-item lg-pred"><i class="lg-swatch lg-swatch--dash"></i> 预测</span>
          </span>
        </div>
        <div class="chart-wrapper">
          <div ref="chartRef" class="echarts-container"></div>
        </div>
      </div>

      <aside class="controls-column">
        <div class="controls-title">情景参数（相对基准倍数）</div>
        <div class="control-panel">
          <div class="control-item" v-for="(ctrl, key) in controls" :key="key">
            <div class="ctrl-header">
              <span class="ctrl-name">{{ ctrl.name }}</span>
              <span class="ctrl-val">{{ (ctrl.value * 100).toFixed(0) }}%</span>
            </div>
            <input type="range" v-model.number="ctrl.value" min="0.5" max="2.0" step="0.05" @input="updateChart" />
          </div>
        </div>
      </aside>
    </div>

    <div class="bottom-panel">
      <div class="coef-box">
        <div class="box-title">SDM模型核心系数 (基于历史面板回归)</div>
        <div class="coef-list">
          <span class="tag">绿色金融(gfi_std): <b>{{ fmt4(coef?.core) }}</b></span>
          <span class="tag">能源强度 / ln_pop: <b>{{ fmt4(coef?.control) }} / {{ fmt4(coef?.control_ln_pop) }}</b></span>
          <span class="tag">周边溢出: <b>{{ fmt4(coef?.spatial) }}</b></span>
          <span class="tag">碳排放强度(rho): <b>{{ fmt4(coef?.rho) }}</b></span>
        </div>
      </div>
      <div class="result-box">
        <div class="box-title">2027年 预测结果 ({{ selectedProvince }})</div>
        <div class="result-data">
          <div class="val-group">
            <span class="label">预测碳排放强度</span>
            <span class="number highlight">{{ finalPrediction.toFixed(4) }}</span>
          </div>
          <div class="val-group">
            <span class="label">较2024年变动</span>
            <span class="number" :class="{'decrease': predictionChange < 0, 'increase': predictionChange >= 0}">
              {{ predictionChange > 0 ? '+' : '' }}{{ (predictionChange * 100).toFixed(2) }}%
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, shallowRef, computed, onUnmounted, nextTick, watch } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import {
  getCarbonPredictData,
  type CarbonPredictCoefficients,
  type CarbonHistoryPoint,
} from '@/api/modules/dashboard';
import { excludeProvincesWithoutPanelData, isProvinceExcludedFromPanel } from './hooks/provinceData';

const chartRef = ref<HTMLElement | null>(null);
const chartInstance = shallowRef<echarts.ECharts | null>(null);

/** 后端拉取：省份 -> 年序列（含面板自变量） */
const historyPayload = ref<Record<string, CarbonHistoryPoint[]>>({});
const coefficientsPayload = ref<CarbonPredictCoefficients | null>(null);
const coef = computed(() => coefficientsPayload.value);

function fmt4(v: number | undefined | null) {
  if (v === undefined || v === null || Number.isNaN(v)) return '—';
  return v.toFixed(4);
}

const provinceList = computed(() => {
  const keys = Object.keys(historyPayload.value).filter((k) => k !== '全国');
  return excludeProvincesWithoutPanelData(keys).sort((a, b) => a.localeCompare(b, 'zh-CN'));
});

const selectedProvince = ref('全国');

const controls = ref({
  core: { name: '核心变量 (绿色金融)', value: 1.1 },
  control: { name: '控制变量 (人口/能耗)', value: 1.0 },
  policy: { name: '政策准自然实验 (DID)', value: 1.2 },
  spatial: { name: '空间滞后 (周边溢出)', value: 1.05 },
  mediator: { name: '中介变量 (产业结构)', value: 1.15 },
});

/** 与推演公式同步的系数（来自 SDM CSV） */
const modelCoef = computed(() => {
  const c = coefficientsPayload.value;
  return {
    core: c?.core ?? 0.1446,
    control: c?.control ?? 1.251,
    spatial: c?.spatial ?? -0.0284,
    rho: c?.rho ?? 0.4882,
    policy: c?.policy ?? 0,
    mediator: c?.mediator ?? -0.08,
  };
});

function seriesFor(province: string) {
  const rows = historyPayload.value[province] || historyPayload.value['全国'] || [];
  return [...rows].sort((a, b) => a.year - b.year);
}

const historicalYears = computed(() => seriesFor(selectedProvince.value).map((r) => r.year));

const yearsFuture = [2025, 2026, 2027];

const allYears = computed(() => [...historicalYears.value, ...yearsFuture]);

const firstFutureYear = computed(() => yearsFuture[0] ?? 2025);

const currentHistory = computed(() => seriesFor(selectedProvince.value).map((r) => r.value));

const currentPrediction = computed(() => {
  const hist = currentHistory.value;
  const mc = modelCoef.value;
  if (!hist.length) return [];
  let currentVal = hist[hist.length - 1]!;
  const predicted: number[] = [];
  for (let i = 0; i < yearsFuture.length; i++) {
    const deltaCore = (controls.value.core.value - 1) * mc.core;
    const deltaControl = (controls.value.control.value - 1) * mc.control * 0.1;
    const deltaPolicy = (controls.value.policy.value - 1) * mc.policy;
    const deltaSpatial = (controls.value.spatial.value - 1) * mc.spatial;
    const deltaMediator = (controls.value.mediator.value - 1) * mc.mediator;
    const netEffect = -(deltaCore + deltaPolicy + deltaMediator - deltaControl - deltaSpatial);
    currentVal = currentVal + netEffect - 0.015;
    predicted.push(Number(Math.max(currentVal, 0.1).toFixed(4)));
  }
  return predicted;
});

const finalPrediction = computed(() => currentPrediction.value[2] ?? 0);
const predictionChange = computed(() => {
  const hist = currentHistory.value;
  if (!hist.length) return 0;
  const base = hist[hist.length - 1]!;
  if (base === 0) return 0;
  return (finalPrediction.value - base) / base;
});

const resizeHandler = () => chartInstance.value?.resize();

const scheduleChartResize = () => {
  nextTick(() => {
    requestAnimationFrame(() => {
      chartInstance.value?.resize();
    });
  });
};

const updateChart = () => {
  if (!chartInstance.value) return;

  const years = allYears.value;
  const historyData = currentHistory.value;
  const predictData = currentPrediction.value;
  const yearToData = new Map(seriesFor(selectedProvince.value).map((r) => [r.year, r]));

  if (!years.length || !historyData.length) {
    chartInstance.value.setOption({
      title: {
        text: '暂无面板历史数据（请检查后端 CSV 与接口）',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#94a3b8', fontSize: 13 },
      },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: [],
    });
    scheduleChartResize();
    return;
  }

  const histLine = years.map((y) => {
    if (yearToData.has(y)) return yearToData.get(y)!.value;
    return null;
  });

  const padding = new Array(historyData.length - 1).fill(null);
  const connectedPrediction = [...padding, historyData[historyData.length - 1]!, ...predictData];

  const fy = firstFutureYear.value;
  const option = {
    title: { show: false },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'transparent',
      padding: 0,
      borderWidth: 0,
      formatter: (params: any) => {
        const year = params[0].axisValue;
        const isPredict = Number(year) >= fy;
        const rawVal = params.find((p: any) => p.value !== null && p.value !== undefined)?.value ?? 0;
        const numVal = typeof rawVal === 'number' ? rawVal : Number(rawVal);
        const rowData = yearToData.get(Number(year));

        let detailsHtml = '';
        if (isPredict) {
          detailsHtml = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px;">
              <span style="color: #888;">绿色金融强度预设</span>
              <span style="color: #00ffcc;">${(controls.value.core.value * 100).toFixed(0)}%</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px;">
              <span style="color: #888;">政策及结构效能预设</span>
              <span style="color: #ffaa00;">${(controls.value.policy.value * 100).toFixed(0)}%</span>
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
              📍 ${selectedProvince.value} | ${year}年 ${isPredict ? '(预测沙盘推演)' : '(历史真实实证)'}
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
              <span style="color: #aaa;">碳排放强度 (因变量Y)</span>
              <span style="color: #fff; font-weight: bold; font-size: 14px;">${Number.isFinite(numVal) ? numVal.toFixed(4) : String(rawVal)}</span>
            </div>
            ${detailsHtml}
          </div>
        `;
      }
    },
    grid: { top: 52, left: 12, right: 20, bottom: 28, containLabel: true },
    xAxis: {
      type: 'category',
      data: years,
      axisLabel: { color: '#94a3b8', fontSize: 11, interval: 2 },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: '碳排放强度',
      nameTextStyle: { color: '#8ba3c7', fontSize: 12, padding: [0, 0, 0, 8] },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(148,163,184,0.12)', type: 'dashed' } }
    },
    series: [
      {
        name: '历史数据',
        type: 'line',
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#4facfe' },
        lineStyle: { width: 3, color: '#4facfe' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(79, 172, 254, 0.4)' },
            { offset: 1, color: 'rgba(79, 172, 254, 0.0)' }
          ])
        },
        data: histLine,
        animationDuration: 800
      },
      {
        name: '模型预测',
        type: 'line',
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: { color: '#00ffcc', shadowColor: '#00ffcc', shadowBlur: 10 },
        lineStyle: { width: 3, type: 'dashed', color: '#00ffcc' },
        data: connectedPrediction,
        animationDuration: 300
      }
    ]
  };

  chartInstance.value.setOption(option);
  scheduleChartResize();
};

async function loadPredictData() {
  try {
    const res = await getCarbonPredictData();
    if (res.code === 200 && res.data) {
      historyPayload.value = res.data.historyData;
      coefficientsPayload.value = res.data.coefficients;
      if (
        !historyPayload.value[selectedProvince.value] ||
        isProvinceExcludedFromPanel(selectedProvince.value)
      ) {
        selectedProvince.value = historyPayload.value['全国']
          ? '全国'
          : excludeProvincesWithoutPanelData(Object.keys(historyPayload.value))[0] || '全国';
      }
    } else {
      ElMessage.error(res.msg || '碳强度预测数据加载失败');
    }
  } catch (e) {
    console.error(e);
    ElMessage.error('无法连接预测数据接口');
  }
}

function onProvinceChange() {
  updateChart();
}

let resizeObserver: ResizeObserver | null = null;

onMounted(async () => {
  await loadPredictData();
  if (chartRef.value) {
    chartInstance.value = echarts.init(chartRef.value);
    updateChart();
    window.addEventListener('resize', resizeHandler);
    resizeObserver = new ResizeObserver(() => resizeHandler());
    resizeObserver.observe(chartRef.value);
    scheduleChartResize();
  }
});

watch([selectedProvince, historyPayload, coefficientsPayload], () => nextTick(() => updateChart()), { deep: true });

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler);
  resizeObserver?.disconnect();
  resizeObserver = null;
  chartInstance.value?.dispose();
});
</script>

<style scoped lang="scss">
/* 整体面板：主区左侧大图 + 右侧参数，避免中间留白 */
.biz-carbon-prediction {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(165deg, rgba(13, 24, 42, 0.92) 0%, rgba(10, 18, 32, 0.88) 100%);
  border: 1px solid rgba(0, 255, 204, 0.12);
  border-radius: 12px;
  padding: 14px 18px;
  box-sizing: border-box;
  overflow: hidden;
  color: #fff;
  font-family: 'Helvetica Neue', 'Noto Sans SC', Arial, sans-serif;
}

/* 1. 顶部标题区域 */
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;

  .module-title {
    font-size: 16px;
    font-weight: 600;
    color: #e2e8f0;
    .icon { margin-right: 6px; }
  }

  .province-selector {
    display: flex;
    align-items: center;
    font-size: 13px;
    .label { color: #8ba3c7; margin-right: 8px; }
    select {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(0, 255, 204, 0.4);
      color: #00ffcc;
      padding: 4px 10px;
      border-radius: 4px;
      outline: none;
      cursor: pointer;
      font-weight: bold;
      &:focus { border-color: #00ffcc; }
      option { background: #0d1424; color: #fff; }
    }
  }
}

/* 2. 主工作区：左图右控 */
.main-workspace {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 16px;
  margin-top: 4px;
}

.chart-column {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 220px;
}

.chart-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 0 4px 8px;
  font-size: 12px;
  color: #8ba3c7;

  .toolbar-hint {
    letter-spacing: 0.02em;
  }

  .toolbar-legend {
    display: flex;
    gap: 14px;
  }

  .lg-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #cbd5e1;
    font-size: 11px;

    .lg-swatch {
      display: inline-block;
      width: 16px;
      height: 3px;
      border-radius: 2px;
      font-style: normal;
    }
  }

  .lg-hist .lg-swatch {
    background: linear-gradient(90deg, #4facfe, #38bdf8);
    box-shadow: 0 0 8px rgba(79, 172, 254, 0.45);
  }

  .lg-pred .lg-swatch--dash {
    background: repeating-linear-gradient(
      90deg,
      #2dd4bf,
      #2dd4bf 3px,
      transparent 3px,
      transparent 5px
    );
    height: 2px;
    box-shadow: 0 0 8px rgba(45, 212, 191, 0.4);
  }
}

.chart-wrapper {
  flex: 1;
  min-height: 0;
  position: relative;
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 10px;
  overflow: hidden;

  .echarts-container {
    width: 100%;
    height: 100%;
    min-height: 200px;
  }
}

.controls-column {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 10px;
}

.controls-title {
  font-size: 12px;
  font-weight: 600;
  color: #5eead4;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(94, 234, 212, 0.15);
}

.control-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;

  &::-webkit-scrollbar {
    width: 4px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(94, 234, 212, 0.25);
    border-radius: 2px;
  }

  .control-item {
    background: rgba(15, 23, 42, 0.45);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 8px;
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    justify-content: center;

    .ctrl-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
      margin-bottom: 8px;
      font-size: 11px;
      line-height: 1.35;

      .ctrl-name {
        color: #94a3b8;
        flex: 1;
        white-space: normal;
      }

      .ctrl-val {
        flex-shrink: 0;
        font-weight: 700;
        font-family: 'DIN Alternate', 'DIN', ui-monospace, sans-serif;
        color: #5eead4;
        font-variant-numeric: tabular-nums;
      }
    }

    input[type='range'] {
      width: 100%;
      height: 5px;
      border-radius: 3px;
      background: linear-gradient(90deg, rgba(94, 234, 212, 0.15), rgba(56, 189, 248, 0.15));
      outline: none;
      appearance: none;

      &::-webkit-slider-thumb {
        appearance: none;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #5eead4, #14b8a6);
        cursor: pointer;
        box-shadow:
          0 0 0 2px rgba(15, 23, 42, 0.9),
          0 0 12px rgba(45, 212, 191, 0.55);
      }

      &::-moz-range-thumb {
        width: 14px;
        height: 14px;
        border: none;
        border-radius: 50%;
        background: #5eead4;
        cursor: pointer;
      }
    }
  }
}

@media (max-width: 1100px) {
  .main-workspace {
    flex-direction: column;
  }

  .controls-column {
    width: 100%;
    max-height: 200px;
  }

  .control-panel {
    flex-direction: row;
    flex-wrap: wrap;

    .control-item {
      flex: 1 1 calc(50% - 6px);
      min-width: 140px;
    }
  }
}

/* 3. 底部信息面板（系数 / 预测结果：等分铺满容器） */
.bottom-panel {
  display: flex;
  gap: 14px;
  margin-top: 12px;
  flex-shrink: 0;
  min-height: 96px;

  .coef-box,
  .result-box {
    border-radius: 8px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    min-height: 0;
  }

  .coef-box {
    flex: 2.2;
    background: rgba(15, 23, 42, 0.55);
    border: 1px solid rgba(56, 189, 248, 0.2);

    .box-title {
      color: #94a3b8;
      font-size: 12px;
      margin-bottom: 8px;
      font-weight: 500;
      flex-shrink: 0;
    }

    .coef-list {
      flex: 1;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      align-items: stretch;
      min-height: 52px;

      .tag {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        font-size: 11px;
        line-height: 1.35;
        color: #e2e8f0;
        background: rgba(255, 255, 255, 0.06);
        padding: 8px 6px;
        border-radius: 6px;
        border: 1px solid rgba(148, 163, 184, 0.12);
        min-width: 0;

        b {
          color: #7dd3fc;
          font-family: 'DIN Alternate', 'DIN', ui-monospace, sans-serif;
          font-weight: 600;
          margin-top: 2px;
          font-size: 12px;
        }
      }
    }
  }

  .result-box {
    flex: 1;
    min-width: 200px;
    background: linear-gradient(135deg, rgba(13, 148, 136, 0.12) 0%, rgba(15, 23, 42, 0.6) 100%);
    border: 1px solid rgba(45, 212, 191, 0.35);

    .box-title {
      color: #5eead4;
      font-size: 12px;
      margin-bottom: 8px;
      font-weight: 600;
      flex-shrink: 0;
    }

    .result-data {
      flex: 1;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      align-items: stretch;
      min-height: 52px;

      .val-group {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 6px;
        padding: 8px 10px;
        background: rgba(0, 0, 0, 0.12);
        border-radius: 8px;
        border: 1px solid rgba(45, 212, 191, 0.12);
        min-width: 0;

        .label {
          font-size: 11px;
          color: #94a3b8;
          line-height: 1.2;
        }

        .number {
          font-size: clamp(18px, 2.2vw, 24px);
          font-weight: 700;
          font-family: 'DIN Alternate', 'DIN', ui-monospace, sans-serif;
          font-variant-numeric: tabular-nums;
          line-height: 1.2;

          &.highlight {
            color: #f1f5f9;
            text-shadow: 0 0 16px rgba(45, 212, 191, 0.35);
          }

          &.decrease {
            color: #5eead4;
          }

          &.increase {
            color: #fbbf24;
          }
        }
      }
    }
  }
}

@media (max-width: 900px) {
  .bottom-panel .coef-box .coef-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    min-height: auto;
  }
}
</style>