import { computed, ref } from 'vue';
import {
  postAiChat,
  postAiChatStream,
  postAiSummary,
  postAiSummaryStream,
  type AiAudienceRole,
  type AiChatRequest,
  type AiHistoryMessage,
  type AiPageContext,
  type AiPageKey,
  type AiResultKind,
} from '@/api/modules/ai';

export type AiMessageStatus = 'pending' | 'tooling' | 'streaming' | 'done' | 'error';

export interface AiToolTrace {
  id: string;
  name: string;
  summary: string;
  ok: boolean | null;
}

export interface AiAssistantMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  kind: 'chat' | 'summary' | 'error';
  page: AiPageKey;
  pageTitle: string;
  createdAt: number;
  status: AiMessageStatus;
  phaseText?: string;
  toolTraces: AiToolTrace[];
}

type PageSnapshotGetter = () => Omit<AiPageContext, 'page' | 'pageTitle'> | null;

const panelOpen = ref(false);
const requestMode = ref<AiResultKind | null>(null);
const messages = ref<AiAssistantMessage[]>([]);
const errorText = ref('');
const pageSnapshotGetters = new Map<AiPageKey, PageSnapshotGetter>();

let messageSeed = 0;

function nextMessageId() {
  messageSeed += 1;
  return `ai-msg-${Date.now()}-${messageSeed}`;
}

function pushMessage(message: Omit<AiAssistantMessage, 'id' | 'createdAt'>) {
  const nextMessage: AiAssistantMessage = {
    ...message,
    id: nextMessageId(),
    createdAt: Date.now(),
  };
  messages.value.push(nextMessage);
  return nextMessage;
}

function updateMessage(id: string, patch: Partial<AiAssistantMessage>) {
  const target = messages.value.find((item) => item.id === id);
  if (!target) return;
  Object.assign(target, patch);
}

function appendMessageContent(id: string, delta: string) {
  const target = messages.value.find((item) => item.id === id);
  if (!target) return;
  target.content += delta;
}

function appendToolTrace(id: string, trace: AiToolTrace) {
  const target = messages.value.find((item) => item.id === id);
  if (!target) return;
  const existing = target.toolTraces.find((item) => item.name === trace.name && item.summary === trace.summary);
  if (!existing) {
    target.toolTraces.push(trace);
  }
}

function markLastToolTrace(id: string, toolName: string, summary: string, ok: boolean) {
  const target = messages.value.find((item) => item.id === id);
  if (!target) return;

  const trace = target.toolTraces.find((item) => item.name === toolName && item.ok === null);
  if (trace) {
    trace.summary = summary;
    trace.ok = ok;
    return;
  }

  target.toolTraces.push({
    id: `${toolName}-${Date.now()}`,
    name: toolName,
    summary,
    ok,
  });
}

function trimHistoryForApi(items: AiAssistantMessage[]): AiHistoryMessage[] {
  return items
    .filter((item) => item.role === 'user' || (item.role === 'assistant' && item.content.trim()))
    .filter((item) => item.kind !== 'error')
    .slice(-12)
    .map((item) => ({
      role: item.role,
      content: item.content,
    }));
}

function buildPageContext(page: AiPageKey, pageTitle: string): AiPageContext {
  const getter = pageSnapshotGetters.get(page);
  const extra = getter?.() ?? null;

  return {
    page,
    pageTitle,
    year: extra?.year ?? null,
    selectedProvince: extra?.selectedProvince,
    drillProvince: extra?.drillProvince,
    drillCity: extra?.drillCity,
    snapshot: extra?.snapshot ?? {},
  };
}

async function fallbackToNonStream(
  payload: AiChatRequest,
  page: AiPageKey,
  pageTitle: string,
  kind: AiResultKind,
  messageId: string,
) {
  const response = kind === 'chat'
    ? await postAiChat(payload)
    : await postAiSummary({
      audienceRole: payload.audienceRole,
      pageContext: payload.pageContext,
      history: payload.history,
    });

  const content = response.data?.content?.trim();
  if (!content) {
    throw new Error('AI 未返回可用内容');
  }

  updateMessage(messageId, {
    role: 'assistant',
    kind,
    page,
    pageTitle,
    content,
    status: 'done',
    phaseText: '',
  });
  errorText.value = '';
  return content;
}

async function runStreamRequest(
  kind: AiResultKind,
  payload: AiChatRequest,
  page: AiPageKey,
  pageTitle: string,
  messageId: string,
) {
  let receivedContent = false;

  const handlers = {
    onStart: () => {
      updateMessage(messageId, {
        status: 'pending',
        phaseText: kind === 'summary' ? '正在整理当前页总结…' : '正在思考你的问题…',
      });
    },
    onToolStart: (event: { name: string; message: string }) => {
      updateMessage(messageId, {
        status: 'tooling',
        phaseText: event.message,
      });
      appendToolTrace(messageId, {
        id: `${event.name}-${Date.now()}`,
        name: event.name,
        summary: event.message,
        ok: null,
      });
    },
    onToolResult: (event: { name: string; summary: string; ok: boolean }) => {
      markLastToolTrace(messageId, event.name, event.summary, event.ok);
      updateMessage(messageId, {
        status: 'tooling',
        phaseText: '数据查询完成，正在组织回答…',
      });
    },
    onDelta: (event: { content: string }) => {
      receivedContent = true;
      appendMessageContent(messageId, event.content);
      updateMessage(messageId, {
        status: 'streaming',
        phaseText: '',
      });
      errorText.value = '';
    },
    onDone: () => {
      updateMessage(messageId, {
        status: 'done',
        phaseText: '',
      });
      errorText.value = '';
    },
  };

  try {
    if (kind === 'chat') {
      await postAiChatStream(payload, handlers);
    } else {
      await postAiSummaryStream({
        audienceRole: payload.audienceRole,
        pageContext: payload.pageContext,
        history: payload.history,
      }, handlers);
    }

    const finalMessage = messages.value.find((item) => item.id === messageId);
    return finalMessage?.content ?? '';
  } catch (error) {
    if (!receivedContent) {
      return fallbackToNonStream(payload, page, pageTitle, kind, messageId);
    }

    const message = error instanceof Error ? error.message : 'AI 流式请求失败，请稍后重试';
    updateMessage(messageId, {
      status: 'error',
      phaseText: '',
      kind: finalMessageKind(kind),
      content: `${messages.value.find((item) => item.id === messageId)?.content || ''}\n\n（回答中断：${message}）`,
    });
    errorText.value = message;
    throw error;
  }
}

function finalMessageKind(kind: AiResultKind): 'chat' | 'summary' {
  return kind === 'summary' ? 'summary' : 'chat';
}

export function useAiAssistant() {
  const loading = computed(() => requestMode.value !== null);
  const canAsk = computed(() => !loading.value);

  function registerPageContext(page: AiPageKey, getter: PageSnapshotGetter) {
    pageSnapshotGetters.set(page, getter);
    return () => {
      const current = pageSnapshotGetters.get(page);
      if (current === getter) {
        pageSnapshotGetters.delete(page);
      }
    };
  }

  async function sendQuestion(question: string, page: AiPageKey, pageTitle: string, audienceRole: AiAudienceRole) {
    const content = question.trim();
    if (!content || loading.value) return null;

    panelOpen.value = true;
    errorText.value = '';
    const history = trimHistoryForApi(messages.value);
    const pageContext = buildPageContext(page, pageTitle);

    pushMessage({
      role: 'user',
      content,
      kind: 'chat',
      page,
      pageTitle,
      status: 'done',
      phaseText: '',
      toolTraces: [],
    });

    const placeholder = pushMessage({
      role: 'assistant',
      content: '',
      kind: 'chat',
      page,
      pageTitle,
      status: 'pending',
      phaseText: '正在思考你的问题…',
      toolTraces: [],
    });

    requestMode.value = 'chat';
    try {
      return await runStreamRequest(
        'chat',
        {
          question: content,
          audienceRole,
          pageContext,
          history,
        },
        page,
        pageTitle,
        placeholder.id,
      );
    } finally {
      requestMode.value = null;
    }
  }

  async function generateSummary(page: AiPageKey, pageTitle: string, audienceRole: AiAudienceRole) {
    if (loading.value) return null;

    panelOpen.value = true;
    errorText.value = '';
    const pageContext = buildPageContext(page, pageTitle);
    const history = trimHistoryForApi(messages.value);

    const placeholder = pushMessage({
      role: 'assistant',
      content: '',
      kind: 'summary',
      page,
      pageTitle,
      status: 'pending',
      phaseText: '正在整理当前页总结…',
      toolTraces: [],
    });

    requestMode.value = 'summary';
    try {
      return await runStreamRequest(
        'summary',
        {
          question: '请总结当前页面',
          audienceRole,
          pageContext,
          history,
        },
        page,
        pageTitle,
        placeholder.id,
      );
    } finally {
      requestMode.value = null;
    }
  }

  function clearMessages() {
    messages.value = [];
    errorText.value = '';
  }

  function togglePanel(force?: boolean) {
    panelOpen.value = typeof force === 'boolean' ? force : !panelOpen.value;
  }

  return {
    panelOpen,
    loading,
    requestMode,
    messages,
    errorText,
    canAsk,
    registerPageContext,
    sendQuestion,
    generateSummary,
    clearMessages,
    togglePanel,
  };
}
