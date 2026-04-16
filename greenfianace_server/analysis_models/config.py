import pandas as pd
import numpy as np
import os
import sys
import warnings

warnings.filterwarnings('ignore')

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ==================== 【一键切换层级】 ====================
# 可选：province(省级) / city(地级市)
RUN_LEVEL = "province"

# ==================== 一、全局路径配置（自动分文件夹，防覆盖） ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(SERVER_DIR, 'data', 'model_inputs_v2')
base_output = os.path.join(SERVER_DIR, 'empirical_results')
output_path = os.path.join(base_output, RUN_LEVEL)
os.makedirs(output_path, exist_ok=True)

# ==================== 二、文件路径 ====================
file_paths = {
    '核心数据集': os.path.join(DATA_DIR, '省级绿色金融指数+碳排放+能源+DID数据(剔除西藏）.xlsx'),
    '地级市数据集': os.path.join(DATA_DIR, '地级市绿色金融+碳排放+能源+DID数据（剔除西藏）.xlsx'),
    '企业数据集': os.path.join(DATA_DIR, '企业绿色金融+碳排放+DID.xlsx'),
    '省级经纬度表': os.path.join(DATA_DIR, '中国省级行政区经纬度表.xlsx'),
    '最终清洗数据集': os.path.join(output_path, '中国绿色金融-能源平衡面板数据集(最终版).csv')
}

# 自动创建子文件夹
for sub_dir in ['figures', 'spatial', 'test_results', 'regression_tables']:
    os.makedirs(os.path.join(output_path, sub_dir), exist_ok=True)
print(f"📁 当前运行层级：{RUN_LEVEL}")
print(f"📁 结果保存路径：{os.path.abspath(output_path)}")

# ==================== 三、核心变量配置（🔥 100%适配你的表头） ====================
# --------------- 原省级核心变量（100%原样不动，保证结果完全一致） ---------------
province_core_vars = {
    'id_cols': ['省份', '年份'],
    'dep_vars': {'primary': '碳排放强度', 'secondary': '减排效率', 'tertiary': '能源强度'},
    'core_x': {'primary': 'gfi_std', 'raw': '绿色金融综合指数'},
    'gfi_components': ['绿色信贷', '绿色投资', '绿色保险', '绿色债券', '绿色支持', '绿色基金', '绿色权益'],
    'control_vars': ['ln_GDP', 'indus_2', '人均能源消耗', '减排效率', '碳排放强度'],
    'mediator_vars': ['能源利用效率', '产业结构高级化', '绿色信贷规模'],
    'moderator_vars': ['环境规制强度', '技术创新水平'],
    'other_policies': {
        'carbon_trading_provinces': ['北京市', '天津市', '上海市', '重庆市', '广东省', '湖北省', '辽宁省', '陕西省'],
        'carbon_trading_year': 2013, 'environmental_tax_year': 2018},
    'green_did_config': {'treat_provinces': ['浙江省', '江西省', '广东省', '贵州省', '新疆维吾尔自治区'],
                         'policy_year': 2017, 'did_col': '绿色金融试点DID', 'post_col': 'Post_green',
                         'treat_col': 'Treat_green'},
    'carbon_did_config': {
        'treat_provinces': ['北京市', '天津市', '上海市', '重庆市', '广东省', '湖北省', '辽宁省', '陕西省'],
        'policy_year': 2013, 'did_col': '碳排放交易DID', 'post_col': 'Post_carbon', 'treat_col': 'Treat_carbon'},
    'energy_consumption_vars': ['煤炭消费量', '焦炭消费量', '原油消费量', '汽油消费量', '煤油消费量', '柴油消费量',
                                '燃料油消费量', '天然气消费量', '电力消费量'],
    'region_split': {
        '东部': ['北京市', '天津市', '河北省', '辽宁省', '上海市', '江苏省', '浙江省', '福建省', '山东省', '广东省',
                 '海南省'], '中部': ['山西省', '吉林省', '黑龙江省', '安徽省', '江西省', '河南省', '湖北省', '湖南省'],
        '西部': ['内蒙古自治区', '广西壮族自治区', '重庆市', '四川省', '贵州省', '云南省', '陕西省', '甘肃省', '青海省',
                 '宁夏回族自治区', '新疆维吾尔自治区']},
    'did_config': ['green_did_config'],
    # 省级无需保留经纬度
    'spatial_cols': [],
    # 🔥 新增：预处理强制保留字段（省级）
    'keep_essential_cols': ['省份', '年份', '绿色金融综合指数', '碳排放强度', '减排效率']
}

# --------------- 地级市核心变量（🔥 100%适配你的表头，所有字段全配齐） ---------------
city_core_vars = {
    'id_cols': ['地级市', '年份'],
    # 🔥 被解释变量：完全对应你的表头
    'dep_vars': {'primary': '碳排放强度', 'secondary': '减排效率', 'tertiary': 'CO2排放量'},
    'core_x': {'primary': 'gfi_std', 'raw': '绿色金融综合指数'},
    # 🔥 绿色金融细分指标：完全对应你的表头
    'gfi_components': ['绿色信贷', '绿色投资', '绿色保险', '绿色债券', '绿色支持', '绿色基金', '绿色权益'],
    # 🔥 控制变量：完全对应你的表头，贴合参考文献STIRPAT模型
    'control_vars': [
        '人均地区生产总值', 'GDP增速', '年末常住人口数', '能源消费强度',
        '第二产业增加值占GDP比重', '第三产业增加值占GDP比重'
    ],
    # 🔥 中介变量：优先用你表头里现成的，没有再构造
    'mediator_vars': ['能源利用效率', '产业结构高级化', '绿色信贷规模'],
    'moderator_vars': ['环境规制强度', '技术创新水平'],
    # 🔥 绿色金融试点DID：完全对应你的表头
    'green_did_config': {
        'treat_provinces': ['浙江省', '江西省', '广东省', '贵州省', '新疆维吾尔自治区'],
        'policy_year': 2017,
        'did_col': '绿色金融试点DID',
        'post_col': 'Post_green',
        'treat_col': 'Treat_green'
    },
    # 🔥 碳排放交易DID：完全对应你的表头
    'carbon_did_config': {
        'treat_provinces': ['北京市', '天津市', '上海市', '重庆市', '广东省', '湖北省', '辽宁省', '陕西省'],
        'policy_year': 2013,
        'did_col': '碳排放交易DID',
        'post_col': 'Post_carbon',
        'treat_col': 'Treat_carbon'
    },
    'region_split': province_core_vars['region_split'],
    'did_config': ['green_did_config'],
    # 🔥 关键修复1：地级市强制保留经纬度，不被预处理删除
    'spatial_cols': ['经度', '纬度'],
    # 🔥 关键修复2：预处理强制保留的核心字段（你的表头里所有重要字段全在这）
    'keep_essential_cols': [
        '地级市', '年份', '省份', '绿色金融综合指数', '碳排放强度', '减排效率', 'CO2排放量',
        '绿色信贷', '绿色投资', '绿色保险', '绿色债券', '绿色支持', '绿色基金', '绿色权益',
        '人均地区生产总值', 'GDP增速', '年末常住人口数', '能源消费强度', '能源消费总量',
        '第二产业增加值占GDP比重', '第三产业增加值占GDP比重',
        'Post_green', 'Treat_green', '绿色金融试点DID',
        'Post_carbon', 'Treat_carbon', '碳排放交易DID',
        '长江经济带', '经度', '纬度'
    ]
}

# 自动切换配置
core_vars = {
    "province": province_core_vars,
    "city": city_core_vars
}[RUN_LEVEL]

# 变量别名（优化输出可读性）
core_vars['var_alias'] = {
    '年份': '年份',
    '省份': '省份',
    '地级市': '地级市',
    '减排效率': '减排效率（正向指标）',
    '碳排放强度': '碳排放强度（吨/万元）',
    'gfi_std': '标准化绿色金融综合指数',
    '绿色金融综合指数': '绿色金融综合指数（原始值）',
    '第二产业增加值占GDP比重': '第二产业占比',
    '第三产业增加值占GDP比重': '第三产业占比'

}
pilot_policy_dict = {
    '浙江省': 2017, '江西省': 2017, '广东省': 2017,
    '贵州省': 2017, '新疆维吾尔自治区': 2017, # 第一批
    '甘肃省': 2019, # 第二批
    '重庆市': 2022, # 第三批
    '上海市': 2024, '内蒙古自治区': 2024 # 第四批
}

# ==================== 四、模型参数（🔥 完美适配经纬度+双DID） ====================
model_params = {
    'fixed_effects': ['Entity', 'Time'],
    'cluster_level': 'Entity',
    'spatial_weight_type': 'geo_econ_nested',
    'distance_threshold': 1200,
    'spatial_model_type': 'SDM',
    # 🔥 终极修复：地级市直接用数据里的 经度/纬度，省级用原有配置
    'spatial_lat_col': '纬度' if RUN_LEVEL == 'city' else '纬度（北纬）',
    'spatial_lon_col': '经度' if RUN_LEVEL == 'city' else '经度（东经）',
    'spatial_prov_col': '地级市' if RUN_LEVEL == 'city' else '省级行政区',
    'bootstrap_iter': 1000,
    'bootstrap_seed': 42,
    'event_window': [-5, 5],
    'group_split_quantile': 0.5,
}

# ==================== 五、预处理参数（🔥 100%适配你的表头，强制保留核心字段） ====================
preprocess_params = {
    'winsorize_limits': [0.01, 0.01],
    'missing_value_method': 'drop',
    'dep_var_invert': True,
    'invert_executed': False,
    # 🔥 关键修复：预处理时强制保留 keep_essential_cols 里的所有字段
    'force_keep_cols': core_vars.get('keep_essential_cols', [])
}

# ==================== 六、经纬度加载（🔥 地级市直接跳过，不报错） ====================
def load_lon_lat():
    try:
        if RUN_LEVEL == "province":
            lat_lon_path = file_paths.get('省级经纬度表')
            lat_lon_df = pd.read_excel(lat_lon_path, engine='openpyxl')
            prov_col = model_params['spatial_prov_col']
            lon_col = model_params['spatial_lon_col']
            lat_col = model_params['spatial_lat_col']
            lat_lon_df[prov_col] = lat_lon_df[prov_col].astype(str).str.strip()
            res = dict(zip(lat_lon_df[prov_col], zip(lat_lon_df[lon_col], lat_lon_df[lat_col])))
            print(f"✅ 成功读取省级经纬度xlsx文件")
            return res
        else:
            # 地级市直接返回空，用数据里的经纬度
            return {}
    except Exception as e:
        print(f"❌ 读取经纬度xlsx失败：{str(e)}")
        print("⚠️  启用兜底方案：使用数据内置经纬度")
        return {}

province_lon_lat = load_lon_lat()
print("✅ 配置文件加载完成！")
