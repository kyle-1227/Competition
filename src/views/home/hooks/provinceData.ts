/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
import axios from 'axios';
import { ref, type Ref } from 'vue';
import { getProvinceDataApi, getCityDataApi } from '@/api/modules/dashboard-green-finance';

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
  carbonEmission?: number | null;
  gdp?: number | null;
  primaryIndustry?: number | null;
  secondaryIndustry?: number | null;
  tertiaryIndustry?: number | null;
  primaryIndustryRatio?: number | null;
  secondaryIndustryRatio?: number | null;
  tertiaryIndustryRatio?: number | null;
}

export const indicatorLabels = {
  greenCredit: '绿色信贷',
  greenInvest: '绿色投资',
  greenInsurance: '绿色保险',
  greenBond: '绿色债券',
  greenExpend: '绿色支出',
  greenFund: '绿色基金',
  greenEquity: '绿色权益',
} as const;

export type GreenFinanceIndicatorKey = keyof typeof indicatorLabels;
export const indicatorKeys = Object.keys(indicatorLabels) as GreenFinanceIndicatorKey[];

export const yearlyData: Record<number, ProvinceGreenFinance[]> = {};

export const PROVINCES_EXCLUDED_FROM_PANEL = [
  '西藏自治区',
  '香港特别行政区',
  '澳门特别行政区',
  '台湾省',
] as const;

const PROVINCES_EXCLUDED_SET = new Set<string>(PROVINCES_EXCLUDED_FROM_PANEL);

export const NO_PANEL_DATA_REGIONS_LEGEND = '西藏、香港、澳门、台湾';

export function isProvinceExcludedFromPanel(name: string): boolean {
  return PROVINCES_EXCLUDED_SET.has(String(name || '').trim());
}

export function excludeProvincesWithoutPanelData(names: string[]): string[] {
  return names.filter((name) => !isProvinceExcludedFromPanel(name));
}

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
  云南省: [102.712, 25.04],
  内蒙古自治区: [111.678, 40.854],
  北京市: [116.407, 39.904],
  吉林省: [125.324, 43.886],
  四川省: [104.066, 30.659],
  天津市: [117.19, 39.126],
  宁夏回族自治区: [106.278, 38.466],
  安徽省: [117.283, 31.861],
  山东省: [117.001, 36.676],
  山西省: [112.549, 37.857],
  广东省: [113.264, 23.129],
  广西壮族自治区: [108.32, 22.825],
  新疆维吾尔自治区: [87.617, 43.792],
  江苏省: [118.797, 32.06],
  江西省: [115.892, 28.676],
  河北省: [114.502, 38.045],
  河南省: [113.665, 34.758],
  浙江省: [120.154, 30.287],
  海南省: [110.329, 20.036],
  湖北省: [114.299, 30.584],
  湖南省: [112.982, 28.194],
  甘肃省: [103.823, 36.058],
  福建省: [119.306, 26.075],
  西藏自治区: [91.118, 29.646],
  贵州省: [106.713, 26.578],
  辽宁省: [123.429, 41.796],
  重庆市: [106.552, 29.563],
  陕西省: [108.948, 34.263],
  青海省: [101.778, 36.623],
  黑龙江省: [126.642, 45.756],
};

export const fullToShortName: Record<string, string> = Object.fromEntries(
  Object.entries(provinceNameMap).map(([shortName, fullName]) => [fullName, shortName]),
);

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

export type LocalGeoJson = { type: string; features: any[] };

const provinceCache = new Map<number, ProvinceGreenFinance[]>();
const cityCache = new Map<string, ProvinceGreenFinance[]>();
const localGeoJsonCache = new Map<string, LocalGeoJson>();
export const geoJsonCache = new Map<string, LocalGeoJson>();
const cityAdcodeMap = new Map<string, string>();

const PROVINCE_CACHE_MAX = 10;
const CITY_CACHE_MAX = 16;

let provinceFetchGen = 0;
let provinceAbort: AbortController | null = null;
let cityFetchGen = 0;
let cityAbort: AbortController | null = null;

function trimMap<K, V>(target: Map<K, V>, max: number) {
  while (target.size >= max) {
    const firstKey = target.keys().next().value as K;
    target.delete(firstKey);
  }
}

function cityCacheKey(province: string, year: number) {
  return `${province}|${year}`;
}

function normalizeGeoJsonPayload(json: { type: string; features?: any[] }, label: string): LocalGeoJson {
  if (json.type === 'FeatureCollection' && Array.isArray(json.features)) {
    return { type: 'FeatureCollection', features: json.features };
  }
  if (json.type === 'Feature') {
    return { type: 'FeatureCollection', features: [json] };
  }
  throw new Error(`无效的 GeoJSON 数据: ${label}`);
}

async function fetchLocalGeoJson(fileBaseName: string): Promise<LocalGeoJson> {
  const cacheKey = String(fileBaseName || '').trim();
  const localHit = localGeoJsonCache.get(cacheKey);
  if (localHit) return localHit;

  const sharedHit = geoJsonCache.get(cacheKey);
  if (sharedHit) return sharedHit;

  const base = import.meta.env.BASE_URL || '/';
  const fileName = `${encodeURIComponent(cacheKey)}.geojson`;
  const path = `${base}geojson/${fileName}`.replace(/\/{2,}/g, '/');
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`GeoJSON 请求失败 ${cacheKey}: ${response.status}`);
  }

  const json = (await response.json()) as { type: string; features?: any[] };
  const normalized = normalizeGeoJsonPayload(json, cacheKey);
  localGeoJsonCache.set(cacheKey, normalized);
  geoJsonCache.set(cacheKey, normalized);
  return normalized;
}

export async function fetchCountryGeoJson(): Promise<LocalGeoJson> {
  return fetchLocalGeoJson('中华人民共和国');
}

export async function fetchGeoJson(provinceFullName: string): Promise<LocalGeoJson> {
  return fetchLocalGeoJson(provinceFullName);
}

export function rememberCityAdcode(cityName: string, adcode: string | number): void {
  const normalizedName = String(cityName || '').trim();
  const normalizedCode = String(adcode ?? '').trim();
  if (!normalizedName || !normalizedCode) return;
  cityAdcodeMap.set(normalizedName, normalizedCode);
}

export function scoreToColor(score: number): string {
  if (score > 0.7) return '#00e5ff';
  if (score > 0.5) return '#2979ff';
  if (score > 0.3) return '#7c4dff';
  if (score > 0.15) return '#ff6d00';
  return '#ff1744';
}

export const gfDrillProvince: Ref<string> = ref('');
export const gfRadarCityHoverGeoName: Ref<string> = ref('');
export const selectedProvince: Ref<string> = ref('');
export const selectedYear: Ref<number> = ref(2024);
export const timelineYear: Ref<number> = ref(2024);
export const apiProvinceYear = ref<number | null>(null);
export const realProvinceData = ref<ProvinceGreenFinance[]>([]);
export const realCityData = ref<ProvinceGreenFinance[]>([]);

function toNum(value: unknown, fallback = 0): number {
  const parsed = typeof value === 'number' ? value : parseFloat(String(value ?? ''));
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toNullableNum(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = typeof value === 'number' ? value : parseFloat(String(value));
  return Number.isFinite(parsed) ? parsed : null;
}

export function normalizeProvinceRecord(row: Record<string, unknown>): ProvinceGreenFinance {
  const cityRaw = row.city;
  const hasCity = cityRaw !== undefined && cityRaw !== null && String(cityRaw).trim() !== '';
  const normalizedName = String(
    hasCity ? cityRaw : (row.province ?? row.name ?? row.city_name ?? ''),
  ).trim();

  return {
    province: normalizedName,
    score: toNum(row.score ?? row.total_score),
    greenCredit: toNum(row.greenCredit ?? row.green_credit),
    greenInvest: toNum(row.greenInvest ?? row.green_invest),
    greenInsurance: toNum(row.greenInsurance ?? row.green_insurance),
    greenBond: toNum(row.greenBond ?? row.green_bond),
    greenExpend: toNum(row.greenExpend ?? row.green_expend ?? row.greenSupport ?? row.green_support),
    greenFund: toNum(row.greenFund ?? row.green_fund),
    greenEquity: toNum(row.greenEquity ?? row.green_equity),
    carbonEmission: toNullableNum(row.carbonEmission ?? row.carbon_emission),
    gdp: toNullableNum(row.gdp ?? row.GDP),
    primaryIndustry: toNullableNum(row.primaryIndustry ?? row.primary_industry),
    secondaryIndustry: toNullableNum(row.secondaryIndustry ?? row.secondary_industry),
    tertiaryIndustry: toNullableNum(row.tertiaryIndustry ?? row.tertiary_industry),
    primaryIndustryRatio: toNullableNum(row.primaryIndustryRatio ?? row.primary_industry_ratio),
    secondaryIndustryRatio: toNullableNum(row.secondaryIndustryRatio ?? row.secondary_industry_ratio),
    tertiaryIndustryRatio: toNullableNum(row.tertiaryIndustryRatio ?? row.tertiary_industry_ratio),
  };
}

export function extractList(payload: unknown): unknown[] {
  if (Array.isArray(payload)) return payload;
  if (payload && typeof payload === 'object') {
    const record = payload as Record<string, unknown>;
    if (Array.isArray(record.data)) return record.data;
    if (Array.isArray(record.list)) return record.list;
    if (Array.isArray(record.records)) return record.records;
  }
  return [];
}

export function getProvinceRows(year: number): ProvinceGreenFinance[] {
  if (apiProvinceYear.value === year && realProvinceData.value.length > 0) {
    return realProvinceData.value;
  }
  return [];
}

export function findProvince(name: string, year = 2024): ProvinceGreenFinance | undefined {
  const list = getProvinceRows(year);
  const fullName = provinceNameMap[name] || name;
  return list.find(
    (item) => item.province === fullName || item.province.startsWith(name) || name.startsWith(item.province),
  );
}

export function findCityRowByGeoName(geoName: string): ProvinceGreenFinance | undefined {
  const normalizedGeoName = String(geoName || '').trim();
  if (!normalizedGeoName) return undefined;
  return realCityData.value.find(
    (item) =>
      item.province === normalizedGeoName ||
      normalizedGeoName.startsWith(item.province) ||
      item.province.startsWith(normalizedGeoName),
  );
}

export const fetchProvinceData = async (year: number) => {
  const cacheHit = provinceCache.get(year);
  if (cacheHit) {
    realProvinceData.value = cacheHit;
    apiProvinceYear.value = year;
    return;
  }

  provinceAbort?.abort();
  provinceAbort = new AbortController();
  const signal = provinceAbort.signal;
  const currentGen = ++provinceFetchGen;

  try {
    const response: unknown = await getProvinceDataApi(year, signal);
    if (currentGen !== provinceFetchGen) return;

    const rows = extractList(response).map((item) =>
      normalizeProvinceRecord((item as Record<string, unknown>) ?? {}),
    );

    realProvinceData.value = rows;
    apiProvinceYear.value = year;
    if (!provinceCache.has(year)) trimMap(provinceCache, PROVINCE_CACHE_MAX);
    provinceCache.set(year, rows);
    console.log(`成功拉取 ${year} 年省级绿色金融数据 ${rows.length} 条`);
  } catch (error) {
    if (signal.aborted || axios.isCancel(error)) return;
    if (currentGen !== provinceFetchGen) return;
    console.error(`拉取 ${year} 年省级绿色金融数据失败`, error);
    apiProvinceYear.value = null;
  }
};

export const fetchCityData = async (province: string, year: number) => {
  if (!province) {
    realCityData.value = [];
    return;
  }

  const cacheKey = cityCacheKey(province, year);
  const cacheHit = cityCache.get(cacheKey);
  if (cacheHit) {
    realCityData.value = cacheHit;
    return;
  }

  cityAbort?.abort();
  cityAbort = new AbortController();
  const signal = cityAbort.signal;
  const currentGen = ++cityFetchGen;

  try {
    const response: unknown = await getCityDataApi(province, year, signal);
    if (currentGen !== cityFetchGen) return;

    const rows = extractList(response).map((item) =>
      normalizeProvinceRecord((item as Record<string, unknown>) ?? {}),
    );

    realCityData.value = rows;
    if (!cityCache.has(cacheKey)) trimMap(cityCache, CITY_CACHE_MAX);
    cityCache.set(cacheKey, rows);
    console.log(`成功拉取 [${province}] ${year} 年市级绿色金融数据 ${rows.length} 条`);
  } catch (error) {
    if (signal.aborted || axios.isCancel(error)) return;
    if (currentGen !== cityFetchGen) return;
    console.error(`拉取 [${province}] ${year} 年市级绿色金融数据失败`, error);
    realCityData.value = [];
  }
};
