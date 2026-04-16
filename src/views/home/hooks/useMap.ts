/* eslint-disable @typescript-eslint/ban-ts-comment, no-undef, no-underscore-dangle, no-param-reassign, no-plusplus, no-continue */
// @ts-nocheck
import { onMounted, watch, type Ref } from 'vue';
import { LineLayer, PolygonLayer, Scene } from '@antv/l7';
import { Map } from '@antv/l7-maps';
import {
  realProvinceData,
  scoreToColor,
  fetchCountryGeoJson,
  fetchGeoJson,
  fetchCityData,
  realCityData,
  selectedYear,
  gfDrillProvince,
  gfRadarCityHoverGeoName,
  rememberCityAdcode,
  isProvinceExcludedFromPanel,
  indicatorKeys,
  indicatorLabels,
  type ProvinceGreenFinance,
} from './provinceData';
import { getTooltipAiSnapshot, requestTooltipAi } from './useTooltipAi';

/** 缁胯壊閲戣瀺鍦板浘鎮仠娴锛圴ue 涓?useGreenFinanceMap 鍏辩敤锛?*/
export interface GfMapTooltipState {
  visible: boolean;
  left: number;
  top: number;
  regionName: string;
  year: number;
  scoreText: string;
  rows: { label: string; value: string }[];
  mode: 'province' | 'city';
  aiInsight: string;
  aiLoading: boolean;
  aiCacheKey: string;
}

export function createHiddenGfTooltip(): GfMapTooltipState {
  return {
    visible: false,
    left: 0,
    top: 0,
    regionName: '',
    year: selectedYear.value,
    scoreText: '',
    rows: [],
    mode: 'province',
    aiInsight: '',
    aiLoading: false,
    aiCacheKey: '',
  };
}

export interface CarbonMapTooltipState {
  visible: boolean;
  left: number;
  top: number;
  regionName: string;
  year: number;
  headlineLabel: string;
  headlineValue: string;
  headlineUnit: string;
  rows: { label: string; value: string }[];
  mode: 'province' | 'city';
  metric: 'carbon' | 'gdp';
  aiInsight: string;
  aiLoading: boolean;
  aiCacheKey: string;
}

export function createHiddenCarbonTooltip(): CarbonMapTooltipState {
  return {
    visible: false,
    left: 0,
    top: 0,
    regionName: '',
    year: selectedYear.value,
    headlineLabel: '',
    headlineValue: '—',
    headlineUnit: '',
    rows: [],
    mode: 'province',
    metric: 'carbon',
    aiInsight: '',
    aiLoading: false,
    aiCacheKey: '',
  };
}

function formatTooltipMetricNumber(value: unknown, digits = 2): string {
  if (value == null) return '—';
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return '—';
  return parsed.toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

function formatTooltipMetricCell(value: unknown, unit = '', digits = 2): string {
  const formatted = formatTooltipMetricNumber(value, digits);
  if (formatted === '—') return formatted;
  return unit ? `${formatted} ${unit}` : formatted;
}

/** 涓冪淮涓庣患鍚堟寚鏁颁竴鑷达細搴撳唴涓?0锝?锛屽睍绀轰负鐧惧垎鍒讹紝淇濈暀 2 浣嶅皬鏁?*/
function formatIndicatorCell(v: unknown): string {
  if (v == null || (typeof v === 'number' && !Number.isFinite(v))) return '—';
  if (typeof v === 'number') {
    return (v * 100).toLocaleString('zh-CN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  return String(v);
}

function findProvinceRow(fullName: string): ProvinceGreenFinance | undefined {
  return realProvinceData.value.find(
    (r) =>
      r.province === fullName ||
      fullName.startsWith(r.province) ||
      r.province.startsWith(fullName),
  );
}

function findCityRow(geoName: string): ProvinceGreenFinance | undefined {
  const g = String(geoName || '').trim();
  if (!g) return undefined;
  return realCityData.value.find(
    (r) => r.province === g || g.startsWith(r.province) || r.province.startsWith(g),
  );
}

function buildTooltipRowsFromRow(row: ProvinceGreenFinance | undefined): { label: string; value: string }[] {
  return indicatorKeys.map((key) => ({
    label: indicatorLabels[key],
    value: formatIndicatorCell(row?.[key]),
  }));
}

function scoreToDisplayText(row: ProvinceGreenFinance | undefined): string {
  if (!row || typeof row.score !== 'number' || !Number.isFinite(row.score)) return '—';
  return (row.score * 100).toFixed(2);
}

function buildGreenFinanceTooltipAiPayload(
  regionName: string,
  mode: 'province' | 'city',
  row: ProvinceGreenFinance | undefined,
) {
  const indicators = indicatorKeys.reduce((acc, key) => {
    const rawValue = row?.[key];
    acc[key] = typeof rawValue === 'number' && Number.isFinite(rawValue) ? Number((rawValue * 100).toFixed(2)) : null;
    return acc;
  }, {} as Record<string, number | null>);

  return {
    regionName,
    year: selectedYear.value,
    moduleName: 'greenFinance',
    tooltipScope: mode === 'province' ? 'greenFinanceMapProvince' : 'greenFinanceMapCity',
    dataPayload: {
      regionName,
      mode,
      score: row && typeof row.score === 'number' ? Number((row.score * 100).toFixed(2)) : null,
      indicators,
    },
  };
}

function applyGreenFinanceTooltipAi(
  tooltipRef: Ref<GfMapTooltipState>,
  baseState: Omit<GfMapTooltipState, 'aiInsight' | 'aiLoading' | 'aiCacheKey'>,
  aiPayload: {
    regionName: string;
    year: number;
    moduleName: string;
    tooltipScope: string;
    dataPayload: Record<string, unknown>;
  },
) {
  const requestPromise = requestTooltipAi(aiPayload);
  const snapshot = getTooltipAiSnapshot(aiPayload);
  tooltipRef.value = {
    ...baseState,
    aiInsight: snapshot.content,
    aiLoading: snapshot.loading,
    aiCacheKey: snapshot.cacheKey,
  };

  void requestPromise.then((content) => {
    const current = tooltipRef.value;
    if (!current.visible || current.aiCacheKey !== snapshot.cacheKey) return;
    tooltipRef.value = {
      ...current,
      aiInsight: content,
      aiLoading: false,
    };
  });
}

function attachGreenFinanceMapTooltip(
  layer: PolygonLayer,
  scene: Scene,
  mapAreaEl: HTMLElement,
  mapRootEl: HTMLElement,
  tooltipRef: Ref<GfMapTooltipState>,
  mode: 'province' | 'city',
  shouldHandle?: (e: any) => boolean,
) {
  const OFFSET_X = 14;
  const OFFSET_Y = 14;

  const applyPayload = (name: string, lng: number, lat: number) => {
    const pt = scene.lngLatToContainer([lng, lat]);
    const areaR = mapAreaEl.getBoundingClientRect();
    const mapR = mapRootEl.getBoundingClientRect();
    const left = mapR.left - areaR.left + pt.x + OFFSET_X;
    const top = mapR.top - areaR.top + pt.y + OFFSET_Y;
    const row = mode === 'province' ? findProvinceRow(name) : findCityRow(name);
    const baseState = {
      visible: true,
      left,
      top,
      regionName: name,
      year: selectedYear.value,
      scoreText: scoreToDisplayText(row),
      rows: buildTooltipRowsFromRow(row),
      mode,
    };
    applyGreenFinanceTooltipAi(tooltipRef, baseState, buildGreenFinanceTooltipAiPayload(name, mode, row));
    if (mode === 'city') {
      gfRadarCityHoverGeoName.value = name;
    }
  };

  const hide = () => {
    tooltipRef.value = createHiddenGfTooltip();
    if (mode === 'city') {
      gfRadarCityHoverGeoName.value = '';
    }
  };

  const onPick = (e: any) => {
    if (shouldHandle && !shouldHandle(e)) {
      hide();
      return;
    }
    const name = e.feature?.properties?.name;
    if (!name) return;
    if (mode === 'province' && isProvinceExcludedFromPanel(name)) return;
    const ll = e.lngLat ?? e.lnglat;
    if (!ll) return;
    const lng = typeof ll.lng === 'number' ? ll.lng : ll[0];
    const lat = typeof ll.lat === 'number' ? ll.lat : ll[1];
    if (typeof lng !== 'number' || typeof lat !== 'number') return;
    applyPayload(name, lng, lat, true);
  };

  layer.on('mouseenter', onPick);
  layer.on('mousemove', onPick);
  layer.on('mouseout', hide);

  return { hide };
}

/** 缁块噾 3D 鏌变綋椤堕潰澶栬疆寤撶櫧绾匡紙涓庢煴椤跺悓楂橈紝鍖哄垎閭荤渷/甯傦級 */
const GF_EXTRUDE_TOP_LINE_COLOR = 'rgba(255,255,255,0.9)';
const GF_EXTRUDE_TOP_LINE_WIDTH = 1.15;
const GF_BACKDROP_COLOR = 'rgba(40, 50, 70, 0.4)';
const GF_BACKDROP_TOP_LINE_COLOR = 'rgba(180, 196, 220, 0.3)';
const GF_BACKDROP_SCORE = 100;
/** 涓?PolygonLayer `.size('_score', range)` 涓€鑷?*/
const GF_PROVINCE_EXTRUDE_RANGE: [number, number] = [20000, 2000000];
const GF_CITY_EXTRUDE_RANGE: [number, number] = [12000, 1800000];
const COUNTY_NO_DATA_COLOR = '#5c6470';
const PROVINCE_COLOR_RAMP = [
  '#1a237e',
  '#0d47a1',
  '#01579b',
  '#006064',
  '#1b5e20',
  '#827717',
  '#f57f17',
  '#ff6f00',
  '#e65100',
  '#ffab00',
];
const GF_CINEMATIC_PADDING = { top: 80, bottom: 80, left: 80, right: 80 };
const GF_CINEMATIC_DRILL_CAMERA = {
  pitch: 55,
  bearing: 5,
  duration: 1800,
  curve: 1.414,
  essential: true,
};
const GF_CINEMATIC_RESET_CAMERA = {
  center: [104.195397, 35.86166] as [number, number],
  zoom: 3.2,
  pitch: 45,
  bearing: 0,
  duration: 1800,
  essential: true,
};
const GF_ACTIVE_COLOR = 'rgba(0,229,255,0.45)';
const CARBON_MUTED_SCORE = 0.001;
const CARBON_FILL_OPACITY = 0.88;
const CARBON_BOUNDARY_COLOR = 'rgba(225, 240, 255, 0.76)';
const CARBON_BOUNDARY_BACKDROP_COLOR = 'rgba(180, 196, 220, 0.42)';
const CARBON_PROVINCE_BOUNDARY_COLOR = 'rgba(0,229,255,0.38)';
const CARBON_PROVINCE_BOUNDARY_BACKDROP_COLOR = 'rgba(140,168,190,0.18)';
const CARBON_BOUNDARY_WIDTH = 0.85;
const CARBON_PROVINCE_BOUNDARY_WIDTH = 0.65;
const CARBON_COLOR_RAMP = [
  '#1b5e20',
  '#2e7d32',
  '#388e3c',
  '#43a047',
  '#66bb6a',
  '#a5d6a7',
  '#ffcc80',
  '#ffb74d',
  '#ff9800',
  '#f57c00',
  '#e65100',
  '#d84315',
  '#b71c1c',
];

function regionNameMatches(geoName: string, selectedName: string): boolean {
  const geo = String(geoName || '').trim();
  const selected = String(selectedName || '').trim();
  return !!geo && !!selected && (geo === selected || geo.startsWith(selected) || selected.startsWith(geo));
}

function carbonRampColor(value: number, maxValue: number): string {
  const carbon = Number(value);
  if (!Number.isFinite(carbon) || carbon <= 0) return CARBON_COLOR_RAMP[0];
  const maxCarbon = Number.isFinite(maxValue) && maxValue > 0 ? maxValue : carbon;
  const ratio = Math.max(0, Math.min(1, carbon / maxCarbon));
  const idx = Math.min(CARBON_COLOR_RAMP.length - 1, Math.round(ratio * (CARBON_COLOR_RAMP.length - 1)));
  return CARBON_COLOR_RAMP[idx];
}

function buildProvinceScoreMap(): Record<string, number> {
  const scoreMap: Record<string, number> = {};
  realProvinceData.value.forEach((d) => {
    scoreMap[d.province] = d.score;
  });
  return scoreMap;
}

function buildCarbonMapWanTon(): Record<string, number> {
  const m: Record<string, number> = {};
  realProvinceData.value.forEach((d) => {
    m[d.province] = (d.carbonEmission ?? 0) / 10000;
  });
  return m;
}

function buildProvinceGdpMap(): Record<string, number> {
  const m: Record<string, number> = {};
  realProvinceData.value.forEach((d) => {
    m[d.province] = Number(d.gdp ?? 0);
  });
  return m;
}

/** 涓?L7 瀵?`_score` 绾挎€ф槧灏勫埌鏌遍珮锛堢背锛夌殑瑙勫垯瀵归綈 */
function extrudeHeightMForScores(
  features: { properties?: { _score?: number } }[],
  range: [number, number],
): (f: { properties?: { _score?: number } }) => number {
  let minS = Infinity;
  let maxS = -Infinity;
  features.forEach((f) => {
    const s = f.properties?._score;
    if (typeof s !== 'number' || Number.isNaN(s)) return;
    minS = Math.min(minS, s);
    maxS = Math.max(maxS, s);
  });
  const [r0, r1] = range;
  if (!Number.isFinite(minS) || minS === maxS) {
    return () => r0;
  }
  return (f) => {
    const s = f.properties?._score;
    const v = typeof s === 'number' && !Number.isNaN(s) ? s : minS;
    return r0 + ((v - minS) / (maxS - minS)) * (r1 - r0);
  };
}

/** 澶氳竟褰㈠鐜?鈫?甯︾粺涓€ Z锛堟煴椤堕珮搴︾背锛夌殑 LineString锛屼緵 LineLayer 缁樺埗椤惰竟 */
function buildExtrudeTopOutlines(
  fc: { features: any[] },
  range: [number, number],
): { type: string; features: any[] } {
  const getH = extrudeHeightMForScores(fc.features, range);
  const lineFeatures: any[] = [];
  fc.features.forEach((f) => {
    const h = getH(f);
    const geom = f.geometry;
    if (!geom) return;
    const pushRing = (ring: number[][]) => {
      if (!ring || ring.length < 2) return;
      const coords: number[][] = [];
      ring.forEach((pt) => {
        if (typeof pt[0] !== 'number' || typeof pt[1] !== 'number') return;
        coords.push([pt[0], pt[1], h]);
      });
      if (coords.length < 2) return;
      const a = coords[0];
      const b = coords[coords.length - 1];
      if (a[0] !== b[0] || a[1] !== b[1]) {
        coords.push([a[0], a[1], h]);
      }
      lineFeatures.push({
        type: 'Feature',
        properties: { ...(f.properties || {}) },
        geometry: { type: 'LineString', coordinates: coords },
      });
    };
    if (geom.type === 'Polygon') {
      pushRing(geom.coordinates[0]);
    } else if (geom.type === 'MultiPolygon') {
      geom.coordinates.forEach((poly: number[][][]) => pushRing(poly[0]));
    }
  });
  return { type: 'FeatureCollection', features: lineFeatures };
}

function matchCityScore(geoName: string, rows: { province: string; score: number }[]): number {
  if (!geoName || !rows.length) return 0;
  const g = String(geoName).trim();
  const row = rows.find(
    (r) => r.province === g || g.startsWith(r.province) || r.province.startsWith(g),
  );
  return row ? row.score : 0;
}

function updateBBoxFromCoords(
  bbox: [number, number, number, number] | null,
  coord: unknown,
): [number, number, number, number] | null {
  if (coord == null) return bbox;
  if (typeof coord === 'number') return bbox;
  const arr = coord as unknown[];
  if (arr.length >= 2 && typeof arr[0] === 'number' && typeof arr[1] === 'number') {
    const lng = arr[0] as number;
    const lat = arr[1] as number;
    if (!bbox) return [lng, lat, lng, lat];
    return [
      Math.min(bbox[0], lng),
      Math.min(bbox[1], lat),
      Math.max(bbox[2], lng),
      Math.max(bbox[3], lat),
    ];
  }
  let b = bbox;
  for (let i = 0; i < arr.length; i++) {
    b = updateBBoxFromCoords(b, arr[i]);
  }
  return b;
}

function boundsFromFeatures(features: { geometry?: { coordinates?: unknown } }[]): [[number, number], [number, number]] | null {
  let bbox: [number, number, number, number] | null = null;
  features.forEach((f) => {
    const coords = f.geometry?.coordinates;
    if (coords !== undefined) bbox = updateBBoxFromCoords(bbox, coords);
  });
  if (!bbox || bbox[0] === Infinity) return null;
  return [
    [bbox[0], bbox[1]],
    [bbox[2], bbox[3]],
  ];
}

function cloneFeatureCollection(fc: { type: string; features: any[] }): { type: string; features: any[] } {
  return {
    type: fc.type,
    features: fc.features.map((f) => ({
      ...f,
      properties: { ...(f.properties || {}) },
      geometry: f.geometry ? JSON.parse(JSON.stringify(f.geometry)) : f.geometry,
    })),
  };
}

export function useGreenFinanceMap(selectedProv: Ref<string>, tooltipRef: Ref<GfMapTooltipState>) {
  onMounted(() => {
    const scene = new Scene({
      id: 'gf-map',
      map: new Map({
        pitch: 45,
        style: 'dark',
        center: [104.195397, 35.86166],
        zoom: 3.2,
      }),
    });
    scene.setBgColor('#131722');

    scene.on('loaded', () => {
      const mapEl = document.getElementById('gf-map');
      if (mapEl) mapEl.style.background = '#131722';
      const mapAreaEl = mapEl?.parentElement instanceof HTMLElement ? mapEl.parentElement : null;
      const nativeMap = scene.getMapService?.()?.map || scene.map;

      nativeMap?.doubleClickZoom?.disable?.();

      let cityExtrudeLayer: PolygonLayer | null = null;
      let provinceTopOutlineLayer: LineLayer | null = null;
      let cityTopOutlineLayer: LineLayer | null = null;
      let cityBaseSnapshot: { type: string; features: any[] } | null = null;
      let cityFullSnapshot: { type: string; features: any[] } | null = null;
      let citySnapshotProvince = '';
      let drillGen = 0;

      const runNextFrame = (cb: () => void) => {
        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
          window.requestAnimationFrame(cb);
          return;
        }
        setTimeout(cb, 16);
      };

      const runCinematicFit = (bounds: [[number, number], [number, number]] | null) => {
        if (!bounds) return;
        runNextFrame(() => {
          nativeMap?.stop?.();
          if (nativeMap?.fitBounds) {
            nativeMap.fitBounds(bounds, {
              padding: GF_CINEMATIC_PADDING,
              ...GF_CINEMATIC_DRILL_CAMERA,
            });
            return;
          }
          scene.fitBounds(bounds, {
            padding: 80,
            duration: GF_CINEMATIC_DRILL_CAMERA.duration,
          });
          scene.setPitch(GF_CINEMATIC_DRILL_CAMERA.pitch);
          scene.setRotation?.(GF_CINEMATIC_DRILL_CAMERA.bearing);
        });
      };

      const runNationalResetFlight = () => {
        runNextFrame(() => {
          nativeMap?.stop?.();
          if (nativeMap?.flyTo) {
            nativeMap.flyTo({ ...GF_CINEMATIC_RESET_CAMERA });
            return;
          }
          scene.setZoomAndCenter(GF_CINEMATIC_RESET_CAMERA.zoom, GF_CINEMATIC_RESET_CAMERA.center);
          scene.setPitch(GF_CINEMATIC_RESET_CAMERA.pitch);
          scene.setRotation?.(GF_CINEMATIC_RESET_CAMERA.bearing);
        });
      };

      const stepOutOneLevel = () => {
        tooltipRef.value = createHiddenGfTooltip();
        gfRadarCityHoverGeoName.value = '';
        if (gfDrillProvince.value) {
          gfDrillProvince.value = '';
        }
      };

      fetchCountryGeoJson().then((geoData) => {
        const features = geoData.features.filter((f) => f.properties.name);
        const noPanelFeats = features.filter((f) => isProvinceExcludedFromPanel(f.properties.name));
        const mainFeats = features.filter((f) => !isProvinceExcludedFromPanel(f.properties.name));
        const fullOutlineGeo = { type: 'FeatureCollection', features };
        const provinceBaseSnapshot = cloneFeatureCollection({ type: 'FeatureCollection', features: mainFeats });
        let cityExtrudeLayer: PolygonLayer | null = null;
        let cityTopOutlineLayer: LineLayer | null = null;
        let cityBaseSnapshot: { type: string; features: any[] } | null = null;
        let cityFullSnapshot: { type: string; features: any[] } | null = null;
        let citySnapshotProvince = '';
        let drillGen = 0;

        const noPanelFillGeo = { type: 'FeatureCollection', features: noPanelFeats };
        const noPanelFill = new PolygonLayer({ zIndex: 4 })
          .source(noPanelFillGeo)
          .shape('fill')
          .color('#5c6470')
          .style({ opacity: 0.95 });
        scene.addLayer(noPanelFill);

        const applyProvinceScoresToFc = (fc: { features: any[] }) => {
          const scoreMap = buildProvinceScoreMap();
          fc.features.forEach((f) => {
            const s = scoreMap[f.properties?.name || ''] || 0;
            f.properties._score = s ** 1.5;
            f.properties._rawScore = s;
            f.properties._color = scoreToColor(s);
            f.properties._isBackdrop = false;
          });
        };

        let provinceFullSnapshot = cloneFeatureCollection(provinceBaseSnapshot);
        applyProvinceScoresToFc(provinceFullSnapshot);

        const restoreProvinceForegroundGeo = () => {
          const fc = cloneFeatureCollection(provinceBaseSnapshot);
          applyProvinceScoresToFc(fc);
          provinceFullSnapshot = cloneFeatureCollection(fc);
          return fc;
        };

        const buildProvinceBackdropGeo = (selectedProvince: string) => {
          const fc = cloneFeatureCollection(provinceFullSnapshot);
          fc.features = fc.features
            .filter((f) => f.properties?.name !== selectedProvince)
            .map((f) => ({
              ...f,
              properties: {
                ...(f.properties || {}),
                _score: GF_BACKDROP_SCORE,
                _rawScore: 0,
                _color: GF_BACKDROP_COLOR,
                _isBackdrop: true,
              },
            }));
          return fc;
        };

        const extrudeLayer = new PolygonLayer({ zIndex: 5 })
          .source(provinceFullSnapshot)
          .shape('extrude')
          .size('_score', GF_PROVINCE_EXTRUDE_RANGE)
          .color('_rawScore', PROVINCE_COLOR_RAMP)
          .style({ heightfixed: true, pickLight: true, opacity: 0.88 })
          .active({ color: GF_ACTIVE_COLOR });
        scene.addLayer(extrudeLayer);

        provinceTopOutlineLayer = new LineLayer({ zIndex: 15 })
          .source(buildExtrudeTopOutlines(provinceFullSnapshot, GF_PROVINCE_EXTRUDE_RANGE))
          .shape('line')
          .color(GF_EXTRUDE_TOP_LINE_COLOR)
          .size(GF_EXTRUDE_TOP_LINE_WIDTH)
          .style({
            opacity: 0.94,
            heightfixed: true,
            vertexHeightScale: 1,
            depth: true,
          });
        scene.addLayer(provinceTopOutlineLayer);

        const borderLayer = new LineLayer({ zIndex: 10 })
          .source(fullOutlineGeo)
          .shape('line')
          .color('rgba(0,229,255,0.38)')
          .size(0.65)
          .style({ opacity: 0.75 });
        scene.addLayer(borderLayer);

        const setProvinceLayerData = (fc: { type: string; features: any[] }, backdrop = false) => {
          const nextGeo = cloneFeatureCollection(fc);
          extrudeLayer.setData(nextGeo);
          if (backdrop) {
            extrudeLayer.color('_color');
            extrudeLayer.active(false);
            provinceTopOutlineLayer?.color(GF_BACKDROP_TOP_LINE_COLOR);
            borderLayer.color('rgba(140,168,190,0.18)');
            borderLayer.style({ opacity: 0.45 });
            noPanelFill.color('rgba(92,100,112,0.72)');
            noPanelFill.style({ opacity: 0.72 });
          } else {
            extrudeLayer.color('_rawScore', PROVINCE_COLOR_RAMP);
            extrudeLayer.active({ color: GF_ACTIVE_COLOR });
            provinceTopOutlineLayer?.color(GF_EXTRUDE_TOP_LINE_COLOR);
            borderLayer.color('rgba(0,229,255,0.38)');
            borderLayer.style({ opacity: 0.75 });
            noPanelFill.color('#5c6470');
            noPanelFill.style({ opacity: 0.95 });
          }
          provinceTopOutlineLayer?.setData(buildExtrudeTopOutlines(nextGeo, GF_PROVINCE_EXTRUDE_RANGE));
          extrudeLayer.show();
          provinceTopOutlineLayer?.show();
        };

        extrudeLayer.on('click', (e) => {
          if (gfDrillProvince.value) return;
          const name = e.feature?.properties?.name;
          if (name && !isProvinceExcludedFromPanel(name) && e.feature?.properties?._isBackdrop !== true) {
            selectedProv.value = name;
            gfDrillProvince.value = name;
          }
        });

        if (mapAreaEl && mapEl) {
          attachGreenFinanceMapTooltip(
            extrudeLayer,
            scene,
            mapAreaEl,
            mapEl,
            tooltipRef,
            'province',
            () => !gfDrillProvince.value,
          );
          mapEl.addEventListener('mouseleave', () => {
            tooltipRef.value = createHiddenGfTooltip();
            gfRadarCityHoverGeoName.value = '';
          });
        }

        watch(
          [selectedYear, realProvinceData, realCityData],
          () => {
            const t = tooltipRef.value;
            if (!t.visible || !t.regionName) return;
            const row = t.mode === 'province' ? findProvinceRow(t.regionName) : findCityRow(t.regionName);
            const baseState = {
              ...t,
              year: selectedYear.value,
              scoreText: scoreToDisplayText(row),
              rows: buildTooltipRowsFromRow(row),
            };
            applyGreenFinanceTooltipAi(
              tooltipRef,
              baseState,
              buildGreenFinanceTooltipAiPayload(t.regionName, t.mode, row),
            );
          },
          { deep: true },
        );

        watch(gfDrillProvince, () => {
          tooltipRef.value = createHiddenGfTooltip();
          gfRadarCityHoverGeoName.value = '';
        });

        const applyCityScoresToFc = (fc: { features: any[] }) => {
          const rows = realCityData.value;
          fc.features.forEach((f) => {
            const geoName = f.properties?.name || '';
            const s = matchCityScore(geoName, rows);
            f.properties._score = s ** 1.5;
            f.properties._rawScore = s;
            f.properties._color = scoreToColor(s);
            f.properties._hasData = true;
            f.properties._isBackdrop = false;
          });
        };

        const restoreCityForegroundGeo = () => {
          if (!cityBaseSnapshot) return null;
          const fc = cloneFeatureCollection(cityBaseSnapshot);
          applyCityScoresToFc(fc);
          cityFullSnapshot = cloneFeatureCollection(fc);
          return fc;
        };

        const ensureCityLayers = (fc: { type: string; features: any[] }) => {
          if (!cityExtrudeLayer) {
            cityExtrudeLayer = new PolygonLayer({ zIndex: 6 })
              .source(fc)
              .shape('extrude')
              .size('_score', GF_CITY_EXTRUDE_RANGE)
              .color('_color')
              .style({ heightfixed: true, pickLight: true, opacity: 0.88 })
              .active({ color: GF_ACTIVE_COLOR });
            scene.addLayer(cityExtrudeLayer);
            if (mapAreaEl && mapEl) {
              attachGreenFinanceMapTooltip(
                cityExtrudeLayer,
                scene,
                mapAreaEl,
                mapEl,
                tooltipRef,
                'city',
                () => !!gfDrillProvince.value,
              );
            }
          }
          if (!cityTopOutlineLayer) {
            cityTopOutlineLayer = new LineLayer({ zIndex: 16 })
              .source(buildExtrudeTopOutlines(fc, GF_CITY_EXTRUDE_RANGE))
              .shape('line')
              .color(GF_EXTRUDE_TOP_LINE_COLOR)
              .size(GF_EXTRUDE_TOP_LINE_WIDTH)
              .style({
                opacity: 0.94,
                heightfixed: true,
                vertexHeightScale: 1,
                depth: true,
              });
            scene.addLayer(cityTopOutlineLayer);
          }
        };

        const setCityLayerData = (fc: { type: string; features: any[] }, backdrop = false) => {
          ensureCityLayers(fc);
          const nextGeo = cloneFeatureCollection(fc);
          cityExtrudeLayer?.setData(nextGeo);
          if (backdrop) {
            cityExtrudeLayer?.active(false);
            cityTopOutlineLayer?.color(GF_BACKDROP_TOP_LINE_COLOR);
          } else {
            cityExtrudeLayer?.active({ color: GF_ACTIVE_COLOR });
            cityTopOutlineLayer?.color(GF_EXTRUDE_TOP_LINE_COLOR);
          }
          cityTopOutlineLayer?.setData(buildExtrudeTopOutlines(nextGeo, GF_CITY_EXTRUDE_RANGE));
          cityExtrudeLayer?.show();
          cityTopOutlineLayer?.show();
        };

        watch(
          realProvinceData,
          () => {
            if (gfDrillProvince.value) return;
            const provinceGeo = restoreProvinceForegroundGeo();
            setProvinceLayerData(provinceGeo, false);
            scene.render();
          },
          { deep: true, immediate: true },
        );

        watch(
          realCityData,
          () => {
            if (!gfDrillProvince.value || !cityBaseSnapshot || citySnapshotProvince !== gfDrillProvince.value) return;
            const nextGeo = restoreCityForegroundGeo();
            if (!nextGeo) return;
            setCityLayerData(nextGeo, false);
          },
          { deep: true },
        );

        scene.on('contextmenu', (e: any) => {
          e?.preventDefault?.();
          e?.originalEvent?.preventDefault?.();
          stepOutOneLevel();
        });

        scene.on('dblclick', (e: any) => {
          e?.preventDefault?.();
          e?.originalEvent?.preventDefault?.();
          if (e?.feature) return;
          stepOutOneLevel();
        });

        watch(gfDrillProvince, async (prov) => {
          const gen = ++drillGen;

          if (!prov) {
            cityExtrudeLayer?.hide();
            cityTopOutlineLayer?.hide();
            cityBaseSnapshot = null;
            cityFullSnapshot = null;
            citySnapshotProvince = '';
            const provinceGeo = restoreProvinceForegroundGeo();
            setProvinceLayerData(provinceGeo, false);
            fetchCityData('', selectedYear.value);
            scene.render();
            runNationalResetFlight();
            return;
          }

          const provinceBackdropGeo = buildProvinceBackdropGeo(prov);
          setProvinceLayerData(provinceBackdropGeo, true);
          scene.render();

          try {
            await fetchCityData(prov, selectedYear.value);
            if (gen !== drillGen) return;

            const geoRes = await fetchGeoJson(prov);
            if (gen !== drillGen) return;
            cityBaseSnapshot = cloneFeatureCollection(geoRes);
            citySnapshotProvince = prov;
            cityBaseSnapshot.features.forEach((f: any) => {
              rememberCityAdcode(f.properties?.name || '', f.properties?.adcode ?? '');
            });
            const cityGeo = restoreCityForegroundGeo();
            if (!cityGeo) throw new Error('city geo snapshot missing');
            setCityLayerData(cityGeo, false);
            scene.render();
            runCinematicFit(boundsFromFeatures(cityGeo.features));
            return;
          } catch (err) {
            console.error('缁胯壊閲戣瀺鍦板浘涓嬮捇澶辫触:', err);
            gfDrillProvince.value = '';
          }
        });
      }).catch((err) => {
        console.error('缁胯壊閲戣瀺鍦板浘鐪佺骇 GeoJSON 鍔犺浇澶辫触:', err);
      });
    });
  });
}

interface CarbonTooltipMetricsRow {
  city?: string;
  province?: string;
  carbonEmissionWanTon?: number;
  carbonEmission?: number;
  gdp?: number;
  primaryIndustry?: number | null;
  secondaryIndustry?: number | null;
  tertiaryIndustry?: number | null;
  primaryIndustryRatio?: number | null;
  secondaryIndustryRatio?: number | null;
  tertiaryIndustryRatio?: number | null;
}

export interface UseCarbonMapOptions {
  metric: Ref<'carbon' | 'gdp'>;
  selectedProvince: Ref<string>;
  cityRows: Ref<CarbonTooltipMetricsRow[]>;
  tooltipRef: Ref<CarbonMapTooltipState>;
  onProvinceClick?: (provinceName: string) => void;
}

function findCarbonProvinceRow(fullName: string): ProvinceGreenFinance | undefined {
  return realProvinceData.value.find(
    (row) =>
      row.province === fullName ||
      fullName.startsWith(row.province) ||
      row.province.startsWith(fullName),
  );
}

function findCarbonCityRow(
  geoName: string,
  rows: CarbonTooltipMetricsRow[],
): CarbonTooltipMetricsRow | undefined {
  const g = String(geoName || '').trim();
  if (!g) return undefined;
  return rows.find((row) => {
    const name = String(row?.city || '').trim();
    return name && (name === g || g.startsWith(name) || name.startsWith(g));
  });
}

function buildCarbonIndustryTooltipRows(row: CarbonTooltipMetricsRow | ProvinceGreenFinance | undefined) {
  return [
    { label: '第一产业增加值', value: formatTooltipMetricCell(row?.primaryIndustry, '亿元') },
    { label: '第二产业增加值', value: formatTooltipMetricCell(row?.secondaryIndustry, '亿元') },
    { label: '第三产业增加值', value: formatTooltipMetricCell(row?.tertiaryIndustry, '亿元') },
    { label: '第一产业占比', value: formatTooltipMetricCell(row?.primaryIndustryRatio, '%') },
    { label: '第二产业占比', value: formatTooltipMetricCell(row?.secondaryIndustryRatio, '%') },
    { label: '第三产业占比', value: formatTooltipMetricCell(row?.tertiaryIndustryRatio, '%') },
  ];
}

function buildCarbonMapTooltipAiPayload(
  regionName: string,
  mode: 'province' | 'city',
  metric: 'carbon' | 'gdp',
  dataPayload: Record<string, unknown>,
) {
  const tooltipScope = metric === 'gdp'
    ? (mode === 'province' ? 'carbonMapProvinceGdp' : 'carbonMapCityGdp')
    : (mode === 'province' ? 'carbonMapProvinceCarbon' : 'carbonMapCityCarbon');

  return {
    regionName,
    year: selectedYear.value,
    moduleName: 'carbon',
    tooltipScope,
    dataPayload,
  };
}

function applyCarbonMapTooltipAi(
  tooltipRef: Ref<CarbonMapTooltipState>,
  baseState: Omit<CarbonMapTooltipState, 'aiInsight' | 'aiLoading' | 'aiCacheKey'>,
  aiPayload: {
    regionName: string;
    year: number;
    moduleName: string;
    tooltipScope: string;
    dataPayload: Record<string, unknown>;
  },
) {
  const requestPromise = requestTooltipAi(aiPayload);
  const snapshot = getTooltipAiSnapshot(aiPayload);
  tooltipRef.value = {
    ...baseState,
    aiInsight: snapshot.content,
    aiLoading: snapshot.loading,
    aiCacheKey: snapshot.cacheKey,
  };

  void requestPromise.then((content) => {
    const current = tooltipRef.value;
    if (!current.visible || current.aiCacheKey !== snapshot.cacheKey) return;
    tooltipRef.value = {
      ...current,
      aiInsight: content,
      aiLoading: false,
    };
  });
}

function attachCarbonMapTooltip(
  layer: PolygonLayer,
  scene: Scene,
  mapAreaEl: HTMLElement,
  mapRootEl: HTMLElement,
  tooltipRef: Ref<CarbonMapTooltipState>,
  resolveTooltip: (name: string) => {
    baseState: Omit<CarbonMapTooltipState, 'visible' | 'left' | 'top' | 'aiInsight' | 'aiLoading' | 'aiCacheKey'>;
    aiPayload: {
      regionName: string;
      year: number;
      moduleName: string;
      tooltipScope: string;
      dataPayload: Record<string, unknown>;
    };
  } | null,
  shouldHandle?: (e: any) => boolean,
) {
  const OFFSET_X = 14;
  const OFFSET_Y = 14;

  const hide = () => {
    tooltipRef.value = createHiddenCarbonTooltip();
  };

  const onPick = (e: any) => {
    if (shouldHandle && !shouldHandle(e)) {
      hide();
      return;
    }
    const name = e.feature?.properties?.name;
    if (!name || isProvinceExcludedFromPanel(name)) {
      hide();
      return;
    }
    const ll = e.lngLat ?? e.lnglat;
    if (!ll) return;
    const lng = typeof ll.lng === 'number' ? ll.lng : ll[0];
    const lat = typeof ll.lat === 'number' ? ll.lat : ll[1];
    if (typeof lng !== 'number' || typeof lat !== 'number') return;

    const resolved = resolveTooltip(name);
    if (!resolved) {
      hide();
      return;
    }

    const pt = scene.lngLatToContainer([lng, lat]);
    const areaR = mapAreaEl.getBoundingClientRect();
    const mapR = mapRootEl.getBoundingClientRect();
    const left = mapR.left - areaR.left + pt.x + OFFSET_X;
    const top = mapR.top - areaR.top + pt.y + OFFSET_Y;

    applyCarbonMapTooltipAi(tooltipRef, {
      ...resolved.baseState,
      visible: true,
      left,
      top,
    }, resolved.aiPayload);
  };

  layer.on('mouseenter', onPick);
  layer.on('mousemove', onPick);
  layer.on('mouseout', hide);

  return { hide };
}

function metricValueFromProvinceRow(
  row: { carbonEmission?: number; gdp?: number },
  metric: 'carbon' | 'gdp',
): number {
  if (metric === 'gdp') return Number(row.gdp ?? 0);
  return Number((row.carbonEmission ?? 0) / 10000);
}

function metricValueFromCityRow(
  row: { carbonEmissionWanTon?: number; carbonEmission?: number; gdp?: number },
  metric: 'carbon' | 'gdp',
): number {
  if (metric === 'gdp') return Number(row.gdp ?? 0);
  return Number(row.carbonEmissionWanTon ?? row.carbonEmission ?? 0);
}

function matchCarbonValue(
  geoName: string,
  rows: Array<Record<string, any>>,
  nameKey: 'city',
  metric: 'carbon' | 'gdp',
): { value: number; hasData: boolean } {
  const g = String(geoName || '').trim();
  if (!g) return { value: 0, hasData: false };
  const row = rows.find((item) => {
    const name = String(item?.[nameKey] || '').trim();
    return name && (name === g || g.startsWith(name) || name.startsWith(g));
  });
  if (!row) return { value: 0, hasData: false };
  const value = metricValueFromCityRow(row, metric);
  return { value: Number.isFinite(value) ? value : 0, hasData: true };
}

function buildCarbonMapTooltipContent(
  regionName: string,
  mode: 'province' | 'city',
  metric: 'carbon' | 'gdp',
  cityRows: CarbonTooltipMetricsRow[],
) {
  if (metric === 'gdp') {
    const row = mode === 'province'
      ? findCarbonProvinceRow(regionName)
      : findCarbonCityRow(regionName, cityRows);
    const gdp = row ? Number(row.gdp ?? 0) : null;
    const rows = buildCarbonIndustryTooltipRows(row);
    return {
      baseState: {
        regionName,
        year: selectedYear.value,
        headlineLabel: 'GDP 总量',
        headlineValue: formatTooltipMetricNumber(gdp),
        headlineUnit: '亿元',
        rows,
        mode,
        metric,
      },
      aiPayload: buildCarbonMapTooltipAiPayload(regionName, mode, metric, {
        metric,
        level: mode,
        regionName,
        gdp,
        primaryIndustry: row?.primaryIndustry ?? null,
        secondaryIndustry: row?.secondaryIndustry ?? null,
        tertiaryIndustry: row?.tertiaryIndustry ?? null,
        primaryIndustryRatio: row?.primaryIndustryRatio ?? null,
        secondaryIndustryRatio: row?.secondaryIndustryRatio ?? null,
        tertiaryIndustryRatio: row?.tertiaryIndustryRatio ?? null,
      }),
    };
  }

  if (mode === 'province') {
    const row = findCarbonProvinceRow(regionName);
    const carbonEmissionWanTon = row ? metricValueFromProvinceRow(row, 'carbon') : null;
    return {
      baseState: {
        regionName,
        year: selectedYear.value,
        headlineLabel: '碳排放总量',
        headlineValue: formatTooltipMetricNumber(carbonEmissionWanTon),
        headlineUnit: '万吨',
        rows: [],
        mode,
        metric,
      },
      aiPayload: buildCarbonMapTooltipAiPayload(regionName, mode, metric, {
        metric,
        level: mode,
        regionName,
        carbonEmissionWanTon,
      }),
    };
  }

  const row = findCarbonCityRow(regionName, cityRows);
  const carbonEmissionWanTon = row ? metricValueFromCityRow(row, 'carbon') : null;
  return {
    baseState: {
      regionName,
      year: selectedYear.value,
      headlineLabel: '碳排放总量',
      headlineValue: formatTooltipMetricNumber(carbonEmissionWanTon),
      headlineUnit: '万吨',
      rows: [],
      mode,
      metric,
    },
    aiPayload: buildCarbonMapTooltipAiPayload(regionName, mode, metric, {
      metric,
      level: mode,
      regionName,
      carbonEmissionWanTon,
    }),
  };
}

export function useCarbonMap(options: UseCarbonMapOptions) {
  onMounted(() => {
    const scene = new Scene({
      id: 'carbon-map',
      map: new Map({
        pitch: 45,
        style: 'dark',
        center: [104.195397, 35.86166],
        zoom: 3.2,
      }),
    });
    scene.setBgColor('#131722');
    scene.on('loaded', () => {
      const mapEl = document.getElementById('carbon-map');
      if (mapEl) mapEl.style.background = '#131722';
      const mapAreaEl = mapEl?.parentElement instanceof HTMLElement ? mapEl.parentElement : null;
      const nativeMap = scene.getMapService?.()?.map || scene.map;

      nativeMap?.doubleClickZoom?.disable?.();

      let cityExtrudeLayer: PolygonLayer | null = null;
      let provinceTopOutlineLayer: LineLayer | null = null;
      let cityTopOutlineLayer: LineLayer | null = null;
      let cityBaseSnapshot: { type: string; features: any[] } | null = null;
      let cityFullSnapshot: { type: string; features: any[] } | null = null;
      let citySnapshotProvince = '';
      let drillGen = 0;

      const runNextFrame = (cb: () => void) => {
        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
          window.requestAnimationFrame(cb);
          return;
        }
        setTimeout(cb, 16);
      };

      const runCinematicFit = (bounds: [[number, number], [number, number]] | null) => {
        if (!bounds) return;
        runNextFrame(() => {
          nativeMap?.stop?.();
          if (nativeMap?.fitBounds) {
            nativeMap.fitBounds(bounds, {
              padding: GF_CINEMATIC_PADDING,
              ...GF_CINEMATIC_DRILL_CAMERA,
            });
            return;
          }
          scene.fitBounds(bounds, {
            padding: 80,
            duration: GF_CINEMATIC_DRILL_CAMERA.duration,
          });
          scene.setPitch(GF_CINEMATIC_DRILL_CAMERA.pitch);
          scene.setRotation?.(GF_CINEMATIC_DRILL_CAMERA.bearing);
        });
      };

      const runNationalResetFlight = () => {
        runNextFrame(() => {
          nativeMap?.stop?.();
          if (nativeMap?.flyTo) {
            nativeMap.flyTo({ ...GF_CINEMATIC_RESET_CAMERA });
            return;
          }
          scene.setZoomAndCenter(GF_CINEMATIC_RESET_CAMERA.zoom, GF_CINEMATIC_RESET_CAMERA.center);
          scene.setPitch(GF_CINEMATIC_RESET_CAMERA.pitch);
          scene.setRotation?.(GF_CINEMATIC_RESET_CAMERA.bearing);
        });
      };

      const stepOutOneLevel = () => {
        options.tooltipRef.value = createHiddenCarbonTooltip();
        if (options.selectedProvince.value) {
          options.onProvinceClick?.('');
        }
      };

      fetchCountryGeoJson().then((geoData) => {
        const features = geoData.features.filter((f) => f.properties.name);
        const noPanelFeats = features.filter((f) => isProvinceExcludedFromPanel(f.properties.name));
        const mainFeats = features.filter((f) => !isProvinceExcludedFromPanel(f.properties.name));
        const fullOutlineGeo = { type: 'FeatureCollection', features };
        const provinceBaseSnapshot = cloneFeatureCollection({ type: 'FeatureCollection', features: mainFeats });

        const noPanelFillGeo = { type: 'FeatureCollection', features: noPanelFeats };
        const noPanelFill = new PolygonLayer({ zIndex: 4 })
          .source(noPanelFillGeo)
          .shape('fill')
          .color('#5c6470')
          .style({ opacity: 0.95 });
        scene.addLayer(noPanelFill);

        const applyMetricToProvinceFc = (fc: { features: any[] }) => {
          const metric = options.metric.value;
          const valueMap = metric === 'gdp' ? buildProvinceGdpMap() : buildCarbonMapWanTon();
          const maxValue = Math.max(...Object.values(valueMap), 0);
          fc.features.forEach((f) => {
            const value = valueMap[f.properties?.name || ''] || 0;
            const hasData = Number.isFinite(value) && value > 0;
            f.properties._score = hasData ? value : CARBON_MUTED_SCORE;
            f.properties._rawValue = value;
            f.properties._hasData = hasData;
            f.properties._color = hasData ? carbonRampColor(value, maxValue) : COUNTY_NO_DATA_COLOR;
            f.properties._isBackdrop = false;
          });
        };

        const applyMetricToCityFc = (fc: { features: any[] }) => {
          const metric = options.metric.value;
          const rows = options.cityRows.value as Array<Record<string, any>>;
          const maxValue = Math.max(
            ...rows.map((row) => metricValueFromCityRow(row, metric)).filter(Number.isFinite),
            0,
          );
          fc.features.forEach((f) => {
            const { value, hasData } = matchCarbonValue(f.properties?.name || '', rows, 'city', metric);
            f.properties._score = hasData ? value : 0.001;
            f.properties._rawValue = value;
            f.properties._hasData = hasData;
            f.properties._color = hasData ? carbonRampColor(value, maxValue) : COUNTY_NO_DATA_COLOR;
            f.properties._isBackdrop = false;
          });
        };

        const buildMetricProvinceGeo = () => {
          const fc = cloneFeatureCollection(provinceBaseSnapshot);
          applyMetricToProvinceFc(fc);
          return fc;
        };

        let provinceFullSnapshot = buildMetricProvinceGeo();

        const restoreProvinceForegroundGeo = () => {
          const fc = buildMetricProvinceGeo();
          provinceFullSnapshot = cloneFeatureCollection(fc);
          return fc;
        };

        const buildProvinceBackdropGeo = (selectedProvince: string) => {
          const fc = buildMetricProvinceGeo();
          provinceFullSnapshot = cloneFeatureCollection(fc);
          fc.features = fc.features
            .filter((f) => f.properties?.name !== selectedProvince)
            .map((f) => ({
              ...f,
              properties: {
                ...(f.properties || {}),
                _score: GF_BACKDROP_SCORE,
                _rawValue: 0,
                _color: GF_BACKDROP_COLOR,
                _isBackdrop: true,
              },
            }));
          return fc;
        };

        const provinceGeo = restoreProvinceForegroundGeo();

        const provinceFillLayer = new PolygonLayer({ zIndex: 5 })
          .source(provinceGeo)
          .shape('extrude')
          .size('_score', GF_PROVINCE_EXTRUDE_RANGE)
          .color('_color')
          .style({ heightfixed: true, pickLight: true, opacity: CARBON_FILL_OPACITY })
          .active({ color: GF_ACTIVE_COLOR });
        scene.addLayer(provinceFillLayer);
        provinceTopOutlineLayer = new LineLayer({ zIndex: 15 })
          .source(buildExtrudeTopOutlines(provinceGeo, GF_PROVINCE_EXTRUDE_RANGE))
          .shape('line')
          .color(GF_EXTRUDE_TOP_LINE_COLOR)
          .size(GF_EXTRUDE_TOP_LINE_WIDTH)
          .style({
            opacity: 0.94,
            heightfixed: true,
            vertexHeightScale: 1,
            depth: true,
          });
        scene.addLayer(provinceTopOutlineLayer);

        provinceFillLayer.on('click', (e) => {
          if (options.selectedProvince.value) return;
          const name = e.feature?.properties?.name;
          if (name && !isProvinceExcludedFromPanel(name) && e.feature?.properties?._isBackdrop !== true) {
            options.onProvinceClick?.(name);
          }
        });
        if (mapAreaEl && mapEl) {
          attachCarbonMapTooltip(
            provinceFillLayer,
            scene,
            mapAreaEl,
            mapEl,
            options.tooltipRef,
            (name) => buildCarbonMapTooltipContent(name, 'province', options.metric.value, options.cityRows.value),
            () => !options.selectedProvince.value,
          );
          mapEl.addEventListener('mouseleave', () => {
            options.tooltipRef.value = createHiddenCarbonTooltip();
          });
        }

        const provinceBoundaryLayer = new LineLayer({ zIndex: 10 })
          .source(fullOutlineGeo)
          .shape('line')
          .color(CARBON_PROVINCE_BOUNDARY_COLOR)
          .size(CARBON_PROVINCE_BOUNDARY_WIDTH)
          .style({ opacity: 0.75 });
        scene.addLayer(provinceBoundaryLayer);

        const setProvinceLayerData = (fc: { type: string; features: any[] }, backdrop = false) => {
          const nextGeo = cloneFeatureCollection(fc);
          provinceFillLayer.setData(nextGeo);
          if (backdrop) {
            provinceFillLayer.color('_color');
            provinceFillLayer.active(false);
            provinceTopOutlineLayer?.color(GF_BACKDROP_TOP_LINE_COLOR);
            provinceBoundaryLayer.color(CARBON_PROVINCE_BOUNDARY_BACKDROP_COLOR);
            provinceBoundaryLayer.style({ opacity: 0.45 });
            noPanelFill.color('rgba(92,100,112,0.72)');
            noPanelFill.style({ opacity: 0.72 });
          } else {
            provinceFillLayer.color('_color');
            provinceFillLayer.active({ color: GF_ACTIVE_COLOR });
            provinceTopOutlineLayer?.color(GF_EXTRUDE_TOP_LINE_COLOR);
            provinceBoundaryLayer.color(CARBON_PROVINCE_BOUNDARY_COLOR);
            provinceBoundaryLayer.style({ opacity: 0.75 });
            noPanelFill.color('#5c6470');
            noPanelFill.style({ opacity: 0.95 });
          }
          provinceTopOutlineLayer?.setData(buildExtrudeTopOutlines(nextGeo, GF_PROVINCE_EXTRUDE_RANGE));
          provinceFillLayer.show();
          provinceTopOutlineLayer?.show();
          provinceBoundaryLayer.show();
        };

        const restoreCityForegroundGeo = () => {
          if (!cityBaseSnapshot) return null;
          const fc = cloneFeatureCollection(cityBaseSnapshot);
          applyMetricToCityFc(fc);
          cityFullSnapshot = cloneFeatureCollection(fc);
          return fc;
        };

        const ensureCityLayers = (fc: { type: string; features: any[] }) => {
          if (!cityExtrudeLayer) {
            cityExtrudeLayer = new PolygonLayer({ zIndex: 6 })
              .source(fc)
              .shape('extrude')
              .size('_score', GF_CITY_EXTRUDE_RANGE)
              .color('_color')
              .style({ heightfixed: true, pickLight: true, opacity: CARBON_FILL_OPACITY })
              .active({ color: GF_ACTIVE_COLOR });
            scene.addLayer(cityExtrudeLayer);
            if (mapAreaEl && mapEl) {
              attachCarbonMapTooltip(
                cityExtrudeLayer,
                scene,
                mapAreaEl,
                mapEl,
                options.tooltipRef,
                (name) => buildCarbonMapTooltipContent(name, 'city', options.metric.value, options.cityRows.value),
                () => !!options.selectedProvince.value,
              );
            }
          }
          if (!cityTopOutlineLayer) {
            cityTopOutlineLayer = new LineLayer({ zIndex: 16 })
              .source(buildExtrudeTopOutlines(fc, GF_CITY_EXTRUDE_RANGE))
              .shape('line')
              .color(GF_EXTRUDE_TOP_LINE_COLOR)
              .size(GF_EXTRUDE_TOP_LINE_WIDTH)
              .style({
                opacity: 0.94,
                heightfixed: true,
                vertexHeightScale: 1,
                depth: true,
              });
            scene.addLayer(cityTopOutlineLayer);
          }
        };

        const setCityLayerData = (fc: { type: string; features: any[] }, backdrop = false) => {
          ensureCityLayers(fc);
          const nextGeo = cloneFeatureCollection(fc);
          cityExtrudeLayer?.setData(nextGeo);
          if (backdrop) {
            cityExtrudeLayer?.active(false);
            cityTopOutlineLayer?.color(GF_BACKDROP_TOP_LINE_COLOR);
          } else {
            cityExtrudeLayer?.active({ color: GF_ACTIVE_COLOR });
            cityTopOutlineLayer?.color(GF_EXTRUDE_TOP_LINE_COLOR);
          }
          cityTopOutlineLayer?.setData(buildExtrudeTopOutlines(nextGeo, GF_CITY_EXTRUDE_RANGE));
          cityExtrudeLayer?.show();
          cityTopOutlineLayer?.show();
        };

        watch(
          [realProvinceData, options.metric],
          () => {
            options.tooltipRef.value = createHiddenCarbonTooltip();
            const nextGeo = options.selectedProvince.value
              ? buildProvinceBackdropGeo(options.selectedProvince.value)
              : restoreProvinceForegroundGeo();
            setProvinceLayerData(nextGeo, !!options.selectedProvince.value);
            scene.render();
          },
          { deep: true, immediate: true },
        );

        watch(
          [options.cityRows, options.metric],
          () => {
            if (!options.selectedProvince.value || !cityBaseSnapshot || citySnapshotProvince !== options.selectedProvince.value) return;
            options.tooltipRef.value = createHiddenCarbonTooltip();
            const nextGeo = restoreCityForegroundGeo();
            if (!nextGeo) return;
            setCityLayerData(nextGeo, false);
            scene.render();
          },
          { deep: true },
        );

        watch(
          [options.metric, options.selectedProvince],
          () => {
            options.tooltipRef.value = createHiddenCarbonTooltip();
          },
          { immediate: true },
        );

        scene.on('contextmenu', (e: any) => {
          e?.preventDefault?.();
          e?.originalEvent?.preventDefault?.();
          stepOutOneLevel();
        });

        scene.on('dblclick', (e: any) => {
          e?.preventDefault?.();
          e?.originalEvent?.preventDefault?.();
          if (e?.feature) return;
          stepOutOneLevel();
        });

        watch(
          options.selectedProvince,
          async (prov) => {
            const gen = ++drillGen;
            options.tooltipRef.value = createHiddenCarbonTooltip();

            if (!prov) {
              cityExtrudeLayer?.hide();
              cityTopOutlineLayer?.hide();
              cityBaseSnapshot = null;
              cityFullSnapshot = null;
              citySnapshotProvince = '';
              const provinceGeo = restoreProvinceForegroundGeo();
              setProvinceLayerData(provinceGeo, false);
              scene.render();
              runNationalResetFlight();
              return;
            }

            const provinceBackdropGeo = buildProvinceBackdropGeo(prov);
            setProvinceLayerData(provinceBackdropGeo, true);
            scene.render();

            try {
              const geoRes = await fetchGeoJson(prov);
              if (gen !== drillGen) return;
              cityBaseSnapshot = cloneFeatureCollection(geoRes);
              citySnapshotProvince = prov;
              cityBaseSnapshot.features.forEach((f: any) => {
                rememberCityAdcode(f.properties?.name || '', f.properties?.adcode ?? '');
              });
              const cityGeo = restoreCityForegroundGeo();
              if (!cityGeo) throw new Error('city geo snapshot missing');
              setCityLayerData(cityGeo, false);
              scene.render();
              runCinematicFit(boundsFromFeatures(cityGeo.features));
            } catch (err) {
              console.error('纰虫帓鏀惧湴鍥惧競绾т笅閽诲け璐?', err);
              options.onProvinceClick?.('');
            }
          },
          { immediate: true },
        );
      }).catch((err) => {
        console.error('纰虫帓鍦板浘鐪佺骇 GeoJSON 鍔犺浇澶辫触:', err);
      });
    });
  });
}

export default {};
