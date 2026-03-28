<template>
  <div class="biz-prediction">
    <div class="module-title">碳减排效率预测沙盘</div>

    <div class="control-panel">
      <div class="control-item">
        <div class="label">
          <span>绿色金融年预期增长率:</span>
          <span class="value">{{ growthRate }}%</span>
        </div>
        <input type="range" v-model.number="growthRate" min="0" max="20" step="1" />
      </div>

      <div class="control-item">
        <div class="label">
          <span>空间溢出乘数 (周边协同):</span>
          <span class="value">{{ spilloverMultiplier.toFixed(1) }}x</span>
        </div>
        <input type="range" v-model.number="spilloverMultiplier" min="1.0" max="2.0" step="0.1" />
      </div>
    </div>

    <div ref="chartRef" class="chart-container" v-loading="loading" />

    <!-- 推演摘要：与滑块联动的关键指标 -->
    <div class="prediction-summary">
      <div class="summary-card">
        <div class="summary-label">历史基准 ({{ lastHistoricalYear || '—' }}年)</div>
        <div class="summary-value">{{ hasData ? summary.base.toFixed(3) : '—' }}</div>
      </div>
      <div class="summary-card summary-card--highlight">
        <div class="summary-label">预测终点 ({{ terminalYear || '—' }}年)</div>
        <div class="summary-value">{{ hasData ? summary.terminal.toFixed(3) : '—' }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">相对基准提升</div>
        <div class="summary-value summary-value--accent">
          {{ hasData ? `+${summary.gainPercent.toFixed(2)}%` : '—' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import type { EChartsOption } from 'echarts';
import { useChart } from './hooks/useChart';
import { getPredictionDataApi, type PredictionEfficiencyPayload } from '@/api/modules/dashboard';
import { selectedProvince } from './hooks/provinceData';

const props = withDefaults(
  defineProps<{
    /** 与 index provide 的 activeTab 一致（当前挂在「碳减排效率预测」Tab），用于 useChart 切 Tab 时 resize */
    chartTabKey?: string;
  }>(),
  { chartTabKey: 'energy' },
);

const growthRate = ref(8);
const spilloverMultiplier = ref(1.2);
const chartRef = ref<HTMLElement | null>(null);
const loading = ref(false);

const historicalYears = ref<string[]>([]);
const historicalData = ref<number[]>([]);
const baseCoefficient = ref(0);
const futureYears = ref<string[]>([]);
const baselinePredictValues = ref<number[]>([]);

const { setOption } = useChart(chartRef, { tabKey: props.chartTabKey });

const lastHistoricalYear = computed(() => {
  const y = historicalYears.value;
  return y.length ? String(y[y.length - 1]) : '';
});

const terminalYear = computed(() => {
  const y = futureYears.value;
  return y.length ? String(y[y.length - 1]) : '';
});

const hasData = computed(
  () =>
    historicalYears.value.length > 0 &&
    historicalData.value.length > 0 &&
    futureYears.value.length > 0 &&
    historicalYears.value.length === historicalData.value.length,
);

const calculateFutureData = (): number[] => {
  if (!hasData.value || !futureYears.value.length) return [];
  let lastValue = historicalData.value[historicalData.value.length - 1];
  const predicted: number[] = [];
  const coef = baseCoefficient.value;

  for (let i = 0; i < futureYears.value.length; i++) {
    const nextValue = lastValue + coef * (growthRate.value / 100) * spilloverMultiplier.value;
    predicted.push(Number(nextValue.toFixed(3)));
    lastValue = nextValue;
  }
  return predicted;
};

const summary = computed(() => {
  const predicted = calculateFutureData();
  const hd = historicalData.value;
  const base = hd.length ? hd[hd.length - 1] : 0;
  const terminal = predicted.length ? predicted[predicted.length - 1] : base;
  const gainPercent = base !== 0 ? ((terminal - base) / base) * 100 : 0;
  return { base, terminal, gainPercent };
});

function isOkPayload(
  res: unknown,
): res is { code: number; msg: string; data: PredictionEfficiencyPayload } {
  return (
    typeof res === 'object' &&
    res !== null &&
    'code' in res &&
    (res as { code: number }).code === 200 &&
    'data' in res &&
    (res as { data: PredictionEfficiencyPayload | null }).data != null
  );
}

async function fetchPredictionData(province?: string) {
  loading.value = true;
  try {
    const res = await getPredictionDataApi(province);
    if (isOkPayload(res)) {
      const d = res.data;
      historicalYears.value = d.historical_years.map((y) => String(y));
      historicalData.value = [...d.historical_values];
      baseCoefficient.value = d.base_coefficient;
      futureYears.value = d.predict_years.map((y) => String(y));
      baselinePredictValues.value = [...d.baseline_predict_values];
      await nextTick();
      renderChart();
    } else {
      const msg = typeof res === 'object' && res !== null && 'msg' in res ? String((res as { msg: string }).msg) : '获取预测数据失败';
      ElMessage.error(msg);
    }
  } catch (e) {
    console.error(e);
    ElMessage.error('获取预测数据失败');
  } finally {
    loading.value = false;
  }
}

function buildChartOption(): EChartsOption {
  const hy = historicalYears.value;
  const hd = historicalData.value;
  const fy = futureYears.value;

  if (!hy.length || !hd.length || !fy.length || hy.length !== hd.length) {
    return {
      backgroundColor: 'transparent',
      title: {
        text: loading.value ? '加载中…' : '暂无数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: 'rgba(255,255,255,0.45)', fontSize: 14 },
      },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: [],
    };
  }

  const futureData = calculateFutureData();
  const paddingData = new Array(hd.length - 1).fill(null);
  const connectedFutureData = [...paddingData, hd[hd.length - 1], ...futureData];

  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: {
      top: 6,
      left: 'center',
      itemGap: 24,
      data: ['历史实际值', '动态预测值'],
      textStyle: { color: 'rgba(255,255,255,0.92)', fontSize: 11 },
    },
    grid: {
      left: '2%',
      right: '3%',
      top: 44,
      bottom: 52,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: [...hy, ...fy],
      axisLabel: {
        color: '#ccc',
        fontSize: 9,
        rotate: 38,
        interval: 0,
        hideOverlap: true,
      },
    },
    yAxis: {
      type: 'value',
      name: '减排效率',
      nameTextStyle: { color: '#ccc' },
      axisLabel: { color: '#ccc' },
      min: 0,
      max: 1.0,
    },
    series: [
      {
        name: '历史实际值',
        type: 'line',
        data: [...hd, ...new Array(fy.length).fill(null)],
        itemStyle: { color: '#8884d8' },
        lineStyle: { width: 3 },
        smooth: true,
      },
      {
        name: '动态预测值',
        type: 'line',
        data: connectedFutureData,
        itemStyle: { color: '#82ca9d' },
        lineStyle: { type: 'dashed', width: 3 },
        smooth: true,
        animationDuration: 500,
      },
    ],
  };
}

function renderChart() {
  setOption(buildChartOption(), true);
}

onMounted(() => {
  void fetchPredictionData(selectedProvince.value || undefined);
});

watch([growthRate, spilloverMultiplier], () => {
  if (hasData.value) renderChart();
});

watch(selectedProvince, (name) => {
  fetchPredictionData(name ? name : undefined);
});
</script>

<style scoped lang="scss">
.biz-prediction {
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: auto;
  border-radius: 10px;
  padding: 12px 12px 14px;
  /* 透明荧光毛玻璃 */
  background: linear-gradient(
    145deg,
    rgba(12, 28, 52, 0.38) 0%,
    rgba(8, 20, 42, 0.32) 50%,
    rgba(6, 18, 38, 0.4) 100%
  );
  border: 1px solid rgba(0, 229, 255, 0.28);
  box-shadow:
    0 0 0 1px rgba(0, 255, 255, 0.06) inset,
    0 8px 32px rgba(0, 0, 0, 0.35),
    0 0 24px rgba(0, 229, 255, 0.08);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);

  .module-title {
    flex-shrink: 0;
    font-size: 17px;
    font-weight: bold;
    color: rgba(255, 255, 255, 0.96);
    margin-bottom: 12px;
    text-shadow: 0 0 18px rgba(0, 229, 255, 0.35);
  }

  .control-panel {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 12px;
    margin-bottom: 12px;
    padding: 10px 10px 12px;
    border-radius: 8px;
    box-sizing: border-box;
    max-width: 100%;
    min-width: 0;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(0, 229, 255, 0.2);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.06) inset;

    .control-item {
      flex: 1 1 200px;
      min-width: 0;
      max-width: 100%;
      display: flex;
      flex-direction: column;

      .label {
        display: flex;
        flex-wrap: wrap;
        align-items: baseline;
        justify-content: space-between;
        gap: 4px 8px;
        color: rgba(238, 238, 238, 0.95);
        font-size: 12px;
        margin-bottom: 6px;
        line-height: 1.35;

        .value {
          flex-shrink: 0;
          color: #5fffea;
          font-weight: bold;
          text-shadow: 0 0 10px rgba(0, 255, 204, 0.45);
        }
      }

      input[type='range'] {
        box-sizing: border-box;
        width: 100%;
        max-width: 100%;
        min-width: 0;
        cursor: pointer;
        accent-color: #00ffcc;
      }
    }
  }

  .chart-container {
    flex: 1;
    min-width: 0;
    min-height: 240px;
    width: 100%;
  }

  .prediction-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
    flex-shrink: 0;
    box-sizing: border-box;
    max-width: 100%;
    min-width: 0;
  }

  .summary-card {
    flex: 1 1 140px;
    min-width: 0;
    padding: 10px 10px;
    border-radius: 8px;
    box-sizing: border-box;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(0, 229, 255, 0.22);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 0 16px rgba(0, 229, 255, 0.05) inset;
    &--highlight {
      border-color: rgba(0, 255, 204, 0.42);
      background: rgba(0, 229, 255, 0.1);
      box-shadow:
        0 0 20px rgba(0, 255, 204, 0.12) inset,
        0 0 12px rgba(0, 229, 255, 0.15);
    }
  }

  .summary-label {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.58);
    margin-bottom: 5px;
    letter-spacing: 0.3px;
    word-break: break-all;
  }

  .summary-value {
    font-size: clamp(15px, 2.8vw, 18px);
    font-weight: 700;
    color: rgba(255, 255, 255, 0.96);
    font-family: 'DIN Alternate', 'DIN', 'Segoe UI', sans-serif;
    &--accent {
      color: #5fffea;
      text-shadow: 0 0 14px rgba(0, 255, 204, 0.4);
    }
  }
}
</style>
