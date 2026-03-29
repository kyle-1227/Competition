<script setup lang="ts">
import { useCarbonBar, getCarbonRowsFromApi } from './hooks/useChart';
import { useCarbonMap } from './hooks/useMap';
import { NO_PANEL_DATA_REGIONS_LEGEND } from './hooks/provinceData';

useCarbonBar();
useCarbonMap();

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
  padding: 10px 0 25px 0;
  &-sidebar {
    flex: 0 0 25%;
    max-width: 25%;
    padding: 6px 10px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    overflow-y: auto;
    &::-webkit-scrollbar {
      width: 3px;
    }
    &::-webkit-scrollbar-thumb {
      background: rgba(0, 229, 255, 0.2);
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
      background: rgba(10, 15, 30, 0.85);
      border: 1px solid rgba(0, 229, 255, 0.2);
      border-radius: 6px;
      padding: 8px 12px;
      backdrop-filter: blur(4px);
      width: min(220px, 40vw);
    }
    .legend-title {
      color: rgba(0, 229, 255, 0.8);
      font-size: 11px;
      margin-bottom: 6px;
    }
    .legend-bar {
      height: 8px;
      border-radius: 4px;
      background: linear-gradient(90deg, #1b5e20, #66bb6a, #ffcc80, #ff9800, #b71c1c);
    }
    .legend-labels {
      display: flex;
      justify-content: space-between;
      color: rgba(255, 255, 255, 0.5);
      font-size: 10px;
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
    .map-approve {
      position: absolute;
      bottom: 10px;
      right: 10px;
      color: rgba(255, 255, 255, 0.5);
      z-index: 999;
      font-size: 12px;
    }
  }
}
.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.chart-section {
  flex: 1;
  min-height: 0;
}
.chart-box {
  flex: 1;
  min-height: 320px;
}
.chart-title {
  text-align: center;
  color: rgba(0, 229, 255, 0.85);
  font-size: 13px;
  padding-bottom: 4px;
  letter-spacing: 1px;
  flex-shrink: 0;
}
.info-card {
  background: rgba(10, 15, 30, 0.7);
  border: 1px solid rgba(0, 229, 255, 0.12);
  border-radius: 6px;
  padding: 8px 12px;
}
.info-label {
  color: rgba(200, 220, 255, 0.45);
  font-size: 10px;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}
.info-value {
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  font-family: 'DIN Alternate', 'DIN', sans-serif;
  .info-unit {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.4);
    font-weight: normal;
  }
  &.highlight {
    color: #ff6d00;
  }
}
</style>
