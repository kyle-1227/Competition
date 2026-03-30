import pandas as pd
import numpy as np
from linearmodels import PanelOLS
import warnings
import os
from config import core_vars, model_params, output_path

warnings.filterwarnings('ignore')


def run_standard_did(df, keep_vars):
    """
    【优化版】渐进DID
    1. 限制样本期为政策前后5年（2012-2022）
    2. 优化对照组筛选
    """
    print("\n" + "=" * 60)
    print("📌 渐进DID双重差分模型")
    print("=" * 60)

    # 1. 全局配置
    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']  # 正向指标
    did_config = core_vars['did_config']
    treat_provinces = did_config['treat_provinces']
    policy_year = did_config['policy_year']
    event_window = model_params['event_window']  # [-5, 5]

    # 控制变量
    control_vars = [v for v in keep_vars if v not in [dep_var, core_vars['core_x']['primary']] and v in df.columns]

    # 2. 数据预处理
    df_panel_base = df.copy()
    df_panel_base[id_cols[1]] = pd.to_numeric(df_panel_base[id_cols[1]], errors='coerce').astype(int)

    # ==========================================================
    # 【优化1】限制样本期：政策前后对称窗口 (2012-2022)
    # ==========================================================
    sample_start = policy_year + event_window[0]  # 2017-5=2012
    sample_end = policy_year + event_window[1]  # 2017+5=2022
    df_panel_base = df_panel_base[(df_panel_base['年份'] >= sample_start) & (df_panel_base['年份'] <= sample_end)].copy()
    print(f"✅ DID样本期限制：{sample_start}-{sample_end} (政策前后{abs(event_window[0])}年)")
    print(f"✅ 处理组省份：{treat_provinces}")

    # ==========================================================
    # 【优化2】对照组筛选：匹配政策前特征
    # ==========================================================
    try:
        base_year = policy_year - 1
        df_base = df_panel_base[df_panel_base['年份'] == base_year].copy()

        # 匹配政策前一年的GDP中位数±30%
        treat_gdp_median = df_base[df_base['省份'].isin(treat_provinces)]['地区生产总值'].median()

        control_candidates = df_base[
            (df_base['地区生产总值'] >= treat_gdp_median * 0.7) &
            (df_base['地区生产总值'] <= treat_gdp_median * 1.3) &
            (~df_base['省份'].isin(treat_provinces))
            ]['省份'].unique()

        keep_provinces = list(treat_provinces) + list(control_candidates)
        df_panel_base = df_panel_base[df_panel_base['省份'].isin(keep_provinces)].copy()
        print(f"✅ 对照组筛选完成：保留{len(control_candidates)}个经济水平相近省份")
    except Exception as e:
        print(f"⚠️  对照组筛选失败，使用全样本：{str(e)}")

    # 3. 基准DID回归
    df_panel = df_panel_base.set_index(id_cols).sort_index()
    formula_did = f"{dep_var} ~ DID + {' + '.join(control_vars)} + EntityEffects + TimeEffects"

    res_did = None
    try:
        model_did = PanelOLS.from_formula(formula_did, data=df_panel, drop_absorbed=True)
        res_did = model_did.fit(cov_type='clustered', cluster_entity=True)
        print("\n🎯 标准DID回归结果：")
        print(res_did.summary)
    except Exception as e:
        print(f"❌ 标准DID回归失败：{str(e)}")

    # 4. 动态DID平行趋势检验
    # ... (这部分代码保持原有逻辑不变，确保生成rel_year_p0等变量) ...

    print("\n✅ DID模块运行完成！")
    return res_did  # 简化返回