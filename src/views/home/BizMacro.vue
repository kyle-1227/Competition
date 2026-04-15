<script setup lang="ts">
defineOptions({ name: 'BizMacro' });

import { useMacroChart } from './hooks/useChart';
import { realProvinceData, excludeProvincesWithoutPanelData } from './hooks/provinceData';
import { getMacroCityOptionsApi, type MacroCityOption } from '@/api/modules/dashboard-macro';

const props = withDefaults(
  defineProps<{
    chartId?: string;
    tabKey?: string;
    embedded?: boolean;
    initialProvince?: string;
  }>(),
  {
    chartId: 'macro-chart',
    tabKey: 'macro',
    embedded: false,
    initialProvince: '',
  },
);

const selectedProvince = ref(props.initialProvince || '全国');
const selectedCity = ref('');
const cityOptions = ref<MacroCityOption[]>([]);
const cityOptionsLoading = ref(false);
let cityOptionsFetchSeq = 0;

const provinceList = computed(() => {
  const provinces = excludeProvincesWithoutPanelData(realProvinceData.value.map((p) => p.province));
  return ['全国', ...provinces.sort((a, b) => a.localeCompare(b, 'zh-CN'))];
});

const currentRegionName = computed(() => selectedCity.value || selectedProvince.value);
const chartLevelLabel = computed(() => {
  if (selectedCity.value) return '市级趋势';
  return selectedProvince.value === '全国' ? '全国趋势' : '省级趋势';
});

async function loadCityOptions(province: string) {
  const seq = ++cityOptionsFetchSeq;
  selectedCity.value = '';
  cityOptions.value = [];

  if (!province || province === '全国') return;

  cityOptionsLoading.value = true;
  try {
    const res = await getMacroCityOptionsApi(province);
    if (seq !== cityOptionsFetchSeq) return;
    cityOptions.value = Array.isArray(res.data) ? res.data : [];
  } catch (error) {
    if (seq !== cityOptionsFetchSeq) return;
    cityOptions.value = [];
    console.error('城市GDP列表加载失败:', error);
  } finally {
    if (seq === cityOptionsFetchSeq) {
      cityOptionsLoading.value = false;
    }
  }
}

watch(
  () => props.initialProvince,
  (province) => {
    const nextProvince = province || '全国';
    if (nextProvince !== selectedProvince.value) {
      selectedProvince.value = nextProvince;
    }
  },
);

watch(selectedProvince, loadCityOptions, { immediate: true });

useMacroChart(selectedProvince, {
  chartId: props.chartId,
  tabKey: props.tabKey,
  selectedCity,
});
</script>
<template>
  <div class="macro-wrap" :class="{ 'is-embedded': props.embedded }">
    <div class="province-selector">
      <div class="selector-controls">
        <div class="selector-control">
          <div class="selector-label">选择区域</div>
          <el-select v-model="selectedProvince" placeholder="选择区域" size="default" popper-class="dark-popper">
            <el-option
              v-for="item in provinceList"
              :key="item"
              :label="item === '全国' ? item : item.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, '')"
              :value="item"
            />
          </el-select>
        </div>
        <div v-if="selectedProvince !== '全国'" class="selector-control">
          <div class="selector-label">市级数据</div>
          <el-select
            v-model="selectedCity"
            clearable
            filterable
            :loading="cityOptionsLoading"
            placeholder="省级汇总"
            size="default"
            popper-class="dark-popper"
          >
            <el-option label="省级汇总" value="" />
            <el-option
              v-for="item in cityOptions"
              :key="`${item.province}-${item.city}`"
              :label="item.city"
              :value="item.city"
            />
            <template #empty>
              <div class="selector-empty">
                {{ cityOptionsLoading ? '城市加载中...' : '暂无该省市级 GDP 数据' }}
              </div>
            </template>
          </el-select>
        </div>
      </div>
      <div class="selector-hint">
        当前：<span>{{ currentRegionName }}</span> · {{ chartLevelLabel }}
      </div>
    </div>
    <div class="biz-wrap-content">
      <div class="chart-header">
        <div class="chart-title">GDP 与碳排放趋势 · 2000—2024</div>
        <div class="chart-desc">柱状图为 GDP（亿元），折线为碳排放（万吨） —— 双 Y 轴混合图</div>
      </div>
      <div :id="props.chartId" class="chart-box" />
    </div>
  </div>
</template>
<style lang="scss" scoped>
.macro-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0;
  position: relative;
  background: none;
}
.province-selector {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 100;
  min-width: 168px;
  max-width: min(460px, 58vw);
  background: $panel-bg;
  border: 1px solid $border-color;
  border-radius: 12px;
  padding: 10px 14px;
  backdrop-filter: blur(10px);
  box-shadow: $box-shadow-panel;
  .selector-controls {
    display: flex;
    align-items: flex-end;
    gap: 10px;
  }
  .selector-control {
    flex: 1 1 160px;
    min-width: 150px;
  }
  .selector-label {
    color: rgba($tech-cyan, 0.74);
    font-size: 15px;
    margin-bottom: 6px;
    letter-spacing: 0.14em;
  }
  .selector-hint {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid rgba($tech-cyan, 0.12);
    color: rgba(200, 220, 255, 0.58);
    font-size: 14px;
    letter-spacing: 0.04em;
    span {
      color: $tech-cyan;
      font-weight: 700;
    }
  }
  .selector-empty {
    padding: 8px 12px;
    color: rgba(200, 220, 255, 0.58);
    font-size: 14px;
    text-align: center;
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
.biz-wrap-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: $panel-bg;
  border: 1px solid rgba($tech-cyan, 0.14);
  border-radius: 16px;
  box-shadow: $box-shadow-panel;
  backdrop-filter: blur(10px);
  padding: 60px 18px 14px;
}
.chart-header {
  text-align: center;
  flex-shrink: 0;
  padding: 4px 0 10px;
}
.chart-title {
  color: rgba($tech-cyan, 0.88);
  font-size: 19px;
  font-family: $font-title;
  letter-spacing: 0.14em;
  text-shadow: 0 0 10px rgba($tech-cyan, 0.16);
}
.chart-desc {
  color: rgba(200, 220, 255, 0.4);
  font-size: 15px;
  margin-top: 6px;
  letter-spacing: 0.04em;
}
.chart-box {
  flex: 1;
  min-height: 0;
}
</style>
