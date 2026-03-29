/* eslint-disable @typescript-eslint/ban-ts-comment, no-undef, no-underscore-dangle, no-param-reassign, no-plusplus, no-continue */
// @ts-nocheck
import { onMounted, watch, type Ref } from 'vue';
import { LineLayer, PolygonLayer, Scene } from '@antv/l7';
import { Map } from '@antv/l7-maps';
import { RDBSource } from 'district-data';
import {
  selectedProvince,
  realProvinceData,
  scoreToColor,
  fetchGeoJson,
  fetchCityData,
  realCityData,
  selectedYear,
  gfDrillProvince,
  isProvinceExcludedFromPanel,
} from './provinceData';

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
          .source(fullOutlineGeo)
          .shape('line')
          .color('#5DDDFF')
          .size(0.6)
          .style({ opacity: 0.7 });
        scene.addLayer(borderLayer);

        extrudeLayer.on('click', (e) => {
          const name = e.feature?.properties?.name;
          if (name && !isProvinceExcludedFromPanel(name)) {
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
            extrudeLayer.setData({ type: 'FeatureCollection', features: [...mainFeats] });
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
            applyScores();
            extrudeLayer.setData({ type: 'FeatureCollection', features: [...mainFeats] });
            extrudeLayer.show();
            borderLayer.show();
            noPanelFill.show();
            scene.setZoomAndCenter(3.2, [104.195397, 35.86166]);
            scene.setPitch(45);
            fetchCityData('', selectedYear.value);
            scene.render();
            return;
          }

          extrudeLayer.hide();
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
