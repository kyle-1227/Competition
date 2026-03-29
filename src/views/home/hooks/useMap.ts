/* eslint-disable @typescript-eslint/ban-ts-comment, no-undef, no-underscore-dangle, no-param-reassign, no-plusplus, no-continue */
// @ts-nocheck
import { onMounted, watch, type Ref } from 'vue';
import { LineLayer, PolygonLayer, Scene } from '@antv/l7';
import { Map } from '@antv/l7-maps';
import { RDBSource } from 'district-data';
import {
  realProvinceData,
  scoreToColor,
  fetchGeoJson,
  fetchCityData,
  realCityData,
  selectedYear,
  gfDrillProvince,
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
  mode: 'province' | 'city';
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

function formatIndicatorCell(v: unknown): string {
  if (v == null || (typeof v === 'number' && !Number.isFinite(v))) return '—';
  if (typeof v === 'number') {
    return v.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
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
  return (row.score * 100).toFixed(1);
}

function attachGreenFinanceMapTooltip(
  layer: PolygonLayer,
  scene: Scene,
  mapAreaEl: HTMLElement,
  mapRootEl: HTMLElement,
  tooltipRef: Ref<GfMapTooltipState>,
  mode: 'province' | 'city',
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
  };

  const onPick = (e: any) => {
    const name = e.feature?.properties?.name;
    if (!name) return;
    if (mode === 'province' && isProvinceExcludedFromPanel(name)) return;
    const ll = e.lngLat ?? e.lnglat;
    if (!ll) return;
    const lng = typeof ll.lng === 'number' ? ll.lng : ll[0];
    const lat = typeof ll.lat === 'number' ? ll.lat : ll[1];
    if (typeof lng !== 'number' || typeof lat !== 'number') return;
    applyPayload(name, lng, lat);
  };

  const hide = () => {
    tooltipRef.value = createHiddenGfTooltip();
  };

  layer.on('mouseenter', onPick);
  layer.on('mousemove', onPick);
  layer.on('mouseout', hide);

  return { hide };
}

/** 绿金 3D 柱体顶面外轮廓白线（与柱顶同高，区分邻省/市） */
const GF_EXTRUDE_TOP_LINE_COLOR = 'rgba(255,255,255,0.9)';
const GF_EXTRUDE_TOP_LINE_WIDTH = 1.15;
/** 与 PolygonLayer `.size('_score', range)` 一致 */
const GF_PROVINCE_EXTRUDE_RANGE: [number, number] = [20000, 2000000];
const GF_CITY_EXTRUDE_RANGE: [number, number] = [12000, 1800000];

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
    const mid = (r0 + r1) / 2;
    return () => mid;
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

      let cityExtrudeLayer: PolygonLayer | null = null;
      let topOutlineLayer: LineLayer | null = null;
      let cityFcSnapshot: { type: string; features: any[] } | null = null;
      let drillGen = 0;

      const source = new RDBSource({ version: 2023 });
      source.getData({ level: 'province', precision: 'low' }).then((geoData) => {
        const features = geoData.features.filter((f) => f.properties.name);
        const noPanelFeats = features.filter((f) => isProvinceExcludedFromPanel(f.properties.name));
        const mainFeats = features.filter((f) => !isProvinceExcludedFromPanel(f.properties.name));
        const fullOutlineGeo = { type: 'FeatureCollection', features };

        const noPanelFillGeo = { type: 'FeatureCollection', features: noPanelFeats };
        const noPanelFill = new PolygonLayer({ zIndex: 4 })
          .source(noPanelFillGeo)
          .shape('fill')
          .color('#5c6470')
          .style({ opacity: 0.95 });
        scene.addLayer(noPanelFill);

        const applyScores = () => {
          const scoreMap = buildProvinceScoreMap();
          mainFeats.forEach((f) => {
            const s = scoreMap[f.properties.name] || 0;
            f.properties._score = s ** 1.5;
            f.properties._rawScore = s;
          });
        };
        applyScores();
        const provinceGeo = { type: 'FeatureCollection', features: mainFeats };

        const extrudeLayer = new PolygonLayer({ zIndex: 5 })
          .source(provinceGeo)
          .shape('extrude')
          .size('_score', GF_PROVINCE_EXTRUDE_RANGE)
          .color('_rawScore', [
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
          ])
          .style({ heightfixed: true, pickLight: true, opacity: 0.88 })
          .active({ color: 'rgba(0,229,255,0.45)' });
        scene.addLayer(extrudeLayer);

        const provinceTopOutlineGeo = buildExtrudeTopOutlines(provinceGeo, GF_PROVINCE_EXTRUDE_RANGE);
        topOutlineLayer = new LineLayer({ zIndex: 15 })
          .source(provinceTopOutlineGeo)
          .shape('line')
          .color(GF_EXTRUDE_TOP_LINE_COLOR)
          .size(GF_EXTRUDE_TOP_LINE_WIDTH)
          .style({
            opacity: 0.94,
            heightfixed: true,
            vertexHeightScale: 1,
            depth: true,
          });
        scene.addLayer(topOutlineLayer);

        const borderLayer = new LineLayer({ zIndex: 10 })
          .source(fullOutlineGeo)
          .shape('line')
          .color('rgba(0,229,255,0.38)')
          .size(0.65)
          .style({ opacity: 0.75 });
        scene.addLayer(borderLayer);

        extrudeLayer.on('click', (e) => {
          const name = e.feature?.properties?.name;
          if (name && !isProvinceExcludedFromPanel(name)) {
            selectedProv.value = name;
            gfDrillProvince.value = name;
          }
        });

        if (mapAreaEl && mapEl) {
          attachGreenFinanceMapTooltip(extrudeLayer, scene, mapAreaEl, mapEl, tooltipRef, 'province');
          mapEl.addEventListener('mouseleave', () => {
            tooltipRef.value = createHiddenGfTooltip();
          });
        }

        watch(
          [selectedYear, realProvinceData, realCityData],
          () => {
            const t = tooltipRef.value;
            if (!t.visible || !t.regionName) return;
            const row = t.mode === 'province' ? findProvinceRow(t.regionName) : findCityRow(t.regionName);
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
          tooltipRef.value = createHiddenGfTooltip();
        });

        const applyCityScoresToFc = (fc: { features: any[] }) => {
          const rows = realCityData.value;
          fc.features.forEach((f) => {
            const geoName = f.properties?.name || '';
            const s = matchCityScore(geoName, rows);
            f.properties._score = s ** 1.5;
            f.properties._color = scoreToColor(s);
          });
        };

        const refreshCityLayers = () => {
          if (!gfDrillProvince.value || !cityExtrudeLayer || !topOutlineLayer || !cityFcSnapshot) return;
          applyCityScoresToFc(cityFcSnapshot);
          const newGeo = { type: 'FeatureCollection', features: [...cityFcSnapshot.features] };
          cityExtrudeLayer.setData(newGeo);
          topOutlineLayer.setData(buildExtrudeTopOutlines(newGeo, GF_CITY_EXTRUDE_RANGE));
          scene.render();
        };

        watch(
          realProvinceData,
          () => {
            if (gfDrillProvince.value) return;
            applyScores();
            const pg = { type: 'FeatureCollection', features: [...mainFeats] };
            extrudeLayer.setData(pg);
            topOutlineLayer?.setData(buildExtrudeTopOutlines(pg, GF_PROVINCE_EXTRUDE_RANGE));
            scene.render();
          },
          { deep: true, immediate: true },
        );

        watch(
          realCityData,
          () => {
            if (!gfDrillProvince.value) return;
            refreshCityLayers();
          },
          { deep: true },
        );

        watch(gfDrillProvince, async (prov) => {
          const gen = ++drillGen;

          if (!prov) {
            cityExtrudeLayer?.hide();
            cityFcSnapshot = null;
            applyScores();
            const pg = { type: 'FeatureCollection', features: [...mainFeats] };
            extrudeLayer.setData(pg);
            extrudeLayer.show();
            topOutlineLayer?.setData(buildExtrudeTopOutlines(pg, GF_PROVINCE_EXTRUDE_RANGE));
            topOutlineLayer?.show();
            borderLayer.show();
            noPanelFill.show();
            scene.setZoomAndCenter(3.2, [104.195397, 35.86166]);
            scene.setPitch(45);
            fetchCityData('', selectedYear.value);
            scene.render();
            return;
          }

          extrudeLayer.hide();
          topOutlineLayer?.hide();
          borderLayer.hide();
          noPanelFill.hide();

          try {
            await fetchCityData(prov, selectedYear.value);
            if (gen !== drillGen) return;

            const geoRes = await fetchGeoJson(prov);
            if (gen !== drillGen) return;

            const fc = {
              type: 'FeatureCollection',
              features: geoRes.features.map((f: any) => ({
                ...f,
                properties: { ...(f.properties || {}) },
              })),
            };
            applyCityScoresToFc(fc);
            cityFcSnapshot = fc;

            if (!cityExtrudeLayer) {
              cityExtrudeLayer = new PolygonLayer({ zIndex: 6 })
                .source(fc)
                .shape('extrude')
                .size('_score', GF_CITY_EXTRUDE_RANGE)
                .color('_color')
                .style({ heightfixed: true, pickLight: true, opacity: 0.88 })
                .active({ color: 'rgba(0,229,255,0.45)' });
              scene.addLayer(cityExtrudeLayer);
              if (mapAreaEl && mapEl) {
                attachGreenFinanceMapTooltip(cityExtrudeLayer, scene, mapAreaEl, mapEl, tooltipRef, 'city');
              }
            } else {
              cityExtrudeLayer.setData(fc);
            }

            topOutlineLayer?.setData(buildExtrudeTopOutlines(fc, GF_CITY_EXTRUDE_RANGE));
            cityExtrudeLayer.show();
            topOutlineLayer?.show();

            const bounds = boundsFromFeatures(fc.features);
            if (bounds) {
              scene.fitBounds(bounds, { padding: 50, duration: 600 });
            }
            scene.setPitch(50);
            scene.render();
          } catch (err) {
            console.error('绿色金融地图下钻失败:', err);
            gfDrillProvince.value = '';
          }
        });
      });
    });
  });
}

export function useCarbonMap() {
  onMounted(() => {
    const scene = new Scene({
      id: 'carbon-map',
      map: new Map({
        pitch: 20,
        style: 'dark',
        center: [104.195397, 35.86166],
        zoom: 3.5,
      }),
    });
    scene.setBgColor('#131722');
    scene.on('loaded', () => {
      const mapEl = document.getElementById('carbon-map');
      if (mapEl) mapEl.style.background = '#131722';

      const source = new RDBSource({ version: 2023 });
      source.getData({ level: 'province', precision: 'low' }).then((geoData) => {
        const features = geoData.features.filter((f) => f.properties.name);
        const noPanelFeats = features.filter((f) => isProvinceExcludedFromPanel(f.properties.name));
        const mainFeats = features.filter((f) => !isProvinceExcludedFromPanel(f.properties.name));
        const fullOutlineGeo = { type: 'FeatureCollection', features };

        const noPanelFillGeo = { type: 'FeatureCollection', features: noPanelFeats };
        const noPanelFill = new PolygonLayer({ zIndex: 4 })
          .source(noPanelFillGeo)
          .shape('fill')
          .color('#5c6470')
          .style({ opacity: 0.95 });
        scene.addLayer(noPanelFill);

        const applyCarbon = () => {
          const carbonMap = buildCarbonMapWanTon();
          mainFeats.forEach((f) => {
            f.properties._carbon = carbonMap[f.properties.name] || 0;
          });
        };
        applyCarbon();
        const provinceGeo = { type: 'FeatureCollection', features: mainFeats };

        const choropleth = new PolygonLayer({ zIndex: 5 })
          .source(provinceGeo)
          .shape('fill')
          .color('_carbon', [
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
          ])
          .style({ opacity: 0.8 })
          .active({ color: 'rgba(255,255,255,0.25)' });
        scene.addLayer(choropleth);

        const border = new LineLayer({ zIndex: 10 })
          .source(fullOutlineGeo)
          .shape('line')
          .color('rgba(255,255,255,0.25)')
          .size(0.6)
          .style({ opacity: 0.7 });
        scene.addLayer(border);

        watch(
          realProvinceData,
          () => {
            applyCarbon();
            choropleth.setData({ type: 'FeatureCollection', features: [...mainFeats] });
            scene.render();
          },
          { deep: true, immediate: true },
        );
      });
    });
  });
}

export default {};
