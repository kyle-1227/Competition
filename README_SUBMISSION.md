# 绿色金融数据大屏源码提交说明

本压缩包用于提交《中国大学生计算机设计大赛》源码材料，内容按“前后端完整源码 + 必要工程配置 + 少量典型数据样本 + 运行说明”整理。

## 作品概述

作品名称：绿色金融与区域碳减排空间协同智能测算平台

技术栈：

- 前端：Vue 3、Vite 5、TypeScript、Element Plus、ECharts、AntV L7
- 后端：FastAPI、Uvicorn、PyMySQL、DBUtils、python-dotenv
- 数据库：MySQL 5.7+ / 8.x
- 分析模型：Python、pandas、linearmodels、statsmodels、scikit-learn
- AI 能力：通过 FastAPI 后端代理调用大模型接口

## 包内目录

```text
.
├─ src/                         前端源码
├─ public/                      前端静态资源和 GeoJSON
├─ presets/                     前端预设配置
├─ greenfianace_server/         后端、模型和知识库源码
│  ├─ analysis_models/          数据处理和预测模型代码
│  ├─ knowledge/                AI 助手知识库、提示词和指标说明
│  ├─ sql_samples/              数据库结构和少量 SQL 样例
│  ├─ data_samples/             少量典型数据样本
│  ├─ *.py                      FastAPI 服务和业务接口源码
│  ├─ requirements.txt          Python 依赖清单
│  └─ .env.example              后端环境变量模板
├─ package.json                 前端依赖清单
├─ pnpm-lock.yaml               前端锁定依赖版本
├─ index.html
├─ vite.config.ts
├─ tsconfig.json
└─ README.md
```

本包不包含 `node_modules/`、Python 虚拟环境、`dist/`、`.git/`、真实 `.env`、缓存文件和完整数据集。

## 数据集说明

按比赛要求，源码包内只保留少量典型样本：

- `greenfianace_server/data_samples/`
- `greenfianace_server/sql_samples/`

完整数据集请在《作品信息概要表》中填写下载链接，并同步替换本说明中的占位信息。

完整数据集下载链接：`提交前请替换为正式下载链接`

建议在概要表中说明：

- 数据来源和授权情况
- 数据字段含义
- 完整数据文件列表
- 与源码包内样例数据的对应关系
- 复现实验时完整数据应放置到 `greenfianace_server/data/` 和 `greenfianace_server/empirical_results/` 的对应目录

## 环境要求

- Node.js 18+
- pnpm 8+
- Python 3.10+
- MySQL 5.7+ / 8.x

## 启动步骤

1. 初始化数据库

```bash
cd greenfianace_server
mysql -u root -p < sql_samples/green_finance_sample.sql
mysql -u root -p < sql_samples/city_carbon_gdp_sample.sql
```

样例 SQL 只用于结构和小规模数据检查。完整运行请导入完整版 SQL 或按概要表中的完整数据集说明恢复数据。

2. 配置后端环境变量

```bash
cd greenfianace_server
cp .env.example .env
```

在 `.env` 中填写本地 MySQL 配置和大模型 API Key。真实 `.env` 不应提交。

3. 启动后端

```bash
cd greenfianace_server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Windows PowerShell 激活虚拟环境命令：

```powershell
.\.venv\Scripts\Activate.ps1
```

4. 启动前端

```bash
pnpm install
pnpm run serve
```

默认访问地址：

```text
http://localhost:5173/vue3-vite5-dashboard/
```

## 构建检查

```bash
pnpm run build
```

构建产物输出到 `dist/`。`dist/` 属于编译产物，不包含在源码提交包内。

## 提交前检查

- 压缩包小于 200MB
- 包内没有 `node_modules/`、`.venv/`、`dist/`、`.git/`
- 包内没有真实 `.env`、数据库密码、API Key
- `README.md` 和《作品信息概要表》中的完整数据集下载链接已替换
- 样例数据可以支撑结构检查，完整数据可按说明恢复
