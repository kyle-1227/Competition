import http from '@/api/http';

export interface MacroDataQuery {
  province?: string;
  city?: string;
}

export interface MacroCityOption {
  province: string;
  city: string;
}

function normalizeMacroQuery(query?: string | MacroDataQuery) {
  if (!query) return {};
  const raw = typeof query === 'string' ? { province: query } : query;
  return Object.fromEntries(
    Object.entries(raw).filter(([, value]) => value !== undefined && value !== ''),
  );
}

export const getMacroDataApi = (query?: string | MacroDataQuery, signal?: AbortSignal) => {
  return http.get<unknown>(
    'api/macro/data',
    normalizeMacroQuery(query),
    signal ? { signal } : undefined,
  );
};

export const getMacroCityOptionsApi = (province?: string, signal?: AbortSignal) => {
  return http.get<{ code: number; msg: string; data: MacroCityOption[] | null }>(
    'api/macro/cities',
    province ? { province } : {},
    signal ? { signal } : undefined,
  );
};

export const getMacroStatsData = (signal?: AbortSignal) => {
  return http.get<{ code: number; msg: string; data: Record<string, unknown>[] | null }>(
    'api/dashboard/macro-stats',
    undefined,
    signal ? { signal } : undefined,
  );
};
