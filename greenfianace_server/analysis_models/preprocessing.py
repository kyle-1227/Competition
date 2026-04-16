import pandas as pd
import numpy as np
from scipy.stats.mstats import winsorize
from statsmodels.stats.outliers_influence import variance_inflation_factor
import os
from config import core_vars, preprocess_params, output_path, file_paths, RUN_LEVEL


def full_preprocessing_pipeline(df):
    print("\n" + "=" * 60)
    print("🔧 全量数据预处理全流程")
    print("=" * 60)

    df_processed = df.copy().reset_index(drop=True)
    id_cols = core_vars['id_cols']
    entity_col = id_cols[0]
    year_col = id_cols[1]

    dep_var_final = core_vars['dep_vars']['primary']
    core_x_raw = core_vars['core_x']['raw']
    core_x_final = core_vars['core_x']['primary']
    invert_switch = preprocess_params['dep_var_invert']
    invert_executed = False

    # ---------------------- 1. 因变量方向修正 ----------------------
    if invert_switch and not invert_executed and dep_var_final in df_processed.columns:
        df_processed[dep_var_final] = -df_processed[dep_var_final]
        invert_executed = True
        print(f"✅ 已对因变量【{dep_var_final}】取反")
    else:
        print(f"ℹ️  因变量【{dep_var_final}】方向已固定")

    # ---------------------- 2. 核心字段校验 ----------------------
    print("\n📋 核心字段校验")
    missing_id = [col for col in id_cols if col not in df_processed.columns]
    if missing_id:
        raise ValueError(f"❌ 缺失面板索引字段：{missing_id}")
    df_processed[year_col] = pd.to_numeric(df_processed[year_col], errors='coerce').fillna(0).astype(int)
    print(f"✅ 已存在核心因变量：{dep_var_final}（正向指标）")

    # ---------------------- 3. DID变量 ----------------------
    print("✅ DID变量已存在，直接使用原始数据")

    # ---------------------- 4. 中介变量自动生成 ----------------------
    if '产业结构高级化' not in df_processed.columns and all(
            col in df_processed.columns for col in ['第三产业增加值', '第二产业增加值']):
        df_processed['产业结构高级化'] = df_processed['第三产业增加值'] / df_processed['第二产业增加值'].clip(
            lower=1e-8)
        print("✅ 生成中介变量：产业结构高级化")
    if '能源利用效率' not in df_processed.columns and all(
            col in df_processed.columns for col in ['地区生产总值', '能源消费总量']):
        df_processed['能源利用效率'] = df_processed['地区生产总值'] / df_processed['能源消费总量'].clip(lower=1e-8)
        print("✅ 生成中介变量：能源利用效率")
    if '绿色信贷规模' not in df_processed.columns and all(
            col in df_processed.columns for col in ['绿色信贷', '地区生产总值']):
        df_processed['绿色信贷规模'] = df_processed['绿色信贷'] / df_processed['地区生产总值'].clip(lower=1e-8)
        print("✅ 生成中介变量：绿色信贷规模占比")
    if 'indus_2' not in df_processed.columns and all(
            col in df_processed.columns for col in ['第二产业增加值', '地区生产总值']):
        df_processed['indus_2'] = df_processed['第二产业增加值'] / df_processed['地区生产总值'].clip(lower=1e-8)
        print("✅ 生成控制变量：第二产业增加值占比（indus_2）")

    # ---------------------- 5. 政策控制变量 ----------------------
    if RUN_LEVEL == "province":
        other_policies = core_vars['other_policies']
        if 'carbon_trading' not in df_processed.columns:
            df_processed['carbon_trading'] = np.where(
                (df_processed[entity_col].isin(other_policies['carbon_trading_provinces'])) &
                (df_processed[year_col] >= other_policies['carbon_trading_year']), 1, 0
            )
            print("✅ 生成控制变量：碳交易试点政策虚拟变量")
        if 'environmental_tax' not in df_processed.columns:
            df_processed['environmental_tax'] = np.where(
                df_processed[year_col] >= other_policies['environmental_tax_year'], 1, 0
            )
            print("✅ 生成控制变量：环保税政策虚拟变量")
    else:
        print("ℹ️  地级市/企业层级，跳过省级专属政策变量生成")

    # ---------------------- 6. 核心变量标准化+对数化 ----------------------
    if core_x_final not in df_processed.columns and core_x_raw in df_processed.columns:
        df_processed[core_x_final] = (df_processed[core_x_raw] - df_processed[core_x_raw].mean()) / df_processed[
            core_x_raw].std()
        print(f"✅ 生成标准化核心解释变量：{core_x_final}")

    # ====================== 🔥 核心修改：删除ln_GDP，解决共线性 ======================
    # 原代码生成ln_GDP，现在注释掉/删除，彻底不生成
    # 只保留ln_pop，剔除ln_GDP
    log_vars = {k: v for k, v in {'年末常住人口': 'ln_pop'}.items() if k in df_processed.columns}
    for raw_col, log_col in log_vars.items():
        if log_col not in df_processed.columns:
            df_processed[log_col] = np.log(df_processed[raw_col].clip(lower=1e-8))
            print(f"✅ 生成对数化控制变量：{log_col}")
    # ==============================================================================

    # ---------------------- 7. 异常值处理（剔除ln_GDP） ----------------------
    base_process_cols = [
        dep_var_final, core_x_final,
        '能源强度', '人均能源消耗',  # 删掉ln_GDP
        '产业结构高级化', '能源利用效率', '绿色信贷规模'
    ]
    numeric_cols = [col for col in base_process_cols if
                    col in df_processed.columns and pd.api.types.is_numeric_dtype(df_processed[col])]
    for col in numeric_cols:
        df_processed[col] = np.asarray(winsorize(df_processed[col], limits=preprocess_params['winsorize_limits']))
    print(f"✅ 1%缩尾处理完成，涉及变量：{numeric_cols}")

    # ---------------------- 8. VIF多重共线性检验 ----------------------
    control_vars = [v for v in core_vars['control_vars'] if v in df_processed.columns]
    # 🔥 强制剔除ln_GDP
    control_vars = [v for v in control_vars if v not in ['ln_GDP', 'lnGDP']]

    test_cols = [core_x_final] + control_vars
    test_cols = [x for x in test_cols if x in df_processed.columns]
    df_vif = df_processed[test_cols].dropna()
    keep_control_vars = [x for x in control_vars if x in df_processed.columns]

    if len(df_vif) > 0 and len(test_cols) > 1:
        vif_result = pd.DataFrame({
            '变量名': test_cols,
            'VIF值': [variance_inflation_factor(df_vif.values, i) for i in range(df_vif.shape[1])]
        })
        print(f"\n📊 最终VIF检验结果：\n{vif_result.to_string(index=False)}")

    if not keep_control_vars:
        keep_control_vars = ['ln_pop'] if 'ln_pop' in df_processed.columns else []
    keep_vars = [core_x_final] + keep_control_vars + core_vars.get("spatial_cols", [])
    print(f"\n✅ 最终保留变量：{keep_vars}")

    # ---------------------- 9. 导出最终数据集 ----------------------
    try:
        final_data_save_path = file_paths['最终清洗数据集']
        os.makedirs(os.path.dirname(final_data_save_path), exist_ok=True)
        df_processed.to_csv(final_data_save_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ 最终面板数据集已导出：{final_data_save_path}")
    except:
        print("⚠️  数据集导出失败")

    # ---------------------- 10. 描述性统计 ----------------------
    desc_cols = [dep_var_final] + keep_vars + ['产业结构高级化', '能源利用效率', '绿色信贷规模']
    desc_cols = [col for col in desc_cols if col in df_processed.columns]
    desc_stats = df_processed[desc_cols].describe().T.round(4)
    desc_path = os.path.join(output_path, 'test_results/描述性统计.csv')
    os.makedirs(os.path.dirname(desc_path), exist_ok=True)
    desc_stats.to_csv(desc_path, encoding='utf-8-sig')
    print(f"✅ 描述性统计已保存")

    return df_processed, keep_vars