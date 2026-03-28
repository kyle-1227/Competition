/** 绿色金融监测七维指标（无 mock 数据） */
export const greenFinanceIndicators = [
  { key: 'greenCredit', label: '绿色信贷' },
  { key: 'greenInvest', label: '绿色投资' },
  { key: 'greenInsurance', label: '绿色保险' },
  { key: 'greenBond', label: '绿色债券' },
  { key: 'greenSupport', label: '绿色支持' },
  { key: 'greenFund', label: '绿色基金' },
  { key: 'greenEquity', label: '绿色权益' },
] as const;

export interface GreenFinanceMonitorRow {
  province: string;
  score: number;
  greenCredit: number;
  greenInvest: number;
  greenInsurance: number;
  greenBond: number;
  greenSupport: number;
  greenFund: number;
  greenEquity: number;
}
