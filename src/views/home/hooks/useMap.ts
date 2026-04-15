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
  fetchCountyGeoJson,
  fetchCountyData,
  realCityData,
  realCountyData,
  selectedYear,
  gfDrillProvince,
  gfDrillCity,
  gfRadarCityHoverGeoName,
  rememberCityAdcode,
  isProvinceExcludedFromPanel,
  indicatorKeys,
  indicatorLabels,
  type ProvinceGreenFinance,
} from './provinceData';

/** 绿色金融地图悬停浮框（Vue 与 useGreenFinanceMap 共用） */
export interface GfMapTooltipState {
  visible: boolean;
  left: number;
  top: number;
  regionName: string;
  year: number;
  scoreText: string;
  rows: { label: string; value: string }[];
  mode: 'province' | 'city' | 'county';
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
  };
}

/** 七维与综合指数一致：库内为 0～1，展示为百分制，保留 2 位小数 */
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

function findCountyRow(geoName: string): ProvinceGreenFinance | undefined {
  const g = String(geoName || '').trim();
  if (!g) return undefined;
  return realCountyData.value.find(
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

function attachGreenFinanceMapTooltip(
  layer: PolygonLayer,
  scene: Scene,
  mapAreaEl: HTMLElement,
  mapRootEl: HTMLElement,
  tooltipRef: Ref<GfMapTooltipState>,
  mode: 'province' | 'city' | 'county',
  shouldHandle?: (e: any) => boolean,
) {
  const OFFSET_X = 14;
  const OFFSET_Y = 14;

  const applyPayload = (name: string, lng: number, lat: number, hasData = true) => {
    const pt = scene.lngLatToContainer([lng, lat]);
    const areaR = mapAreaEl.getBoundingClientRect();
    const mapR = mapRootEl.getBoundingClientRect();
    const left = mapR.left - areaR.left + pt.x + OFFSET_X;
    const top = mapR.top - areaR.top + pt.y + OFFSET_Y;
    const row = mode === 'province'
      ? findProvinceRow(name)
      : mode === 'city'
        ? findCityRow(name)
        : hasData
          ? findCountyRow(name)
          : undefined;
    tooltipRef.value = {
      visible: true,
      left,
      top,
      regionName: name,
      year: selectedYear.value,
      scoreText: scoreToDisplayText(row),
      rows: buildTooltipRowsFromRow(row),
      mode,
    };
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
    const hasData = mode !== 'county' || e.feature?.properties?._hasData !== false;
    applyPayload(name, lng, lat, hasData);
  };

  layer.on('mouseenter', onPick);
  layer.on('mousemove', onPick);
  layer.on('mouseout', hide);

  return { hide };
}

/** 绿金 3D 柱体顶面外轮廓白线（与柱顶同高，区分邻省/市） */
const GF_EXTRUDE_TOP_LINE_COLOR = 'rgba(255,255,255,0.9)';
const GF_EXTRUDE_TOP_LINE_WIDTH = 1.15;
const GF_BACKDROP_COLOR = 'rgba(40, 50, 70, 0.4)';
const GF_BACKDROP_TOP_LINE_COLOR = 'rgba(180, 196, 220, 0.3)';
const GF_BACKDROP_SCORE = 100;
/** 与 PolygonLayer `.size('_score', range)` 一致 */
const GF_PROVINCE_EXTRUDE_RANGE: [number, number] = [20000, 2000000];
const GF_CITY_EXTRUDE_RANGE: [number, number] = [12000, 1800000];
const GF_COUNTY_EXTRUDE_RANGE: [number, number] = [8000, 1000000];
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
const CARBON_PROVINCE_EXTRUDE_RANGE: [number, number] = [20000, 2000000];
const CARBON_CITY_EXTRUDE_RANGE: [number, number] = [12000, 1800000];
const CARBON_COUNTY_EXTRUDE_RANGE: [number, number] = [8000, 1000000];
const CARBON_MUTED_SCORE = 0.001;
const CARBON_DRILL_HIT_COLOR = 'rgba(40, 50, 70, 0.06)';
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

/** 与 L7 对 `_score` 线性映射到柱高（米）的规则对齐 */
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

/** 多边形外环 → 带统一 Z（柱顶高度米）的 LineString，供 LineLayer 绘制顶边 */
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
      let countyExtrudeLayer: PolygonLayer | null = null;
      let provinceTopOutlineLayer: LineLayer | null = null;
      let cityTopOutlineLayer: LineLayer | null = null;
      let countyTopOutlineLayer: LineLayer | null = null;
      let cityBaseSnapshot: { type: string; features: any[] } | null = null;
      let cityFullSnapshot: { type: string; features: any[] } | null = null;
      let countyBaseSnapshot: { type: string; features: any[] } | null = null;
      let countyFullSnapshot: { type: string; features: any[] } | null = null;
      let citySnapshotProvince = '';
      let countySnapshotCity = '';
      let drillGen = 0;
      let countyDrillGen = 0;

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
        if (gfDrillCity.value) {
          gfDrillCity.value = '';
          return;
        }
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
        let countyExtrudeLayer: PolygonLayer | null = null;
        let cityTopOutlineLayer: LineLayer | null = null;
        let countyTopOutlineLayer: LineLayer | null = null;
        let cityBaseSnapshot: { type: string; features: any[] } | null = null;
        let cityFullSnapshot: { type: string; features: any[] } | null = null;
        let countyBaseSnapshot: { type: string; features: any[] } | null = null;
        let countyFullSnapshot: { type: string; features: any[] } | null = null;
        let citySnapshotProvince = '';
        let countySnapshotCity = '';
        let drillGen = 0;
        let countyDrillGen = 0;

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
          [selectedYear, realProvinceData, realCityData, realCountyData],
          () => {
            const t = tooltipRef.value;
            if (!t.visible || !t.regionName) return;
            const row = t.mode === 'province'
              ? findProvinceRow(t.regionName)
              : t.mode === 'city'
                ? findCityRow(t.regionName)
                : findCountyRow(t.regionName);
            tooltipRef.value = {
              ...t,
              year: selectedYear.value,
              scoreText: scoreToDisplayText(row),
              rows: buildTooltipRowsFromRow(row),
            };
          },
          { deep: true },
        );

        watch(gfDrillProvince, () => {
          gfDrillCity.value = '';
          realCountyData.value = [];
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

        const applyCountyScoresToFc = (fc: { features: any[] }) => {
          const rows = realCountyData.value;
          fc.features.forEach((f) => {
            const geoName = String(f.properties?.name || '').trim();
            const row = rows.find(
              (r) => r.province === geoName || geoName.startsWith(r.province) || r.province.startsWith(geoName),
            );
            if (row) {
              f.properties._hasData = true;
              f.properties._rawScore = row.score;
              f.properties._score = row.score ** 1.5;
              f.properties._color = scoreToColor(row.score);
            } else {
              f.properties._hasData = false;
              f.properties._rawScore = 0;
              f.properties._score = 0.001;
              f.properties._color = COUNTY_NO_DATA_COLOR;
            }
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

        const buildCityBackdropGeo = (selectedCity: string) => {
          if (!cityFullSnapshot) return null;
          const fc = cloneFeatureCollection(cityFullSnapshot);
          fc.features = fc.features
            .filter((f) => f.properties?.name !== selectedCity)
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

        const restoreCountyForegroundGeo = () => {
          if (!countyBaseSnapshot) return null;
          const fc = cloneFeatureCollection(countyBaseSnapshot);
          applyCountyScoresToFc(fc);
          countyFullSnapshot = cloneFeatureCollection(fc);
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
            cityExtrudeLayer.on('click', (e) => {
              if (!gfDrillProvince.value || gfDrillCity.value) return;
              const name = e.feature?.properties?.name;
              if (name && e.feature?.properties?._isBackdrop !== true) {
                gfDrillCity.value = name;
              }
            });
            if (mapAreaEl && mapEl) {
              attachGreenFinanceMapTooltip(
                cityExtrudeLayer,
                scene,
                mapAreaEl,
                mapEl,
                tooltipRef,
                'city',
                () => !!gfDrillProvince.value && !gfDrillCity.value,
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

        const ensureCountyLayers = (fc: { type: string; features: any[] }) => {
          if (!countyExtrudeLayer) {
            countyExtrudeLayer = new PolygonLayer({ zIndex: 7 })
              .source(fc)
              .shape('extrude')
              .size('_score', GF_COUNTY_EXTRUDE_RANGE)
              .color('_color')
              .style({ heightfixed: true, pickLight: true, opacity: 0.88 })
              .active({ color: GF_ACTIVE_COLOR });
            scene.addLayer(countyExtrudeLayer);
            if (mapAreaEl && mapEl) {
              attachGreenFinanceMapTooltip(
                countyExtrudeLayer,
                scene,
                mapAreaEl,
                mapEl,
                tooltipRef,
                'county',
                () => !!gfDrillProvince.value && !!gfDrillCity.value,
              );
            }
          }
          if (!countyTopOutlineLayer) {
            countyTopOutlineLayer = new LineLayer({ zIndex: 17 })
              .source(buildExtrudeTopOutlines(fc, GF_COUNTY_EXTRUDE_RANGE))
              .shape('line')
              .color(GF_EXTRUDE_TOP_LINE_COLOR)
              .size(GF_EXTRUDE_TOP_LINE_WIDTH)
              .style({
                opacity: 0.94,
                heightfixed: true,
                vertexHeightScale: 1,
                depth: true,
              });
            scene.addLayer(countyTopOutlineLayer);
          }
        };

        const setCountyLayerData = (fc: { type: string; features: any[] }) => {
          ensureCountyLayers(fc);
          const nextGeo = cloneFeatureCollection(fc);
          countyExtrudeLayer?.setData(nextGeo);
          countyTopOutlineLayer?.setData(buildExtrudeTopOutlines(nextGeo, GF_COUNTY_EXTRUDE_RANGE));
          countyExtrudeLayer?.active({ color: GF_ACTIVE_COLOR });
          countyTopOutlineLayer?.color(GF_EXTRUDE_TOP_LINE_COLOR);
          countyExtrudeLayer?.show();
          countyTopOutlineLayer?.show();
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
            const nextGeo = gfDrillCity.value ? buildCityBackdropGeo(gfDrillCity.value) : restoreCityForegroundGeo();
            if (!nextGeo) return;
            setCityLayerData(nextGeo, !!gfDrillCity.value);
          },
          { deep: true },
        );

        watch(
          realCountyData,
          () => {
            if (!gfDrillCity.value || !countyBaseSnapshot || countySnapshotCity !== gfDrillCity.value) return;
            const countyGeo = restoreCountyForegroundGeo();
            if (!countyGeo) return;
            setCountyLayerData(countyGeo);
          },
          { deep: true },
        );

        watch(selectedYear, () => {
          if (!gfDrillProvince.value || !gfDrillCity.value) return;
          fetchCountyData(gfDrillProvince.value, gfDrillCity.value, selectedYear.value);
        });

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

        watch(gfDrillCity, async (city) => {
          const gen = ++countyDrillGen;
          tooltipRef.value = createHiddenGfTooltip();
          gfRadarCityHoverGeoName.value = '';

          if (!city) {
            countyExtrudeLayer?.hide();
            countyTopOutlineLayer?.hide();
            countyBaseSnapshot = null;
            countyFullSnapshot = null;
            countySnapshotCity = '';
            if (!gfDrillProvince.value || !cityBaseSnapshot || citySnapshotProvince !== gfDrillProvince.value) {
              scene.render();
              return;
            }
            const cityGeo = restoreCityForegroundGeo();
            if (!cityGeo) {
              scene.render();
              return;
            }
            setCityLayerData(cityGeo, false);
            scene.render();
            runCinematicFit(boundsFromFeatures(cityGeo.features));
            return;
          }

          const prov = gfDrillProvince.value;
          if (!prov || !cityBaseSnapshot || citySnapshotProvince !== prov) {
            gfDrillCity.value = '';
            return;
          }

          const cityBackdropGeo = buildCityBackdropGeo(city);
          if (!cityBackdropGeo) {
            gfDrillCity.value = '';
            return;
          }

          setCityLayerData(cityBackdropGeo, true);
          countyExtrudeLayer?.hide();
          countyTopOutlineLayer?.hide();
          countyBaseSnapshot = null;
          countyFullSnapshot = null;
          countySnapshotCity = '';
          scene.render();

          try {
            const [geoRes] = await Promise.all([
              fetchCountyGeoJson(city),
              fetchCountyData(prov, city, selectedYear.value),
            ]);
            if (gen !== countyDrillGen) return;

            countyBaseSnapshot = cloneFeatureCollection(geoRes);
            countySnapshotCity = city;
            const countyGeo = restoreCountyForegroundGeo();
            if (!countyGeo) throw new Error('county geo snapshot missing');
            setCountyLayerData(countyGeo);
            scene.render();
            runCinematicFit(boundsFromFeatures(countyGeo.features));
            return;
          } catch (err) {
            console.error('绿色金融地图县级下钻失败:', err);
            if (gen !== countyDrillGen) return;
            gfDrillCity.value = '';
          }
        });

        watch(gfDrillProvince, async (prov) => {
          const gen = ++drillGen;
          countyDrillGen += 1;
          countyExtrudeLayer?.hide();
          countyTopOutlineLayer?.hide();
          countyBaseSnapshot = null;
          countyFullSnapshot = null;
          countySnapshotCity = '';

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
            console.error('绿色金融地图下钻失败:', err);
            gfDrillProvince.value = '';
          }
        });
      }).catch((err) => {
        console.error('绿色金融地图省级 GeoJSON 加载失败:', err);
      });
    });
  });
}

export interface UseCarbonMapOptions {
  selectedProvince: Ref<string>;
  selectedCity: Ref<string>;
  cityRows: Ref<Array<{ city: string; carbonEmissionWanTon?: number; carbonEmission?: number }>>;
  countyRows: Ref<Array<{ county: string; carbonEmissionWanTon?: number; carbonEmission?: number }>>;
  onProvinceClick?: (provinceName: string) => void;
  onCityClick?: (cityName: string) => void;
}

function matchCarbonValue(
  geoName: string,
  rows: Array<Record<string, any>>,
  nameKey: 'city' | 'county',
): { value: number; hasData: boolean } {
  const g = String(geoName || '').trim();
  if (!g) return { value: 0, hasData: false };
  const row = rows.find((item) => {
    const name = String(item?.[nameKey] || '').trim();
    return name && (name === g || g.startsWith(name) || name.startsWith(g));
  });
  if (!row) return { value: 0, hasData: false };
  const value = Number(row.carbonEmissionWanTon ?? row.carbonEmission ?? 0);
  return { value: Number.isFinite(value) ? value : 0, hasData: true };
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
      const nativeMap = scene.getMapService?.()?.map || scene.map;

      nativeMap?.doubleClickZoom?.disable?.();

      let cityExtrudeLayer: PolygonLayer | null = null;
      let countyExtrudeLayer: PolygonLayer | null = null;
      let cityTopOutlineLayer: LineLayer | null = null;
      let countyTopOutlineLayer: LineLayer | null = null;
      let cityBaseSnapshot: { type: string; features: any[] } | null = null;
      let cityFullSnapshot: { type: string; features: any[] } | null = null;
      let countyBaseSnapshot: { type: string; features: any[] } | null = null;
      let countyFullSnapshot: { type: string; features: any[] } | null = null;
      let citySnapshotProvince = '';
      let countySnapshotCity = '';
      let selectedCountyName = '';
      let drillGen = 0;
      let countyDrillGen = 0;

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

        const applyCarbonToFc = (fc: { features: any[] }) => {
          const carbonMap = buildCarbonMapWanTon();
          fc.features.forEach((f) => {
            const carbon = carbonMap[f.properties?.name || ''] || 0;
            f.properties._score = carbon;
            f.properties._rawCarbon = carbon;
            f.properties._color = '';
            f.properties._isBackdrop = false;
          });
        };

        const applyCityCarbonToFc = (fc: { features: any[] }) => {
          const rows = options.cityRows.value as Array<Record<string, any>>;
          fc.features.forEach((f) => {
            const { value, hasData } = matchCarbonValue(f.properties?.name || '', rows, 'city');
            f.properties._score = hasData ? value : 0.001;
            f.properties._rawCarbon = value;
            f.properties._hasData = hasData;
            f.properties._color = hasData ? '' : COUNTY_NO_DATA_COLOR;
            f.properties._isBackdrop = false;
          });
        };

        const applyCountyCarbonToFc = (fc: { features: any[] }) => {
          const rows = options.countyRows.value as Array<Record<string, any>>;
          fc.features.forEach((f) => {
            const { value, hasData } = matchCarbonValue(f.properties?.name || '', rows, 'county');
            f.properties._score = hasData ? value : 0.001;
            f.properties._rawCarbon = value;
            f.properties._hasData = hasData;
            f.properties._color = hasData ? '' : COUNTY_NO_DATA_COLOR;
            f.properties._isBackdrop = false;
          });
        };

        const applySelectedCarbonStyle = (
          fc: { features: any[] },
          selectedName = '',
          mutedColor = GF_BACKDROP_COLOR,
        ) => {
          const maxCarbon = Math.max(
            ...fc.features.map((f) => {
              const hasData = f.properties?._hasData !== false;
              const value = Number(f.properties?._rawCarbon || 0);
              return hasData && Number.isFinite(value) ? value : 0;
            }),
            0,
          );

          fc.features.forEach((f) => {
            const props = f.properties || {};
            const hasData = props._hasData !== false;
            const rawCarbon = Number(props._rawCarbon || 0);
            const isSelected = !!selectedName && regionNameMatches(props.name || '', selectedName);
            f.properties = {
              ...props,
              _score: isSelected && hasData ? Math.max(rawCarbon, CARBON_MUTED_SCORE) : CARBON_MUTED_SCORE,
              _color: isSelected && hasData
                ? carbonRampColor(rawCarbon, maxCarbon)
                : selectedName && !hasData
                  ? COUNTY_NO_DATA_COLOR
                  : mutedColor,
              _isBackdrop: !isSelected,
              _isSelected: isSelected,
            };
          });
        };

        const buildCarbonProvinceGeo = () => {
          const fc = cloneFeatureCollection(provinceBaseSnapshot);
          applyCarbonToFc(fc);
          return fc;
        };

        let provinceFullSnapshot = buildCarbonProvinceGeo();

        const restoreProvinceForegroundGeo = () => {
          const fc = buildCarbonProvinceGeo();
          provinceFullSnapshot = cloneFeatureCollection(fc);
          return fc;
        };

        const buildProvinceBackdropGeo = (selectedProvince: string) => {
          const fc = buildCarbonProvinceGeo();
          provinceFullSnapshot = cloneFeatureCollection(fc);
          applySelectedCarbonStyle(fc, selectedProvince);
          return fc;
        };

        const provinceGeo = restoreProvinceForegroundGeo();

        const carbonExtrudeLayer = new PolygonLayer({ zIndex: 5 })
          .source(provinceGeo)
          .shape('extrude')
          .size('_score', CARBON_PROVINCE_EXTRUDE_RANGE)
          .color('_rawCarbon', CARBON_COLOR_RAMP)
          .style({ heightfixed: true, pickLight: true, opacity: 0.88 })
          .active({ color: GF_ACTIVE_COLOR });
        scene.addLayer(carbonExtrudeLayer);
        carbonExtrudeLayer.on('click', (e) => {
          if (options.selectedProvince.value) return;
          const name = e.feature?.properties?.name;
          if (name && !isProvinceExcludedFromPanel(name) && e.feature?.properties?._isBackdrop !== true) {
            options.onProvinceClick?.(name);
          }
        });

        const carbonTopOutlineLayer = new LineLayer({ zIndex: 15 })
          .source(buildExtrudeTopOutlines(provinceGeo, CARBON_PROVINCE_EXTRUDE_RANGE))
          .shape('line')
          .color(GF_EXTRUDE_TOP_LINE_COLOR)
          .size(GF_EXTRUDE_TOP_LINE_WIDTH)
          .style({
            opacity: 0.94,
            heightfixed: true,
            vertexHeightScale: 1,
            depth: true,
          });
        scene.addLayer(carbonTopOutlineLayer);

        const border = new LineLayer({ zIndex: 10 })
          .source(fullOutlineGeo)
          .shape('line')
          .color('rgba(0,229,255,0.38)')
          .size(0.65)
          .style({ opacity: 0.75 });
        scene.addLayer(border);

        const setProvinceLayerData = (fc: { type: string; features: any[] }, backdrop = false) => {
          const nextGeo = cloneFeatureCollection(fc);
          carbonExtrudeLayer.setData(nextGeo);
          if (backdrop) {
            carbonExtrudeLayer.color('_color');
            carbonExtrudeLayer.active(false);
            carbonTopOutlineLayer.color(GF_BACKDROP_TOP_LINE_COLOR);
            border.color('rgba(140,168,190,0.18)');
            border.style({ opacity: 0.45 });
            noPanelFill.color('rgba(92,100,112,0.72)');
            noPanelFill.style({ opacity: 0.72 });
          } else {
            carbonExtrudeLayer.color('_rawCarbon', CARBON_COLOR_RAMP);
            carbonExtrudeLayer.active({ color: GF_ACTIVE_COLOR });
            carbonTopOutlineLayer.color(GF_EXTRUDE_TOP_LINE_COLOR);
            border.color('rgba(0,229,255,0.38)');
            border.style({ opacity: 0.75 });
            noPanelFill.color('#5c6470');
            noPanelFill.style({ opacity: 0.95 });
          }
          carbonTopOutlineLayer.setData(buildExtrudeTopOutlines(nextGeo, CARBON_PROVINCE_EXTRUDE_RANGE));
          carbonExtrudeLayer.show();
          carbonTopOutlineLayer.show();
        };

        const restoreCityForegroundGeo = () => {
          if (!cityBaseSnapshot) return null;
          const fc = cloneFeatureCollection(cityBaseSnapshot);
          applyCityCarbonToFc(fc);
          cityFullSnapshot = cloneFeatureCollection(fc);
          return fc;
        };

        const buildCityBackdropGeo = (selectedCity: string) => {
          if (!cityBaseSnapshot) return null;
          const fc = cloneFeatureCollection(cityBaseSnapshot);
          applyCityCarbonToFc(fc);
          cityFullSnapshot = cloneFeatureCollection(fc);
          applySelectedCarbonStyle(fc, selectedCity, selectedCity ? GF_BACKDROP_COLOR : CARBON_DRILL_HIT_COLOR);
          return fc;
        };

        const restoreCountyForegroundGeo = () => {
          if (!countyBaseSnapshot) return null;
          const fc = cloneFeatureCollection(countyBaseSnapshot);
          applyCountyCarbonToFc(fc);
          countyFullSnapshot = cloneFeatureCollection(fc);
          return fc;
        };

        const buildCountyBackdropGeo = (selectedCounty = '') => {
          if (!countyBaseSnapshot) return null;
          const fc = cloneFeatureCollection(countyBaseSnapshot);
          applyCountyCarbonToFc(fc);
          countyFullSnapshot = cloneFeatureCollection(fc);
          applySelectedCarbonStyle(fc, selectedCounty, selectedCounty ? GF_BACKDROP_COLOR : CARBON_DRILL_HIT_COLOR);
          return fc;
        };

        const ensureCityLayers = (fc: { type: string; features: any[] }) => {
          if (!cityExtrudeLayer) {
            cityExtrudeLayer = new PolygonLayer({ zIndex: 6 })
              .source(fc)
              .shape('extrude')
              .size('_score', CARBON_CITY_EXTRUDE_RANGE)
              .color('_rawCarbon', CARBON_COLOR_RAMP)
              .style({ heightfixed: true, pickLight: true, opacity: 0.88 })
              .active({ color: GF_ACTIVE_COLOR });
            scene.addLayer(cityExtrudeLayer);
            cityExtrudeLayer.on('click', (e) => {
              if (!options.selectedProvince.value || options.selectedCity.value) return;
              const name = e.feature?.properties?.name;
              if (name && e.feature?.properties?._hasData !== false) {
                options.onCityClick?.(name);
              }
            });
          }
          if (!cityTopOutlineLayer) {
            cityTopOutlineLayer = new LineLayer({ zIndex: 16 })
              .source(buildExtrudeTopOutlines(fc, CARBON_CITY_EXTRUDE_RANGE))
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
            cityExtrudeLayer?.color('_color');
            cityExtrudeLayer?.active(false);
            cityTopOutlineLayer?.color(GF_BACKDROP_TOP_LINE_COLOR);
          } else {
            cityExtrudeLayer?.color('_rawCarbon', CARBON_COLOR_RAMP);
            cityExtrudeLayer?.active({ color: GF_ACTIVE_COLOR });
            cityTopOutlineLayer?.color(GF_EXTRUDE_TOP_LINE_COLOR);
          }
          cityTopOutlineLayer?.setData(buildExtrudeTopOutlines(nextGeo, CARBON_CITY_EXTRUDE_RANGE));
          cityExtrudeLayer?.show();
          cityTopOutlineLayer?.show();
        };

        const ensureCountyLayers = (fc: { type: string; features: any[] }) => {
          if (!countyExtrudeLayer) {
            countyExtrudeLayer = new PolygonLayer({ zIndex: 7 })
              .source(fc)
              .shape('extrude')
              .size('_score', CARBON_COUNTY_EXTRUDE_RANGE)
              .color('_rawCarbon', CARBON_COLOR_RAMP)
              .style({ heightfixed: true, pickLight: true, opacity: 0.88 })
              .active({ color: GF_ACTIVE_COLOR });
            scene.addLayer(countyExtrudeLayer);
            countyExtrudeLayer.on('click', (e) => {
              if (!options.selectedProvince.value || !options.selectedCity.value) return;
              const name = e.feature?.properties?.name;
              if (!name || e.feature?.properties?._hasData === false) return;
              selectedCountyName = name;
              const countyGeo = buildCountyBackdropGeo(name);
              if (!countyGeo) return;
              setCountyLayerData(countyGeo, true);
              scene.render();
              const selectedFeature = countyGeo.features.filter((f) => regionNameMatches(f.properties?.name || '', name));
              if (selectedFeature.length) {
                runCinematicFit(boundsFromFeatures(selectedFeature));
              }
            });
          }
          if (!countyTopOutlineLayer) {
            countyTopOutlineLayer = new LineLayer({ zIndex: 17 })
              .source(buildExtrudeTopOutlines(fc, CARBON_COUNTY_EXTRUDE_RANGE))
              .shape('line')
              .color(GF_EXTRUDE_TOP_LINE_COLOR)
              .size(GF_EXTRUDE_TOP_LINE_WIDTH)
              .style({
                opacity: 0.94,
                heightfixed: true,
                vertexHeightScale: 1,
                depth: true,
              });
            scene.addLayer(countyTopOutlineLayer);
          }
        };

        const setCountyLayerData = (fc: { type: string; features: any[] }, backdrop = false) => {
          ensureCountyLayers(fc);
          const nextGeo = cloneFeatureCollection(fc);
          countyExtrudeLayer?.setData(nextGeo);
          if (backdrop) {
            countyExtrudeLayer?.color('_color');
            countyExtrudeLayer?.active(false);
            countyTopOutlineLayer?.color(GF_BACKDROP_TOP_LINE_COLOR);
          } else {
            countyExtrudeLayer?.color('_rawCarbon', CARBON_COLOR_RAMP);
            countyExtrudeLayer?.active({ color: GF_ACTIVE_COLOR });
            countyTopOutlineLayer?.color(GF_EXTRUDE_TOP_LINE_COLOR);
          }
          countyTopOutlineLayer?.setData(buildExtrudeTopOutlines(nextGeo, CARBON_COUNTY_EXTRUDE_RANGE));
          countyExtrudeLayer?.show();
          countyTopOutlineLayer?.show();
        };

        watch(
          realProvinceData,
          () => {
            const nextGeo = options.selectedProvince.value
              ? buildProvinceBackdropGeo(options.selectedProvince.value)
              : restoreProvinceForegroundGeo();
            setProvinceLayerData(nextGeo, !!options.selectedProvince.value);
            scene.render();
          },
          { deep: true, immediate: true },
        );

        watch(
          options.cityRows,
          () => {
            if (!options.selectedProvince.value || !cityBaseSnapshot || citySnapshotProvince !== options.selectedProvince.value) return;
            const nextGeo = buildCityBackdropGeo(options.selectedCity.value || '');
            if (!nextGeo) return;
            setCityLayerData(nextGeo, true);
            scene.render();
          },
          { deep: true },
        );

        watch(
          options.countyRows,
          () => {
            if (!options.selectedCity.value || !countyBaseSnapshot || countySnapshotCity !== options.selectedCity.value) return;
            const countyGeo = buildCountyBackdropGeo(selectedCountyName);
            if (!countyGeo) return;
            setCountyLayerData(countyGeo, true);
            scene.render();
          },
          { deep: true },
        );

        watch(options.selectedCity, async (city) => {
          const gen = ++countyDrillGen;

          if (!city) {
            selectedCountyName = '';
            countyExtrudeLayer?.hide();
            countyTopOutlineLayer?.hide();
            countyBaseSnapshot = null;
            countyFullSnapshot = null;
            countySnapshotCity = '';
            if (!options.selectedProvince.value || !cityBaseSnapshot || citySnapshotProvince !== options.selectedProvince.value) {
              scene.render();
              return;
            }
            const cityGeo = buildCityBackdropGeo('');
            if (!cityGeo) {
              scene.render();
              return;
            }
            setCityLayerData(cityGeo, true);
            scene.render();
            runCinematicFit(boundsFromFeatures(cityGeo.features));
            return;
          }

          const prov = options.selectedProvince.value;
          if (!prov || !cityBaseSnapshot || citySnapshotProvince !== prov) {
            options.onCityClick?.('');
            return;
          }

          const cityBackdropGeo = buildCityBackdropGeo(city);
          if (!cityBackdropGeo) {
            options.onCityClick?.('');
            return;
          }

          setCityLayerData(cityBackdropGeo, true);
          selectedCountyName = '';
          countyExtrudeLayer?.hide();
          countyTopOutlineLayer?.hide();
          countyBaseSnapshot = null;
          countyFullSnapshot = null;
          countySnapshotCity = '';
          scene.render();

          try {
            const geoRes = await fetchCountyGeoJson(city);
            if (gen !== countyDrillGen) return;
            countyBaseSnapshot = cloneFeatureCollection(geoRes);
            countySnapshotCity = city;
            const countyGeo = buildCountyBackdropGeo('');
            if (!countyGeo) throw new Error('county geo snapshot missing');
            setCountyLayerData(countyGeo, true);
            scene.render();
            runCinematicFit(boundsFromFeatures(countyGeo.features));
          } catch (err) {
            console.error('碳排放地图县级下钻失败:', err);
            if (gen !== countyDrillGen) return;
            options.onCityClick?.('');
          }
        });

        watch(
          options.selectedProvince,
          async (prov) => {
            const gen = ++drillGen;
            countyDrillGen += 1;
            selectedCountyName = '';
            countyExtrudeLayer?.hide();
            countyTopOutlineLayer?.hide();
            countyBaseSnapshot = null;
            countyFullSnapshot = null;
            countySnapshotCity = '';

            if (!prov) {
              cityExtrudeLayer?.hide();
              cityTopOutlineLayer?.hide();
              cityBaseSnapshot = null;
              cityFullSnapshot = null;
              citySnapshotProvince = '';
              selectedCountyName = '';
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
              const cityGeo = buildCityBackdropGeo('');
              if (!cityGeo) throw new Error('city geo snapshot missing');
              setCityLayerData(cityGeo, true);
              scene.render();
              runCinematicFit(boundsFromFeatures(cityGeo.features));
            } catch (err) {
              console.error('碳排放地图市级下钻失败:', err);
              options.onProvinceClick?.('');
            }
          },
          { immediate: true },
        );
      }).catch((err) => {
        console.error('碳排地图省级 GeoJSON 加载失败:', err);
      });
    });
  });
}

export default {};
