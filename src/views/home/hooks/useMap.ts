// @ts-nocheck
/* eslint-disable no-undef */
import { onMounted, watch } from 'vue';
import { LineLayer, PointLayer, PolygonLayer, Scene } from '@antv/l7';
import { Map } from '@antv/l7-maps';
import { RDBSource } from 'district-data';
import {
  selectedProvince,
  selectedYear,
  tfeeThreshold,
  yearlyData,
} from './provinceData';

// ===== 正向空间溢出（协同减排）=====
const greenLines = [
  { x: '121.473', y: '31.230', x1: '118.797', y1: '32.060', from: '上海', to: '南京' },
  { x: '121.473', y: '31.230', x1: '120.154', y1: '30.287', from: '上海', to: '杭州' },
  { x: '121.473', y: '31.230', x1: '117.283', y1: '31.861', from: '上海', to: '合肥' },
  { x: '113.264', y: '23.129', x1: '112.982', y1: '28.194', from: '广州', to: '长沙' },
  { x: '113.264', y: '23.129', x1: '108.320', y1: '22.825', from: '广州', to: '南宁' },
  { x: '113.264', y: '23.129', x1: '119.306', y1: '26.075', from: '广州', to: '福州' },
  { x: '116.407', y: '39.904', x1: '117.190', y1: '39.126', from: '北京', to: '天津' },
  { x: '116.407', y: '39.904', x1: '117.001', y1: '36.676', from: '北京', to: '济南' },
  { x: '116.407', y: '39.904', x1: '114.502', y1: '38.045', from: '北京', to: '石家庄' },
  { x: '120.154', y: '30.287', x1: '115.892', y1: '28.676', from: '杭州', to: '南昌' },
  { x: '114.299', y: '30.584', x1: '112.982', y1: '28.194', from: '武汉', to: '长沙' },
];

// ===== 负向空间交互（污染转移）=====
const redLines = [
  { x: '121.473', y: '31.230', x1: '115.892', y1: '28.676', from: '上海', to: '南昌' },
  { x: '118.797', y: '32.060', x1: '117.283', y1: '31.861', from: '南京', to: '合肥' },
  { x: '113.264', y: '23.129', x1: '106.713', y1: '26.578', from: '广州', to: '贵阳' },
  { x: '116.407', y: '39.904', x1: '111.678', y1: '40.854', from: '北京', to: '呼和浩特' },
  { x: '117.001', y: '36.676', x1: '113.665', y1: '34.758', from: '济南', to: '郑州' },
  { x: '120.154', y: '30.287', x1: '106.552', y1: '29.563', from: '杭州', to: '重庆' },
  { x: '118.797', y: '32.060', x1: '104.066', y1: '30.659', from: '南京', to: '成都' },
];

// 飞线节点（城市标注）
const hubCities = [
  { lng: '121.473', lat: '31.230', name: '上海' },
  { lng: '116.407', lat: '39.904', name: '北京' },
  { lng: '113.264', lat: '23.129', name: '广州' },
  { lng: '120.154', lat: '30.287', name: '杭州' },
  { lng: '118.797', lat: '32.060', name: '南京' },
  { lng: '117.190', lat: '39.126', name: '天津' },
  { lng: '114.299', lat: '30.584', name: '武汉' },
  { lng: '117.001', lat: '36.676', name: '济南' },
  { lng: '117.283', lat: '31.861', name: '合肥' },
  { lng: '112.982', lat: '28.194', name: '长沙' },
  { lng: '115.892', lat: '28.676', name: '南昌' },
  { lng: '108.320', lat: '22.825', name: '南宁' },
  { lng: '119.306', lat: '26.075', name: '福州' },
  { lng: '114.502', lat: '38.045', name: '石家庄' },
  { lng: '113.665', lat: '34.758', name: '郑州' },
  { lng: '106.713', lat: '26.578', name: '贵阳' },
  { lng: '106.552', lat: '29.563', name: '重庆' },
  { lng: '104.066', lat: '30.659', name: '成都' },
  { lng: '111.678', lat: '40.854', name: '呼和浩特' },
];

function buildScoreMap(year: number): Record<string, number> {
  const list = yearlyData[year] || yearlyData[2024];
  const map: Record<string, number> = {};
  list.forEach((p) => { map[p.province] = p.score; });
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
          f.properties._score = Math.pow(s, 1.6);
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
            f.properties._score = Math.pow(s, 1.6);
            f.properties._color = scoreToColor(s);
          });
          const newGeo = { type: 'FeatureCollection', features: [...features] };
          provinceExtrudeLayer?.setData(newGeo);
          provinceBorderLayer?.setData(newGeo);
        });
      });

      // ========== 绿色飞线：正向空间溢出（协同减排）==========
      const greenFlyLayer = new LineLayer({ blend: 'normal', zIndex: 8 })
        .source(greenLines, {
          parser: { type: 'json', x: 'x', y: 'y', x1: 'x1', y1: 'y1' },
        })
        .size(1.8)
        .shape('arc3d')
        .color('#00e5ff')
        .animate({ interval: 0.08, trailLength: 0.5, duration: 0.6 })
        .style({ sourceColor: '#00e5ff', targetColor: '#76ff03', thetaOffset: 0.8, opacity: 0.9 });
      scene.addLayer(greenFlyLayer);

      // ========== 红色飞线：负向空间交互（污染转移）==========
      redFlyLayer = new LineLayer({ blend: 'normal', zIndex: 8 })
        .source(redLines, {
          parser: { type: 'json', x: 'x', y: 'y', x1: 'x1', y1: 'y1' },
        })
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

      // ========== 城市节点：脉冲圆点 ==========
      const dotLayer = new PointLayer({ zIndex: 12 })
        .source(hubCities, { parser: { type: 'json', x: 'lng', y: 'lat' } })
        .shape('circle')
        .animate(true)
        .size(30)
        .color('#00e5ff')
        .style({ opacity: 0.8 });
      scene.addLayer(dotLayer);

      // ========== 城市名称标注 ==========
      const textLayer = new PointLayer({ zIndex: 15 })
        .source(hubCities, { parser: { type: 'json', x: 'lng', y: 'lat' } })
        .shape('name', 'text')
        .size(12)
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
      scene.addLayer(textLayer);
    });
  });
}

export default {};
