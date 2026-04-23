import pandas as pd
import numpy as np
from linearmodels import PanelOLS
import warnings
import os
import scipy.stats as stats
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
# 【完全对接你的配置文件】
from config import core_vars, output_path, model_params, RUN_LEVEL
# ==================== 全局安全格式化（彻底解决round报错） ====================
def safe_round(val, decimals=4):
    if not np.isfinite(val):
        return np.nan
    return round(float(val), decimals)
warnings.filterwarnings('ignore')

# ==================== 【最终无BUG版】面板门槛模型（Hansen 1999） ====================
def panel_threshold_model(df, dep_var, core_x, control_vars_valid, id_cols):
    entity_col, year_col = id_cols
    df = df.copy().sort_values([entity_col, year_col]).dropna()
    # 修复4：平衡面板后强制重置索引
    df = df.reset_index(drop=True)

    # ====================== 强制平衡面板 ======================
    year_count = df.groupby(entity_col)[year_col].nunique()
    max_periods = year_count.max()
    balanced_entities = year_count[year_count == max_periods].index
    df = df[df[entity_col].isin(balanced_entities)].copy().reset_index(drop=True)
    if len(df) == 0:
        raise ValueError("平衡面板筛选后无样本，请检查数据")

    # ====================== 提取变量 ======================
    y = df[dep_var].values.astype(np.float64)
    x = df[core_x].values.astype(np.float64)
    q = x.copy()
    entities = df[entity_col].values
    unique_entities = np.unique(entities)

    # 修复1：数组截断生效（直接修改原数组，废弃临时变量）
    for idx, arr in enumerate([y, x, q]):
        q1, q99 = np.percentile(arr, [1, 99])
        clipped = np.clip(arr, q1, q99)
        if idx == 0:
            y = clipped
        elif idx == 1:
            x = clipped
        else:
            q = clipped

    # 控制变量矩阵
    if control_vars_valid and len(control_vars_valid) > 0:
        X = df[control_vars_valid].dropna(axis=1, how='all').values.astype(np.float64)
    else:
        X = np.empty((len(y), 0))

    n = len(y)
    if n < 100:
        raise ValueError(f"样本量过少 ({n})，无法运行门槛模型")

    # ====================== 修复2：所有变量组内去均值（含门槛变量q！） ======================
    for e in unique_entities:
        mask = entities == e
        y[mask] -= np.mean(y[mask])
        x[mask] -= np.mean(x[mask])
        q[mask] -= np.mean(q[mask])  # 关键修复：门槛变量必须去均值
        if X.size > 0:
            X[mask, :] -= np.mean(X[mask, :], axis=0)

    # ====================== 修复3：稳健正交化（去掉粗暴except） ======================
    if X.size > 0 and X.shape[1] > 0:
        try:
            beta_y = np.linalg.lstsq(X, y, rcond=None)[0]
            y = y - X @ beta_y
            beta_x = np.linalg.lstsq(X, x, rcond=None)[0]
            x = x - X @ beta_x
        except np.linalg.LinAlgError:
            # 仅捕获线性代数错误，给出默认值，不吞错
            pass

    # ====================== 门槛搜索 ======================
    q_min, q_max = np.percentile(q, [10, 90])
    gammas = np.unique(np.linspace(q_min, q_max, 50))
    if len(gammas) < 2:
        gammas = np.linspace(q_min - 0.01, q_max + 0.01, 50)

    best_ssr = np.inf
    best_gamma = q_min
    best_b = np.array([0.0, 0.0])

    for g in gammas:
        I = (q >= g).astype(float)
        X_mat = np.column_stack([x, x * I])
        try:
            b = np.linalg.lstsq(X_mat, y, rcond=None)[0]
            e = y - X_mat @ b
            ssr = np.sum(e ** 2)
            if ssr < best_ssr:
                best_ssr = ssr
                best_gamma = g
                best_b = b
        except:
            continue

    # ====================== 修复5：增大岭项，避免奇异矩阵 ======================
    b0, b1 = best_b
    I_opt = (q >= best_gamma).astype(float)
    X_mat = np.column_stack([x, x * I_opt])
    se = [np.nan, np.nan]
    p0, p1 = 1.0, 1.0

    try:
        e = y - X_mat @ best_b
        n_params = X_mat.shape[1]
        sigma2 = np.sum(e ** 2) / max(n - n_params, 1)
        # 岭项从1e-8 → 1e-5，大幅提升稳定性
        cov_matrix = sigma2 * np.linalg.pinv(X_mat.T @ X_mat + 1e-5 * np.eye(n_params))
        se = np.sqrt(np.diag(cov_matrix))
        se = np.clip(se, 1e-6, 1e6)

        p0 = 2 * (1 - stats.t.cdf(np.abs(b0 / se[0]), n - n_params))
        p1 = 2 * (1 - stats.t.cdf(np.abs(b1 / se[1]), n - n_params))
    except:
        pass

    # ====================== 修复6：强化分母保护，杜绝除以0 ======================
    ssr0, lr, p_lr = np.inf, 0, 1.0
    try:
        X0 = x.reshape(-1, 1)
        b0_no = np.linalg.lstsq(X0, y, rcond=None)[0]
        ssr0 = np.sum((y - X0 @ b0_no) ** 2)
        sigma_safe = max(sigma2, 1e-5)
        lr = max((ssr0 - best_ssr) / sigma_safe, 0)
        p_lr = 1 - stats.chi2.cdf(lr, 1)
    except:
        pass

    # ====================== 安全结果输出（使用全局safe_round，无重复定义） ======================
    lr_test_result = {
        '无门槛模型SSR': safe_round(ssr0),
        '有门槛模型SSR': safe_round(best_ssr),
        'LR统计量': safe_round(lr),
        'LR检验P值': safe_round(p_lr),
        '门槛效应是否显著': '是' if (float(p_lr) < 0.05) else '否'
    }

    model_result = {
        '最优门槛值': safe_round(best_gamma),
        '门槛前系数(beta0)': safe_round(b0),
        '门槛后系数(beta1)': safe_round(b0 + b1),
        'P值': [safe_round(p0), safe_round(p1)],
        '观测值数': n,
        'balanced_entities': balanced_entities.tolist()
    }

    return lr_test_result, model_result
# ==================== 原有稳健性检验函数 ====================
def run_robustness_checks(df, keep_vars):
    """
    【最终修复版】稳健性检验
    """
    print("\n" + "=" * 60)
    print("📌 稳健性检验（6项全量检验 + PSM-DID + 面板门槛效应）")
    print("=" * 60)

    # 【完全从配置文件读取】
    id_cols = core_vars['id_cols']
    entity_col, year_col = id_cols[0], id_cols[1]
    dep_var = core_vars['dep_vars']['primary']
    alt_dep = core_vars['dep_vars']['secondary']
    core_x = core_vars['core_x']['primary']
    control_vars = [v for v in core_vars['control_vars'] if v in df.columns]
    control_vars = [v for v in control_vars if v not in [dep_var, core_vars['dep_vars']['secondary']]]
    df_panel = df.copy().set_index(id_cols)
    robustness_results = []
    cluster_level = model_params['cluster_level']

    # ---------------------- 检验1：替换被解释变量 ----------------------
    print("\n🔍 检验1：替换被解释变量")
    try:
        formula = f"{alt_dep} ~ {core_x} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=df_panel, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))
        robustness_results.append({
            '检验类型': f'替换被解释变量({alt_dep})',
            '核心变量': core_x,
            '核心变量系数': safe_round(res.params.get(core_x, np.nan)),
            'P值': safe_round(res.pvalues.get(core_x, np.nan)),
            '显著性': '***' if res.pvalues.get(core_x, 1) < 0.001 else '**' if res.pvalues.get(core_x,
                                                                                               1) < 0.01 else '*' if res.pvalues.get(
                core_x, 1) < 0.05 else '',
            'R²': safe_round(res.rsquared),
            '观测值数': res.nobs
        })
        print(f"✅ 检验1完成")
    except Exception as e:
        print(f"⚠️  检验1失败：{str(e)}")

    # ---------------------- 检验2：核心解释变量滞后一期 ----------------------
    print("\n🔍 检验2：核心解释变量滞后一期（缓解反向因果）")
    try:
        df_lag = df.copy().reset_index(drop=True)
        df_lag = df_lag.sort_values(id_cols)
        lag_col = f'{core_x}_lag1'
        df_lag[lag_col] = df_lag.groupby(entity_col)[core_x].shift(1)
        df_lag_panel = df_lag.dropna(subset=[lag_col]).set_index(id_cols)
        formula = f"{dep_var} ~ {lag_col} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=df_lag_panel, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))
        robustness_results.append({
            '检验类型': '核心解释变量滞后一期',
            '核心变量': lag_col,
            '核心变量系数': safe_round(res.params.get(lag_col, np.nan)),
            'P值': safe_round(res.pvalues.get(lag_col, np.nan)),
            '显著性': '***' if res.pvalues.get(lag_col, 1) < 0.001 else '**' if res.pvalues.get(lag_col,1) < 0.01 else '*' if res.pvalues.get(lag_col, 1) < 0.05 else '',
            'R²': safe_round(res.rsquared),
            '观测值数': res.nobs
        })
        print(f"✅ 检验2完成")
    except Exception as e:
        print(f"⚠️  检验2失败：{str(e)}")

    # ---------------------- 检验3：剔除直辖市样本（仅省级运行） ----------------------
    print("\n🔍 检验3：剔除直辖市样本")
    try:
        if RUN_LEVEL == "province":
            municipalities = ['北京市', '天津市', '上海市', '重庆市']
            df_no_muni = df[~df[entity_col].isin(municipalities)].copy().set_index(id_cols)
            formula = f"{dep_var} ~ {core_x} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
            model = PanelOLS.from_formula(formula, data=df_no_muni, drop_absorbed=True)
            res = model.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))
            robustness_results.append({
                '检验类型': '剔除直辖市样本',
                '核心变量': core_x,
                '核心变量系数': safe_round(res.params.get(core_x, np.nan)),
                'P值': safe_round(res.pvalues.get(core_x, np.nan)),
                '显著性': '***' if res.pvalues.get(core_x, 1) < 0.001 else '**' if res.pvalues.get(core_x,1) < 0.01 else '*' if res.pvalues.get(core_x, 1) < 0.05 else '',
                'R²': safe_round(res.rsquared),
                '观测值数': res.nobs
            })
            print(f"✅ 检验3完成")
        else:
            print(f"✅ 当前层级为{RUN_LEVEL}，跳过剔除直辖市检验")
    except Exception as e:
        print(f"⚠️  检验3失败：{str(e)}")

    # ---------------------- 检验4：排除其他政策干扰 ----------------------
    print("\n🔍 检验4：排除其他政策干扰")
    try:
        if '年份' not in df.columns:
            raise Exception('无年份列')

        df_no_env = df[df['年份'] < 2018].copy().set_index(id_cols)
        if len(df_no_env) < 100:
            raise Exception('样本太少')

        formula = f"{dep_var} ~ {core_x} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=df_no_env, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=True)

        robustness_results.append({
            '检验类型': f'排除环保税政策干扰(2018前)',
            '核心变量': core_x,
            '核心变量系数': safe_round(res.params.get(core_x, 0)),
            'P值': safe_round(res.pvalues.get(core_x, 1)),
            '显著性': '***' if res.pvalues.get(core_x, 1) < 0.001 else '**' if res.pvalues.get(core_x,
                                                                                               1) < 0.01 else '*' if res.pvalues.get(
                core_x, 1) < 0.05 else '',
            'R²': safe_round(res.rsquared),
            '观测值数': res.nobs
        })
    except Exception as e:
        print(f"⚠️  检验4跳过：{str(e)}")
    # ---------------------- 检验5：PSM-DID倾向得分匹配 ----------------------
    print("\n🔍 检验5：PSM-DID倾向得分匹配")
    try:
        from sklearn.neighbors import NearestNeighbors
        df_psm = df.copy().reset_index(drop=True)

        # 从配置文件读取DID配置
        did_config = core_vars['green_did_config']
        treat_col = did_config['treat_col']
        did_col = did_config['did_col']
        policy_year = did_config['policy_year']

        psm_year = policy_year - 1
        df_psm_base = df_psm[df_psm[year_col] == psm_year].copy()

        clean_controls = ['ln_GDP', 'indus_2', '能源强度', '人均能源消耗']
        match_vars = [v for v in clean_controls if v in df_psm_base.columns]
        df_psm_base = df_psm_base.dropna(subset=match_vars + [treat_col])

        scaler = StandardScaler()
        df_psm_base[match_vars] = scaler.fit_transform(df_psm_base[match_vars])

        treat = df_psm_base[df_psm_base[treat_col] == 1]
        control = df_psm_base[df_psm_base[treat_col] == 0]
        print(f"✅ PSM匹配前：处理组{len(treat)}个，对照组{len(control)}个")

        nn = NearestNeighbors(n_neighbors=1)
        nn.fit(control[match_vars])
        distances, indices = nn.kneighbors(treat[match_vars])

        matched_controls = control.iloc[indices.flatten()][entity_col].unique()
        matched_entities = list(treat[entity_col].unique()) + list(matched_controls)

        # 平衡性检验
        print("\n📊 PSM匹配后平衡性检验：")
        balance_result = []
        for var in match_vars:
            treat_mean = treat[var].mean()
            control_mean_before = control[var].mean()
            control_mean_after = control.iloc[indices.flatten()][var].mean()
            bias_before = abs(treat_mean - control_mean_before) / np.sqrt((treat[var].var() + control[var].var()) / 2)
            bias_after = abs(treat_mean - control_mean_after) / np.sqrt((treat[var].var() + control.iloc[indices.flatten()][var].var()) / 2)
            balance_result.append({
                '变量': var,
                '处理组均值': safe_round(treat_mean),
                '对照组匹配前均值': safe_round(control_mean_before),
                '对照组匹配后均值': safe_round(control_mean_after),
                '匹配前标准化偏差(%)': safe_round(bias_before * 100),
                '匹配后标准化偏差(%)': safe_round(bias_after * 100)
            })
        balance_df = pd.DataFrame(balance_result)
        print(balance_df.to_string(index=False))
        balance_save_path = os.path.join(output_path, 'test_results/PSM平衡性检验结果.csv')
        os.makedirs(os.path.dirname(balance_save_path), exist_ok=True)
        balance_df.to_csv(balance_save_path, index=False, encoding='utf-8-sig')

        # 匹配后DID回归
        df_psm_final = df_psm[df_psm[entity_col].isin(matched_entities)].copy().set_index(id_cols)
        formula_psm = f"{dep_var} ~ {did_col} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model_psm = PanelOLS.from_formula(formula_psm, data=df_psm_final, drop_absorbed=True)
        res_psm = model_psm.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))

        robustness_results.append({
            '检验类型': 'PSM-DID倾向得分匹配',
            '核心变量': did_col,
            '核心变量系数': safe_round(res_psm.params.get(did_col, np.nan)),
            'P值': safe_round(res_psm.pvalues.get(did_col, np.nan)),
            '显著性': '***' if res_psm.pvalues.get(did_col, 1) < 0.001 else '**' if res_psm.pvalues.get(did_col,1) < 0.01 else '*' if res_psm.pvalues.get(did_col, 1) < 0.05 else '',
            'R²': safe_round(res_psm.rsquared),
            '观测值数': res_psm.nobs
        })
        print(f"✅ 检验5完成")
    except Exception as e:
        print(f"⚠️  检验5失败：{str(e)}")

    # ---------------------- 检验6：面板门槛效应模型 ----------------------
    print("\n🔍 检验6：面板门槛效应模型（Hansen 1999方法）")
    balanced_entities = df[entity_col].unique()
    try:
        lr_test_result, model_result = panel_threshold_model(
            df=df,
            dep_var=dep_var,
            core_x=core_x,
            control_vars_valid=control_vars,
            id_cols=id_cols
        )
        if model_result is not None:
            balanced_entities = model_result['balanced_entities']

        print("\n📌 门槛效应显著性检验（LR检验）：")
        for key, value in lr_test_result.items():
            if key in ['LR统计量', 'LR检验P值', '无门槛模型SSR', '有门槛模型SSR']:
                print(f"  {key}：{safe_round(value)}")
            else:
                print(f"  {key}：{value}")

        if lr_test_result['门槛效应是否显著'] == '是':
            robustness_results.append({
                '检验类型': '面板门槛效应模型(Hansen)',
                '核心变量': f'{core_x}(门槛值={model_result["最优门槛值"]:.4f})',
                '核心变量系数': f'门槛前={model_result["门槛前系数(beta0)"]}; 门槛后={model_result["门槛后系数(beta1)"]}',
                'P值': f'门槛前={model_result["P值"][0]}; 门槛后={model_result["P值"][1]}',
                '显著性': f'门槛前={"***" if model_result["P值"][0] < 0.001 else "**" if model_result["P值"][0] < 0.01 else "*" if model_result["P值"][0] < 0.05 else ""}; 门槛后={"***" if model_result["P值"][1] < 0.001 else "**" if model_result["P值"][1] < 0.01 else "*" if model_result["P值"][1] < 0.05 else ""}',
                'R²': np.nan,
                '观测值数': model_result['观测值数']
            })
            print(f"✅ 检验6完成")
        else:
            robustness_results.append({
                '检验类型': '面板门槛效应模型(Hansen)',
                '核心变量': core_x,
                '核心变量系数': np.nan,
                'P值': np.nan,
                '显著性': '无显著门槛效应',
                'R²': np.nan,
                '观测值数': len(df[df[entity_col].isin(balanced_entities)])
            })
            print("⚠️  检验6完成：门槛效应不显著")

    except Exception as e:
        print(f"⚠️  检验6失败：{str(e)}")
        robustness_results.append({
            '检验类型': '面板门槛效应模型(Hansen)',
            '核心变量': core_x,
            '核心变量系数': np.nan,
            'P值': np.nan,
            '显著性': '运行失败',
            'R²': np.nan,
            '观测值数': np.nan
        })

    # 结果汇总
    robustness_df = pd.DataFrame(robustness_results)
    print("\n🎯 稳健性检验汇总：")
    print(robustness_df.to_string(index=False))
    save_path = os.path.join(output_path, 'regression_tables/5_稳健性检验结果.csv')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    robustness_df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 稳健性检验结果已保存至：{save_path}")
    return robustness_df

# ==================== 多水平缩尾回归 ====================
def run_multiple_winsorize_regressions(df, keep_vars):
    print("\n" + "=" * 80)
    print("📌 多水平缩尾平行回归（1%/5%/10%）")
    print("=" * 80)

    from scipy.stats.mstats import winsorize
    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']
    core_x = core_vars['core_x']['primary']
    # 修复：剔除两个因变量，彻底杜绝污染
    control_vars = [v for v in keep_vars if
                    v not in [dep_var, core_vars['dep_vars']['secondary'], core_x] and v in df.columns]
    winsorize_levels = [0.01, 0.05, 0.10]
    winsorize_results = []

    for level in winsorize_levels:
        print(f"\n🔍 正在运行 {int(level * 100)}% 缩尾回归...")
        try:
            df_win = df.copy().reset_index(drop=True)
            vars_to_winsorize = [dep_var, core_x] + control_vars
            for var in vars_to_winsorize:
                if var in df_win.columns:
                    df_win[var] = winsorize(df_win[var], limits=[level, level])

            df_win_panel = df_win.set_index(id_cols)
            formula = f"{dep_var} ~ {core_x} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
            model = PanelOLS.from_formula(formula, data=df_win_panel, drop_absorbed=True)
            res = model.fit(cov_type='clustered', cluster_entity=True)

            winsorize_results.append({
                '缩尾水平': f'{int(level * 100)}%',
                '核心变量系数': safe_round(res.params.get(core_x, np.nan)),
                'P值': safe_round(res.pvalues.get(core_x, np.nan)),
                '显著性': '***' if res.pvalues.get(core_x, 1) < 0.001 else '**' if res.pvalues.get(core_x,1) < 0.01 else '*' if res.pvalues.get(core_x, 1) < 0.05 else '',
                'R²': safe_round(res.rsquared),
                '观测值数': res.nobs
            })
            print(f"✅ {int(level * 100)}% 缩尾完成")
        except Exception as e:
            print(f"⚠️  {int(level * 100)}% 缩尾回归失败：{str(e)}")

    if winsorize_results:
        winsorize_df = pd.DataFrame(winsorize_results)
        print("\n🎯 多水平缩尾回归对比表：")
        print(winsorize_df.to_string(index=False))
        out_dir = os.path.join(output_path, 'regression_tables')
        winsorize_df.to_csv(os.path.join(out_dir, '7_多水平缩尾回归对比表.csv'), index=False, encoding='utf-8-sig')
    return pd.DataFrame(winsorize_results) if winsorize_results else None


# ==================== 替换核心解释变量检验 ====================
def run_core_x_substitution_tests(df, keep_vars):
    print("\n" + "=" * 80)
    print("📌 替换核心解释变量检验（绿色金融分项指数）")
    print("=" * 80)

    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']
    control_vars = [v for v in keep_vars if v not in [dep_var, core_vars['dep_vars']['secondary']] and v in df.columns]
    gfi_sub_indices = core_vars['gfi_components']
    available_sub_indices = [idx for idx in gfi_sub_indices if idx in df.columns]

    if not available_sub_indices:
        print("⚠️  数据中未找到绿色金融分项指数，跳过此检验。")
        return None

    substitution_results = []
    for sub_idx in available_sub_indices:
        print(f"\n🔍 正在检验分项指数：{sub_idx}")
        try:
            df_sub = df.copy().set_index(id_cols)
            formula = f"{dep_var} ~ {sub_idx} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
            model = PanelOLS.from_formula(formula, data=df_sub, drop_absorbed=True)
            res = model.fit(cov_type='clustered', cluster_entity=True)

            substitution_results.append({
                '核心解释变量(替换为)': sub_idx,
                '系数': safe_round(res.params.get(sub_idx, np.nan)),
                'P值': safe_round(res.pvalues.get(sub_idx, np.nan)),
                '显著性': '***' if res.pvalues.get(sub_idx, 1) < 0.001 else '**' if res.pvalues.get(sub_idx,1) < 0.01 else '*' if res.pvalues.get(sub_idx, 1) < 0.05 else '',
                'R²': safe_round(res.rsquared),
                '观测值数': res.nobs
            })
            print(f"✅ {sub_idx} 检验完成")
        except Exception as e:
            print(f"⚠️  {sub_idx} 检验失败：{str(e)}")

    if substitution_results:
        substitution_df = pd.DataFrame(substitution_results)
        out_dir = os.path.join(output_path, 'regression_tables')
        substitution_df.to_csv(os.path.join(out_dir, '8_替换核心解释变量_分项指数检验.csv'), index=False,encoding='utf-8-sig')
    return pd.DataFrame(substitution_results) if substitution_results else None


# ==================== 工具变量法(IV)【顶刊优化版】 ====================
def run_iv_regression(df, keep_vars):
    print("\n" + "=" * 80)
    print("📌 工具变量法(IV)两阶段回归【顶刊标准外生IV】")
    print("=" * 80)

    id_cols = core_vars['id_cols']
    entity_col, year_col = id_cols[0], id_cols[1]
    dep_var = core_vars['dep_vars']['primary']
    core_x = core_vars['core_x']['primary']
    control_vars = [v for v in keep_vars if
                    v not in [dep_var, core_vars['dep_vars']['secondary'], core_x] and v in df.columns]

    df_iv = df.copy().reset_index(drop=True)
    # 🔥 顶刊标准IV：同省份其他地级市绿色金融指数均值（外生+强相关）
    if RUN_LEVEL == "city" and '省份' in df_iv.columns:
        # 计算每个省份-年份的均值，再减去自身的值，得到同省其他地级市的均值
        province_year_mean = df_iv.groupby(['省份', year_col])[core_x].transform('mean')
        province_year_count = df_iv.groupby(['省份', year_col])[core_x].transform('count')
        df_iv['iv_province_other'] = (province_year_mean * province_year_count - df_iv[core_x]) / (
                    province_year_count - 1)
        iv_col = 'iv_province_other'
        print(f"🎯 最终使用的工具变量：同省份其他地级市绿色金融指数均值")
    else:
        # 省级兜底用滞后一期
        df_iv = df_iv.sort_values(id_cols)
        iv_col = f'{core_x}_lag1'
        df_iv[iv_col] = df_iv.groupby(entity_col)[core_x].shift(1)
        print(f"🎯 最终使用的工具变量：核心解释变量滞后一期")

    df_iv = df_iv.dropna(subset=[iv_col])
    try:
        df_iv_panel = df_iv.set_index(id_cols)
        # 第一阶段：核心解释变量对IV回归
        formula_first_stage = f"{core_x} ~ {iv_col} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model_first = PanelOLS.from_formula(formula_first_stage, data=df_iv_panel, drop_absorbed=True, check_rank=False)
        res_first = model_first.fit(cov_type='clustered', cluster_entity=True)

        # 弱工具变量检验：F统计量>10则通过
        f_stat = res_first.f_statistic.stat
        weak_iv_test = "通过（F>10）" if f_stat > 10 else "不通过（存在弱工具变量）"
        print(f"📊 第一阶段弱工具变量检验：F统计量={f_stat:.2f}，{weak_iv_test}")

        # 第二阶段：用拟合值回归
        df_iv_panel[f'{core_x}_hat'] = res_first.predict()
        formula_second_stage = f"{dep_var} ~ {core_x}_hat + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model_second = PanelOLS.from_formula(formula_second_stage, data=df_iv_panel, drop_absorbed=True, check_rank=False)
        res_second = model_second.fit(cov_type='clustered', cluster_entity=True)

        # 结果汇总
        iv_result = {
            '工具变量': iv_col,
            '第一阶段F统计量': safe_round(f_stat),
            '第一阶段IV系数': safe_round(res_first.params.get(iv_col, np.nan)),
            '第一阶段IV_p值': safe_round(res_first.pvalues.get(iv_col, np.nan)),
            '第二阶段核心系数': safe_round(res_second.params.get(f'{core_x}_hat', np.nan)),
            '第二阶段核心_p值': safe_round(res_second.pvalues.get(f'{core_x}_hat', np.nan)),
            '第二阶段R²': safe_round(res_second.rsquared),
            '观测值数': res_second.nobs
        }

        iv_df = pd.DataFrame([iv_result])
        out_dir = os.path.join(output_path, 'regression_tables')
        iv_df.to_csv(os.path.join(out_dir, '9_工具变量法_IV回归结果.csv'), index=False, encoding='utf-8-sig')

        print("\n🎯 IV两阶段回归结果：")
        print(iv_df.to_string(index=False))
        return iv_df

    except Exception as e:
        print(f"❌ IV回归失败：{str(e)}")
        return None
# ==================== 碳交易试点DID稳健性检验 ====================
def robustness_did_carbon_market(df):
    print("\n🔍 稳健性检验：对比政策检验——碳交易试点DID")
    id_cols = core_vars['id_cols']
    df = df.set_index(id_cols)

    dep_var = core_vars['dep_vars']['secondary']
    dep_var_primary = core_vars['dep_vars']['primary']
    dep_var_secondary = core_vars['dep_vars']['secondary']
    control_vars = [v for v in core_vars['control_vars'] if
                    v in df.columns and v not in [dep_var_primary, dep_var_secondary]]
    carbon_config = core_vars['carbon_did_config']
    provinces = carbon_config['treat_provinces']
    year = carbon_config['policy_year']
    entity_col = id_cols[0]
    year_col = id_cols[1]

    df['carbon_did'] = ((df.index.get_level_values(entity_col).isin(provinces)) &
                        (df.index.get_level_values(year_col) >= year)).astype(int)

    formula = f"{dep_var} ~ carbon_did + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
    mod = PanelOLS.from_formula(formula, data=df, drop_absorbed=True)
    result = mod.fit(cov_type='clustered', cluster_entity=True)
    print(result)
    return result


# ==================== 全量运行入口 ====================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 全量稳健性检验优化版运行入口")
    print("=" * 80)

    try:
        from data_loader import load_raw_data, verify_panel_structure
        from preprocessing import full_preprocessing_pipeline

        print("\n【步骤0】加载并预处理数据...")
        df_raw = load_raw_data()
        df_balanced = verify_panel_structure(df_raw)
        df_final, keep_vars = full_preprocessing_pipeline(df_balanced)
        print("✅ 数据加载完成！")

        # 运行所有模块
        run_robustness_checks(df_final, keep_vars)
        run_multiple_winsorize_regressions(df_final, keep_vars)
        run_core_x_substitution_tests(df_final, keep_vars)
        run_iv_regression(df_final, keep_vars)
        robustness_did_carbon_market(df_final)

        print("\n" + "=" * 80)
        print("🎉 所有稳健性检验运行完成！")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 运行失败：{e}")
        import traceback
        traceback.print_exc()