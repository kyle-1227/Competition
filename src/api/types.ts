/** 与 FastAPI 大屏接口统一的业务响应壳 */
export interface ApiEnvelope<T = unknown> {
  code: number;
  msg: string;
  data: T;
}
