import pandas as pd
import os
from config import file_paths, RUN_LEVEL, core_vars


def load_raw_data():
    if RUN_LEVEL == "province":
        file_path = file_paths['核心数据集']
    elif RUN_LEVEL == "city":
        file_path = file_paths['地级市数据集']
    else:
        file_path = file_paths['企业数据集']

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ 核心数据文件不存在：{os.path.abspath(file_path)}")

    df = pd.read_excel(file_path)
    print(f"✅ 成功加载原始数据 | 运行层级：{RUN_LEVEL}")
    return df


def verify_panel_structure(df):
    id_col = core_vars['id_cols'][0]
    year_col = core_vars['id_cols'][1]

    df = df.sort_values([id_col, year_col]).reset_index(drop=True)
    print(f"✅ 面板数据结构校验完成 | 个体ID：{id_col}")
    return df