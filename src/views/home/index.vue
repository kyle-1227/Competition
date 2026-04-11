<template>
  <ScreenAdapter>
    <div class="title">绿色金融与区域碳减排空间协同智能测算平台</div>
    <!-- 科技风 Tab 导航栏 -->
    <div class="tab-nav">
      <div
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
        <div class="tab-glow" />
      </div>
    </div>

    <!-- 绿色金融监测 -->
    <div class="content-shell">
      <BizGreenFinance v-show="activeTab === 'greenFinance'" class="content" />
    <!-- 碳排放底色 -->
    <BizCarbon v-show="activeTab === 'carbon'" class="content" />
    <!-- 碳减排效率预测（energy Tab：碳排放强度动态预测沙盘 BizCarbonPrediction） -->
    <BizCarbonPrediction v-show="activeTab === 'energy'" class="content" />
    <!-- 宏观经济动态 -->
      <BizMacro v-show="activeTab === 'macro'" class="content" />
    </div>

    <!-- 底部年份时间轴（宏观经济动态与碳排放强度预测 Tab 不展示） -->
    <div v-if="false" v-show="activeTab === 'carbon'" class="timeline-bar">
      <span class="timeline-label">数据年份</span>
      <el-slider
        v-model="timelineYear"
        :min="2000"
        :max="2024"
        :step="1"
        :marks="yearMarks"
        :format-tooltip="(v: number) => `${v}年`"
        class="timeline-slider"
        @change="commitTimelineYear"
      />
      <div class="year-badge">{{ timelineYear }}年</div>
    </div>
  </ScreenAdapter>
</template>

<script setup lang="ts">
defineOptions({ name: 'HomePage' });

import BizGreenFinance from './BizGreenFinance.vue';
import BizCarbon from './BizCarbon.vue';
import BizCarbonPrediction from './BizCarbonPrediction.vue';
import BizMacro from './BizMacro.vue';
import {
  selectedYear,
  timelineYear,
  selectedProvince,
  fetchProvinceData,
  fetchCityData,
} from './hooks/provinceData';

function commitTimelineYear() {
  const y = timelineYear.value;
  if (y === selectedYear.value) return;
  selectedYear.value = y;
  fetchProvinceData(y);
  if (selectedProvince.value) {
    fetchCityData(selectedProvince.value, y);
  }
}

onMounted(() => {
  timelineYear.value = selectedYear.value;
  fetchProvinceData(selectedYear.value);
  if (selectedProvince.value) {
    fetchCityData(selectedProvince.value, selectedYear.value);
  }
});

watch(selectedYear, (y) => {
  timelineYear.value = y;
});

watch(selectedProvince, (name) => {
  if (name) {
    fetchCityData(name, selectedYear.value);
  }
});

const tabs = [
  { key: 'greenFinance', label: '绿色金融综合指数', icon: '💹' },
  { key: 'carbon', label: '碳排放底色', icon: '🏭' },
  { key: 'energy', label: '碳排放强度预测', icon: '⚡' },
  { key: 'macro', label: '宏观经济', icon: '📈' },
];
const activeTab = ref('greenFinance');

const yearMarks = {
  2000: '2000',
  2005: '2005',
  2010: '2010',
  2015: '2015',
  2020: '2020',
  2024: '2024',
};

provide('activeTab', activeTab);
</script>

<style lang="scss" scoped>
.title {
  flex: 0 0 72px;
  position: relative;
  line-height: 72px;
  font-size: 28px;
  font-family: $font-title;
  letter-spacing: 0.18em;
  color: rgba(235, 246, 255, 0.95);
  text-shadow: 0 0 18px rgba($tech-cyan, 0.24);

  &::after {
    content: '';
    position: absolute;
    left: 50%;
    bottom: 12px;
    width: min(580px, 42vw);
    height: 2px;
    transform: translateX(-50%);
    background: linear-gradient(90deg, transparent, rgba($tech-cyan, 0.85), transparent);
    box-shadow: $glow-shadow;
  }
}
.content {
  flex: 1;
  min-height: 0;
}
.content-shell {
  flex: 1;
  min-height: 0;
  margin: 0 14px 14px;
  padding: 14px;
  background: $panel-bg;
  border: 1px solid rgba($tech-cyan, 0.16);
  border-radius: 20px;
  backdrop-filter: blur(12px);
  box-shadow: $box-shadow-panel;
  overflow: hidden;
}
/* ===== 科技风 Tab 导航栏 ===== */
.tab-nav {
  flex: 0 0 auto;
  display: flex;
  justify-content: center;
  gap: 10px;
  padding: 0 40px 10px;
  position: relative;
  z-index: 50;
  font-family: $font-title;
}
.tab-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  cursor: pointer;
  border: 1px solid rgba($tech-cyan, 0.18);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(4, 10, 24, 0.72));
  backdrop-filter: blur(10px);
  box-shadow: inset 0 0 22px rgba($tech-cyan, 0.04);
  color: rgba(255, 255, 255, 0.58);
  font-size: 13px;
  letter-spacing: 0.06em;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  .tab-icon {
    font-size: 15px;
    filter: grayscale(0.8);
    transition: filter 0.35s;
  }
  .tab-label {
    position: relative;
    z-index: 1;
    text-transform: uppercase;
  }
  .tab-glow {
    position: absolute;
    inset: 0;
    opacity: 0;
    background:
      radial-gradient(ellipse at 50% 100%, rgba($tech-cyan, 0.18) 0%, transparent 70%),
      linear-gradient(90deg, transparent, rgba($tech-cyan, 0.08), transparent);
    transition: opacity 0.35s;
  }
  &:hover {
    transform: translateY(-2px);
    border-color: rgba($tech-cyan, 0.38);
    color: rgba(255, 255, 255, 0.88);
    background: linear-gradient(180deg, rgba($tech-cyan, 0.08), rgba(4, 10, 24, 0.84));
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35), inset 0 0 18px rgba($tech-cyan, 0.06);
    .tab-icon {
      filter: grayscale(0);
    }
    .tab-glow {
      opacity: 0.6;
    }
  }
  &.active {
    border-color: rgba($tech-cyan, 0.62);
    color: #fff;
    background: linear-gradient(180deg, rgba($tech-cyan, 0.14) 0%, rgba(4, 10, 24, 0.92) 100%);
    box-shadow: $glow-shadow, inset 0 1px 0 rgba($tech-cyan, 0.3);
    text-shadow: 0 0 8px rgba($tech-cyan, 0.5);
    .tab-icon {
      filter: grayscale(0) drop-shadow(0 0 4px rgba($tech-cyan, 0.6));
    }
    .tab-glow {
      opacity: 1;
    }
    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 20%;
      right: 20%;
      height: 2px;
      background: linear-gradient(90deg, transparent, $tech-cyan, transparent);
      box-shadow: 0 0 8px rgba($tech-cyan, 0.6);
    }
  }
}

/* ===== 底部年份时间轴 ===== */
.timeline-bar {
  position: absolute;
  bottom: 8px;
  left: 340px;
  right: 340px;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 100;
  background: $panel-bg;
  border: 1px solid $border-color;
  border-radius: 12px;
  padding: 8px 20px;
  backdrop-filter: blur(10px);
  box-shadow: $box-shadow-panel;
}
.timeline-label {
  color: rgba($tech-cyan, 0.84);
  font-size: 12px;
  letter-spacing: 0.16em;
  white-space: nowrap;
}
.timeline-slider {
  flex: 1;
  :deep(.el-slider__runway) {
    background: rgba($tech-cyan, 0.12);
  }
  :deep(.el-slider__bar) {
    background: linear-gradient(90deg, $tech-cyan, $tech-green, $theme-color);
  }
  :deep(.el-slider__button) {
    width: 14px;
    height: 14px;
    border: 2px solid $tech-cyan;
    background: $bg-dark;
    box-shadow: 0 0 0 4px rgba($tech-cyan, 0.08), 0 0 14px rgba($tech-cyan, 0.4);
  }
  :deep(.el-slider__marks-text) {
    color: rgba(255, 255, 255, 0.45);
    font-size: 10px;
  }
}
.year-badge {
  background: rgba($tech-cyan, 0.12);
  border: 1px solid rgba($tech-cyan, 0.4);
  border-radius: 999px;
  padding: 4px 12px;
  color: $tech-cyan;
  font-size: 14px;
  font-weight: bold;
  box-shadow: inset 0 0 14px rgba($tech-cyan, 0.08);
  white-space: nowrap;
}
</style>
