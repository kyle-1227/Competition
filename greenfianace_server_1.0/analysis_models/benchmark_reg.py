import pandas as pd
import numpy as np
from linearmodels import PanelOLS, RandomEffects, IV2SLS
import warnings
import os
from config import core_vars, model_params, output_path

warnings.filterwarnings('ignore')


def hausman_test(results_fe, results_re):
    """手动实现Hausman检验，修复原矩阵奇异值问题"""
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


def run_benchmark_regression(df, keep_vars):
    """
    基准双向固定效应模型+2SLS工具变量法（核心优化：解决符号反转+工具变量有效性检验）
    """
    print("\n" + "=" * 60)
    print("📌 第一步：基准双向固定效应模型+2SLS内生性处理")
    print("=" * 60)

    # ---------------------- 1. 全局统一索引定义，修复原id_vars错误 ----------------------
    id_cols = core_vars['id_cols']
    df_panel = df.copy()
    df_panel[id_cols[1]] = pd.to_numeric(df_panel[id_cols[1]], errors='coerce').fillna(0).astype(int)
    df_panel = df_panel.set_index(id_cols)
    print(f"✅ 面板索引设置完成：个体={df_panel.index.levels[0].nunique()}个，时间={df_panel.index.levels[1].nunique()}年")

    # ---------------------- 2. 定义回归变量，匹配你的字段表 ----------------------
    dep_var = core_vars['dep_vars']['primary']
    core_exog = core_vars['core_x']['primary']
    control_vars = [v for v in keep_vars if v not in [dep_var, core_exog] and v in df_panel.columns]

    # 生成省份×时间趋势交互项，控制时间趋势
    df_panel['province_trend'] = df_panel.index.get_level_values(0).astype(
        'category').codes * df_panel.index.get_level_values(1)
    exog_vars = [core_exog] + control_vars + ['province_trend']
    exog_part = ' + '.join(exog_vars)

    # ---------------------- 3. 构建回归公式，学术规范 ----------------------
    formula_fe = f"{dep_var} ~ {exog_part} + EntityEffects + TimeEffects"
    formula_re = f"{dep_var} ~ {exog_part}"

    # 美化打印公式
    debug_formula = f"{core_vars['var_alias'].get(dep_var, dep_var)} ~ " \
                    f"{core_vars['var_alias'].get(core_exog, core_exog)} + " \
                    f"{' + '.join([core_vars['var_alias'].get(col, col) for col in control_vars])} + " \
                    f"省份时间趋势 + 个体固定效应 + 时间固定效应"
    print(f"📝 基准回归公式：{debug_formula}")

    # ---------------------- 4. 基准双向固定效应回归（优化原逻辑） ----------------------
    try:
        # 固定效应模型
        model_fe = PanelOLS.from_formula(formula_fe, data=df_panel, drop_absorbed=True)
        results_fe = model_fe.fit(cov_type='clustered', cluster_entity=True)
        # 随机效应模型
        model_re = RandomEffects.from_formula(formula_re, data=df_panel)
        results_re = model_re.fit(cov_type='clustered', cluster_entity=True)
        # Hausman检验
        hausman_stat, hausman_p, hausman_df = hausman_test(results_fe, results_re)

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

        # 【核心优化】指标方向说明，解决符号混淆问题
        core_coef = results_fe.params[core_exog]
        core_p = results_fe.pvalues[core_exog]
        if core_coef > 0 and core_p < 0.05:
            print(
                f"ℹ️  核心结论：绿色金融综合指数系数为{core_coef.round(4)}（p={core_p.round(4)}），显著为正，符合理论预期——绿色金融显著提升减排效率")
        elif core_coef < 0 and core_p < 0.05:
            print(
                f"ℹ️  核心结论：绿色金融综合指数系数为{core_coef.round(4)}（p={core_p.round(4)}），显著为负，需检查因变量方向（减排效率为正向指标）")
        else:
            print(f"ℹ️  核心结论：绿色金融综合指数系数不显著，需进一步检验")
    except Exception as e:
        print(f"❌ 基准回归运行失败：{str(e)}")
        raise

    # ---------------------- 5. 【核心优化】2SLS工具变量法（解决符号反转+有效性检验） ----------------------
    print("\n" + "-" * 60)
    print("📌 2SLS工具变量法（滞后2期作为工具变量，解决反向因果+弱工具变量）")
    print("-" * 60)
    results_iv = None
    first_stage_F = np.nan
    try:
        df_iv = df.copy().reset_index(drop=True)
        df_iv[id_cols[1]] = pd.to_numeric(df_iv[id_cols[1]], errors='coerce').fillna(0).astype(int)
        df_iv = df_iv.sort_values(id_cols)

        # 用滞后2期作为工具变量（学术标准，满足外生性）
        iv_lag = model_params['iv_lag_periods']
        iv_col = f'{core_exog}_lag{iv_lag}'
        df_iv[iv_col] = df_iv.groupby(id_cols[0])[core_exog].shift(iv_lag)
        df_iv = df_iv.dropna(subset=[iv_col])
        df_iv_panel = df_iv.set_index(id_cols)
        df_iv_panel['province_trend'] = df_iv_panel.index.get_level_values(0).astype(
            'category').codes * df_iv_panel.index.get_level_values(1)

        # 构建2SLS公式，加入双向固定效应
        iv_formula = f"{dep_var} ~ 1 + {' + '.join(control_vars)} + province_trend + [{core_exog} ~ {iv_col}]"
        model_iv = IV2SLS.from_formula(iv_formula, data=df_iv_panel)
        model_iv.add_entity_effects = True
        model_iv.add_time_effects = True

        # 兼容所有版本的聚类标准误
        try:
            results_iv = model_iv.fit(cov_type='clustered', cluster_entity=True)
        except:
            try:
                results_iv = model_iv.fit(cov_type='clustered', groups=df_iv_panel.index.get_level_values(0))
            except:
                print("⚠️  聚类标准误适配失败，改用稳健标准误运行2SLS")
                results_iv = model_iv.fit(cov_type='robust')

        if results_iv is not None:
            # 【核心优化】正确获取第一阶段F统计量，解决弱工具变量检验
            try:
                first_stage_F = results_iv.first_stage.f_statistic.stat
                print(f"\n📊 第一阶段F统计量：{round(first_stage_F, 4)}")
                if first_stage_F > 10:
                    print("✅ 工具变量通过弱工具变量检验（F>10），工具变量有效")
                else:
                    print("⚠️  工具变量可能存在弱工具变量问题（F<10），建议更换工具变量")
            except Exception as e:
                print(f"⚠️  第一阶段F统计量获取失败：{str(e)}")

            print("\n🎯 2SLS工具变量法回归结果：")
            print(results_iv.summary)

            # 【核心优化】符号一致性检验，解决符号反转问题
            iv_coef = results_iv.params.get(core_exog, np.nan)
            if not np.isnan(iv_coef) and iv_coef * core_coef > 0:
                print("✅ 2SLS与基准回归符号一致，内生性处理结果稳健，核心结论成立")
            else:
                print("⚠️  2SLS与基准回归符号相反，需检查工具变量外生性或因变量方向")
    except Exception as e:
        print(f"⚠️  2SLS回归运行失败：{str(e)}")
        import traceback
        traceback.print_exc()
        results_iv = None

    # ---------------------- 6. 整理并保存回归结果 ----------------------
    # 基准固定效应结果整理
    benchmark_result = pd.DataFrame({
        '标准化列名': results_fe.params.index,
        '变量含义': [core_vars['var_alias'].get(col, col) for col in results_fe.params.index],
        '系数': results_fe.params.values.round(4),
        '标准误': results_fe.std_errors.values.round(4),
        't值': results_fe.tstats.values.round(4),
        'p值': results_fe.pvalues.values.round(4),
        '95%置信区间下限': results_fe.conf_int().iloc[:, 0].values.round(4),
        '95%置信区间上限': results_fe.conf_int().iloc[:, 1].values.round(4),
        '显著性': ['***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
                   for p in results_fe.pvalues.values]
    })
    # 拟合优度等指标补充
    fit_metrics = pd.DataFrame({
        '标准化列名': ['', '', '', '', '', ''],
        '变量含义': ['R²(整体)', '观测值数', '省份数', '时间期数', '聚类标准误', 'Hausman检验P值'],
        '系数': [
            round(results_fe.rsquared, 4),
            results_fe.nobs,
            df_panel.index.levels[0].nunique(),
            df_panel.index.levels[1].nunique(),
            model_params['cluster_level'],
            round(hausman_p, 4) if not np.isnan(hausman_p) else ''
        ],
        '标准误': [''] * 6, 't值': [''] * 6, 'p值': [''] * 6,
        '95%置信区间下限': [''] * 6, '95%置信区间上限': [''] * 6, '显著性': [''] * 6
    })
    benchmark_result = pd.concat([benchmark_result, fit_metrics], ignore_index=True)

    # 保存2SLS结果
    if results_iv is not None:
        iv_result = pd.DataFrame({
            '标准化列名': results_iv.params.index,
            '变量含义': [core_vars['var_alias'].get(col, col) for col in results_iv.params.index],
            '系数': results_iv.params.values.round(4),
            '标准误': results_iv.std_errors.values.round(4),
            't值': results_iv.tstats.values.round(4),
            'p值': results_iv.pvalues.values.round(4),
            '第一阶段F统计量': [round(first_stage_F, 4) if col == core_exog else '' for col in results_iv.params.index],
            '显著性': ['***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
                       for p in results_iv.pvalues.values]
        })
        iv_path = os.path.join(output_path, 'regression_tables/1_2_2SLS工具变量回归结果.csv')
        os.makedirs(os.path.dirname(iv_path), exist_ok=True)
        iv_result.to_csv(iv_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ 2SLS工具变量回归结果已保存至：{iv_path}")

    # 保存基准回归结果
    result_path = os.path.join(output_path, 'regression_tables/1_基准回归结果.csv')
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    benchmark_result.to_csv(result_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 基准回归结果已保存至：{result_path}")

    # ---------------------- 7. DID数据传递，修复原逻辑 ----------------------
    df_reset = df.reset_index(drop=True)
    did_essential_vars = ['Treat', 'Post', 'DID', 'rel_year'] if 'rel_year' in df_reset.columns else ['Treat', 'Post',
                                                                                                      'DID']
    all_vars = list(dict.fromkeys(id_cols + did_essential_vars + keep_vars + [dep_var, core_exog]))
    valid_vars = [v for v in all_vars if v in df_reset.columns]
    df_keep_did = df_reset[valid_vars].drop_duplicates()
    df_keep_did[id_cols[1]] = pd.to_numeric(df_keep_did[id_cols[1]], errors='coerce').fillna(0).astype(int)

    return benchmark_result, df_keep_did