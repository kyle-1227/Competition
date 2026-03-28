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

    <div ref="chartRef" class="chart-container"></div>

    <!-- 推演摘要：与滑块联动的关键指标 -->
    <div class="prediction-summary">
      <div class="summary-card">
        <div class="summary-label">历史基准 ({{ lastHistoricalYear }}年)</div>
        <div class="summary-value">{{ summary.base.toFixed(3) }}</div>
      </div>
      <div class="summary-card summary-card--highlight">
        <div class="summary-label">预测终点 ({{ terminalYear }}年)</div>
        <div class="summary-value">{{ summary.terminal.toFixed(3) }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">相对基准提升</div>
        <div class="summary-value summary-value--accent">+{{ summary.gainPercent.toFixed(2) }}%</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import type { EChartsOption } from 'echarts';
import { useChart } from './hooks/useChart';

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

const { setOption } = useChart(chartRef, { tabKey: props.chartTabKey });

const baseCoefficient = 0.05;
const historicalYears = ['2017', '2018', '2019', '2020', '2021', '2022'];
const historicalData = [0.35, 0.38, 0.42, 0.46, 0.5, 0.53];
const futureYears = ['2023', '2024', '2025', '2026', '2027', '2028', '2029', '2030'];

const lastHistoricalYear = historicalYears[historicalYears.length - 1];
const terminalYear = futureYears[futureYears.length - 1];

const calculateFutureData = () => {
  let lastValue = historicalData[historicalData.length - 1];
  const predicted: number[] = [];

  for (let i = 0; i < futureYears.length; i++) {
    const nextValue =
      lastValue + baseCoefficient * (growthRate.value / 100) * spilloverMultiplier.value;
    predicted.push(Number(nextValue.toFixed(3)));
    lastValue = nextValue;
  }
  return predicted;
};

const summary = computed(() => {
  const predicted = calculateFutureData();
  const base = historicalData[historicalData.length - 1];
  const terminal = predicted.length ? predicted[predicted.length - 1] : base;
  const gainPercent = base !== 0 ? ((terminal - base) / base) * 100 : 0;
  return { base, terminal, gainPercent };
});

function buildChartOption(): EChartsOption {
  const futureData = calculateFutureData();
  const paddingData = new Array(historicalData.length - 1).fill(null);
  const connectedFutureData = [...paddingData, historicalData[historicalData.length - 1], ...futureData];

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['历史实际值', '动态预测值'], textStyle: { color: '#fff' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: [...historicalYears, ...futureYears],
      axisLabel: { color: '#ccc' },
    },
    yAxis: {
      type: 'value',
      name: '减排效率',
      nameTextStyle: { color: '#ccc' },
      axisLabel: { color: '#ccc' },
      min: 0.2,
      max: 1.0,
    },
    series: [
      {
        name: '历史实际值',
        type: 'line',
        data: [...historicalData, ...new Array(futureYears.length).fill(null)],
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
  nextTick(() => {
    renderChart();
  });
});

watch([growthRate, spilloverMultiplier], () => {
  renderChart();
});
</script>

<style scoped lang="scss">
.biz-prediction {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(13, 20, 36, 0.6);
  border-radius: 8px;
  padding: 15px;

  .module-title {
    font-size: 18px;
    font-weight: bold;
    color: #fff;
    margin-bottom: 15px;
  }

  .control-panel {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 15px;
    padding: 10px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 6px;

    .control-item {
      flex: 1;
      display: flex;
      flex-direction: column;

      .label {
        display: flex;
        justify-content: space-between;
        color: #eee;
        font-size: 14px;
        margin-bottom: 8px;

        .value {
          color: #00ffcc;
          font-weight: bold;
        }
      }

      input[type='range'] {
        width: 100%;
        cursor: pointer;
        accent-color: #00ffcc;
      }
    }
  }

  .chart-container {
    flex: 1;
    min-height: 250px;
  }

  .prediction-summary {
    display: flex;
    gap: 12px;
    margin-top: 12px;
    flex-shrink: 0;
  }

  .summary-card {
    flex: 1;
    min-width: 0;
    padding: 10px 12px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(0, 229, 255, 0.12);
    &--highlight {
      border-color: rgba(0, 255, 204, 0.35);
      background: rgba(0, 229, 255, 0.06);
    }
  }

  .summary-label {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.55);
    margin-bottom: 6px;
    letter-spacing: 0.5px;
  }

  .summary-value {
    font-size: 18px;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.95);
    font-family: 'DIN Alternate', 'DIN', 'Segoe UI', sans-serif;
    &--accent {
      color: #00ffcc;
      text-shadow: 0 0 12px rgba(0, 255, 204, 0.25);
    }
  }
}
</style>
