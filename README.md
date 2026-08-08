# 绿色金融与区域碳减排空间协同智能测算平台

本项目是一个面向绿色金融、区域碳排放与能源协同分析的数据可视化平台。前端提供全国省级到省内市级的地图下钻、指标对比、趋势分析和预测交互；后端负责 MySQL 数据查询、实证结果读取、预测计算以及可选的 DeepSeek AI 解读。

## 主要功能

- 绿色金融综合指数：展示省市绿色金融指标、排名、趋势和空间分布。
- 碳排放与 GDP：切换碳排放或 GDP 地图底色，并查看二者联动关系。
- 碳排放强度预测：展示组合预测、情景结果和自定义驱动因素测算。
- 地图下钻：支持“全国省级 → 省内市级”两级浏览。
- AI 助手：可选启用问答、页面总结、图表提示词解读和流式回答。
- 实证结果：保留省级、市级空间计量、稳健性检验、模型评估和情景预测结果。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite 5、Element Plus、ECharts、AntV L7、Pinia、Vue Router |
| 后端 | FastAPI、Uvicorn、PyMySQL、DBUtils、python-dotenv、httpx |
| 数据与模型 | MySQL 8、pandas、NumPy、scikit-learn、statsmodels、linearmodels、libpysal、esda |
| AI | DeepSeek API，由 FastAPI 后端代理调用 |
| 工程化 | pnpm、ESLint、Prettier、Commitlint、Husky |

## 仓库结构

以下为清理后的源码结构；不展示 Git 内部目录，也不包含安装或构建后才生成的依赖、虚拟环境和产物目录。

```text
.
├─ .husky/                         Git 提交钩子
├─ .vscode/                        推荐的编辑器配置
├─ greenfianace_server/            FastAPI 后端、数据、模型与 SQL
│  ├─ analysis_models/             离线分析和预测模型代码
│  ├─ data/
│  │  ├─ model_inputs_v2/          省市模型输入工作簿
│  │  └─ 2000-2024县级碳排放(1).xlsx
│  ├─ empirical_results/           省市实证、空间计量与预测结果
│  ├─ knowledge/
│  │  ├─ 01_indicator_dictionary/  指标字典 JSON
│  │  ├─ 02_page_guidance/         页面语义 JSON
│  │  ├─ 04_result_cards/          结果卡片 JSON
│  │  └─ 05_prompt_templates/      AI 提示词 TXT
│  ├─ ai_agent.py                  AI 工具调用编排
│  ├─ ai_context.py                AI 页面上下文组装
│  ├─ ai_knowledge.py              知识库加载
│  ├─ ai_service.py                DeepSeek 请求封装
│  ├─ ai_tools.py                  AI 可调用的数据工具
│  ├─ ai_types.py                  AI 数据类型
│  ├─ city_carbon_gdp.sql          市级碳排放与 GDP 完整数据
│  ├─ data_service.py              MySQL 数据服务
│  ├─ green_finance.sql            绿色金融与省级业务完整数据
│  ├─ predict_results_service.py   预测与实证结果服务
│  └─ server.py                    FastAPI 入口
├─ presets/                        前端预设配置
├─ public/                         图标与全国、省级 GeoJSON
├─ src/                            Vue 前端业务源码
│  ├─ api/                         HTTP 客户端、接口与类型
│  ├─ assets/                      字体和全局样式
│  ├─ components/                  公共组件
│  ├─ router/                      路由配置
│  ├─ utils/                       通用工具
│  └─ views/                       大屏页面、AI 面板与业务 hooks
├─ .commitlintrc.js                Commitlint 配置
├─ .editorconfig                   编辑器基础规范
├─ .env.example                    可提交的环境配置模板
├─ .eslintignore                   ESLint 忽略规则
├─ .eslintrc-auto-import.json      自动导入类型规则
├─ .eslintrc.js                    ESLint 配置
├─ .gitattributes                  Git 属性
├─ .gitignore                      生成物与私密文件忽略规则
├─ .prettierignore                 Prettier 忽略规则
├─ docker.yaml                     前端构建平台配置
├─ index.html                      Vite HTML 入口
├─ package.json                    前端依赖与命令
├─ pnpm-lock.yaml                  前端依赖锁文件
├─ prettier.config.js              Prettier 配置
├─ requirements.txt                全仓唯一 Python 依赖清单
├─ tsconfig.json                   TypeScript 配置
├─ vite.config.ts                  Vite 构建与本地代理配置
├─ deploy.ps1                      Windows 本地一键部署脚本
└─ README.md                       唯一项目说明文档
```

首次安装或构建后会生成 `node_modules/`、`dist/` 和 `greenfianace_server/.venv/`。这些目录均已忽略，不属于源码提交内容。仓库只跟踪根目录 `.env.example` 和 `requirements.txt`；本地 `.env` 由开发者自行保留，不提交到 Git。

> `greenfianace_server` 是项目沿用的目录名，虽然拼写不是标准的 `greenfinance_server`，但为避免破坏现有路径和接口，本次未重命名。

## 环境要求

- Windows 10 或 Windows 11，使用 Windows PowerShell 5.1 或 PowerShell 7。
- Node.js 18 或更高版本。
- pnpm 8 或更高版本。
- Python 3.10 或更高版本。
- MySQL Server 与 MySQL Client 8.0 或更高版本，`mysql.exe` 需加入 `PATH`。
- 默认端口：前端 `5173`，后端 `8002`，MySQL `3306`。

完整 SQL 使用了 MySQL 8 的字符集排序规则，不能保证兼容 MySQL 5.7。

## Windows 一键部署

先在项目根目录执行只读检查：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\deploy.ps1 -DryRun
```

检查通过后执行完整部署：

```powershell
.\deploy.ps1
```

脚本会依次完成：

1. 检查项目路径、完整 SQL、Node.js、pnpm、Python 和 MySQL Client。
2. 使用固定 MySQL 配置 `127.0.0.1`、用户 `root`、数据库 `green_finance`，只提示输入 MySQL 密码。
3. 首次运行且缺少 `.env` 时从 `.env.example` 生成本地配置，然后读取其中的可选 DeepSeek 配置，不在部署过程中额外询问。
4. 检查目标数据库，创建数据库并导入两份完整 SQL。
5. 保留已有的本地 `.env`，不覆盖其中内容，只将本次输入的数据库密码临时注入后端子进程。
6. 根据依赖指纹决定是否安装前端和后端依赖。
7. 检查 `8002`、`5173` 端口，并在两个可见 PowerShell 窗口中启动服务。

启动地址：

- 前端：`http://localhost:5173/vue3-vite5-dashboard/`
- 后端接口：`http://127.0.0.1:8002/api`
- FastAPI 文档：`http://127.0.0.1:8002/docs`

### 一键部署参数

| 参数 | 作用 |
| --- | --- |
| `-DryRun` | 只检查路径、文件、工具版本、SQL 重建表、依赖状态、端口和启动命令；不提示输入密码，不写文件，不连接数据库，不安装依赖，不启动服务。 |
| `-ForceInstall` | 忽略依赖指纹，强制执行 `pnpm install --frozen-lockfile` 和后端 `pip install`。 |

前端指纹由 `package.json + pnpm-lock.yaml` 计算，保存在 `node_modules/` 内；后端指纹由 `requirements.txt + 虚拟环境 Python 版本` 计算，保存在 `greenfianace_server/.venv/` 内。依赖目录缺失、指纹缺失或输入变化时会自动重装。

### 重复部署与数据库覆盖警告

两份 SQL 包含 `DROP TABLE IF EXISTS`。目标数据库已存在时，脚本会动态解析 SQL，并展示当前将被删除和重建的表，通常包括：

- `city_carbon_gdp`
- `city_green_finance`
- `descriptive_statistics`
- `province_energy_consumption`
- `province_green_finance`
- `province_panel_data`
- `sdm_coefficients`

首次部署且目标数据库不存在时，完整部署只需要输入 MySQL 密码。目标数据库已存在时，出于防止误删数据的安全要求，必须再次输入完整数据库名确认重建；直接回车或输入其他内容会以退出码 `2` 取消，且不会写文件、导入 SQL、安装依赖或启动服务。请勿对含有需保留数据的数据库执行该脚本。

脚本退出码：`0` 表示成功，`1` 表示失败，`2` 表示用户取消。

## 手动部署

### 1. 创建并导入数据库

默认数据库名为 `green_finance`。在项目根目录执行：

```powershell
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS green_finance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p --default-character-set=utf8mb4 green_finance -e "source greenfianace_server/green_finance.sql"
mysql -u root -p --default-character-set=utf8mb4 green_finance -e "source greenfianace_server/city_carbon_gdp.sql"
```

第二份 SQL 内含 `USE green_finance`。一键部署默认固定使用 `green_finance`；如需自定义数据库名，请同步修改根目录 `.env` 的 `DB_NAME` 和 `deploy.ps1` 顶部的 `$script:DatabaseName`，脚本会在系统临时目录生成替换后的 SQL，并在成功或失败后自动清除。

### 2. 配置并启动后端

后端会读取根目录 `.env`。首次手动部署先复制模板：

```powershell
Copy-Item .\.env.example .\.env
```

然后建议将密码和 API Key 设置为当前 PowerShell 进程变量：

```powershell
$env:DB_PASSWORD = 'your_mysql_password'
$env:DEEPSEEK_API_KEY = ''

python -m venv .\greenfianace_server\.venv
.\greenfianace_server\.venv\Scripts\python.exe -m pip install -r .\requirements.txt

Set-Location .\greenfianace_server
.\.venv\Scripts\python.exe -m uvicorn server:app --reload --host 0.0.0.0 --port 8002
```

若选择直接修改根目录 `.env`，请勿提交该文件或其中的真实数据库密码、API Key。DeepSeek 配置可以留空。

### 3. 安装并启动前端

另开一个 PowerShell 窗口，在项目根目录执行：

```powershell
pnpm install --frozen-lockfile
pnpm run dev
```

Vite 会将 `/api` 以及带项目基础路径的 API 请求代理到 `http://127.0.0.1:8002`。

## 环境变量

### 根目录 `.env.example` 与本地 `.env`

仓库提交根目录 `.env.example` 作为模板，真实运行配置使用同级本地 `.env`。`.env` 已加入 `.gitignore`，不会被 Git 跟踪；前后端统一读取根目录 `.env`，不再使用后端子目录 `.env`。Vite 只会把 `VITE_` 前缀变量暴露给浏览器，后端变量不会进入前端构建。

| 变量 | 必需 | 说明 |
| --- | --- | --- |
| `VITE_APP_TITLE` | 是 | 页面标题 |
| `VITE_BASE` | 是 | 部署基础路径，当前为 `/vue3-vite5-dashboard/` |
| `VITE_APP_DOMAIN` | 是 | API 前缀，当前为 `/api` |
| `SERVER_PORT` | 是 | 后端端口，项目统一为 `8002` |
| `DB_HOST` | 是 | MySQL 地址，默认 `127.0.0.1` |
| `DB_USER` | 是 | MySQL 用户 |
| `DB_PASSWORD` | 是 | MySQL 密码 |
| `DB_NAME` | 是 | 已导入完整 SQL 的数据库名 |
| `DB_CHARSET` | 是 | 推荐 `utf8mb4` |
| `DEEPSEEK_API_KEY` | 否 | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | 否 | 默认 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 否 | 默认 `deepseek-chat` |
| `DEEPSEEK_TIMEOUT` | 否 | 请求超时秒数，默认 `60` |

`.env.example` 中的 `DB_PASSWORD` 和 `DEEPSEEK_API_KEY` 默认留空。一键部署不会覆盖已有 `.env`，只在创建后端进程时临时注入本次输入的 MySQL 密码；DeepSeek 配置直接读取本地 `.env` 或当前进程环境变量。关闭后端窗口后部署脚本注入的密码不会持久化。

## 数据库、模型与知识库

### 完整 SQL

- `greenfianace_server/green_finance.sql`：绿色金融、省级能源消费、面板数据、描述性统计和空间模型系数等业务表。
- `greenfianace_server/city_carbon_gdp.sql`：市级 GDP、碳排放、能源消费和政策标识数据。

仓库不再包含样例 SQL 或提交包回退逻辑；部署必须使用上述两份完整 SQL。

### 模型输入与实证结果

- `greenfianace_server/data/model_inputs_v2/`：省级、市级模型输入工作簿和行政区经纬度表。
- `greenfianace_server/data/2000-2024县级碳排放(1).xlsx`：县级碳排放原始数据。
- `greenfianace_server/analysis_models/`：数据加载、预处理和预测模型代码。
- `greenfianace_server/empirical_results/`：省市面板、回归表、空间权重、模型检验、稳健性检验、情景预测和模型评估结果。预测页面会直接读取其中的 CSV 文件。

### AI 知识库

- `01_indicator_dictionary/`：省、市、县指标定义。
- `02_page_guidance/`：页面功能、数据范围和解读引导。
- `04_result_cards/`：省市实证结果卡片。
- `05_prompt_templates/`：聊天、总结和 Tooltip 提示词模板。

这些 JSON 和 TXT 文件参与运行，不属于说明文档，不应删除。

## 核心指标单位

下表由原数据单位说明提炼而来。不同来源文件可能存在字段缩放或展示换算，二次分析时仍应同时核对具体数据文件、SQL 字段和接口转换逻辑。

| 适用层级 | 指标 | 单位或编码 |
| --- | --- | --- |
| 省、市 | 绿色金融综合指数 | 无量纲，标准化后范围 `0–1` |
| 省 | 绿色信贷规模 | 亿元 |
| 市 | 绿色保险保费收入 | 万元 |
| 省、市、县 | 碳排放量 | 万吨 CO₂ |
| 省、市、县 | 碳排放强度 | 吨 CO₂/万元 GDP |
| 省、市 | 能源消费总量 | 万吨标准煤 |
| 省、市 | 能源强度 | 吨标准煤/万元 GDP |
| 省 | 人均能源消耗 | 吨标准煤/人 |
| 市 | 清洁能源占比 | % |
| 省、市、县 | 绿色金融、环保税、碳交易或所属试点标识 | `0` 表示否，`1` 表示是 |
| 市 | 长江经济带标识 | `0` 表示非沿线，`1` 表示沿线 |
| 省、市 | 地区生产总值 GDP | 亿元 |
| 省、市 | 人均 GDP | 万元/人 |
| 省 | 第二产业增加值占 GDP 比重 | % |

## AI 助手的可选边界

未配置 `DEEPSEEK_API_KEY` 时，下列功能不可用：

- AI 对话与流式问答
- 页面自动总结
- Tooltip AI 解读
- 依赖大模型生成的分析文本

地图、图表、MySQL 查询、排名、下钻、实证结果和预测展示不依赖 DeepSeek，仍可正常使用。API Key 应通过根目录 `.env` 或后端进程环境变量提供，不要提交到 Git；一键部署不会询问或写入 API Key。

## 常用开发命令

在项目根目录执行：

| 命令 | 作用 |
| --- | --- |
| `pnpm run dev` | 启动 Vite 开发服务器 |
| `pnpm run build` | TypeScript 检查并生成生产构建到 `dist/` |
| `pnpm run preview` | 本地预览生产构建 |
| `pnpm run lint` | 检查 `src/` 中的 ESLint 问题 |
| `.\deploy.ps1 -DryRun` | 无副作用检查部署条件 |
| `.\deploy.ps1 -ForceInstall` | 完整部署并强制重装依赖 |

后端开发模式：

```powershell
Set-Location .\greenfianace_server
.\.venv\Scripts\python.exe -m uvicorn server:app --reload --host 0.0.0.0 --port 8002
```

## 生产构建

前端构建：

```powershell
pnpm install --frozen-lockfile
pnpm run build
```

构建输出位于 `dist/`，该目录不纳入 Git。部署到子路径时，Web 服务器需与 `VITE_BASE=/vue3-vite5-dashboard/` 保持一致。

后端生产启动示例：

```powershell
Set-Location .\greenfianace_server
.\.venv\Scripts\python.exe -m uvicorn server:app --host 0.0.0.0 --port 8002
```

生产环境应通过反向代理托管前端静态文件，并将 `/api` 转发到后端；数据库密码和 DeepSeek API Key 应由部署环境安全注入。

## 故障排查

### PowerShell 禁止执行脚本

仅对当前终端临时放开：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

### 找不到 `mysql`、`node`、`pnpm` 或 `python`

先执行 `.\deploy.ps1 -DryRun` 查看命令路径和版本。安装对应工具后重新打开终端，确认其可由 `PATH` 访问。

### 数据库导入失败

- 确认 MySQL 8 服务已启动，账号有建库、建表和写入权限。
- 确认密码正确，目标数据库名只包含字母、数字和下划线。
- 确认两份完整 SQL 文件未缺失或被截断。
- 对已有数据库重复部署前先备份需保留的数据。

### `8002` 或 `5173` 端口被占用

脚本会在启动前停止并报告端口。关闭占用端口的旧进程后重新运行；前后端当前固定使用这两个端口，不建议只修改一侧。

### 前端能打开但接口失败

- 确认后端可访问 `http://127.0.0.1:8002/docs`。
- 确认根目录 `.env` 或后端进程环境变量中的数据库名与实际导入目标一致。
- 确认从 `http://localhost:5173/vue3-vite5-dashboard/` 访问，而不是省略基础路径。
- 检查 `vite.config.ts` 中 `/api` 代理仍指向 `127.0.0.1:8002`。

### 依赖变化后没有重新安装

正常情况下锁文件或 Python 版本变化会触发指纹更新；如本地依赖目录损坏，执行：

```powershell
.\deploy.ps1 -ForceInstall
```

## 许可证

`package.json` 中声明本项目使用 MIT License。对外分发前，请同时核对数据集、地图和第三方依赖各自的授权条件。
