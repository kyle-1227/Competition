import pandas as pd
import numpy as np
import os


def load_raw_data():
    """
    加载原始数据（路径与 config.file_paths['核心数据集'] 一致）
    """
    from .config import file_paths

    file_path = file_paths['核心数据集']
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ 数据文件不存在：{file_path}")

    df_raw = pd.read_excel(file_path, engine='openpyxl')
    print("✅ 数据加载成功！")
    return df_raw


def verify_panel_structure(df):
    """
    验证面板数据结构，100%匹配你的字段表，修复原索引错误
    """
    print("\n" + "=" * 60)
    print("📊 面板数据验证")
    print("=" * 60)

    # 【全局统一】从config导入索引定义，避免硬编码
    from .config import core_vars
    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']

    # 强制校验核心字段（匹配你的字段表）
    missing_core = [col for col in id_cols + [dep_var] if col not in df.columns]
    if missing_core:
        raise ValueError(f"❌ 缺失核心字段：{missing_core}，请检查数据文件")

    # 年份强制转数值型，匹配你的字段定义
    df['年份'] = pd.to_numeric(df['年份'], errors='coerce').fillna(0).astype(int)

    # 打印面板基本信息
    print(f"数据维度：{df.shape[0]}行，{df.shape[1]}列")
    print(f"时间跨度：{df['年份'].min()} - {df['年份'].max()}")
    print(f"省份数量：{df['省份'].nunique()}")

    # 打印前2行预览
    print("\n📋 前2行预览：")
    print(df.head(2).to_string(index=False))

    # 打印核心字段列名
    print("\n📋 核心字段列名：")
    core_cols = id_cols + [core_vars['core_x']['raw']] + list(core_vars['dep_vars'].values()) + ['Post', 'Treat', 'DID']
    core_cols = [col for col in core_cols if col in df.columns]
    print(core_cols)

    return df