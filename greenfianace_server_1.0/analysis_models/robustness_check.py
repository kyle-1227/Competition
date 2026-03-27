import pandas as pd
import numpy as np
from linearmodels import PanelOLS
import warnings
import os
from config import core_vars, output_path

warnings.filterwarnings('ignore')


def run_robustness_checks(df, keep_vars):
    """
    稳健性检验（终极修复：id_vars→id_cols+补充PSM-DID）
    """
    print("\n" + "=" * 60)
    print("📌 第五步：稳健性检验（补充PSM-DID+排除其他政策）")
    print("=" * 60)

    id_cols = core_vars['id_cols']  # 【核心修复】id_vars→id_cols
    dep_var = core_vars['dep_vars']['primary']
    core_x = core_vars['core_x']['primary']
    control_vars = [v for v in keep_vars if v not in [dep_var, core_x] and v in df.columns]
    df_panel = df.copy().set_index(id_cols)
    robustness_results = []

    # ---------------------- 检验1：替换被解释变量 ----------------------
    print("\n🔍 检验1：替换被解释变量（碳排放强度替代减排效率）")
    try:
        alt_dep = core_vars['dep_vars']['secondary']
        formula = f"{alt_dep} ~ {core_x} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=df_panel, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=True)
        robustness_results.append({
            '检验类型': '替换被解释变量(碳排放强度)',
            '核心变量': core_x,
            '核心变量系数': res.params.get(core_x, np.nan).round(4),
            'P值': res.pvalues.get(core_x, np.nan).round(4),
            '显著性': '***' if res.pvalues.get(core_x, 1) < 0.001 else '**' if res.pvalues.get(core_x,
                                                                                               1) < 0.01 else '*' if res.pvalues.get(
                core_x, 1) < 0.05 else '',
            'R²': round(res.rsquared, 4),
            '观测值数': res.nobs
        })
        print(
            f"✅ 检验1完成：核心变量系数={res.params.get(core_x, np.nan).round(4)}，P值={res.pvalues.get(core_x, np.nan).round(4)}")
    except Exception as e:
        print(f"⚠️  检验1失败：{str(e)}")

    # ---------------------- 检验2：核心解释变量滞后一期 ----------------------
    print("\n🔍 检验2：核心解释变量滞后一期")
    try:
        df_lag = df.copy().reset_index(drop=True)
        df_lag = df_lag.sort_values(id_cols)
        lag_col = f'{core_x}_lag1'
        df_lag[lag_col] = df_lag.groupby(id_cols[0])[core_x].shift(1)
        df_lag_panel = df_lag.dropna(subset=[lag_col]).set_index(id_cols)
        formula = f"{dep_var} ~ {lag_col} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=df_lag_panel, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=True)
        robustness_results.append({
            '检验类型': '核心解释变量滞后一期',
            '核心变量': lag_col,
            '核心变量系数': res.params.get(lag_col, np.nan).round(4),
            'P值': res.pvalues.get(lag_col, np.nan).round(4),
            '显著性': '***' if res.pvalues.get(lag_col, 1) < 0.001 else '**' if res.pvalues.get(lag_col,
                                                                                                1) < 0.01 else '*' if res.pvalues.get(
                lag_col, 1) < 0.05 else '',
            'R²': round(res.rsquared, 4),
            '观测值数': res.nobs
        })
        print(
            f"✅ 检验2完成：滞后一期系数={res.params.get(lag_col, np.nan).round(4)}，P值={res.pvalues.get(lag_col, np.nan).round(4)}")
    except Exception as e:
        print(f"⚠️  检验2失败：{str(e)}")

    # ---------------------- 检验3：剔除直辖市样本 ----------------------
    print("\n🔍 检验3：剔除直辖市样本")
    try:
        municipalities = ['北京市', '天津市', '上海市', '重庆市']
        df_no_muni = df[~df['省份'].isin(municipalities)].copy().set_index(id_cols)
        formula = f"{dep_var} ~ {core_x} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=df_no_muni, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=True)
        robustness_results.append({
            '检验类型': '剔除直辖市样本',
            '核心变量': core_x,
            '核心变量系数': res.params.get(core_x, np.nan).round(4),
            'P值': res.pvalues.get(core_x, np.nan).round(4),
            '显著性': '***' if res.pvalues.get(core_x, 1) < 0.001 else '**' if res.pvalues.get(core_x,
                                                                                               1) < 0.01 else '*' if res.pvalues.get(
                core_x, 1) < 0.05 else '',
            'R²': round(res.rsquared, 4),
            '观测值数': res.nobs
        })
        print(
            f"✅ 检验3完成：核心变量系数={res.params.get(core_x, np.nan).round(4)}，P值={res.pvalues.get(core_x, np.nan).round(4)}")
    except Exception as e:
        print(f"⚠️  检验3失败：{str(e)}")

    # ---------------------- 检验4：排除其他政策干扰（环保税） ----------------------
    print("\n🔍 检验4：排除其他政策干扰（环保税2018年）")
    try:
        df_no_policy = df[df['年份'] < 2018].copy().set_index(id_cols)
        formula = f"{dep_var} ~ {core_x} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=df_no_policy, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=True)
        robustness_results.append({
            '检验类型': '排除环保税政策干扰(2018前)',
            '核心变量': core_x,
            '核心变量系数': res.params.get(core_x, np.nan).round(4),
            'P值': res.pvalues.get(core_x, np.nan).round(4),
            '显著性': '***' if res.pvalues.get(core_x, 1) < 0.001 else '**' if res.pvalues.get(core_x,
                                                                                               1) < 0.01 else '*' if res.pvalues.get(
                core_x, 1) < 0.05 else '',
            'R²': round(res.rsquared, 4),
            '观测值数': res.nobs
        })
        print(
            f"✅ 检验4完成：核心变量系数={res.params.get(core_x, np.nan).round(4)}，P值={res.pvalues.get(core_x, np.nan).round(4)}")
    except Exception as e:
        print(f"⚠️  检验4失败：{str(e)}")

    # ---------------------- 【补充评估要求】检验5：PSM-DID倾向得分匹配 ----------------------
    print("\n🔍 检验5：PSM-DID倾向得分匹配（1:1最近邻匹配）")
    try:
        from sklearn.neighbors import NearestNeighbors
        df_psm = df.copy().reset_index(drop=True)
        # 取政策前一年做匹配
        psm_year = core_vars['did_config']['policy_year'] - 1
        df_psm_base = df_psm[df_psm['年份'] == psm_year].copy()

        # 匹配变量
        match_vars = control_vars
        df_psm_base = df_psm_base.dropna(subset=match_vars + ['Treat'])

        # 1:1最近邻匹配
        treat = df_psm_base[df_psm_base['Treat'] == 1]
        control = df_psm_base[df_psm_base['Treat'] == 0]

        nn = NearestNeighbors(n_neighbors=1)
        nn.fit(control[match_vars])
        distances, indices = nn.kneighbors(treat[match_vars])

        matched_controls = control.iloc[indices.flatten()]['省份'].unique()
        matched_provinces = list(treat['省份'].unique()) + list(matched_controls)

        # 匹配后DID回归
        df_psm_final = df_psm[df_psm['省份'].isin(matched_provinces)].copy().set_index(id_cols)
        formula_psm = f"{dep_var} ~ DID + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model_psm = PanelOLS.from_formula(formula_psm, data=df_psm_final, drop_absorbed=True)
        res_psm = model_psm.fit(cov_type='clustered', cluster_entity=True)

        robustness_results.append({
            '检验类型': 'PSM-DID倾向得分匹配',
            '核心变量': 'DID',
            '核心变量系数': res_psm.params.get('DID', np.nan).round(4),
            'P值': res_psm.pvalues.get('DID', np.nan).round(4),
            '显著性': '***' if res_psm.pvalues.get('DID', 1) < 0.001 else '**' if res_psm.pvalues.get('DID',
                                                                                                      1) < 0.01 else '*' if res_psm.pvalues.get(
                'DID', 1) < 0.05 else '',
            'R²': round(res_psm.rsquared, 4),
            '观测值数': res_psm.nobs
        })
        print(
            f"✅ 检验5完成：PSM-DID系数={res_psm.params.get('DID', np.nan).round(4)}，P值={res_psm.pvalues.get('DID', np.nan).round(4)}，匹配省份数={len(matched_provinces)}")
    except Exception as e:
        print(f"⚠️  检验5失败：{str(e)}")
        import traceback
        traceback.print_exc()

    robustness_df = pd.DataFrame(robustness_results)
    print("\n🎯 稳健性检验汇总：")
    print(robustness_df.to_string(index=False))
    save_path = os.path.join(output_path, 'regression_tables/5_稳健性检验结果.csv')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    robustness_df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 稳健性检验结果已保存至：{save_path}")
    return robustness_df