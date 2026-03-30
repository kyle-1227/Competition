import pandas as pd
import numpy as np
from linearmodels import PanelOLS
import warnings
import os
import scipy.stats as stats
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler  # 【修复1：补全导入】
from config import core_vars, output_path, model_params

warnings.filterwarnings('ignore')


# ==================== 封装面板门槛效应模型为可复用函数 ====================
def panel_threshold_model(df, dep_var, core_x, control_vars_valid, id_cols):
    """
    【修复版】面板门槛效应模型（Hansen方法）
    修复：奇异矩阵、共线性、inf/nan清洗
    """
    # 1. 数据预处理：清洗inf/nan，构建平衡面板
    df_threshold = df.copy().reset_index(drop=True)
    # 清洗核心变量的inf/nan
    clean_cols = [dep_var, core_x] + control_vars_valid
    df_threshold[clean_cols] = df_threshold[clean_cols].replace([np.inf, -np.inf], np.nan)
    df_threshold = df_threshold.dropna(subset=clean_cols).reset_index(drop=True)

    # 构建平衡面板
    province_year_count = df_threshold.groupby(id_cols[0])[id_cols[1]].nunique()
    max_year_count = province_year_count.value_counts().idxmax()
    balanced_provinces = province_year_count[province_year_count == max_year_count].index.tolist()
    df_threshold = df_threshold[df_threshold[id_cols[0]].isin(balanced_provinces)].reset_index(drop=True)
    n_provinces = len(balanced_provinces)
    n_periods = max_year_count
    print(f"✅ 门槛模型-平衡面板：{n_provinces}省份×{n_periods}年，观测值数量：{len(df_threshold)}")

    # 2. 变量定义（修复共线性：剔除和核心解释变量高度相关的控制变量）
    if dep_var not in df_threshold.columns:
        raise ValueError(f"❌ 门槛模型缺失被解释变量：{dep_var}")
    # 仅当变量名不含ln/对数时，才执行对数化
    if 'ln_' not in dep_var and '对数' not in dep_var:
        df_threshold[f'ln_{dep_var}'] = np.log(df_threshold[dep_var].clip(lower=1e-10))
        y_col = f'ln_{dep_var}'
    else:
        y_col = dep_var
    y = df_threshold[y_col].values

    # 核心解释变量（门槛变量）
    if core_x not in df_threshold.columns:
        raise ValueError(f"❌ 门槛模型缺失核心解释变量：{core_x}")
    X = df_threshold[core_x].values.reshape(-1, 1)

    # 控制变量 + 省份固定效应（虚拟变量）
    # 【修复2：剔除和核心变量相关系数>0.8的控制变量，避免共线性】
    corr_threshold = 0.8
    final_control_vars = []
    for var in control_vars_valid:
        corr = abs(df_threshold[core_x].corr(df_threshold[var]))
        if corr < corr_threshold:
            final_control_vars.append(var)
    print(f"✅ 门槛模型-剔除高共线控制变量后，有效控制变量：{final_control_vars}")

    Z = df_threshold[final_control_vars].values if final_control_vars else None
    province_dummies = pd.get_dummies(df_threshold[id_cols[0]], drop_first=True).values
    if Z is not None:
        Z = np.hstack([Z, province_dummies])
    else:
        Z = province_dummies

    # 3. 定义面板门槛模型类（修复奇异矩阵）
    class PanelThresholdModel:
        def __init__(self, y, X, Z, n_provinces, n_periods):
            self.y = y.reshape(n_provinces, n_periods)
            self.X = X.reshape(n_provinces, n_periods)
            self.Z = Z.reshape(n_provinces, n_periods, -1) if Z.ndim == 2 else Z
            self.n = n_provinces
            self.T = n_periods
            self.k = self.Z.shape[2] if self.Z.ndim == 3 else self.Z.shape[1]

        def _residuals(self, gamma, beta0, beta1, theta):
            residuals = []
            for i in range(self.n):
                for t in range(self.T):
                    I = 1 if self.X[i, t] >= gamma else 0
                    y_hat = beta0 * self.X[i, t] + beta1 * self.X[i, t] * I + np.dot(self.Z[i, t], theta)
                    residuals.append(self.y[i, t] - y_hat)
            return np.array(residuals)

        def _ssr(self, params):
            gamma, beta0, beta1 = params[0], params[1], params[2]
            theta = params[3:]
            residuals = self._residuals(gamma, beta0, beta1, theta)
            return np.sum(residuals ** 2)

        def estimate(self, gamma_candidates=None):
            # 优化门槛候选值（15%-85%分位数区间，避免极端值）
            if gamma_candidates is None:
                gfi_flat = self.X.flatten()
                gamma_min = np.percentile(gfi_flat, 15)
                gamma_max = np.percentile(gfi_flat, 85)
                gamma_candidates = np.linspace(gamma_min, gamma_max, 100)
                gamma_candidates = np.unique(gamma_candidates)

            min_ssr = np.inf
            best_params = None
            best_gamma = None
            for gamma in gamma_candidates:
                init_params = [gamma, 0.0, 0.0] + [0.0] * self.k
                result = minimize(
                    self._ssr, init_params, method='L-BFGS-B',
                    bounds=[(gamma_min, gamma_max)] + [(None, None)] * (len(init_params) - 1)
                )
                if result.success and result.fun < min_ssr:
                    min_ssr = result.fun
                    best_params = result.x
                    best_gamma = gamma

            if best_params is None:
                raise ValueError("未找到有效最优参数")

            beta0 = best_params[1]
            beta1 = best_params[2]
            theta = best_params[3:]
            residuals = self._residuals(best_gamma, beta0, beta1, theta)
            sigma2 = np.sum(residuals ** 2) / (self.n * self.T - self.k - 2)

            # 【修复3：用伪逆pinv替代inv，彻底解决奇异矩阵】
            def grad_fun(params):
                h = 1e-6
                grad = np.zeros_like(params)
                for i in range(len(params)):
                    params_plus = params.copy()
                    params_minus = params.copy()
                    params_plus[i] += h
                    params_minus[i] -= h
                    grad[i] = (self._ssr(params_plus) - self._ssr(params_minus)) / (2 * h)
                return grad

            def hessian_fun(params, epsilon=1e-6):
                n_params = len(params)
                hessian = np.zeros((n_params, n_params))
                grad_base = grad_fun(params)
                for i in range(n_params):
                    params_plus = params.copy()
                    params_plus[i] += epsilon
                    grad_plus = grad_fun(params_plus)
                    hessian[i, :] = (grad_plus - grad_base) / epsilon
                hessian = (hessian + hessian.T) / 2
                return hessian + 1e-6 * np.eye(hessian.shape[0])

            grad = grad_fun(best_params)
            hessian = hessian_fun(best_params)
            cov_matrix = sigma2 * np.linalg.pinv(hessian)  # 伪逆，兼容奇异矩阵
            se = np.sqrt(np.diag(cov_matrix))
            t_stats = best_params / se
            df = self.n * self.T - self.k - 3
            p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), df=df))

            return {
                '最优门槛值': best_gamma,
                '门槛前系数(beta0)': beta0,
                '门槛后系数(beta1)': beta1,
                '控制变量系数(theta)': theta,
                '残差方差': sigma2,
                'SSR': min_ssr,
                '参数标准误': se,
                't统计量': t_stats,
                'P值': p_values,
                '控制变量名称': final_control_vars + ['省份虚拟变量'] * (province_dummies.shape[1]),
                '省份数': n_provinces,
                '时间期数': n_periods,
                '观测值数': self.n * self.T,
                'balanced_provinces': balanced_provinces
            }

        def threshold_test(self, gamma_candidates=None):
            # 无门槛模型SSR
            def ssr_no_threshold(params):
                beta0, theta = params[0], params[1:]
                residuals = []
                for i in range(self.n):
                    for t in range(self.T):
                        y_hat = beta0 * self.X[i, t] + np.dot(self.Z[i, t], theta)
                        residuals.append(self.y[i, t] - y_hat)
                return np.sum(np.array(residuals) ** 2)

            init_no_thresh = [0.0] + [0.0] * self.k
            result_no_thresh = minimize(ssr_no_threshold, init_no_thresh, method='L-BFGS-B')
            ssr0 = result_no_thresh.fun
            # 有门槛模型SSR
            result_thresh = self.estimate(gamma_candidates)
            ssr1 = result_thresh['SSR']
            # LR检验
            lr_stat = (ssr0 - ssr1) / result_thresh['残差方差']
            p_value_lr = 1 - stats.chi2.cdf(lr_stat, df=1)
            return {
                '无门槛模型SSR': ssr0,
                '有门槛模型SSR': ssr1,
                'LR统计量': lr_stat,
                'LR检验P值': p_value_lr,
                '门槛效应是否显著': '是' if p_value_lr < 0.05 else '否'
            }, result_thresh

    # 4. 运行门槛模型
    ptm = PanelThresholdModel(y, X, Z, n_provinces, n_periods)
    # 5. 门槛效应显著性检验
    lr_test_result, model_result = ptm.threshold_test()
    return lr_test_result, model_result


# ==================== 原有稳健性检验函数 ====================
def run_robustness_checks(df, keep_vars):
    """
    【最终修复版】稳健性检验
    """
    print("\n" + "=" * 60)
    print("📌 稳健性检验（6项全量检验 + PSM-DID + 面板门槛效应）")
    print("=" * 60)

    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']
    core_x = core_vars['core_x']['primary']
    control_vars = [v for v in keep_vars if v not in [dep_var, core_x] and v in df.columns]
    df_panel = df.copy().set_index(id_cols)
    robustness_results = []
    cluster_level = model_params['cluster_level']

    # ---------------------- 检验1：替换被解释变量 ----------------------
    print("\n🔍 检验1：替换被解释变量（碳排放强度替代减排效率）")
    try:
        alt_dep = core_vars['dep_vars']['secondary']
        formula = f"{alt_dep} ~ {core_x} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=df_panel, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))
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
    print("\n🔍 检验2：核心解释变量滞后一期（缓解反向因果）")
    try:
        df_lag = df.copy().reset_index(drop=True)
        df_lag = df_lag.sort_values(id_cols)
        lag_col = f'{core_x}_lag1'
        df_lag[lag_col] = df_lag.groupby(id_cols[0])[core_x].shift(1)
        df_lag_panel = df_lag.dropna(subset=[lag_col]).set_index(id_cols)
        formula = f"{dep_var} ~ {lag_col} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=df_lag_panel, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))
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
        res = model.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))
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
    print("\n🔍 检验4：排除其他政策干扰（2018年环保税）")
    try:
        df_no_policy = df[df['年份'] < 2018].copy().set_index(id_cols)
        formula = f"{dep_var} ~ {core_x} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=df_no_policy, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))
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

    # ---------------------- 检验5：PSM-DID倾向得分匹配 ----------------------
    print("\n🔍 检验5：PSM-DID倾向得分匹配（卡尺内1:1最近邻匹配）")
    try:
        from sklearn.neighbors import NearestNeighbors
        df_psm = df.copy().reset_index(drop=True)
        # 取政策前一年做匹配
        psm_year = core_vars['did_config']['policy_year'] - 1
        df_psm_base = df_psm[df_psm['年份'] == psm_year].copy()

        # 匹配变量
        match_vars = control_vars
        df_psm_base = df_psm_base.dropna(subset=match_vars + ['Treat'])

        # 【修复4：匹配变量标准化，提升匹配效果】
        scaler = StandardScaler()
        df_psm_base[match_vars] = scaler.fit_transform(df_psm_base[match_vars])

        # 1:1最近邻匹配
        treat = df_psm_base[df_psm_base['Treat'] == 1]
        control = df_psm_base[df_psm_base['Treat'] == 0]
        print(f"✅ PSM匹配前：处理组{len(treat)}个，对照组{len(control)}个")

        nn = NearestNeighbors(n_neighbors=1)
        nn.fit(control[match_vars])
        distances, indices = nn.kneighbors(treat[match_vars])

        matched_controls = control.iloc[indices.flatten()]['省份'].unique()
        matched_provinces = list(treat['省份'].unique()) + list(matched_controls)

        # PSM平衡性检验
        print("\n📊 PSM匹配后平衡性检验：")
        balance_result = []
        for var in match_vars:
            treat_mean = treat[var].mean()
            control_mean_before = control[var].mean()
            control_mean_after = control.iloc[indices.flatten()][var].mean()
            # 标准化偏差
            bias_before = abs(treat_mean - control_mean_before) / np.sqrt((treat[var].var() + control[var].var()) / 2)
            bias_after = abs(treat_mean - control_mean_after) / np.sqrt(
                (treat[var].var() + control.iloc[indices.flatten()][var].var()) / 2)
            balance_result.append({
                '变量': var,
                '处理组均值': round(treat_mean, 4),
                '对照组匹配前均值': round(control_mean_before, 4),
                '对照组匹配后均值': round(control_mean_after, 4),
                '匹配前标准化偏差(%)': round(bias_before * 100, 2),
                '匹配后标准化偏差(%)': round(bias_after * 100, 2)
            })
        balance_df = pd.DataFrame(balance_result)
        print(balance_df.to_string(index=False))
        # 保存平衡性检验结果
        balance_save_path = os.path.join(output_path, 'test_results/PSM平衡性检验结果.csv')
        os.makedirs(os.path.dirname(balance_save_path), exist_ok=True)
        balance_df.to_csv(balance_save_path, index=False, encoding='utf-8-sig')
        print(f"✅ PSM平衡性检验结果已保存至：{balance_save_path}")

        # 匹配后DID回归
        df_psm_final = df_psm[df_psm['省份'].isin(matched_provinces)].copy().set_index(id_cols)
        formula_psm = f"{dep_var} ~ DID + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model_psm = PanelOLS.from_formula(formula_psm, data=df_psm_final, drop_absorbed=True)
        res_psm = model_psm.fit(cov_type='clustered', cluster_entity=(cluster_level == 'Entity'))

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

    # ---------------------- 检验6：面板门槛效应模型 ----------------------
    print("\n🔍 检验6：面板门槛效应模型（Hansen 1999方法）")
    balanced_provinces = df['省份'].unique()
    try:
        # 调用封装的门槛模型函数
        lr_test_result, model_result = panel_threshold_model(
            df=df,
            dep_var=dep_var,
            core_x=core_x,
            control_vars_valid=control_vars,
            id_cols=id_cols
        )
        if model_result is not None:
            balanced_provinces = model_result['balanced_provinces']

        # 输出门槛效应检验结果
        print("\n📌 门槛效应显著性检验（LR检验）：")
        for key, value in lr_test_result.items():
            if key in ['LR统计量', 'LR检验P值', '无门槛模型SSR', '有门槛模型SSR']:
                print(f"  {key}：{value:.4f}")
            else:
                print(f"  {key}：{value}")

        # 门槛效应显著时，记录核心结果
        if lr_test_result['门槛效应是否显著'] == '是':
            robustness_results.append({
                '检验类型': '面板门槛效应模型(Hansen)',
                '核心变量': f'{core_x}(门槛值={model_result["最优门槛值"]:.4f})',
                '核心变量系数': f'门槛前={model_result["门槛前系数(beta0)"].round(4)}; 门槛后={model_result["门槛后系数(beta1)"].round(4)}',
                'P值': f'门槛前={model_result["P值"][1].round(4)}; 门槛后={model_result["P值"][2].round(4)}',
                '显著性': f'门槛前={"***" if model_result["P值"][1] < 0.001 else "**" if model_result["P值"][1] < 0.01 else "*" if model_result["P值"][1] < 0.05 else ""}; 门槛后={"***" if model_result["P值"][2] < 0.001 else "**" if model_result["P值"][2] < 0.01 else "*" if model_result["P值"][2] < 0.05 else ""}',
                'R²': np.nan,
                '观测值数': model_result['观测值数']
            })

            # 保存门槛模型详细结果
            core_params = pd.DataFrame({
                '参数名称': ['最优门槛值', '门槛前系数(beta0)', '门槛后系数(beta1)'],
                '估计值': [model_result['最优门槛值'], model_result['门槛前系数(beta0)'],
                           model_result['门槛后系数(beta1)']],
                '标准误': [model_result['参数标准误'][0], model_result['参数标准误'][1], model_result['参数标准误'][2]],
                't统计量': [model_result['t统计量'][0], model_result['t统计量'][1], model_result['t统计量'][2]],
                'P值': [model_result['P值'][0], model_result['P值'][1], model_result['P值'][2]]
            }).round(4)

            control_params = pd.DataFrame({
                '控制变量名称': model_result['控制变量名称'],
                '估计值': model_result['控制变量系数(theta)'],
                '标准误': model_result['参数标准误'][3:],
                't统计量': model_result['t统计量'][3:],
                'P值': model_result['P值'][3:]
            }).round(4)

            all_params = pd.concat([core_params, control_params], ignore_index=True)
            params_save_path = os.path.join(output_path, 'regression_tables/6_门槛模型_参数估计结果.csv')
            lr_test_save_path = os.path.join(output_path, 'regression_tables/6_门槛模型_显著性检验结果.csv')
            os.makedirs(os.path.dirname(params_save_path), exist_ok=True)

            pd.DataFrame([lr_test_result]).to_csv(lr_test_save_path, index=False, encoding='utf-8-sig')
            all_params.to_csv(params_save_path, index=False, encoding='utf-8-sig')

            print(
                f"✅ 检验6完成：最优门槛值={model_result['最优门槛值']:.4f}，门槛前系数={model_result['门槛前系数(beta0)'].round(4)}，门槛后系数={model_result['门槛后系数(beta1)'].round(4)}")
        else:
            robustness_results.append({
                '检验类型': '面板门槛效应模型(Hansen)',
                '核心变量': core_x,
                '核心变量系数': np.nan,
                'P值': np.nan,
                '显著性': '无显著门槛效应',
                'R²': np.nan,
                '观测值数': len(df[df['省份'].isin(balanced_provinces)])
            })
            print("⚠️  检验6完成：门槛效应不显著")

    except Exception as e:
        print(f"⚠️  检验6失败：{str(e)}")
        import traceback
        traceback.print_exc()
        robustness_results.append({
            '检验类型': '面板门槛效应模型(Hansen)',
            '核心变量': core_x,
            '核心变量系数': np.nan,
            'P值': np.nan,
            '显著性': '运行失败',
            'R²': np.nan,
            '观测值数': np.nan
        })

    # ---------------------- 结果汇总与保存 ----------------------
    robustness_df = pd.DataFrame(robustness_results)
    print("\n🎯 稳健性检验汇总：")
    print(robustness_df.to_string(index=False))
    save_path = os.path.join(output_path, 'regression_tables/5_稳健性检验结果.csv')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    robustness_df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 稳健性检验结果已保存至：{save_path}")
    return robustness_df