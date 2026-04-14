<script setup lang="ts">
import { useGreenFinanceRadar, useGreenFinanceTop10Bar } from './hooks/useChart';
import {
  useGreenFinanceMap,
  createHiddenGfTooltip,
  type GfMapTooltipState,
} from './hooks/useMap';
import {
  realProvinceData,
  gfDrillProvince,
  gfDrillCity,
  gfRadarCityHoverGeoName,
  fetchCityData,
  fetchProvinceData,
  selectedYear,
  timelineYear,
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
  if (gfDrillCity.value) {
    gfDrillCity.value = '';
    gfRadarCityHoverGeoName.value = '';
    return;
  }
  gfDrillProvince.value = '';
  gfRadarCityHoverGeoName.value = '';
}

const yearMarks = {
  2000: '2000',
  2005: '2005',
  2010: '2010',
  2015: '2015',
  2020: '2020',
  2024: '2024',
};

function commitTimelineYear() {
  const y = timelineYear.value;
  if (y === selectedYear.value) return;
  selectedYear.value = y;
  fetchProvinceData(y);
}

const backButtonText = computed(() => (gfDrillCity.value ? '返回市级视角' : '返回全国视角'));

watch([gfDrillProvince, selectedYear], () => {
  if (gfDrillProvince.value) {
    fetchCityData(gfDrillProvince.value, selectedYear.value);
  }
});

watch(
  selectedYear,
  (y) => {
    timelineYear.value = y;
  },
  { immediate: true },
);

watch(selectedProv, (v) => {
  if (gfDrillProvince.value && v !== gfDrillProvince.value) {
    gfDrillProvince.value = '';
  }
});
useGreenFinanceRadar(selectedProv);
useGreenFinanceTop10Bar();
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
  const avgScore = +((rows.reduce((s, r) => s + r.score, 0) / rows.length) * 100).toFixed(2);
  return {
    totalGreenFinance,
    totalCarbon,
    avgScore,
    coveredProvinces: rows.length,
  };
});

const displayProv = computed(() => selectedProv.value.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, ''));

const top10Title = computed(() => {
  if (gfDrillProvince.value) {
    return `${displayProv.value} · 地级市 Top10`;
  }
  return '绿色金融综合指数 · Top10';
});
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
      <div class="sidebar-charts">
        <div class="sidebar-section sidebar-section--top">
          <div class="chart-title">{{ top10Title }}</div>
          <div id="gf-gf-top10-bar" class="chart-box chart-box--top10" />
        </div>
        <div class="sidebar-section sidebar-section--bottom">
          <div class="chart-title">{{ displayProv }} · 七维雷达图</div>
          <div id="gf-radar" class="chart-box chart-box--radar" />
        </div>
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
          {{ backButtonText }}
        </button>
        <div id="gf-map" />
        <div class="map-timeline">
          <span class="map-timeline__label">数据年份</span>
          <el-slider
            v-model="timelineYear"
            :min="2000"
            :max="2024"
            :step="1"
            :marks="yearMarks"
            :format-tooltip="(v: number) => `${v}年`"
            class="map-timeline__slider"
            @change="commitTimelineYear"
          />
          <div class="map-timeline__badge">{{ timelineYear }}年</div>
        </div>
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
  gap: 12px;
  padding: 0;
  &-sidebar {
    flex: 0 0 25%;
    max-width: 25%;
    min-width: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
    overflow-y: auto;
    overflow-x: hidden;
    &::-webkit-scrollbar {
      width: 3px;
    }
    &::-webkit-scrollbar-thumb {
      background: rgba($tech-cyan, 0.2);
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
  padding: 12px 18px;
  margin: 0 0 10px;
  background: $panel-bg;
  border: 1px solid $border-color;
  border-radius: 14px;
  backdrop-filter: blur(10px);
  box-shadow: $box-shadow-panel;
}
.board-item {
  flex: 1;
  text-align: center;
  padding: 4px 14px;
}
.board-label {
  color: rgba(200, 220, 255, 0.5);
  font-size: 15px;
  letter-spacing: 0.18em;
  margin-bottom: 4px;
}
.board-value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 4px;
}
.board-num {
  font-size: 31px;
  font-weight: 900;
  font-family: $font-title;
  letter-spacing: -0.5px;
}
.board-unit {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.4);
  font-weight: normal;
}
.board-value.cyan .board-num {
  background: linear-gradient(180deg, #29fbff, #00849a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 8px rgba($tech-cyan, 0.4));
}
.board-value.green .board-num {
  background: linear-gradient(180deg, #2fffc0, #009a68);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 8px rgba($tech-green, 0.4));
}
.board-value.gold .board-num {
  background: linear-gradient(180deg, #ffc66a, $tech-orange);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 8px rgba($tech-orange, 0.34));
}
.board-value.purple .board-num {
  background: linear-gradient(180deg, #7fb8ff, #0b5cbe);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 8px rgba($theme-color, 0.4));
}
.board-divider {
  width: 1px;
  height: 52px;
  background: linear-gradient(180deg, transparent, rgba($tech-cyan, 0.25), transparent);
  flex-shrink: 0;
}
.gf-back-map {
  position: absolute;
  top: 88px;
  right: 10px;
  z-index: 1000;
  padding: 10px 18px;
  font-size: 16px;
  letter-spacing: 1px;
  color: $tech-cyan;
  cursor: pointer;
  background: rgba(8, 14, 32, 0.92);
  border: 1px solid rgba($tech-cyan, 0.45);
  border-radius: 999px;
  box-shadow: $box-shadow-panel;
  transition:
    box-shadow 0.2s,
    border-color 0.2s,
    transform 0.2s;
}
.gf-back-map:hover {
  transform: translateY(-1px);
  border-color: rgba($tech-cyan, 0.8);
  box-shadow: $glow-shadow, inset 0 0 24px rgba($tech-cyan, 0.1);
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
    background: $panel-bg;
    border: 1px solid $border-color;
    border-radius: 10px;
    padding: 10px 14px;
    backdrop-filter: blur(10px);
    box-shadow: $box-shadow-panel;
    width: min(292px, 46vw);
  }
  .map-timeline {
    position: absolute;
    top: 10px;
    left: 352px;
    right: 34px;
    z-index: 999;
    display: flex;
    align-items: center;
    gap: 14px;
    min-height: 56px;
    padding: 10px 18px;
    background: $panel-bg;
    border: 1px solid $border-color;
    border-radius: 10px;
    backdrop-filter: blur(10px);
    box-shadow: $box-shadow-panel;
  }
  .map-timeline__label {
    color: rgba($tech-cyan, 0.84);
    font-size: 16px;
    letter-spacing: 0.14em;
    white-space: nowrap;
  }
  .map-timeline__slider {
    flex: 1;
    :deep(.el-slider__runway) {
      background: rgba($tech-cyan, 0.12);
    }
    :deep(.el-slider__bar) {
      background: linear-gradient(90deg, $theme-color, $tech-cyan, $tech-green, $tech-orange);
    }
    :deep(.el-slider__button) {
      width: 18px;
      height: 18px;
      border: 2px solid $tech-cyan;
      background: $bg-dark;
      box-shadow: 0 0 0 4px rgba($tech-cyan, 0.08), 0 0 14px rgba($tech-cyan, 0.4);
    }
    :deep(.el-slider__marks-text) {
      color: rgba(255, 255, 255, 0.45);
      font-size: 14px;
    }
  }
  .map-timeline__badge {
    flex-shrink: 0;
    background: rgba($tech-cyan, 0.12);
    border: 1px solid rgba($tech-cyan, 0.4);
    border-radius: 999px;
    padding: 6px 14px;
    color: $tech-cyan;
    font-size: 18px;
    font-weight: bold;
    box-shadow: inset 0 0 14px rgba($tech-cyan, 0.08);
    white-space: nowrap;
  }
  .legend-note {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    margin-top: 8px;
    padding-top: 6px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    color: rgba(200, 210, 225, 0.85);
    font-size: 14px;
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
    color: rgba($tech-cyan, 0.84);
    font-size: 15px;
    letter-spacing: 0.14em;
    margin-bottom: 6px;
  }
  .legend-bar {
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(90deg, #0a4fae, $theme-color, $tech-green, $tech-orange);
    box-shadow: inset 0 0 10px rgba(255, 255, 255, 0.12);
  }
  .legend-labels {
    display: flex;
    justify-content: space-between;
    color: rgba(255, 255, 255, 0.5);
    font-size: 14px;
    margin-top: 2px;
  }
  .map-approve {
    position: absolute;
    bottom: 10px;
    right: 10px;
    color: rgba(255, 255, 255, 0.5);
    z-index: 999;
    font-size: 16px;
    text-shadow: 0 0 8px rgba(0, 0, 0, 0.4);
  }
  .gf-map-tooltip {
    position: absolute;
    z-index: 1001;
    width: min(360px, calc(100% - 20px));
    max-height: min(400px, calc(100% - 24px));
    overflow: auto;
    pointer-events: none;
    padding: 14px 16px 16px;
    border-radius: 10px;
    background: rgba(9, 16, 34, 0.82);
    border: 1px solid rgba($tech-cyan, 0.42);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow:
      0 0 24px rgba($tech-cyan, 0.22),
      0 8px 32px rgba(0, 0, 0, 0.45),
      inset 0 0 28px rgba($tech-cyan, 0.06);
    &::-webkit-scrollbar {
      width: 4px;
    }
    &::-webkit-scrollbar-thumb {
      background: rgba($tech-cyan, 0.2);
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
    color: rgba($tech-cyan, 0.92);
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-shadow: 0 0 12px rgba($tech-cyan, 0.35);
  }
  .gf-map-tooltip__year {
    flex-shrink: 0;
    font-size: 15px;
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
    font-size: 15px;
    color: rgba(200, 220, 255, 0.5);
    letter-spacing: 1px;
  }
  .gf-map-tooltip__score-val {
    font-size: 27px;
    font-weight: 900;
    font-family: $font-title;
    letter-spacing: -0.5px;
    background: linear-gradient(180deg, #ffc66a, $tech-orange);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 0 8px rgba($tech-orange, 0.42));
  }
  .gf-map-tooltip__score-unit {
    font-size: 15px;
    color: rgba(255, 255, 255, 0.4);
  }
  .gf-map-tooltip__grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 14px;
  }
  .gf-map-tooltip__cell {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 0;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }
  .gf-map-tooltip__cell-label {
    font-size: 14px;
    color: rgba(200, 210, 225, 0.55);
    letter-spacing: 0.5px;
  }
  .gf-map-tooltip__cell-value {
    font-size: 16px;
    font-weight: 600;
    color: rgba(230, 240, 255, 0.92);
    font-variant-numeric: tabular-nums;
  }
}
.sidebar-charts {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}
.sidebar-section {
  flex: 1 1 50%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}
.sidebar-section--top {
  padding-bottom: 4px;
}
.sidebar-section--bottom {
  padding-top: 6px;
}
.sidebar-section--bottom .chart-title {
  padding-top: 2px;
}
.chart-box {
  flex: 1;
  min-height: 120px;
  min-width: 0;
  width: 100%;
  overflow: hidden;
}
.chart-box--top10 {
  min-height: 180px;
}
.chart-box--radar {
  min-height: 220px;
}
.chart-title {
  text-align: center;
  color: rgba($tech-cyan, 0.85);
  font-size: 17px;
  font-family: $font-title;
  padding-bottom: 6px;
  letter-spacing: 0.14em;
  flex-shrink: 0;
  text-shadow: 0 0 10px rgba($tech-cyan, 0.18);
}
.prov-selector {
  flex: 0 0 auto;
  margin-bottom: 4px;
  background: $panel-bg;
  border: 1px solid $border-color;
  border-radius: 12px;
  padding: 10px 14px;
  backdrop-filter: blur(10px);
  box-shadow: $box-shadow-panel;
  .selector-label {
    color: rgba($tech-cyan, 0.74);
    font-size: 15px;
    margin-bottom: 6px;
    letter-spacing: 0.14em;
  }
  :deep(.el-select) {
    width: 100%;
  }
  :deep(.el-select__wrapper) {
    background: rgba($tech-cyan, 0.06) !important;
    border: 1px solid rgba($tech-cyan, 0.25) !important;
    box-shadow: inset 0 0 10px rgba($tech-cyan, 0.08) !important;
    border-radius: 8px !important;
    display: flex !important;
    align-items: center !important;
    min-height: 48px !important;
    padding: 0 14px !important;
    transition: border-color 0.3s, box-shadow 0.3s;
    &:hover,
    &.is-focused {
      border-color: rgba($tech-cyan, 0.5) !important;
      box-shadow: 0 0 12px rgba($tech-cyan, 0.15) !important;
    }
  }
  :deep(.el-select__selected-item) {
    color: $tech-cyan !important;
    font-size: 17px !important;
    font-weight: bold;
    display: flex !important;
    align-items: center !important;
    min-height: 28px !important;
    line-height: 1 !important;
  }
  :deep(.el-select__placeholder) {
    color: rgba($tech-cyan, 0.5) !important;
    font-size: 17px !important;
    display: flex !important;
    align-items: center !important;
    min-height: 28px !important;
    line-height: 1 !important;
  }
  :deep(.el-select__suffix) {
    color: rgba($tech-cyan, 0.6) !important;
  }
  :deep(.el-input__wrapper) {
    background: rgba($tech-cyan, 0.06) !important;
    border: 1px solid rgba($tech-cyan, 0.25) !important;
    box-shadow: inset 0 0 10px rgba($tech-cyan, 0.08) !important;
    border-radius: 8px !important;
    min-height: 48px !important;
    padding: 0 14px !important;
    &:hover,
    &.is-focus {
      border-color: rgba($tech-cyan, 0.5) !important;
      box-shadow: 0 0 12px rgba($tech-cyan, 0.15) !important;
    }
  }
  :deep(.el-input__inner) {
    color: $tech-cyan !important;
    font-size: 17px !important;
    font-weight: bold;
    line-height: 1 !important;
  }
  :deep(.el-input__suffix) {
    color: rgba($tech-cyan, 0.6) !important;
  }
}
</style>
