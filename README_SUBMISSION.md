# 绿色金融数据大屏源码包 README

本目录是比赛提交用源码包，不是完整数据包。整理口径为“前后端完整源码 + 必要工程配置 + 少量典型数据样本 + 运行说明”。

源码包内的一键部署脚本在找不到完整 SQL 时，会自动导入 `greenfianace_server/sql_samples/` 下的样例数据，也就是 simple/sample 数据。该模式只适合检查项目结构、依赖安装、服务启动和部分页面数据链路。

## 作品概述

作品名称：绿色金融与区域碳减排空间协同智能测算平台

主要功能：

- 绿色金融综合指数可视化
- 碳排放与 GDP 空间联动分析
- 碳排放强度预测结果展示
- 基于知识库和页面上下文的 AI 助手

技术栈：

- 前端：Vue 3、Vite 5、TypeScript、Element Plus、ECharts、AntV L7
- 后端：FastAPI、Uvicorn、PyMySQL、DBUtils、python-dotenv
- 数据库：MySQL 5.7+ / 8.x
- 分析模型：Python、pandas、statsmodels、scikit-learn 等
- AI 能力：后端代理调用 DeepSeek API

## 包内结构

```text
.
├─ 一键部署.bat                 Windows 双击部署入口
├─ scripts/deploy-local.ps1     Windows 本地部署脚本
├─ src/                         前端源码
├─ public/                      前端静态资源和 GeoJSON
├─ presets/                     前端预设配置
├─ greenfianace_server/         后端、模型和知识库源码
│  ├─ analysis_models/          当前预测模型与数据处理代码
│  ├─ knowledge/                AI 助手知识库、提示词和指标说明
│  ├─ sql_samples/              数据库结构和少量 SQL 样例
│  ├─ data_samples/             少量典型 CSV / Excel 样本
│  ├─ *.py                      FastAPI 服务和业务接口源码
│  ├─ requirements.txt          Python 依赖清单
│  └─ .env.example              后端环境变量模板
├─ package.json                 前端依赖清单
├─ pnpm-lock.yaml               前端锁定依赖版本
├─ index.html                   Vite 应用入口文件
├─ vite.config.ts
├─ tsconfig.json
├─ README_DEVELOPMENT.md        开发版详细说明
├─ README_SUBMISSION.md         源码提交说明
└─ PACKAGE_MANIFEST.md          源码包清单
```

本包不包含 `node_modules/`、Python 虚拟环境、`dist/`、`.git/`、真实 `.env`、数据库密码、API Key、完整 SQL 和完整数据集。

## 样例数据说明

源码包只保留少量典型样本，位置如下：

- `greenfianace_server/sql_samples/`
- `greenfianace_server/data_samples/`

因此，一键部署在源码包中导入的是 simple/sample 数据，不是完整业务数据。影响如下：

- 地图、图表、排名、下钻列表只会显示样例覆盖的少量地区、年份或指标。
- 绿色金融、省级能源、市级 GDP / 碳排放等页面可能出现数据稀疏、为空或只展示局部结果。
- 预测展示和模型复现只能做结构检查，不能代表完整训练数据和正式预测结果。
- AI 页面总结、Tooltip AI 解读和问答如果启用，会基于当前样例数据回答，结论不具备完整数据口径下的代表性。
- 评审或演示完整效果前，需要按《作品信息概要表》中的完整数据集链接恢复完整 SQL 或数据文件。

完整数据集下载链接：`提交前请替换为正式下载链接`

建议在《作品信息概要表》中同时说明数据来源、字段含义、完整文件列表、样例数据与完整数据的对应关系，以及复现实验时完整数据应放置的目录。

## 一键部署

Windows 本地演示可优先双击：

```text
一键部署.bat
```

脚本会依次完成：

- 检查 `mysql`、`node`、`pnpm`、`python` 命令是否可用
- 提示输入 MySQL 地址、用户名、数据库名和密码
- 将数据库名写入 `greenfianace_server/.env` 的 `DB_NAME`
- 如果输入非默认数据库名，二次确认并保证建库、导入 SQL、后端连接三者一致
- 找不到完整 SQL 时，导入 `greenfianace_server/sql_samples/` 下的 simple/sample 数据，并在终端说明影响
- 询问是否启用 AI 助手
- 生成根目录 `.env` 和 `greenfianace_server/.env`
- 安装前后端依赖，并分别启动 FastAPI 后端和 Vite 前端

如果不启用 AI 助手，AI 问答、页面总结、Tooltip AI 解读、流式问答不可用；地图、图表、数据库查询和预测展示仍可尝试使用，但受样例数据范围限制。

默认访问地址：

```text
http://localhost:5173/vue3-vite5-dashboard/
```

## 手动启动

1. 初始化数据库

源码包默认使用样例 SQL：

```bash
cd greenfianace_server
mysql -u root -p < sql_samples/green_finance_sample.sql
mysql -u root -p < sql_samples/city_carbon_gdp_sample.sql
```

如果已经取得完整 SQL，请优先导入完整数据，而不是样例 SQL。

2. 配置后端环境变量

```bash
cd greenfianace_server
cp .env.example .env
```

在 `.env` 中填写本地 MySQL 配置。真实 `.env` 不应提交。

3. 启动后端

```bash
cd greenfianace_server
python -m venv .venv
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Windows PowerShell 激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

4. 启动前端

```bash
pnpm install
pnpm run serve
```

## 完整数据恢复

源码包为了满足提交体积和数据集上传要求，未直接包含完整数据。完整演示前建议恢复以下内容：

- 完整版 `green_finance.sql`
- 完整版 `city_carbon_gdp.sql`
- 完整模型输入数据，放入 `greenfianace_server/data/` 的对应目录
- 完整预测或实证结果数据，放入 `greenfianace_server/empirical_results/` 的对应目录

恢复完整数据后，再运行 `一键部署.bat`，脚本会优先导入完整 SQL。

## 构建检查

```bash
pnpm run build
```

构建产物输出到 `dist/`。`dist/` 属于编译产物，不包含在源码提交包内。

## 提交检查

- 压缩包小于 200MB
- 包内没有 `node_modules/`、`.venv/`、`dist/`、`.git/`
- 包内没有真实 `.env`、数据库密码、API Key
- `README.md` 和《作品信息概要表》中的完整数据集下载链接已替换
- 已说明源码包只包含 simple/sample 数据，以及由此带来的功能影响
