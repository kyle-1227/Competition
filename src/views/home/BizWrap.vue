<script setup lang="ts">
import { useStackedBar, useRadar } from './hooks/useChart';
import { useMap } from './hooks/useMap';
import { selectedYear } from './hooks/provinceData';

useStackedBar();
useRadar();
useMap();
</script>

<template>
  <div class="biz-wrap">
    <div class="biz-wrap-left">
      <div class="chart-title">绿色金融指数结构 · {{ selectedYear }}年（TOP 15）</div>
      <div id="bar"></div>
    </div>
    <div class="biz-wrap-center">
      <div id="map"></div>
      <div class="map-legend">
        <div class="legend-item">
          <span class="legend-line green"></span>
          <span>正向溢出（协同减排）</span>
        </div>
        <div class="legend-item">
          <span class="legend-line red"></span>
          <span>污染转移（负外部性）</span>
        </div>
      </div>
      <div class="map-approve">本底图基于国家地理信息公共服务平台标准地图制作，审图号：GS(2025)5996号</div>
    </div>
    <div class="biz-wrap-right">
      <div class="chart-title">绿色金融雷达图 · {{ selectedYear }}年</div>
      <div id="radar"></div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.biz-wrap {
  display: flex;
  height: 100%;
  padding: 10px 0 25px 0;
  &-left {
    flex: 0 0 320px;
    padding: 10px;
    #bar {
      height: 400px;
    }
  }
  &-center {
    flex: 2 0 auto;
    position: relative;
    #map {
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
    }
    .legend-item {
      display: flex;
      align-items: center;
      gap: 8px;
      color: rgba(255, 255, 255, 0.8);
      font-size: 11px;
      line-height: 20px;
    }
    .legend-line {
      display: inline-block;
      width: 24px;
      height: 3px;
      border-radius: 2px;
      &.green {
        background: linear-gradient(90deg, #00e5ff, #76ff03);
        box-shadow: 0 0 6px rgba(0, 229, 255, 0.6);
      }
      &.red {
        background: linear-gradient(90deg, #ff4444, #ffab00);
        box-shadow: 0 0 6px rgba(255, 68, 68, 0.6);
      }
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
  &-right {
    flex: 0 0 320px;
    padding: 10px;
    #radar {
      width: 100%;
      height: 400px;
    }
  }
}
.chart-title {
  text-align: center;
  color: rgba(0, 229, 255, 0.85);
  font-size: 14px;
  padding-bottom: 5px;
  letter-spacing: 1px;
}
</style>
