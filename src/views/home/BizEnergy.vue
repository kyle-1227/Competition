<script setup lang="ts">
import { ref, onMounted, watch, nextTick, inject, type Ref } from 'vue';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';
import { predictEnergyIntensity, type PredictEnergyResponse } from '@/api/modules/dashboard';
import { selectedProvince, selectedYear } from './hooks/provinceData';

const policyIntensity = ref(0);
const chartData = ref<PredictEnergyResponse | null>(null);
const loading = ref(false);
let chart: echarts.ECharts | null = null;

let debounceTimer: ReturnType<typeof setTimeout> | null = null;
/** v-show 隐藏时容器宽高为 0，首次 renderChart 会跳过；切换 Tab 后需重绘 */
let chartDimensionRetry = 0;
const activeTab = inject<Ref<string>>('activeTab', ref('sandbox'));

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
      ElMessage.error(res.msg || '能耗强度预测失败');
    }
  } catch (error) {
    console.error('预测接口调用失败:', error);
    ElMessage.error('能耗预测请求失败，请检查网络或服务');
  } finally {
    loading.value = false;
  }
}

function renderChart() {
  if (!chartData.value) return;

  const el = document.getElementById('energy-scatter');
  if (!el) return;

  // 隐藏 Tab 下宽高为 0；仅在能耗 Tab 可见时重试布局，避免后台空转
  if (el.clientWidth === 0 || el.clientHeight === 0) {
    if (activeTab.value === 'energy' && chartDimensionRetry < 30) {
      chartDimensionRetry += 1;
      requestAnimationFrame(() => renderChart());
    }
    return;
  }
  chartDimensionRetry = 0;

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

  const processedScatterData = scatterData.map((item) => {
    const [, , province] = item;
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
          if (params.seriesName === '趋势线') return '';

          if (params.seriesName === '预测点') {
            const [gfi, outcome] = params.value;
            return `
              <div style="padding: 4px 0;">
                <div style="color: #ff6b6b; font-weight: bold; font-size: 13px; margin-bottom: 6px;">
                  预测情景
                </div>
                <div style="margin: 4px 0; display: flex; justify-content: space-between; gap: 20px;">
                  <span style="color: #aaa;">预测绿色金融指数</span>
                  <span style="color: #00e5ff; font-weight: bold;">${gfi.toFixed(4)}</span>
                </div>
                <div style="margin: 4px 0; display: flex; justify-content: space-between; gap: 20px;">
                  <span style="color: #aaa;">预测能耗强度</span>
                  <span style="color: #00ff88; font-weight: bold;">${outcome.toFixed(4)}</span>
                </div>
              </div>
            `;
          }

          if (params.seriesName === '历史数据') {
            const [gfi, outcome, province, year] = params.value;
            return `
              <div style="padding: 4px 0;">
                <div style="color: #00e5ff; font-weight: bold; font-size: 14px; margin-bottom: 8px; border-bottom: 1px solid rgba(0, 229, 255, 0.3); padding-bottom: 4px;">
                  ${province} · ${year}年
                </div>
                <div style="margin: 4px 0; display: flex; justify-content: space-between; gap: 20px;">
                  <span style="color: #aaa;">绿色金融指数</span>
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
      grid: { left: 62, right: '7%', top: 48, bottom: 50 },
      textStyle: {
        fontFamily: "'Noto Sans SC', 'Microsoft YaHei', 'PingFang SC', sans-serif",
      },
      xAxis: {
        type: 'value',
        name: '绿色金融指数（自变量）',
        nameLocation: 'middle',
        nameGap: 28,
        nameTextStyle: {
          color: 'rgba(0, 238, 255, 0.95)',
          fontSize: 13,
          fontWeight: 600,
          fontFamily: "'Noto Sans SC', 'Microsoft YaHei', 'PingFang SC', sans-serif",
        },
        axisLabel: { color: '#aaa', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } },
      },
      yAxis: {
        type: 'value',
        name: '能耗强度（因变量）',
        nameLocation: 'middle',
        nameGap: 40,
        nameTextStyle: {
          color: 'rgba(0, 238, 255, 0.95)',
          fontSize: 13,
          fontWeight: 600,
          fontFamily: "'Noto Sans SC', 'Microsoft YaHei', 'PingFang SC', sans-serif",
        },
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

watch([selectedProvince, selectedYear], () => {
  handlePredict();
});

watch([policyIntensity, chartData], () => {
  nextTick(() => chart?.resize());
});

watch(
  () => activeTab.value,
  (tab) => {
    if (tab !== 'energy') return;
    nextTick(() => {
      requestAnimationFrame(() => {
        chartDimensionRetry = 0;
        if (chartData.value) renderChart();
        else handlePredict();
        nextTick(() => chart?.resize());
      });
    });
  },
);
</script>

<template>
  <div class="biz-wrap">
    <div class="biz-wrap-content">
      <div class="energy-toolbar">
        <div class="energy-toolbar-left">
          <div class="title-row zh-text">
            <span class="chart-title">
              <span class="t-em">绿色金融指数</span><span class="t-vs"> vs </span><span class="t-em">能耗强度</span>
            </span>
            <span class="chart-subtitle">· 预测沙盘</span>
          </div>
          <div class="chart-desc zh-text">
            横轴：绿色金融指数（自变量）。纵轴：能耗强度（因变量）。滑块表示在现有绿色金融投入基础上追加的比例（%）。
          </div>
          <div v-if="chartData" class="current-target zh-text">
            <span class="target-label">推演省份</span>
            <span class="target-value">{{ chartData.base_province }}</span>
          </div>
        </div>
        <div class="energy-controls-card">
          <div class="control-item control-item-select">
            <span class="label">省份</span>
            <el-select
              v-model="selectedProvince"
              class="energy-province-select"
              popper-class="energy-province-dropdown"
              placeholder="选择省份"
              clearable
              :disabled="loading"
              filterable
              size="default"
            >
              <el-option label="全国（宏观基准）" value="" />
              <el-option v-for="province in provinceOptions" :key="province" :label="province" :value="province" />
            </el-select>
          </div>
          <div class="control-divider" />
          <div class="control-item slider-item">
            <span class="label">追加投入比例</span>
            <el-slider
              v-model="policyIntensity"
              class="energy-slider"
              :min="0"
              :max="100"
              :step="5"
              :disabled="loading"
              @change="onSliderChange"
            />
            <span class="value">{{ policyIntensity }}%</span>
          </div>
        </div>
      </div>

      <div v-if="chartData && policyIntensity > 0" class="predict-strip">
        <div class="result-card zh-text">
          <div class="result-header">
            <span class="result-prov">【{{ chartData.base_province }}】</span>
            <span class="result-tag">沙盘推演</span>
          </div>
          <div class="result-main">
            <span class="result-label">能耗强度</span>
            <span class="result-hint">相对基准</span>
            <span class="result-arrow">↓</span>
            <span class="result-value">{{ Math.abs(chartData.predicted_drop_percent).toFixed(2) }}%</span>
          </div>
        </div>
      </div>

      <div class="chart-box-wrapper">
        <div id="energy-scatter" v-loading="loading" class="chart-box" />
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
  padding: 6px 12px 14px;
  font-family: var(--el-font-family);
}

/* 关键文案与整站同源字体（见 index.scss :root） */
.zh-text {
  font-family: var(--el-font-family) !important;
  text-rendering: optimizeLegibility;
}

.t-em {
  font-weight: 600;
}

.t-vs {
  font-weight: 400;
  opacity: 0.75;
  margin: 0 2px;
}

.biz-wrap-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  gap: 0;
}

.energy-toolbar {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px 14px;
  padding-bottom: 6px;
}

.energy-toolbar-left {
  flex: 1;
  min-width: 220px;
  text-align: left;
}

.title-row {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px 8px;
}

.chart-title {
  color: rgba(0, 229, 255, 0.92);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.chart-subtitle {
  color: rgba(0, 229, 255, 0.5);
  font-size: 12px;
  font-weight: 400;
}

.chart-desc {
  color: rgba(200, 220, 255, 0.48);
  font-size: 11px;
  line-height: 1.4;
  margin-top: 3px;
  max-width: 52em;
}

.current-target {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: 11px;
}

.target-label {
  color: rgba(200, 220, 255, 0.55);
  white-space: nowrap;
}

.target-value {
  color: #ffd700;
  font-weight: 600;
  padding: 2px 8px;
  background: rgba(255, 215, 0, 0.1);
  border: 1px solid rgba(255, 215, 0, 0.28);
  border-radius: 4px;
}

.energy-controls-card {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
  padding: 8px 12px;
  background: rgba(10, 15, 30, 0.88);
  border: 1px solid rgba(0, 229, 255, 0.22);
  border-radius: 8px;
  backdrop-filter: blur(8px);
  flex-shrink: 0;
}

.control-divider {
  width: 1px;
  height: 22px;
  background: linear-gradient(180deg, transparent, rgba(0, 229, 255, 0.28), transparent);
}

.control-item {
  display: flex;
  align-items: center;
  gap: 6px;

  .label {
    color: rgba(0, 229, 255, 0.85);
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
  }

  .value {
    color: #00ff88;
    font-size: 12px;
    font-weight: 700;
    min-width: 30px;
    text-align: right;
  }

  &.slider-item {
    gap: 8px;
  }

  :deep(.energy-slider.el-slider) {
    width: 128px;
    --el-slider-runway-bg-color: rgba(8, 14, 28, 0.95);
    --el-color-primary: #00e5ff;
  }

  :deep(.el-slider__runway) {
    height: 5px;
    border: 1px solid rgba(0, 229, 255, 0.28);
    border-radius: 3px;
  }

  :deep(.el-slider__bar) {
    background: linear-gradient(90deg, #00e5ff, #00ff88);
    height: 5px;
    border-radius: 3px;
  }

  :deep(.el-slider__button) {
    width: 12px;
    height: 12px;
    border: 2px solid #00e5ff;
    background: #0a0f1e;
    box-shadow: 0 0 6px rgba(0, 229, 255, 0.45);

    &:hover {
      transform: scale(1.12);
    }
  }
}

// 省份选择：触发器（科技风描边 + 略宽以容纳省名）
.control-item-select {
  :deep(.energy-province-select) {
    width: 158px;
    min-width: 140px;
  }

  :deep(.energy-province-select .el-input__wrapper) {
    border-radius: 6px;
    min-height: 32px;
    padding: 0 10px 0 12px;
    /* 覆盖 Element Plus 默认浅色底，避免大屏上出现「白底」下拉框 */
    --el-input-bg-color: rgba(8, 14, 28, 0.98);
    --el-fill-color-blank: rgba(8, 14, 28, 0.98);
    background: linear-gradient(135deg, rgba(6, 14, 28, 0.98) 0%, rgba(10, 22, 42, 0.92) 100%) !important;
    border: 1px solid rgba(0, 229, 255, 0.38);
    box-shadow:
      inset 0 1px 0 rgba(0, 229, 255, 0.12),
      0 2px 8px rgba(0, 0, 0, 0.25);
    transition:
      border-color 0.2s ease,
      box-shadow 0.2s ease,
      background 0.2s ease;

    &:hover {
      border-color: rgba(0, 229, 255, 0.62);
      box-shadow:
        inset 0 1px 0 rgba(0, 229, 255, 0.18),
        0 0 14px rgba(0, 229, 255, 0.12);
    }
  }

  :deep(.energy-province-select .el-input__wrapper.is-focus) {
    border-color: #00e5ff;
    box-shadow:
      0 0 0 1px rgba(0, 229, 255, 0.45),
      0 0 0 1px rgba(0, 229, 255, 0.15) inset,
      0 0 20px rgba(0, 229, 255, 0.2);
  }

  :deep(.energy-province-select .el-input__wrapper.is-disabled) {
    opacity: 0.55;
    cursor: not-allowed;
  }

  :deep(.energy-province-select .el-input__inner) {
    color: rgba(255, 255, 255, 0.95);
    font-size: 12px;
    font-weight: 500;
    height: 30px;
    line-height: 30px;

    &::placeholder {
      color: rgba(180, 210, 255, 0.45);
    }
  }

  :deep(.energy-province-select .el-select__caret) {
    color: rgba(0, 229, 255, 0.8);
    font-size: 13px;
    transition: color 0.2s ease;
  }

  :deep(.energy-province-select .el-input__wrapper.is-focus .el-select__caret) {
    color: #00e5ff;
  }
}

.predict-strip {
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  padding: 0 0 8px;
  animation: predictFadeIn 0.35s ease;
}

.result-card {
  box-sizing: border-box;
  width: 100%;
  max-width: 560px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: linear-gradient(
    135deg,
    rgba(12, 22, 42, 0.78) 0%,
    rgba(8, 16, 32, 0.85) 100%
  );
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(0, 229, 255, 0.32);
  border-radius: 10px;
  box-shadow:
    inset 0 1px 0 rgba(0, 229, 255, 0.22),
    0 6px 24px rgba(0, 0, 0, 0.35),
    0 0 20px rgba(0, 229, 255, 0.06);
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px 10px;
  line-height: 1.4;
}

.result-prov {
  color: rgba(0, 229, 255, 0.95);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.result-tag {
  color: rgba(180, 220, 255, 0.88);
  font-size: 13px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: 6px;
  border: 1px solid rgba(0, 229, 255, 0.28);
  background: rgba(0, 229, 255, 0.06);
}

.result-main {
  display: flex;
  align-items: baseline;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px 10px;
}

.result-label {
  color: rgba(220, 232, 255, 0.96);
  font-size: 16px;
  font-weight: 700;
}

.result-hint {
  color: rgba(180, 200, 230, 0.65);
  font-size: 12px;
  font-weight: 400;
}

.result-arrow {
  color: #00ff88;
  font-size: 20px;
  font-weight: bold;
  line-height: 1;
  animation: bounce 1.5s ease-in-out infinite;
}

.result-value {
  color: #5aebff;
  font-size: 26px;
  font-weight: 800;
  font-family: 'DIN Alternate', 'DIN', 'Arial', sans-serif;
  text-shadow: 0 0 16px rgba(0, 229, 255, 0.55);
  letter-spacing: 0.5px;
}

@keyframes predictFadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes bounce {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-3px);
  }
}

.chart-box-wrapper {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.chart-box {
  flex: 1;
  min-height: 0;
  width: 100%;
}

</style>

<style lang="scss">
/* 下拉层 teleport 到 body，须 popper-class + 非 scoped */
.energy-province-dropdown.el-select-dropdown,
.energy-province-dropdown.el-popper {
  background: linear-gradient(165deg, rgba(6, 14, 28, 0.98), rgba(10, 22, 44, 0.96)) !important;
  border: 1px solid rgba(0, 229, 255, 0.38) !important;
  border-radius: 8px !important;
  backdrop-filter: blur(16px) saturate(1.15);
  -webkit-backdrop-filter: blur(16px) saturate(1.15);
  box-shadow:
    0 0 0 1px rgba(0, 229, 255, 0.08) inset,
    0 12px 40px rgba(0, 0, 0, 0.55),
    0 0 28px rgba(0, 229, 255, 0.08);
  padding: 6px 0;
}

.energy-province-dropdown .el-select-dropdown__item {
  position: relative;
  margin: 0 6px;
  padding: 9px 14px 9px 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.35;
  color: rgba(210, 225, 255, 0.92);
  font-family: var(--el-font-family);
  transition:
    background 0.2s ease,
    color 0.2s ease;
}

.energy-province-dropdown .el-select-dropdown__item:hover,
.energy-province-dropdown .el-select-dropdown__item.hover,
.energy-province-dropdown .el-select-dropdown__item.is-hovering {
  background: rgba(0, 229, 255, 0.14);
  color: #fff;
}

.energy-province-dropdown .el-select-dropdown__item.selected,
.energy-province-dropdown .el-select-dropdown__item.is-selected {
  background: linear-gradient(90deg, rgba(0, 229, 255, 0.24), rgba(0, 229, 255, 0.06));
  color: #00e5ff;
  font-weight: 600;
  box-shadow: inset 3px 0 0 #00e5ff;
}

.energy-province-dropdown .el-scrollbar__bar.is-vertical {
  width: 5px;
}

.energy-province-dropdown .el-scrollbar__thumb {
  background: rgba(0, 229, 255, 0.35);
  border-radius: 3px;
}

.energy-province-dropdown .el-select-dropdown__wrap {
  max-height: min(320px, 40vh);
}
</style>
