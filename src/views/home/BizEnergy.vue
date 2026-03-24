<script setup lang="ts">
import { useEnergyScatter } from './hooks/useChart';

useEnergyScatter();
</script>
<template>
  <div class="biz-wrap">
    <div class="biz-wrap-content">
      <div class="chart-header">
        <div class="chart-title">绿色金融指数 vs 能耗强度 · 散点分析</div>
        <div class="chart-desc">横轴为绿色金融综合得分，纵轴为能耗强度 —— 虚线为线性拟合趋势线</div>
      </div>
      <div id="energy-scatter" class="chart-box" />
    </div>
  </div>
</template>
<script lang="ts">
export default { name: 'BizEnergy' };
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
