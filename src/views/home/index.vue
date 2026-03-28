<template>
  <ScreenAdapter>
    <div class="title">绿色金融赋能新质生产力与区域协同减排智能沙盘</div>
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
    <BizGreenFinance v-show="activeTab === 'greenFinance'" class="content" />
    <!-- 碳排放底色 -->
    <BizCarbon v-show="activeTab === 'carbon'" class="content" />
    <!-- 碳减排效率预测（energy Tab：碳排放强度动态预测沙盘 BizCarbonPrediction） -->
    <BizCarbonPrediction v-show="activeTab === 'energy'" class="content" />
    <!-- 宏观经济动态 -->
    <BizMacro v-show="activeTab === 'macro'" class="content" />

    <!-- 底部年份时间轴（宏观经济动态与碳排放强度预测 Tab 不展示） -->
    <div v-show="activeTab !== 'macro' && activeTab !== 'energy'" class="timeline-bar">
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
  { key: 'greenFinance', label: '绿色金融监测', icon: '💹' },
  { key: 'carbon', label: '碳排放底色', icon: '🏭' },
  { key: 'energy', label: '碳排放强度预测', icon: '⚡' },
  { key: 'macro', label: '宏观经济动态', icon: '📈' },
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

<script lang="ts">
export default {
  name: 'HomePage',
};
</script>

<style lang="scss" scoped>
.title {
  flex: 0 0 72px;
  line-height: 72px;
  font-size: 24px;
  font-family: var(--el-font-family);
  letter-spacing: 0.02em;
}
.content {
  flex: 1;
}
/* ===== 科技风 Tab 导航栏 ===== */
.tab-nav {
  flex: 0 0 auto;
  display: flex;
  justify-content: center;
  gap: 6px;
  padding: 0 40px 8px;
  position: relative;
  z-index: 50;
  font-family: var(--el-font-family);
}
.tab-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 22px;
  cursor: pointer;
  border: 1px solid rgba(0, 229, 255, 0.15);
  border-radius: 6px;
  background: rgba(10, 15, 30, 0.6);
  backdrop-filter: blur(8px);
  color: rgba(255, 255, 255, 0.55);
  font-size: 13px;
  letter-spacing: 0;
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
    letter-spacing: 0;
  }
  .tab-glow {
    position: absolute;
    inset: 0;
    opacity: 0;
    background: radial-gradient(ellipse at 50% 100%, rgba(0, 229, 255, 0.15) 0%, transparent 70%);
    transition: opacity 0.35s;
  }
  &:hover {
    border-color: rgba(0, 229, 255, 0.35);
    color: rgba(255, 255, 255, 0.8);
    background: rgba(10, 15, 30, 0.8);
    .tab-icon {
      filter: grayscale(0);
    }
    .tab-glow {
      opacity: 0.6;
    }
  }
  &.active {
    border-color: rgba(0, 229, 255, 0.6);
    color: #fff;
    background: linear-gradient(180deg, rgba(0, 229, 255, 0.08) 0%, rgba(10, 15, 30, 0.9) 100%);
    box-shadow: 0 0 12px rgba(0, 229, 255, 0.2), inset 0 1px 0 rgba(0, 229, 255, 0.3);
    text-shadow: 0 0 8px rgba(0, 229, 255, 0.5);
    .tab-icon {
      filter: grayscale(0) drop-shadow(0 0 4px rgba(0, 229, 255, 0.6));
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
      background: linear-gradient(90deg, transparent, #00e5ff, transparent);
      box-shadow: 0 0 8px rgba(0, 229, 255, 0.6);
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
  background: rgba(10, 15, 30, 0.85);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 8px;
  padding: 6px 20px;
  backdrop-filter: blur(6px);
}
.timeline-label {
  color: rgba(0, 229, 255, 0.8);
  font-size: 12px;
  white-space: nowrap;
}
.timeline-slider {
  flex: 1;
  :deep(.el-slider__runway) {
    background: rgba(0, 229, 255, 0.12);
  }
  :deep(.el-slider__bar) {
    background: linear-gradient(90deg, #00e5ff, #7c4dff);
  }
  :deep(.el-slider__button) {
    width: 14px;
    height: 14px;
    border: 2px solid #00e5ff;
    background: #131722;
  }
  :deep(.el-slider__marks-text) {
    color: rgba(255, 255, 255, 0.45);
    font-size: 10px;
  }
}
.year-badge {
  background: rgba(0, 229, 255, 0.15);
  border: 1px solid rgba(0, 229, 255, 0.4);
  border-radius: 4px;
  padding: 2px 10px;
  color: #00e5ff;
  font-size: 14px;
  font-weight: bold;
  white-space: nowrap;
}
</style>
