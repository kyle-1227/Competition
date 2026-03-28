<template>
  <div class="biz-carbon-prediction">
    <div class="header-section">
      <div class="module-title">
        <span class="icon">📈</span> 碳排放强度动态预测沙盘 (SDM模型)
      </div>
      <div class="province-selector">
        <span class="label">分析区域：</span>
        <select v-model="selectedProvince" @change="updateChart">
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
        <div class="box-title">📊 SDM模型核心系数 (基于历史面板回归)</div>
        <div class="coef-list">
          <span class="tag">绿色金融(核心): <b>0.1446</b></span>
          <span class="tag">人口&能耗(控制): <b>1.18~1.25</b></span>
          <span class="tag">空间滞后(W_X): <b>-3.69~0.62</b></span>
          <span class="tag">空间自回归(Rho): <b>0.4882</b></span>
        </div>
      </div>
      <div class="result-box">
        <div class="box-title">🎯 2027年 预测结果 ({{ selectedProvince }})</div>
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
import { ref, onMounted, shallowRef, computed, onUnmounted, nextTick } from 'vue';
import * as echarts from 'echarts';

// --- 1. 状态定义 ---
const chartRef = ref<HTMLElement | null>(null);
const chartInstance = shallowRef<echarts.ECharts | null>(null);

const provinceList = ['北京市', '浙江省', '广东省', '内蒙古自治区', '四川省', '新疆维吾尔自治区']; // 示例省份
const selectedProvince = ref('全国');

// 五大自变量控制器 (1.0 表示维持2024年现状，1.2表示强度提升20%)
const controls = ref({
  core: { name: '核心变量 (绿色金融)', value: 1.1 },
  control: { name: '控制变量 (人口/能耗)', value: 1.0 },
  policy: { name: '政策准自然实验 (DID)', value: 1.2 },
  spatial: { name: '空间滞后 (周边溢出)', value: 1.05 },
  mediator: { name: '中介变量 (产业结构)', value: 1.15 }
});

// SDM模型核心回归系数 (用于底层推算)
const modelCoef = { core: 0.1446, control: 1.2510, spatial: -0.0284, rho: 0.4882, policy: -0.05, mediator: -0.08 };

// --- 2. 模拟历史数据生成器 (2000 - 2024) ---
const yearsHistorical = Array.from({length: 25}, (_, i) => 2000 + i);
const yearsFuture = [2025, 2026, 2027];
const allYears = [...yearsHistorical, ...yearsFuture];

// 生成基于省份的历史波动数据
const getHistoricalData = (province: string) => {
  let base = province === '全国' ? 1.5 : (province === '内蒙古自治区' ? 2.8 : 1.0);
  return yearsHistorical.map((year, index) => {
    // 模拟碳排放强度随时间先升后降的倒U型趋势
    const trend = Math.sin(index / 8) * 0.4;
    const noise = (Math.random() - 0.5) * 0.05;
    return Number((base + trend - (index * 0.02) + noise).toFixed(4));
  });
};

// 当前历史数据
const currentHistory = computed(() => getHistoricalData(selectedProvince.value));

// --- 3. 预测推算逻辑 (2025 - 2027) ---
const currentPrediction = computed(() => {
  const lastVal = currentHistory.value[currentHistory.value.length - 1];
  let predicted = [];
  let currentVal = lastVal;

  for (let i = 0; i < yearsFuture.length; i++) {
    // 根据调整的乘数和系数推演
    // 简化公式: ΔY = (Core * Coef) + (Control * Coef) + (Spatial * Coef) ... + (Rho * W_Y)
    const deltaCore = (controls.value.core.value - 1) * modelCoef.core;
    const deltaControl = (controls.value.control.value - 1) * modelCoef.control * 0.1; // 权重缩放
    const deltaPolicy = (controls.value.policy.value - 1) * modelCoef.policy;
    const deltaSpatial = (controls.value.spatial.value - 1) * modelCoef.spatial;
    const deltaMediator = (controls.value.mediator.value - 1) * modelCoef.mediator;
    
    // 综合边际影响
    const netEffect = -(deltaCore + deltaPolicy + deltaMediator - deltaControl - deltaSpatial); 
    
    currentVal = currentVal + netEffect - 0.015; // 基础自然下降0.015
    predicted.push(Number(Math.max(currentVal, 0.1).toFixed(4)));
  }
  return predicted;
});

// 底部结果展示数据
const finalPrediction = computed(() => currentPrediction.value[2] || 0);
const predictionChange = computed(() => {
  const base = currentHistory.value[currentHistory.value.length - 1];
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

// --- 4. 图表渲染 ---
const updateChart = () => {
  if (!chartInstance.value) return;

  const historyData = currentHistory.value;
  const predictData = currentPrediction.value;
  
  // 拼接数据以保持折线连贯
  const padding = new Array(historyData.length - 1).fill(null);
  const connectedPrediction = [...padding, historyData[historyData.length - 1], ...predictData];

  const option = {
    // 💡 核心亮点：荧光毛玻璃浮框 Tooltip
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'transparent',
      padding: 0,
      borderWidth: 0,
      formatter: (params: any) => {
        const year = params[0].axisValue;
        const isPredict = year >= 2025;
        const val = params.find((p:any) => p.value !== null)?.value || 0;
        
        // 自定义 HTML 毛玻璃样式
        return `
          <div style="
            background: rgba(13, 20, 36, 0.65);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 255, 204, 0.6);
            box-shadow: 0 0 20px rgba(0, 255, 204, 0.4), inset 0 0 10px rgba(0,255,204,0.1);
            border-radius: 8px;
            padding: 12px 16px;
            color: #fff;
            font-family: sans-serif;
            min-width: 220px;
          ">
            <div style="border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 8px; margin-bottom: 8px; font-weight: bold; color: #00ffcc; font-size: 15px;">
              📍 ${selectedProvince.value} | 📅 ${year}年 ${isPredict ? '(预测)' : '(历史)'}
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px;">
              <span style="color: #aaa;">碳排放强度 (因变量)</span>
              <span style="color: #fff; font-weight: bold;">${val.toFixed(4)}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px;">
              <span style="color: #888;">绿色金融强度设定</span>
              <span style="color: #00ffcc;">${(controls.value.core.value * 100).toFixed(0)}%</span>
            </div>
             <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px;">
              <span style="color: #888;">政策及中介效能设定</span>
              <span style="color: #ffaa00;">${(controls.value.policy.value * 100).toFixed(0)}%</span>
            </div>
          </div>
        `;
      }
    },
    grid: { top: 52, left: 12, right: 20, bottom: 28, containLabel: true },
    xAxis: {
      type: 'category',
      data: allYears,
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
        data: [...historyData, ...new Array(yearsFuture.length).fill(null)],
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

// --- 5. 生命周期管理 ---
let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (chartRef.value) {
    chartInstance.value = echarts.init(chartRef.value);
    updateChart();
    window.addEventListener('resize', resizeHandler);
    resizeObserver = new ResizeObserver(() => resizeHandler());
    resizeObserver.observe(chartRef.value);
    scheduleChartResize();
  }
});

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

/* 3. 底部信息面板 */
.bottom-panel {
  display: flex;
  gap: 14px;
  margin-top: 12px;
  flex-shrink: 0;
  min-height: 72px;

  .coef-box,
  .result-box {
    border-radius: 8px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    justify-content: center;
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
    }

    .coef-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 12px;

      .tag {
        font-size: 11px;
        color: #e2e8f0;
        background: rgba(255, 255, 255, 0.06);
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid rgba(148, 163, 184, 0.12);

        b {
          color: #7dd3fc;
          font-family: 'DIN Alternate', 'DIN', ui-monospace, sans-serif;
          font-weight: 600;
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
    }

    .result-data {
      display: flex;
      gap: 20px;
      align-items: stretch;

      .val-group {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .label {
          font-size: 11px;
          color: #94a3b8;
        }

        .number {
          font-size: 20px;
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
</style>