<script setup lang="ts">
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
<script lang="ts">
export default { name: 'BizMacro' };
</script>
<style lang="scss" scoped>
.biz-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 10px 20px 25px;
  position: relative;
}
.province-selector {
  position: absolute;
  top: 16px;
  left: 24px;
  z-index: 100;
  background: rgba(10, 15, 30, 0.85);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 8px;
  padding: 8px 12px;
  backdrop-filter: blur(6px);
  min-width: 160px;
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
}
.biz-wrap-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.chart-header {
  text-align: center;
  flex-shrink: 0;
  padding-bottom: 6px;
}
.chart-title {
  color: rgba(0, 229, 255, 0.85);
  font-size: 15px;
  letter-spacing: 1px;
}
.chart-desc {
  color: rgba(200, 220, 255, 0.4);
  font-size: 11px;
  margin-top: 2px;
}
.chart-box {
  flex: 1;
  min-height: 0;
}
</style>
