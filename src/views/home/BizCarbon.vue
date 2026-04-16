<script setup lang="ts">
defineOptions({ name: 'BizCarbon' });

import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import {
  getCityCarbonDataApi,
  type CityCarbonPayload,
  type CityCarbonRow,
} from '@/api/modules/dashboard-carbon';
import { getCarbonRowsFromApi } from './hooks/useChart';
import { useAiAssistant } from './hooks/aiAssistant';
import {
  useCarbonMap,
  createHiddenCarbonTooltip,
  type CarbonMapTooltipState,
} from './hooks/useMap';
import BizMacro from './BizMacro.vue';
import {
  NO_PANEL_DATA_REGIONS_LEGEND,
  fetchProvinceData,
  fetchCityData,
  realProvinceData,
  selectedYear,
  timelineYear,
  selectedProvince as gfSelectedProvince,
} from './hooks/provinceData';

type CarbonViewMode = 'map-carbon' | 'map-gdp' | 'macro';
type CarbonMapMetric = 'carbon' | 'gdp';
type CarbonSidebarAction = 'province' | null;

interface CarbonSidebarRow {
  key: string;
  name: string;
  subLabel: string;
  value: number;
  clickable: boolean;
  action: CarbonSidebarAction;
  targetName: string;
}

const { registerPageContext } = useAiAssistant();
const noPanelRegionsLegend = NO_PANEL_DATA_REGIONS_LEGEND;

const activeCarbonView = ref<CarbonViewMode>('map-carbon');
const lastMapView = ref<'map-carbon' | 'map-gdp'>('map-carbon');
const mapAreaRef = ref<HTMLElement | null>(null);
const carbonMapTooltip = ref<CarbonMapTooltipState>(createHiddenCarbonTooltip());
const selectedCarbonProvince = ref('');
const cityCarbonRows = ref<CityCarbonRow[]>([]);
const cityCarbonTotalWanTon = ref(0);
const cityCarbonLoading = ref(false);
const cityCarbonError = ref('');

let cityCarbonFetchSeq = 0;

function shortRegionName(name: string) {
  return name.replace(/(特别行政区|维吾尔自治区|壮族自治区|回族自治区|自治区|省|市)$/g, '');
}

function formatWanTon(value: number) {
  return Number(value || 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function resetCityCarbon() {
  cityCarbonRows.value = [];
  cityCarbonTotalWanTon.value = 0;
  cityCarbonLoading.value = false;
  cityCarbonError.value = '';
}

function selectCarbonProvince(provinceName: string) {
  carbonMapTooltip.value = createHiddenCarbonTooltip();
  selectedCarbonProvince.value = provinceName;
  resetCityCarbon();
}

function clearCarbonProvince() {
  cityCarbonFetchSeq += 1;
  carbonMapTooltip.value = createHiddenCarbonTooltip();
  selectedCarbonProvince.value = '';
  resetCityCarbon();
}

const currentMapView = computed<'map-carbon' | 'map-gdp'>(() =>
  activeCarbonView.value === 'macro' ? lastMapView.value : activeCarbonView.value,
);
const currentMetric = computed<CarbonMapMetric>(() => (currentMapView.value === 'map-gdp' ? 'gdp' : 'carbon'));

useCarbonMap({
  metric: currentMetric,
  selectedProvince: selectedCarbonProvince,
  cityRows: cityCarbonRows,
  tooltipRef: carbonMapTooltip,
  onProvinceClick: selectCarbonProvince,
});

const provinceCarbonRows = computed(() => getCarbonRowsFromApi());
const provinceGdpRows = computed(() =>
  realProvinceData.value.map((row) => ({
    province: row.province,
    value: Number(row.gdp ?? 0),
  })),
);
const provinceMetricRows = computed(() =>
  currentMetric.value === 'gdp'
    ? provinceGdpRows.value
    : provinceCarbonRows.value.map((row) => ({ province: row.province, value: row.carbonEmission })),
);
const sortedProvinceMetricRows = computed(() =>
  [...provinceMetricRows.value].sort((a, b) => Number(b.value || 0) - Number(a.value || 0)),
);
const sortedCityMetricRows = computed(() =>
  [...cityCarbonRows.value].sort((a, b) =>
    currentMetric.value === 'gdp'
      ? Number(b.gdp || 0) - Number(a.gdp || 0)
      : Number(b.carbonEmissionWanTon || 0) - Number(a.carbonEmissionWanTon || 0),
  ),
);
const totalMetric = computed(() =>
  sortedProvinceMetricRows.value.reduce((sum, row) => sum + Number(row.value || 0), 0),
);
const avgMetric = computed(() =>
  sortedProvinceMetricRows.value.length ? Math.round(totalMetric.value / sortedProvinceMetricRows.value.length) : 0,
);
const topProvince = computed(() => {
  const top = sortedProvinceMetricRows.value[0];
  return top ? shortRegionName(top.province) : '—';
});
const selectedProvinceShortName = computed(() => shortRegionName(selectedCarbonProvince.value));
const selectedProvinceMetricFromProvince = computed(
  () => provinceMetricRows.value.find((row) => row.province === selectedCarbonProvince.value)?.value || 0,
);
const cityGdpTotal = computed(() =>
  cityCarbonRows.value.reduce((sum, row) => sum + Number(row.gdp || 0), 0),
);
const selectedProvinceMetricValue = computed(() => {
  if (currentMetric.value === 'gdp') {
    return cityGdpTotal.value || selectedProvinceMetricFromProvince.value;
  }
  return cityCarbonTotalWanTon.value || selectedProvinceMetricFromProvince.value;
});
const topCityMetric = computed(() => sortedCityMetricRows.value[0] || null);
const currentMetricLabel = computed(() => (currentMetric.value === 'gdp' ? 'GDP' : '碳排放'));
const currentMetricUnit = computed(() => (currentMetric.value === 'gdp' ? '亿元' : '万吨'));
const primaryToggleLabel = computed(() =>
  currentMapView.value === 'map-carbon' ? '切换 GDP 数据' : '返回碳排放数据',
);
const macroToggleLabel = computed(() =>
  activeCarbonView.value === 'macro' ? '返回地图视图' : 'GDP和碳排放组合图',
);
const rankingTitle = computed(() => {
  if (selectedCarbonProvince.value) return `${selectedProvinceShortName.value} 市级${currentMetricLabel.value}`;
  return `全国省级${currentMetricLabel.value}`;
});
const legendTitle = computed(() =>
  currentMetric.value === 'gdp' ? 'GDP 总量（亿元）' : '碳排放总量（万吨）',
);
const carbonLevelLabel = computed(() => {
  if (activeCarbonView.value === 'macro') return 'GDP和碳排放组合图';
  if (selectedCarbonProvince.value) return `市级${currentMetricLabel.value}视角`;
  return `全国省级${currentMetricLabel.value}视角`;
});
const carbonSidebarRows = computed<CarbonSidebarRow[]>(() => {
  if (selectedCarbonProvince.value) {
    return sortedCityMetricRows.value.map((row) => ({
      key: `${row.province}-${row.city}`,
      name: row.city,
      subLabel: row.province,
      value: currentMetric.value === 'gdp'
        ? Number((row.gdp || 0).toFixed(2))
        : Number((row.carbonEmissionWanTon || 0).toFixed(2)),
      clickable: false,
      action: null,
      targetName: '',
    }));
  }

  return sortedProvinceMetricRows.value.map((row) => ({
    key: row.province,
    name: shortRegionName(row.province),
    subLabel: row.province,
    value: Number((row.value || 0).toFixed(2)),
    clickable: true,
    action: 'province',
    targetName: row.province,
  }));
});
const metricTop10Rows = computed(() => {
  const rows = carbonSidebarRows.value.slice(0, 10);
  return rows.map((row) => ({
    name: row.name,
    value: row.value,
    metric: currentMetric.value,
  }));
});
const sidebarLoading = computed(() => selectedCarbonProvince.value ? cityCarbonLoading.value : false);
const sidebarError = computed(() => selectedCarbonProvince.value ? cityCarbonError.value : '');
const sidebarEmptyText = computed(() => {
  if (selectedCarbonProvince.value) {
    return `暂无该省份市级${currentMetricLabel.value}数据`;
  }
  return `暂无全国省级${currentMetricLabel.value}数据`;
});
const carbonTooltipStyle = computed(() => {
  const tooltip = carbonMapTooltip.value;
  const area = mapAreaRef.value;
  if (!tooltip.visible || !area) return { display: 'none' as const };

  const padding = 10;
  const estimatedWidth = 360;
  const estimatedContentHeight = 170 + Math.max(1, Math.ceil(tooltip.rows.length / 2)) * 56 + 108;
  const areaWidth = area.clientWidth;
  const areaHeight = area.clientHeight;
  const estimatedHeight = Math.min(estimatedContentHeight, 420, Math.max(180, areaHeight - padding * 2));

  let left = tooltip.left;
  let top = tooltip.top;

  if (left + estimatedWidth > areaWidth - padding) {
    left = Math.max(padding, areaWidth - estimatedWidth - padding);
  }
  if (top + estimatedHeight > areaHeight - padding) {
    top = Math.max(padding, areaHeight - estimatedHeight - padding);
  }

  return {
    left: `${Math.max(padding, left)}px`,
    top: `${Math.max(padding, top)}px`,
  };
});

function keepCarbonTooltipOpen(event: Event) {
  event.stopPropagation();
}

function hideCarbonTooltipFromPanel(event: Event) {
  event.stopPropagation();
  carbonMapTooltip.value = createHiddenCarbonTooltip();
}

function handleSidebarRowClick(row: CarbonSidebarRow) {
  if (!row.clickable) return;
  if (row.action === 'province') {
    selectCarbonProvince(row.targetName);
  }
}

const yearMarks = {
  2000: '2000',
  2005: '2005',
  2010: '2010',
  2015: '2015',
  2020: '2020',
  2024: '2024',
};

function emitResizeSoon() {
  nextTick(() => {
    window.dispatchEvent(new Event('resize'));
  });
}

function setMapView(view: 'map-carbon' | 'map-gdp') {
  carbonMapTooltip.value = createHiddenCarbonTooltip();
  lastMapView.value = view;
  activeCarbonView.value = view;
  emitResizeSoon();
}

function toggleMapMetricView() {
  setMapView(currentMapView.value === 'map-carbon' ? 'map-gdp' : 'map-carbon');
}

function toggleMacroView() {
  carbonMapTooltip.value = createHiddenCarbonTooltip();
  if (activeCarbonView.value === 'macro') {
    activeCarbonView.value = lastMapView.value;
  } else {
    lastMapView.value = currentMapView.value;
    activeCarbonView.value = 'macro';
  }
  emitResizeSoon();
}

async function loadCityCarbonData() {
  const province = selectedCarbonProvince.value;
  const seq = ++cityCarbonFetchSeq;
  cityCarbonError.value = '';

  if (!province) {
    resetCityCarbon();
    return;
  }

  cityCarbonLoading.value = true;
  cityCarbonRows.value = [];
  cityCarbonTotalWanTon.value = 0;
  try {
    const res = await getCityCarbonDataApi(province, selectedYear.value);
    if (seq !== cityCarbonFetchSeq) return;
    const payload: CityCarbonPayload | null = res?.data ?? null;
    cityCarbonRows.value = payload?.rows ?? [];
    cityCarbonTotalWanTon.value = Number(payload?.carbonEmissionWanTon || 0);
  } catch (error) {
    if (seq !== cityCarbonFetchSeq) return;
    cityCarbonRows.value = [];
    cityCarbonTotalWanTon.value = 0;
    cityCarbonError.value = error instanceof Error ? error.message : '市级碳排放数据加载失败';
  } finally {
    if (seq === cityCarbonFetchSeq) {
      cityCarbonLoading.value = false;
    }
  }
}

function commitTimelineYear() {
  const year = timelineYear.value;
  if (year === selectedYear.value) return;
  selectedYear.value = year;
  fetchProvinceData(year);
  if (gfSelectedProvince.value) {
    fetchCityData(gfSelectedProvince.value, year);
  }
}

watch(
  selectedYear,
  (year) => {
    timelineYear.value = year;
  },
  { immediate: true },
);

watch([selectedCarbonProvince, selectedYear], loadCityCarbonData, { immediate: true });

const unregisterAiContext = registerPageContext('carbon', () => ({
  year: selectedYear.value,
  selectedProvince: selectedCarbonProvince.value || undefined,
  drillProvince: selectedCarbonProvince.value || undefined,
  snapshot: {
    viewMode: activeCarbonView.value,
    mapMetric: currentMetric.value,
    level: carbonLevelLabel.value,
    totalValue: Number(totalMetric.value.toFixed(2)),
    unit: currentMetricUnit.value,
    avgValue: avgMetric.value,
    topProvince: topProvince.value,
    top10: metricTop10Rows.value,
  },
}));

onUnmounted(() => {
  unregisterAiContext();
});
</script>

<template>
  <div class="carbon-page">
    <div class="carbon-view-actions">
      <button
        type="button"
        class="carbon-view-toggle"
        :class="{ 'is-gdp': currentMapView === 'map-gdp' }"
        @click="toggleMapMetricView"
      >
        {{ primaryToggleLabel }}
      </button>
      <button
        type="button"
        class="carbon-view-toggle carbon-view-toggle--secondary"
        :class="{ 'is-active': activeCarbonView === 'macro' }"
        @click="toggleMacroView"
      >
        {{ macroToggleLabel }}
      </button>
    </div>

    <div v-show="activeCarbonView !== 'macro'" class="biz-wrap">
      <div class="biz-wrap-sidebar">
        <div class="sidebar-section">
          <div v-if="selectedCarbonProvince" class="selected-province-bar">
            <div>
              <div class="selected-label">当前省份</div>
              <div class="selected-name">{{ selectedProvinceShortName }}</div>
            </div>
            <div class="selected-actions">
              <button type="button" class="reset-province" @click="clearCarbonProvince">全国</button>
            </div>
          </div>

          <template v-if="selectedCarbonProvince">
            <div class="info-card">
              <div class="info-label">{{ selectedYear }} 年省级{{ currentMetricLabel }}</div>
              <div class="info-value">
                {{ formatWanTon(selectedProvinceMetricValue) }} <span class="info-unit">{{ currentMetricUnit }}</span>
              </div>
            </div>
            <div class="info-card">
              <div class="info-label">市级记录数量</div>
              <div class="info-value">{{ cityCarbonRows.length }} <span class="info-unit">个</span></div>
            </div>
            <div class="info-card">
              <div class="info-label">{{ currentMetricLabel }}最高地市</div>
              <div class="info-value highlight">{{ topCityMetric?.city || '—' }}</div>
            </div>
          </template>

          <template v-else>
            <div class="info-card">
              <div class="info-label">全国{{ currentMetricLabel }}总量</div>
              <div class="info-value">{{ formatWanTon(totalMetric) }} <span class="info-unit">{{ currentMetricUnit }}</span></div>
            </div>
            <div class="info-card">
              <div class="info-label">省均{{ currentMetricLabel }}</div>
              <div class="info-value">{{ formatWanTon(avgMetric) }} <span class="info-unit">{{ currentMetricUnit }}</span></div>
            </div>
            <div class="info-card">
              <div class="info-label">{{ currentMetricLabel }}最高省份</div>
              <div class="info-value highlight">{{ topProvince }}</div>
            </div>
          </template>
        </div>

        <div class="sidebar-section chart-section">
          <div class="chart-title">{{ rankingTitle }}</div>
          <div class="county-carbon-list">
            <div v-if="sidebarLoading" class="county-state">
              {{ selectedCarbonProvince ? '市级数据加载中...' : '省级数据加载中...' }}
            </div>
            <div v-else-if="sidebarError" class="county-state error">{{ sidebarError }}</div>
            <div v-else-if="!carbonSidebarRows.length" class="county-state">{{ sidebarEmptyText }}</div>
            <div v-else class="county-list-inner">
              <div
                v-for="(row, idx) in carbonSidebarRows"
                :key="row.key"
                class="county-row"
                :class="{ clickable: row.clickable }"
                @click="handleSidebarRowClick(row)"
              >
                <div class="county-rank">{{ idx + 1 }}</div>
                <div class="county-main">
                  <div class="county-name">{{ row.name }}</div>
                  <div class="county-city">{{ row.subLabel }}</div>
                </div>
                <div class="county-value">{{ formatWanTon(row.value) }} {{ currentMetricUnit }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div ref="mapAreaRef" class="biz-wrap-map">
        <button v-if="selectedCarbonProvince" type="button" class="carbon-back-map" @click="clearCarbonProvince">
          返回全国视角
        </button>
        <div id="carbon-map" />

        <div class="map-timeline">
          <span class="map-timeline__label">数据年份</span>
          <el-slider
            v-model="timelineYear"
            :min="2000"
            :max="2024"
            :step="1"
            :marks="yearMarks"
            :format-tooltip="(value: number) => `${value}年`"
            class="map-timeline__slider"
            @change="commitTimelineYear"
          />
          <div class="map-timeline__badge">{{ timelineYear }}年</div>
        </div>

        <div
          v-show="carbonMapTooltip.visible"
          class="carbon-map-tooltip"
          :style="carbonTooltipStyle"
          @mouseenter="keepCarbonTooltipOpen"
          @mousemove="keepCarbonTooltipOpen"
          @mouseleave="hideCarbonTooltipFromPanel"
          @wheel.stop
        >
          <div class="carbon-map-tooltip__head">
            <span class="carbon-map-tooltip__name">{{ carbonMapTooltip.regionName }}</span>
            <span class="carbon-map-tooltip__year">{{ carbonMapTooltip.year }} 年</span>
          </div>
          <div class="carbon-map-tooltip__score-row">
            <span class="carbon-map-tooltip__score-label">{{ carbonMapTooltip.headlineLabel }}</span>
            <span class="carbon-map-tooltip__score-val">{{ carbonMapTooltip.headlineValue }}</span>
            <span
              v-if="carbonMapTooltip.headlineValue !== '—' && carbonMapTooltip.headlineUnit"
              class="carbon-map-tooltip__score-unit"
            >
              {{ carbonMapTooltip.headlineUnit }}
            </span>
          </div>
          <div v-if="carbonMapTooltip.rows.length" class="carbon-map-tooltip__grid">
            <div
              v-for="(cell, idx) in carbonMapTooltip.rows"
              :key="idx"
              class="carbon-map-tooltip__cell"
            >
              <span class="carbon-map-tooltip__cell-label">{{ cell.label }}</span>
              <span class="carbon-map-tooltip__cell-value">{{ cell.value }}</span>
            </div>
          </div>
          <div class="carbon-map-tooltip__ai">
            <div class="carbon-map-tooltip__ai-title">AI 分析</div>
            <div class="carbon-map-tooltip__ai-text">
              {{ carbonMapTooltip.aiLoading ? 'AI 分析生成中...' : carbonMapTooltip.aiInsight }}
            </div>
          </div>
        </div>

        <div class="map-legend">
          <div class="legend-title">{{ legendTitle }}</div>
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

    <BizMacro
      v-if="activeCarbonView === 'macro'"
      class="carbon-macro-view"
      :initial-province="selectedCarbonProvince"
      chart-id="carbon-macro-chart"
      tab-key="carbon"
      embedded
    />
  </div>
</template>

<style lang="scss" scoped>
.carbon-page {
  position: relative;
  height: 100%;
  min-height: 0;
}

.carbon-view-actions {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1300;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}

.carbon-view-toggle {
  min-width: 176px;
  padding: 11px 18px;
  color: $tech-cyan;
  cursor: pointer;
  background: linear-gradient(135deg, rgba($tech-cyan, 0.16), rgba($tech-orange, 0.08)), rgba(8, 14, 32, 0.94);
  border: 1px solid rgba($tech-cyan, 0.52);
  border-radius: 10px;
  box-shadow: $box-shadow-panel, inset 0 0 20px rgba($tech-cyan, 0.08);
  font-family: $font-title;
  font-size: 16px;
  letter-spacing: 0.12em;
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
}

.carbon-view-toggle:hover {
  transform: translateY(-1px);
  border-color: rgba($tech-cyan, 0.85);
  box-shadow: $glow-shadow, inset 0 0 24px rgba($tech-cyan, 0.12);
}

.carbon-view-toggle.is-gdp {
  color: $tech-orange;
  border-color: rgba($tech-orange, 0.62);
  background: linear-gradient(135deg, rgba($tech-orange, 0.17), rgba($tech-cyan, 0.08)), rgba(8, 14, 32, 0.94);
}

.carbon-view-toggle--secondary {
  color: rgba(214, 228, 255, 0.9);
  border-color: rgba(214, 228, 255, 0.28);
  background: rgba(8, 14, 32, 0.94);
}

.carbon-view-toggle--secondary.is-active {
  color: $tech-green;
  border-color: rgba($tech-green, 0.62);
  box-shadow: $glow-shadow, inset 0 0 24px rgba($tech-green, 0.12);
}

.carbon-macro-view {
  width: 100%;
  height: 100%;
  min-height: 0;
}

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

    .carbon-back-map {
      position: absolute;
      top: 132px;
      right: 10px;
      z-index: 1000;
      padding: 10px 18px;
      font-size: 16px;
      letter-spacing: 1px;
      color: $tech-cyan;
      cursor: pointer;
      background: rgba(8, 14, 32, 0.92);
      border: 1px solid rgba($tech-cyan, 0.45);
      border-radius: 8px;
      box-shadow: $box-shadow-panel;
      transition: box-shadow 0.2s, border-color 0.2s, transform 0.2s;
    }

    .carbon-back-map:hover {
      transform: translateY(-1px);
      border-color: rgba($tech-cyan, 0.8);
      box-shadow: $glow-shadow, inset 0 0 24px rgba($tech-cyan, 0.1);
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
      right: 214px;
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

    .carbon-map-tooltip {
      position: absolute;
      z-index: 1200;
      width: min(360px, calc(100% - 20px));
      max-height: min(420px, calc(100% - 24px));
      overflow: auto;
      overscroll-behavior: contain;
      pointer-events: auto;
      cursor: default;
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

    .carbon-map-tooltip__head {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .carbon-map-tooltip__name {
      color: rgba($tech-cyan, 0.92);
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0.5px;
      text-shadow: 0 0 12px rgba($tech-cyan, 0.35);
    }

    .carbon-map-tooltip__year {
      flex-shrink: 0;
      font-size: 15px;
      color: rgba(200, 220, 255, 0.55);
      letter-spacing: 1px;
    }

    .carbon-map-tooltip__score-row {
      display: flex;
      align-items: baseline;
      gap: 6px;
      margin-bottom: 10px;
    }

    .carbon-map-tooltip__score-label {
      font-size: 15px;
      color: rgba(200, 220, 255, 0.5);
      letter-spacing: 1px;
    }

    .carbon-map-tooltip__score-val {
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

    .carbon-map-tooltip__score-unit {
      font-size: 15px;
      color: rgba(255, 255, 255, 0.4);
    }

    .carbon-map-tooltip__grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px 14px;
    }

    .carbon-map-tooltip__cell {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 8px 0;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
    }

    .carbon-map-tooltip__cell-label {
      font-size: 14px;
      color: rgba(200, 210, 225, 0.55);
      letter-spacing: 0.5px;
    }

    .carbon-map-tooltip__cell-value {
      font-size: 16px;
      font-weight: 600;
      color: rgba(230, 240, 255, 0.92);
      font-variant-numeric: tabular-nums;
    }

    .carbon-map-tooltip__ai {
      margin-top: 12px;
      padding-top: 10px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .carbon-map-tooltip__ai-title {
      margin-bottom: 6px;
      color: rgba($tech-cyan, 0.86);
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.08em;
    }

    .carbon-map-tooltip__ai-text {
      color: rgba(230, 240, 255, 0.88);
      font-size: 14px;
      line-height: 1.6;
      white-space: normal;
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

.selected-province-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(8, 14, 32, 0.9);
  border: 1px solid rgba($tech-cyan, 0.28);
  border-radius: 8px;
  box-shadow: $box-shadow-panel;
}

.selected-label {
  color: rgba(200, 220, 255, 0.48);
  font-size: 13px;
  letter-spacing: 0.12em;
}

.selected-name {
  color: $tech-cyan;
  font-family: $font-title;
  font-size: 23px;
  font-weight: 800;
  text-shadow: 0 0 12px rgba($tech-cyan, 0.24);
}

.selected-actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
}

.reset-province {
  flex-shrink: 0;
  padding: 6px 12px;
  color: $tech-cyan;
  cursor: pointer;
  background: rgba($tech-cyan, 0.08);
  border: 1px solid rgba($tech-cyan, 0.34);
  border-radius: 8px;
  font-size: 14px;
}

.chart-box {
  flex: 1;
  min-height: 320px;
  min-width: 0;
  width: 100%;
  overflow: hidden;
}

.county-carbon-list {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: rgba(8, 14, 32, 0.45);
  border: 1px solid rgba($tech-cyan, 0.12);
  border-radius: 8px;
}

.county-list-inner {
  height: 100%;
  overflow-y: auto;
  padding: 6px;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba($tech-cyan, 0.24);
    border-radius: 2px;
  }
}

.county-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) minmax(88px, auto);
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 6px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  transition: background 0.2s, border-color 0.2s;

  &.clickable {
    cursor: pointer;
  }

  &.clickable:hover {
    background: rgba($tech-cyan, 0.08);
    border-color: rgba($tech-cyan, 0.18);
  }
}

.county-rank {
  color: $tech-orange;
  font-family: $font-title;
  font-size: 17px;
  text-align: center;
}

.county-main {
  min-width: 0;
}

.county-name {
  color: rgba(255, 255, 255, 0.92);
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.county-city {
  color: rgba(200, 220, 255, 0.44);
  font-size: 12px;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.county-value {
  color: $tech-green;
  font-family: $font-title;
  font-size: 15px;
  text-align: right;
  white-space: nowrap;
}

.county-state {
  height: 100%;
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: rgba(200, 220, 255, 0.7);
  text-align: center;

  &.error {
    color: $tech-orange;
  }
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
