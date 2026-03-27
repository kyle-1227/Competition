import os
import pandas as pd
import numpy as np
from linearmodels import PanelOLS
from scipy.stats import f
from config import core_vars, model_params, output_path


def chow_test(df_full, df_group1, df_group2, formula, id_cols):
    """Chow检验，适配linearmodels库"""
    try:
        model_full = PanelOLS.from_formula(formula, data=df_full.set_index(id_cols), drop_absorbed=True)
        res_full = model_full.fit()
        sse_full = (res_full.resids ** 2).sum()
        df_full = res_full.df_resid

        model1 = PanelOLS.from_formula(formula, data=df_group1.set_index(id_cols), drop_absorbed=True)
        res1 = model1.fit()
        sse1 = (res1.resids ** 2).sum()
        df1 = res1.df_resid

        model2 = PanelOLS.from_formula(formula, data=df_group2.set_index(id_cols), drop_absorbed=True)
        res2 = model2.fit()
        sse2 = (res2.resids ** 2).sum()
        df2 = res2.df_resid

        k = res_full.df_model
        chow_stat = ((sse_full - (sse1 + sse2)) / k) / ((sse1 + sse2) / (df1 + df2 - 2 * k))
        p_value = f.sf(chow_stat, k, df1 + df2 - 2 * k)
        return chow_stat.round(4), p_value.round(4)
    except Exception as e:
        print(f"⚠️  Chow检验计算失败：{str(e)}")
        return np.nan, np.nan


def run_group_regression(df: pd.DataFrame, group_col: str, group_name: str, keep_vars: list) -> pd.DataFrame:
    """分组回归函数+Chow检验"""
    df_group = df.reset_index(drop=True).copy()
    dep_var = core_vars['dep_vars']['primary']
    core_x = core_vars['core_x']['primary']
    control_vars = [var for var in keep_vars if var != core_x and var in df_group.columns]
    id_cols = core_vars['id_cols']  # 【核心修复】id_vars→id_cols
    formula = f"{dep_var} ~ {core_x} + {' + '.join(control_vars) if control_vars else ''} + EntityEffects + TimeEffects"

    if group_col not in df_group.columns:
        print(f"⚠️  分组变量{group_col}不存在，跳过{group_name}分组")
        return pd.DataFrame()

    # 确定分组
    if group_col == 'region':
        groups = df_group[group_col].dropna().unique()
    else:
        if not pd.api.types.is_numeric_dtype(df_group[group_col]):
            print(f"⚠️  分组变量{group_col}非数值型，跳过{group_name}分组")
            return pd.DataFrame()
        split_value = df_group[group_col].quantile(model_params['group_split_quantile'])
        df_group['group'] = np.where(df_group[group_col] >= split_value, '高组', '低组')
        groups = ['高组', '低组']
        group_stats = df_group['group'].value_counts()
        print(
            f"\n📊 {group_name}分组：阈值={split_value.round(4)}，高组{group_stats.get('高组', 0)}个，低组{group_stats.get('低组', 0)}个")

    # 分组回归
    group_results = []
    group_dfs = {}
    for group in groups:
        if group_col == 'region':
            df_sub = df_group[df_group['region'] == group].copy()
        else:
            df_sub = df_group[df_group['group'] == group].copy()
        if len(df_sub) < 10:
            print(f"⚠️  {group_name}-{group}观测值过少，跳过回归")
            continue
        group_dfs[group] = df_sub
        df_sub_panel = df_sub.set_index(id_cols).sort_index()
        try:
            model = PanelOLS.from_formula(formula, data=df_sub_panel, drop_absorbed=True)
            result = model.fit(cov_type='clustered', cluster_entity=True)
            group_results.append({
                '分组维度': group_name,
                '分组类型': group,
                '核心变量': core_x,
                '核心变量含义': core_vars['var_alias'].get(core_x, core_x),
                '核心变量系数': round(result.params[core_x], 4),
                '标准误': round(result.std_errors[core_x], 4),
                't值': round(result.tstats[core_x], 4),
                'P值': round(result.pvalues[core_x], 4),
                '显著性': '***' if result.pvalues[core_x] < 0.001 else '**' if result.pvalues[core_x] < 0.01 else '*' if
                result.pvalues[core_x] < 0.05 else '',
                'R²': round(result.rsquared, 4),
                '观测值数量': result.nobs
            })
        except Exception as e:
            print(f"⚠️  {group_name}-{group}回归失败：{str(e)}")
            continue

    # Chow检验
    if len(group_dfs) == 2:
        chow_stat, chow_p = chow_test(df_group, group_dfs['高组'], group_dfs['低组'], formula, id_cols)
        print(f"📊 {group_name}组间差异Chow检验：统计量={chow_stat}，P值={chow_p}")
        for res in group_results:
            res['Chow检验P值'] = chow_p
    elif len(group_dfs) >= 3:
        for res in group_results:
            res['Chow检验P值'] = np.nan
    return pd.DataFrame(group_results)


def run_heterogeneity_analysis(df: pd.DataFrame, keep_vars: list) -> pd.DataFrame:
    """异质性分析（分组回归+交互项+Chow检验+补充时间异质性）"""
    print("\n" + "=" * 60)
    print("📌 第四步：异质性分析（分组回归+交互项+Chow检验+时间异质性）")
    print("=" * 60)

    # 1. 自动生成东中西部region列
    df_heter = df.copy()
    region_map = {}
    for region, provinces in core_vars['region_split'].items():
        for prov in provinces:
            region_map[prov] = region
    df_heter['region'] = df_heter['省份'].map(region_map)

    # 2. 分组配置（补充时间异质性）
    group_configs = [
        ('region', '东中西部区域'),
        ('地区生产总值', '经济水平'),
        ('能源消费总量', '能源依赖度'),
        ('年末常住人口', '人口规模'),
        ('年份', '时间异质性（政策前后）')  # 【补充评估要求】时间异质性
    ]

    # 3. 批量运行分组回归
    all_group_results = []
    for group_col, group_name in group_configs:
        # 时间异质性特殊处理
        if group_name == '时间异质性（政策前后）':
            df_heter['time_group'] = np.where(df_heter['年份'] >= core_vars['did_config']['policy_year'], '政策后',
                                              '政策前')
            group_res = run_group_regression(df_heter.rename(columns={'time_group': group_col}), group_col, group_name,
                                             keep_vars)
        else:
            group_res = run_group_regression(df_heter, group_col, group_name, keep_vars)
        if not group_res.empty:
            all_group_results.append(group_res)

    # 4. 交互项回归
    print("\n" + "-" * 60)
    print("📌 交互项回归（验证异质性）")
    print("-" * 60)
    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']
    core_x = core_vars['core_x']['primary']
    control_vars = [v for v in keep_vars if v != core_x and v in df_heter.columns]
    df_heter_panel = df_heter.set_index(id_cols)

    df_heter_panel['东部_dummy'] = np.where(
        df_heter_panel.index.get_level_values(0).isin(core_vars['region_split']['东部']), 1, 0)
    df_heter_panel['gfi_east'] = df_heter_panel[core_x] * df_heter_panel['东部_dummy']

    interact_formula = f"{dep_var} ~ {core_x} + gfi_east + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
    try:
        model_interact = PanelOLS.from_formula(interact_formula, data=df_heter_panel, drop_absorbed=True)
        res_interact = model_interact.fit(cov_type='clustered', cluster_entity=True)
        print("\n🎯 区域交互项回归结果：")
        print(res_interact.params[['gfi_std', 'gfi_east']])
    except Exception as e:
        print(f"⚠️  交互项回归运行失败：{str(e)}")

    if not all_group_results:
        print("⚠️  无有效分组回归结果，跳过异质性分析")
        return pd.DataFrame()

    # 5. 保存结果
    heterogeneity_table = pd.concat(all_group_results, ignore_index=True)
    print("\n📊 异质性分析汇总结果：")
    print(heterogeneity_table.to_string(index=False))
    save_path = os.path.join(output_path, 'regression_tables/4_异质性分析结果.csv')
    heterogeneity_table.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 异质性分析结果已保存至：{save_path}")
    return heterogeneity_table