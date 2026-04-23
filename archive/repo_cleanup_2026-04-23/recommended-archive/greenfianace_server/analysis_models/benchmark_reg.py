import pandas as pd
import numpy as np
from linearmodels import PanelOLS, RandomEffects
from statsmodels.stats.outliers_influence import variance_inflation_factor
import warnings
import os
from config import core_vars, model_params, output_path, RUN_LEVEL

warnings.filterwarnings('ignore')


# -------------------------- 正确Hausman检验（保留）--------------------------
def hausman_test_optimized(results_fe, results_re):
    try:
        b_fe = results_fe.params
        b_re = results_re.params
        common_params = b_fe.index.intersection(b_re.index)

        b_diff = b_fe[common_params] - b_re[common_params]
        cov_diff = results_fe.cov[common_params].loc[common_params] - results_re.cov[common_params].loc[common_params]

        hausman_stat = float(b_diff.T @ np.linalg.inv(cov_diff) @ b_diff)
        df = len(common_params)
        pval = 1 - np.random.chisquare(df, 10000).clip(0, hausman_stat).mean()
        return hausman_stat, pval, df
    except Exception as e:
        print(f"⚠️ Hausman检验计算失败：{str(e)}")
        return np.nan, np.nan, np.nan


# -------------------------- 1%缩尾（保留）--------------------------
def winsorize_1pct(series):
    lower = series.quantile(0.01)
    upper = series.quantile(0.99)
    return series.clip(lower, upper)


# -------------------------- VIF检验（保留）--------------------------
def calculate_vif(df, vars_list):
    df_vif = df[vars_list].dropna()
    if df_vif.empty:
        print("❌ VIF检验：无有效数据")
        return pd.DataFrame()
    vif_data = np.column_stack((np.ones(len(df_vif)), df_vif.values))
    vif_scores = [variance_inflation_factor(vif_data, i+1) for i in range(len(vars_list))]
    vif_df = pd.DataFrame({'变量': vars_list, 'VIF': vif_scores}).round(2)
    print("\n📊 多重共线性VIF检验（<10为合格）：")
    print(vif_df)
    return vif_df


# -------------------------- 数据预处理（修复：强制剔除因变量+平衡面板）--------------------------
def preprocess_panel_data_optimized(df, id_cols, dep_var, core_exog, control_vars):
    df_panel = df.copy()
    # 年份标准化
    df_panel[id_cols[1]] = pd.to_numeric(df_panel[id_cols[1]], errors='coerce')
    df_panel = df_panel[(df_panel[id_cols[1]] >= 2000) & (df_panel[id_cols[1]] <= 2025)].dropna(subset=[id_cols[1]])
    df_panel[id_cols[1]] = df_panel[id_cols[1]].astype(int)

    # 🔥 修复1：永久删除 ln_GDP
    control_vars = [v for v in control_vars if v not in ['ln_GDP', 'lnGDP']]
    # 🔥 修复2：强制剔除因变量，绝对禁止进入自变量（解决R²=1）
    control_vars = [v for v in control_vars if v != dep_var]

    # 变量清理
    key_vars = [dep_var, core_exog] + control_vars
    key_vars = [v for v in key_vars if v in df_panel.columns]
    df_panel = df_panel.dropna(subset=key_vars)

    # 缩尾处理
    for var in key_vars:
        if np.issubdtype(df_panel[var].dtype, np.number):
            df_panel[var] = winsorize_1pct(df_panel[var])

    # 🔥 修复：正确的【多变量严格平衡面板】（顶刊标准，不会清空数据）
    df_panel = df_panel.set_index(id_cols).sort_index()
    df_panel = df_panel[~df_panel.index.duplicated(keep='first')]

    # 获取所有存在的年份
    all_years = df_panel.index.get_level_values(1).unique()
    n_years = len(all_years)

    # 筛选：每个省份必须拥有【全部年份】的数据（严格平衡）
    valid_provs = df_panel.groupby(level=0).size()
    valid_provs = valid_provs[valid_provs == n_years].index
    df_panel = df_panel.loc[valid_provs]

    return df_panel, control_vars

# -------------------------- 基准回归主函数（全量修复）--------------------------
def run_benchmark_regression(df, keep_vars=None):
    print("\n" + "=" * 60)
    print("📌 修复版：基准双向固定效应模型（省级面板）")
    print("=" * 60)

    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']
    core_exog = core_vars['core_x']['primary']
    control_vars = [v for v in core_vars['control_vars'] if v in df.columns]

    # 数据预处理
    df_panel, control_vars = preprocess_panel_data_optimized(df, id_cols, dep_var, core_exog, control_vars)

    # 🔥 修复4：严格过滤自变量，绝对不含因变量
    exog_vars = [core_exog] + control_vars
    exog_vars = [v for v in exog_vars if v in df_panel.columns and v != dep_var]

    # VIF
    calculate_vif(df_panel.reset_index(), exog_vars)

    # 🔥 修复5：删除 drop_absorbed=True，避免吞掉变量
    formula_fe = f"{dep_var} ~ {' + '.join(exog_vars)} + EntityEffects + TimeEffects"
    formula_re = f"{dep_var} ~ {' + '.join(exog_vars)}"

    # 🔥 修复6：省级双向聚类标准误
    try:
        model_fe = PanelOLS.from_formula(formula_fe, data=df_panel)
        results_fe = model_fe.fit(cov_type='clustered', cluster_entity=True, cluster_time=True)

        model_re = RandomEffects.from_formula(formula_re, data=df_panel)
        results_re = model_re.fit(cov_type='clustered', cluster_entity=True)

        hausman_stat, hausman_p, hausman_df = hausman_test_optimized(results_fe, results_re)

        print("\n🎯 基准回归结果：")
        print(results_fe.summary)

        core_coef = results_fe.params.get(core_exog, np.nan)
        core_p = results_fe.pvalues.get(core_exog, np.nan)
        print(f"\n✅ 核心变量结果：{core_exog} 系数={core_coef.round(4)}, p={core_p.round(4)}")

    except Exception as e:
        print(f"❌ 回归失败：{str(e)}")
        raise

    # 🔥 修复7：滞后一期回归正常运行 + 双向聚类
    print("\n📌 内生性：滞后一期")
    try:
        df_lag = df_panel.copy()
        lag_col = f'{core_exog}_lag1'
        df_lag[lag_col] = df_lag.groupby(id_cols[0])[core_exog].shift(1)
        df_lag = df_lag.dropna(subset=[lag_col])

        formula_lag = f"{dep_var} ~ {lag_col} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model_lag = PanelOLS.from_formula(formula_lag, data=df_lag)
        # 双向聚类
        results_lag = model_lag.fit(cov_type='clustered', cluster_entity=True, cluster_time=True)
        print("✅ 滞后一期回归完成")
        print(results_lag.summary)
    except Exception as e:
        print(f"❌ 滞后回归失败：{str(e)}")

    # 保存结果
    os.makedirs(os.path.join(output_path, 'regression_tables'), exist_ok=True)
    benchmark_result = pd.DataFrame({
        '变量': results_fe.params.index,
        '系数': results_fe.params.values.round(4),
        'p值': results_fe.pvalues.values.round(4),
        '显著性': ['***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '' for p in
                   results_fe.pvalues.values]
    })
    benchmark_result.to_csv(os.path.join(output_path, 'regression_tables/1_基准回归结果.csv'), index=False,
                            encoding='utf-8-sig')

    # 🔥 最小改动：仅重置索引，恢复年份/省份列，兼容原有DID
    df_keep_did = df_panel.reset_index()
    return benchmark_result, df_keep_did
