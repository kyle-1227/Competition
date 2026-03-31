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
  // justify-content: center;
  // align-items: center;
  box-sizing: border-box;
  // 根据设计搞设置即可
  width: 1600px;
  height: 900px;
  color: #fff;
  text-align: center;
  font-family: var(--el-font-family);
  background-color: #131124;
}
</style>
