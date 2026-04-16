<template>
  <ScreenAdapter>
    <div class="home-page">
      <div class="title">绿色金融与区域碳减排空间协同智能测算平台</div>

      <div class="home-page__ai-anchor">
        <AiAssistantPanel :active-tab="activeTab" :tab-labels="tabLabelMap" />
      </div>

      <div class="tab-nav">
        <div
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-item"
          :class="{ active: activeTab === tab.key }"
          @click="setActiveTab(tab.key)"
        >
          <span class="tab-label">{{ tab.label }}</span>
          <div class="tab-glow" />
        </div>
      </div>

      <div class="content-shell">
        <div class="content-stage">
          <div
            v-for="tab in tabs"
            :key="tab.key"
            class="content-panel"
            :class="{ 'is-active': activeTab === tab.key }"
          >
            <component
              v-if="visitedTabs[tab.key]"
              :is="tabComponents[tab.key]"
              class="content"
            />
          </div>
        </div>
      </div>

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
    </div>
  </ScreenAdapter>
</template>

<script setup lang="ts">
defineOptions({ name: 'HomePage' });

import { defineAsyncComponent, onMounted, provide, reactive, ref, watch } from 'vue';
import AiAssistantPanel from './components/AiAssistantPanel.vue';
import {
  selectedYear,
  timelineYear,
  selectedProvince,
  fetchProvinceData,
  fetchCityData,
} from './hooks/provinceData';

type HomeTabKey = 'greenFinance' | 'carbon' | 'energy';

const tabComponents: Record<HomeTabKey, ReturnType<typeof defineAsyncComponent>> = {
  greenFinance: defineAsyncComponent(() => import('./BizGreenFinance.vue')),
  carbon: defineAsyncComponent(() => import('./BizCarbon.vue')),
  energy: defineAsyncComponent(() => import('./BizCarbonPredictionV3.vue')),
};

const visitedTabs = reactive<Record<HomeTabKey, boolean>>({
  greenFinance: true,
  carbon: false,
  energy: false,
});

function commitTimelineYear() {
  const year = timelineYear.value;
  if (year === selectedYear.value) return;
  selectedYear.value = year;
  fetchProvinceData(year);
  if (selectedProvince.value) {
    fetchCityData(selectedProvince.value, year);
  }
}

onMounted(() => {
  timelineYear.value = selectedYear.value;
  fetchProvinceData(selectedYear.value);
  if (selectedProvince.value) {
    fetchCityData(selectedProvince.value, selectedYear.value);
  }
});

watch(selectedYear, (year) => {
  timelineYear.value = year;
});

watch(selectedProvince, (province) => {
  if (province) {
    fetchCityData(province, selectedYear.value);
  }
});

const tabs = [
  { key: 'greenFinance', label: '绿色金融综合指数' },
  { key: 'carbon', label: '碳排放底色' },
  { key: 'energy', label: '碳排放强度预测' },
] as Array<{ key: HomeTabKey; label: string }>;

const tabLabelMap: Record<HomeTabKey, string> = {
  greenFinance: '绿色金融综合指数',
  carbon: '碳排放底色',
  energy: '碳排放强度预测',
};

const activeTab = ref<HomeTabKey>('greenFinance');

function setActiveTab(tabKey: string) {
  const nextTab = tabKey as HomeTabKey;
  visitedTabs[nextTab] = true;
  activeTab.value = nextTab;
}

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
.home-page {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
}

.title {
  flex: 0 0 72px;
  position: relative;
  line-height: 72px;
  font-size: 33px;
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

.home-page__ai-anchor {
  position: absolute;
  top: 20px;
  right: 30px;
  z-index: 140;
  pointer-events: none;
}

.content {
  width: 100%;
  height: 100%;
  min-height: 0;
}

.content-shell {
  flex: 1;
  min-height: 0;
  position: relative;
  margin: 0 14px 14px;
  padding: 14px;
  background: $panel-bg;
  border: 1px solid rgba($tech-cyan, 0.16);
  border-radius: 20px;
  backdrop-filter: blur(12px);
  box-shadow: $box-shadow-panel;
  overflow: hidden;
}

.content-stage {
  position: relative;
  width: 100%;
  height: 100%;
}

.content-panel {
  position: absolute;
  inset: 0;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translateY(12px) scale(0.995);
  transition:
    opacity 0.24s ease,
    transform 0.24s ease,
    visibility 0.24s ease;
  will-change: opacity, transform;
}

.content-panel.is-active {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transform: translateY(0) scale(1);
}

.tab-nav {
  flex: 0 0 auto;
  display: flex;
  justify-content: center;
  gap: 14px;
  padding: 4px 40px 14px;
  flex-wrap: wrap;
  position: relative;
  z-index: 50;
  font-family: $font-title;
}

.tab-item {
  position: relative;
  display: flex;
  align-items: center;
  padding: 13px 30px;
  min-height: 52px;
  cursor: pointer;
  border: 1px solid rgba($tech-cyan, 0.18);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(4, 10, 24, 0.72));
  backdrop-filter: blur(10px);
  box-shadow: inset 0 0 22px rgba($tech-cyan, 0.04);
  color: rgba(255, 255, 255, 0.58);
  font-size: 17px;
  letter-spacing: 0.04em;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;

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

.timeline-bar {
  position: absolute;
  bottom: 8px;
  left: 340px;
  right: 340px;
  display: flex;
  align-items: center;
  gap: 14px;
  z-index: 100;
  background: $panel-bg;
  border: 1px solid $border-color;
  border-radius: 12px;
  padding: 10px 22px;
  backdrop-filter: blur(10px);
  box-shadow: $box-shadow-panel;
}

.timeline-label {
  color: rgba($tech-cyan, 0.84);
  font-size: 16px;
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

.year-badge {
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
</style>
