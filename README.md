# 绿色金融与区域碳减排空间协同智能测算平台

基于 `Vue 3 + Vite 5 + TypeScript + AntV L7 + ECharts + FastAPI + MySQL` 的数据可视化大屏项目，用于展示绿色金融、碳排放空间分布、碳排放强度预测，以及 GDP 与碳排放联动分析。

## 项目概览

当前首页包含 3 个主页面：

- `绿色金融综合指数`
- `碳排放+GDP底色`
- `碳排放强度预测`

其中：

- 碳排放+GDP底色页支持两种地图指标视图：`碳排放`、`GDP`
- 碳排放+GDP底色页内置 `GDP 和碳排放组合图`
- 宏观经济不再作为独立 Tab，而是并入碳排放+GDP底色页
- 绿色金融页和碳排放+GDP底色页当前都只保留 `全国省级 -> 省内市级` 两级下钻
- 碳排放强度预测页使用 `BizCarbonPredictionV3.vue`，前端统一展示 `组合预测` 结果；展示层仍对碳排放强度做正向化，但不再对预测段做自适应缩放

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite 5、Element Plus、ECharts、AntV L7、Pinia、Vue Router |
| 后端 | FastAPI、Uvicorn、PyMySQL、DBUtils、python-dotenv、httpx |
| 数据库 | MySQL 5.7+ / 8.x |
| AI 能力 | DeepSeek API（通过 FastAPI 后端代理） |

## 目录结构

```text
.
├─ greenfianace_server/
│  ├─ analysis_models/
│  ├─ data/
│  ├─ empirical_results/
│  ├─ .env.example
│  ├─ ai_agent.py
│  ├─ ai_context.py
│  ├─ ai_service.py
│  ├─ ai_tools.py
│  ├─ ai_types.py
│  ├─ city_carbon_gdp.sql
│  ├─ data_service.py
│  ├─ green_finance.sql
│  ├─ requirements.txt
│  └─ server.py
├─ public/
├─ scripts/
│  └─ deploy-local.ps1
├─ src/
├─ .env
├─ .env.local.tpl
├─ .env.production
├─ 一键部署.bat
├─ package.json
├─ pnpm-lock.yaml
├─ vite.config.ts
└─ README.md
```

## 环境要求

- `Node.js 18+`
- `pnpm 8+`
- `Python 3.10+`
- `MySQL 5.7+` 或 `MySQL 8.x`

## 快速开始

### 0. Windows 一键本地部署

Windows 本地演示环境可直接双击运行：

```text
一键部署.bat
```

脚本会依次完成：

- 检查 `mysql`、`node`、`pnpm`、`python` 命令是否可用
- 在创建数据库前提示输入 MySQL 地址、用户名、数据库名和密码；数据库名会同步写入后端 `greenfianace_server/.env` 的 `DB_NAME`
- 创建用户指定的数据库（默认 `green_finance`）并导入 `greenfianace_server/green_finance.sql`、`greenfianace_server/city_carbon_gdp.sql`
- 询问是否启用 AI 助手；启用时需要输入 DeepSeek API Key
- 自动生成根目录 `.env` 和 `greenfianace_server/.env`
- 安装前后端依赖，并分别启动 FastAPI 后端和 Vite 前端

如果不启用 AI 助手，AI 问答、页面总结、Tooltip AI 解读、流式问答不可用；地图、图表、数据库查询和预测展示仍可使用。

数据库名以一键部署生成的 `greenfianace_server/.env` 中 `DB_NAME` 为准。若输入非默认数据库名，脚本会二次确认，并保证建库、导入 SQL、后端连接三者一致；后续不要手动把 `DB_NAME` 改成未导入数据的库。

> 源码提交包只包含少量样例 SQL 时，一键部署脚本会自动导入样例数据并提示说明。完整演示请先按概要表中的完整数据集链接恢复完整 SQL 或数据文件。

推荐启动顺序：

1. 导入 MySQL 数据
2. 启动后端服务
3. 启动前端服务

### 1. 导入数据库

项目默认使用数据库 `green_finance`。

主要 SQL 文件：

- `greenfianace_server/green_finance.sql`
  作用：绿色金融、省级数据、省级能源消费、预测数据等基础表
- `greenfianace_server/city_carbon_gdp.sql`
  作用：市级 GDP、碳排放、能源消费联动数据表 `city_carbon_gdp`

示例：

```bash
cd greenfianace_server
mysql -u root -p < green_finance.sql
mysql -u root -p < city_carbon_gdp.sql
```

如果你使用的是 PowerShell，也可以执行：

```powershell
Set-Location greenfianace_server
Get-Content .\green_finance.sql -Raw | mysql -u root -p
Get-Content .\city_carbon_gdp.sql -Raw | mysql -u root -p
```

说明：

- `green_finance.sql` 负责基础业务表，包含 `province_energy_consumption` 等省级能源消费数据
- `city_carbon_gdp.sql` 负责市级 GDP / 碳排放 / 能源消费数据库化
- 碳排放+GDP底色页当前的市级数据已走数据库，不再依赖 Excel

### 2. 配置后端环境变量

后端会读取：

```text
greenfianace_server/.env
```

可以先复制模板：

```bash
cd greenfianace_server
cp .env.example .env
```

Windows PowerShell：

```powershell
Set-Location greenfianace_server
Copy-Item .env.example .env
```

推荐配置如下：

```env
DB_HOST=127.0.0.1
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=green_finance
DB_CHARSET=utf8mb4

DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT=60
```

字段说明：

- `DB_HOST`：MySQL 地址
- `DB_USER`：MySQL 用户名
- `DB_PASSWORD`：MySQL 密码
- `DB_NAME`：数据库名，默认 `green_finance`
- `DB_CHARSET`：推荐 `utf8mb4`
- `DEEPSEEK_API_KEY`：AI 助手调用所需密钥
- `DEEPSEEK_BASE_URL`：DeepSeek 接口地址
- `DEEPSEEK_MODEL`：默认模型名
- `DEEPSEEK_TIMEOUT`：后端请求超时时间，单位秒

注意：

- 根目录下的 `.env` 是给前端 Vite 用的
- `greenfianace_server/.env` 才是给 FastAPI 后端用的
- 这两个文件不要混用

### 3. 启动后端

```bash
cd greenfianace_server
python -m venv .venv
```

激活虚拟环境：

- Windows PowerShell：`.venv\Scripts\Activate.ps1`
- Windows CMD：`.venv\Scripts\activate`
- macOS / Linux：`source .venv/bin/activate`

安装依赖：

```bash
pip install -r requirements.txt
```

启动服务：

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

启动后默认接口基地址：

```text
http://127.0.0.1:8000/api
```

### 3.1 运行新预测模型所需文件

新预测链路已切换为 `greenfianace_server/analysis_models/prediction_model.py`，默认实现为：

- `STIRPAT 面板预测`
- `系统动力学情景仿真`
- `组合预测`
- `Logit 风险预警`

说明：当前主路径已收敛为“预处理 + 当前预测模型 + API/前端展示”链路。旧版 `SDM + LSTM` 预测实现，以及旧的基准回归、DID、中介效应、异质性、稳健性和空间模型模块已从仓库中移除，不再作为默认运行入口或作品源码的一部分。

运行前至少需要以下文件存在：

- 原始输入文件
  - `greenfianace_server/data/model_inputs_v2/省级绿色金融指数+碳排放+能源+DID数据(剔除西藏）.xlsx`
  - `greenfianace_server/data/model_inputs_v2/地级市绿色金融+碳排放+能源+DID数据（剔除西藏）.xlsx`
  - `greenfianace_server/data/model_inputs_v2/中国省级行政区经纬度表.xlsx`
- 预处理产物
  - `greenfianace_server/empirical_results/province/中国绿色金融-能源平衡面板数据集(最终版).csv`
  - `greenfianace_server/empirical_results/city/中国绿色金融-能源平衡面板数据集(最终版).csv`

如果预处理 CSV 不存在，建议运行顺序是：

1. 先执行 `analysis_models/main.py` 的预处理步骤生成最终清洗数据集。
2. 再运行新的预测步骤生成 `prediction_results/` 下的三类情景文件、评估文件和 STIRPAT 结果。
3. 最后启动 FastAPI 和前端页面读取这些离线产物。

切换运行层级时不需要手改 `config.py`，可以直接通过环境变量控制：

```powershell
$env:GF_RUN_LEVEL='province'
python greenfianace_server/analysis_models/prediction_model.py

$env:GF_RUN_LEVEL='city'
python greenfianace_server/analysis_models/prediction_model.py
```

### 4. 启动前端

回到项目根目录后执行：

```bash
pnpm install
pnpm run serve
```

默认访问地址：

```text
http://localhost:5173/vue3-vite5-dashboard/
```

说明：

- 当前 `.env` 中默认配置了 `VITE_BASE=/vue3-vite5-dashboard/`
- `vite.config.ts` 已配置本地 `/api` 代理到 `http://127.0.0.1:8000`
- 如果你修改了 `VITE_BASE`，前端访问地址也要跟着调整

## 前端环境变量

根目录 `.env` / `.env.development` / `.env.production` 用于前端配置。

常见字段：

```env
VITE_APP_TITLE=绿色金融与区域碳减排空间协同智能测算平台
VITE_BASE=/vue3-vite5-dashboard/
VITE_APP_DOMAIN=/api
```

字段说明：

- `VITE_APP_TITLE`：页面标题
- `VITE_BASE`：前端部署基础路径
- `VITE_APP_DOMAIN`：本地开发时的接口前缀

## 当前功能说明

### 1. 绿色金融综合指数

- 全国省级地图着色
- 下钻到省内市级，碳排放+GDP底色页已复用同类下钻体验
- 侧边栏排行
- 雷达图联动展示
- 地图悬浮框保留绿色金融七维指标，不展示能源消费明细

### 2. 碳排放+GDP底色

- 默认显示碳排放地图
- 可一键切换到 `GDP 地图模式`
- 可切换到 `GDP 和碳排放组合图`
- 支持全国省级到省内市级下钻
- 地图使用 3D 底色挤出效果，省级和市级交互体验与绿色金融页保持一致
- 地图悬浮框支持滚动查看完整数据和 AI 分析
- 省级悬浮框展示能源消费总量、强度、人均能源消耗及能源消费分项；如果当前年份分项为 0，会回退到该省最近一个非 0 年份并显示明细年份
- 市级悬浮框展示 GDP、产业结构、碳排放和能源消费相关指标
- 市级数据来自数据库 `city_carbon_gdp`

### 3. 碳排放强度预测

- 首页 `碳排放强度预测` Tab 当前挂载 `src/views/home/BizCarbonPredictionV3.vue`
- 支持省级预测、市级预测、区域选择，前端固定展示 `组合预测`
- 后端官方情景键仍为 `baseline / lowCarbon / optimized`，前端展示为 `保守 / 基准 / 乐观 / 自定义`
- 历史观测与 2025-2027 年预测结果在同一张折线图中展示
- 前端展示层将碳排放强度主指标正向化，但预测段直接展示当前模型输出，不再做自适应缩放
- 页面保留统一的组合预测展示，不恢复来源切换；主交互改为 `保守 / 基准 / 乐观 / 自定义` 四态切换
- AI 上下文中保留 `raw*` 字段用于追溯，并固定使用组合预测口径
- Tooltip 和右侧结论卡使用同一展示口径，避免同一指标出现正负或尺度不一致

### 4. AI 助手

项目已接入 AI 助手，支持：

- 当前页面问答
- 当前页面总结
- 流式输出
- 页面级工具调用

后端接口包括：

```text
POST /api/ai/chat
POST /api/ai/summary
POST /api/ai/chat/stream
POST /api/ai/summary/stream
```

## 常用脚本

在项目根目录执行：

```bash
pnpm run serve
pnpm run build
pnpm run preview
pnpm run lint
```

含义：

- `serve`：启动前端开发环境
- `build`：类型检查并构建生产包
- `preview`：本地预览构建结果
- `lint`：执行 ESLint

## 生产构建

```bash
pnpm run build
```

构建产物输出到：

```text
dist/
```

补充说明：

- 项目启用了 `vite-plugin-compression`
- 构建时会生成 `.gz` 压缩文件
- 若部署在子路径下，服务器配置需要与 `VITE_BASE` 保持一致

## 部署建议

### 前端

- 将 `dist/` 部署到 Nginx、Apache 或其他静态资源服务器
- 建议开启 `gzip` 或 `brotli`
- 若使用 `.gz` 文件，需正确配置 `Content-Encoding`

### 后端

生产环境建议使用：

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

然后通过反向代理将前端的 `/api` 转发到 FastAPI 服务。

## 常见问题

### 1. 后端提示数据库连接失败

优先检查：

- `greenfianace_server/.env` 是否已创建
- `DB_HOST`、`DB_USER`、`DB_PASSWORD`、`DB_NAME` 是否正确
- MySQL 服务是否已启动
- `green_finance.sql` 和 `city_carbon_gdp.sql` 是否已导入

### 2. 出现 `Access denied ... using password: NO`

这通常表示后端没有正确读取 `greenfianace_server/.env`，或者 `DB_PASSWORD` 为空。

### 3. 出现 `cryptography package is required`

在后端虚拟环境中重新安装依赖：

```bash
pip install -r requirements.txt
```

### 4. 前端能打开，但接口 404 或代理失败

请检查：

- 后端是否运行在 `127.0.0.1:8000`
- 是否先启动后端再启动前端
- `vite.config.ts` 中 `/api` 代理是否被改动

### 5. 出现 `pnpm` 无法识别

安装方式任选其一：

```bash
npm install -g pnpm
```

或：

```bash
corepack enable
corepack prepare pnpm@8 --activate
```

安装后重新打开终端再执行：

```bash
pnpm -v
pnpm install
```

### 6. 出现 `[plugin:vite:css] Preprocessor dependency "less" not found`

在项目根目录执行：

```bash
pnpm add -D less
pnpm install
pnpm run serve
```

### 7. 构建时报 `spawn EPERM`

这通常不是项目代码问题，而是本机权限、杀毒软件或受限目录拦截了 `esbuild` 子进程。

可优先尝试：

- 使用普通本机终端重新执行构建
- 检查安全软件是否拦截 `node` / `esbuild`
- 避免在受限沙箱或只读同步目录中构建

### 8. AI 助手提示 API Key 未配置

请检查：

- 是否已创建 `greenfianace_server/.env`
- `DEEPSEEK_API_KEY` 是否已填写
- 后端是否已经重启

### 9. DeepSeek 请求出现 SSL EOF 错误

如果出现类似：

```text
DeepSeek 请求失败: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol
```

通常表示 HTTPS 连接在读取响应时被中途断开，不是 API Key 未配置。可优先检查：

- 当前网络是否稳定
- 代理、VPN、校园网或公司网关是否拦截 HTTPS
- `DEEPSEEK_BASE_URL` 是否正确
- 后端是否可以正常访问外网
- 稍后重试或切换网络环境

## 开发补充说明

- 地图 GeoJSON 静态资源位于 `public/geojson/`
- 当前地图主交互以省级和市级为主
- 县级相关功能已移除，不再作为当前默认链路
- 碳排放+GDP底色页市级 GDP / 碳排放 / 能源消费联动数据来自 `city_carbon_gdp`
- 碳排放+GDP底色页省级能源消费明细来自 `province_energy_consumption`
- 预测页显示层正向化只影响用户可见的碳排放强度展示值，不改变后端预测接口和模型原始结果

## 预测页补充说明（2026-04）

- 预测页当前仍然只展示 `组合预测`，不恢复 `STIRPAT / 系统动力学` 来源切换。
- 省级和市级统一改成 `保守 / 基准 / 乐观 / 自定义` 四态切换。
- `自定义` 固定基于 `基准` 官方曲线，统一使用 6 个驱动项：`人口 / 富裕度 / 技术或能耗 / 产业结构 / 能源结构 / 绿色金融`。
- 这套调节不是后端重新训练或正式重算，而是基于 `STIRPAT` 弹性系数，对当前 `组合预测` 做前端近似推演。
- `自定义` 模式下会同时展示 `基准官方预测` 与 `自定义调节曲线`；对比线和“官方情景区间”保持官方组合预测结果不变。
- 页面展示层仍然保持碳排放强度的绝对值口径，参数调节计算则基于原始预测值完成，再进入展示层。

## License

MIT
