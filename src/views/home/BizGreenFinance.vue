<script setup lang="ts">
import { useGreenFinanceRadar, useGreenFinanceRose } from './hooks/useChart';
import { useGreenFinanceMap } from './hooks/useMap';
import { mockGreenFinanceData } from './hooks/mockData';
import {
  realProvinceData,
  gfDrillProvince,
  fetchCityData,
  selectedYear,
} from './hooks/provinceData';

const selectedProv = ref('北京市');

function clearGfDrill() {
  gfDrillProvince.value = '';
}

watch([gfDrillProvince, selectedYear], () => {
  if (gfDrillProvince.value) {
    fetchCityData(gfDrillProvince.value, selectedYear.value);
  }
});

watch(selectedProv, (v) => {
  if (gfDrillProvince.value && v !== gfDrillProvince.value) {
    gfDrillProvince.value = '';
  }
});
useGreenFinanceRadar(selectedProv);
useGreenFinanceRose(selectedProv);
useGreenFinanceMap(selectedProv);

const provList = computed(() => {
  const rows = realProvinceData.value;
  if (rows.length > 0) {
    return [...rows].map((r) => r.province).sort((a, b) => a.localeCompare(b, 'zh-CN'));
  }
  return mockGreenFinanceData.map((d) => d.province);
});

watch(
  provList,
  (list) => {
    if (list.length && !list.includes(selectedProv.value)) {
      selectedProv.value = list[0];
    }
  },
  { immediate: true },
);

/** 与省级接口联调：有数据时用 Σ(gdp×score)、Σ(碳/1e4) 等；无数据时沿用 mock 展示占位 */
const boardStats = computed(() => {
  const rows = realProvinceData.value;
  if (!rows.length) {
    const n = mockGreenFinanceData.length;
    return {
      totalGreenFinance: 286452.8,
      totalCarbon: 134876.5,
      avgScore: +((mockGreenFinanceData.reduce((s, d) => s + d.score, 0) / n) * 100).toFixed(1),
      coveredProvinces: n,
    };
  }
  const totalGreenFinance = Math.round(rows.reduce((s, r) => s + (r.gdp || 0) * (r.score || 0), 0));
  const totalCarbon = Math.round(rows.reduce((s, r) => s + (r.carbonEmission || 0) / 10000, 0));
  const avgScore = +((rows.reduce((s, r) => s + r.score, 0) / rows.length) * 100).toFixed(1);
  return {
    totalGreenFinance,
    totalCarbon,
    avgScore,
    coveredProvinces: rows.length,
  };
});

const displayProv = computed(() => selectedProv.value.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, ''));
</script>
<template>
  <div class="biz-wrap">
    <div class="biz-wrap-sidebar">
      <div class="prov-selector">
        <div class="selector-label">选择省份</div>
        <el-select v-model="selectedProv" placeholder="选择省份" size="default" popper-class="dark-popper">
          <el-option
            v-for="item in provList"
            :key="item"
            :label="item.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, '')"
            :value="item"
          />
        </el-select>
      </div>
      <div class="sidebar-section">
        <div class="chart-title">{{ displayProv }} · 七维雷达图</div>
        <div id="gf-radar" class="chart-box" />
      </div>
      <div class="sidebar-section">
        <div id="gf-rose" class="chart-box" />
      </div>
    </div>
    <div class="biz-wrap-main">
      <div class="data-board">
        <div class="board-item">
          <div class="board-label">全国绿色金融总规模</div>
          <div class="board-value cyan">
            <span class="board-num">{{ boardStats.totalGreenFinance.toLocaleString() }}</span>
            <span class="board-unit">亿元</span>
          </div>
        </div>
        <div class="board-divider" />
        <div class="board-item">
          <div class="board-label">全国碳排放合计</div>
          <div class="board-value green">
            <span class="board-num">{{ boardStats.totalCarbon.toLocaleString() }}</span>
            <span class="board-unit">万吨CO₂</span>
          </div>
        </div>
        <div class="board-divider" />
        <div class="board-item">
          <div class="board-label">全国均值指数</div>
          <div class="board-value gold">
            <span class="board-num">{{ boardStats.avgScore }}</span>
            <span class="board-unit">分</span>
          </div>
        </div>
        <div class="board-divider" />
        <div class="board-item">
          <div class="board-label">覆盖省份</div>
          <div class="board-value purple">
            <span class="board-num">{{ boardStats.coveredProvinces }}</span>
            <span class="board-unit">个</span>
          </div>
        </div>
      </div>
      <div class="map-area">
        <button
          v-if="gfDrillProvince"
          type="button"
          class="gf-back-map"
          @click="clearGfDrill"
        >
          返回全国视角
        </button>
        <div id="gf-map" />
        <div class="map-legend">
          <div class="legend-title">绿色金融综合指数</div>
          <div class="legend-bar" />
          <div class="legend-labels">
            <span>低</span>
            <span>高</span>
          </div>
        </div>
        <div class="map-approve">本底图基于国家地理信息公共服务平台标准地图制作，审图号：GS(2025)5996号</div>
      </div>
    </div>
  </div>
</template>
<script lang="ts">
export default { name: 'BizGreenFinance' };
</script>
<style lang="scss" scoped>
.biz-wrap {
  display: flex;
  height: 100%;
  padding: 10px 0 25px 0;
  &-sidebar {
    flex: 0 0 25%;
    max-width: 25%;
    padding: 6px 10px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    overflow-y: auto;
    &::-webkit-scrollbar {
      width: 3px;
    }
    &::-webkit-scrollbar-thumb {
      background: rgba(0, 229, 255, 0.2);
      border-radius: 2px;
    }
  }
  &-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
}
.data-board {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  margin: 0 10px 6px;
  background: rgba(10, 15, 30, 0.8);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 8px;
  backdrop-filter: blur(6px);
}
.board-item {
  flex: 1;
  text-align: center;
  padding: 2px 12px;
}
.board-label {
  color: rgba(200, 220, 255, 0.5);
  font-size: 11px;
  letter-spacing: 1px;
  margin-bottom: 2px;
}
.board-value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 4px;
}
.board-num {
  font-size: 26px;
  font-weight: 900;
  font-family: 'DIN Alternate', 'DIN', 'Oswald', 'Rajdhani', 'Arial Black', sans-serif;
  letter-spacing: -0.5px;
}
.board-unit {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  font-weight: normal;
}
.board-value.cyan .board-num {
  background: linear-gradient(180deg, #00ffff, #0088aa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 8px rgba(0, 255, 255, 0.4));
}
.board-value.green .board-num {
  background: linear-gradient(180deg, #00ff88, #00aa44);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 8px rgba(0, 255, 136, 0.4));
}
.board-value.gold .board-num {
  background: linear-gradient(180deg, #ffd54f, #ff8f00);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 8px rgba(255, 213, 79, 0.4));
}
.board-value.purple .board-num {
  background: linear-gradient(180deg, #ce93d8, #7b1fa2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 8px rgba(206, 147, 216, 0.4));
}
.board-divider {
  width: 1px;
  height: 36px;
  background: linear-gradient(180deg, transparent, rgba(0, 229, 255, 0.25), transparent);
  flex-shrink: 0;
}
.gf-back-map {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 1000;
  padding: 8px 16px;
  font-size: 12px;
  letter-spacing: 1px;
  color: #00e5ff;
  cursor: pointer;
  background: rgba(10, 18, 40, 0.92);
  border: 1px solid rgba(0, 229, 255, 0.45);
  border-radius: 6px;
  box-shadow:
    0 0 12px rgba(0, 229, 255, 0.25),
    inset 0 0 20px rgba(0, 229, 255, 0.06);
  transition:
    box-shadow 0.2s,
    border-color 0.2s;
}
.gf-back-map:hover {
  border-color: rgba(0, 255, 255, 0.8);
  box-shadow:
    0 0 18px rgba(0, 229, 255, 0.45),
    inset 0 0 24px rgba(0, 229, 255, 0.1);
}
.map-area {
  flex: 1;
  position: relative;
  min-height: 0;
  #gf-map {
    width: 100%;
    height: 100%;
  }
  .map-legend {
    position: absolute;
    top: 10px;
    left: 10px;
    z-index: 999;
    background: rgba(10, 15, 30, 0.85);
    border: 1px solid rgba(0, 229, 255, 0.2);
    border-radius: 6px;
    padding: 8px 12px;
    backdrop-filter: blur(4px);
    width: 140px;
  }
  .legend-title {
    color: rgba(0, 229, 255, 0.8);
    font-size: 11px;
    margin-bottom: 6px;
  }
  .legend-bar {
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(90deg, #1a237e, #01579b, #006064, #827717, #f57f17, #ffab00);
  }
  .legend-labels {
    display: flex;
    justify-content: space-between;
    color: rgba(255, 255, 255, 0.5);
    font-size: 10px;
    margin-top: 2px;
  }
  .map-approve {
    position: absolute;
    bottom: 10px;
    right: 10px;
    color: rgba(255, 255, 255, 0.5);
    z-index: 999;
    font-size: 12px;
  }
}
.sidebar-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.chart-box {
  flex: 1;
  min-height: 240px;
}
.chart-title {
  text-align: center;
  color: rgba(0, 229, 255, 0.85);
  font-size: 13px;
  padding-bottom: 4px;
  letter-spacing: 1px;
  flex-shrink: 0;
}
.prov-selector {
  flex: 0 0 auto;
  margin-bottom: 4px;
  background: rgba(10, 15, 30, 0.7);
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 8px;
  padding: 8px 12px;
  backdrop-filter: blur(4px);
  .selector-label {
    color: rgba(0, 229, 255, 0.7);
    font-size: 11px;
    margin-bottom: 4px;
    letter-spacing: 1px;
  }
  :deep(.el-select) {
    width: 100%;
  }
  :deep(.el-select__wrapper) {
    background: rgba(0, 229, 255, 0.06) !important;
    border: 1px solid rgba(0, 229, 255, 0.25) !important;
    box-shadow: 0 0 8px rgba(0, 229, 255, 0.08) !important;
    border-radius: 6px !important;
    transition: border-color 0.3s, box-shadow 0.3s;
    &:hover,
    &.is-focused {
      border-color: rgba(0, 229, 255, 0.5) !important;
      box-shadow: 0 0 12px rgba(0, 229, 255, 0.15) !important;
    }
  }
  :deep(.el-select__selected-item) {
    color: #00e5ff !important;
    font-weight: bold;
  }
  :deep(.el-select__placeholder) {
    color: rgba(0, 229, 255, 0.5) !important;
  }
  :deep(.el-select__suffix) {
    color: rgba(0, 229, 255, 0.6) !important;
  }
  :deep(.el-input__wrapper) {
    background: rgba(0, 229, 255, 0.06) !important;
    border: 1px solid rgba(0, 229, 255, 0.25) !important;
    box-shadow: 0 0 8px rgba(0, 229, 255, 0.08) !important;
    border-radius: 6px !important;
    &:hover,
    &.is-focus {
      border-color: rgba(0, 229, 255, 0.5) !important;
      box-shadow: 0 0 12px rgba(0, 229, 255, 0.15) !important;
    }
  }
  :deep(.el-input__inner) {
    color: #00e5ff !important;
    font-weight: bold;
  }
  :deep(.el-input__suffix) {
    color: rgba(0, 229, 255, 0.6) !important;
  }
}
</style>
