import pandas as pd
import os
from config import file_paths, core_vars

def \
        load_raw_data():
    """
    加载原始面板数据
    """
    file_path = file_paths.get('核心数据集')
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ 核心数据文件不存在：{os.path.abspath(file_path)}")
    try:
        df_raw = pd.read_excel(file_path, engine='openpyxl')
        print(f"✅ 原始数据加载成功！数据维度：{df_raw.shape[0]}行，{df_raw.shape[1]}列")
        return df_raw
    except Exception as e:
        raise RuntimeError(f"❌ 数据文件读取失败：{str(e)}")

def verify_panel_structure(df):
    """
    验证面板数据结构完整性，校验核心字段
    """
    print("\n" + "=" * 60)
    print("📊 面板数据结构校验")
    print("=" * 60)

    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']
    core_x_raw = core_vars['core_x']['raw']

    # 核心字段缺失校验
    missing_core = [col for col in id_cols + [dep_var, core_x_raw] if col not in df.columns]
    if missing_core:
        raise ValueError(f"❌ 缺失核心字段：{missing_core}，请检查原始数据文件")

    # 年份字段强制转换
    df[id_cols[1]] = pd.to_numeric(df[id_cols[1]], errors='coerce').fillna(0).astype(int)

    # 面板基本信息打印
    print(f"时间跨度：{df[id_cols[1]].min()} - {df[id_cols[1]].max()}年")
    print(f"省份数量：{df[id_cols[0]].nunique()}个")
    print(f"平衡面板校验：{'是' if df.groupby(id_cols[0])[id_cols[1]].nunique().nunique() == 1 else '否'}")

    # 核心字段预览
    print("\n📋 核心字段前2行预览：")
    core_cols = id_cols + [core_x_raw, dep_var] + ['Post', 'Treat', 'DID']
    core_cols = [col for col in core_cols if col in df.columns]
    print(df[core_cols].head(2).to_string(index=False))

    return df