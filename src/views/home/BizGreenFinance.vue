<script setup lang="ts">
import { useGreenFinanceRadar, useGreenFinanceRose } from './hooks/useChart';
import {
  useGreenFinanceMap,
  createHiddenGfTooltip,
  type GfMapTooltipState,
} from './hooks/useMap';
import {
  realProvinceData,
  gfDrillProvince,
  fetchCityData,
  selectedYear,
  excludeProvincesWithoutPanelData,
  NO_PANEL_DATA_REGIONS_LEGEND,
} from './hooks/provinceData';

const noDataRegionLabel = NO_PANEL_DATA_REGIONS_LEGEND;

const selectedProv = ref('北京市');

const mapAreaRef = ref<HTMLElement | null>(null);
const gfMapTooltip = ref<GfMapTooltipState>(createHiddenGfTooltip());

const gfTooltipStyle = computed(() => {
  const t = gfMapTooltip.value;
  const area = mapAreaRef.value;
  if (!t.visible || !area) return { display: 'none' as const };
  const pad = 10;
  const estW = 292;
  const estH = 400;
  const aw = area.clientWidth;
  const ah = area.clientHeight;
  let left = t.left;
  let top = t.top;
  if (left + estW > aw - pad) left = Math.max(pad, aw - estW - pad);
  if (top + estH > ah - pad) top = Math.max(pad, ah - estH - pad);
  left = Math.max(pad, left);
  top = Math.max(pad, top);
  return {
    left: `${left}px`,
    top: `${top}px`,
  };
});

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
useGreenFinanceMap(selectedProv, gfMapTooltip);

const provList = computed(() => {
  const rows = realProvinceData.value;
  if (rows.length > 0) {
    return excludeProvincesWithoutPanelData([...rows].map((r) => r.province)).sort((a, b) =>
      a.localeCompare(b, 'zh-CN'),
    );
  }
  return [];
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

/** 与省级接口联调：有数据时用 Σ(gdp×score)、Σ(碳/1e4) 等 */
const boardStats = computed(() => {
  const rows = realProvinceData.value;
  if (!rows.length) {
    return {
      totalGreenFinance: 0,
      totalCarbon: 0,
      avgScore: 0,
      coveredProvinces: 0,
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
      <div ref="mapAreaRef" class="map-area">
        <button
          v-if="gfDrillProvince"
          type="button"
          class="gf-back-map"
          @click="clearGfDrill"
        >
          返回全国视角
        </button>
        <div id="gf-map" />
        <div
          v-show="gfMapTooltip.visible"
          class="gf-map-tooltip"
          :style="gfTooltipStyle"
        >
          <div class="gf-map-tooltip__head">
            <span class="gf-map-tooltip__name">{{ gfMapTooltip.regionName }}</span>
            <span class="gf-map-tooltip__year">{{ gfMapTooltip.year }} 年</span>
          </div>
          <div class="gf-map-tooltip__score-row">
            <span class="gf-map-tooltip__score-label">综合指数</span>
            <span class="gf-map-tooltip__score-val">{{ gfMapTooltip.scoreText }}</span>
            <span v-if="gfMapTooltip.scoreText !== '—'" class="gf-map-tooltip__score-unit">分</span>
          </div>
          <div class="gf-map-tooltip__grid">
            <div
              v-for="(cell, idx) in gfMapTooltip.rows"
              :key="idx"
              class="gf-map-tooltip__cell"
            >
              <span class="gf-map-tooltip__cell-label">{{ cell.label }}</span>
              <span class="gf-map-tooltip__cell-value">{{ cell.value }}</span>
            </div>
          </div>
        </div>
        <div class="map-legend">
          <div class="legend-title">绿色金融综合指数</div>
          <div class="legend-bar" />
          <div class="legend-labels">
            <span>低</span>
            <span>高</span>
          </div>
          <div class="legend-note">
            <span class="swatch swatch--muted" />
            <span>灰色：无面板数据区域（{{ noDataRegionLabel }}），不可选</span>
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
    width: min(240px, 42vw);
  }
  .legend-note {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    margin-top: 8px;
    padding-top: 6px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    color: rgba(200, 210, 225, 0.85);
    font-size: 10px;
    line-height: 1.35;
  }
  .swatch {
    flex-shrink: 0;
    width: 14px;
    height: 10px;
    border-radius: 2px;
    margin-top: 2px;
    border: 1px solid rgba(255, 255, 255, 0.15);
  }
  .swatch--muted {
    background: #5c6470;
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
  .gf-map-tooltip {
    position: absolute;
    z-index: 1001;
    width: min(292px, calc(100% - 20px));
    max-height: min(400px, calc(100% - 24px));
    overflow: auto;
    pointer-events: none;
    padding: 12px 14px 14px;
    border-radius: 10px;
    background: rgba(10, 18, 40, 0.78);
    border: 1px solid rgba(0, 229, 255, 0.42);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow:
      0 0 24px rgba(0, 229, 255, 0.22),
      0 8px 32px rgba(0, 0, 0, 0.45),
      inset 0 0 28px rgba(0, 229, 255, 0.06);
    &::-webkit-scrollbar {
      width: 4px;
    }
    &::-webkit-scrollbar-thumb {
      background: rgba(0, 229, 255, 0.2);
      border-radius: 2px;
    }
  }
  .gf-map-tooltip__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }
  .gf-map-tooltip__name {
    color: rgba(0, 229, 255, 0.92);
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-shadow: 0 0 12px rgba(0, 229, 255, 0.35);
  }
  .gf-map-tooltip__year {
    flex-shrink: 0;
    font-size: 11px;
    color: rgba(200, 220, 255, 0.55);
    letter-spacing: 1px;
  }
  .gf-map-tooltip__score-row {
    display: flex;
    align-items: baseline;
    gap: 6px;
    margin-bottom: 10px;
  }
  .gf-map-tooltip__score-label {
    font-size: 11px;
    color: rgba(200, 220, 255, 0.5);
    letter-spacing: 1px;
  }
  .gf-map-tooltip__score-val {
    font-size: 22px;
    font-weight: 900;
    font-family: 'DIN Alternate', 'DIN', 'Oswald', 'Rajdhani', 'Arial Black', sans-serif;
    letter-spacing: -0.5px;
    background: linear-gradient(180deg, #ffd54f, #ff8f00);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 0 8px rgba(255, 213, 79, 0.45));
  }
  .gf-map-tooltip__score-unit {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.4);
  }
  .gf-map-tooltip__grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px 12px;
  }
  .gf-map-tooltip__cell {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 6px 0;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }
  .gf-map-tooltip__cell-label {
    font-size: 10px;
    color: rgba(200, 210, 225, 0.55);
    letter-spacing: 0.5px;
  }
  .gf-map-tooltip__cell-value {
    font-size: 12px;
    font-weight: 600;
    color: rgba(230, 240, 255, 0.92);
    font-variant-numeric: tabular-nums;
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
