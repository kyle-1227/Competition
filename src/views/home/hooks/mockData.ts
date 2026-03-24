export const greenFinanceIndicators = [
  { key: 'greenCredit', label: '绿色信贷' },
  { key: 'greenInvest', label: '绿色投资' },
  { key: 'greenInsurance', label: '绿色保险' },
  { key: 'greenBond', label: '绿色债券' },
  { key: 'greenSupport', label: '绿色支持' },
  { key: 'greenFund', label: '绿色基金' },
  { key: 'greenEquity', label: '绿色权益' },
];
/**

 * 屏二：碳排放底色 Mock 数据
 */
export const mockCarbonData = [
  { province: '山东省', carbonEmission: 89200 },
  { province: '河北省', carbonEmission: 78500 },
  { province: '江苏省', carbonEmission: 72300 },
  { province: '内蒙古自治区', carbonEmission: 69800 },
  { province: '广东省', carbonEmission: 65400 },
  { province: '山西省', carbonEmission: 62100 },
  { province: '河南省', carbonEmission: 58700 },
  { province: '辽宁省', carbonEmission: 55200 },
  { province: '浙江省', carbonEmission: 51800 },
  { province: '四川省', carbonEmission: 48900 },
  { province: '湖北省', carbonEmission: 45600 },
  { province: '安徽省', carbonEmission: 43200 },
  { province: '湖南省', carbonEmission: 40800 },
  { province: '福建省', carbonEmission: 38400 },
  { province: '陕西省', carbonEmission: 36700 },
  { province: '黑龙江省', carbonEmission: 34200 },
  { province: '江西省', carbonEmission: 31500 },
  { province: '重庆市', carbonEmission: 29800 },
  { province: '吉林省', carbonEmission: 27400 },
  { province: '广西壮族自治区', carbonEmission: 25600 },
  { province: '云南省', carbonEmission: 23800 },
  { province: '贵州省', carbonEmission: 22100 },
  { province: '天津市', carbonEmission: 20400 },
  { province: '新疆维吾尔自治区', carbonEmission: 19200 },
  { province: '甘肃省', carbonEmission: 17800 },
  { province: '上海市', carbonEmission: 16500 },
  { province: '北京市', carbonEmission: 15200 },
  { province: '宁夏回族自治区', carbonEmission: 14600 },
  { province: '海南省', carbonEmission: 8900 },
  { province: '青海省', carbonEmission: 7600 },
  { province: '西藏自治区', carbonEmission: 3200 },
];

/** 屏一 / 绿色金融监测：各省七维结构 + 综合得分（与 greenFinanceIndicators 键一致） */
export interface MockGreenFinanceRow {
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

export const mockGreenFinanceData: MockGreenFinanceRow[] = mockCarbonData.map((d, i) => {
  const greenCredit = 0.02 + ((i * 3) % 11) / 100;
  const greenInvest = 0.02 + ((i * 5) % 11) / 100;
  const greenInsurance = 0.015 + ((i * 7) % 11) / 100;
  const greenBond = 0.018 + ((i * 2) % 11) / 100;
  const greenSupport = 0.02 + ((i * 4) % 11) / 100;
  const greenFund = 0.025 + ((i * 6) % 11) / 100;
  const greenEquity = 0.02 + ((i * 8) % 11) / 100;
  const score = (greenCredit + greenInvest + greenInsurance + greenBond + greenSupport + greenFund + greenEquity) / 7;
  return {
    province: d.province,
    score,
    greenCredit,
    greenInvest,
    greenInsurance,
    greenBond,
    greenSupport,
    greenFund,
    greenEquity,
  };
});

/**
 * 屏三：能耗强度分析 Mock 数据
 */
export const mockEnergyIntensityData = [
  { province: '北京市', score: 0.8523, energyConsume: 0.28 },
  { province: '上海市', score: 0.821, energyConsume: 0.31 },
  { province: '广东省', score: 0.7856, energyConsume: 0.35 },
  { province: '浙江省', score: 0.7523, energyConsume: 0.38 },
  { province: '江苏省', score: 0.7312, energyConsume: 0.42 },
  { province: '山东省', score: 0.6845, energyConsume: 0.56 },
  { province: '四川省', score: 0.6234, energyConsume: 0.48 },
  { province: '福建省', score: 0.5987, energyConsume: 0.44 },
  { province: '湖北省', score: 0.5654, energyConsume: 0.52 },
  { province: '重庆市', score: 0.5432, energyConsume: 0.5 },
  { province: '天津市', score: 0.521, energyConsume: 0.54 },
  { province: '河南省', score: 0.4876, energyConsume: 0.62 },
  { province: '安徽省', score: 0.4654, energyConsume: 0.58 },
  { province: '湖南省', score: 0.4432, energyConsume: 0.55 },
  { province: '河北省', score: 0.421, energyConsume: 0.72 },
  { province: '陕西省', score: 0.3987, energyConsume: 0.68 },
  { province: '辽宁省', score: 0.3765, energyConsume: 0.75 },
  { province: '江西省', score: 0.3543, energyConsume: 0.6 },
  { province: '山西省', score: 0.321, energyConsume: 0.95 },
  { province: '吉林省', score: 0.2987, energyConsume: 0.78 },
  { province: '黑龙江省', score: 0.2765, energyConsume: 0.82 },
  { province: '广西壮族自治区', score: 0.2543, energyConsume: 0.7 },
  { province: '云南省', score: 0.2321, energyConsume: 0.76 },
  { province: '贵州省', score: 0.2098, energyConsume: 0.88 },
  { province: '内蒙古自治区', score: 0.1987, energyConsume: 1.12 },
  { province: '甘肃省', score: 0.1765, energyConsume: 0.92 },
  { province: '新疆维吾尔自治区', score: 0.1543, energyConsume: 1.05 },
  { province: '海南省', score: 0.1432, energyConsume: 0.65 },
  { province: '宁夏回族自治区', score: 0.121, energyConsume: 1.35 },
  { province: '青海省', score: 0.1054, energyConsume: 1.18 },
  { province: '西藏自治区', score: 0.0876, energyConsume: 0.85 },
];
/**
 * 屏四：宏观经济动态 Mock 数据 (全国年度均值)
 */
export const mockMacroEconomyData = [
  { year: 2000, gdp: 10028, carbonEmission: 33500 },
  { year: 2001, gdp: 11024, carbonEmission: 34800 },
  { year: 2002, gdp: 12172, carbonEmission: 36200 },
  { year: 2003, gdp: 13742, carbonEmission: 39100 },
  { year: 2004, gdp: 16184, carbonEmission: 42800 },
  { year: 2005, gdp: 18732, carbonEmission: 51000 },
  { year: 2006, gdp: 21944, carbonEmission: 56500 },
  { year: 2007, gdp: 27023, carbonEmission: 61200 },
  { year: 2008, gdp: 31952, carbonEmission: 65800 },
  { year: 2009, gdp: 34908, carbonEmission: 68500 },
  { year: 2010, gdp: 41303, carbonEmission: 76300 },
  { year: 2011, gdp: 48930, carbonEmission: 82100 },
  { year: 2012, gdp: 53858, carbonEmission: 85600 },
  { year: 2013, gdp: 59524, carbonEmission: 89200 },
  { year: 2014, gdp: 64397, carbonEmission: 90500 },
  { year: 2015, gdp: 68886, carbonEmission: 89800 },
  { year: 2016, gdp: 74640, carbonEmission: 90100 },
  { year: 2017, gdp: 83204, carbonEmission: 92300 },
  { year: 2018, gdp: 91928, carbonEmission: 94600 },
  { year: 2019, gdp: 98652, carbonEmission: 96200 },
  { year: 2020, gdp: 101357, carbonEmission: 97800 },
  { year: 2021, gdp: 114367, carbonEmission: 105200 },
  { year: 2022, gdp: 121020, carbonEmission: 104500 },
  { year: 2023, gdp: 126058, carbonEmission: 103800 },
  { year: 2024, gdp: 132680, carbonEmission: 102900 },
];
