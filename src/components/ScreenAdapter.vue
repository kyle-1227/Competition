<script setup lang="ts">
import { ElMessage } from 'element-plus';

const el = ref<HTMLElement | null>(null);
const { isSupported, isFullscreen, toggle } = useFullscreen(el);
provide('isFullscreen', isFullscreen);

onMounted(() => {
  if (!isSupported) {
    ElMessage.warning('您的浏览器不支持全屏！');
    return;
  }
  useEventListener(document, 'keydown', (e) => {
    if (e.key === 'Enter') toggle();
  });
});
</script>

<template>
  <div ref="el" class="screen-adapter" lang="zh-CN">
    <slot />
  </div>
</template>

<style lang="scss" scoped>
.screen-adapter {
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  position: relative;
  isolation: isolate;
  overflow: hidden;
  // 根据设计搞设置即可
  width: 1920px;
  height: 1080px;
  background:
    radial-gradient(circle at 20% 18%, rgba($tech-cyan, 0.12) 0%, transparent 24%),
    radial-gradient(circle at 82% 14%, rgba($tech-green, 0.1) 0%, transparent 22%),
    radial-gradient(circle at 50% 50%, rgba($theme-color, 0.12) 0%, transparent 36%),
    linear-gradient(180deg, #161127 0%, $bg-dark 52%, #090812 100%);
  color: #fff;
  text-align: center;
  font-family: var(--el-font-family);
  background-color: $bg-dark;

  &::before {
    content: '';
    position: absolute;
    inset: 14px;
    border: 1px solid rgba($tech-cyan, 0.1);
    border-radius: 22px;
    box-shadow: inset 0 0 30px rgba($tech-cyan, 0.04);
    pointer-events: none;
    z-index: -1;
  }

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba($tech-cyan, 0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba($tech-cyan, 0.03) 1px, transparent 1px);
    background-size: 48px 48px;
    mask-image: radial-gradient(circle at center, rgba(0, 0, 0, 0.85), transparent 90%);
    pointer-events: none;
    opacity: 0.6;
    z-index: -1;
  }
}
</style>
