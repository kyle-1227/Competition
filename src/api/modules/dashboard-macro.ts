import http from '@/api/http';

export const getMacroDataApi = (province?: string, signal?: AbortSignal) => {
  return http.get<unknown>(
    'api/macro/data',
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
