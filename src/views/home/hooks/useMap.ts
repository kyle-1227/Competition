/* eslint-disable @typescript-eslint/ban-ts-comment, no-undef, no-underscore-dangle, no-param-reassign, no-plusplus, no-continue */
// @ts-nocheck
import { onMounted, watch } from 'vue';
import { LineLayer, PointLayer, PolygonLayer, Scene } from '@antv/l7';
import { Map } from '@antv/l7-maps';
import { RDBSource } from 'district-data';
import {
  selectedProvince,
  selectedYear,
  tfeeThreshold,
  yearlyData,
  provinceCoords,
  fullToShortName,
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
function generateDynamicLines(year: number) {
  const data = yearlyData[year] || yearlyData[2024];
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

  const activeCities: CityPoint[] = [...activeSet].map((fullName) => {
    const coord = provinceCoords[fullName];
    return { lng: coord[0], lat: coord[1], name: fullToShortName[fullName] || fullName };
  });

  return { greenLines, redLines, activeCities };
}

function buildScoreMap(year: number): Record<string, number> {
  const list = yearlyData[year] || yearlyData[2024];
  const map: Record<string, number> = {};
  list.forEach((p) => {
    map[p.province] = p.score;
  });
  return map;
}

function scoreToColor(score: number): string {
  if (score > 0.7) return '#00e5ff';
  if (score > 0.5) return '#2979ff';
  if (score > 0.3) return '#7c4dff';
  if (score > 0.15) return '#ff6d00';
  return '#ff1744';
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

      // ========== Province 3D extrude ==========
      source.getData({ level: 'province', precision: 'low' }).then((geoData) => {
        const features = geoData.features.filter((f) => f.properties.name);
        const scoreMap = buildScoreMap(selectedYear.value);

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

        watch(selectedYear, (year) => {
          const newScoreMap = buildScoreMap(year);
          features.forEach((f) => {
            const s = newScoreMap[f.properties.name] || 0;
            f.properties._score = s ** 1.6;
            f.properties._color = scoreToColor(s);
          });
          const newGeo = { type: 'FeatureCollection', features: [...features] };
          provinceExtrudeLayer?.setData(newGeo);
          provinceBorderLayer?.setData(newGeo);

          // 动态更新飞线和雷达
          const { greenLines, redLines, activeCities } = generateDynamicLines(year);
          greenFlyLayer?.setData(greenLines, LINE_PARSER);
          redFlyLayer?.setData(redLines, LINE_PARSER);
          radarLayer?.setData(activeCities, POINT_PARSER);
          scene.render();
        });
      });

      // ========== 动态飞线初始化 ==========
      const initial = generateDynamicLines(selectedYear.value);

      // 绿色飞线：正向空间溢出（协同减排）
      greenFlyLayer = new LineLayer({ blend: 'normal', zIndex: 8 })
        .source(initial.greenLines, LINE_PARSER)
        .size(1.8)
        .shape('arc3d')
        .color('#00e5ff')
        .animate({ interval: 0.08, trailLength: 0.5, duration: 0.6 })
        .style({ sourceColor: '#00e5ff', targetColor: '#76ff03', thetaOffset: 0.8, opacity: 0.9 });
      scene.addLayer(greenFlyLayer);

      // 红色飞线：负向空间交互（污染转移）
      redFlyLayer = new LineLayer({ blend: 'normal', zIndex: 8 })
        .source(initial.redLines, LINE_PARSER)
        .size(2)
        .shape('arc3d')
        .color('#ff4444')
        .animate({ interval: 0.08, trailLength: 0.4, duration: 0.5 })
        .style({ sourceColor: '#ff4444', targetColor: '#ffab00', thetaOffset: 1, opacity: 1 });
      scene.addLayer(redFlyLayer);

      // TFEE 阈值联动：红色飞线变细变淡
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

      // ========== 飞线关联省份：雷达脉冲效果 ==========
      radarLayer = new PointLayer({ zIndex: 12 })
        .source(initial.activeCities, POINT_PARSER)
        .shape('circle')
        .animate(true)
        .size(30)
        .color('#00e5ff')
        .style({ opacity: 0.8 });
      scene.addLayer(radarLayer);

      // ========== 全部 31 省名称标注 ==========
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
    });
  });
}

export default {};
