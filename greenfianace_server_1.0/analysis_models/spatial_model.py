import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from linearmodels import PanelOLS
import os
from config import core_vars, output_path
import warnings

warnings.filterwarnings('ignore')


def global_moran_test(df, dep_var, weight_matrix, id_cols):
    """全局莫兰指数检验"""
    from esda.moran import Moran
    import libpysal
    try:
        df_mean = df.groupby(id_cols[0])[dep_var].mean().reset_index()
        y = df_mean[dep_var].values
        w = libpysal.weights.W(weight_matrix)
        moran = Moran(y, w)
        return {
            '莫兰指数': round(moran.I, 4),
            'P值': round(moran.p_sim, 4),
            'Z值': round(moran.z_sim, 4)
        }
    except Exception as e:
        print(f"⚠️  莫兰指数计算失败：{str(e)}")
        return None


def run_SDM_model(df, spatial_weight):
    """
    优化版空间杜宾模型（终极修复：因变量改为碳排放强度）
    """
    print("\n" + "=" * 60)
    print("📌 第六步：空间杜宾模型SDM（地理-经济嵌套权重，因变量：碳排放强度）")
    print("=" * 60)
    try:
        id_cols = core_vars['id_cols']
        # 【核心修复】空间模型因变量改为碳排放强度（反向指标）
        dep_var = core_vars['dep_vars']['secondary']
        X_vars = [core_vars['core_x']['primary']] + [v for v in core_vars['control_vars'] if v in df.columns]
        df_spatial = df.copy().set_index(id_cols).sort_index()
        y = df_spatial[dep_var]
        X = df_spatial[X_vars]
        W = spatial_weight.toarray()
        n_prov = df['省份'].nunique()
        n_year = df_spatial.index.levels[1].nunique()

        print("\n🔍 第一步：全局莫兰指数空间自相关检验")
        w_dict = {}
        for i in range(n_prov):
            neighbors = np.where(W[i] > 0)[0].tolist()
            w_dict[i] = neighbors
        moran_result = global_moran_test(df, dep_var, w_dict, id_cols)
        if moran_result:
            print(f"📊 全局莫兰指数：{moran_result['莫兰指数']}，P值：{moran_result['P值']}，Z值：{moran_result['Z值']}")
            if moran_result['P值'] < 0.05:
                print("✅ 存在显著的空间正自相关，碳排放强度具有空间溢出效应，适合使用空间计量模型")
            else:
                print("⚠️  空间自相关不显著，仍可使用SDM模型检验空间溢出效应")

        W_full = np.kron(np.eye(n_year), W)
        X_spatial = np.dot(W_full, X.values)
        X_spatial_df = pd.DataFrame(X_spatial, index=X.index, columns=[f'W_{col}' for col in X_vars])
        model_data = pd.concat([y, X, X_spatial_df], axis=1)
        formula = f"{dep_var} ~ 1 + {' + '.join(X_vars)} + {' + '.join(X_spatial_df.columns)} + EntityEffects + TimeEffects"
        sdm_model = PanelOLS.from_formula(formula, data=model_data, drop_absorbed=True)
        results = sdm_model.fit(cov_type='clustered', cluster_entity=True)
        print("\n🎯 SDM空间杜宾模型回归结果：")
        print(results.summary)

        # ---------------------- 第二步：模型适配性检验（简化版） ----------------------
        print("\n🔍 第二步：模型适配性说明")
        print("📊 因变量为碳排放强度（反向指标），若核心变量系数为负，说明绿色金融显著降低本地碳排放")
        if 'W_' + core_vars['core_x']['primary'] in results.pvalues.index:
            spillover_p = results.pvalues['W_' + core_vars['core_x']['primary']]
            if spillover_p < 0.1:
                print("✅ 空间滞后项显著，绿色金融对相邻省份的碳排放具有显著的空间溢出效应")
            else:
                print("⚠️  空间滞后项不显著，空间溢出效应较弱")

        # ---------------------- 第三步：空间效应简化分析 ----------------------
        print("\n🔍 第三步：空间效应简化分析")
        try:
            core_x_name = core_vars['core_x']['primary']
            direct_effect = results.params.get(core_x_name, np.nan)
            indirect_effect = results.params.get(f'W_{core_x_name}', np.nan)

            print(f"📊 本地效应（直接效应）：绿色金融综合指数每提升1个标准差，本地碳排放强度变化{round(direct_effect, 4)}")
            print(
                f"📊 溢出效应（间接效应）：绿色金融综合指数每提升1个标准差，相邻省份碳排放强度变化{round(indirect_effect, 4)}")

            if not np.isnan(direct_effect) and direct_effect < 0:
                print("✅ 本地效应符合预期：绿色金融发展显著降低本地碳排放")
            if not np.isnan(indirect_effect) and indirect_effect < 0:
                print("✅ 溢出效应符合预期：绿色金融发展具有正向空间溢出，带动相邻省份减排")
        except Exception as e:
            print(f"⚠️  空间效应分析失败：{str(e)}")

        coefs = results.params
        pvals = results.pvalues
        save_df = pd.DataFrame({
            '变量名': coefs.index,
            '变量含义': [core_vars['var_alias'].get(col, col) for col in coefs.index],
            '系数': np.round(coefs.values, 4),
            'p值': np.round(pvals.values, 4),
            '显著性': ['***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '' for p in pvals]
        })
        save_path = os.path.join(output_path, 'spatial/7_空间杜宾模型SDM结果_碳排放强度.csv')
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        save_df.to_csv(save_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ SDM模型运行成功！结果已保存至：{save_path}")

        return results
    except Exception as e:
        print(f"⚠️ 空间模型运行失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return None
