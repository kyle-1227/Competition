// @ts-nocheck
import { onMounted, watch } from 'vue';
import * as echarts from 'echarts';
import {
  yearlyData,
  indicatorLabels,
  indicatorKeys,
  findProvince,
  selectedProvince,
  selectedYear,
} from './provinceData';

const colors = ['#00e5ff', '#00e676', '#ffea00', '#ff6d00', '#d500f9', '#2979ff', '#1de9b6'];

function getYearData(year: number) {
  return yearlyData[year] || yearlyData[2024];
}

export function useStackedBar() {
  let chart: echarts.ECharts | null = null;

  function render(year: number) {
    const data = getYearData(year);
    const sorted = [...data].sort((a, b) => b.score - a.score).slice(0, 15);
    const provinces = sorted.map((d) => d.province.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, ''));

    const series = indicatorKeys.map((key, i) => ({
      name: indicatorLabels[key],
      type: 'bar',
      stack: 'total',
      barWidth: '60%',
      data: sorted.map((d) => +(d[key] * 100).toFixed(2)),
      itemStyle: { color: colors[i] },
    }));

    if (!chart) {
      chart = echarts.init(document.getElementById('bar')!, 'dark');
      window.addEventListener('resize', () => chart?.resize());
    }

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter(params) {
          let s = `<b>${params[0].axisValue}（${year}）</b><br/>`;
          params.forEach((p) => { s += `${p.marker} ${p.seriesName}: ${p.value.toFixed(2)}<br/>`; });
          const total = params.reduce((sum, p) => sum + p.value, 0);
          s += `<b>合计: ${total.toFixed(2)}</b>`;
          return s;
        },
      },
      legend: { bottom: 0, textStyle: { color: '#ccc', fontSize: 9 }, itemWidth: 10, itemHeight: 8 },
      grid: { left: 8, right: 8, top: 30, bottom: 55, containLabel: true },
      xAxis: {
        type: 'category',
        data: provinces,
        axisLabel: { color: '#aaa', fontSize: 9, rotate: 35 },
        axisLine: { lineStyle: { color: '#555' } },
      },
      yAxis: {
        type: 'value',
        name: '指数(%)',
        nameTextStyle: { color: '#aaa', fontSize: 10 },
        axisLabel: { color: '#aaa', fontSize: 9 },
        splitLine: { lineStyle: { color: '#333' } },
      },
      series,
    }, true);
  }

  onMounted(() => {
    render(selectedYear.value);
    watch(selectedYear, (y) => render(y));
  });
}

export function useRadar() {
  let chart: echarts.ECharts | null = null;

  function renderRadar(province?: string, year?: number) {
    const yr = year ?? selectedYear.value;
    const p = province ? findProvince(province, yr) : getYearData(yr)[0];
    if (!p) return;

    const indicator = indicatorKeys.map((key) => ({ name: indicatorLabels[key], max: 0.18 }));
    const values = indicatorKeys.map((key) => p[key]);
    const displayName = p.province.replace(/(省|市|自治区|壮族|回族|维吾尔)/g, '');

    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'item',
        formatter() {
          let s = `<b>${displayName}（${yr}）</b><br/>`;
          indicatorKeys.forEach((key, i) => { s += `${indicatorLabels[key]}: ${(values[i] * 100).toFixed(2)}<br/>`; });
          s += `<b>综合指数: ${(p.score * 100).toFixed(2)}</b>`;
          return s;
        },
      },
      radar: {
        indicator,
        shape: 'polygon',
        radius: '60%',
        axisName: { color: '#0ff', fontSize: 10 },
        splitArea: { areaStyle: { color: ['rgba(0,255,255,0.02)', 'rgba(0,255,255,0.06)'] } },
        splitLine: { lineStyle: { color: 'rgba(0,255,255,0.15)' } },
        axisLine: { lineStyle: { color: 'rgba(0,255,255,0.2)' } },
      },
      series: [{
        type: 'radar',
        data: [{
          value: values,
          name: displayName,
          areaStyle: { color: 'rgba(0,229,255,0.25)' },
          lineStyle: { color: '#00e5ff', width: 2 },
          itemStyle: { color: '#00e5ff' },
          symbol: 'circle',
          symbolSize: 5,
        }],
      }],
    };

    if (!chart) {
      chart = echarts.init(document.getElementById('radar')!, 'dark');
      window.addEventListener('resize', () => chart?.resize());
    }
    chart.setOption(option, true);
  }

  onMounted(() => {
    renderRadar();
    watch(selectedProvince, (name) => { if (name) renderRadar(name); });
    watch(selectedYear, () => { renderRadar(selectedProvince.value || undefined); });
  });
}

export default {};
