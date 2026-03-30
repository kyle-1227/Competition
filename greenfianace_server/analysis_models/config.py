import pandas as pd
import numpy as np
import os
import re
import warnings

warnings.filterwarnings('ignore')

# ==================== 一、全局路径配置 ====================
# config.py 位于 analysis_models/；服务器根目录为 greenfianace_server/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(SERVER_DIR, 'data')
output_path = os.path.join(SERVER_DIR, 'empirical_results')


def _find_lat_lon_path() -> str:
    """省级经纬度表：优先 xlsx，其次 csv。"""
    for name in ('中国省级行政区经纬度表.xlsx', '中国省级行政区经纬度表.csv'):
        p = os.path.join(DATA_DIR, name)
        if os.path.isfile(p):
            return p
    return os.path.join(DATA_DIR, '中国省级行政区经纬度表.xlsx')


def _find_core_dataset_path() -> str:
    """
    核心数据集：在 DATA_DIR 下智能匹配主面板数据文件。
    优先文件名含「减排效率7.0」>「6.0」> 含「合并数据」且非经纬度的 xlsx/csv。
    """
    if not os.path.isdir(DATA_DIR):
        return os.path.join(DATA_DIR, '省级绿色金融指数，碳排放、DID与能源消耗合并数据(清洗后-剔除西藏）+减排效率7.0.xlsx')

    # 显式优先列表（与仓库 data/ 中实际文件名一致时可命中）
    preferred = [
        '省级绿色金融指数，碳排放、DID与能源消耗合并数据(清洗后-剔除西藏）+减排效率7.0.xlsx',
        '省级绿色金融指数，碳排放、DID与能源消耗合并数据(清洗后-剔除西藏）+减排效率6.0.xlsx',
    ]
    for name in preferred:
        p = os.path.join(DATA_DIR, name)
        if os.path.isfile(p):
            return p

    # 按「版本号」在文件名中的数字排序，取较新
    def version_key(filename: str) -> tuple:
        m = re.search(r'减排效率\s*(\d+)\.0', filename)
        if m:
            return (1, int(m.group(1)))
        m2 = re.search(r'(\d+)\.0\.xlsx$', filename)
        if m2:
            return (0, int(m2.group(1)))
        return (0, 0)

    candidates = []
    for fn in os.listdir(DATA_DIR):
        lower = fn.lower()
        if not lower.endswith(('.xlsx', '.xls', '.csv')):
            continue
        if '经纬度' in fn:
            continue
        if any(k in fn for k in ('合并数据', '绿色金融', '减排效率', '省级绿色金融')):
            candidates.append(fn)

    if candidates:
        candidates.sort(key=version_key, reverse=True)
        return os.path.join(DATA_DIR, candidates[0])

    # 兜底：任意非经纬度表格文件
    for fn in sorted(os.listdir(DATA_DIR)):
        if fn.lower().endswith(('.xlsx', '.xls', '.csv')) and '经纬度' not in fn:
            return os.path.join(DATA_DIR, fn)

    return os.path.join(DATA_DIR, preferred[0])


file_paths = {
    '核心数据集': _find_core_dataset_path(),
    '省级经纬度表': _find_lat_lon_path(),
    '最终清洗数据集': os.path.join(DATA_DIR, '最终面板数据集.csv'),
}

for sub_dir in ['figures', 'spatial', 'test_results', 'regression_tables']:
    os.makedirs(os.path.join(output_path, sub_dir), exist_ok=True)

print(f"📁 结果保存路径：{os.path.abspath(output_path)}")
print(f"📁 数据目录：{os.path.abspath(DATA_DIR)}")
print(f"📄 核心数据集：{file_paths['核心数据集']}")
print(f"📄 省级经纬度表：{file_paths['省级经纬度表']}")
print(f"📄 最终清洗数据集（导出目标）：{file_paths['最终清洗数据集']}")

# ==================== 二、核心变量全局配置 ====================
core_vars = {
    'id_cols': ['省份', '年份'],
    'dep_vars': {
        'primary': '减排效率',
        'secondary': '碳排放强度',
        'tertiary': '能源强度'
    },
    'core_x': {
        'primary': 'gfi_std',
        'raw': '绿色金融综合指数'
    },
    # 【新增】绿色金融7大分项指数（根据你的表头推断）
    'gfi_components': ['绿色信贷', '绿色投资', '绿色保险', '绿色债券', '绿色支持', '绿色基金', '绿色权益'],

    'control_vars': ['ln_GDP', 'ln_pop', '能源强度', '人均能源消耗'],
    'mediator_vars': ['能源结构清洁化', '能源利用效率', '产业结构高级化'],
    'moderator_vars': ['环境规制强度', '技术创新水平'],

    # 【确认】DID已配置为绿色金融改革创新试验区（2017年五省一区）
    'did_config': {
        'treat_provinces': ['浙江省', '江西省', '广东省', '贵州省', '新疆维吾尔自治区', '甘肃省'],
        'policy_year': 2017,
        'policy_detail': {
            '浙江省': 2017, '江西省': 2017, '广东省': 2017,
            '贵州省': 2017, '新疆维吾尔自治区': 2017, '甘肃省': 2017
        },
        'did_sample_start': 2012,
        'did_sample_end': 2022
    },
    'other_policies': {
        'carbon_trading_provinces': ['北京市', '天津市', '上海市', '重庆市', '广东省', '湖北省', '辽宁省', '陕西省'],
        'carbon_trading_year': 2013,
        'environmental_tax_year': 2018
    },
    'region_split': {
        '东部': ['北京市', '天津市', '河北省', '辽宁省', '上海市', '江苏省', '浙江省', '福建省', '山东省', '广东省', '海南省'],
        '中部': ['山西省', '吉林省', '黑龙江省', '安徽省', '江西省', '河南省', '湖北省', '湖南省'],
        '西部': ['内蒙古自治区', '广西壮族自治区', '重庆市', '四川省', '贵州省', '云南省', '陕西省', '甘肃省', '青海省', '宁夏回族自治区', '新疆维吾尔自治区']
    }
}

# ==================== 变量别名 ====================
core_vars['var_alias'] = {
    '年份': '年份', '省份': '省份',
    '减排效率': '减排效率（正向指标）', '碳排放强度': '碳排放强度', '能源强度': '能源强度',
    'gfi_std': '标准化绿色金融综合指数', '绿色金融综合指数': '原始绿色金融综合指数',
    'ln_GDP': '地区生产总值(对数)', 'ln_pop': '年末常住人口(对数)', '人均能源消耗': '人均能源消耗',
    '产业结构高级化': '产业结构高级化（三产/二产）', '能源利用效率': '能源利用效率（GDP/能耗）',
    '能源结构清洁化': '能源结构清洁化（清洁能源占比）',
    '绿色信贷': '绿色信贷指数', '绿色投资': '绿色投资指数', '绿色保险': '绿色保险指数',
    '绿色债券': '绿色债券指数', '绿色支持': '绿色支持指数', '绿色基金': '绿色基金指数', '绿色权益': '绿色权益指数',
    'DID': '政策交互项DID', 'Post': '政策时间虚拟变量', 'Treat': '处理组虚拟变量'
}

# ==================== 三、模型参数 ====================
model_params = {
    'fixed_effects': ['Entity', 'Time'],
    'cluster_level': 'Entity',
    'spatial_weight_type': 'geo_econ_nested',
    'distance_threshold': 1200,
    'spatial_model_type': 'SDM',
    'spatial_lat_col': '纬度（北纬）',
    'spatial_lon_col': '经度（东经）',
    'spatial_prov_col': '省级行政区',
    'bootstrap_iter': 1000,
    'bootstrap_seed': 42,
    'event_window': [-5, 5],
    'placebo_iter': 500,
    'group_split_quantile': 0.5,
    'iv_lag_periods': 1,
    'vif_max_threshold': 10,
    'psm_match_ratio': 1,
    'psm_caliper': 0.05
}

# ==================== 四、预处理参数 ====================
preprocess_params = {
    # 【关键修复】必须包含 winsorize_limits
    'winsorize_limits': [0.01, 0.01],  # 1% 双侧缩尾
    'vif_threshold': 10,  # VIF 阈值，通常设为 10
    'missing_value_method': 'drop',

    # 因变量方向控制
    'dep_var_invert': True,  # 是否需要对因变量取反
    'invert_executed': False  # 取反操作是否已执行（防止重复取反，由代码自动维护）
}


# ==================== 五、经纬度读取 ====================
def load_province_lon_lat():
    lat_lon_path = file_paths.get('省级经纬度表')
    if not os.path.exists(lat_lon_path):
        print("⚠️  未找到经纬度表，空间权重将用默认矩阵")
        return {}
    try:
        lat_lon_df = pd.read_excel(lat_lon_path, engine='openpyxl')
        lat_lon_df[model_params['spatial_prov_col']] = lat_lon_df[model_params['spatial_prov_col']].str.strip()
        province_lon_lat = dict(zip(
            lat_lon_df[model_params['spatial_prov_col']],
            zip(lat_lon_df[model_params['spatial_lon_col']], lat_lon_df[model_params['spatial_lat_col']])
        ))
        print(f"✅ 成功读取经纬度表，共{len(province_lon_lat)}个省份")
        return province_lon_lat
    except Exception as e:
        print(f"❌ 经纬度表读取失败：{str(e)}")
        return {}


# 全局加载经纬度
province_lon_lat = load_province_lon_lat()
print("✅ 配置文件加载完成！")
