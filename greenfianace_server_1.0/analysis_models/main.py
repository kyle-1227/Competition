import warnings
warnings.filterwarnings('ignore')
from config import output_path, province_lon_lat
from data_loader import load_raw_data, verify_panel_structure
from preprocessing import full_preprocessing_pipeline
from benchmark_reg import run_benchmark_regression
from continuous_did import run_standard_did
from mediation_effect import run_mediation_analysis
from heterogeneity import run_heterogeneity_analysis
from robustness_check import run_robustness_checks
# 调用SDM空间模型
from spatial_model import run_SDM_model
import pandas as pd
import os
import numpy as np
from scipy.sparse import csr_matrix
from scipy.spatial.distance import pdist, squareform

def main():
    print("="*80)
    print("🚀 绿色金融与减排效率实证分析全流程（比赛优化版）")
    print("="*80)
    try:
        # ---------------------- 1. 数据读取与面板结构验证 ----------------------
        print("\n【步骤1/8】数据读取与面板结构验证")
        df_raw = load_raw_data()
        print("\n📋 数据列名：")
        print(df_raw.columns.tolist())
        df_balanced = verify_panel_structure(df_raw)

        # ---------------------- 2. 数据预处理全流程 ----------------------
        print("\n【步骤2/8】数据预处理全流程（变量生成+标准化+缩尾+VIF）")
        df_final, keep_vars = full_preprocessing_pipeline(df_balanced)

        # ---------------------- 3. 基准双向固定效应+2SLS ----------------------
        print("\n【步骤3/8】基准双向固定效应模型+2SLS内生性处理")
        # 修复：接收返回值（benchmark_result, df_keep_did），匹配benchmark_reg.py的返回
        benchmark_result, df_keep_did = run_benchmark_regression(df_final, keep_vars)

        # ---------------------- 4. 渐进DID双重差分模型 ----------------------
        print("\n【步骤4/8】渐进DID双重差分模型（因果识别）")
        # 修复：确保df_keep_did的年份列是合法的一维序列
        if '年份' in df_keep_did.columns:
            # 双重验证：确保是Series且无缺失
            df_keep_did['年份'] = pd.to_numeric(df_keep_did['年份'].squeeze(), errors='coerce').fillna(0).astype(int)
        run_standard_did(df_keep_did, keep_vars)

        # ---------------------- 5. 中介效应模型检验 ----------------------
        print("\n【步骤5/8】中介效应模型检验（Bootstrap）")
        mediation_result = run_mediation_analysis(df_final, keep_vars)

        # ---------------------- 6. 异质性分析 ----------------------
        print("\n【步骤6/8】异质性分析（分组回归+交互项+Chow检验）")
        heterogeneity_result = run_heterogeneity_analysis(df_final, keep_vars)

        # ---------------------- 7. 稳健性检验 ----------------------
        print("\n【步骤7/8】稳健性检验")
        robustness_result = run_robustness_checks(df_final, keep_vars)

        # ---------------------- 8. 空间杜宾模型SDM ----------------------
        print("\n【步骤8/8】空间杜宾模型SDM（地理-经济复合权重）")
        # ========== 生成正确的空间权重矩阵 ==========
        # 1. 匹配省份经纬度
        provinces = df_final['省份'].unique()
        coords = []
        valid_provinces = []
        for prov in provinces:
            if prov in province_lon_lat:
                coords.append(province_lon_lat[prov])
                valid_provinces.append(prov)
        coords = np.array(coords)
        n_prov = len(valid_provinces)

        # 2. 生成地理距离倒数矩阵（学术标准）
        dist_matrix = squareform(pdist(coords, 'euclidean'))  # 地理距离矩阵
        w_geo = 1 / (dist_matrix + np.eye(n_prov))  # 距离倒数，对角线为0
        np.fill_diagonal(w_geo, 0)  # 对角线置0，自身无空间效应
        w_geo = w_geo / w_geo.sum(axis=1, keepdims=True)  # 行标准化（空间计量必备）

        # 3. 生成经济权重矩阵
        gdp_mean = df_final[df_final['省份'].isin(valid_provinces)].groupby('省份')['人均地区生产总值'].mean().loc[valid_provinces].values
        econ_dist = np.abs(gdp_mean.reshape(-1, 1) - gdp_mean)
        w_econ = 1 / (econ_dist + np.eye(n_prov))
        np.fill_diagonal(w_econ, 0)
        w_econ = w_econ / w_econ.sum(axis=1, keepdims=True)

        # 4. 地理-经济嵌套权重（学术优化）
        spatial_weight = 0.7 * w_geo + 0.3 * w_econ  # 权重系数可调整
        spatial_weight = csr_matrix(spatial_weight)

        # 运行SDM模型
        sdm_result = run_SDM_model(df_final, spatial_weight)

        print("\n" + "="*80)
        print("🎉 全流程运行完成！所有结果已保存至指定路径")
        print("="*80)

    except Exception as e:
        print(f"\n❌ 全流程运行失败：{str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()