import http from '@/api/http';
import type { ApiEnvelope } from '@/api/types';

export type AiPageKey = 'greenFinance' | 'carbon' | 'energy';
export type AiHistoryRole = 'user' | 'assistant';
export type AiResultKind = 'chat' | 'summary';
export type AiStreamEventType = 'start' | 'tool_start' | 'tool_result' | 'delta' | 'done' | 'error';
export type AiTooltipResultKind = 'tooltip';

export interface AiHistoryMessage {
  role: AiHistoryRole;
  content: string;
}

export interface AiPageContext {
  page: AiPageKey;
  pageTitle: string;
  year?: number | null;
  selectedProvince?: string;
  drillProvince?: string;
  drillCity?: string;
  snapshot: Record<string, unknown>;
}

export interface AiChatRequest {
  question: string;
  pageContext: AiPageContext;
  history: AiHistoryMessage[];
}

export interface AiSummaryRequest {
  pageContext: AiPageContext;
  history: AiHistoryMessage[];
}

export interface AiTooltipRequest {
  regionName: string;
  year?: number | null;
  moduleName: string;
  tooltipScope: string;
  dataPayload: Record<string, unknown>;
}

export interface AiResultData {
  content: string;
  model: string;
  kind: AiResultKind;
}

export interface AiTooltipResultData {
  content: string;
  model: string;
  kind: AiTooltipResultKind;
}

export interface AiStreamStartPayload {
  kind: AiResultKind;
  page: AiPageKey;
  pageTitle: string;
}

export interface AiStreamToolStartPayload {
  name: string;
  message: string;
}

export interface AiStreamToolResultPayload {
  name: string;
  summary: string;
  ok: boolean;
}

export interface AiStreamDeltaPayload {
  content: string;
  model?: string | null;
}

export interface AiStreamDonePayload {
  kind: AiResultKind;
  model?: string | null;
}

export interface AiStreamErrorPayload {
  message: string;
}

export interface AiStreamHandlers {
  onStart?: (payload: AiStreamStartPayload) => void;
  onToolStart?: (payload: AiStreamToolStartPayload) => void;
  onToolResult?: (payload: AiStreamToolResultPayload) => void;
  onDelta?: (payload: AiStreamDeltaPayload) => void;
  onDone?: (payload: AiStreamDonePayload) => void;
  onError?: (payload: AiStreamErrorPayload) => void;
  onEvent?: (event: AiStreamEventType, payload: unknown) => void;
}

export const postAiChat = (payload: AiChatRequest) =>
  http.post<ApiEnvelope<AiResultData | null>>('api/ai/chat', payload);

export const postAiSummary = (payload: AiSummaryRequest) =>
  http.post<ApiEnvelope<AiResultData | null>>('api/ai/summary', payload);

export const postAiTooltip = (payload: AiTooltipRequest) =>
  http.post<ApiEnvelope<AiTooltipResultData | null>>('api/ai/tooltip', payload);

function resolveApiUrl(path: string) {
  return new URL(path, `${window.location.origin}${import.meta.env.BASE_URL}`).toString();
}

function dispatchAiStreamEvent(event: AiStreamEventType, payload: unknown, handlers: AiStreamHandlers) {
  handlers.onEvent?.(event, payload);

  switch (event) {
    case 'start':
      handlers.onStart?.(payload as AiStreamStartPayload);
      break;
    case 'tool_start':
      handlers.onToolStart?.(payload as AiStreamToolStartPayload);
      break;
    case 'tool_result':
      handlers.onToolResult?.(payload as AiStreamToolResultPayload);
      break;
    case 'delta':
      handlers.onDelta?.(payload as AiStreamDeltaPayload);
      break;
    case 'done':
      handlers.onDone?.(payload as AiStreamDonePayload);
      break;
    case 'error':
      handlers.onError?.(payload as AiStreamErrorPayload);
      break;
    default:
      break;
  }
}

async function consumeSseStream(response: Response, handlers: AiStreamHandlers) {
  if (!response.body) {
    throw new Error('AI 流式响应体为空');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let streamError: Error | null = null;

  const parseBlock = (block: string) => {
    const lines = block.split('\n');
    let event = 'message';
    const dataLines: string[] = [];

    lines.forEach((line) => {
      if (line.startsWith('event:')) {
        event = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim());
      }
    });

    if (!dataLines.length) return;

    const dataText = dataLines.join('\n');
    let payload: unknown = dataText;
    try {
      payload = JSON.parse(dataText);
    } catch {
      payload = dataText;
    }

    const typedEvent = event as AiStreamEventType;
    dispatchAiStreamEvent(typedEvent, payload, handlers);

    if (typedEvent === 'error') {
      const message = typeof payload === 'object' && payload && 'message' in payload
        ? String((payload as AiStreamErrorPayload).message || 'AI 流式请求失败')
        : 'AI 流式请求失败';
      streamError = new Error(message);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done }).replace(/\r\n/g, '\n');

    let separatorIndex = buffer.indexOf('\n\n');
    while (separatorIndex !== -1) {
      const block = buffer.slice(0, separatorIndex).trim();
      buffer = buffer.slice(separatorIndex + 2);
      if (block) parseBlock(block);
      separatorIndex = buffer.indexOf('\n\n');
    }

    if (done) {
      const tail = buffer.trim();
      if (tail) parseBlock(tail);
      break;
    }
  }

  if (streamError) {
    throw streamError;
  }
}

async function postAiStream(path: string, payload: AiChatRequest | AiSummaryRequest, handlers: AiStreamHandlers = {}) {
  const response = await fetch(resolveApiUrl(path), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `AI 流式请求失败(${response.status})`);
  }

  await consumeSseStream(response, handlers);
}

export const postAiChatStream = (payload: AiChatRequest, handlers?: AiStreamHandlers) =>
  postAiStream('api/ai/chat/stream', payload, handlers);

export const postAiSummaryStream = (payload: AiSummaryRequest, handlers?: AiStreamHandlers) =>
  postAiStream('api/ai/summary/stream', payload, handlers);
