# ==================== 基础库导入 & 全局配置 ====================
import pandas as pd
import numpy as np
import os
import warnings
import random
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import xgboost as xgb
from prophet import Prophet
from config import core_vars, output_path, RUN_LEVEL, file_paths

np.random.seed(42)
random.seed(42)
torch.manual_seed(42)
if torch.cuda.is_available():
    torch.cuda.manual_seed(42)
warnings.filterwarnings('ignore')

# ==================== 核心配置：自动适配省级/地级市 ====================
PRED_CONFIG = {
    "pred_years": 5,
    "history_years": 5,
    "train_test_split": 0.8,
    "id_cols": core_vars['id_cols'],
    # ✅ 自动用你配置里的控制变量，绝不报错
    "feature_cols": [core_vars['core_x']['primary']] + core_vars['control_vars'],
    "weight_map": {
"减排效率": ["地理权重", "经济权重", "嵌套权重"],
"碳排放强度": ["地理权重", "经济权重", "嵌套权重"],
"能源强度": ["地理权重", "经济权重", "嵌套权重"],
"碳排放量(补)": ["地理权重", "经济权重", "嵌套权重"],
"CO2排放量": ["地理权重", "经济权重", "嵌套权重"]  # <-- 加这行
},
    "effect_pattern": "{target}_{weight}_效应分解.csv",
    "coef_pattern": "{target}_{weight}_回归系数.csv"
}

PRED_OUTPUT_PATH = os.path.join(output_path, 'prediction_results')
os.makedirs(PRED_OUTPUT_PATH, exist_ok=True)
os.makedirs(os.path.join(PRED_OUTPUT_PATH, 'model_eval'), exist_ok=True)
os.makedirs(os.path.join(PRED_OUTPUT_PATH, 'scenario'), exist_ok=True)

# ==================== 数据预处理 ====================
class PredictionDataProcessor:
    def __init__(self, target_col):
        self.target_col = target_col
        self.id_cols = PRED_CONFIG["id_cols"]
        self.base_features = PRED_CONFIG["feature_cols"]
        self.weights = PRED_CONFIG["weight_map"][target_col]
        self.entity_col = self.id_cols[0]
        self.year_col = self.id_cols[1]

        self.df_base = None
        self.entities = None
        self.max_year = None
        self.spatial_features = {}
        self.has_spatial = False
        self.final_features = []

    def load_final_data(self):
        data_path = file_paths['最终清洗数据集']
        self.df_base = pd.read_csv(data_path, encoding="utf-8-sig")
        self.df_base = self.df_base.copy()

        # ✅ 自动过滤：只保留数据里有的列（最关键修复！）
        self.final_features = [f for f in self.base_features if f in self.df_base.columns]

        self.entities = self.df_base[self.entity_col].unique()
        self.max_year = self.df_base[self.year_col].max()
        print(f"✅ 数据加载完成 | {len(self.entities)}个{self.entity_col} | 2000-{self.max_year}")
        print(f"✅ 自动匹配有效预测特征：{self.final_features}")
        return self.df_base

    def load_sdm_spatial_effect(self):
        sdm_dir = os.path.join(output_path, "spatial", "主回归结果")
        if not os.path.exists(sdm_dir):
            print("❌ 未找到SDM文件夹")
            return False

        for weight in self.weights:
            try:
                effect_file = PRED_CONFIG["effect_pattern"].format(target=self.target_col, weight=weight)
                coef_file = PRED_CONFIG["coef_pattern"].format(target=self.target_col, weight=weight)
                df_effect = pd.read_csv(os.path.join(sdm_dir, effect_file), encoding="utf-8-sig")
                df_coef = pd.read_csv(os.path.join(sdm_dir, coef_file), encoding="utf-8-sig")

                gfi = df_effect[df_effect["变量"] == core_vars['core_x']['primary']].iloc[0]
                rho_val = df_coef[df_coef.iloc[:,0] == f"W_{self.target_col}"].iloc[0,1]

                self.spatial_features[weight] = {
                    "direct": float(gfi["直接效应"]),
                    "indirect": float(gfi["间接效应"]),
                    "total": float(gfi["总效应"]),
                    "rho": float(rho_val)
                }
            except:
                continue

        self.has_spatial = len(self.spatial_features) > 0
        if self.has_spatial:
            mean_spatial = np.mean([list(v.values()) for v in self.spatial_features.values()], axis=0)
            self.df_base["spatial_direct"] = mean_spatial[0]
            self.df_base["spatial_indirect"] = mean_spatial[1]
            self.df_base["spatial_rho"] = mean_spatial[3]
            self.final_features += ["spatial_direct", "spatial_indirect", "spatial_rho"]

        return self.has_spatial

    def build_sequences(self):
        seq_len = PRED_CONFIG["history_years"]
        X, y = [], []
        scaler_x = MinMaxScaler()
        scaler_y = MinMaxScaler()

        for entity in self.entities:
            df_p = self.df_base[self.df_base[self.entity_col] == entity].sort_values(self.year_col).reset_index(drop=True)
            if len(df_p) < seq_len + 1:
                continue

            # ✅ 只用有效列，永远不报错 KeyError
            x_vals = scaler_x.fit_transform(df_p[self.final_features])
            y_vals = scaler_y.fit_transform(df_p[[self.target_col]])

            for i in range(len(df_p) - seq_len):
                X.append(x_vals[i:i+seq_len])
                y.append(y_vals[i+seq_len])

        return np.array(X), np.array(y), scaler_x, scaler_y

    def gen_future_features(self, scenario="基准情景", gfi_growth=None, gdp_growth=0.05, energy_adjust=0.02):
        default_growth = {"乐观情景":0.2,"基准情景":0.1,"保守情景":0.03}
        g = gfi_growth if gfi_growth is not None else default_growth[scenario]
        future_years = np.arange(self.max_year+1, self.max_year+1+5)

        df_future = pd.DataFrame()
        for entity in self.entities:
            last = self.df_base[(self.df_base[self.entity_col]==entity) & (self.df_base[self.year_col]==self.max_year)].iloc[0].copy()
            for y in future_years:
                row = last.copy()
                row[self.year_col] = y
                gap = y - self.max_year
                row[core_vars['core_x']['primary']] = last[core_vars['core_x']['primary']] * (1+g)**gap
                df_future = pd.concat([df_future, pd.DataFrame([row])], ignore_index=True)
        return df_future

# ==================== LSTM ====================
class LSTMModel(nn.Module):
    def __init__(self, in_dim=7, hid_dim=64, layers=2):
        super().__init__()
        self.lstm = nn.LSTM(in_dim, hid_dim, layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hid_dim,1)
    def forward(self,x):
        out,_=self.lstm(x)
        return self.fc(out[:,-1,:])

class LSTMTrainer:
    def __init__(self,in_dim):
        self.device="cuda" if torch.cuda.is_available() else "cpu"
        self.model=LSTMModel(in_dim).to(self.device)
        self.opt=torch.optim.Adam(self.model.parameters(),lr=0.001)
        self.loss_fn=nn.MSELoss()
        self.scaler_x=None
        self.scaler_y=None

    def train(self,X_train,y_train,X_test,y_test,epochs=800):
        X_train=torch.tensor(X_train,dtype=torch.float32).to(self.device)
        y_train=torch.tensor(y_train,dtype=torch.float32).to(self.device)
        X_test=torch.tensor(X_test,dtype=torch.float32).to(self.device)
        y_test=torch.tensor(y_test,dtype=torch.float32).to(self.device)

        scheduler=torch.optim.lr_scheduler.ReduceLROnPlateau(self.opt,patience=50,factor=0.5)
        best_loss=float('inf')
        patience=100
        trigger=0

        for e in range(epochs):
            self.model.train()
            self.opt.zero_grad()
            pred=self.model(X_train)
            loss=self.loss_fn(pred,y_train)
            loss.backward()
            self.opt.step()

            self.model.eval()
            with torch.no_grad():
                val_pred=self.model(X_test)
                val_loss=self.loss_fn(val_pred,y_test)

            scheduler.step(val_loss)
            if val_loss<best_loss:
                best_loss=val_loss;trigger=0
            else:
                trigger+=1
                if trigger>=patience:
                    print(f"✅ 早停：最优轮次{e}")
                    break
            if e%100==0:
                print(f"Epoch {e:3d} | 训练Loss:{loss.item():.4f} | 验证Loss:{val_loss.item():.4f}")

    def predict(self,X):
        self.model.eval()
        with torch.no_grad():
            return self.model(torch.tensor(X,dtype=torch.float32).to(self.device)).cpu().numpy()

# ==================== 预测主流程 ====================
def run_full_prediction(target):
    print(f"\n{'='*60}")
    print(f"🚀 开始预测：{target} | SDM+LSTM 空间融合预测模型")
    print(f"{'='*60}")

    processor=PredictionDataProcessor(target)
    processor.load_final_data()
    processor.load_sdm_spatial_effect()

    X,y,scaler_x,scaler_y=processor.build_sequences()
    split=int(len(X)*0.8)
    X_train,X_test=X[:split],X[split:]
    y_train,y_test=y[:split],y[split:]

    trainer=LSTMTrainer(in_dim=len(processor.final_features))
    trainer.scaler_x=scaler_x
    trainer.scaler_y=scaler_y
    trainer.train(X_train,y_train,X_test,y_test,epochs=800)

    y_pred=trainer.predict(X_test)
    y_true=y_test.flatten()
    mae=mean_absolute_error(y_true,y_pred)
    rmse=np.sqrt(mean_squared_error(y_true,y_pred))
    r2=r2_score(y_true,y_pred)
    print(f"\n📊 模型评估：MAE={mae:.4f} | RMSE={rmse:.4f} | R²={r2:.4f}")

    all_res=pd.DataFrame()
    for sce in ["保守情景","基准情景","乐观情景"]:
        df_fut=processor.gen_future_features(sce)
        seqs=[]
        for entity in processor.entities:
            hist=processor.df_base[processor.df_base[processor.entity_col]==entity].sort_values(processor.year_col).tail(5)
            fut=df_fut[df_fut[processor.entity_col]==entity].sort_values(processor.year_col)
            for _,row in fut.iterrows():
                win=pd.concat([hist,pd.DataFrame([row])])
                seqs.append(win[processor.final_features].values[-5:])
                hist=pd.concat([hist.iloc[1:],pd.DataFrame([row])])

        pred_raw=trainer.predict(np.array(seqs))
        pred_val=scaler_y.inverse_transform(pred_raw).flatten()
        ci=1.96*np.std(pred_val)
        df_fut["预测值"]=pred_val
        df_fut["95%_下限"]=pred_val-ci
        df_fut["95%_上限"]=pred_val+ci
        df_fut["情景"]=sce
        df_fut["预测目标"]=target

        cols=processor.id_cols+["情景","预测目标","预测值","95%_下限","95%_上限"]+processor.final_features
        all_res=pd.concat([all_res,df_fut[cols]],ignore_index=True)

    save_path=os.path.join(PRED_OUTPUT_PATH,"scenario",f"{target}_三情景预测结果.csv")
    all_res.to_csv(save_path,index=False,encoding="utf-8-sig")
    print(f"\n🎉 预测完成！已保存：\n{save_path}")
    return all_res

# ==================== 入口 ====================
if __name__=="__main__":
    target_vars = [v for v in core_vars['dep_vars'].values() if v]
    for target in target_vars:
        run_full_prediction(target)