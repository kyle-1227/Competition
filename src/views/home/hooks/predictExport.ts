import type { PredictLevel } from '@/api/modules/dashboard-carbon-predict';
import type { PredictContributionBreakdown } from './useCarbonPredictV2';

type ExportCell = string | number | null | undefined;

export interface PredictExportSeriesPoint {
  year: number;
  displayValue: number | null;
  rawValue: number | null;
}

export interface PredictExportScenarioSeries {
  key: string;
  label: string;
  points: PredictExportSeriesPoint[];
}

export interface PredictExportBandPoint {
  year: number;
  displayMin: number | null;
  displayMax: number | null;
  rawMin: number | null;
  rawMax: number | null;
}

export interface PredictExportSummaryRow {
  label: string;
  year?: number | string | null;
  displayValue?: ExportCell;
  rawValue?: ExportCell;
  unit?: string;
  note?: string;
}

export interface PredictExportContext {
  level: PredictLevel;
  province: string;
  city?: string | null;
  entityLabel: string;
  compareLabel: string;
  target: string;
  selectedMode: string;
  sourceMode: string;
  weightType: string;
  historySeries: PredictExportSeriesPoint[];
  scenarios: PredictExportScenarioSeries[];
  selectedModeSeries: PredictExportScenarioSeries;
  compareHistorySeries?: PredictExportSeriesPoint[];
  compareSelectedModeSeries?: PredictExportSeriesPoint[];
  scenarioBand: PredictExportBandPoint[];
  summaryRows: PredictExportSummaryRow[];
  contributionBreakdown?: PredictContributionBreakdown | null;
  controlSnapshot?: Record<string, number> | null;
  exportTime?: Date;
}

export interface PredictExportRow {
  exportTime: string;
  level: PredictLevel;
  province: string;
  city: string;
  entityLabel: string;
  compareLabel: string;
  target: string;
  selectedMode: string;
  sourceMode: string;
  weightType: string;
  section: string;
  scenarioKey: string;
  seriesLabel: string;
  year: string | number;
  displayValue: ExportCell;
  rawValue: ExportCell;
  unit: string;
  note: string;
}

const EXPORT_COLUMNS: Array<keyof PredictExportRow> = [
  'exportTime',
  'level',
  'province',
  'city',
  'entityLabel',
  'compareLabel',
  'target',
  'selectedMode',
  'sourceMode',
  'weightType',
  'section',
  'scenarioKey',
  'seriesLabel',
  'year',
  'displayValue',
  'rawValue',
  'unit',
  'note',
];

function formatExportTimestamp(date: Date) {
  const pad = (value: number) => String(value).padStart(2, '0');
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hour = pad(date.getHours());
  const minute = pad(date.getMinutes());
  const second = pad(date.getSeconds());
  return {
    display: `${year}-${month}-${day} ${hour}:${minute}:${second}`,
    fileStamp: `${year}${month}${day}_${hour}${minute}${second}`,
  };
}

function sanitizeFilenamePart(value: string) {
  return value.replace(/[\\/:*?"<>|]/g, '-').trim() || 'unknown';
}

function toCsvCell(value: ExportCell) {
  if (value == null) return '';
  const text = String(value);
  if (/[",\r\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function downloadCsv(filename: string, rows: PredictExportRow[]) {
  const lines = [
    EXPORT_COLUMNS.join(','),
    ...rows.map((row) => EXPORT_COLUMNS.map((column) => toCsvCell(row[column])).join(',')),
  ];
  const blob = new Blob([`\uFEFF${lines.join('\r\n')}`], { type: 'text/csv;charset=utf-8;' });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(href);
}

function createBaseRow(context: PredictExportContext, exportTime: string): Omit<PredictExportRow, 'section' | 'scenarioKey' | 'seriesLabel' | 'year' | 'displayValue' | 'rawValue' | 'unit' | 'note'> {
  return {
    exportTime,
    level: context.level,
    province: context.province,
    city: context.city ?? '',
    entityLabel: context.entityLabel,
    compareLabel: context.compareLabel,
    target: context.target,
    selectedMode: context.selectedMode,
    sourceMode: context.sourceMode,
    weightType: context.weightType,
  };
}

function buildPointRows(
  context: PredictExportContext,
  exportTime: string,
  section: PredictExportRow['section'],
  scenarioKey: string,
  seriesLabel: string,
  points: PredictExportSeriesPoint[],
  unit: string,
  note = '',
): PredictExportRow[] {
  const base = createBaseRow(context, exportTime);
  return points.map((point) => ({
    ...base,
    section,
    scenarioKey,
    seriesLabel,
    year: point.year,
    displayValue: point.displayValue,
    rawValue: point.rawValue,
    unit,
    note,
  }));
}

function buildSummaryRows(context: PredictExportContext, exportTime: string): PredictExportRow[] {
  const base = createBaseRow(context, exportTime);
  return context.summaryRows.map((item) => ({
    ...base,
    section: 'summary',
    scenarioKey: context.selectedMode,
    seriesLabel: item.label,
    year: item.year ?? '',
    displayValue: item.displayValue ?? '',
    rawValue: item.rawValue ?? '',
    unit: item.unit ?? '',
    note: item.note ?? '',
  }));
}

function buildBandRows(context: PredictExportContext, exportTime: string): PredictExportRow[] {
  const base = createBaseRow(context, exportTime);
  return context.scenarioBand.flatMap((item) => ([
    {
      ...base,
      section: 'scenario_band',
      scenarioKey: 'band',
      seriesLabel: '情景区间下界',
      year: item.year,
      displayValue: item.displayMin,
      rawValue: item.rawMin,
      unit: '吨/万元',
      note: '情景区间，不是统计置信区间',
    },
    {
      ...base,
      section: 'scenario_band',
      scenarioKey: 'band',
      seriesLabel: '情景区间上界',
      year: item.year,
      displayValue: item.displayMax,
      rawValue: item.rawMax,
      unit: '吨/万元',
      note: '情景区间，不是统计置信区间',
    },
  ]));
}

function buildContributionRows(context: PredictExportContext, exportTime: string): PredictExportRow[] {
  if (!context.contributionBreakdown) return [];
  const base = createBaseRow(context, exportTime);
  const rows: Array<[string, number]> = [
    ['baselineTrend', context.contributionBreakdown.baselineTrend],
    ['core', context.contributionBreakdown.core],
    ['control', context.contributionBreakdown.control],
    ['policy', context.contributionBreakdown.policy],
    ['spatial', context.contributionBreakdown.spatial],
    ['mediator', context.contributionBreakdown.mediator],
  ];
  const note = context.controlSnapshot
    ? Object.entries(context.controlSnapshot).map(([key, value]) => `${key}=${Math.round(value * 100)}%`).join('; ')
    : '';

  return rows.map(([label, value]) => ({
    ...base,
    section: 'custom_contribution',
    scenarioKey: 'custom',
    seriesLabel: label,
    year: '',
    displayValue: value,
    rawValue: value,
    unit: '同图表展示口径',
    note,
  }));
}

export function buildPredictExportRows(context: PredictExportContext): PredictExportRow[] {
  const timestamp = formatExportTimestamp(context.exportTime ?? new Date());
  const rows: PredictExportRow[] = [
    ...buildSummaryRows(context, timestamp.display),
    ...buildPointRows(context, timestamp.display, 'entity_history', 'history', `${context.entityLabel}·历史观测`, context.historySeries, '吨/万元'),
    ...context.scenarios.flatMap((scenario) =>
      buildPointRows(context, timestamp.display, 'entity_scenario', scenario.key, scenario.label, scenario.points, '吨/万元'),
    ),
    ...buildPointRows(
      context,
      timestamp.display,
      'entity_selected_mode',
      context.selectedModeSeries.key,
      context.selectedModeSeries.label,
      context.selectedModeSeries.points,
      '吨/万元',
    ),
    ...(context.compareHistorySeries?.length
      ? buildPointRows(context, timestamp.display, 'compare_history', 'history', `${context.compareLabel}·历史观测`, context.compareHistorySeries, '吨/万元')
      : []),
    ...(context.compareSelectedModeSeries?.length
      ? buildPointRows(context, timestamp.display, 'compare_selected_mode', context.selectedModeSeries.key, `${context.compareLabel}·当前模式`, context.compareSelectedModeSeries, '吨/万元')
      : []),
    ...buildBandRows(context, timestamp.display),
    ...buildContributionRows(context, timestamp.display),
  ];

  return rows;
}

export function buildPredictExportFilename(context: PredictExportContext) {
  const timestamp = formatExportTimestamp(context.exportTime ?? new Date());
  const level = context.level === 'city' ? '市级' : '省级';
  const region = context.level === 'city'
    ? `${context.province}-${context.city ?? context.entityLabel}`
    : context.province;
  return `预测结果_${level}_${sanitizeFilenamePart(region)}_${sanitizeFilenamePart(context.selectedMode)}_${timestamp.fileStamp}.csv`;
}

export function exportPredictCsv(context: PredictExportContext) {
  const rows = buildPredictExportRows(context);
  const filename = buildPredictExportFilename(context);
  downloadCsv(filename, rows);
  return filename;
}
