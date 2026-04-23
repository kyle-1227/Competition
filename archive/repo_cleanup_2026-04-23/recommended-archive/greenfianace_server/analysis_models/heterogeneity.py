import os
import pandas as pd
import numpy as np
from linearmodels import PanelOLS
import warnings
# 🔥 最小改动：新增导入 RUN_LEVEL，兼容3套数据
from config import core_vars, model_params, output_path, RUN_LEVEL

warnings.filterwarnings('ignore')


def run_province_interaction_heterogeneity(df: pd.DataFrame) -> pd.DataFrame:
    """【仅省级运行】异质性分析：交互项法（最终修复版）"""
    if RUN_LEVEL != "province":
        return pd.DataFrame()

    print("\n" + "=" * 60)
    print("📌 【省级专属】异质性分析：交互项法（顶刊规范，最终修复版）")
    print("=" * 60)

    df_heter = df.copy()
    id_cols = core_vars['id_cols']
    dep_var = '碳排放强度'
    core_x = 'gfi_std'

    # 匹配数据真实变量
    control_vars = ['第二产业增加值占GDP比重', '人均能源消耗', '人均地区生产总值']
    control_vars = [v for v in control_vars if v in df_heter.columns]

    interaction_configs = [
        ('第二产业增加值占GDP比重', '产业结构异质性', '高二产占比'),
        ('人均能源消耗', '能源依赖度异质性', '高能源消耗'),
    ]

    all_interact_results = []

    for base_var, dim_name, high_group_name in interaction_configs:
        if base_var not in df_heter.columns:
            continue

        median_val = df_heter[base_var].median()
        df_heter[f'high_{base_var}'] = (df_heter[base_var] >= median_val).astype(int)

        interact_col = f'{core_x}_x_high_{base_var}'
        df_heter[interact_col] = df_heter[core_x] * df_heter[f'high_{base_var}']

        df_reg = df_heter.dropna(subset=[f'high_{base_var}']).set_index(id_cols)
        formula = f"{dep_var} ~ 1 + {core_x} + {interact_col} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"

        try:
            model = PanelOLS.from_formula(formula, data=df_reg, drop_absorbed=True)
            if RUN_LEVEL == 'province':
                res = model.fit(cov_type="clustered", cluster_entity=True)
            else:
                res = model.fit(cov_type="clustered", cluster_entity=True, cluster_time=True)

            all_interact_results.append({
                '异质性维度': dim_name,
                '核心变量': core_x,
                '核心变量系数': round(res.params[core_x], 4),
                '核心变量P值': round(res.pvalues[core_x], 4),
                f'交乘项({core_x}×{high_group_name})': round(res.params[interact_col], 4),
                '交乘项P值': round(res.pvalues[interact_col], 4),
                '结论': f'{high_group_name}地区效应更强' if res.params[
                                                                interact_col] < 0 else f'{high_group_name}地区更弱',
                'R²': round(res.rsquared, 4),
                '观测值数量': res.nobs
            })
            print(f"\n✅ {dim_name}交互项回归完成：")
            print(f"   核心变量系数：{res.params[core_x]:.4f} (p={res.pvalues[core_x]:.4f})")
            print(f"   交乘项系数：{res.params[interact_col]:.4f} (p={res.pvalues[interact_col]:.4f})")
        except Exception as e:
            print(f"⚠️  {dim_name}交互项回归失败：{e}")
            continue

    if not all_interact_results:
        return pd.DataFrame()

    save_path = os.path.join(output_path, 'regression_tables/4_3_省级交互项异质性结果.csv')
    interact_result_df = pd.DataFrame(all_interact_results)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    interact_result_df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 【省级专属】交互项异质性结果已保存至：{save_path}")
    return interact_result_df


def run_group_regression(df: pd.DataFrame, group_col: str, group_name: str, keep_vars: list) -> pd.DataFrame:
    """分组回归函数【最终修复版：无重复逻辑+无报错】"""
    df_group = df.reset_index(drop=True).copy()
    dep_var = core_vars['dep_vars']['primary']
    core_x = core_vars['core_x']['primary']
    id_cols = core_vars['id_cols']

    # 控制变量自动适配层级
    if RUN_LEVEL == "province":
        control_vars = ['第二产业增加值占GDP比重', '人均能源消耗', '人均地区生产总值']
        control_vars = [v for v in control_vars if v in df_group.columns]
    else:
        control_vars = [var for var in core_vars['control_vars'] if var in df_group.columns and var != core_x]

    formula = f"{dep_var} ~ {core_x} + {' + '.join(control_vars) if control_vars else ''} + EntityEffects + TimeEffects"
    min_sample_threshold = 15

    # 校验分组变量
    if group_col not in df_group.columns:
        print(f"⚠️  分组变量{group_col}不存在，跳过{group_name}分组")
        return pd.DataFrame()

    # ===================== 分组逻辑：修复重复赋值，互不干扰 =====================
    if group_col == 'region':
        # 东中西部分组（仅省级）
        groups = df_group[group_col].dropna().unique()
    elif group_col == '长江经济带':
        # 长江经济带：根治map报错，强制类型转换+替换
        df_group[group_col] = pd.to_numeric(df_group[group_col], errors='coerce').fillna(0).astype(int)
        df_group['group'] = df_group[group_col].replace({1: '长江经济带', 0: '非长江经济带'})
        groups = ['长江经济带', '非长江经济带']
    else:
        # 连续变量中位数分组
        if not pd.api.types.is_numeric_dtype(df_group[group_col]):
            print(f"⚠️  分组变量{group_col}非数值型，跳过")
            return pd.DataFrame()
        split_value = df_group[group_col].median()
        df_group['group'] = np.where(df_group[group_col] >= split_value, '高组', '低组')
        groups = ['高组', '低组']
        group_stats = df_group['group'].value_counts()
        print(
            f"\n📊 {group_name}分组：阈值={split_value.round(4)}，高组{group_stats.get('高组', 0)}，低组{group_stats.get('低组', 0)}")

    # 分组回归
    group_results = []
    for group in groups:
        df_sub = df_group[df_group['group'] == group].copy() if group_col != 'region' else df_group[
            df_group[group_col] == group].copy()

        if len(df_sub) < min_sample_threshold:
            print(f"⚠️  {group_name}-{group}观测值过少，跳过")
            continue

        df_sub_panel = df_sub.set_index(id_cols).sort_index()
        try:
            model = PanelOLS.from_formula(formula, data=df_sub_panel, drop_absorbed=True)
            # 聚类标准误适配层级
            if RUN_LEVEL == 'province':
                result = model.fit(cov_type="clustered", cluster_entity=True)
            else:
                result = model.fit(cov_type="clustered", cluster_entity=True, cluster_time=True)

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

    return pd.DataFrame(group_results)


def run_heterogeneity_analysis(df: pd.DataFrame, keep_vars: list) -> pd.DataFrame:
    """异质性分析【最终修复版：地级市/省级全自动适配，零报错】"""
    print("\n" + "=" * 60)
    print("📌 异质性分析（分组回归+交互项）")
    print("=" * 60)

    df_heter = df.copy()
    id_cols = core_vars['id_cols']
    entity_col = id_cols[0]

    # 仅省级添加东中西部
    if RUN_LEVEL == "province":
        region_map = {prov: region for region, pro_list in core_vars['region_split'].items() for prov in pro_list}
        df_heter['region'] = df_heter[entity_col].map(region_map)
    else:
        df_heter['region'] = np.nan

    # 地级市：清洗长江经济带列
    if RUN_LEVEL == "city" and '长江经济带' in df_heter.columns:
        df_heter['长江经济带'] = pd.to_numeric(df_heter['长江经济带'], errors='coerce').fillna(0).astype(int)
        print("✅ 长江经济带列已转为0-1数值型")

    # 省级专属交互项
    if RUN_LEVEL == "province":
        run_province_interaction_heterogeneity(df)

    # ===================== 分组配置：自动适配层级 =====================
    group_configs = []
    # 地级市优先加长江经济带
    if RUN_LEVEL == "city" and '长江经济带' in df_heter.columns:
        group_configs.append(('长江经济带', '长江经济带'))
        print("✅ 检测到【长江经济带】列，已加入分组")
    # 省级加东中西部
    if RUN_LEVEL == "province":
        group_configs.append(('region', '东中西部区域'))
    # 通用分组
    group_configs.extend([
        ('人均地区生产总值', '经济水平'),
        ('人均能源消耗', '能源依赖度'),
    ])

    # 执行分组回归
    all_group_results = []
    for group_col, group_name in group_configs:
        try:
            group_res = run_group_regression(df_heter, group_col, group_name, keep_vars)
            if not group_res.empty:
                all_group_results.append(group_res)
        except Exception as e:
            print(f"⚠️  {group_name}分组失败：{e}")
            continue

    # 交互项回归（仅省级）
    print("\n" + "-" * 60)
    print("📌 交互项回归（验证异质性）")
    print("-" * 60)
    if RUN_LEVEL == "province":
        try:
            dep_var = core_vars['dep_vars']['primary']
            core_x = core_vars['core_x']['primary']
            control_vars = [v for v in ['第二产业增加值占GDP比重', '人均能源消耗', '人均地区生产总值'] if
                            v in df_heter.columns]
            df_heter_panel = df_heter.set_index(id_cols)

            df_heter_panel['东部_dummy'] = np.where(
                df_heter_panel.index.get_level_values(0).isin(core_vars['region_split']['东部']), 1, 0)
            interact_col = f'{core_x}_east'
            df_heter_panel[interact_col] = df_heter_panel[core_x] * df_heter_panel['东部_dummy']

            interact_formula = f"{dep_var} ~ {core_x} + {interact_col} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
            model_interact = PanelOLS.from_formula(interact_formula, data=df_heter_panel, drop_absorbed=True)
            res_interact = model_interact.fit(cov_type="clustered", cluster_entity=True)

            print("\n🎯 区域交互项回归结果：")
            print(res_interact.params[[core_x, interact_col]])

            interact_save_path = os.path.join(output_path, 'regression_tables/4_2_区域交互项回归结果.csv')
            interact_result = pd.DataFrame({
                '变量名': res_interact.params.index,
                '变量含义': [core_vars['var_alias'].get(col, col) for col in res_interact.params.index],
                '系数': res_interact.params.values.round(4),
                '标准误': res_interact.std_errors.values.round(4),
                'P值': res_interact.pvalues.values.round(4),
                '显著性': ['***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '' for p in
                           res_interact.pvalues.values]
            })
            os.makedirs(os.path.dirname(interact_save_path), exist_ok=True)
            interact_result.to_csv(interact_save_path, index=False, encoding='utf-8-sig')
            print(f"✅ 区域交互项回归结果已保存至：{interact_save_path}")
        except Exception as e:
            print(f"⚠️  交互项回归运行失败：{str(e)}")
    else:
        print("ℹ️  非省级数据，跳过区域交互项回归")

    # 输出结果
    if not all_group_results:
        print("⚠️  无有效分组回归结果，跳过异质性分析")
        return pd.DataFrame()

    heterogeneity_table = pd.concat(all_group_results, ignore_index=True)
    print("\n📊 异质性分析汇总结果：")
    print(heterogeneity_table.to_string(index=False))

    save_path = os.path.join(output_path, 'regression_tables/4_异质性分析结果.csv')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    heterogeneity_table.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 异质性分析结果已保存至：{save_path}")

    return heterogeneity_table