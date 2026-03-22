<template>
  <ScreenAdapter>
    <div class="title">绿色金融赋能新质生产力与区域协同减排智能沙盘</div>
    <BizWrap class="content" />

    <!-- 底部年份时间轴 -->
    <div class="timeline-bar">
      <span class="timeline-label">数据年份</span>
      <el-slider
        v-model="selectedYear"
        :min="2000"
        :max="2024"
        :step="1"
        :marks="yearMarks"
        :format-tooltip="(v: number) => `${v}年`"
        class="timeline-slider"
      />
      <div class="year-badge">{{ selectedYear }}年</div>
    </div>

    <!-- 右下角 TFEE 阈值滑块 -->
    <div class="tfee-panel">
      <div class="tfee-title">全要素能源效率 (TFEE) 阈值模拟</div>
      <el-slider
        v-model="tfeeThreshold"
        :min="0"
        :max="1"
        :step="0.01"
        :format-tooltip="(v: number) => v.toFixed(2)"
        class="tfee-slider"
      />
      <div class="tfee-value">
        当前: <b>{{ tfeeThreshold.toFixed(2) }}</b>
        <span class="tfee-threshold-mark" :class="{ active: tfeeThreshold >= 0.62 }"> 门槛值 0.62 </span>
      </div>
    </div>

    <!-- 门槛跨越弹窗 -->
    <Transition name="boom">
      <div v-if="showThresholdEffect" class="threshold-popup" @click="showThresholdEffect = false">
        <div class="popup-icon">⚡</div>
        <div class="popup-number">
          <span class="popup-prefix">减碳效应提升</span>
          <span class="popup-value">{{ animatedPercent }}%</span>
        </div>
        <div class="popup-sub">TFEE 突破门槛值 0.62，污染转移效应显著弱化</div>
      </div>
    </Transition>
  </ScreenAdapter>
</template>

<script setup lang="ts">
import BizWrap from './BizWrap.vue';
import { selectedYear, tfeeThreshold } from './hooks/provinceData';

const showThresholdEffect = ref(false);
const animatedPercent = ref('0.0');
let hasCrossed = false;

const yearMarks = {
  2000: '2000',
  2005: '2005',
  2010: '2010',
  2015: '2015',
  2020: '2020',
  2024: '2024',
};

watch(tfeeThreshold, (val, oldVal) => {
  if (val >= 0.62 && oldVal < 0.62 && !hasCrossed) {
    hasCrossed = true;
    showThresholdEffect.value = true;
    animateNumber(0, 184.5, 1200);
    setTimeout(() => {
      showThresholdEffect.value = false;
    }, 4000);
  }
  if (val < 0.62) {
    hasCrossed = false;
  }
});

function animateNumber(from: number, to: number, duration: number) {
  const start = performance.now();
  function tick(now: number) {
    const t = Math.min((now - start) / duration, 1);
    const ease = 1 - (1 - t) ** 3;
    animatedPercent.value = (from + (to - from) * ease).toFixed(1);
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
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
}
.content {
  flex: 1;
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

/* ===== 右下角 TFEE 滑块 ===== */
.tfee-panel {
  position: absolute;
  bottom: 50px;
  right: 16px;
  width: 280px;
  z-index: 100;
  background: rgba(10, 15, 30, 0.9);
  border: 1px solid rgba(0, 229, 255, 0.2);
  border-radius: 8px;
  padding: 12px 16px;
  backdrop-filter: blur(6px);
}
.tfee-title {
  color: rgba(0, 229, 255, 0.85);
  font-size: 12px;
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}
.tfee-slider {
  :deep(.el-slider__runway) {
    background: linear-gradient(90deg, rgba(255, 80, 80, 0.3), rgba(80, 220, 120, 0.3));
  }
  :deep(.el-slider__bar) {
    background: linear-gradient(90deg, rgb(255, 80, 80), rgb(80, 220, 120));
  }
  :deep(.el-slider__button) {
    width: 14px;
    height: 14px;
    border: 2px solid #fff;
    background: #131722;
  }
}
.tfee-value {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
  color: #aaa;
  font-size: 12px;
  b {
    color: #fff;
    font-size: 16px;
  }
}
.tfee-threshold-mark {
  padding: 1px 6px;
  border-radius: 3px;
  border: 1px dashed rgba(255, 200, 50, 0.5);
  color: rgba(255, 200, 50, 0.7);
  font-size: 10px;
  transition: all 0.3s;
  &.active {
    border-color: rgb(80, 220, 120);
    color: rgb(80, 220, 120);
    background: rgba(80, 220, 120, 0.1);
    font-weight: bold;
  }
}

/* ===== 门槛弹窗动画 ===== */
.threshold-popup {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 9999;
  text-align: center;
  pointer-events: auto;
  cursor: pointer;
  padding: 30px 50px;
  background: radial-gradient(ellipse at center, rgba(0, 229, 255, 0.15) 0%, rgba(10, 15, 30, 0.95) 70%);
  border: 1px solid rgba(0, 229, 255, 0.3);
  border-radius: 16px;
  backdrop-filter: blur(12px);
}
.popup-icon {
  font-size: 48px;
  margin-bottom: 8px;
  animation: pulse-glow 0.6s ease-in-out infinite alternate;
}
.popup-number {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 8px;
}
.popup-prefix {
  color: rgba(255, 255, 255, 0.7);
  font-size: 18px;
}
.popup-value {
  font-size: 56px;
  font-weight: 900;
  background: linear-gradient(135deg, #00e5ff, #76ff03);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 20px rgba(0, 229, 255, 0.6));
}
.popup-sub {
  margin-top: 10px;
  color: rgba(0, 229, 255, 0.7);
  font-size: 13px;
  letter-spacing: 1px;
}

@keyframes pulse-glow {
  from {
    transform: scale(1);
    filter: brightness(1);
  }
  to {
    transform: scale(1.15);
    filter: brightness(1.5);
  }
}

.boom-enter-active {
  animation: boom-in 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.boom-leave-active {
  animation: boom-out 0.4s ease-in;
}
@keyframes boom-in {
  0% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.3);
  }
  50% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1.1);
  }
  100% {
    transform: translate(-50%, -50%) scale(1);
  }
}
@keyframes boom-out {
  to {
    opacity: 0;
    transform: translate(-50%, -50%) scale(1.5);
  }
}
</style>
