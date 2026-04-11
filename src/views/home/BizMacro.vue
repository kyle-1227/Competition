<script setup lang="ts">
defineOptions({ name: 'BizMacro' });

import { useMacroChart } from './hooks/useChart';
import { realProvinceData, excludeProvincesWithoutPanelData } from './hooks/provinceData';

const selectedProvince = ref('全国');

const provinceList = computed(() => {
  const provinces = excludeProvincesWithoutPanelData(realProvinceData.value.map((p) => p.province));
  return ['全国', ...provinces.sort((a, b) => a.localeCompare(b, 'zh-CN'))];
});

useMacroChart(selectedProvince);
</script>
<template>
  <div class="biz-wrap">
    <div class="province-selector">
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
    <div class="biz-wrap-content">
      <div class="chart-header">
        <div class="chart-title">GDP 与碳排放趋势 · 2000—2024</div>
        <div class="chart-desc">柱状图为 GDP（亿元），折线为碳排放（万吨） —— 双 Y 轴混合图</div>
      </div>
      <div id="macro-chart" class="chart-box" />
    </div>
  </div>
</template>
<style lang="scss" scoped>
.biz-wrap {
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
  max-width: min(240px, 42vw);
  background: $panel-bg;
  border: 1px solid $border-color;
  border-radius: 12px;
  padding: 8px 12px;
  backdrop-filter: blur(10px);
  box-shadow: $box-shadow-panel;
  .selector-label {
    color: rgba($tech-cyan, 0.74);
    font-size: 11px;
    margin-bottom: 4px;
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
    min-height: 40px !important;
    padding: 0 12px !important;
    transition: border-color 0.3s, box-shadow 0.3s;
    &:hover,
    &.is-focused {
      border-color: rgba($tech-cyan, 0.5) !important;
      box-shadow: 0 0 12px rgba($tech-cyan, 0.15) !important;
    }
  }
  :deep(.el-select__selected-item) {
    color: $tech-cyan !important;
    font-weight: bold;
    display: flex !important;
    align-items: center !important;
    min-height: 24px !important;
    line-height: 1 !important;
  }
  :deep(.el-select__placeholder) {
    color: rgba($tech-cyan, 0.5) !important;
    display: flex !important;
    align-items: center !important;
    min-height: 24px !important;
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
    min-height: 40px !important;
    padding: 0 12px !important;
    &:hover,
    &.is-focus {
      border-color: rgba($tech-cyan, 0.5) !important;
      box-shadow: 0 0 12px rgba($tech-cyan, 0.15) !important;
    }
  }
  :deep(.el-input__inner) {
    color: $tech-cyan !important;
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
  font-size: 15px;
  font-family: $font-title;
  letter-spacing: 0.14em;
  text-shadow: 0 0 10px rgba($tech-cyan, 0.16);
}
.chart-desc {
  color: rgba(200, 220, 255, 0.4);
  font-size: 11px;
  margin-top: 4px;
  letter-spacing: 0.04em;
}
.chart-box {
  flex: 1;
  min-height: 0;
}
</style>
