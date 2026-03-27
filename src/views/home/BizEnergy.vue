<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { predictEnergyIntensity, type PredictEnergyResponse } from '@/api/modules/dashboard';
import { selectedProvince, selectedYear } from './hooks/provinceData';

const policyIntensity = ref(0);
const chartData = ref<PredictEnergyResponse | null>(null);
const loading = ref(false);
let chart: echarts.ECharts | null = null;

// 防抖处理
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

// 中国省份列表（31个省/直辖市/自治区）
const provinceOptions = [
  '北京市',
  '天津市',
  '河北省',
  '山西省',
  '内蒙古自治区',
  '辽宁省',
  '吉林省',
  '黑龙江省',
  '上海市',
  '江苏省',
  '浙江省',
  '安徽省',
  '福建省',
  '江西省',
  '山东省',
  '河南省',
  '湖北省',
  '湖南省',
  '广东省',
  '广西壮族自治区',
  '海南省',
  '重庆市',
  '四川省',
  '贵州省',
  '云南省',
  '陕西省',
  '甘肃省',
  '青海省',
  '宁夏回族自治区',
  '新疆维吾尔自治区',
  '西藏自治区',
];

async function handlePredict() {
  loading.value = true;
  try {
    const res = await predictEnergyIntensity({
      intensity_increment: policyIntensity.value / 100,
      year: selectedYear.value,
      province: selectedProvince.value || undefined,
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

  const {
    scatter_data: scatterData,
    predict_point: predictPoint,
    trendline,
    base_province: baseProvince,
  } = chartData.value;

  // 处理散点数据，根据是否为选中省份进行高亮
  const processedScatterData = scatterData.map((item) => {
    const [gfi, outcome, province] = item;
    const isSelected = baseProvince !== '全国平均' && String(province) === baseProvince;
    return {
      value: item,
      itemStyle: isSelected
        ? {
            color: new echarts.graphic.RadialGradient(0.5, 0.5, 0.7, [
              { offset: 0, color: '#FFD700' },
              { offset: 1, color: 'rgba(255, 215, 0, 0.3)' },
            ]),
            borderColor: '#FFD700',
            borderWidth: 2,
            shadowBlur: 15,
            shadowColor: 'rgba(255, 215, 0, 0.8)',
          }
        : {
            color: new echarts.graphic.RadialGradient(0.5, 0.5, 0.5, [
              { offset: 0, color: '#00e5ff' },
              { offset: 1, color: 'rgba(0,229,255,0.3)' },
            ]),
            opacity: baseProvince !== '全国平均' ? 0.3 : 1,
            shadowBlur: 6,
            shadowColor: 'rgba(0,229,255,0.3)',
          },
      symbolSize: isSelected ? 14 : 10,
    };
  });

  chart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(10, 15, 30, 0.95)',
        borderColor: 'rgba(0, 229, 255, 0.5)',
        borderWidth: 1,
        textStyle: {
          color: '#fff',
          fontSize: 12,
        },
        formatter: (params: { seriesName: string; value: number[] }) => {
          // 趋势线不显示 tooltip
          if (params.seriesName === '趋势线') {
            return '';
          }

          // 预测点的 tooltip
          if (params.seriesName === '预测点') {
            const [gfi, outcome] = params.value;
            return `
              <div style="padding: 4px 0;">
                <div style="color: #ff4444; font-weight: bold; font-size: 13px; margin-bottom: 6px;">
                  🔮 预测情景
                </div>
                <div style="margin: 4px 0; display: flex; justify-content: space-between; gap: 20px;">
                  <span style="color: #aaa;">预测绿色金融得分</span>
                  <span style="color: #00e5ff; font-weight: bold;">${gfi.toFixed(4)}</span>
                </div>
                <div style="margin: 4px 0; display: flex; justify-content: space-between; gap: 20px;">
                  <span style="color: #aaa;">预测能耗强度</span>
                  <span style="color: #00ff88; font-weight: bold;">${outcome.toFixed(4)}</span>
                </div>
              </div>
            `;
          }

          // 历史数据点的 tooltip
          if (params.seriesName === '历史数据') {
            const [gfi, outcome, province, year] = params.value;
            return `
              <div style="padding: 4px 0;">
                <div style="color: #00e5ff; font-weight: bold; font-size: 14px; margin-bottom: 8px; border-bottom: 1px solid rgba(0, 229, 255, 0.3); padding-bottom: 4px;">
                  ${province} · ${year}年
                </div>
                <div style="margin: 4px 0; display: flex; justify-content: space-between; gap: 20px;">
                  <span style="color: #aaa;">绿色金融得分</span>
                  <span style="color: #00e5ff; font-weight: bold;">${gfi.toFixed(4)}</span>
                </div>
                <div style="margin: 4px 0; display: flex; justify-content: space-between; gap: 20px;">
                  <span style="color: #aaa;">能耗强度</span>
                  <span style="color: #00ff88; font-weight: bold;">${outcome.toFixed(4)}</span>
                </div>
              </div>
            `;
          }

          return '';
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
          data: processedScatterData,
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
            color: baseProvince !== '全国平均' ? '#FFD700' : '#fff',
            width: 2,
            type: 'dashed',
            shadowBlur: 4,
            shadowColor: baseProvince !== '全国平均' ? 'rgba(255, 215, 0, 0.3)' : 'rgba(255,255,255,0.3)',
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

// 监听省份和年份变化，自动更新预测
watch([selectedProvince, selectedYear], () => {
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
          <div v-if="chartData" class="current-target">
            当前推演对象：<span class="target-name">{{ chartData.base_province }}</span>
            <span class="target-year">{{ chartData.base_year }}年</span>
          </div>
        </div>
        <div class="control-panel">
          <div class="province-selector">
            <div class="selector-label">推演对象</div>
            <el-select
              v-model="selectedProvince"
              placeholder="选择省份"
              clearable
              :disabled="loading"
              class="province-select"
            >
              <el-option label="📍 全国（宏观基准）" value="" />
              <el-option v-for="province in provinceOptions" :key="province" :label="province" :value="province" />
            </el-select>
          </div>
          <div class="divider"></div>
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
          【{{ chartData.base_province }}】预测减排：能耗强度将额外下降
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
.current-target {
  color: rgba(200, 220, 255, 0.7);
  font-size: 12px;
  margin-top: 6px;
  padding: 4px 0;
}
.target-name {
  color: #ffd700;
  font-weight: bold;
  margin: 0 4px;
}
.target-year {
  color: #00e5ff;
  margin-left: 8px;
}
.control-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(0, 229, 255, 0.05);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 6px;
  min-width: 280px;
}
.province-selector {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.selector-label {
  color: rgba(0, 229, 255, 0.8);
  font-size: 11px;
  font-weight: 500;
}
.province-select {
  width: 100%;
  :deep(.el-input__wrapper) {
    background: rgba(10, 15, 30, 0.8);
    border: 1px solid rgba(0, 229, 255, 0.3);
    box-shadow: none;
    transition: all 0.3s ease;
    &:hover {
      border-color: rgba(0, 229, 255, 0.6);
      box-shadow: 0 0 8px rgba(0, 229, 255, 0.3);
    }
  }
  :deep(.el-input__wrapper.is-focus) {
    border-color: #00e5ff;
    box-shadow: 0 0 12px rgba(0, 229, 255, 0.5);
  }
  :deep(.el-input__inner) {
    color: #00e5ff;
    font-size: 12px;
    &::placeholder {
      color: rgba(0, 229, 255, 0.4);
    }
  }
  :deep(.el-input__suffix) {
    .el-icon {
      color: rgba(0, 229, 255, 0.6);
    }
  }
}
.divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.3), transparent);
  margin: 4px 0;
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

// Element Plus 下拉框全局样式覆盖
:deep(.el-select-dropdown) {
  background: rgba(10, 15, 30, 0.95);
  border: 1px solid rgba(0, 229, 255, 0.3);
  box-shadow: 0 4px 20px rgba(0, 229, 255, 0.2);
}
:deep(.el-select-dropdown__item) {
  color: rgba(200, 220, 255, 0.8);
  font-size: 12px;
  &:hover {
    background: rgba(0, 229, 255, 0.15);
    color: #00e5ff;
  }
  &.selected {
    background: rgba(0, 229, 255, 0.2);
    color: #00e5ff;
    font-weight: bold;
  }
}
</style>
