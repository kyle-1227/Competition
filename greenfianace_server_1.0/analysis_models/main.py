import warnings
warnings.filterwarnings('ignore')

# ==================== 全局导入（置顶，符合规范） ====================
from config import output_path, province_lon_lat
from data_loader import load_raw_data, verify_panel_structure
from preprocessing import full_preprocessing_pipeline
from benchmark_reg import run_benchmark_regression
from continuous_did import run_standard_did
from spatial_model import run_all_spatial_models

# 【新增】导入优化后的核心模块
from mediation_effect import run_mediation_analysis
from heterogeneity import run_heterogeneity_analysis
from robustness_check import run_robustness_checks
from spatial_model import run_SDM_model

# ==================== 步骤开关（灵活控制运行模块，调试必备） ====================
RUN_DATA = True          # 步骤1-2：数据读取与预处理
RUN_BENCHMARK = True     # 步骤3：基准回归
RUN_DID = True           # 步骤4：DID因果识别
RUN_MEDIATION = True     # 步骤5：中介效应分析
RUN_HETEROGENEITY = True # 步骤6：异质性分析
RUN_ROBUSTNESS = True    # 步骤7：稳健性检验
RUN_SPATIAL = True       # 步骤8：空间杜宾模型

def main():
    print("\n" + "="*80)
    print("🚀 绿色金融与减排效率实证分析全流程")
    print("="*80)

    # 初始化全局变量，避免步骤间传递报错
    df_final = None
    keep_vars = None
    df_keep_did = None

    try:
        # ---------------------- 步骤1：数据读取与面板结构校验 ----------------------
        if RUN_DATA:
            print("\n【步骤1/8】数据读取与面板结构校验")
            df_raw = load_raw_data()
            df_balanced = verify_panel_structure(df_raw)
            print("✅ 步骤1完成：数据读取与校验成功")

            # ---------------------- 步骤2：数据预处理全流程 ----------------------
            print("\n【步骤2/8】数据预处理全流程")
            df_final, keep_vars = full_preprocessing_pipeline(df_balanced)
            print(f"✅ 步骤2完成：预处理成功，最终样本量：{len(df_final)}，有效变量数：{len(keep_vars)}")
        else:
            print("\n⏭️  跳过步骤1-2：数据读取与预处理")

        # 确保数据存在才继续后续步骤
        if df_final is None or keep_vars is None:
            raise ValueError("数据未正确加载，请检查步骤1-2或开启RUN_DATA开关")

        # ---------------------- 步骤3：基准回归+内生性处理 ----------------------
        if RUN_BENCHMARK:
            print("\n【步骤3/8】基准双向固定效应模型+2SLS内生性处理")
            benchmark_result, df_keep_did = run_benchmark_regression(df_final, keep_vars)
            print("✅ 步骤3完成：基准回归与内生性处理成功")
        else:
            print("\n⏭️  跳过步骤3：基准回归")
            df_keep_did = df_final  # 若跳过基准回归，直接用全量数据做DID

        # ---------------------- 步骤4：DID因果识别 ----------------------
        if RUN_DID:
            print("\n【步骤4/8】渐进DID双重差分模型（因果识别）")
            did_result = run_standard_did(df_keep_did, keep_vars)
            print("✅ 步骤4完成：DID因果识别成功")
        else:
            print("\n⏭️  跳过步骤4：DID因果识别")

        # ---------------------- 步骤5：中介效应分析 ----------------------
        if RUN_MEDIATION:
            print("\n【步骤5/8】中介效应模型（机制分析：Bootstrap检验）")
            mediation_result = run_mediation_analysis(df_final, keep_vars)
            if not mediation_result.empty:
                print("✅ 步骤5完成：中介效应分析成功")
            else:
                print("⚠️  步骤5完成：无有效中介效应结果")
        else:
            print("\n⏭️  跳过步骤5：中介效应分析")

        # ---------------------- 步骤6：异质性分析 ----------------------
        if RUN_HETEROGENEITY:
            print("\n【步骤6/8】异质性分析（分组回归+交互项+Chow检验）")
            heterogeneity_result = run_heterogeneity_analysis(df_final, keep_vars)
            if not heterogeneity_result.empty:
                print("✅ 步骤6完成：异质性分析成功")
            else:
                print("⚠️  步骤6完成：无有效异质性分析结果")
        else:
            print("\n⏭️  跳过步骤6：异质性分析")

        # ---------------------- 步骤7：稳健性检验 ----------------------
        if RUN_ROBUSTNESS:
            print("\n【步骤7/8】稳健性检验（6种方法+PSM-DID+门槛模型）")
            robustness_result = run_robustness_checks(df_final, keep_vars)
            if not robustness_result.empty:
                print("✅ 步骤7完成：稳健性检验成功")
            else:
                print("⚠️  步骤7完成：无有效稳健性检验结果")
        else:
            print("\n⏭️  跳过步骤7：稳健性检验")

        # ---------------------- 步骤8：空间杜宾模型 ----------------------
        if RUN_SPATIAL:
            print("\n【步骤8/8】空间杜宾模型SDM（空间溢出效应+效应分解）")
            # 调用全自动双模型函数，无需传参，自动跑减排效率+碳排放强度
            run_all_spatial_models(df_final)
            print("✅ 步骤8完成：空间杜宾模型运行成功")
        else:
            print("\n⏭️  跳过步骤8：空间杜宾模型")

        # ---------------------- 全流程完成提示 ----------------------
        print("\n" + "="*80)
        print("🎉 实证分析全流程运行完成！")
        print(f"📁 所有结果已保存至：{output_path}")
        print("="*80)

    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ 全流程运行失败：{str(e)}")
        print("="*80)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()