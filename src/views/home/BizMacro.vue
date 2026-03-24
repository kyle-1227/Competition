<script setup lang="ts">
import { useMacroChart } from './hooks/useChart';

useMacroChart();
</script>
<template>
  <div class="biz-wrap">
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
  height: 100%;
  padding: 10px 20px 25px;
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
