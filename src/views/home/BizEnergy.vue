<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { predictEnergyIntensity, type PredictEnergyResponse } from '@/api/modules/dashboard';

const policyIntensity = ref(0);
const chartData = ref<PredictEnergyResponse | null>(null);
const loading = ref(false);
let chart: echarts.ECharts | null = null;

// 防抖处理
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

async function handlePredict() {
  loading.value = true;
  try {
    const res = await predictEnergyIntensity({
      intensity_increment: policyIntensity.value / 100,
    });

    if (res.code === 200 && res.data) {
      chartData.value = res.data;
      renderChart();
    } else {
      ElMessage.error(res.msg || '预测失败');
    }
  } catch (error) {
    console.error('预测接口调用失败:', error);
    ElMessage.error('预测接口调用失败');
  } finally {
    loading.value = false;
  }
}

function renderChart() {
  if (!chartData.value) return;

  const el = document.getElementById('energy-scatter');
  if (!el || el.clientWidth === 0) return;

  if (!chart) {
    chart = echarts.init(el, 'dark');
    window.addEventListener('resize', () => chart?.resize());
  }

  const { scatter_data: scatterData, predict_point: predictPoint, trendline } = chartData.value;

  chart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: (p: { seriesIndex: number; value: number[] | [number, number, string]; seriesName: string }) => {
          if (p.seriesIndex === 1) return '';
          if (p.seriesIndex === 2) {
            return `<b style="color:#ff4444">预测点</b><br/>绿色金融指数: ${p.value[0]}<br/>能耗强度: ${p.value[1]}`;
          }
          const val = p.value as [number, number, string];
          return `<b>${val[2] || '历史数据'}</b><br/>绿色金融指数: ${val[0]}<br/>能耗强度: ${val[1]}`;
        },
      },
      grid: { left: 50, right: 30, top: 40, bottom: 50 },
      xAxis: {
        type: 'value',
        name: '绿色金融指数',
        nameTextStyle: { color: '#0ff', fontSize: 11 },
        axisLabel: { color: '#aaa', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } },
      },
      yAxis: {
        type: 'value',
        name: '能耗强度',
        nameTextStyle: { color: '#0ff', fontSize: 11 },
        axisLabel: { color: '#aaa', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } },
      },
      series: [
        {
          name: '历史数据',
          type: 'scatter',
          data: scatterData,
          symbolSize: 10,
          itemStyle: {
            color: new echarts.graphic.RadialGradient(0.5, 0.5, 0.5, [
              { offset: 0, color: '#00e5ff' },
              { offset: 1, color: 'rgba(0,229,255,0.3)' },
            ]),
            shadowBlur: 6,
            shadowColor: 'rgba(0,229,255,0.3)',
          },
          emphasis: {
            itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0,229,255,0.6)' },
          },
        },
        {
          name: '趋势线',
          type: 'line',
          data: trendline,
          symbol: 'none',
          lineStyle: {
            color: '#fff',
            width: 2,
            type: 'dashed',
            shadowBlur: 4,
            shadowColor: 'rgba(255,255,255,0.3)',
          },
          tooltip: { show: false },
          z: 0,
        },
        {
          name: '预测点',
          type: 'scatter',
          data: [predictPoint],
          symbolSize: 18,
          itemStyle: {
            color: new echarts.graphic.RadialGradient(0.5, 0.5, 0.7, [
              { offset: 0, color: '#ff4444' },
              { offset: 1, color: 'rgba(255,68,68,0.2)' },
            ]),
            borderColor: '#ff0000',
            borderWidth: 2,
            shadowBlur: 15,
            shadowColor: 'rgba(255,68,68,0.8)',
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 25,
              shadowColor: 'rgba(255,68,68,1)',
            },
          },
          z: 10,
        },
      ],
      animationDurationUpdate: 800,
      animationEasingUpdate: 'cubicOut',
    },
    true,
  );
}

function onSliderChange() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    handlePredict();
  }, 300);
}

onMounted(() => {
  handlePredict();
});
</script>
<template>
  <div class="biz-wrap">
    <div class="biz-wrap-content">
      <div class="chart-header">
        <div class="header-left">
          <div class="chart-title">绿色金融指数 vs 能耗强度 · 交互式预测沙盘</div>
          <div class="chart-desc">横轴为绿色金融综合得分，纵轴为能耗强度 —— 拖动滑块模拟政策效果</div>
        </div>
        <div class="control-panel">
          <div class="control-label">追加投入模拟 (%)</div>
          <el-slider
            v-model="policyIntensity"
            :min="0"
            :max="100"
            :step="5"
            :disabled="loading"
            class="policy-slider"
            @change="onSliderChange"
          />
          <div class="control-value">{{ policyIntensity }}%</div>
        </div>
      </div>
      <div id="energy-scatter" v-loading="loading" class="chart-box" />
      <div v-if="chartData && policyIntensity > 0" class="prediction-summary">
        <div class="summary-icon">📊</div>
        <div class="summary-text">
          预测减排：能耗强度将额外下降
          <b class="highlight">{{ Math.abs(chartData.predicted_drop_percent).toFixed(2) }}%</b>
        </div>
      </div>
    </div>
  </div>
</template>
<script lang="ts">
export default { name: 'BizEnergy' };
</script>
<style lang="scss" scoped>
.biz-wrap {
  display: flex;
  height: 100%;
  padding: 10px 20px 25px;
}
.biz-wrap-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  padding-bottom: 10px;
  gap: 20px;
}
.header-left {
  flex: 1;
  text-align: left;
}
.chart-title {
  color: rgba(0, 229, 255, 0.85);
  font-size: 15px;
  letter-spacing: 1px;
}
.chart-desc {
  color: rgba(200, 220, 255, 0.4);
  font-size: 11px;
  margin-top: 2px;
}
.control-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: rgba(0, 229, 255, 0.05);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 6px;
  min-width: 280px;
}
.control-label {
  color: rgba(0, 229, 255, 0.8);
  font-size: 12px;
  white-space: nowrap;
}
.policy-slider {
  flex: 1;
  :deep(.el-slider__runway) {
    background-color: rgba(0, 229, 255, 0.1);
  }
  :deep(.el-slider__bar) {
    background: linear-gradient(90deg, #00e5ff, #00ff88);
  }
  :deep(.el-slider__button) {
    border-color: #00e5ff;
    background-color: #00e5ff;
  }
}
.control-value {
  color: #00ff88;
  font-size: 14px;
  font-weight: bold;
  min-width: 40px;
  text-align: right;
}
.chart-box {
  flex: 1;
  min-height: 0;
}
.prediction-summary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px 20px;
  margin-top: 10px;
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.08), rgba(0, 255, 136, 0.08));
  border: 1px solid rgba(0, 229, 255, 0.25);
  border-radius: 8px;
  animation: fadeIn 0.5s ease-in;
}
.summary-icon {
  font-size: 24px;
}
.summary-text {
  color: rgba(200, 220, 255, 0.9);
  font-size: 13px;
  letter-spacing: 0.5px;
}
.highlight {
  color: #00ff88;
  font-size: 16px;
  margin: 0 4px;
  text-shadow: 0 0 8px rgba(0, 255, 136, 0.5);
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
