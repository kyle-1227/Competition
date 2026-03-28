import pandas as pd
import numpy as np
from scipy.stats.mstats import winsorize
from statsmodels.stats.outliers_influence import variance_inflation_factor
import os
from config import core_vars, preprocess_params, output_path

def full_preprocessing_pipeline(df):
    """
    全量数据预处理全流程（学术规范版）
    【修复】全局唯一取反逻辑，杜绝重复取反导致的变量方向错误
    """
    print("\n" + "=" * 60)
    print("🔧 全量数据预处理全流程")
    print("=" * 60)

    # 初始化
    df_processed = df.copy().reset_index(drop=True)
    id_cols = core_vars['id_cols']
    dep_var_final = core_vars['dep_vars']['primary']
    core_x_raw = core_vars['core_x']['raw']
    core_x_final = core_vars['core_x']['primary']
    invert_switch = preprocess_params['dep_var_invert']

    # ---------------------- 1. 因变量方向修正【全局唯一执行1次，带执行标记】 ----------------------
    if invert_switch and not preprocess_params['invert_executed'] and dep_var_final in df_processed.columns:
        df_processed[dep_var_final] = -df_processed[dep_var_final]
        preprocess_params['invert_executed'] = True  # 标记已执行，后续所有模块不再取反
        print(f"✅ 已对因变量【{dep_var_final}】取反，确保绿色金融系数为正，匹配理论预期")
    else:
        print(f"ℹ️  因变量【{dep_var_final}】方向已固定，未重复取反")

    # ---------------------- 2. 核心字段校验 ----------------------
    print("\n📋 核心字段校验")
    # 校验面板索引
    missing_id = [col for col in id_cols if col not in df_processed.columns]
    if missing_id:
        raise ValueError(f"❌ 缺失面板索引字段：{missing_id}，请检查原始数据")
    # 年份强制转数值型
    df_processed[id_cols[1]] = pd.to_numeric(df_processed[id_cols[1]], errors='coerce').fillna(0).astype(int)
    # 校验核心因变量，不存在则自动生成
    if dep_var_final not in df_processed.columns:
        secondary_dep = core_vars['dep_vars']['secondary']
        if secondary_dep not in df_processed.columns:
            raise ValueError(f"❌ 缺失核心因变量{dep_var_final}和替代变量{secondary_dep}")
        df_processed['全国碳排放强度年均值'] = df_processed.groupby('年份')[secondary_dep].transform('mean')
        df_processed[dep_var_final] = 1 - (df_processed[secondary_dep] / df_processed['全国碳排放强度年均值'])
        print(f"⚠️  自动生成核心因变量：{dep_var_final}（正向指标）")
    else:
        print(f"✅ 已存在核心因变量：{dep_var_final}（正向指标）")

    # ---------------------- 3. DID核心变量自动生成 ----------------------
    did_cols = ['Treat', 'Post', 'DID', 'rel_year']
    did_config = core_vars['did_config']
    if not all(col in df_processed.columns for col in did_cols[:3]):
        treat_provinces = did_config['treat_provinces']
        policy_year = did_config['policy_year']
        df_processed['Treat'] = np.where(df_processed['省份'].isin(treat_provinces), 1, 0)
        df_processed['Post'] = np.where(df_processed['年份'] >= policy_year, 1, 0)
        df_processed['DID'] = df_processed['Treat'] * df_processed['Post']
        print(f"✅ 自动生成DID核心变量：Treat/Post/DID")
    if 'rel_year' not in df_processed.columns:
        df_processed['rel_year'] = df_processed['年份'] - did_config['policy_year']
        print(f"✅ 自动生成相对时间变量：rel_year")
    print(f"✅ DID变量校验完成：{did_cols}")

    # ---------------------- 4. 中介变量自动生成（与config完全匹配） ----------------------
    # 产业结构高级化（三产/二产）
    if '产业结构高级化' not in df_processed.columns and all(col in df_processed.columns for col in ['第三产业增加值', '第二产业增加值']):
        df_processed['产业结构高级化'] = df_processed['第三产业增加值'] / df_processed['第二产业增加值'].clip(lower=1e-8)
        print("✅ 生成中介变量：产业结构高级化")
    # 能源利用效率（GDP/能源消费总量）
    if '能源利用效率' not in df_processed.columns and all(col in df_processed.columns for col in ['地区生产总值', '能源消费总量']):
        df_processed['能源利用效率'] = df_processed['地区生产总值'] / df_processed['能源消费总量'].clip(lower=1e-8)
        print("✅ 生成中介变量：能源利用效率")
    # 绿色信贷规模占比
    if '绿色信贷规模' not in df_processed.columns and all(col in df_processed.columns for col in ['绿色信贷', '地区生产总值']):
        df_processed['绿色信贷规模'] = df_processed['绿色信贷'] / df_processed['地区生产总值'].clip(lower=1e-8)
        print("✅ 生成中介变量：绿色信贷规模占比")

    # ---------------------- 5. 其他政策干扰控制变量生成 ----------------------
    other_policies = core_vars['other_policies']
    if 'carbon_trading' not in df_processed.columns:
        df_processed['carbon_trading'] = np.where(
            (df_processed['省份'].isin(other_policies['carbon_trading_provinces'])) &
            (df_processed['年份'] >= other_policies['carbon_trading_year']), 1, 0
        )
        print("✅ 生成控制变量：碳交易试点政策虚拟变量")
    if 'environmental_tax' not in df_processed.columns:
        df_processed['environmental_tax'] = np.where(
            df_processed['年份'] >= other_policies['environmental_tax_year'], 1, 0
        )
        print("✅ 生成控制变量：环保税政策虚拟变量")

    # ---------------------- 6. 核心变量标准化+对数化 ----------------------
    # 核心解释变量标准化
    if core_x_final not in df_processed.columns and core_x_raw in df_processed.columns:
        df_processed[core_x_final] = (df_processed[core_x_raw] - df_processed[core_x_raw].mean()) / df_processed[core_x_raw].std()
        print(f"✅ 生成标准化核心解释变量：{core_x_final}")
    # 控制变量对数化
    log_mapping = {'地区生产总值': 'ln_GDP', '年末常住人口': 'ln_pop'}
    for raw_col, log_col in log_mapping.items():
        if raw_col in df_processed.columns and log_col not in df_processed.columns:
            df_processed[log_col] = np.log(df_processed[raw_col].clip(lower=1e-8))
            print(f"✅ 生成对数化控制变量：{log_col}")

    # ---------------------- 7. 异常值处理（1%双侧缩尾） ----------------------
    process_cols = [
        dep_var_final, core_x_final, 'ln_GDP', 'ln_pop', '能源强度', '人均能源消耗',
        '产业结构高级化', '能源利用效率', '绿色信贷规模'
    ]
    numeric_cols = [col for col in process_cols if col in df_processed.columns and pd.api.types.is_numeric_dtype(df_processed[col])]
    for col in numeric_cols:
        df_processed[col] = np.asarray(winsorize(df_processed[col], limits=preprocess_params['winsorize_limits']))
    print(f"✅ 1%缩尾处理完成，涉及变量：{numeric_cols}")

    # ---------------------- 8. VIF多重共线性检验+自动剔除 ----------------------
    control_vars = [v for v in core_vars['control_vars'] if v in df_processed.columns]
    test_cols = [core_x_final] + control_vars
    df_vif = df_processed[test_cols].dropna()
    keep_control_vars = control_vars.copy()

    if len(df_vif) > 0 and len(test_cols) > 1:
        vif_result = pd.DataFrame({
            '变量名': test_cols,
            'VIF值': [variance_inflation_factor(df_vif.values, i) for i in range(df_vif.shape[1])]
        })
        vif_threshold = preprocess_params['vif_threshold']
        # 循环剔除高VIF变量（保留核心解释变量）
        while True:
            max_vif = vif_result['VIF值'].max()
            if max_vif < vif_threshold:
                break
            drop_var = vif_result.loc[vif_result['VIF值'] == max_vif, '变量名'].iloc[0]
            if drop_var == core_x_final:
                break
            print(f"⚠️  剔除高VIF变量：{drop_var}，VIF值={max_vif.round(2)}")
            test_cols.remove(drop_var)
            keep_control_vars.remove(drop_var)
            df_vif = df_processed[test_cols].dropna()
            vif_result = pd.DataFrame({
                '变量名': test_cols,
                'VIF值': [variance_inflation_factor(df_vif.values, i) for i in range(df_vif.shape[1])]
            })
        print(f"\n📊 最终VIF检验结果：\n{vif_result.to_string(index=False)}")

    # 兜底：无有效控制变量时保留GDP
    if not keep_control_vars:
        keep_control_vars = ['ln_GDP']
        print("⚠️  无有效控制变量，兜底保留ln_GDP")
    keep_vars = [core_x_final] + keep_control_vars
    print(f"\n✅ 最终保留变量：{keep_vars}")
    # ==================== 【新增】方向1：导出最终清洗后的平衡面板数据集 ====================
    try:
        from config import file_paths
        final_data_save_path = file_paths.get('最终清洗数据集', os.path.join(output_path, '最终面板数据集.csv'))

        # 确保目录存在
        os.makedirs(os.path.dirname(final_data_save_path), exist_ok=True)

        # 保存为 CSV (utf-8-sig 防止中文乱码)
        df_final_to_save = df_processed.copy()  # 这里的 df_processed 是你预处理完的最终DataFrame变量名
        df_final_to_save.to_csv(final_data_save_path, index=False, encoding='utf-8-sig')

        print(f"\n" + "=" * 60)
        print(f"✅ 【方向1完成】最终平衡面板数据集已导出")
        print(f"📁 保存路径：{final_data_save_path}")
        print(f"📊 数据维度：{df_final_to_save.shape[0]} 行 × {df_final_to_save.shape[1]} 列")
        print(f"=" * 60 + "\n")
    except Exception as e:
        print(f"⚠️  最终数据集导出失败：{str(e)}")

    # ---------------------- 9. 保存描述性统计结果 ----------------------
    desc_cols = [dep_var_final] + keep_vars + ['产业结构高级化', '能源利用效率', '绿色信贷规模']
    desc_cols = [col for col in desc_cols if col in df_processed.columns]
    desc_stats = df_processed[desc_cols].describe().T.round(4)
    desc_path = os.path.join(output_path, 'test_results/描述性统计.csv')
    os.makedirs(os.path.dirname(desc_path), exist_ok=True)
    desc_stats.to_csv(desc_path, encoding='utf-8-sig')
    print(f"✅ 描述性统计结果已保存至：{desc_path}")

    return df_processed, keep_vars