/* eslint-disable @typescript-eslint/ban-ts-comment, no-undef, no-underscore-dangle, no-param-reassign, no-plusplus, no-continue */
// @ts-nocheck
import { onMounted, watch, type Ref } from 'vue';
import { LineLayer, PointLayer, PolygonLayer, Scene } from '@antv/l7';
import { Map } from '@antv/l7-maps';
import { RDBSource } from 'district-data';
import {
  selectedProvince,
  tfeeThreshold,
  provinceCoords,
  fullToShortName,
  realProvinceData,
  scoreToColor,
  fetchGeoJson,
  fetchCityData,
  realCityData,
  selectedYear,
  gfDrillProvince,
} from './provinceData';

const LINE_PARSER = { parser: { type: 'json', x: 'x', y: 'y', x1: 'x1', y1: 'y1' } };
const POINT_PARSER = { parser: { type: 'json', x: 'lng', y: 'lat' } };

// 全部 31 省省会标注数据（静态）
const allProvincePoints = Object.entries(provinceCoords).map(([full, [lng, lat]]) => ({
  lng,
  lat,
  name: fullToShortName[full] || full,
}));

interface FlyLine {
  x: number;
  y: number;
  x1: number;
  y1: number;
  from: string;
  to: string;
}
interface CityPoint {
  lng: number;
  lat: number;
  name: string;
}

/**
 * 基于引力模型的动态飞线生成算法
 * 根据当年各省绿色金融得分排名，动态计算空间溢出关系
 */
function generateDynamicLines() {
  /* 联调：无接口数据时不使用 mock，飞线为空便于对比 */
  const data = realProvinceData.value;
  const sorted = [...data].sort((a, b) => b.score - a.score);

  const hubs = sorted.slice(0, 5);
  const middles = sorted.slice(5, 15);
  const bottoms = sorted.slice(-5);

  const greenLines: FlyLine[] = [];
  const redLines: FlyLine[] = [];
  const activeSet = new Set<string>();

  hubs.forEach((hub, i) => {
    const hubCoord = provinceCoords[hub.province];
    if (!hubCoord) return;
    const hubShort = fullToShortName[hub.province] || hub.province;
    activeSet.add(hub.province);

    // 每个 hub 向 3 个中等省份发绿线（偏移选取，避免重叠）
    for (let j = 0; j < 3; j++) {
      const mid = middles[(i * 3 + j) % middles.length];
      const midCoord = provinceCoords[mid.province];
      if (!midCoord) continue;
      activeSet.add(mid.province);
      greenLines.push({
        x: hubCoord[0],
        y: hubCoord[1],
        x1: midCoord[0],
        y1: midCoord[1],
        from: hubShort,
        to: fullToShortName[mid.province] || mid.province,
      });
    }

    // 每个 hub 向 1 个落后省份发红线
    const bot = bottoms[i % bottoms.length];
    const botCoord = provinceCoords[bot.province];
    if (botCoord) {
      activeSet.add(bot.province);
      redLines.push({
        x: hubCoord[0],
        y: hubCoord[1],
        x1: botCoord[0],
        y1: botCoord[1],
        from: hubShort,
        to: fullToShortName[bot.province] || bot.province,
      });
    }
  });

  const activeCities: CityPoint[] = [...activeSet].flatMap((fullName) => {
    const coord = provinceCoords[fullName];
    if (!coord) return [];
    return [{ lng: coord[0], lat: coord[1], name: fullToShortName[fullName] || fullName }];
  });

  return { greenLines, redLines, activeCities };
}

function buildScoreMap(): Record<string, number> {
  const list = realProvinceData.value;
  const map: Record<string, number> = {};
  list.forEach((p) => {
    map[p.province] = p.score;
  });
  return map;
}

export function useMap() {
  onMounted(() => {
    const source = new RDBSource({ version: 2023 });

    const scene = new Scene({
      id: 'map',
      map: new Map({
        pitch: 45,
        style: 'dark',
        center: [104.195397, 35.86166],
        zoom: 3,
      }),
    });

    scene.setBgColor('#131722');

    let redFlyLayer: LineLayer | null = null;
    let greenFlyLayer: LineLayer | null = null;
    let radarLayer: PointLayer | null = null;
    let provinceExtrudeLayer: PolygonLayer | null = null;
    let provinceBorderLayer: LineLayer | null = null;

    scene.on('loaded', () => {
      const mapEl = document.getElementById('map');
      if (mapEl) mapEl.style.background = '#131722';

      source.getData({ level: 'province', precision: 'low' }).then((geoData) => {
        const features = geoData.features.filter((f) => f.properties.name);
        const scoreMap = buildScoreMap();

        features.forEach((f) => {
          const s = scoreMap[f.properties.name] || 0;
          f.properties._score = s ** 1.6;
          f.properties._color = scoreToColor(s);
        });

        const provinceGeo = { type: 'FeatureCollection', features };

        provinceExtrudeLayer = new PolygonLayer({ zIndex: 5 })
          .source(provinceGeo)
          .shape('extrude')
          .size('_score', [15000, 2500000])
          .color('_color')
          .style({ heightfixed: true, pickLight: true, opacity: 0.85 })
          .active({ color: 'rgba(0,229,255,0.5)' });
        scene.addLayer(provinceExtrudeLayer);

        provinceBorderLayer = new LineLayer({ zIndex: 10 })
          .source(provinceGeo)
          .shape('line')
          .color('#5DDDFF')
          .size(0.6)
          .style({ opacity: 0.8 });
        scene.addLayer(provinceBorderLayer);

        provinceExtrudeLayer.on('click', (e) => {
          const name = e.feature?.properties?.name;
          if (name) selectedProvince.value = name;
        });

        const syncFromProvinceData = () => {
          const newScoreMap = buildScoreMap();
          features.forEach((f) => {
            const s = newScoreMap[f.properties.name] || 0;
            f.properties._score = s ** 1.6;
            f.properties._color = scoreToColor(s);
          });
          const newGeo = { type: 'FeatureCollection', features: [...features] };
          provinceExtrudeLayer?.setData(newGeo);
          provinceBorderLayer?.setData(newGeo);

          const { greenLines, redLines, activeCities } = generateDynamicLines();
          greenFlyLayer?.setData(greenLines, LINE_PARSER);
          redFlyLayer?.setData(redLines, LINE_PARSER);
          radarLayer?.setData(activeCities, POINT_PARSER);
          scene.render();
        };

        const initial = generateDynamicLines();

        greenFlyLayer = new LineLayer({ blend: 'normal', zIndex: 8 })
          .source(initial.greenLines, LINE_PARSER)
          .size(1.8)
          .shape('arc3d')
          .color('#00e5ff')
          .animate({ interval: 0.08, trailLength: 0.5, duration: 0.6 })
          .style({ sourceColor: '#00e5ff', targetColor: '#76ff03', thetaOffset: 0.8, opacity: 0.9 });
        scene.addLayer(greenFlyLayer);

        redFlyLayer = new LineLayer({ blend: 'normal', zIndex: 8 })
          .source(initial.redLines, LINE_PARSER)
          .size(2)
          .shape('arc3d')
          .color('#ff4444')
          .animate({ interval: 0.08, trailLength: 0.4, duration: 0.5 })
          .style({ sourceColor: '#ff4444', targetColor: '#ffab00', thetaOffset: 1, opacity: 1 });
        scene.addLayer(redFlyLayer);

        watch(tfeeThreshold, (val) => {
          if (!redFlyLayer) return;
          if (val >= 0.62) {
            redFlyLayer.size(0.4);
            redFlyLayer.color('#66bb6a');
            redFlyLayer.style({ sourceColor: '#66bb6a', targetColor: '#a5d6a7', opacity: 0.3 });
          } else {
            redFlyLayer.size(2);
            redFlyLayer.color('#ff4444');
            redFlyLayer.style({ sourceColor: '#ff4444', targetColor: '#ffab00', opacity: 1 });
          }
          scene.render();
        });

        radarLayer = new PointLayer({ zIndex: 12 })
          .source(initial.activeCities, POINT_PARSER)
          .shape('circle')
          .animate(true)
          .size(30)
          .color('#00e5ff')
          .style({ opacity: 0.8 });
        scene.addLayer(radarLayer);

        const allLabelsLayer = new PointLayer({ zIndex: 15 })
          .source(allProvincePoints, POINT_PARSER)
          .shape('name', 'text')
          .size(10)
          .color('#0ff')
          .style({
            textAnchor: 'bottom',
            textOffset: [0, -8],
            spacing: 2,
            padding: [2, 2],
            stroke: '#0ff',
            strokeWidth: 0.3,
            textAllowOverlap: true,
          });
        scene.addLayer(allLabelsLayer);

        watch(realProvinceData, syncFromProvinceData, { deep: true, immediate: true });
      });
    });
  });
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

export function useGreenFinanceMap(selectedProv: Ref<string>) {
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

      let cityExtrudeLayer: PolygonLayer | null = null;
      let cityBorderLayer: LineLayer | null = null;
      let cityFcSnapshot: { type: string; features: any[] } | null = null;
      let drillGen = 0;

      const source = new RDBSource({ version: 2023 });
      source.getData({ level: 'province', precision: 'low' }).then((geoData) => {
        const features = geoData.features.filter((f) => f.properties.name);
        const applyScores = () => {
          const scoreMap = buildProvinceScoreMap();
          features.forEach((f) => {
            const s = scoreMap[f.properties.name] || 0;
            f.properties._score = s ** 1.5;
            f.properties._rawScore = s;
          });
        };
        applyScores();
        const provinceGeo = { type: 'FeatureCollection', features };

        const extrudeLayer = new PolygonLayer({ zIndex: 5 })
          .source(provinceGeo)
          .shape('extrude')
          .size('_score', [20000, 2000000])
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

        const borderLayer = new LineLayer({ zIndex: 10 })
          .source(provinceGeo)
          .shape('line')
          .color('#5DDDFF')
          .size(0.6)
          .style({ opacity: 0.7 });
        scene.addLayer(borderLayer);

        const labelLayer = new PointLayer({ zIndex: 15 })
          .source(allProvincePoints, POINT_PARSER)
          .shape('name', 'text')
          .size(9)
          .color('#0ff')
          .style({
            textAnchor: 'bottom',
            textOffset: [0, -8],
            spacing: 2,
            padding: [2, 2],
            stroke: '#0ff',
            strokeWidth: 0.3,
            textAllowOverlap: true,
          });
        scene.addLayer(labelLayer);

        extrudeLayer.on('click', (e) => {
          const name = e.feature?.properties?.name;
          if (name) {
            selectedProv.value = name;
            gfDrillProvince.value = name;
          }
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
          if (!gfDrillProvince.value || !cityExtrudeLayer || !cityBorderLayer || !cityFcSnapshot) return;
          applyCityScoresToFc(cityFcSnapshot);
          const newGeo = { type: 'FeatureCollection', features: [...cityFcSnapshot.features] };
          cityExtrudeLayer.setData(newGeo);
          cityBorderLayer.setData(newGeo);
          scene.render();
        };

        watch(
          realProvinceData,
          () => {
            if (gfDrillProvince.value) return;
            applyScores();
            const newGeo = { type: 'FeatureCollection', features: [...features] };
            extrudeLayer.setData(newGeo);
            borderLayer.setData(newGeo);
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
            cityBorderLayer?.hide();
            cityFcSnapshot = null;
            extrudeLayer.show();
            borderLayer.show();
            labelLayer.show();
            scene.setZoomAndCenter(3.2, [104.195397, 35.86166]);
            scene.setPitch(45);
            fetchCityData('', selectedYear.value);
            scene.render();
            return;
          }

          extrudeLayer.hide();
          borderLayer.hide();
          labelLayer.hide();

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
                .size('_score', [12000, 1800000])
                .color('_color')
                .style({ heightfixed: true, pickLight: true, opacity: 0.88 })
                .active({ color: 'rgba(0,229,255,0.45)' });
              scene.addLayer(cityExtrudeLayer);

              cityBorderLayer = new LineLayer({ zIndex: 11 })
                .source(fc)
                .shape('line')
                .color('#5DDDFF')
                .size(0.5)
                .style({ opacity: 0.75 });
              scene.addLayer(cityBorderLayer);
            } else {
              cityExtrudeLayer.setData(fc);
              cityBorderLayer.setData(fc);
            }

            cityExtrudeLayer.show();
            cityBorderLayer.show();

            const bounds = boundsFromFeatures(fc.features);
            if (bounds) {
              scene.fitBounds(bounds, { padding: 50, duration: 600 });
            }
            scene.setPitch(50);
            scene.render();
          } catch (err) {
            console.error('绿色金融地图下钻失败:', err);
            gfDrillProvince.value = '';
            extrudeLayer.show();
            borderLayer.show();
            labelLayer.show();
            scene.render();
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
        const applyCarbon = () => {
          const carbonMap = buildCarbonMapWanTon();
          features.forEach((f) => {
            f.properties._carbon = carbonMap[f.properties.name] || 0;
          });
        };
        applyCarbon();
        const provinceGeo = { type: 'FeatureCollection', features };

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
          .source(provinceGeo)
          .shape('line')
          .color('rgba(255,255,255,0.25)')
          .size(0.6)
          .style({ opacity: 0.7 });
        scene.addLayer(border);

        watch(
          realProvinceData,
          () => {
            applyCarbon();
            const newGeo = { type: 'FeatureCollection', features: [...features] };
            choropleth.setData(newGeo);
            border.setData(newGeo);
            scene.render();
          },
          { deep: true, immediate: true },
        );
      });

      const labelLayer = new PointLayer({ zIndex: 15 })
        .source(allProvincePoints, POINT_PARSER)
        .shape('name', 'text')
        .size(9)
        .color('#fff')
        .style({
          textAnchor: 'bottom',
          textOffset: [0, -4],
          spacing: 2,
          padding: [2, 2],
          stroke: '#000',
          strokeWidth: 0.8,
          textAllowOverlap: true,
        });
      scene.addLayer(labelLayer);
    });
  });
}

export default {};
