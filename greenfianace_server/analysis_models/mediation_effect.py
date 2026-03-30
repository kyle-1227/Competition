import pandas as pd
import numpy as np
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler
import warnings
import os
import random
from scipy.stats import norm
from config import core_vars, output_path

np.random.seed(42)
random.seed(42)
warnings.filterwarnings('ignore')

def run_mediation_analysis(df, keep_vars):
    print("\n" + "=" * 70)
    print("📌 中介效应模型（完全匹配你的表头 · 学术优化版）")
    print("=" * 70)

    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']
    core_x = core_vars['core_x']['primary']

    df_med = df.copy().reset_index(drop=True)

    # ==============================
    # 以下完全使用你的真实列名
    # ==============================

    # 1. 能源利用效率（单要素/全要素通用）
    df_med["能源利用效率"] = df_med["地区生产总值"] / df_med["能源消费总量"].clip(lower=1e-8)

    # 2. 能源结构清洁化（电力+天然气 / 总能耗）→ 文献标准！
    df_med["能源结构清洁化"] = (df_med["电力消费量"] + df_med["天然气消费量"]) / df_med["能源消费总量"].clip(lower=1e-8)

    # 3. 产业结构高级化
    df_med["产业结构高级化"] = df_med["第三产业增加值"] / df_med["第二产业增加值"].clip(lower=1e-8)

    print("✅ 能源利用效率 生成完成")
    print("✅ 能源结构清洁化 生成完成")
    print("✅ 产业结构高级化 生成完成")

    mediators = ["能源利用效率", "能源结构清洁化", "产业结构高级化"]
    print(f"\n📝 检验中介变量：{mediators}")

    control_vars = [v for v in keep_vars if v not in [dep_var, core_x] + mediators and v in df_med.columns]
    df_clean = df_med.dropna(subset=[core_x, dep_var] + control_vars + mediators).copy()
    print(f"✅ 有效样本量：{len(df_clean)}")

    scaler = StandardScaler()
    df_clean[mediators] = scaler.fit_transform(df_clean[mediators])

    # 固定效应
    province_dummies = pd.get_dummies(df_clean['省份'], drop_first=True, prefix='prov')
    year_dummies = pd.get_dummies(df_clean['年份'], drop_first=True, prefix='year')
    df_clean = pd.concat([df_clean, province_dummies, year_dummies], axis=1)
    fe_cols = list(province_dummies.columns) + list(year_dummies.columns)

    def run_reg(df, y_col, x_col, med_list, controls, fe_list):
        all_controls = controls + fe_list
        control_str = ' + '.join(all_controls) if all_controls else '1'
        med_str = ' + '.join(med_list)

        total = sm.OLS.from_formula(f"{y_col} ~ {x_col} + {control_str}", data=df).fit(cov_type='HC3')
        med_res = {}
        for med in med_list:
            med_res[med] = sm.OLS.from_formula(f"{med} ~ {x_col} + {control_str}", data=df).fit(cov_type='HC3')
        direct = sm.OLS.from_formula(f"{y_col} ~ {x_col} + {med_str} + {control_str}", data=df).fit(cov_type='HC3')
        return total, med_res, direct

    def bootstrap_test(df, x_col, med_list, y_col, controls, fe_list, n_iter=1000):
        effects = {m: [] for m in med_list}
        n_samples = len(df)
        for _ in range(n_iter):
            idx = random.choices(range(n_samples), k=n_samples)
            d = df.iloc[idx].copy()
            try:
                ctrls = controls + fe_list
                cstr = " + ".join(ctrls) if ctrls else "1"
                a = {m: sm.OLS.from_formula(f"{m} ~ {x_col} + {cstr}", data=d).fit(disp=0).params[x_col] for m in med_list}
                y_reg = sm.OLS.from_formula(f"{y_col} ~ {x_col} + {'+'.join(med_list)} + {cstr}", data=d).fit(disp=0)
                b = {m: y_reg.params[m] for m in med_list}
                for m in med_list:
                    effects[m].append(a[m] * b[m])
            except:
                continue
        res = {}
        for m in med_list:
            e = np.array(effects[m])
            if len(e) < 200:
                res[m] = (np.nan, np.nan, np.nan)
            else:
                ci = np.percentile(e, [2.5, 97.5])
                p = 2 * min(np.mean(e <= 0), np.mean(e >= 0))
                res[m] = (ci, p, np.mean(e))
        return res

    total_res, med_res_dict, direct_res = run_reg(df_clean, dep_var, core_x, mediators, control_vars, fe_cols)
    boot_res = bootstrap_test(df_clean, core_x, mediators, dep_var, control_vars, fe_cols)

    total = total_res.params[core_x]
    total_p = total_res.pvalues[core_x]
    direct = direct_res.params[core_x]
    direct_p = direct_res.pvalues[core_x]

    print(f"\n🎯 总效应：{total:.4f} (p={total_p:.4f})")
    print(f"🎯 直接效应：{direct:.4f} (p={direct_p:.4f})")

    output = []
    for med in mediators:
        a = med_res_dict[med].params[core_x]
        a_p = med_res_dict[med].pvalues[core_x]
        b = direct_res.params[med]
        b_p = direct_res.pvalues[med]
        ab = a * b
        ratio = (ab / total) * 100 if abs(total) > 1e-8 else np.nan
        ci, p, mean_ab = boot_res[med]
        sig = "✅ 显著" if p < 0.05 and not np.isnan(p) and ci[0] * ci[1] > 0 else "❌ 不显著"

        print(f"\n🔍 中介：{med}")
        print(f"   a={a:.4f}({a_p:.3f}) | b={b:.4f}({b_p:.3f})")
        print(f"   中介效应={ab:.4f} | 占比={ratio:.2f}% | Bootstrap p={p:.3f} | {sig}")

        output.append({
            "中介变量": med,
            "总效应": round(total,4),
            "直接效应": round(direct,4),
            "a": round(a,4),
            "a_p": round(a_p,3),
            "b": round(b,4),
            "b_p": round(b_p,3),
            "中介效应": round(ab,4),
            "中介效应占比(%)": round(ratio,2) if not np.isnan(ratio) else np.nan,
            "Bootstrap_p": round(p,3) if not np.isnan(p) else np.nan,
            "显著性": sig
        })

    out_dir = os.path.join(output_path, 'regression_tables')
    os.makedirs(out_dir, exist_ok=True)
    pd.DataFrame(output).to_csv(os.path.join(out_dir, '3_中介效应_最终版.csv'), index=False, encoding='utf-8-sig')
    print(f"\n✅ 结果已保存：3_中介效应_最终版.csv")
    return pd.DataFrame(output)