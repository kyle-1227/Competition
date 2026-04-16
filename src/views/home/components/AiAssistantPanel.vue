<template>
  <div class="ai-assistant" :class="{ 'is-open': panelOpen }">
    <button type="button" class="ai-assistant__trigger" @click="togglePanel()">
      <span class="ai-assistant__trigger-dot" />
      <span>{{ panelOpen ? '收起 AI 助手' : '打开 AI 助手' }}</span>
    </button>

    <transition name="ai-panel-fade">
      <section v-if="panelOpen" class="ai-assistant__panel">
        <div class="ai-assistant__header">
          <div>
            <div class="ai-assistant__title">DeepSeek 答疑助手</div>
            <div class="ai-assistant__subtitle">当前页面：{{ currentTabLabel }}</div>
          </div>
          <button type="button" class="ai-assistant__close" @click="togglePanel(false)">×</button>
        </div>

        <div class="ai-assistant__toolbar">
          <button
            type="button"
            class="ai-assistant__action ai-assistant__action--primary"
            :disabled="loading"
            @click="handleSummary"
          >
            {{ loading && requestMode === 'summary' ? '总结生成中…' : '生成当前页总结' }}
          </button>
          <button type="button" class="ai-assistant__action" :disabled="loading" @click="clearMessages">
            清空对话
          </button>
        </div>

        <div ref="messageListRef" class="ai-assistant__messages">
          <div v-if="!messages.length" class="ai-assistant__empty">
            <div class="ai-assistant__empty-title">可以直接开始提问</div>
            <div class="ai-assistant__empty-text">
              我会结合当前页面、年份、区域下钻和已加载数据来回答，也支持一键生成当前页总结。
            </div>
          </div>

          <div
            v-for="message in messages"
            :key="message.id"
            class="ai-assistant__message"
            :class="[
              `is-${message.role}`,
              `is-${message.kind}`,
              `status-${message.status}`,
            ]"
          >
            <div class="ai-assistant__message-meta">
              <div class="ai-assistant__meta-left">
                <span class="ai-assistant__role-chip">{{ message.role === 'user' ? '你' : 'AI' }}</span>
                <span class="ai-assistant__page-chip">{{ message.pageTitle }}</span>
              </div>
              <span v-if="message.status !== 'done' && message.role === 'assistant'" class="ai-assistant__status-chip">
                {{ message.phaseText || '正在处理…' }}
              </span>
            </div>

            <div v-if="message.toolTraces.length" class="ai-assistant__tool-list">
              <div
                v-for="trace in message.toolTraces"
                :key="trace.id"
                class="ai-assistant__tool-item"
                :class="{
                  'is-running': trace.ok === null,
                  'is-success': trace.ok === true,
                  'is-error': trace.ok === false,
                }"
              >
                <span class="ai-assistant__tool-name">{{ friendlyToolName(trace.name) }}</span>
                <span class="ai-assistant__tool-summary">{{ trace.summary }}</span>
              </div>
            </div>

            <div
              v-if="message.role === 'assistant'"
              class="ai-assistant__message-body ai-assistant__message-body--markdown"
              v-html="renderAssistantContent(message.content, message.status)"
            />
            <div v-else class="ai-assistant__message-body ai-assistant__message-body--plain">
              {{ message.content }}
            </div>
          </div>
        </div>

        <div v-if="errorText" class="ai-assistant__error">{{ errorText }}</div>

        <div class="ai-assistant__composer">
          <textarea
            v-model="draft"
            class="ai-assistant__textarea"
            :disabled="loading"
            placeholder="输入你想问的问题，例如：当前页面最值得关注的趋势是什么？"
            @keydown.ctrl.enter.prevent="handleAsk"
          />
          <div class="ai-assistant__composer-foot">
            <span class="ai-assistant__hint">Ctrl + Enter 发送</span>
            <button
              type="button"
              class="ai-assistant__send"
              :disabled="loading || !draft.trim()"
              @click="handleAsk"
            >
              {{ loading && requestMode === 'chat' ? '提问中…' : '提问' }}
            </button>
          </div>
        </div>
      </section>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import MarkdownIt from 'markdown-it';
import { useAiAssistant, type AiAssistantMessage } from '../hooks/aiAssistant';
import type { AiPageKey } from '@/api/modules/ai';

const props = defineProps<{
  activeTab: AiPageKey;
  tabLabels: Record<AiPageKey, string>;
}>();

const markdown = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
});

const toolNameMap: Record<string, string> = {
  get_green_finance_province_data: '省级绿色金融数据',
  get_green_finance_city_data: '城市绿色金融关联数据',
  get_green_finance_province_history: '省级绿色金融历史',
  get_green_finance_city_history: '城市绿色金融历史',
  get_carbon_province_data: '省级碳排放数据',
  get_carbon_city_data: '城市碳排放对比数据',
  get_carbon_province_history: '省级碳排放历史',
  get_carbon_city_history: '城市碳排放历史',
  get_energy_prediction_data: '预测情景与对比数据',
  get_macro_series_data: '宏观时间序列',
  get_macro_stats_data: '宏观描述性统计',
};

const draft = ref('');
const messageListRef = ref<HTMLElement | null>(null);

const {
  panelOpen,
  loading,
  requestMode,
  messages,
  errorText,
  sendQuestion,
  generateSummary,
  clearMessages,
  togglePanel,
} = useAiAssistant();

const currentTabLabel = computed(() => props.tabLabels[props.activeTab] || props.activeTab);
const messageSignature = computed(() => messages.value.map((message) => `${message.id}:${message.status}:${message.content.length}:${message.toolTraces.length}`).join('|'));

function friendlyToolName(name: string) {
  return toolNameMap[name] || name;
}

function renderAssistantContent(content: string, status: AiAssistantMessage['status']) {
  if (!content.trim()) {
    const hint = status === 'tooling' ? '正在查询当前页数据…' : 'AI 正在组织回答…';
    return `<p>${hint}</p>`;
  }
  return markdown.render(content);
}

async function handleAsk() {
  const question = draft.value.trim();
  if (!question || loading.value) return;
  draft.value = '';
  try {
    await sendQuestion(question, props.activeTab, currentTabLabel.value);
  } catch {
    // 错误态已经在共享 AI 状态中处理，这里不重复抛出提示。
  }
}

async function handleSummary() {
  if (loading.value) return;
  try {
    await generateSummary(props.activeTab, currentTabLabel.value);
  } catch {
    // 错误态已经在共享 AI 状态中处理，这里不重复抛出提示。
  }
}

watch(
  messageSignature,
  async () => {
    await nextTick();
    const el = messageListRef.value;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  },
);
</script>

<style lang="scss" scoped>
.ai-assistant {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 14px;
  pointer-events: none;
}

.ai-assistant__trigger,
.ai-assistant__panel,
.ai-assistant__close,
.ai-assistant__action,
.ai-assistant__send {
  pointer-events: auto;
}

.ai-assistant__trigger {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba($tech-cyan, 0.4);
  background: linear-gradient(135deg, rgba(7, 26, 47, 0.94), rgba(5, 12, 28, 0.92));
  color: rgba(235, 246, 255, 0.98);
  border-radius: 999px;
  padding: 12px 18px;
  font-size: 16px;
  font-family: $font-title;
  letter-spacing: 0.08em;
  box-shadow: $glow-shadow;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease;

  &:hover {
    transform: translateY(-1px);
    border-color: rgba($tech-cyan, 0.68);
  }
}

.ai-assistant__trigger-dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: radial-gradient(circle, $tech-cyan 0%, $tech-green 100%);
  box-shadow: 0 0 10px rgba($tech-cyan, 0.72);
}

.ai-assistant__panel {
  width: min(520px, calc(100vw - 60px));
  height: min(68vh, 740px);
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto auto;
  background: rgba(7, 15, 32, 0.96);
  border: 1px solid rgba($tech-cyan, 0.34);
  border-radius: 20px;
  backdrop-filter: blur(16px);
  box-shadow:
    0 20px 54px rgba(0, 0, 0, 0.46),
    inset 0 0 28px rgba($tech-cyan, 0.08);
  overflow: hidden;
}

.ai-assistant__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 18px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.ai-assistant__title {
  color: rgba($tech-cyan, 0.96);
  font-size: 23px;
  font-family: $font-title;
  letter-spacing: 0.08em;
}

.ai-assistant__subtitle {
  margin-top: 6px;
  color: rgba(220, 235, 255, 0.56);
  font-size: 16px;
}

.ai-assistant__close {
  border: none;
  background: transparent;
  color: rgba(220, 235, 255, 0.68);
  font-size: 32px;
  line-height: 1;
  cursor: pointer;
}

.ai-assistant__toolbar {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 14px 18px;
}

.ai-assistant__action {
  min-height: 50px;
  border: 1px solid rgba($tech-cyan, 0.22);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(235, 246, 255, 0.88);
  padding: 10px 16px;
  font-size: 17px;
  cursor: pointer;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.ai-assistant__action--primary {
  border-color: rgba($tech-cyan, 0.45);
  color: #fff;
  box-shadow: inset 0 0 14px rgba($tech-cyan, 0.08);
}

.ai-assistant__messages {
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 18px 16px;
  scrollbar-width: thin;
  scrollbar-color: rgba($tech-cyan, 0.62) rgba(255, 255, 255, 0.06);

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.06);
    border-radius: 999px;
  }

  &::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, rgba($tech-cyan, 0.76), rgba($tech-green, 0.48));
    border-radius: 999px;
    box-shadow: inset 0 0 8px rgba($tech-cyan, 0.18);
  }

  &::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, rgba($tech-cyan, 0.92), rgba($tech-green, 0.68));
  }
}

.ai-assistant__empty {
  margin-top: 18px;
  padding: 18px;
  border: 1px dashed rgba($tech-cyan, 0.24);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.02);
}

.ai-assistant__empty-title {
  color: rgba($tech-cyan, 0.92);
  font-size: 18px;
  margin-bottom: 10px;
}

.ai-assistant__empty-text {
  color: rgba(220, 235, 255, 0.6);
  font-size: 15px;
  line-height: 1.8;
}

.ai-assistant__message {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
}

.ai-assistant__message.is-user {
  border-color: rgba($tech-cyan, 0.18);
  background: rgba($tech-cyan, 0.08);
}

.ai-assistant__message.is-summary {
  border-color: rgba($tech-green, 0.22);
  box-shadow: inset 0 0 18px rgba($tech-green, 0.05);
}

.ai-assistant__message.is-error,
.ai-assistant__message.status-error {
  border-color: rgba($tech-orange, 0.3);
}

.ai-assistant__message-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.ai-assistant__meta-left {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ai-assistant__role-chip,
.ai-assistant__page-chip,
.ai-assistant__status-chip {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 13px;
}

.ai-assistant__role-chip {
  background: rgba($tech-cyan, 0.12);
  color: rgba($tech-cyan, 0.95);
}

.ai-assistant__page-chip {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(220, 235, 255, 0.72);
}

.ai-assistant__status-chip {
  background: rgba($tech-green, 0.08);
  color: rgba($tech-green, 0.92);
}

.ai-assistant__tool-list {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
}

.ai-assistant__tool-item {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba($tech-cyan, 0.12);
}

.ai-assistant__tool-item.is-running {
  border-color: rgba($tech-cyan, 0.28);
}

.ai-assistant__tool-item.is-success {
  border-color: rgba($tech-green, 0.24);
}

.ai-assistant__tool-item.is-error {
  border-color: rgba($tech-orange, 0.24);
}

.ai-assistant__tool-name {
  color: rgba($tech-cyan, 0.92);
  font-size: 14px;
}

.ai-assistant__tool-summary {
  color: rgba(220, 235, 255, 0.68);
  font-size: 14px;
  line-height: 1.6;
}

.ai-assistant__message-body {
  color: rgba(245, 248, 255, 0.97);
  font-size: 16px;
  line-height: 1.82;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.ai-assistant__message-body--plain {
  white-space: pre-wrap;
}

.ai-assistant__message-body--markdown {
  :deep(p),
  :deep(ul),
  :deep(ol),
  :deep(blockquote),
  :deep(pre) {
    margin: 0 0 12px;
  }

  :deep(p:last-child),
  :deep(ul:last-child),
  :deep(ol:last-child),
  :deep(blockquote:last-child),
  :deep(pre:last-child) {
    margin-bottom: 0;
  }

  :deep(h1),
  :deep(h2),
  :deep(h3),
  :deep(h4) {
    margin: 0 0 12px;
    color: rgba($tech-cyan, 0.96);
    font-family: $font-title;
    letter-spacing: 0.04em;
  }

  :deep(ul),
  :deep(ol) {
    padding-left: 20px;
  }

  :deep(li) {
    margin-bottom: 6px;
  }

  :deep(strong) {
    color: rgba($tech-green, 0.98);
    font-weight: 600;
  }

  :deep(code) {
    padding: 2px 6px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.08);
    font-size: 14px;
  }

  :deep(pre) {
    padding: 12px;
    border-radius: 12px;
    background: rgba(0, 0, 0, 0.3);
    overflow-x: auto;
    scrollbar-width: thin;
    scrollbar-color: rgba($tech-cyan, 0.62) rgba(255, 255, 255, 0.06);
  }

  :deep(pre::-webkit-scrollbar) {
    height: 6px;
  }

  :deep(pre::-webkit-scrollbar-track) {
    background: rgba(255, 255, 255, 0.06);
    border-radius: 999px;
  }

  :deep(pre::-webkit-scrollbar-thumb) {
    background: linear-gradient(90deg, rgba($tech-cyan, 0.76), rgba($tech-green, 0.48));
    border-radius: 999px;
  }

  :deep(pre::-webkit-scrollbar-thumb:hover) {
    background: linear-gradient(90deg, rgba($tech-cyan, 0.92), rgba($tech-green, 0.68));
  }

  :deep(pre code) {
    padding: 0;
    background: transparent;
  }
}

.ai-assistant__error {
  margin: 0 18px 14px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba($tech-orange, 0.08);
  border: 1px solid rgba($tech-orange, 0.22);
  color: #ffd7a2;
  font-size: 15px;
}

.ai-assistant__composer {
  padding: 14px 18px 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.ai-assistant__textarea {
  width: 100%;
  min-height: 112px;
  resize: none;
  overflow-y: auto;
  border-radius: 14px;
  border: 1px solid rgba($tech-cyan, 0.22);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(245, 248, 255, 0.97);
  padding: 14px 16px;
  font-size: 16px;
  line-height: 1.7;
  outline: none;
  scrollbar-width: thin;
  scrollbar-color: rgba($tech-cyan, 0.62) rgba(255, 255, 255, 0.06);

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.06);
    border-radius: 999px;
  }

  &::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, rgba($tech-cyan, 0.76), rgba($tech-green, 0.48));
    border-radius: 999px;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, rgba($tech-cyan, 0.92), rgba($tech-green, 0.68));
  }

  &:focus {
    border-color: rgba($tech-cyan, 0.45);
    box-shadow: inset 0 0 0 1px rgba($tech-cyan, 0.12);
  }

  &::placeholder {
    color: rgba(220, 235, 255, 0.34);
  }
}

.ai-assistant__composer-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
}

.ai-assistant__hint {
  color: rgba(220, 235, 255, 0.44);
  font-size: 13px;
}

.ai-assistant__send {
  min-width: 108px;
  min-height: 48px;
  border: 1px solid rgba($tech-cyan, 0.5);
  border-radius: 12px;
  background: linear-gradient(135deg, rgba($tech-cyan, 0.24), rgba($tech-green, 0.16));
  color: #fff;
  padding: 10px 18px;
  font-size: 16px;
  cursor: pointer;

  &:disabled {
    opacity: 0.46;
    cursor: not-allowed;
  }
}

.ai-panel-fade-enter-active,
.ai-panel-fade-leave-active {
  transition: all 0.24s ease;
}

.ai-panel-fade-enter-from,
.ai-panel-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.985);
}
</style>
