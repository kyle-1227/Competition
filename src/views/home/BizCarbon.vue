<script setup lang="ts">
import {
  getCityCarbonDataApi,
  getCountyCarbonDataApi,
  type CityCarbonPayload,
  type CityCarbonRow,
  type CountyCarbonPayload,
  type CountyCarbonRow,
} from '@/api/modules/dashboard-carbon';
import { useCarbonBar, getCarbonRowsFromApi } from './hooks/useChart';
import { useAiAssistant } from './hooks/aiAssistant';
import { useCarbonMap } from './hooks/useMap';
import BizMacro from './BizMacro.vue';
import {
  NO_PANEL_DATA_REGIONS_LEGEND,
  fetchProvinceData,
  fetchCityData,
  selectedYear,
  timelineYear,
  selectedProvince,
} from './hooks/provinceData';

<<<<<<< HEAD
useCarbonBar();
useCarbonMap();
const { registerPageContext } = useAiAssistant();
=======
type CarbonViewMode = 'carbon' | 'gdp';

const activeCarbonView = ref<CarbonViewMode>('carbon');
const selectedCarbonProvince = ref('');
const selectedCarbonCity = ref('');
const cityCarbonRows = ref<CityCarbonRow[]>([]);
const cityCarbonTotalWanTon = ref(0);
const cityCarbonLoading = ref(false);
const cityCarbonError = ref('');
const countyCarbonRows = ref<CountyCarbonRow[]>([]);
const countyCarbonTotalWanTon = ref(0);
const countyCarbonLoading = ref(false);
const countyCarbonError = ref('');
let cityCarbonFetchSeq = 0;
let countyCarbonFetchSeq = 0;

function selectCarbonProvince(provinceName: string) {
  selectedCarbonProvince.value = provinceName;
  selectedCarbonCity.value = '';
  resetCountyCarbon();
}

function selectCarbonCity(cityName: string) {
  selectedCarbonCity.value = cityName;
}

useCarbonBar(selectCarbonProvince);
useCarbonMap({
  selectedProvince: selectedCarbonProvince,
  selectedCity: selectedCarbonCity,
  cityRows: cityCarbonRows,
  countyRows: countyCarbonRows,
  onProvinceClick: selectCarbonProvince,
  onCityClick: selectCarbonCity,
});
>>>>>>> origin/main

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
const selectedProvinceShortName = computed(() => shortRegionName(selectedCarbonProvince.value));
const selectedCityShortName = computed(() => shortRegionName(selectedCarbonCity.value));
const selectedProvinceDbCarbon = computed(
  () => carbonRows.value.find((d) => d.province === selectedCarbonProvince.value)?.carbonEmission || 0,
);
const selectedProvinceCarbonWanTon = computed(() => cityCarbonTotalWanTon.value || selectedProvinceDbCarbon.value);
const selectedCityCarbonWanTon = computed(
  () =>
    cityCarbonRows.value.find((d) => d.city === selectedCarbonCity.value)?.carbonEmissionWanTon ||
    countyCarbonTotalWanTon.value,
);
const topCityCarbon = computed(() => cityCarbonRows.value[0] || null);
const topCountyCarbon = computed(() => countyCarbonRows.value[0] || null);
const yearMarks = {
  2000: '2000',
  2005: '2005',
  2010: '2010',
  2015: '2015',
  2020: '2020',
  2024: '2024',
};

const carbonViewToggleLabel = computed(() =>
  activeCarbonView.value === 'carbon' ? '切换 GDP 数据' : '返回碳排放底色',
);

function toggleCarbonView() {
  activeCarbonView.value = activeCarbonView.value === 'carbon' ? 'gdp' : 'carbon';
  nextTick(() => {
    window.dispatchEvent(new Event('resize'));
  });
}

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

function resetCountyCarbon() {
  countyCarbonRows.value = [];
  countyCarbonTotalWanTon.value = 0;
  countyCarbonLoading.value = false;
  countyCarbonError.value = '';
}

function clearCarbonProvince() {
  cityCarbonFetchSeq += 1;
  countyCarbonFetchSeq += 1;
  selectedCarbonProvince.value = '';
  selectedCarbonCity.value = '';
  resetCityCarbon();
  resetCountyCarbon();
}

function backToCityCarbon() {
  countyCarbonFetchSeq += 1;
  selectedCarbonCity.value = '';
  resetCountyCarbon();
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

async function loadCountyCarbonData() {
  const province = selectedCarbonProvince.value;
  const city = selectedCarbonCity.value;
  const seq = ++countyCarbonFetchSeq;
  countyCarbonError.value = '';

  if (!province || !city) {
    resetCountyCarbon();
    return;
  }

  countyCarbonLoading.value = true;
  countyCarbonRows.value = [];
  countyCarbonTotalWanTon.value = 0;
  try {
    const res = await getCountyCarbonDataApi(province, city, selectedYear.value);
    if (seq !== countyCarbonFetchSeq) return;
    const payload: CountyCarbonPayload | null = res?.data ?? null;
    countyCarbonRows.value = payload?.rows ?? [];
    countyCarbonTotalWanTon.value = Number(payload?.carbonEmissionWanTon || 0);
  } catch (error) {
    if (seq !== countyCarbonFetchSeq) return;
    countyCarbonRows.value = [];
    countyCarbonTotalWanTon.value = 0;
    countyCarbonError.value = error instanceof Error ? error.message : '县级碳排放数据加载失败';
  } finally {
    if (seq === countyCarbonFetchSeq) {
      countyCarbonLoading.value = false;
    }
  }
}

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

<<<<<<< HEAD
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
=======
watch([selectedCarbonProvince, selectedYear], loadCityCarbonData, { immediate: true });
watch([selectedCarbonProvince, selectedCarbonCity, selectedYear], loadCountyCarbonData, { immediate: true });
>>>>>>> origin/main
</script>
<template>
  <div class="carbon-page">
    <button
      type="button"
      class="carbon-view-toggle"
      :class="{ 'is-gdp': activeCarbonView === 'gdp' }"
      @click="toggleCarbonView"
    >
      {{ carbonViewToggleLabel }}
    </button>
    <div v-show="activeCarbonView === 'carbon'" class="biz-wrap">
      <div class="biz-wrap-sidebar">
        <div class="sidebar-section">
          <div v-if="selectedCarbonProvince" class="selected-province-bar">
            <div>
              <div class="selected-label">{{ selectedCarbonCity ? '当前城市' : '当前省份' }}</div>
              <div class="selected-name">
                {{ selectedCarbonCity ? selectedCityShortName : selectedProvinceShortName }}
              </div>
            </div>
            <div class="selected-actions">
              <button v-if="selectedCarbonCity" type="button" class="reset-province" @click="backToCityCarbon">
                返回市级
              </button>
              <button type="button" class="reset-province" @click="clearCarbonProvince">全国</button>
            </div>
          </div>
          <template v-if="selectedCarbonProvince && selectedCarbonCity">
            <div class="info-card">
              <div class="info-label">{{ selectedYear }}年市级碳排放</div>
              <div class="info-value">
                {{ formatWanTon(selectedCityCarbonWanTon) }} <span class="info-unit">万吨</span>
              </div>
            </div>
            <div class="info-card">
              <div class="info-label">县级记录数量</div>
              <div class="info-value">{{ countyCarbonRows.length }} <span class="info-unit">个</span></div>
            </div>
            <div class="info-card">
              <div class="info-label">排放最高县域</div>
              <div class="info-value highlight">{{ topCountyCarbon?.county || '—' }}</div>
            </div>
          </template>
          <template v-else-if="selectedCarbonProvince">
            <div class="info-card">
              <div class="info-label">{{ selectedYear }}年省级碳排放</div>
              <div class="info-value">
                {{ formatWanTon(selectedProvinceCarbonWanTon) }} <span class="info-unit">万吨</span>
              </div>
            </div>
            <div class="info-card">
              <div class="info-label">市级记录数量</div>
              <div class="info-value">{{ cityCarbonRows.length }} <span class="info-unit">个</span></div>
            </div>
            <div class="info-card">
              <div class="info-label">排放最高地市</div>
              <div class="info-value highlight">{{ topCityCarbon?.city || '—' }}</div>
            </div>
          </template>
          <template v-else>
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
          </template>
        </div>
        <div class="sidebar-section chart-section">
          <div class="chart-title">
            {{
              selectedCarbonCity
                ? `${selectedCityShortName} 县级碳排放`
                : selectedCarbonProvince
                ? `${selectedProvinceShortName} 市级碳排放`
                : '碳排放 TOP 10 省份'
            }}
          </div>
          <div v-show="!selectedCarbonProvince" id="carbon-bar" class="chart-box" />
          <div v-show="selectedCarbonProvince" class="county-carbon-list">
            <template v-if="selectedCarbonCity">
              <div v-if="countyCarbonLoading" class="county-state">县级数据加载中...</div>
              <div v-else-if="countyCarbonError" class="county-state error">{{ countyCarbonError }}</div>
              <div v-else-if="!countyCarbonRows.length" class="county-state">暂无该城市县级碳排放数据</div>
              <div v-else class="county-list-inner">
                <div
                  v-for="(row, idx) in countyCarbonRows"
                  :key="`${row.city}-${row.county}-${idx}`"
                  class="county-row"
                >
                  <div class="county-rank">{{ idx + 1 }}</div>
                  <div class="county-main">
                    <div class="county-name">{{ row.county }}</div>
                    <div class="county-city">{{ row.city }}</div>
                  </div>
                  <div class="county-value">{{ formatWanTon(row.carbonEmissionWanTon) }} 万吨</div>
                </div>
              </div>
            </template>
            <template v-else>
              <div v-if="cityCarbonLoading" class="county-state">市级数据加载中...</div>
              <div v-else-if="cityCarbonError" class="county-state error">{{ cityCarbonError }}</div>
              <div v-else-if="!cityCarbonRows.length" class="county-state">暂无该省份市级碳排放数据</div>
              <div v-else class="county-list-inner">
                <div
                  v-for="(row, idx) in cityCarbonRows"
                  :key="`${row.city}-${idx}`"
                  class="county-row clickable"
                  @click="selectCarbonCity(row.city)"
                >
                  <div class="county-rank">{{ idx + 1 }}</div>
                  <div class="county-main">
                    <div class="county-name">{{ row.city }}</div>
                    <div class="county-city">{{ row.province }}</div>
                  </div>
                  <div class="county-value">{{ formatWanTon(row.carbonEmissionWanTon) }} 万吨</div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
      <div class="biz-wrap-map">
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
    <BizMacro
      v-if="activeCarbonView === 'gdp'"
      class="carbon-macro-view"
      :initial-province="selectedCarbonProvince"
      chart-id="carbon-macro-chart"
      tab-key="carbon"
      embedded
    />
  </div>
</template>
<script lang="ts">
export default { name: 'BizCarbon' };
</script>
<style lang="scss" scoped>
.carbon-page {
  position: relative;
  height: 100%;
  min-height: 0;
}
.carbon-view-toggle {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1300;
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
