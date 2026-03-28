import pandas as pd
import numpy as np
from linearmodels import PanelOLS, RandomEffects
import warnings
import os
from config import core_vars, model_params, output_path

warnings.filterwarnings('ignore')


def hausman_test(results_fe, results_re):
    """
    手动实现Hausman检验，兼容奇异矩阵
    """
    try:
        b_fe = results_fe.params
        b_re = results_re.params
        common_vars = b_fe.index.intersection(b_re.index)
        b_fe = b_fe.loc[common_vars]
        b_re = b_re.loc[common_vars]
        v_fe = results_fe.cov.loc[common_vars, common_vars]
        v_re = results_re.cov.loc[common_vars, common_vars]

        b_diff = b_fe - b_re
        v_diff = v_fe - v_re

        # 处理奇异矩阵
        try:
            hausman_stat = b_diff @ np.linalg.inv(v_diff) @ b_diff
        except np.linalg.LinAlgError:
            hausman_stat = b_diff @ np.linalg.pinv(v_diff) @ b_diff

        df = len(common_vars)
        from scipy.stats import chi2
        p_value = chi2.sf(hausman_stat, df)
        return hausman_stat, p_value, df
    except Exception as e:
        print(f"⚠️  Hausman检验计算失败：{str(e)}")
        return np.nan, np.nan, np.nan


def preprocess_panel_data(df, id_cols):
    """
    面板数据预处理通用函数（代码复用）
    """
    df_panel = df.copy()
    # 年份强制数值化
    df_panel[id_cols[1]] = pd.to_numeric(df_panel[id_cols[1]], errors='coerce').fillna(0).astype(int)
    # 设置面板索引
    df_panel = df_panel.set_index(id_cols).sort_index()
    # 生成省份×时间趋势交互项
    df_panel['province_trend'] = df_panel.index.get_level_values(0).astype(
        'category').codes * df_panel.index.get_level_values(1)
    return df_panel


def run_benchmark_regression(df, keep_vars):
    """
    【修改版】基准双向固定效应模型+滞后一期内生性处理
    彻底删除2SLS工具变量模块，仅用核心解释变量滞后一期处理内生性
    """
    print("\n" + "=" * 60)
    print("📌 基准双向固定效应模型+滞后一期内生性处理")
    print("=" * 60)

    # ---------------------- 1. 全局变量初始化 ----------------------
    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']
    core_exog = core_vars['core_x']['primary']
    control_vars = [v for v in keep_vars if v not in [dep_var, core_exog] and v in df.columns]
    cluster_level = model_params['cluster_level']

    # 面板数据预处理
    df_panel = preprocess_panel_data(df, id_cols)
    print(f"✅ 面板索引设置完成：个体={df_panel.index.levels[0].nunique()}个，时间={df_panel.index.levels[1].nunique()}年")

    # 回归公式构建
    exog_vars = [core_exog] + control_vars + ['province_trend']
    exog_part = ' + '.join(exog_vars)
    formula_fe = f"{dep_var} ~ {exog_part} + EntityEffects + TimeEffects"
    formula_re = f"{dep_var} ~ {exog_part}"

    # 美化打印回归公式
    debug_formula = f"{core_vars['var_alias'].get(dep_var, dep_var)} ~ " \
                    f"{core_vars['var_alias'].get(core_exog, core_exog)} + " \
                    f"{' + '.join([core_vars['var_alias'].get(col, col) for col in control_vars])} + " \
                    f"省份时间趋势 + 个体固定效应 + 时间固定效应"
    print(f"📝 基准回归公式：{debug_formula}")

    # ---------------------- 2. 基准双向固定效应回归 ----------------------
    results_fe, results_re = None, None
    hausman_stat, hausman_p, hausman_df = np.nan, np.nan, np.nan
    try:
        # 固定效应模型
        model_fe = PanelOLS.from_formula(formula_fe, data=df_panel, drop_absorbed=True)
        results_fe = model_fe.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))
        # 随机效应模型
        model_re = RandomEffects.from_formula(formula_re, data=df_panel)
        results_re = model_re.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))
        # Hausman检验
        hausman_stat, hausman_p, hausman_df = hausman_test(results_fe, results_re)

        # 结果打印
        print("\n🎯 基准双向固定效应模型回归结果：")
        print(results_fe.summary)
        print("\n🎯 Hausman检验结果：")
        if not np.isnan(hausman_stat):
            print(f"Hausman统计量：{hausman_stat.round(4)}，自由度：{hausman_df}，P值：{hausman_p.round(4)}")
            if hausman_p < 0.05:
                print("✅ 拒绝原假设，选择固定效应模型FE，符合学术规范")
            else:
                print("⚠️  接受原假设，随机效应模型RE更优，本文基于研究惯例选择固定效应模型FE")
        else:
            print("⚠️  Hausman检验无法计算，根据研究惯例选择固定效应模型FE")

        # 核心结论提示
        core_coef = results_fe.params.get(core_exog, np.nan)
        core_p = results_fe.pvalues.get(core_exog, np.nan)
        if core_coef > 0 and core_p < 0.05:
            print(f"ℹ️  核心结论：绿色金融综合指数系数为{core_coef.round(4)}（p={core_p.round(4)}），显著为正，符合理论预期——绿色金融显著提升减排效率")
        elif core_coef < 0 and core_p < 0.05:
            print(f"ℹ️  核心结论：绿色金融综合指数系数为{core_coef.round(4)}（p={core_p.round(4)}），显著为负，请检查因变量方向是否正确")
        else:
            print(f"ℹ️  核心结论：绿色金融综合指数系数不显著，需进一步检验")
    except Exception as e:
        print(f"❌ 基准回归运行失败：{str(e)}")
        raise

    # ---------------------- 3. 内生性处理：核心解释变量滞后一期 ----------------------
    print("\n" + "-" * 60)
    print(f"📌 内生性处理：核心解释变量滞后一期（解决反向因果问题）")
    print("-" * 60)
    results_lag = None

    try:
        # 生成滞后一期变量
        df_lag = df.copy().reset_index(drop=True)
        df_lag = df_lag.sort_values(id_cols)
        lag_col = f'{core_exog}_lag1'
        df_lag[lag_col] = df_lag.groupby(id_cols[0])[core_exog].shift(1)
        df_lag = df_lag.dropna(subset=[lag_col])
        df_lag_panel = preprocess_panel_data(df_lag, id_cols)
        print(f"✅ 滞后一期回归样本量：{len(df_lag_panel)}")

        # 滞后一期回归公式
        lag_exog_vars = [lag_col] + control_vars + ['province_trend']
        lag_exog_part = ' + '.join(lag_exog_vars)
        formula_lag = f"{dep_var} ~ {lag_exog_part} + EntityEffects + TimeEffects"

        # 拟合模型
        model_lag = PanelOLS.from_formula(formula_lag, data=df_lag_panel, drop_absorbed=True)
        results_lag = model_lag.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))

        # 结果打印
        print("\n🎯 核心解释变量滞后一期回归结果：")
        print(results_lag.summary)

        # 符号一致性检验
        lag_coef = results_lag.params.get(lag_col, np.nan)
        lag_p = results_lag.pvalues.get(lag_col, np.nan)
        if not np.isnan(lag_coef) and lag_coef * core_coef > 0 and lag_p < 0.05:
            print("✅ 滞后一期与基准回归符号一致且显著，排除反向因果问题，核心结论稳健")
        else:
            print("⚠️  滞后一期结果与基准回归不一致，需进一步检验")
    except Exception as e:
        print(f"⚠️  滞后一期回归运行失败：{str(e)}")
        results_lag = None

    # ---------------------- 4. 回归结果整理与保存 ----------------------
    # 基准回归结果整理
    benchmark_result = pd.DataFrame({
        '标准化列名': results_fe.params.index,
        '变量含义': [core_vars['var_alias'].get(col, col) for col in results_fe.params.index],
        '系数': results_fe.params.values.round(4),
        '标准误': results_fe.std_errors.values.round(4),
        't值': results_fe.tstats.values.round(4),
        'p值': results_fe.pvalues.values.round(4),
        '95%置信区间下限': results_fe.conf_int().iloc[:, 0].values.round(4),
        '95%置信区间上限': results_fe.conf_int().iloc[:, 1].values.round(4),
        '显著性': ['***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '' for p in
                results_fe.pvalues.values]
    })
    # 拟合指标补充
    fit_metrics = pd.DataFrame({
        '标准化列名': [''] * 6,
        '变量含义': ['R²(整体)', '观测值数', '省份数', '时间期数', '聚类标准误', 'Hausman检验P值'],
        '系数': [
            round(results_fe.rsquared, 4), results_fe.nobs,
            df_panel.index.levels[0].nunique(), df_panel.index.levels[1].nunique(),
            cluster_level, round(hausman_p, 4) if not np.isnan(hausman_p) else ''
        ],
        '标准误': [''] * 6, 't值': [''] * 6, 'p值': [''] * 6,
        '95%置信区间下限': [''] * 6, '95%置信区间上限': [''] * 6, '显著性': [''] * 6
    })
    benchmark_result = pd.concat([benchmark_result, fit_metrics], ignore_index=True)

    # 保存滞后一期内生性处理结果
    if results_lag is not None:
        lag_result = pd.DataFrame({
            '标准化列名': results_lag.params.index,
            '变量含义': [core_vars['var_alias'].get(col, col) for col in results_lag.params.index],
            '系数': results_lag.params.values.round(4),
            '标准误': results_lag.std_errors.values.round(4),
            't值': results_lag.tstats.values.round(4),
            'p值': results_lag.pvalues.values.round(4),
            '显著性': ['***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '' for p in
                    results_lag.pvalues.values]
        })
        lag_path = os.path.join(output_path, 'regression_tables/1_2_滞后一期内生性处理结果.csv')
        os.makedirs(os.path.dirname(lag_path), exist_ok=True)
        lag_result.to_csv(lag_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ 滞后一期内生性处理结果已保存至：{lag_path}")

    # 保存基准回归结果
    result_path = os.path.join(output_path, 'regression_tables/1_基准回归结果.csv')
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    benchmark_result.to_csv(result_path, index=False, encoding='utf-8-sig')
    print(f"✅ 基准回归结果已保存至：{result_path}")

    # ---------------------- 5. DID数据传递 ----------------------
    df_reset = df.reset_index(drop=True)
    did_essential_vars = ['Treat', 'Post', 'DID', 'rel_year'] if 'rel_year' in df_reset.columns else ['Treat', 'Post',
                                                                                                      'DID']
    all_vars = list(dict.fromkeys(id_cols + did_essential_vars + keep_vars + [dep_var, core_exog]))
    valid_vars = [v for v in all_vars if v in df_reset.columns]
    df_keep_did = df_reset[valid_vars].drop_duplicates()
    df_keep_did[id_cols[1]] = pd.to_numeric(df_keep_did[id_cols[1]], errors='coerce').fillna(0).astype(int)

    return benchmark_result, df_keep_did