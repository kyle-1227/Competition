# 绿色金融与区域碳减排空间协同智能测算平台

基于 `Vue 3 + Vite 5 + TypeScript + AntV L7 + ECharts + FastAPI + MySQL` 的数据可视化大屏项目，用于展示绿色金融、碳排放空间分布、碳排放强度预测，以及 GDP 与碳排放联动分析。

## 项目概览

当前首页包含 3 个主页面：

- `绿色金融综合指数`
- `碳排放底色`
- `碳排放强度预测`

其中：

- 碳排放页支持两种地图指标视图：`碳排放`、`GDP`
- 碳排放页内置 `GDP 和碳排放组合图`
- 宏观经济不再作为独立 Tab，而是并入碳排放页
- 绿色金融页和碳排放页当前都只保留 `全国省级 -> 省内市级` 两级下钻

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
├─ src/
├─ .env
├─ .env.local.tpl
├─ .env.production
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

推荐启动顺序：

1. 导入 MySQL 数据
2. 启动后端服务
3. 启动前端服务

### 1. 导入数据库

项目默认使用数据库 `green_finance`。

主要 SQL 文件：

- `greenfianace_server/green_finance.sql`
  作用：绿色金融、省级数据、预测数据等基础表
- `greenfianace_server/city_carbon_gdp.sql`
  作用：市级 GDP 与碳排放联动数据表 `city_carbon_gdp`

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

- `green_finance.sql` 负责基础业务表
- `city_carbon_gdp.sql` 负责市级 GDP / 碳排放数据库化
- 碳排放页当前的市级数据已走数据库，不再依赖 Excel

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
- 下钻到省内市级
- 侧边栏排行
- 雷达图联动展示

### 2. 碳排放底色

- 默认显示碳排放地图
- 可一键切换到 `GDP 地图模式`
- 可切换到 `GDP 和碳排放组合图`
- 支持全国省级到省内市级下钻
- 地图使用颜色表达，不再使用 3D 柱体
- 市级数据来自数据库 `city_carbon_gdp`

### 3. 碳排放强度预测

- 预测参数调节
- 历史序列与预测结果展示
- 宏观统计联动接口支持

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

## 开发补充说明

- 地图 GeoJSON 静态资源位于 `public/geojson/`
- 当前地图主交互以省级和市级为主
- 县级相关功能已移除，不再作为当前默认链路
- 碳排放页市级 GDP / 碳排放联动数据来自 `city_carbon_gdp`

## License

MIT
