import { onMounted, watch, inject, nextTick, type Ref } from 'vue';
import * as echarts from 'echarts';
import {
  yearlyData,
  indicatorLabels,
  indicatorKeys,
  findProvince,
  selectedProvince,
  selectedYear,
} from './provinceData';
import {
  mockGreenFinanceData,
  mockCarbonData,
  mockEnergyIntensityData,
  mockMacroEconomyData,
  greenFinanceIndicators,
  type MockGreenFinanceRow,
} from './mockData';

type GfValueKey = keyof Omit<MockGreenFinanceRow, 'province' | 'score'>;

function gfVal(item: MockGreenFinanceRow, key: string): number {
  return item[key as GfValueKey];
}
/* ========================================================================
 * 延迟初始化辅助：解决 v-show 下图表容器 0 尺寸的问题
 * ======================================================================== */
function useDeferredChart(tabKey: string, initFn: () => void) {
  const activeTab = inject<Ref<string>>('activeTab');
  onMounted(() => {
    if (activeTab?.value === tabKey) {
      nextTick(initFn);
    }
    if (activeTab) {
      watch(activeTab, (val) => {
        if (val === tabKey) {
          nextTick(initFn);
        }
      });
    }
  });
}
/* ========================================================================
 * 综合引力沙盘 - 堆叠柱状图 TOP 15
 * ======================================================================== */
export function useStackedBar() {
  let chart: echarts.ECharts | null = null;
  function render() {
    const year = selectedYear.value;
    const list = yearlyData[year] ?? [];
    const top = [...list].sort((a, b) => b.score - a.score).slice(0, 15);
    const provinces = top.map((p) => p.province.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, ''));
    if (!chart) {
      const el = document.getElementById('bar');
      if (!el || el.clientWidth === 0) return;
      chart = echarts.init(el, 'dark');
      window.addEventListener('resize', () => chart?.resize());
    }
    const series = indicatorKeys.map((key) => ({
      name: indicatorLabels[key],
      type: 'bar' as const,
      stack: 'total',
      emphasis: { focus: 'series' },
      data: top.map((row) => row[key]),
    }));
    chart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: { textStyle: { color: '#ccc', fontSize: 8 }, top: 2, type: 'scroll' },
        grid: { left: 4, right: 10, top: 32, bottom: 4, containLabel: true },
        xAxis: {
          type: 'value',
          axisLabel: { color: '#aaa', fontSize: 8 },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        },
        yAxis: {
          type: 'category',
          data: provinces,
          axisLabel: { color: '#ccc', fontSize: 9 },
        },
        series,
      },
      true,
    );
  }
  useDeferredChart('sandbox', () => {
    render();
    watch(selectedYear, render);
  });
}

/* ========================================================================
 * 综合引力沙盘 - 雷达图（当前选中省份 / 默认同分最高省）
 * ======================================================================== */
export function useRadar() {
  let chart: echarts.ECharts | null = null;
  function render() {
    const year = selectedYear.value;
    const list = yearlyData[year] ?? [];
    const row = selectedProvince.value
      ? findProvince(selectedProvince.value, year)
      : [...list].sort((a, b) => b.score - a.score)[0];
    if (!row) return;
    const values = indicatorKeys.map((k) => row[k]);
    const indMax = Math.max(...values, 0.02) * 1.4;
    if (!chart) {
      const el = document.getElementById('radar');
      if (!el || el.clientWidth === 0) return;
      chart = echarts.init(el, 'dark');
      window.addEventListener('resize', () => chart?.resize());
    }
    chart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item' },
        radar: {
          indicator: indicatorKeys.map((k) => ({
            name: indicatorLabels[k],
            max: indMax,
          })),
          shape: 'polygon',
          radius: '62%',
          axisName: { color: 'rgba(220,240,255,0.75)', fontSize: 10 },
          splitArea: {
            areaStyle: {
              color: [
                'rgba(0,60,120,0.12)',
                'rgba(0,20,50,0.08)',
                'rgba(0,60,120,0.06)',
                'rgba(0,20,50,0.04)',
                'rgba(0,60,120,0.02)',
              ],
            },
          },
          splitLine: {
            lineStyle: { color: '#00FFFF', opacity: 0.12, type: 'dashed' },
          },
        },
        series: [
          {
            type: 'radar',
            data: [
              {
                value: values,
                name: row.province,
                areaStyle: {
                  color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
                    { offset: 0, color: 'rgba(0,229,255,0.35)' },
                    { offset: 1, color: 'rgba(0,229,255,0.05)' },
                  ]),
                },
                lineStyle: { color: '#00e5ff', width: 2 },
              },
            ],
          },
        ],
      },
      true,
    );
  }
  useDeferredChart('sandbox', () => {
    render();
    watch([selectedYear, selectedProvince], render);
  });
}

/* ========================================================================
 * 绿色金融监测 - 七维雷达图（增强版）
 * ======================================================================== */
export function useGreenFinanceRadar(selectedProv: Ref<string>) {
  let chart: echarts.ECharts | null = null;
  let inited = false;
  function render() {
    const item = mockGreenFinanceData.find((d) => d.province === selectedProv.value) || mockGreenFinanceData[0];
    const indicator = greenFinanceIndicators.map((ind) => ({ name: ind.label, max: 0.18 }));
    const values = greenFinanceIndicators.map((ind) => gfVal(item, ind.key));
    if (!chart) {
      const el = document.getElementById('gf-radar');
      if (!el || el.clientWidth === 0) return;
      chart = echarts.init(el, 'dark');
      window.addEventListener('resize', () => chart?.resize());
    }
    chart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(10,15,30,0.9)',
          borderColor: 'rgba(0,229,255,0.3)',
          textStyle: { color: '#fff', fontSize: 12 },
          formatter() {
            let s = `<b style="color:#00e5ff">${item.province}</b><br/>`;
            greenFinanceIndicators.forEach((ind, i) => {
              const pct = (values[i] * 100).toFixed(2);
              s += `<div style="display:flex;align-items:center;gap:4px;margin:2px 0">`;
              s += `<span style="color:#aaa;width:56px;font-size:11px">${ind.label}</span>`;
              s += `<div style="flex:1;height:4px;background:rgba(0,255,255,0.1);border-radius:2px">`;
              s += `<div style="width:${
                (values[i] / 0.18) * 100
              }%;height:100%;background:linear-gradient(90deg,#00e5ff,#00FF00);border-radius:2px"></div></div>`;
              s += `<span style="color:#0f0;font-size:11px;width:40px;text-align:right">${pct}</span></div>`;
            });
            s += `<div style="margin-top:4px;border-top:1px solid rgba(0,229,255,0.2);padding-top:4px;text-align:center;color:#FFD54F;font-weight:bold">综合得分: ${(
              item.score * 100
            ).toFixed(1)}</div>`;
            return s;
          },
        },
        radar: {
          indicator,
          shape: 'polygon',
          radius: '62%',
          axisName: {
            color: 'rgba(220,240,255,0.75)',
            fontSize: 10,
            fontFamily: '"Microsoft YaHei", sans-serif',
          },
          splitArea: {
            areaStyle: {
              color: [
                'rgba(0,60,120,0.12)',
                'rgba(0,20,50,0.08)',
                'rgba(0,60,120,0.06)',
                'rgba(0,20,50,0.04)',
                'rgba(0,60,120,0.02)',
              ],
            },
          },
          splitLine: {
            lineStyle: {
              color: '#00FFFF',
              opacity: 0.12,
              type: 'dashed',
            },
          },
          axisLine: { lineStyle: { color: 'rgba(0,255,255,0.15)' } },
        },
        series: [
          {
            type: 'radar',
            data: [
              {
                value: values,
                name: item.province,
                lineStyle: {
                  color: '#00FF00',
                  width: 2,
                  shadowColor: 'rgba(0,255,0,0.5)',
                  shadowBlur: 8,
                },
                areaStyle: {
                  color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
                    { offset: 0, color: 'rgba(0,255,255,0.25)' },
                    { offset: 1, color: 'rgba(0,255,255,0.02)' },
                  ]),
                },
                itemStyle: {
                  color: '#00FFFF',
                  borderColor: '#00FF00',
                  borderWidth: 2,
                  shadowColor: 'rgba(0,255,255,0.8)',
                  shadowBlur: 10,
                },
                symbol: 'circle',
                symbolSize: 6,
                emphasis: {
                  itemStyle: {
                    shadowBlur: 20,
                    shadowColor: 'rgba(0,255,0,1)',
                  },
                },
              },
            ],
          },
        ],
        graphic: [
          {
            type: 'circle',
            shape: { r: 4 },
            style: { fill: 'rgba(0,255,255,0.3)', stroke: '#00FFFF', lineWidth: 1 },
            left: 'center',
            top: 'center',
          },
        ],
      },
      true,
    );
  }
  useDeferredChart('greenFinance', () => {
    render();
    if (!inited) {
      inited = true;
      watch(selectedProv, render);
    }
  });
}
/* ========================================================================
 * 绿色金融监测 - 南丁格尔玫瑰图
 * ======================================================================== */
const ROSE_PALETTE = [
  new echarts.graphic.LinearGradient(0, 0, 1, 1, [
    { offset: 0, color: '#00BFFF' },
    { offset: 1, color: '#004080' },
  ]),
  new echarts.graphic.LinearGradient(0, 0, 1, 1, [
    { offset: 0, color: '#00E5A0' },
    { offset: 1, color: '#005540' },
  ]),
  new echarts.graphic.LinearGradient(0, 0, 1, 1, [
    { offset: 0, color: '#FFD54F' },
    { offset: 1, color: '#996600' },
  ]),
  new echarts.graphic.LinearGradient(0, 0, 1, 1, [
    { offset: 0, color: '#CE93D8' },
    { offset: 1, color: '#6A1B9A' },
  ]),
  new echarts.graphic.LinearGradient(0, 0, 1, 1, [
    { offset: 0, color: '#FF8A65' },
    { offset: 1, color: '#BF360C' },
  ]),
  new echarts.graphic.LinearGradient(0, 0, 1, 1, [
    { offset: 0, color: '#4FC3F7' },
    { offset: 1, color: '#01579B' },
  ]),
  new echarts.graphic.LinearGradient(0, 0, 1, 1, [
    { offset: 0, color: '#AED581' },
    { offset: 1, color: '#33691E' },
  ]),
];
const ROSE_SOLID_COLORS = ['#00BFFF', '#00E5A0', '#FFD54F', '#CE93D8', '#FF8A65', '#4FC3F7', '#AED581'];
export function useGreenFinanceRose(selectedProv: Ref<string>) {
  let chart: echarts.ECharts | null = null;
  let inited = false;
  function render() {
    const item = mockGreenFinanceData.find((d) => d.province === selectedProv.value) || mockGreenFinanceData[0];
    const total = greenFinanceIndicators.reduce((s, ind) => s + gfVal(item, ind.key), 0);
    const data = greenFinanceIndicators.map((ind, i) => ({
      value: +(gfVal(item, ind.key) * 100).toFixed(2),
      name: ind.label,
      itemStyle: {
        color: ROSE_PALETTE[i],
        borderColor: 'rgba(255,255,255,0.15)',
        borderWidth: 1,
        borderRadius: 6,
        shadowBlur: 12,
        shadowColor: `${ROSE_SOLID_COLORS[i]}40`,
      },
    }));
    if (!chart) {
      const el = document.getElementById('gf-rose');
      if (!el || el.clientWidth === 0) return;
      chart = echarts.init(el, 'dark');
      window.addEventListener('resize', () => chart?.resize());
    }
    chart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(10,15,30,0.9)',
          borderColor: 'rgba(0,229,255,0.3)',
          textStyle: { color: '#fff' },
          formatter: (p: { name: string; value: number; dataIndex: number }) =>
            `<b style="color:${ROSE_SOLID_COLORS[p.dataIndex]}">${p.name}</b><br/>数值: ${p.value}<br/>占比: ${(
              (gfVal(item, greenFinanceIndicators[p.dataIndex].key) / total) *
              100
            ).toFixed(1)}%`,
        },
        series: [
          {
            type: 'pie',
            roseType: 'area',
            radius: ['22%', '68%'],
            center: ['50%', '52%'],
            data,
            label: {
              color: '#00FF00',
              fontSize: 10,
              textShadowColor: 'rgba(0,255,0,0.4)',
              textShadowBlur: 4,
              formatter: (p: { name: string; percent: number }) => `{name|${p.name}}\n{pct|${p.percent}%}`,
              rich: {
                name: { color: '#00FF00', fontSize: 10, lineHeight: 14 },
                pct: { color: 'rgba(0,255,255,0.7)', fontSize: 9, lineHeight: 12 },
              },
            },
            labelLine: {
              lineStyle: { color: 'rgba(0,255,255,0.35)', type: 'dashed', width: 1 },
              length: 12,
              length2: 14,
            },
            animationType: 'scale',
            animationEasing: 'elasticOut',
            animationDelay: (idx: number) => idx * 80,
          },
        ],
        graphic: [
          {
            type: 'text',
            left: 'center',
            top: '48%',
            style: {
              text: (item.score * 100).toFixed(1),
              fill: '#00e5ff',
              fontSize: 22,
              fontWeight: 'bold',
              fontFamily: '"DIN Alternate", "DIN", sans-serif',
              textShadowColor: 'rgba(0,229,255,0.5)',
              textShadowBlur: 10,
              textAlign: 'center',
            },
          },
          {
            type: 'text',
            left: 'center',
            top: '55%',
            style: {
              text: '综合指数',
              fill: 'rgba(0,229,255,0.5)',
              fontSize: 10,
              textAlign: 'center',
            },
          },
        ],
      },
      true,
    );
  }
  useDeferredChart('greenFinance', () => {
    render();
    if (!inited) {
      inited = true;
      watch(selectedProv, render);
    }
  });
}
/* ========================================================================
 * 碳排放底色 - 横向柱状图 TOP 10
 * ======================================================================== */
export function useCarbonBar() {
  let chart: echarts.ECharts | null = null;
  function render() {
    const sorted = [...mockCarbonData]
      .sort((a, b) => b.carbonEmission - a.carbonEmission)
      .slice(0, 10)
      .reverse();
    const provinces = sorted.map((d) => d.province.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, ''));
    const values = sorted.map((d) => d.carbonEmission);
    if (!chart) {
      const el = document.getElementById('carbon-bar');
      if (!el || el.clientWidth === 0) return;
      chart = echarts.init(el, 'dark');
      window.addEventListener('resize', () => chart?.resize());
    }
    chart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (params: { name: string; value: number }[]) =>
            `<b>${params[0].name}</b><br/>碳排放: ${params[0].value.toLocaleString()} 万吨`,
        },
        grid: { left: 10, right: 30, top: 20, bottom: 10, containLabel: true },
        xAxis: {
          type: 'value',
          axisLabel: { color: '#aaa', fontSize: 9 },
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
        },
        yAxis: {
          type: 'category',
          data: provinces,
          axisLabel: { color: '#ccc', fontSize: 10 },
          axisLine: { lineStyle: { color: '#333' } },
        },
        series: [
          {
            type: 'bar',
            data: values.map((v, i) => {
              let endColor = '#ffcc80';
              if (i >= 7) endColor = '#ff4444';
              else if (i >= 4) endColor = '#ff9800';
              return {
                value: v,
                itemStyle: {
                  color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                    { offset: 0, color: 'rgba(255,80,80,0.2)' },
                    { offset: 1, color: endColor },
                  ]),
                  borderRadius: [0, 4, 4, 0],
                  shadowColor: 'rgba(255,80,80,0.3)',
                  shadowBlur: 6,
                },
              };
            }),
            barWidth: '55%',
            label: {
              show: true,
              position: 'right',
              color: 'rgba(255,180,180,0.8)',
              fontSize: 10,
              formatter: (p: { value: number }) => p.value.toLocaleString(),
            },
          },
        ],
      },
      true,
    );
  }
  useDeferredChart('carbon', render);
}
/* ========================================================================
 * 能耗强度分析 - 散点图 + 线性回归
 * ======================================================================== */
export function useEnergyScatter() {
  let chart: echarts.ECharts | null = null;
  function render() {
    const data = mockEnergyIntensityData;
    const scatterData = data.map((d) => [d.score, d.energyConsume, d.province]);
    const n = data.length;
    const sumX = data.reduce((s, d) => s + d.score, 0);
    const sumY = data.reduce((s, d) => s + d.energyConsume, 0);
    const sumXY = data.reduce((s, d) => s + d.score * d.energyConsume, 0);
    const sumX2 = data.reduce((s, d) => s + d.score * d.score, 0);
    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;
    const xMin = Math.min(...data.map((d) => d.score)) - 0.05;
    const xMax = Math.max(...data.map((d) => d.score)) + 0.05;
    const regressionLine = [
      [xMin, slope * xMin + intercept],
      [xMax, slope * xMax + intercept],
    ];
    if (!chart) {
      const el = document.getElementById('energy-scatter');
      if (!el || el.clientWidth === 0) return;
      chart = echarts.init(el, 'dark');
      window.addEventListener('resize', () => chart?.resize());
    }
    chart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item',
          formatter: (p: { seriesIndex: number; value: [number, number, string] }) => {
            if (p.seriesIndex === 1) return '';
            return `<b>${p.value[2]}</b><br/>绿色金融指数: ${p.value[0]}<br/>能耗强度: ${p.value[1]}`;
          },
        },
        grid: { left: 50, right: 30, top: 40, bottom: 50 },
        xAxis: {
          type: 'value',
          name: '绿色金融指数',
          nameTextStyle: { color: '#0ff', fontSize: 11 },
          axisLabel: { color: '#aaa', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } },
        },
        yAxis: {
          type: 'value',
          name: '能耗强度',
          nameTextStyle: { color: '#0ff', fontSize: 11 },
          axisLabel: { color: '#aaa', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } },
        },
        series: [
          {
            type: 'scatter',
            data: scatterData,
            symbolSize: 12,
            itemStyle: {
              color: new echarts.graphic.RadialGradient(0.5, 0.5, 0.5, [
                { offset: 0, color: '#00e5ff' },
                { offset: 1, color: 'rgba(0,229,255,0.3)' },
              ]),
              shadowBlur: 8,
              shadowColor: 'rgba(0,229,255,0.4)',
            },
            emphasis: {
              itemStyle: { shadowBlur: 16, shadowColor: 'rgba(0,229,255,0.7)' },
            },
          },
          {
            type: 'line',
            data: regressionLine,
            symbol: 'none',
            lineStyle: {
              color: '#ff6d00',
              width: 2,
              type: 'dashed',
              shadowBlur: 6,
              shadowColor: 'rgba(255,109,0,0.4)',
            },
            tooltip: { show: false },
            z: 0,
          },
        ],
      },
      true,
    );
  }
  useDeferredChart('energy', render);
}
/* ========================================================================
 * 宏观经济动态 - 双 Y 轴混合图（GDP 柱 + 碳排放折线）
 * ======================================================================== */
export function useMacroChart() {
  let chart: echarts.ECharts | null = null;
  function render() {
    const years = mockMacroEconomyData.map((d) => d.year);
    const gdps = mockMacroEconomyData.map((d) => d.gdp);
    const carbons = mockMacroEconomyData.map((d) => d.carbonEmission);
    if (!chart) {
      const el = document.getElementById('macro-chart');
      if (!el || el.clientWidth === 0) return;
      chart = echarts.init(el, 'dark');
      window.addEventListener('resize', () => chart?.resize());
    }
    chart.setOption(
      {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' },
          formatter: (params: { axisValue: string; marker: string; seriesName: string; value: number }[]) => {
            let s = `<b>${params[0].axisValue}年</b><br/>`;
            params.forEach((row) => {
              s += `${row.marker} ${row.seriesName}: ${row.value.toLocaleString()}<br/>`;
            });
            return s;
          },
        },
        legend: {
          data: ['GDP（亿元）', '碳排放（万吨）'],
          textStyle: { color: '#ccc', fontSize: 11 },
          top: 6,
        },
        grid: { left: 55, right: 55, top: 45, bottom: 30 },
        xAxis: {
          type: 'category',
          data: years,
          axisLabel: { color: '#aaa', fontSize: 10 },
          axisLine: { lineStyle: { color: '#555' } },
        },
        yAxis: [
          {
            type: 'value',
            name: 'GDP（亿元）',
            nameTextStyle: { color: '#FFD54F', fontSize: 10 },
            axisLabel: {
              color: '#aaa',
              fontSize: 9,
              formatter: (v: number) => (v >= 10000 ? `${(v / 10000).toFixed(1)}万` : `${v}`),
            },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
          },
          {
            type: 'value',
            name: '碳排放（万吨）',
            nameTextStyle: { color: '#00e5ff', fontSize: 10 },
            axisLabel: { color: '#aaa', fontSize: 9 },
            splitLine: { show: false },
          },
        ],
        series: [
          {
            name: 'GDP（亿元）',
            type: 'bar',
            yAxisIndex: 0,
            data: gdps,
            barWidth: '50%',
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#FFD54F' },
                { offset: 1, color: 'rgba(255,152,0,0.2)' },
              ]),
              borderRadius: [3, 3, 0, 0],
            },
          },
          {
            name: '碳排放（万吨）',
            type: 'line',
            yAxisIndex: 1,
            data: carbons,
            smooth: true,
            lineStyle: { color: '#00e5ff', width: 3, shadowBlur: 8, shadowColor: 'rgba(0,229,255,0.4)' },
            itemStyle: { color: '#00e5ff' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(0,229,255,0.2)' },
                { offset: 1, color: 'rgba(0,229,255,0)' },
              ]),
            },
          },
        ],
      },
      true,
    );
  }
  useDeferredChart('macro', render);
}
