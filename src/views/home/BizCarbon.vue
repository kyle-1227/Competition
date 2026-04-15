<script setup lang="ts">
import { useCarbonBar, getCarbonRowsFromApi } from './hooks/useChart';
import { useAiAssistant } from './hooks/aiAssistant';
import { useCarbonMap } from './hooks/useMap';
import {
  NO_PANEL_DATA_REGIONS_LEGEND,
  fetchProvinceData,
  fetchCityData,
  selectedYear,
  timelineYear,
  selectedProvince,
} from './hooks/provinceData';

useCarbonBar();
useCarbonMap();
const { registerPageContext } = useAiAssistant();

const noPanelRegionsLegend = NO_PANEL_DATA_REGIONS_LEGEND;

const carbonRows = computed(() => getCarbonRowsFromApi());
const totalCarbon = computed(() => carbonRows.value.reduce((s, d) => s + d.carbonEmission, 0));
const avgCarbon = computed(() =>
  carbonRows.value.length ? Math.round(totalCarbon.value / carbonRows.value.length) : 0,
);
const topProvince = computed(() => {
  const top = [...carbonRows.value].sort((a, b) => b.carbonEmission - a.carbonEmission)[0];
  return top ? top.province.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, '') : '—';
});
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
  if (selectedProvince.value) {
    fetchCityData(selectedProvince.value, y);
  }
}

watch(
  selectedYear,
  (y) => {
    timelineYear.value = y;
  },
  { immediate: true },
);

const carbonTop10Rows = computed(() =>
  [...carbonRows.value]
    .sort((a, b) => b.carbonEmission - a.carbonEmission)
    .slice(0, 10)
    .map((row) => ({
      name: row.province,
      carbonEmission: Number(row.carbonEmission.toFixed(2)),
    })),
);

const unregisterAiContext = registerPageContext('carbon', () => ({
  year: selectedYear.value,
  selectedProvince: selectedProvince.value || undefined,
  snapshot: {
    totalCarbon: Number(totalCarbon.value.toFixed(2)),
    avgCarbon: avgCarbon.value,
    topProvince: topProvince.value,
    top10: carbonTop10Rows.value,
  },
}));

onUnmounted(() => {
  unregisterAiContext();
});
</script>
<template>
  <div class="biz-wrap">
    <div class="biz-wrap-sidebar">
      <div class="sidebar-section">
        <div class="info-card">
          <div class="info-label">全国碳排放总量</div>
          <div class="info-value">{{ totalCarbon.toLocaleString() }} <span class="info-unit">万吨</span></div>
        </div>
        <div class="info-card">
          <div class="info-label">省均碳排放</div>
          <div class="info-value">{{ avgCarbon.toLocaleString() }} <span class="info-unit">万吨</span></div>
        </div>
        <div class="info-card">
          <div class="info-label">排放最高省份</div>
          <div class="info-value highlight">{{ topProvince }}</div>
        </div>
      </div>
      <div class="sidebar-section chart-section">
        <div class="chart-title">碳排放 TOP 10 省份</div>
        <div id="carbon-bar" class="chart-box" />
      </div>
    </div>
    <div class="biz-wrap-map">
      <div id="carbon-map" />
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
      <div class="map-legend">
        <div class="legend-title">碳排放总量（万吨）</div>
        <div class="legend-bar" />
        <div class="legend-labels">
          <span>低</span>
          <span>高</span>
        </div>
        <div class="legend-note">
          <span class="swatch swatch--muted" />
          <span>灰色：无面板数据区域（{{ noPanelRegionsLegend }}），不参与填色</span>
        </div>
      </div>
      <div class="map-approve">本底图基于国家地理信息公共服务平台标准地图制作，审图号：GS(2025)5996号</div>
    </div>
  </div>
</template>
<script lang="ts">
export default { name: 'BizCarbon' };
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
    gap: 6px;
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
  &-map {
    flex: 1;
    position: relative;
    #carbon-map {
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
      width: min(268px, 42vw);
    }
    .map-timeline {
      position: absolute;
      top: 10px;
      left: 322px;
      right: 36px;
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
    .legend-title {
      color: rgba($tech-cyan, 0.82);
      font-size: 15px;
      letter-spacing: 0.14em;
      margin-bottom: 6px;
    }
    .legend-bar {
      height: 8px;
      border-radius: 4px;
      background: linear-gradient(90deg, #0c8c61, $tech-green, #ffb74d, $tech-orange, #bf6700);
      box-shadow: inset 0 0 10px rgba(255, 255, 255, 0.12);
    }
    .legend-labels {
      display: flex;
      justify-content: space-between;
      color: rgba(255, 255, 255, 0.5);
      font-size: 14px;
      margin-top: 2px;
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
    .map-approve {
      position: absolute;
      bottom: 10px;
      right: 10px;
      color: rgba(255, 255, 255, 0.5);
      z-index: 999;
      font-size: 16px;
    }
  }
}
.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
}
.chart-section {
  flex: 1;
  min-height: 0;
}
.chart-box {
  flex: 1;
  min-height: 320px;
  min-width: 0;
  width: 100%;
  overflow: hidden;
}
.chart-title {
  text-align: center;
  color: rgba($tech-cyan, 0.86);
  font-size: 17px;
  font-family: $font-title;
  padding-bottom: 4px;
  letter-spacing: 0.14em;
  flex-shrink: 0;
  text-shadow: 0 0 10px rgba($tech-cyan, 0.16);
}
.info-card {
  background: $panel-bg;
  border: 1px solid rgba($tech-cyan, 0.16);
  border-radius: 12px;
  padding: 10px 14px;
  box-shadow: $box-shadow-panel;
}
.info-label {
  color: rgba(200, 220, 255, 0.45);
  font-size: 14px;
  letter-spacing: 0.12em;
  margin-bottom: 2px;
}
.info-value {
  color: #fff;
  font-size: 23px;
  font-weight: bold;
  font-family: $font-title;
  text-shadow: 0 0 10px rgba($tech-cyan, 0.14);
  .info-unit {
    font-size: 15px;
    color: rgba(255, 255, 255, 0.4);
    font-weight: normal;
  }
  &.highlight {
    color: $tech-orange;
    text-shadow: 0 0 12px rgba($tech-orange, 0.24);
  }
}
</style>
