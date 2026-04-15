# 绿色金融与区域碳减排空间协同智能测算平台

基于 Vue 3、Vite 5、AntV L7、ECharts 和 FastAPI 的数据可视化大屏项目，用于展示绿色金融、区域碳减排、碳排放强度预测和宏观经济联动分析。

## 功能概览

- 绿色金融综合指数：全国、省、市、县多级地图下钻，Top10 排行和七维雷达图联动展示
- 碳排放底色：省级碳排放空间分布与年度切换
- 碳排放强度预测：基于 SDM 系数的情景推演与趋势图
- 宏观经济：GDP 与碳排放双轴联动分析

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite 5、AntV L7、ECharts、Element Plus、Vue Router、Pinia |
| 后端 | FastAPI、Uvicorn、PyMySQL、DBUtils、python-dotenv |
| 数据库 | MySQL 5.7+ / 8.x |

## 目录结构

```text
.
├─ greenfianace_server/
│  ├─ analysis_models/
│  ├─ green_finance.sql
│  ├─ requirements.txt
│  ├─ server.py
│  └─ .env                # 需要手动创建，不要提交到版本库
├─ public/
├─ src/
├─ .env
├─ package.json
├─ pnpm-lock.yaml
├─ vite.config.ts
└─ README.md
```

## 环境要求

- Node.js 18 及以上
- pnpm 8 及以上
- Python 3.10 及以上
- MySQL 5.7 或 8.x

## 一、本地部署步骤

建议启动顺序：

1. 准备并导入 MySQL 数据库
2. 启动后端服务
3. 启动前端服务

### 1. 准备数据库

项目后端默认连接名为 `green_finance` 的 MySQL 数据库。

SQL 文件位置：

```text
greenfianace_server/green_finance.sql
```

导入示例：

```bash
cd greenfianace_server
mysql -u root -p < green_finance.sql
```

如果你使用的是 PowerShell，也可以用：

```powershell
cd greenfianace_server
Get-Content .\green_finance.sql -Raw | mysql -u root -p
```

说明：

- SQL 文件内包含建库、建表和初始化数据
- 默认数据库名为 `green_finance`
- 请确认导入账号对该数据库有读写权限

### 2. 启动后端服务

后端目录：

```bash
cd greenfianace_server
```

创建虚拟环境：

```bash
python -m venv .venv
```

激活虚拟环境：

- Windows PowerShell：`.\.venv\Scripts\Activate.ps1`
- Windows CMD：`.venv\Scripts\activate`
- macOS / Linux：`source .venv/bin/activate`

安装依赖：

```bash
pip install -r requirements.txt
```

#### 重要：`greenfianace_server/.env` 需要手动创建

这个文件不会自动生成，后端也不会读取前端根目录下的 `.env`。
你需要在 `greenfianace_server` 目录下手动创建一个 `.env` 文件。

文件路径：

```text
greenfianace_server/.env
```

推荐内容如下：

```env
DB_HOST=127.0.0.1
DB_USER=root
DB_PASSWORD=你的MySQL密码
DB_NAME=green_finance
DB_CHARSET=utf8mb4
DEEPSEEK_API_KEY=你的DeepSeek_API_Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT=60
```

各字段含义：

- `DB_HOST`：数据库地址，默认本机可写 `127.0.0.1`
- `DB_USER`：MySQL 用户名
- `DB_PASSWORD`：MySQL 密码
- `DB_NAME`：数据库名，默认是 `green_finance`
- `DB_CHARSET`：字符集，建议 `utf8mb4`
- `DEEPSEEK_API_KEY`：DeepSeek API Key，仅后端读取，前端不会暴露
- `DEEPSEEK_BASE_URL`：DeepSeek 接口基地址，默认 `https://api.deepseek.com`
- `DEEPSEEK_MODEL`：默认模型，当前项目建议 `deepseek-chat`
- `DEEPSEEK_TIMEOUT`：后端代理调用超时时间，单位秒

注意：

- 根目录下的 `.env` 是给 Vite 前端用的，不会被 `greenfianace_server/server.py` 读取
- 后端代码通过 `load_dotenv(ROOT / ".env")` 读取 `greenfianace_server/.env`
- 如果缺少这个文件，后端可能会以默认空密码尝试连接数据库，导致连接失败
- 如果只想快速对照字段，可以直接复制 `greenfianace_server/.env.example` 为 `greenfianace_server/.env` 后再修改真实值

启动后端：

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

启动成功后，接口地址默认是：

```text
http://127.0.0.1:8000/api
```

#### AI 助手后端接口

本项目已接入 DeepSeek 后端代理，前端不会直接请求 DeepSeek，也不会暴露 API Key。

后端新增接口如下：

```text
POST /api/ai/chat
POST /api/ai/summary
```

接口说明：

- `/api/ai/chat`：基于当前页面上下文进行答疑
- `/api/ai/summary`：基于当前页面、年份、省份和已加载数据生成总结文本
- 两个接口都走本项目 FastAPI 服务代理调用 DeepSeek，因此必须先正确配置 `greenfianace_server/.env`

### 3. 启动前端服务

回到项目根目录：

```bash
cd ..
```

#### 先确认 `pnpm` 已安装

如果执行 `pnpm install` 时出现下面这类报错：

```text
pnpm : 无法将“pnpm”项识别为 cmdlet、函数、脚本文件或可运行程序的名称
```

说明当前机器还没有可用的 `pnpm`。

可任选一种方式安装：

```bash
npm install -g pnpm
```

或使用 Node.js 自带的 Corepack：

```bash
corepack enable
corepack prepare pnpm@8 --activate
```

安装完成后，可先检查版本：

```bash
pnpm -v
```

#### 安装前端依赖

请务必在项目根目录执行，不要在 `greenfianace_server` 目录执行：

```bash
pnpm install
```

说明：

- 项目根目录下存在 `pnpm-lock.yaml`，推荐使用 `pnpm`，不要混用 `npm`、`yarn`
- 如果你更换了包管理器，可能会出现依赖版本不一致、样式预处理器缺失等问题

#### 如果启动时报 `less` 缺失

如果启动前端后出现类似下面的报错：

```text
[plugin:vite:css] Preprocessor dependency "less" not found.
```

可以在项目根目录补装：

```bash
pnpm add -D less
```

然后重新执行：

```bash
pnpm install
pnpm run serve
```

这个报错通常出现在 AntV L7 相关组件依赖到 `.less` 文件，而当前机器本地还没有安装 `less` 预处理器时。

#### 启动开发环境

```bash
pnpm run serve
```

默认访问地址：

```text
http://localhost:5173/vue3-vite5-dashboard/
```

说明：

- 当前项目在 `.env` 中配置了 `VITE_BASE=/vue3-vite5-dashboard/`
- `vite.config.ts` 已配置开发代理，会把 `/api` 请求转发到 `http://127.0.0.1:8000`
- 如果你修改了 `VITE_BASE`，浏览器访问地址也要同步调整

## 二、前端环境变量说明

项目根目录下的 `.env` 用于前端 Vite 配置，当前常见字段如下：

```env
VITE_APP_TITLE=绿色金融与区域碳减排空间协同智能测算平台
VITE_BASE=/vue3-vite5-dashboard/
VITE_APP_DOMAIN=/api
```

说明：

- `VITE_APP_TITLE`：页面标题
- `VITE_BASE`：前端部署基础路径
- `VITE_APP_DOMAIN`：本地开发时的接口代理前缀

## 三、生产环境构建

在项目根目录执行：

```bash
pnpm run build
```

本地预览构建结果：

```bash
pnpm run preview
```

补充说明：

- 构建产物输出到 `dist/`
- 项目已启用 `vite-plugin-compression`，构建时会生成 `.gz` 压缩文件
- 如果部署在子路径下，生产环境 Web 服务器路径需要和 `VITE_BASE` 保持一致

## 四、部署建议

### 前端部署

- 将 `dist/` 部署到 Nginx、Apache 或其他静态资源服务器
- 建议开启 gzip / brotli
- 建议为 `.gz` 文件正确配置 `Content-Encoding`
- 如果是全新服务器，先安装 Node.js，再安装 `pnpm`，最后执行 `pnpm install`

### 后端部署

- 生产环境建议不要使用 `--reload`
- 可以改为：

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

- 再结合 Nginx 反向代理到 `/api`

## 五、AI 助手接入说明

### 1. 功能位置

- AI 助手入口位于首页右上角，为可收起的悬浮面板
- 支持“答疑助手”和“生成当前页总结”两种能力
- 聊天记录在前端内存中全局共享，切换绿色金融、碳排放、预测、宏观四个页面后仍会保留

### 2. 上下文来源

AI 不是裸聊，而是会结合当前页面的结构化快照一起请求后端：

- 绿色金融页：年份、省份、下钻省/市、顶部统计、Top10、雷达图聚焦项、县级 mock 数据
- 碳排放页：年份、总量、均值、最高省份、Top10
- 碳排放强度预测页：当前区域、滑块参数、模型系数、历史序列、预测序列、最终预测结果
- 宏观经济页：当前区域、GDP/碳排放序列、最新年份数据、时间范围

### 3. 启动验证步骤

1. 在 `greenfianace_server/.env` 中填写正确的 `DEEPSEEK_API_KEY`
2. 启动后端：

```bash
cd greenfianace_server
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

3. 启动前端：

```bash
cd ..
pnpm run serve
```

4. 打开首页右上角 AI 助手，验证以下场景：

- 在绿色金融页点击“生成当前页总结”，应返回与当前年份、省份和图表数据相关的中文总结
- 在任意页面输入问题，例如“当前页面最值得关注的趋势是什么”，应得到结合当前页面数据的回答
- 切换到预测页后再次提问，回答内容应转为结合预测结果和滑块参数，而不是沿用上一个页面上下文

### 4. 常见联调风险

- 如果未配置 `DEEPSEEK_API_KEY`，后端会返回明确错误，前端 AI 面板会提示失败原因
- 如果 DeepSeek 网络不可达或认证失败，错误不会直接暴露堆栈，而会以接口错误信息返回
- 如果当前页面尚未加载到足够数据，模型会被要求明确回答“当前页面数据不足”

## 六、常见问题

### 1. 后端提示数据库连接失败

优先检查：

- `greenfianace_server/.env` 是否已手动创建
- `.env` 中的 `DB_HOST`、`DB_USER`、`DB_PASSWORD`、`DB_NAME` 是否正确
- MySQL 服务是否已经启动
- `green_finance.sql` 是否已经导入成功

### 2. 出现 `Access denied ... using password: NO`

这通常表示后端没有正确读取到 `greenfianace_server/.env`，或者 `DB_PASSWORD` 为空。

### 3. 出现 `cryptography package is required`

重新在后端虚拟环境中执行：

```bash
pip install -r requirements.txt
```

### 4. 前端能打开，但接口 404 或代理失败

请检查：

- 后端是否运行在 `127.0.0.1:8000`
- 是否先启动了后端再启动前端
- `vite.config.ts` 中 `/api` 代理是否被改动

### 5. 出现 `pnpm` 命令无法识别

可以按下面任一方式处理：

```bash
npm install -g pnpm
```

或：

```bash
corepack enable
corepack prepare pnpm@8 --activate
```

安装后重新打开终端，再执行：

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

如果你之前混用了 `npm install`、`yarn install` 或手动删改过 `node_modules`，建议删除前端依赖后重新安装：

```bash
Remove-Item -Recurse -Force node_modules
pnpm install
```

### 7. 构建时报 `spawn EPERM`

这通常不是项目代码问题，而是当前终端或系统安全策略阻止了 `esbuild` 拉起子进程。

常见处理方式：

- 尝试使用本机正常权限终端重新执行构建
- 检查安全软件是否拦截 `node` / `esbuild`
- 避免在受限沙箱、只读目录或被严格管控的同步目录中运行构建

### 8. AI 助手提示 `DeepSeek API Key 未配置`

请检查：

- 是否已经手动创建 `greenfianace_server/.env`
- `DEEPSEEK_API_KEY` 是否已经填写且没有多余空格
- 是否是从 `greenfianace_server` 目录启动的后端服务

如果你刚改完 `.env`，请重启后端服务再试。

### 9. AI 助手返回超时或认证失败

优先检查：

- 服务器是否可以访问 `https://api.deepseek.com`
- `DEEPSEEK_API_KEY` 是否有效
- `DEEPSEEK_BASE_URL` 是否被改错
- 是否需要适当增大 `DEEPSEEK_TIMEOUT`

## 七、开发提示

- 地图静态 GeoJSON 位于 `public/geojson/`
- 县级 GeoJSON 为按需网络获取并做内存缓存
- 绿色金融、碳排放、预测、宏观四个页面均采用首页 Tab 切换
- 若需要联调接口，请优先确认后端和数据库都已正常运行

## License

MIT

## AI 助手二期补充说明（流式输出 + 页面级 Tool Calling）

当前版本在原有 `POST /api/ai/chat`、`POST /api/ai/summary` 的基础上，又增加了两条流式接口：

```text
POST /api/ai/chat/stream
POST /api/ai/summary/stream
```

说明：
- 这两条接口返回 `text/event-stream`
- 前端通过 `fetch + ReadableStream` 消费，不会暴露 DeepSeek API Key
- 旧的非流式接口仍然保留，作为流式失败时的 fallback

### 流式事件类型

后端会按下面这些事件逐步返回：

- `start`：开始处理当前请求
- `tool_start`：开始调用当前页面允许的工具查询
- `tool_result`：工具返回了摘要结果
- `delta`：模型增量文本
- `done`：本轮回答结束
- `error`：处理失败

### 页面级 Tool Calling 规则

当前只开放“和当前页面相关”的工具，不会跨页面乱查：

- `greenFinance`
  - 查询指定年份全国省级绿色金融数据
  - 查询指定省份、指定年份的地级市绿色金融数据
- `carbon`
  - 查询指定年份全国省级碳排放数据
- `energy`
  - 查询指定区域的预测历史序列与模型系数
- `macro`
  - 查询指定区域宏观时间序列
  - 查询宏观描述性统计结果

模型默认会优先使用当前页面快照回答；只有在用户问题超出当前快照粒度时，才会进一步触发当前页工具查询。

### 验证建议

1. 启动后端：
```bash
cd greenfianace_server
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

2. 启动前端：
```bash
cd ..
pnpm run serve
```

3. 打开首页右上角 AI 助手，验证以下场景：
- 提问后是否逐字返回
- 点击“生成当前页总结”是否逐步输出总结内容
- 在绿色金融页追问城市层级对比时，是否先出现“正在查询当前页数据”状态，再继续回答
- 在宏观页追问统计口径时，是否能触发宏观时间序列或描述性统计工具
- 如果流式中断，是否能自动回退到旧的非流式接口
