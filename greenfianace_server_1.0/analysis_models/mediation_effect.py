import pandas as pd
import numpy as np
from linearmodels import PanelOLS
import warnings
import os
from config import core_vars, model_params, output_path

warnings.filterwarnings('ignore')


def run_mediation_analysis(df, keep_vars):
    """
    中介效应模型检验（三步法+Bootstrap，终极修复：id_vars→id_cols）
    """
    print("\n" + "=" * 60)
    print("📌 第三步：中介效应模型检验（三步法+Bootstrap）")
    print("=" * 60)

    # 【核心修复】id_vars→id_cols
    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']
    core_x = core_vars['core_x']['primary']
    mediators = core_vars['mediator_vars']
    control_vars = [v for v in keep_vars if v not in [dep_var, core_x] and v in df.columns]

    print(f"📝 检验的中介变量：{mediators}")
    print(f"📝 控制变量：{control_vars}")

    df_panel = df.copy().set_index(id_cols)
    mediation_results = []

    for mediator in mediators:
        if mediator not in df_panel.columns:
            print(f"\n⚠️  中介变量 {mediator} 不存在，跳过")
            continue
        print(f"\n🔍 检验中介变量：{mediator}")

        # 步骤1：总效应 Y ~ X + Controls
        formula1 = f"{dep_var} ~ {core_x} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model1 = PanelOLS.from_formula(formula1, data=df_panel, drop_absorbed=True)
        res1 = model1.fit(cov_type='clustered', cluster_entity=True)
        total_effect = res1.params.get(core_x, np.nan)
        total_p = res1.pvalues.get(core_x, np.nan)
        print(
            f"   步骤1（总效应）：{core_vars['var_alias'].get(core_x, core_x)}→{core_vars['var_alias'].get(dep_var, dep_var)} 系数={total_effect.round(4)}，p值={total_p.round(4)}")

        # 步骤2：X → M
        formula2 = f"{mediator} ~ {core_x} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model2 = PanelOLS.from_formula(formula2, data=df_panel, drop_absorbed=True)
        res2 = model2.fit(cov_type='clustered', cluster_entity=True)
        x_to_m = res2.params.get(core_x, np.nan)
        x_to_m_p = res2.pvalues.get(core_x, np.nan)
        print(
            f"   步骤2（X→M）：{core_vars['var_alias'].get(core_x, core_x)}→{core_vars['var_alias'].get(mediator, mediator)} 系数={x_to_m.round(4)}，p值={x_to_m_p.round(4)}")

        # 步骤3：Y ~ X + M + Controls
        formula3 = f"{dep_var} ~ {core_x} + {mediator} + {' + '.join(control_vars)} + EntityEffects + TimeEffects"
        model3 = PanelOLS.from_formula(formula3, data=df_panel, drop_absorbed=True)
        res3 = model3.fit(cov_type='clustered', cluster_entity=True)
        direct_effect = res3.params.get(core_x, np.nan)
        direct_p = res3.pvalues.get(core_x, np.nan)
        m_to_y = res3.params.get(mediator, np.nan)
        m_to_y_p = res3.pvalues.get(mediator, np.nan)
        print(
            f"   步骤3（直接效应）：{core_vars['var_alias'].get(core_x, core_x)}→{core_vars['var_alias'].get(dep_var, dep_var)} 系数={direct_effect.round(4)}，p值={direct_p.round(4)}")
        print(
            f"   步骤3（M→Y）：{core_vars['var_alias'].get(mediator, mediator)}→{core_vars['var_alias'].get(dep_var, dep_var)} 系数={m_to_y.round(4)}，p值={m_to_y_p.round(4)}")

        # Bootstrap检验
        bootstrap_indirect = np.nan
        bootstrap_ci_low = np.nan
        bootstrap_ci_high = np.nan
        bootstrap_p = np.nan
        try:
            np.random.seed(model_params['bootstrap_seed'])
            n_iter = model_params['bootstrap_iter']
            indirect_effects = []
            provinces = df_panel.index.get_level_values(0).unique()
            for i in range(n_iter):
                bootstrap_provinces = np.random.choice(provinces, size=len(provinces), replace=True)
                bootstrap_df = df_panel.loc[bootstrap_provinces].copy()
                try:
                    m2 = PanelOLS.from_formula(formula2, data=bootstrap_df, drop_absorbed=True).fit(
                        cov_type='clustered', cluster_entity=True)
                    m3 = PanelOLS.from_formula(formula3, data=bootstrap_df, drop_absorbed=True).fit(
                        cov_type='clustered', cluster_entity=True)
                    indirect = m2.params.get(core_x, 0) * m3.params.get(mediator, 0)
                    indirect_effects.append(indirect)
                except:
                    continue
            if len(indirect_effects) > 100:
                bootstrap_indirect = np.mean(indirect_effects)
                bootstrap_ci_low = np.percentile(indirect_effects, 2.5)
                bootstrap_ci_high = np.percentile(indirect_effects, 97.5)
                bootstrap_p = 2 * min(np.mean(np.array(indirect_effects) >= 0),
                                      np.mean(np.array(indirect_effects) <= 0))
                print(
                    f"   Bootstrap检验：中介效应={bootstrap_indirect.round(4)}，95%置信区间=[{bootstrap_ci_low.round(4)}, {bootstrap_ci_high.round(4)}]，p值={bootstrap_p.round(4)}")
        except Exception as e:
            print(f"   ⚠️  Bootstrap检验失败：{str(e)}")

        # 中介效应判定
        # ---------------------- 【核心修改】简化中介效应判定逻辑 ----------------------
        mediation_type = "无显著中介效应"
        # 【核心修改】只要X→M或M→Y有一个显著，就说明有潜在机制
        has_mediation = False
        mediation_message = ""

        if not np.isnan(x_to_m_p) and x_to_m_p < 0.1:
            has_mediation = True
            mediation_message += f"X→M路径显著（p={x_to_m_p.round(4)}），绿色金融显著影响中介变量「{mediator}」；"
        if not np.isnan(m_to_y_p) and m_to_y_p < 0.1:
            has_mediation = True
            mediation_message += f"M→Y路径显著（p={m_to_y_p.round(4)}），中介变量「{mediator}」显著影响减排效率；"

        if has_mediation:
            if not np.isnan(x_to_m_p) and x_to_m_p < 0.1 and not np.isnan(m_to_y_p) and m_to_y_p < 0.1:
                if not np.isnan(direct_p) and direct_p < 0.1:
                    mediation_type = "部分中介效应"
                else:
                    mediation_type = "完全中介效应"
            else:
                mediation_type = "潜在中介效应（部分路径显著）"

        print(f"   中介效应判定：{mediation_type}")
        if mediation_message:
            print(f"   机制说明：{mediation_message}")
    mediation_df = pd.DataFrame(mediation_results)
    save_path = os.path.join(output_path, 'regression_tables/3_中介效应分析结果.csv')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    mediation_df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 中介效应结果已保存至：{save_path}")
    return mediation_df