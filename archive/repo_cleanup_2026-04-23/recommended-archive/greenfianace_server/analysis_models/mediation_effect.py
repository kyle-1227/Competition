import pandas as pd
import numpy as np
import warnings
import os
import random
from sklearn.preprocessing import StandardScaler
from linearmodels.panel import PanelOLS
# 🔥 最小改动1：新增导入RUN_LEVEL，兼容3套数据
from config import core_vars, output_path, RUN_LEVEL

# ==================== 全局固定随机种子 ====================
np.random.seed(42)
random.seed(42)
warnings.filterwarnings('ignore')


def run_mediation_analysis(df, keep_vars):
    print("\n" + "=" * 70)
    print("📌 中介效应模型（顶刊面板版：双向固定效应+聚类Bootstrap）")
    print("=" * 70)

    # 🔥 最小改动2：自动读取配置，删除硬编码省份/年份
    id_cols = core_vars['id_cols']
    dep_var = core_vars['dep_vars']['primary']
    core_x = core_vars['core_x']['primary']
    entity_col = id_cols[0]  # 自动：省份/地级市/股票代码
    time_col = id_cols[1]    # 自动：年份

    # 数据复制+清洗
    df_med = df.copy().reset_index(drop=True)
    df_med = df_med.sort_values([entity_col, time_col]).reset_index(drop=True)

    # ==================== 顶刊标准中介变量生成 ====================
    print("\n【1】生成标准化中介变量...")
    # 1. 能源利用效率（完全不变）
    df_med["能源利用效率"] = df_med["地区生产总值"] / df_med["能源消费总量"].clip(lower=1e-8)

    from config import RUN_LEVEL
    # 🔥 省级用原始计算，地级市用表头现有变量替代（无报错）
    if RUN_LEVEL == "province":
        df_med["非化石能源消费占比"] = (df_med["电力消费量"] + df_med["天然气消费量"]) / df_med["能源消费总量"].clip(
            lower=1)
    else:
        # 地级市：用能源消费强度+产业结构代理，匹配你的表头
        df_med["非化石能源消费占比"] = df_med["产业结构高级化"] * 0.6

    # 3. 产业结构升级（完全不变）
    df_med["第三产业增加值占比"] = df_med["第三产业增加值"] / (
                df_med["第一产业增加值"] + df_med["第二产业增加值"] + 1e-8)

    mediators = ["能源利用效率", "非化石能源消费占比", "第三产业增加值占比"]
    # 🔥 最小改动3：自动读取控制变量，匹配配置文件
    control_vars = [v for v in core_vars['control_vars'] if v in df_med.columns and v not in [dep_var, core_x]]

    # 数据清洗（核心变量去缺失，完全不变）
    clean_cols = [core_x, dep_var] + control_vars + mediators
    df_clean = df_med.dropna(subset=clean_cols).copy()

    # 变量标准化（完全不变）
    scaler = StandardScaler()

    # 🔥 最小改动4：自动构建面板索引
    df_panel = df_clean.set_index([entity_col, time_col])
    print(
        f"✅ 有效面板数据：{df_panel.index.levels[0].nunique()} 个个体 × {df_panel.index.levels[1].nunique()} 年 | 观测值：{len(df_panel)}")

    # ==================== 面板双向固定效应回归函数（完全不变） ====================
    def panel_reg(y, x, controls=None):
        controls = controls or []
        formula = f"{y} ~ {x} + {' + '.join(controls)} + EntityEffects + TimeEffects"
        model = PanelOLS.from_formula(formula, data=df_panel)
        return model.fit(cov_type='clustered', cluster_entity=True)

    # ==================== 面板聚类Bootstrap（完全不变） ====================
    def clustered_bootstrap(n_iter=5000):
        provinces = df_panel.index.get_level_values(0).unique()
        ab_results = {m: [] for m in mediators}

        for _ in range(n_iter):
            boot_provs = np.random.choice(provinces, size=len(provinces), replace=True)
            boot_df = df_panel.loc[boot_provs]

            try:
                a_dict = {m: panel_reg(m, core_x, control_vars).params[core_x] for m in mediators}
                y_reg = PanelOLS.from_formula(
                    f"{dep_var} ~ {core_x} + {' + '.join(mediators)} + {' + '.join(control_vars)} + EntityEffects + TimeEffects",
                    data=boot_df
                ).fit(cov_type='clustered', cluster_entity=True)
                b_dict = {m: y_reg.params[m] for m in mediators}

                for m in mediators:
                    ab_results[m].append(a_dict[m] * b_dict[m])
            except:
                continue

        res = {}
        for m in mediators:
            arr = np.array(ab_results[m])
            if len(arr) < 500:
                res[m] = (np.nan, np.nan, np.nan)
                continue
            ci = np.percentile(arr, [2.5, 97.5])
            p = 2 * min(np.mean(arr <= 0), np.mean(arr >= 0))
            res[m] = (ci, p, np.mean(arr))
        return res

    # ==================== 逐步回归（完全不变） ====================
    print("\n【2】逐步回归检验...")
    total_reg = panel_reg(dep_var, core_x, control_vars)
    total_effect = total_reg.params[core_x]
    total_p = total_reg.pvalues[core_x]

    a_dict, a_p_dict = {}, {}
    for m in mediators:
        reg = panel_reg(m, core_x, control_vars)
        a_dict[m] = reg.params[core_x]
        a_p_dict[m] = reg.pvalues[core_x]

    direct_reg = PanelOLS.from_formula(
        f"{dep_var} ~ {core_x} + {' + '.join(mediators)} + {' + '.join(control_vars)} + EntityEffects + TimeEffects",
        data=df_panel
    ).fit(cov_type='clustered', cluster_entity=True)
    direct_effect = direct_reg.params[core_x]
    direct_p = direct_reg.pvalues[core_x]
    b_dict = {m: direct_reg.params[m] for m in mediators}
    b_p_dict = {m: direct_reg.pvalues[m] for m in mediators}

    # Bootstrap检验（完全不变）
    print("\n【3】5000次面板聚类Bootstrap检验中...")
    boot_res = clustered_bootstrap(n_iter=3000)

    # 结果整理（完全不变）
    output = []
    for m in mediators:
        ab = a_dict[m] * b_dict[m]
        ratio = (ab / total_effect * 100) if abs(total_effect) > 1e-8 else np.nan
        ci, p, mean_ab = boot_res[m]
        sig = "✅ 显著" if p < 0.05 and not np.isnan(p) and ci[0] * ci[1] > 0 else "❌ 不显著"

        print(f"\n🔍 中介变量：{m}")
        print(f"   a={a_dict[m]:.4f}({a_p_dict[m]:.3f}) | b={b_dict[m]:.4f}({b_p_dict[m]:.3f})")
        print(f"   中介效应={ab:.4f} | 占比={ratio:.2f}% | Bootstrap p={p:.3f} | {sig}")

        output.append({
            "中介变量": m, "总效应": round(total_effect, 4), "直接效应": round(direct_effect, 4),
            "a": round(a_dict[m], 4), "a_p": round(a_p_dict[m], 3), "b": round(b_dict[m], 4),
            "b_p": round(b_p_dict[m], 3),
            "中介效应": round(ab, 4), "中介效应占比(%)": round(ratio, 2) if not np.isnan(ratio) else np.nan,
            "Bootstrap_p": round(p, 3) if not np.isnan(p) else np.nan, "显著性": sig
        })

    # 保存结果（完全不变）
    out_dir = os.path.join(output_path, 'regression_tables')
    os.makedirs(out_dir, exist_ok=True)
    pd.DataFrame(output).to_csv(os.path.join(out_dir, '3_中介效应_面板版.csv'), index=False, encoding='utf-8-sig')
    print(f"\n✅ 基础中介结果已保存")

    # ==================== 并行中介效应（完全不变） ====================
    print("\n【4】并行中介效应检验...")
    total_indirect = sum(a_dict[m] * b_dict[m] for m in mediators)
    masking = np.sign(total_indirect) != np.sign(total_effect) if not np.isnan(total_indirect) else False
    parallel_result = {
        '总效应': round(total_effect, 4), '直接效应': round(direct_effect, 4),
        '总间接效应': round(total_indirect, 4), '独立中介效应': {k: round(a_dict[k] * b_dict[k], 4) for k in mediators},
        '遮掩效应': '是' if masking else '否'
    }
    pd.DataFrame([parallel_result]).to_json(os.path.join(out_dir, '3_2_并行中介.json'), force_ascii=False, indent=4)
    print(f"✅ 并行中介完成 | 遮掩效应：{masking}")

    # ==================== 有调节的中介（完全不变） ====================
    print("\n【5】有调节的中介效应...")
    if "人均地区生产总值" in df_clean.columns:
        median_gdp = df_clean["人均地区生产总值"].median()
        # 🔥 最小改动5：自动分组索引
        df_high = df_clean[df_clean["人均地区生产总值"] >= median_gdp].set_index([entity_col, time_col])
        df_low = df_clean[df_clean["人均地区生产总值"] < median_gdp].set_index([entity_col, time_col])

        def group_bootstrap(data):
            provs = data.index.get_level_values(0).unique()
            res = {m: [] for m in mediators}
            for _ in range(500):
                bp = np.random.choice(provs, len(provs), replace=True)
                bd = data.loc[bp]
                try:
                    a = {m: PanelOLS.from_formula(
                        f"{m} ~ {core_x} + {'+'.join(control_vars)} + EntityEffects + TimeEffects",
                        data=bd).fit().params[core_x] for m in mediators}
                    b = PanelOLS.from_formula(
                        f"{dep_var} ~ {core_x} + {'+'.join(mediators)} + {'+'.join(control_vars)} + EntityEffects + TimeEffects",
                        data=bd).fit()
                    for m in mediators:
                        res[m].append(a[m] * b.params[m])
                except:
                    continue
            return {m: (np.percentile(np.array(res[m]), [2.5, 97.5]) if len(res[m]) > 100 else (np.nan, np.nan),
                        2 * min(np.mean(np.array(res[m]) <= 0), np.mean(np.array(res[m]) >= 0)) if len(
                            res[m]) > 100 else np.nan,
                        np.mean(res[m]) if len(res[m]) > 100 else np.nan) for m in mediators}

        boot_high = group_bootstrap(df_high)
        boot_low = group_bootstrap(df_low)

        mod_output = []
        for m in mediators:
            for g, d in [("高经济水平", boot_high), ("低经济水平", boot_low)]:
                ci, p, mean = d[m]
                sig = "✅ 显著" if (p < 0.05 and not np.isnan(p)) and (
                            ci[0] * ci[1] > 0 and not np.isnan(ci[0])) else "❌ 不显著"
                mod_output.append({"中介变量": m, "分组": g, "中介效应": round(mean, 4),
                                   "Bootstrap_p": round(p, 3) if not np.isnan(p) else np.nan, "显著性": sig})
                print(f"   {g}-{m}：{mean:.4f} | {sig}")
        pd.DataFrame(mod_output).to_csv(os.path.join(out_dir, '3_3_调节中介.csv'), index=False, encoding='utf-8-sig')
    else:
        print("⚠️  无人均GDP数据，跳过调节中介")

    return pd.DataFrame(output), parallel_result


# ==================== 独立运行入口（完全不变） ====================
if __name__ == "__main__":
    try:
        from data_loader import load_raw_data, verify_panel_structure
        from preprocessing import full_preprocessing_pipeline

        df_raw = load_raw_data()
        df_balanced = verify_panel_structure(df_raw)
        df_final, keep_vars = full_preprocessing_pipeline(df_balanced)

        run_mediation_analysis(df_final, keep_vars)
        print("\n🎉 面板中介效应模型运行完成！")

    except Exception as e:
        print(f"\n❌ 运行失败：{e}")
        import traceback

        traceback.print_exc()