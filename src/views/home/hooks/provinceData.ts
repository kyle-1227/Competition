/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
import axios from 'axios';
import { ref, type Ref } from 'vue';
import { getProvinceDataApi, getCityDataApi } from '@/api/modules/dashboard';

export interface ProvinceGreenFinance {
  province: string;
  score: number;
  greenCredit: number;
  greenInvest: number;
  greenInsurance: number;
  greenBond: number;
  greenExpend: number;
  greenFund: number;
  greenEquity: number;
  /** 库表 province_green_finance.carbonEmission（原始量纲，前端碳模块除以 1e4 作万吨展示） */
  carbonEmission?: number;
  /** 亿元 */
  gdp?: number;
}

/** 按年省级结果短缓存，来回切年份时免重复请求 */
const provinceCache = new Map<number, ProvinceGreenFinance[]>();
const PROVINCE_CACHE_MAX = 10;

/** 地级市缓存 key：省全称|年 */
const cityCache = new Map<string, ProvinceGreenFinance[]>();
const CITY_CACHE_MAX = 16;

let provinceFetchGen = 0;
let provinceAbort: AbortController | null = null;

let cityFetchGen = 0;
let cityAbort: AbortController | null = null;

function trimMap<K>(m: Map<K, unknown>, max: number) {
  while (m.size >= max) {
    const k = m.keys().next().value as K;
    m.delete(k);
  }
}

function cityCacheKey(province: string, year: number) {
  return `${province}|${year}`;
}

export const indicatorLabels: Record<string, string> = {
  greenCredit: '绿色信贷',
  greenInvest: '绿色投资',
  greenInsurance: '绿色保险',
  greenBond: '绿色债券',
  greenExpend: '绿色支出',
  greenFund: '绿色基金',
  greenEquity: '绿色权益',
};

export const indicatorKeys = Object.keys(indicatorLabels) as (keyof Omit<ProvinceGreenFinance, 'province' | 'score'>)[];

// ======================================================================
// 原「按年多省静态死数据」已移除（联调时仅看接口数据；恢复请从 git 历史还原 yearlyData）。
// ======================================================================
export const yearlyData: Record<number, ProvinceGreenFinance[]> = {};

export const provinceNameMap: Record<string, string> = {
  上海: '上海市',
  云南: '云南省',
  内蒙古: '内蒙古自治区',
  北京: '北京市',
  吉林: '吉林省',
  四川: '四川省',
  天津: '天津市',
  宁夏: '宁夏回族自治区',
  安徽: '安徽省',
  山东: '山东省',
  山西: '山西省',
  广东: '广东省',
  广西: '广西壮族自治区',
  新疆: '新疆维吾尔自治区',
  江苏: '江苏省',
  江西: '江西省',
  河北: '河北省',
  河南: '河南省',
  浙江: '浙江省',
  海南: '海南省',
  湖北: '湖北省',
  湖南: '湖南省',
  甘肃: '甘肃省',
  福建: '福建省',
  西藏: '西藏自治区',
  贵州: '贵州省',
  辽宁: '辽宁省',
  重庆: '重庆市',
  陕西: '陕西省',
  青海: '青海省',
  黑龙江: '黑龙江省',
};

export const provinceCoords: Record<string, [number, number]> = {
  上海市: [121.473, 31.23],
  北京市: [116.407, 39.904],
  天津市: [117.19, 39.126],
  重庆市: [106.552, 29.563],
  广东省: [113.264, 23.129],
  浙江省: [120.154, 30.287],
  江苏省: [118.797, 32.06],
  山东省: [117.001, 36.676],
  福建省: [119.306, 26.075],
  四川省: [104.066, 30.659],
  湖北省: [114.299, 30.584],
  湖南省: [112.982, 28.194],
  安徽省: [117.283, 31.861],
  江西省: [115.892, 28.676],
  河北省: [114.502, 38.045],
  河南省: [113.665, 34.758],
  陕西省: [108.948, 34.263],
  山西省: [112.549, 37.857],
  辽宁省: [123.429, 41.796],
  吉林省: [125.324, 43.886],
  黑龙江省: [126.642, 45.756],
  云南省: [102.712, 25.04],
  贵州省: [106.713, 26.578],
  甘肃省: [103.823, 36.058],
  内蒙古自治区: [111.678, 40.854],
  新疆维吾尔自治区: [87.617, 43.792],
  广西壮族自治区: [108.32, 22.825],
  宁夏回族自治区: [106.278, 38.466],
  西藏自治区: [91.118, 29.646],
  青海省: [101.778, 36.623],
  海南省: [110.329, 20.036],
};

export const fullToShortName: Record<string, string> = Object.fromEntries(
  Object.entries(provinceNameMap).map(([short, full]) => [full, short]),
);

/** 省级全称 → 6 位 adcode（备查；本地 GeoJSON 现按「省全称.geojson」加载） */
export const provinceAdcodeMap: Record<string, string> = {
  北京市: '110000',
  天津市: '120000',
  河北省: '130000',
  山西省: '140000',
  内蒙古自治区: '150000',
  辽宁省: '210000',
  吉林省: '220000',
  黑龙江省: '230000',
  上海市: '310000',
  江苏省: '320000',
  浙江省: '330000',
  安徽省: '340000',
  福建省: '350000',
  江西省: '360000',
  山东省: '370000',
  河南省: '410000',
  湖北省: '420000',
  湖南省: '430000',
  广东省: '440000',
  广西壮族自治区: '450000',
  海南省: '460000',
  重庆市: '500000',
  四川省: '510000',
  贵州省: '520000',
  云南省: '530000',
  西藏自治区: '540000',
  陕西省: '610000',
  甘肃省: '620000',
  青海省: '630000',
  宁夏回族自治区: '640000',
  新疆维吾尔自治区: '650000',
};

/** 按 public/geojson/下的「省级全称.geojson」加载，如 广东省.geojson */
export async function fetchGeoJson(provinceFullName: string): Promise<{ type: string; features: unknown[] }> {
  const base = import.meta.env.BASE_URL || '/';
  const file = `${encodeURIComponent(provinceFullName)}.geojson`;
  const path = `${base}geojson/${file}`.replace(/\/{2,}/g, '/');
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`GeoJSON 请求失败 ${provinceFullName}: ${res.status}`);
  }
  const json = (await res.json()) as { type: string; features?: unknown[] };
  if (json.type === 'FeatureCollection' && Array.isArray(json.features)) {
    return { type: 'FeatureCollection', features: json.features };
  }
  if (json.type === 'Feature') {
    return { type: 'FeatureCollection', features: [json] };
  }
  throw new Error(`无效的 GeoJSON: ${provinceFullName}`);
}

/** 地图柱体配色（沙盘与绿色金融监测共用） */
export function scoreToColor(score: number): string {
  if (score > 0.7) return '#00e5ff';
  if (score > 0.5) return '#2979ff';
  if (score > 0.3) return '#7c4dff';
  if (score > 0.15) return '#ff6d00';
  return '#ff1744';
}

/** 绿色金融监测：地图下钻中的省级全称，空表示全国视角 */
export const gfDrillProvince: Ref<string> = ref('');

export const selectedProvince: Ref<string> = ref('');
export const selectedYear: Ref<number> = ref(2024);
/** 底部时间轴滑块当前值（与角标一致）；松手 commit 后才会与接口数据年 selectedYear 对齐拉数 */
export const timelineYear: Ref<number> = ref(2024);
export const tfeeThreshold: Ref<number> = ref(0.3);

/** 最近一次成功拉取省级数据的年份（与 realProvinceData 对应） */
export const apiProvinceYear = ref<number | null>(null);
export const realProvinceData = ref<ProvinceGreenFinance[]>([]);
/** 当前选中省份下的地级市数据（由 fetchCityData 填充） */
export const realCityData = ref<ProvinceGreenFinance[]>([]);

function toNum(v: unknown, fallback = 0): number {
  const n = typeof v === 'number' ? v : parseFloat(String(v ?? ''));
  return Number.isFinite(n) ? n : fallback;
}

/** 将后端单条记录转为前端 ProvinceGreenFinance（兼容 snake_case / camelCase） */
export function normalizeProvinceRecord(row: Record<string, unknown>): ProvinceGreenFinance {
  const province = String(row.province ?? row.name ?? row.city ?? row.city_name ?? '');
  return {
    province,
    score: toNum(row.score ?? row.total_score),
    greenCredit: toNum(row.greenCredit ?? row.green_credit),
    greenInvest: toNum(row.greenInvest ?? row.green_invest),
    greenInsurance: toNum(row.greenInsurance ?? row.green_insurance),
    greenBond: toNum(row.greenBond ?? row.green_bond),
    greenExpend: toNum(row.greenExpend ?? row.green_expend ?? row.greenSupport ?? row.green_support),
    greenFund: toNum(row.greenFund ?? row.green_fund),
    greenEquity: toNum(row.greenEquity ?? row.green_equity),
    carbonEmission: toNum(row.carbonEmission ?? row.carbon_emission),
    gdp: toNum(row.gdp ?? row.GDP),
  };
}

function extractList(res: unknown): unknown[] {
  if (Array.isArray(res)) return res;
  if (res && typeof res === 'object' && res !== null) {
    const o = res as Record<string, unknown>;
    if (Array.isArray(o.data)) return o.data;
    if (Array.isArray(o.list)) return o.list;
    if (Array.isArray(o.records)) return o.records;
  }
  return [];
}

/** 某年用于展示的省级列表：仅接口数据（本地 yearlyData 已清空，便于联调对比） */
export function getProvinceRows(year: number): ProvinceGreenFinance[] {
  if (apiProvinceYear.value === year && realProvinceData.value.length > 0) {
    return realProvinceData.value;
  }
  return [];
}

export function findProvince(name: string, year = 2024): ProvinceGreenFinance | undefined {
  const list = getProvinceRows(year);
  const fullName = provinceNameMap[name] || name;
  return list.find((p) => p.province === fullName || p.province.startsWith(name));
}

export const fetchProvinceData = async (year: number) => {
  const hit = provinceCache.get(year);
  if (hit) {
    realProvinceData.value = hit;
    apiProvinceYear.value = year;
    return;
  }

  provinceAbort?.abort();
  provinceAbort = new AbortController();
  const signal = provinceAbort.signal;
  const myGen = ++provinceFetchGen;

  try {
    const res: unknown = await getProvinceDataApi(year, signal);
    if (myGen !== provinceFetchGen) return;
    const raw = extractList(res);
    const rows = raw.map((r) => normalizeProvinceRecord((r as Record<string, unknown>) ?? {}));
    realProvinceData.value = rows;
    apiProvinceYear.value = year;
    if (!provinceCache.has(year)) trimMap(provinceCache, PROVINCE_CACHE_MAX);
    provinceCache.set(year, rows);
    console.log(`✅ 成功拉取 ${year} 年省级数据 ${rows.length} 条`);
  } catch (error) {
    if (signal.aborted || axios.isCancel(error)) return;
    if (myGen !== provinceFetchGen) return;
    console.error(`❌ 拉取 ${year} 年省级数据失败:`, error);
    apiProvinceYear.value = null;
  }
};

/** 拉取某省下辖地级市绿色金融数据（province 须为全称如「广东省」） */
export const fetchCityData = async (province: string, year: number) => {
  if (!province) {
    realCityData.value = [];
    return;
  }

  const ck = cityCacheKey(province, year);
  const hit = cityCache.get(ck);
  if (hit) {
    realCityData.value = hit;
    return;
  }

  cityAbort?.abort();
  cityAbort = new AbortController();
  const signal = cityAbort.signal;
  const myGen = ++cityFetchGen;

  try {
    const res: unknown = await getCityDataApi(province, year, signal);
    if (myGen !== cityFetchGen) return;
    const raw = extractList(res);
    const rows = raw.map((r) => normalizeProvinceRecord((r as Record<string, unknown>) ?? {}));
    realCityData.value = rows;
    if (!cityCache.has(ck)) trimMap(cityCache, CITY_CACHE_MAX);
    cityCache.set(ck, rows);
    console.log(`✅ [${province}] ${year} 年地级市数据 ${rows.length} 条`);
  } catch (error) {
    if (signal.aborted || axios.isCancel(error)) return;
    if (myGen !== cityFetchGen) return;
    console.error('❌ 地级市数据拉取失败:', error);
    realCityData.value = [];
  }
};
