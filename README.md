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
```

各字段含义：

- `DB_HOST`：数据库地址，默认本机可写 `127.0.0.1`
- `DB_USER`：MySQL 用户名
- `DB_PASSWORD`：MySQL 密码
- `DB_NAME`：数据库名，默认是 `green_finance`
- `DB_CHARSET`：字符集，建议 `utf8mb4`

注意：

- 根目录下的 `.env` 是给 Vite 前端用的，不会被 `greenfianace_server/server.py` 读取
- 后端代码通过 `load_dotenv(ROOT / ".env")` 读取 `greenfianace_server/.env`
- 如果缺少这个文件，后端可能会以默认空密码尝试连接数据库，导致连接失败

启动后端：

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

启动成功后，接口地址默认是：

```text
http://127.0.0.1:8000/api
```

### 3. 启动前端服务

回到项目根目录：

```bash
cd ..
```

安装前端依赖：

```bash
pnpm install
```

启动开发环境：

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

### 后端部署

- 生产环境建议不要使用 `--reload`
- 可以改为：

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

- 再结合 Nginx 反向代理到 `/api`

## 五、常见问题

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

### 5. 构建时报 `spawn EPERM`

这通常不是项目代码问题，而是当前终端或系统安全策略阻止了 `esbuild` 拉起子进程。

常见处理方式：

- 尝试使用本机正常权限终端重新执行构建
- 检查安全软件是否拦截 `node` / `esbuild`
- 避免在受限沙箱、只读目录或被严格管控的同步目录中运行构建

## 六、开发提示

- 地图静态 GeoJSON 位于 `public/geojson/`
- 县级 GeoJSON 为按需网络获取并做内存缓存
- 绿色金融、碳排放、预测、宏观四个页面均采用首页 Tab 切换
- 若需要联调接口，请优先确认后端和数据库都已正常运行

## License

MIT
