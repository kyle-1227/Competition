import pandas as pd
import numpy as np
from linearmodels import PanelOLS
import warnings

warnings.filterwarnings('ignore')


def run_standard_did(df, keep_vars):
    from config import core_vars
    dep_var = '减排效率'
    treat_provinces = core_vars['did_config']['treat_provinces']
    policy_year = core_vars['did_config']['policy_year']

    print("=" * 60)
    print("📌 第二步：渐进DID双重差分模型（因果识别）")
    print("=" * 60)

    df_panel_base = df.copy()
    df_panel_base['年份'] = pd.to_numeric(df_panel_base['年份'], errors='coerce').astype(int)

    try:
        base_year = policy_year - 1
        df_base = df_panel_base[df_panel_base['年份'] == base_year].copy()
        treat_gdp_median = df_base[df_base['省份'].isin(treat_provinces)]['人均地区生产总值'].median()
        control_candidates = df_base[
            (df_base['人均地区生产总值'] >= treat_gdp_median * 0.7) &
            (df_base['人均地区生产总值'] <= treat_gdp_median * 1.3) &
            (~df_base['省份'].isin(treat_provinces))
            ]['省份'].unique()
        keep_provinces = list(treat_provinces) + list(control_candidates)
        df_panel_base = df_panel_base[df_panel_base['省份'].isin(keep_provinces)].copy()
        print(f"✅ 已缩小对照组范围：保留试点省份+{len(control_candidates)}个经济水平相近的对照省份")
    except Exception as e:
        print(f"⚠️  缩小对照组范围失败，使用全样本：{str(e)}")

    print(f"✅ DID数据校验完成：处理组省份={treat_provinces}，政策年份={policy_year}")

    # ---------------------- 标准DID ----------------------
    print("\n" + "-" * 60)
    print("📌 基准回归：标准DID（论文通用版）")
    print("-" * 60)

    df_panel = df_panel_base.set_index(['省份', '年份'])
    controls = ['ln_pop', '能源强度', '人均能源消耗']
    formula = f"{dep_var} ~ DID + {' + '.join(controls)} + EntityEffects + TimeEffects"

    try:
        model = PanelOLS.from_formula(formula, data=df_panel, drop_absorbed=True)
        res = model.fit(cov_type="robust")
        print("\n🎯 标准DID回归结果：")
        print(res.summary)

        coef = res.params.get('DID', np.nan)
        pval = res.pvalues.get('DID', np.nan)
        if np.isfinite(coef):
            if pval < 0.05:
                print(f"✅ DID政策效应显著：系数={coef:.4f}, p={pval:.4f}")
            else:
                print(f"⚠️ DID不显著：系数={coef:.4f}, p={pval:.4f}")
    except Exception as e:
        print(f"❌ DID报错：{str(e)}")

    # ---------------------- 动态DID ----------------------
    print("\n" + "-" * 60)
    print("📌 动态DID平行趋势检验")
    print("-" * 60)

    df_dy = df_panel_base.copy()
    df_dy['rel_year'] = df_dy['年份'] - policy_year
    df_dy = df_dy[(df_dy['rel_year'] >= -4) & (df_dy['rel_year'] <= 4)].copy()

    dummies = []
    for y in range(-4, 5):
        if y == -1:
            continue
        col = f"did_{y}"
        df_dy[col] = ((df_dy['Treat'] == 1) & (df_dy['rel_year'] == y)).astype(int)
        dummies.append(col)

    controls = ['ln_pop', '能源强度', '人均能源消耗']
    formula_dynamic = f"{dep_var} ~ {' + '.join(dummies + controls)} + EntityEffects + TimeEffects"

    try:
        model_dy = PanelOLS.from_formula(formula_dynamic, data=df_dy.set_index(['省份', '年份']), drop_absorbed=False)
        res_dy = model_dy.fit(cov_type="robust")
        print("\n🎯 动态DID平行趋势检验结果：")
        print(res_dy.summary)
    except Exception as e:
        print(f"❌ 动态DID报错：{str(e)}")

    print("\n✅ DID模块全部运行完成！")