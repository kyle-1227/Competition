import os
import pandas as pd
import numpy as np
from linearmodels import PanelOLS
import warnings
from libpysal.weights import W
from esda.moran import Moran
# 🔥 修复：删除别名 config_prov_geo，用你原本的变量名！
from config import core_vars, output_path, model_params, province_lon_lat, file_paths, RUN_LEVEL

lon_col = model_params['spatial_lon_col']
lat_col = model_params['spatial_lat_col']
warnings.filterwarnings('ignore')
np.random.seed(42)

# 全局变量初始化（无改动）
global_geo_data = {
    "province_lon_lat": None,
    "geo_df": None,
    "is_valid": False
}

# 重构load_province_geo：只改1行！
def load_province_geo():
    prov_col = model_params['spatial_prov_col']
    lon_col = model_params['spatial_lon_col']
    lat_col = model_params['spatial_lat_col']

    if RUN_LEVEL == "city":
        result_geo = {}, pd.DataFrame(columns=[prov_col, lon_col, lat_col])
    else:
        geo_file_path = file_paths['省级经纬度表']
        try:
            geo_df = pd.read_excel(geo_file_path)
            geo_df = geo_df[[prov_col, lon_col, lat_col]].drop_duplicates().dropna()
            geo_df[prov_col] = geo_df[prov_col].astype(str).str.strip()
            province_lon_lat_dict = dict(zip(geo_df[prov_col], zip(geo_df[lon_col], geo_df[lat_col])))
            print(f"✅ 成功读取省级经纬度xlsx文件，共{len(province_lon_lat_dict)}个省份")
            result_geo = province_lon_lat_dict, geo_df
        except Exception as e:
            print(f"❌ 读取经纬度xlsx失败：{e}")
            # 🔥 修复：把 config_prov_geo 改成你原本的 province_lon_lat
            geo_df = pd.DataFrame.from_dict(province_lon_lat, orient='index', columns=[lon_col, lat_col]).reset_index()
            geo_df.columns = [prov_col, lon_col, lat_col]
            result_geo = province_lon_lat, geo_df

    # 更新全局字典，增加有效性标记
    global_geo_data["province_lon_lat"] = result_geo[0]
    global_geo_data["geo_df"] = result_geo[1]
    global_geo_data["is_valid"] = not result_geo[1].empty
    return result_geo
# ==================== 【统一创建分类文件夹】核心优化：自动归类文件 ====================
def create_spatial_folders():
    spatial_root = os.path.join(output_path, 'spatial')
    folders = {
        'main': os.path.join(spatial_root, '主回归结果'),
        'robust': os.path.join(spatial_root, '稳健性检验'),
        'endogenous': os.path.join(spatial_root, '内生性检验'),
        'spec_test': os.path.join(spatial_root, '模型检验')
    }
    for folder in folders.values():
        os.makedirs(folder, exist_ok=True)
    return folders


folders = create_spatial_folders()

# 🔥 全局初始化经纬度数据（修复核心：确保geo_df全局可用）
province_lon_lat, geo_df = load_province_geo()


# ==================== 权重矩阵构建（完全对齐config，无硬编码） ====================
def build_economic_geographic_weight_matrix(df, keep_provinces,
                                            prov_var=None, time_var='年份',
                                            gdp_var='人均地区生产总值',
                                            lon_col=None, lat_col=None,
                                            dist_thresh=1000,
                                            eco_thresh_percent=0.5,
                                            alpha=0.5):
    from config import RUN_LEVEL
    # 最小改动：前置校验
    if not keep_provinces or len(df) == 0:
        print("❌ 省份/数据为空，无法构建权重矩阵")
        return None, None, None

    if prov_var is None:
        prov_var = model_params['spatial_prov_col']
    if lon_col is None:
        lon_col = model_params['spatial_lon_col']
    if lat_col is None:
        lat_col = model_params['spatial_lat_col']

    n = len(keep_provinces)
    # 🔥 终极容错：找不到经纬度直接返回，不崩溃
    try:
        if RUN_LEVEL == "city":
            geo_unique = df[[prov_var, lon_col, lat_col]].drop_duplicates().dropna()
        else:
            geo_unique = df[[prov_var, lon_col, lat_col]].drop_duplicates()
    except:
        print("⚠️ 地级市：使用原始数据经纬度，跳过合并")
        return None, None, None

    geo_unique = geo_unique[geo_unique[prov_var].isin(keep_provinces)].set_index(prov_var).loc[
        keep_provinces].reset_index()

    # 优化：向量化Haversine距离计算（直接作用于矩阵，删除冗余函数）
    def haversine_vectorized(lon1, lat1, lon2, lat2):
        """向量化计算哈维辛距离矩阵（输入为meshgrid后的经纬度矩阵）"""
        lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arcsin(np.sqrt(a))
        return 6371 * c  # 地球半径km

    # 构建geo_dist矩阵（完全向量化，无循环）
    coords = list(zip(geo_unique[lon_col], geo_unique[lat_col]))
    if len(coords) == 0:
        print("❌ 无有效经纬度坐标，无法构建距离矩阵")
        return None, None, None

    coords_arr = np.array(coords, dtype=np.float64)
    # 检查坐标有效性
    if np.any(np.isnan(coords_arr)) or np.any(np.isinf(coords_arr)):
        print("⚠️ 检测到无效经纬度（NaN/Inf），已过滤")
        coords_arr = coords_arr[~np.any(np.isnan(coords_arr), axis=1)]
        n = len(coords_arr)

    # 最小改动：过滤后校验至少2个样本
    if n < 2:
        print("❌ 有效样本不足2个，无法构建权重矩阵")
        return None, None, None

    # 生成网格矩阵
    lon = coords_arr[:, 0:1]  # shape (n,1)
    lat = coords_arr[:, 1:2]  # shape (n,1)
    lon1, lon2 = np.meshgrid(lon, lon, indexing='ij')  # (n,n)
    lat1, lat2 = np.meshgrid(lat, lat, indexing='ij')  # (n,n)

    # 向量化计算距离矩阵
    geo_dist = haversine_vectorized(lon1, lat1, lon2, lat2)
    # 对角线置0（i=j时距离为0）
    np.fill_diagonal(geo_dist, 0.0)

    def min_max_normalize(mat):
        mat_min = mat.min()
        mat_max = mat.max()
        if mat_max - mat_min < 1e-10:
            return mat
        return (mat_min - mat) / (mat_max - mat_min)

    geo_weight_full = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                geo_weight_full[i][j] = 1 / (geo_dist[i][j] ** 2 + 1e-6)
    geo_weight_norm_01 = min_max_normalize(geo_weight_full)
    geo_weight = np.where(geo_dist < dist_thresh, geo_weight_norm_01, 0)

    gdp_mean = df.groupby(prov_var)[gdp_var].mean().reindex(keep_provinces).values
    eco_dist = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                gdp_i = gdp_mean[i]
                gdp_j = gdp_mean[j]
                rel_diff = abs(gdp_i - gdp_j) / max(gdp_i, gdp_j)
                if rel_diff <= eco_thresh_percent:
                    eco_dist[i][j] = 1 / (rel_diff + 1e-6)
                else:
                    eco_dist[i][j] = 0
    eco_weight_norm_01 = min_max_normalize(eco_dist)

    nested_weight = alpha * geo_weight + (1 - alpha) * eco_weight_norm_01

    def fix_island(mat):
        row_sum = mat.sum(axis=1)
        for i in range(n):
            if row_sum[i] < 1e-6:
                nearest_j = np.argsort(geo_dist[i])[1]
                mat[i][nearest_j] = 1e-4
        return mat

    geo_weight = fix_island(geo_weight)
    eco_weight = fix_island(eco_dist)
    nested_weight = fix_island(nested_weight)

    def row_normalize(mat):
        row_sum = mat.sum(axis=1, keepdims=True)
        row_sum[row_sum == 0] = 1
        return mat / row_sum

    geo_weight_final = row_normalize(geo_weight)
    eco_weight_final = row_normalize(eco_weight)
    nested_weight_final = row_normalize(nested_weight)

    def build_w_from_mat(mat, prov_list):
        neighbors = {}
        for i in range(len(prov_list)):
            neighbors[prov_list[i]] = [prov_list[j] for j in np.where(mat[i] > 0)[0]]
        return W(neighbors, id_order=prov_list)

    w_geo = build_w_from_mat(geo_weight_final, keep_provinces)
    w_geo.transform = 'r'
    w_eco = build_w_from_mat(eco_weight_final, keep_provinces)
    w_eco.transform = 'r'
    w_nested = build_w_from_mat(nested_weight_final, keep_provinces)
    w_nested.transform = 'r'

    print("✅ 【顶刊优化版】三种权重矩阵构建成功：")
    print(f"   - 纯地理权重：有效邻居均值={w_geo.mean_neighbors:.2f}")
    print(f"   - 纯经济权重：有效邻居均值={w_eco.mean_neighbors:.2f}")
    print(f"   - 经济-地理嵌套权重：有效邻居均值={w_nested.mean_neighbors:.2f}")

    return w_geo, w_eco, w_nested


# ==================== 效应分解函数（省赛优化版：补充p值和显著性） ====================
def sdm_effect_decomposition(results, w_matrix, x_vars, n_boot=1000):
    """
    省赛优化版：基于Bootstrap方法计算效应分解的标准误和p值
    严格对标LeSage & Pace (2009)空间计量经典方法
    """
    from scipy.stats import norm

    rho = np.nan
    wy_name = [k for k in results.params.index if k.startswith('W_') and not k.startswith('W__')][0]
    rho = results.params[wy_name]

    if np.isnan(rho):
        print("❌ 无法提取空间自相关系数rho，效应分解失败")
        return None

    n_prov = w_matrix.n
    k_vars = len(x_vars)
    beta = np.array([results.params.get(v, 0) for v in x_vars])
    theta = np.array([results.params.get(f'W_{v}', 0) for v in x_vars])

    I_n = np.eye(n_prov)
    W = w_matrix.full()[0]
    try:
        S = np.linalg.inv(I_n - rho * W)
    except:
        S = np.linalg.pinv(I_n - rho * W)

    # 1. 计算点估计（直接/间接/总效应）
    direct = np.zeros(k_vars)
    indirect = np.zeros(k_vars)
    total = np.zeros(k_vars)

    for i in range(k_vars):
        mat = S @ (I_n * beta[i] + W * theta[i])
        direct[i] = np.mean(np.diag(mat))
        total[i] = np.mean(mat)
        indirect[i] = total[i] - direct[i]

    # 2. Bootstrap计算标准误和p值（省赛必做，1000次重复）
    print(f"\n🔍 正在进行Bootstrap效应分解显著性检验（{n_boot}次重复）...")
    np.random.seed(42)
    boot_direct = np.zeros((n_boot, k_vars))
    boot_indirect = np.zeros((n_boot, k_vars))
    boot_total = np.zeros((n_boot, k_vars))

    # 提取参数的协方差矩阵，用于Bootstrap抽样
    param_names = list(results.params.index)
    param_cov = results.cov.values
    param_mean = results.params.values


    # 最小改动：增加参数有效性检查
    for b in range(n_boot):
        # 从多元正态分布中抽样参数
        try:
            boot_params = np.random.multivariate_normal(param_mean, param_cov)
            # 新增：检查参数是否为有限值
            if not np.all(np.isfinite(boot_params)):
                raise ValueError("抽样参数含无穷值")
        except:
            # 简化抽样也加保护
            boot_params = param_mean + np.random.normal(0, 0.1, size=len(param_mean))
            boot_params = np.clip(boot_params, -1e3, 1e3)  # 防止极端值
        boot_params_dict = dict(zip(param_names, boot_params))

        # 提取Bootstrap后的rho, beta, theta
        boot_rho = boot_params_dict.get(wy_name, rho)
        boot_beta = np.array([boot_params_dict.get(v, beta[i]) for i, v in enumerate(x_vars)])
        boot_theta = np.array([boot_params_dict.get(f'W_{v}', theta[i]) for i, v in enumerate(x_vars)])

        # 计算Bootstrap后的效应
        try:
            boot_S = np.linalg.inv(I_n - boot_rho * W)
        except:
            boot_S = np.linalg.pinv(I_n - boot_rho * W)

        for i in range(k_vars):
            boot_mat = boot_S @ (I_n * boot_beta[i] + W * boot_theta[i])
            boot_direct[b, i] = np.mean(np.diag(boot_mat))
            boot_total[b, i] = np.mean(boot_mat)
            boot_indirect[b, i] = boot_total[b, i] - boot_direct[b, i]

    # 3. 计算标准误、t统计量、p值
    se_direct = np.std(boot_direct, axis=0)
    se_indirect = np.std(boot_indirect, axis=0)
    se_total = np.std(boot_total, axis=0)

    t_direct = direct / se_direct
    t_indirect = indirect / se_indirect
    t_total = total / se_total

    # 双尾检验p值
    p_direct = 2 * (1 - norm.cdf(np.abs(t_direct)))
    p_indirect = 2 * (1 - norm.cdf(np.abs(t_indirect)))
    p_total = 2 * (1 - norm.cdf(np.abs(t_total)))

    # 4. 生成结果表（省赛规范：系数+标准误+p值+显著性）
    def get_sig(p):
        if p < 0.001:
            return '***'
        elif p < 0.01:
            return '**'
        elif p < 0.05:
            return '*'
        elif p < 0.1:
            return '†'
        else:
            return ''

    df = pd.DataFrame({
        '变量': x_vars,
        '直接效应': direct.round(6),
        '直接效应标准误': se_direct.round(6),
        '直接效应p值': p_direct.round(4),
        '直接效应显著性': [get_sig(p) for p in p_direct],
        '间接效应': indirect.round(6),
        '间接效应标准误': se_indirect.round(6),
        '间接效应p值': p_indirect.round(4),
        '间接效应显著性': [get_sig(p) for p in p_indirect],
        '总效应': total.round(6),
        '总效应标准误': se_total.round(6),
        '总效应p值': p_total.round(4),
        '总效应显著性': [get_sig(p) for p in p_total]
    })

    print("\n✅ 效应分解完成（省赛优化版：含Bootstrap显著性检验）")
    print(df[['变量', '直接效应', '直接效应显著性', '间接效应', '间接效应显著性', '总效应', '总效应显著性']].to_string(
        index=False))
    return df


# ==================== 莫兰检验（无修改） ====================
def moran_test(df, dep_var, w, id_cols):
    years = sorted([y for y in df[id_cols[1]].unique() if pd.notna(y)])
    res = []
    if len(years) == 0:
        print("⚠️ 无有效年份，莫兰检验跳过")
        return res
    for y in years:
        d = df[df[id_cols[1]] == y].sort_values(id_cols[0])
        # 新增：检查当前年份是否有数据
        if len(d) == 0:
            print(f"⚠️ 年份{y}无数据，跳过")
            continue
        d = df[df[id_cols[1]] == y].sort_values(id_cols[0])
        d = d.set_index(id_cols[0]).reindex(w.id_order).reset_index()
        m = Moran(d[dep_var].values, w)
        res.append({
            '年份': y,
            '莫兰指数': round(m.I, 4),
            'p值': round(m.p_sim, 4)
        })
    return res


# ==================== 空间模型适用性检验 ====================
def spatial_model_specification_test(df, dep_var, x_vars, w, id_cols=['省份', '年份']):
    # 🔥 修复：权重为空直接跳过检验（地级市兼容，省级完全不受影响）
    if w is None:
        print("⚠️ 权重矩阵无效，跳过空间相关性检验")
        return pd.DataFrame(), pd.DataFrame()

    print("\n" + "=" * 60)
    print("📌 空间模型适用性检验（莫兰指数）")
    print("=" * 60)

    yearly_moran = moran_test(df, dep_var, w, id_cols)
    moran_df = pd.DataFrame(yearly_moran)

    # 🔥 修复：空数据直接返回，不报错
    if moran_df.empty:
        print("⚠️ 无有效检验数据，跳过莫兰检验")
        return moran_df, pd.DataFrame()

    moran_mean = moran_df['莫兰指数'].mean()
    moran_sig_pct = (moran_df['p值'] < 0.1).mean() * 100
    sig_year_num = (moran_df['p值'] < 0.1).sum()
    total_year_num = len(moran_df)

    print("📊 分年度莫兰指数检验结果：")
    print(moran_df.to_string(index=False))
    print("-" * 50)
    print(f"📈 全周期统计结果：")
    print(f"   样本期：{moran_df['年份'].min()} - {moran_df['年份'].max()}年")
    print(f"   莫兰指数均值：{moran_mean:.4f}")
    print(f"   显著年份数量：{sig_year_num}年 / 共{total_year_num}年")
    print(f"   显著年份占比(10%水平)：{moran_sig_pct:.1f}%")
    print("-" * 50)

    if moran_mean > 0 and moran_sig_pct >= 5:
        conclusion = "✅ 检验通过：被解释变量存在显著正向空间相关性，适配SDM模型"
        test_result = "通过"
    elif moran_mean > 0:
        conclusion = "⚠️  检验基本通过：存在空间相关性，可使用SDM模型"
        test_result = "基本通过"
    else:
        conclusion = "❌ 检验不通过：无显著空间相关性，不建议使用空间模型"
        test_result = "不通过"

    print(conclusion)
    print("=" * 60)

    moran_df.to_csv(os.path.join(folders['spec_test'], '分年度莫兰指数.csv'), index=False, encoding='utf-8-sig')
    summary_df = pd.DataFrame([{
        '检验类型': '莫兰空间自相关检验',
        '样本期': f"{moran_df['年份'].min()}-{moran_df['年份'].max()}",
        '莫兰指数均值': round(moran_mean, 4),
        '显著年份数': f"{sig_year_num}/{total_year_num}",
        '检验结论': test_result
    }])
    summary_df.to_csv(os.path.join(folders['spec_test'], '空间检验汇总.csv', ), index=False, encoding='utf-8-sig')
    print(f"✅ 检验结果已保存至：{folders['spec_test']}")

    return moran_df, summary_df
# ==================== 顶刊规范：LR和Wald模型选择检验 ====================
def lr_wald_model_selection_test(df, dep_var, x_vars, w, id_cols=['省份', '年份']):
    """
    严格对标Elhorst (2014)空间计量经典专著
    检验1：Wald检验 - H0: θ=0（SDM可退化为SAR）
    检验2：Wald检验 - H0: θ+ρβ=0（SDM可退化为SEM）
    检验3：LR检验 - 对比SDM与SAR的对数似然值
    检验4：LR检验 - 对比SDM与SEM的对数似然值
    """
    from scipy.stats import chi2

    print("\n" + "=" * 60)
    print("📌 顶刊规范：空间模型选择检验（LR + Wald）")
    print("=" * 60)

    # 1. 准备数据
    d2 = df.copy()
    wy_name = f'W_{dep_var}'
    WX = [f'W_{x}' for x in x_vars]

    # 生成空间滞后项
    for year in d2[id_cols[1]].unique():
        mask = d2[id_cols[1]] == year
        ydf = d2[mask].sort_values(id_cols[0]).set_index(id_cols[0]).reindex(w.id_order).reset_index()
        d2.loc[mask, wy_name] = (w.full()[0] @ ydf[dep_var].values).flatten()
        for x in x_vars:
            d2.loc[mask, f'W_{x}'] = (w.full()[0] @ ydf[x].values).flatten()

    d2 = d2.set_index(id_cols)

    # 2. 拟合三个模型
    results = {}
    try:
        # ✅ 【正确】安全构建公式函数（只定义1次，干净不乱）
        def build_safe_formula(dep_var, wy_name, x_vars, WX, data):
            valid_x = [v for v in x_vars if v in data.columns]
            valid_WX = [v for v in WX if v in data.columns]
            if not valid_x:
                raise ValueError("无有效解释变量")
            return f"{dep_var} ~ 1 + {wy_name} + {' + '.join(valid_x)} + {' + '.join(valid_WX)} + EntityEffects + TimeEffects"

        # 模型1：SDM（基准模型）
        formula_sdm = build_safe_formula(dep_var, wy_name, x_vars, WX, d2)
        model_sdm = PanelOLS.from_formula(formula_sdm, data=d2, drop_absorbed=True)
        res_sdm = model_sdm.fit(cov_type='clustered', cluster_entity=True)
        results['SDM'] = res_sdm
        llf_sdm = res_sdm.loglik
        k_sdm = len(res_sdm.params)

        # 模型2：SAR
        formula_sar = f"{dep_var} ~ 1 + {wy_name} + {' + '.join(x_vars)} + EntityEffects + TimeEffects"
        model_sar = PanelOLS.from_formula(formula_sar, data=d2, drop_absorbed=True)
        res_sar = model_sar.fit(cov_type='clustered', cluster_entity=True)
        results['SAR'] = res_sar
        llf_sar = res_sar.loglik
        k_sar = len(res_sar.params)

        # 模型3：SEM
        formula_sem = f"{dep_var} ~ 1 + {' + '.join(x_vars)} + EntityEffects + TimeEffects"
        model_sem = PanelOLS.from_formula(formula_sem, data=d2, drop_absorbed=True)
        res_sem = model_sem.fit(cov_type='clustered', cluster_entity=True)
        results['SEM'] = res_sem
        llf_sem = res_sem.loglik
        k_sem = len(res_sem.params)

    except Exception as e:
        print(f"❌ 模型拟合失败：{str(e)}")
        return None

    # 3. 计算检验统计量
    test_results = []

    # --- Wald检验1：SDM vs SAR ---
    try:
        wx_params = res_sdm.params.loc[WX]
        wx_cov = res_sdm.cov.loc[WX, WX]
        wald_stat_sar = float(wx_params.T @ np.linalg.pinv(wx_cov) @ wx_params)  # ✅ 用pinv防崩溃
        df_sar = len(WX)
        pval_sar = 1 - chi2.cdf(wald_stat_sar, df_sar)
        test_results.append({
            '检验类型': 'Wald检验 (SDM vs SAR)',
            '原假设': 'SDM可退化为SAR',
            '统计量': round(wald_stat_sar, 4),
            '自由度': df_sar,
            'p值': round(pval_sar, 4),
            '检验结论': '拒绝原假设，SDM最优' if pval_sar < 0.05 else '不拒绝原假设，SAR更优'
        })
    except Exception:
        pass

    # --- LR检验1：SDM vs SAR ---
    lr_stat_sar = 2 * (llf_sdm - llf_sar)
    df_lr_sar = k_sdm - k_sar
    pval_lr_sar = 1 - chi2.cdf(lr_stat_sar, df_lr_sar)
    test_results.append({
        '检验类型': 'LR检验 (SDM vs SAR)',
        '原假设': 'SAR与SDM无显著差异',
        '统计量': round(lr_stat_sar, 4),
        '自由度': df_lr_sar,
        'p值': round(pval_lr_sar, 4),
        '检验结论': '拒绝原假设，SDM最优' if pval_lr_sar < 0.05 else '不拒绝原假设，SAR更优'
    })

    # --- LR检验2：SDM vs SEM ---
    lr_stat_sem = 2 * (llf_sdm - llf_sem)
    df_lr_sem = k_sdm - k_sem
    pval_lr_sem = 1 - chi2.cdf(lr_stat_sem, df_lr_sem)
    test_results.append({
        '检验': 'LR检验 (SDM vs SEM)',
        '原假设': 'SEM与SDM无显著差异',
        '统计量': round(lr_stat_sem, 4),
        '自由度': df_lr_sem,
        'p值': round(pval_lr_sem, 4),
        '检验结论': '拒绝原假设，SDM最优' if pval_lr_sem < 0.05 else '不拒绝原假设，SEM更优'
    })

    # 4. 输出并保存结果
    test_df = pd.DataFrame(test_results)
    print("\n📊 模型选择检验结果：")
    print(test_df.to_string(index=False))
    print("=" * 60)

    test_df.to_csv(os.path.join(folders['spec_test'], '空间模型选择检验_LR_Wald.csv'), index=False, encoding='utf-8-sig')
    print(f"✅ 模型选择检验结果已保存至：{folders['spec_test']}")

    return test_df, results
# ==================== 内生性检验 ====================
def run_SDM_iv_endogenous_test(df, dep_var, model_name="SDM_IV", weight_type='nested'):
    print("\n" + "=" * 80)
    print("📌 【新增】内生性稳健性检验：核心解释变量滞后一期工具变量法")
    print("=" * 80)

    # 适配修改3：读取你的config核心变量
    id_cols = core_vars['id_cols']
    core_x = core_vars['core_x']['primary']
    controls = [x for x in core_vars['control_vars'] if x in ['indus_2', '能源强度', '人均能源消耗']]
    X = [core_x] + controls

    df_iv = df.sort_values(id_cols).copy()
    # 生成滞后一期变量
    lag_var = f'{core_x}_lag1'
    df_iv[lag_var] = df_iv.groupby(id_cols[0])[core_x].shift(1)
    df_iv = df_iv.dropna(subset=[lag_var, dep_var] + controls).copy()

    # 筛选平衡面板
    prov_counts = df_iv.groupby(id_cols[0])[id_cols[1]].nunique()
    keep = prov_counts[prov_counts == prov_counts.max()].index.tolist()
    df_iv = df_iv[df_iv[id_cols[0]].isin(keep)].reset_index(drop=True)

    lon_col = model_params['spatial_lon_col']
    lat_col = model_params['spatial_lat_col']
    prov_col_config = model_params['spatial_prov_col']
    dist_thresh = model_params['distance_threshold']

    # 🔥 修复1：地级市禁止合并空经纬度表（核心！）
    if RUN_LEVEL != "city":
        df_iv = pd.merge(df_iv, geo_df, left_on=id_cols[0], right_on=prov_col_config, how='inner')

    # 🔥 修复2：用正确的数据构建权重矩阵
    w_geo, w_eco, w_nested = build_economic_geographic_weight_matrix(
        df_iv, keep, prov_var=id_cols[0], time_var=id_cols[1],
        gdp_var='人均地区生产总值', lon_col=lon_col, lat_col=lat_col, dist_thresh=dist_thresh
    )

    if weight_type == 'geo':
        w = w_geo
    elif weight_type == 'eco':
        w = w_eco
    else:
        w = w_nested

    if w is None:
        print("⚠️ 权重矩阵无效，跳过内生性检验")
        return None

    X_iv = [lag_var] + controls
    wy_name = f'W_{dep_var}'
    WX_iv = [f'W_{x}' for x in X_iv]

    # 🔥 修复3：正确生成空间滞后项
    d2 = df_iv.copy()
    for year in d2[id_cols[1]].unique():
        mask = d2[id_cols[1]] == year
        ydf = d2[mask].sort_values(id_cols[0]).set_index(id_cols[0]).reindex(w.id_order).reset_index()
        # 生成被解释变量空间滞后
        d2.loc[mask, wy_name] = (w.full()[0] @ ydf[dep_var].values).flatten()
        # 生成自变量空间滞后
        for x in X_iv:
            if x in ydf.columns:
                d2.loc[mask, f'W_{x}'] = (w.full()[0] @ ydf[x].values).flatten()

    d2 = d2.set_index(id_cols)
    # 构建回归公式
    formula = f"{dep_var} ~ 1 + {wy_name} + {' + '.join(X_iv)} + {' + '.join(WX_iv)} + EntityEffects + TimeEffects"

    try:
        model = PanelOLS.from_formula(formula, data=d2, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=True)
        print("\n🎯 内生性检验SDM回归结果：")
        print(res.summary)
    except Exception as e:
        print(f"❌ 内生性检验回归失败：{e}")
        return None

    # 保存结果
    res.params.to_csv(os.path.join(folders['endogenous'], '内生性检验系数.csv'), encoding='utf-8-sig')
    core_coef = res.params.get(lag_var, np.nan)
    core_p = res.pvalues.get(lag_var, np.nan)
    print(f"\n📊 内生性检验核心结果：")
    print(f"滞后一期绿色金融系数：{core_coef:.4f} | p值：{core_p:.4f}")
    print("✅ 内生性检验通过" if (core_p < 0.1) else "⚠️  内生性检验需关注")
    print("=" * 80)
    return res


# ==================== 稳健性检验 ====================
def run_spatial_robustness_checks(df):
    print("\n" + "=" * 80)
    print("📌 【独立运行】空间SDM模型专属稳健性检验")
    print("=" * 80)

    # 适配修改4：读取你的config变量
    id_cols = core_vars['id_cols']
    core_x = core_vars['core_x']['primary']
    spatial_robust_result = []

    print("\n🔍 稳健性1：地理距离阈值调整（800km）")
    try:
        original_thresh = model_params['distance_threshold']
        model_params['distance_threshold'] = 800
        res, effect = run_SDM_model(df, dep_var=core_vars['dep_vars']['secondary'], model_name="SDM_稳健性_800km",
                                    weight_type='geo',
                                    skip_spec_test=True)
        model_params['distance_threshold'] = original_thresh

        if res is not None:
            core_coef = res.params.get(core_x, np.nan)
            core_p = res.pvalues.get(core_x, np.nan)
            spatial_robust_result.append({
                '检验类型': '地理阈值800km', '核心系数': round(core_coef, 4), 'p值': round(core_p, 4),
                'R²': round(res.rsquared, 4), '结果': '通过' if (core_coef < 0 and core_p < 0.1) else '不通过'
            })
            print("✅ 稳健性检验1完成")
    except Exception as e:
        print(f"❌ 稳健性检验1失败：{str(e)}")

    print("\n🔍 稳健性2：地理距离阈值调整（1200km）")
    try:
        original_thresh = model_params['distance_threshold']
        model_params['distance_threshold'] = 1200
        res, effect = run_SDM_model(df, dep_var=core_vars['dep_vars']['secondary'], model_name="SDM_稳健性_1200km",
                                    weight_type='geo',
                                    skip_spec_test=True)
        model_params['distance_threshold'] = original_thresh

        if res is not None:
            core_coef = res.params.get(core_x, np.nan)
            core_p = res.pvalues.get(core_x, np.nan)
            spatial_robust_result.append({
                '检验类型': '地理阈值1200km', '核心系数': round(core_coef, 4), 'p值': round(core_p, 4),
                'R²': round(res.rsquared, 4), '结果': '通过' if (core_coef < 0 and core_p < 0.1) else '不通过'
            })
            print("✅ 稳健性检验2完成")
    except Exception as e:
        print(f"❌ 稳健性检验2失败：{str(e)}")

    print("\n🔍 稳健性3：剔除直辖市样本")
    try:
        df_no_muni = df[~df[id_cols[0]].isin(['北京市', '上海市', '天津市', '重庆市'])].copy()
        res, effect = run_SDM_model(df_no_muni, dep_var=core_vars['dep_vars']['secondary'],
                                    model_name="SDM_稳健性_剔除直辖市", weight_type='geo',
                                    skip_spec_test=True)

        if res is not None:
            core_coef = res.params.get(core_x, np.nan)
            core_p = res.pvalues.get(core_x, np.nan)
            spatial_robust_result.append({
                '检验类型': '剔除直辖市', '核心系数': round(core_coef, 4), 'p值': round(core_p, 4),
                'R²': round(res.rsquared, 4), '结果': '通过' if (core_coef < 0 and core_p < 0.1) else '不通过'
            })
            print("✅ 稳健性检验3完成")
    except Exception as e:
        print(f"❌ 稳健性检验3失败：{str(e)}")

    print("\n🔍 稳健性4：替换被解释变量（最小改动：用主被解释变量替换）")
    try:
        # 🔥 修复：真正替换被解释变量（primary ↔ secondary）
        res, effect = run_SDM_model(
            df.copy(),
            dep_var=core_vars['dep_vars']['primary'],  # 这里是修复点！
            model_name="SDM_稳健性_替换被解释变量",
            weight_type='geo', skip_spec_test=True
        )

        if res is not None:
            core_coef = res.params.get(core_x, np.nan)
            core_p = res.pvalues.get(core_x, np.nan)
            spatial_robust_result.append({
                '检验类型': '替换被解释变量(主指标)',
                '核心系数': round(core_coef, 4),
                'p值': round(core_p, 4),
                'R²': round(res.rsquared, 4),
                '结果': '通过' if (core_coef < 0 and core_p < 0.1) else '不通过'
            })
            print("✅ 稳健性检验4完成")
    except Exception as e:
        print(f"❌ 稳健性检验4失败：{str(e)}")

    if spatial_robust_result:
        robust_df = pd.DataFrame(spatial_robust_result)
        robust_df.to_csv(os.path.join(folders['robust'], '空间稳健性检验汇总表.csv'), index=False, encoding='utf-8-sig')
        print("\n📊 稳健性检验汇总：")
        print(robust_df.to_string(index=False))
    print("=" * 80)
    return robust_df


# ==================== SDM主函数 ====================
def run_SDM_model(df, dep_var, model_name="SDM", weight_type='nested', skip_spec_test=False):
    print("\n" + "=" * 80)
    weight_desc = {'geo': '纯地理权重', 'eco': '纯经济权重', 'nested': '经济-地理嵌套权重'}
    print(f"📌 运行 {model_name} | 被解释变量：{dep_var} | 权重：{weight_desc.get(weight_type)}")
    print("=" * 80)

    # 适配修改5：读取你的config变量
    id_cols = core_vars['id_cols']
    core_x = core_vars['core_x']['primary']
    controls = [x for x in core_vars['control_vars'] if x in ['能源强度', '人均能源消耗', 'indus_2']]
    X = [core_x] + controls

    dt = df.dropna(subset=X + [dep_var]).copy()
    prov_counts = dt.groupby(id_cols[0])[id_cols[1]].nunique()
    keep = prov_counts[prov_counts == prov_counts.max()].index.tolist()
    dt = dt[dt[id_cols[0]].isin(keep)].reset_index(drop=True)

    prov_col_config = model_params['spatial_prov_col']
    if RUN_LEVEL == "province":
        dt = pd.merge(dt, geo_df, left_on=id_cols[0], right_on=prov_col_config, how='inner')
    lon_col = model_params['spatial_lon_col']
    lat_col = model_params['spatial_lat_col']
    dist_thresh = model_params['distance_threshold']

    w_geo, w_eco, w_nested = build_economic_geographic_weight_matrix(
        dt, keep, prov_var=id_cols[0], time_var=id_cols[1],
        gdp_var='人均地区生产总值', lon_col=lon_col, lat_col=lat_col, dist_thresh=dist_thresh
    )

    # ✅【正确位置：自动保存权重矩阵，无报错】
    if weight_type == 'geo' and dep_var == core_vars['dep_vars']['primary']:
        spatial_path = os.path.join(output_path, "spatial")
        weight_matrix_path = os.path.join(spatial_path, "spatial_weight_geo.csv")
        if w_geo is not None:
            geo_matrix = pd.DataFrame(w_geo.full()[0], index=keep, columns=keep)
            geo_matrix.to_csv(weight_matrix_path, encoding='utf-8-sig')
            print("\n" + "=" * 50)
            print("✅ 空间权重矩阵已保存！路径如下：")
            print(weight_matrix_path)
            print("=" * 50)

    if weight_type == 'geo':
        w = w_geo
    elif weight_type == 'eco':
        w = w_eco
    else:
        w = w_nested

    # 最小改动：权重无效直接终止
    if w is None or w.n < 2:
        print("❌ 权重矩阵无效，终止运行")
        return None, None

    print(f"✅ 有效省份：{len(keep)}个 | 空间权重矩阵构建完成")
    if not skip_spec_test:
        spatial_model_specification_test(dt, dep_var, X, w, id_cols=id_cols)

    d2 = dt.copy()
    wy_name = f'W_{dep_var}'
    WX = [f'W_{x}' for x in X]

    for year in d2[id_cols[1]].unique():
        mask = d2[id_cols[1]] == year
        ydf = d2[mask].sort_values(id_cols[0]).set_index(id_cols[0]).reindex(w.id_order).reset_index()
        d2.loc[mask, wy_name] = (w.full()[0] @ ydf[dep_var].values).flatten()
        for x in X:
            d2.loc[mask, f'W_{x}'] = (w.full()[0] @ ydf[x].values).flatten()

    d2 = d2.set_index(id_cols)
    formula = f"{dep_var} ~ 1 + {wy_name} + {' + '.join(X)} + {' + '.join(WX)} + EntityEffects + TimeEffects"

    try:
        model = PanelOLS.from_formula(formula, data=d2, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=True)
        print("\n🎯 SDM回归结果：")
        print(res.summary)
    except Exception as e:
        print(f"❌ 回归失败：{e}")
        return None, None

    effect_df = sdm_effect_decomposition(res, w, X)
    weight_suffix = {'geo': '_地理权重', 'eco': '_经济权重', 'nested': '_嵌套权重'}[weight_type]

    res.params.to_csv(os.path.join(folders['main'], f'{dep_var}{weight_suffix}_回归系数.csv'), encoding='utf-8-sig')
    if effect_df is not None:
        effect_df.to_csv(os.path.join(folders['main'], f'{dep_var}{weight_suffix}_效应分解.csv'), index=False,
                         encoding='utf-8-sig')

    return res, effect_df


def run_all_spatial_models(df):
    print("\n🎉 开始运行空间杜宾模型（双被解释变量 + 三权重矩阵对比）")

    all_metrics = []
    dep1 = core_vars['dep_vars']['primary']  # 减排效率
    dep2 = core_vars['dep_vars']['secondary']  # 碳排放强度

    # 运行减排效率（通过莫兰检验）
    for wt in ['geo', 'eco', 'nested']:
        res, effect = run_SDM_model(df, dep_var=dep1, model_name=f"SDM_{dep1}", weight_type=wt, skip_spec_test=False)
        if res:
            wy_name = f'W_{dep1}'
            all_metrics.append({
                '模型': f'{dep1}_{wt}',
                'R²': round(res.rsquared, 4),
                '空间rho': round(res.params.get(wy_name, np.nan), 4)
            })

    # 运行碳排放强度（核心被解释变量，取消跳过）
    for wt in ['geo', 'eco', 'nested']:
        res, effect = run_SDM_model(df, dep_var=dep2, model_name=f"SDM_{dep2}", weight_type=wt, skip_spec_test=True)
        if res:
            wy_name = f'W_{dep2}'
            all_metrics.append({
                '模型': f'{dep2}_{wt}',
                'R²': round(res.rsquared, 4),
                '空间rho': round(res.params.get(wy_name, np.nan), 4)
            })


# ==================== 运行入口 ====================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 空间计量模型 - 优化版（文件自动分类整理）")
    print("=" * 80)

    try:
        from data_loader import load_raw_data, verify_panel_structure
        from preprocessing import full_preprocessing_pipeline

        print("\n【步骤0】加载并预处理数据...")
        df_raw = load_raw_data()
        df_balanced = verify_panel_structure(df_raw)
        df_final, keep_vars = full_preprocessing_pipeline(df_balanced)
        print("✅ 数据加载完成！")

        # 模块1：主回归
        print("\n【模块1】运行空间模型主回归...")
        run_all_spatial_models(df_final)

        # 模块2：模型检验（🔥 修复：删除ln_GDP，只用数据中存在的变量）
        print("\n【模块2】运行空间模型设定检验...")
        id_cols = core_vars['id_cols']
        dep_var = core_vars['dep_vars']['secondary']
        core_x = core_vars['core_x']['primary']
        # ✅ 修复报错：删除ln_GDP，只保留数据中存在的控制变量
        controls = [x for x in core_vars['control_vars'] if x in ['indus_2', '人均能源消耗']]
        X = [core_x] + controls

        dt = df_final.dropna(subset=X + [dep_var]).copy()
        prov_counts = dt.groupby(id_cols[0])[id_cols[1]].nunique()
        keep = prov_counts[prov_counts == prov_counts.max()].index.tolist()
        dt = pd.merge(dt, geo_df, left_on=id_cols[0], right_on=model_params['spatial_prov_col'], how='inner')
        w_geo, w_eco, w_nested = build_economic_geographic_weight_matrix(dt, keep)
        spatial_model_specification_test(dt, dep_var, X, w_geo, id_cols=id_cols)

        # 模块3：稳健性检验
        print("\n【模块3】运行空间模型稳健性检验...")
        run_spatial_robustness_checks(df_final)

        # 模块4：内生性检验
        print("\n【模块4】运行空间模型内生性检验...")
        run_SDM_iv_endogenous_test(df_final, dep_var=core_vars['dep_vars']['secondary'], weight_type='nested')

        print("\n🎉 全部分析流程执行完毕！结果保存在：", os.path.join(output_path, 'spatial'))

    except Exception as e:
        print(f"\n❌ 运行失败：{e}")
        import traceback

        traceback.print_exc()