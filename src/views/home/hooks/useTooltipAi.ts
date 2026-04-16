import { postAiTooltip, type AiTooltipRequest } from '@/api/modules/ai';

export const TOOLTIP_AI_LOADING_TEXT = 'AI 分析生成中...';
export const TOOLTIP_AI_ERROR_TEXT = 'AI 分析加载失败';

const TOOLTIP_AI_SUCCESS_TTL_MS = 5 * 60 * 1000;
const TOOLTIP_AI_ERROR_TTL_MS = 30 * 1000;
const TOOLTIP_AI_DEBOUNCE_MS = 160;

interface TooltipAiCacheEntry {
  content: string;
  ok: boolean;
  expiresAt: number;
}

interface ScheduledTooltipRequest {
  timer: ReturnType<typeof setTimeout>;
  promise: Promise<string>;
}

export interface TooltipAiSnapshot {
  cacheKey: string;
  domId: string;
  content: string;
  loading: boolean;
}

const resultCache = new Map<string, TooltipAiCacheEntry>();
const pendingRequests = new Map<string, Promise<string>>();
const loadingMap = new Map<string, boolean>();
const scheduledRequests = new Map<string, ScheduledTooltipRequest>();

function stableSerialize(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'number' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'string') return JSON.stringify(value);
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableSerialize(item)).join(',')}]`;
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([, entryValue]) => entryValue !== undefined)
      .sort(([left], [right]) => left.localeCompare(right, 'en'));
    return `{${entries.map(([key, entryValue]) => `${JSON.stringify(key)}:${stableSerialize(entryValue)}`).join(',')}}`;
  }
  return JSON.stringify(String(value));
}

function hashString(input: string): string {
  let hash = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(36);
}

function escapeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function getValidCacheEntry(cacheKey: string): TooltipAiCacheEntry | null {
  const entry = resultCache.get(cacheKey);
  if (!entry) return null;
  if (entry.expiresAt <= Date.now()) {
    resultCache.delete(cacheKey);
    return null;
  }
  return entry;
}

function setCacheEntry(cacheKey: string, content: string, ok: boolean) {
  resultCache.set(cacheKey, {
    content,
    ok,
    expiresAt: Date.now() + (ok ? TOOLTIP_AI_SUCCESS_TTL_MS : TOOLTIP_AI_ERROR_TTL_MS),
  });
}

function updateTooltipAiDom(domId: string | undefined, text: string) {
  if (!domId || typeof document === 'undefined') return;
  const el = document.getElementById(domId);
  if (!el) return;
  el.textContent = text;
}

async function executeTooltipAiRequest(payload: AiTooltipRequest, cacheKey: string): Promise<string> {
  try {
    const response = await postAiTooltip(payload);
    const content = String(response?.data?.content || '').trim();
    if (!content) {
      throw new Error('AI tooltip returned empty content');
    }
    setCacheEntry(cacheKey, content, true);
    return content;
  } catch {
    setCacheEntry(cacheKey, TOOLTIP_AI_ERROR_TEXT, false);
    return TOOLTIP_AI_ERROR_TEXT;
  } finally {
    pendingRequests.delete(cacheKey);
    loadingMap.delete(cacheKey);
  }
}

function attachDomUpdate(promise: Promise<string>, domId?: string): Promise<string> {
  if (!domId) return promise;
  promise.then((content) => {
    updateTooltipAiDom(domId, content);
  });
  return promise;
}

// Cache key 额外包含 tooltipScope 和稳定序列化后的 dataPayload，避免不同 tooltip 串文案。
export function buildTooltipAiCacheKey(payload: AiTooltipRequest): string {
  return [
    'tooltip',
    payload.moduleName,
    payload.tooltipScope,
    payload.regionName,
    payload.year ?? 'na',
    stableSerialize(payload.dataPayload),
  ].join('::');
}

export function buildTooltipAiDomId(cacheKey: string): string {
  return `tooltip-ai-${hashString(cacheKey)}`;
}

export function getTooltipAiSnapshot(payload: AiTooltipRequest): TooltipAiSnapshot {
  const cacheKey = buildTooltipAiCacheKey(payload);
  const domId = buildTooltipAiDomId(cacheKey);
  const cached = getValidCacheEntry(cacheKey);
  const loading = loadingMap.get(cacheKey) === true || pendingRequests.has(cacheKey) || scheduledRequests.has(cacheKey);
  const content = cached?.content || (loading ? TOOLTIP_AI_LOADING_TEXT : TOOLTIP_AI_ERROR_TEXT);
  return { cacheKey, domId, content, loading };
}

export function requestTooltipAi(payload: AiTooltipRequest, domId?: string): Promise<string> {
  const cacheKey = buildTooltipAiCacheKey(payload);
  const cached = getValidCacheEntry(cacheKey);
  if (cached) {
    updateTooltipAiDom(domId, cached.content);
    return Promise.resolve(cached.content);
  }

  const scheduled = scheduledRequests.get(cacheKey);
  if (scheduled) {
    loadingMap.set(cacheKey, true);
    return attachDomUpdate(scheduled.promise, domId);
  }

  const pending = pendingRequests.get(cacheKey);
  if (pending) {
    loadingMap.set(cacheKey, true);
    return attachDomUpdate(pending, domId);
  }

  loadingMap.set(cacheKey, true);
  let timer: ReturnType<typeof setTimeout>;
  const promise = new Promise<string>((resolve) => {
    timer = setTimeout(() => {
      scheduledRequests.delete(cacheKey);
      const actualPromise = executeTooltipAiRequest(payload, cacheKey);
      pendingRequests.set(cacheKey, actualPromise);
      actualPromise.then(resolve);
    }, TOOLTIP_AI_DEBOUNCE_MS);
  });
  scheduledRequests.set(cacheKey, { timer: timer!, promise });
  return attachDomUpdate(promise, domId);
}

export function renderTooltipAiHtml(snapshot: TooltipAiSnapshot, title = 'AI 分析'): string {
  return `
    <div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.12)">
      <div style="margin-bottom:4px;color:rgba(0,229,255,0.85);font-size:12px;font-weight:600">${escapeHtml(title)}</div>
      <div id="${snapshot.domId}" style="color:rgba(230,240,255,0.9);font-size:12px;line-height:1.55;">
        ${escapeHtml(snapshot.content)}
      </div>
    </div>
  `;
}

