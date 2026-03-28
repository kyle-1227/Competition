import os
import pandas as pd
import numpy as np
from linearmodels import PanelOLS
import warnings
from libpysal.weights import W
from esda.moran import Moran
from config import core_vars, output_path, model_params, province_lon_lat

warnings.filterwarnings('ignore')

# ==================== 效应分解函数 ====================
def sdm_effect_decomposition(results, w_matrix, x_vars):
    rho = np.nan
    # 修复：精准提取空间自回归系数 W_被解释变量
    for key in results.params.index:
        if key.startswith('W_') and key != f'W_{x_vars[0]}':
            rho = results.params[key]
            break

    if np.isnan(rho):
        print("❌ 无法提取空间自回归系数rho，效应分解失败")
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

    direct = np.zeros(k_vars)
    indirect = np.zeros(k_vars)
    total = np.zeros(k_vars)

    for i in range(k_vars):
        mat = S @ (I_n * beta[i] + W * theta[i])
        direct[i] = np.mean(np.diag(mat))
        total[i] = np.mean(mat)
        indirect[i] = total[i] - direct[i]

    df = pd.DataFrame({
        '变量': x_vars,
        '直接效应': direct.round(6),
        '间接效应': indirect.round(6),
        '总效应': total.round(6)
    })
    print("✅ 效应分解完成")
    print(df)
    return df

# ==================== 莫兰检验 ====================
def moran_test(df, dep_var, w, id_cols):
    years = sorted(df[id_cols[1]].unique())
    res = []
    for y in years:
        d = df[df[id_cols[1]] == y].sort_values(id_cols[0])
        # 匹配空间权重省份顺序，避免报错
        d = d.set_index(id_cols[0]).loc[w.id_order].reset_index()
        m = Moran(d[dep_var].values, w)
        res.append({
            '年份': y,
            '莫兰指数': round(m.I,4),
            'p值': round(m.p_sim,4)
        })
    return res

# ==================== 修复版 SDM 主函数（添加 dep_var 参数） ====================
def run_SDM_model(df, dep_var, model_name="SDM"):
    print("\n" + "="*80)
    print(f"📌 运行 {model_name} | 被解释变量：{dep_var}")
    print("="*80)

    id_cols = core_vars['id_cols']
    core_x = core_vars['core_x']['primary']
    # 关键：和你之前流程一致，剔除高VIF的 ln_GDP
    controls = [c for c in core_vars['control_vars'] if c in df.columns and c != 'ln_GDP']
    X = [core_x] + controls

    # 数据清洗
    dt = df.dropna(subset=X+[dep_var]).copy()
    # 平衡面板筛选
    prov_counts = dt.groupby(id_cols[0])[id_cols[1]].nunique()
    keep = prov_counts[prov_counts == prov_counts.max()].index.tolist()
    dt = dt[dt[id_cols[0]].isin(keep)].reset_index(drop=True)

    # 读取经纬度配置
    lon_col = model_params['spatial_lon_col']
    lat_col = model_params['spatial_lat_col']
    dist_thresh = model_params['distance_threshold']

    # 合并省份经纬度
    geo = pd.DataFrame.from_dict(province_lon_lat, orient='index', columns=[lon_col, lat_col]).reset_index()
    geo.columns = [id_cols[0], lon_col, lat_col]
    dt = pd.merge(dt, geo, on=id_cols[0], how='inner')

    # 去重地理信息
    geo_unique = dt[[id_cols[0], lon_col, lat_col]].drop_duplicates().set_index(id_cols[0]).loc[keep].reset_index()
    n = len(keep)

    # 球面距离公式
    def haversine(c1,c2):
        lon1,lat1 = np.radians(c1)
        lon2,lat2 = np.radians(c2)
        d = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
        return 6371 * 2 * np.arcsin(np.sqrt(d))

    # 构建距离权重矩阵
    coords = list(zip(geo_unique[lon_col], geo_unique[lat_col]))
    dist = np.zeros((n,n))
    for i in range(n):
        for j in range(n):
            if i!=j:
                dist[i,j] = haversine(coords[i], coords[j])
    bin_mat = (dist < dist_thresh).astype(int)
    np.fill_diagonal(bin_mat,0)
    neighbors = {keep[i]: [keep[j] for j in np.where(bin_mat[i])[0]] for i in range(n)}

    # 构建空间权重
    try:
        w = W(neighbors, id_order=keep)
        w.transform = 'r'  # 行标准化
    except Exception as e:
        print(f"❌ 空间权重构建失败：{e}")
        return None, None

    print(f"✅ 平衡省份：{n} | 空间权重矩阵构建完成")
    # 莫兰指数检验
    yearly_moran = moran_test(dt, dep_var, w, id_cols)

    # 构建空间滞后项 WY, WX
    d2 = dt.copy()
    wy_name = f'W_{dep_var}'
    for year in d2[id_cols[1]].unique():
        mask = d2[id_cols[1]] == year
        ydf = d2[mask].sort_values(id_cols[0]).set_index(id_cols[0]).loc[w.id_order].reset_index()
        # 滞后被解释变量
        d2.loc[mask, wy_name] = (w.full()[0] @ ydf[dep_var].values).flatten()
        # 滞后自变量
        for x in X:
            d2.loc[mask, f'W_{x}'] = (w.full()[0] @ ydf[x].values).flatten()

    # 面板回归
    d2 = d2.set_index(id_cols)
    WX = [f'W_{x}' for x in X]
    # SDM 模型公式（双向固定效应）
    formula = f"{dep_var} ~ 1 + {wy_name} + {'+'.join(X)} + {'+'.join(WX)} + EntityEffects + TimeEffects"

    try:
        model = PanelOLS.from_formula(formula, data=d2, drop_absorbed=True)
        res = model.fit(cov_type='clustered', cluster_entity=True)
        print("\n🎯 SDM 回归结果：")
        print(res.summary)
    except Exception as e:
        print(f"❌ 回归失败：{e}")
        return None, None

    # 效应分解
    effect_df = sdm_effect_decomposition(res, w, X)

    # 保存结果
    out = os.path.join(output_path, 'spatial')
    os.makedirs(out, exist_ok=True)
    res.params.to_csv(os.path.join(out, f'{model_name}_系数.csv'), encoding='utf-8-sig')
    if effect_df is not None:
        effect_df.to_csv(os.path.join(out, f'{model_name}_效应分解.csv'), encoding='utf-8-sig')
    pd.DataFrame(yearly_moran).to_csv(os.path.join(out, f'{model_name}_莫兰.csv'), encoding='utf-8-sig')

    print(f"\n✅ {model_name} 结果保存至：{out}")
    return res, effect_df

# ==================== 🔥 单独运行入口（一键跑双模型） ====================
def run_all_spatial_models(df):
    """
    单独运行空间模型：
    1. 减排效率（本地效应）
    2. 碳排放强度（空间溢出效应）
    """
    print("\n🎉 开始单独运行空间杜宾模型（双被解释变量）")
    # 模型1：减排效率
    run_SDM_model(df, dep_var="减排效率", model_name="SDM_减排效率")
    # 模型2：碳排放强度
    run_SDM_model(df, dep_var="碳排放强度", model_name="SDM_碳排放强度")
    print("\n✅ 所有空间模型运行完成！")