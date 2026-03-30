# 绿色金融与区域碳减排空间协同智能测算平台

基于 Vue 3 + Vite 5 + AntV L7 + ECharts 构建的数据可视化大屏，展示绿色金融与区域碳减排的空间协同分析；配套 FastAPI 后端提供省级/地级数据、宏观序列与 SDM 预测等接口。

## 功能模块（首页 Tab）

- **绿色金融监测**：全国/省 3D 地图下钻、七维雷达与 Top10 堆叠柱、数据看板
- **碳排放底色**：省级碳排放相关可视化
- **碳排放强度预测**：SDM 模型情景推演与历史/预测曲线（ECharts）
- **宏观经济动态**：GDP 与碳排放双轴趋势

## 技术栈（摘要）

| 层级 | 说明 |
|------|------|
| 前端 | Vue 3、TypeScript、Vite 5、AntV L7、ECharts 6、Element Plus、Axios、Vue Router |
| 后端 | Python 3、FastAPI、Uvicorn、PyMySQL、DBUtils、`python-dotenv` |
| 数据库 | MySQL 5.7+ / 8.x（8.x 默认认证需安装 **`cryptography`**，已在 `requirements.txt`） |

---

## 从零到一：本地运行

以下路径若无特殊说明，**「项目根目录」**指本仓库根目录（包含 `package.json`、`vite.config.ts` 的目录）。

### 0. 环境要求

| 软件 | 说明 |
|------|------|
| **Node.js** | LTS，建议 ≥ 18（用于前端） |
| **pnpm** | 包管理：`npm install -g pnpm` |
| **Python** | 3.10+（建议 3.11 / 3.12；后端） |
| **MySQL** | 已安装并**能本机登录**（服务监听如 `127.0.0.1:3306`） |

**注意：** 路径中含中文（如 `D:\数据大屏\...`）时，个别旧版 Python 包可能编译失败；本项目后端依赖已尽量使用带 wheel 的版本。若遇问题，优先使用官方 Python + 虚拟环境。

---

### 1. 创建数据库并导入数据

**操作位置：** 在已安装 **MySQL 客户端**（或 Navicat、Workbench 等）的机器上执行；SQL 文件在仓库内。

1. **启动 MySQL 服务**（Windows 服务 / `brew services` / `systemctl` 等）。
2. **导入脚本路径：**  
   `项目根目录/greenfianace_server/green_finance.sql`  
   脚本内含 `create database green_finance;` 及建表、插入数据。
3. **命令行示例（在 `greenfianace_server` 目录下执行，便于写相对路径）：**

```bash
cd greenfianace_server
# 将下面命令中的用户名改为你的 MySQL 账号（常见为 root）
mysql -u root -p < green_finance.sql
```

**Windows PowerShell** 若不支持上述重定向，可改用：

```powershell
cd greenfianace_server
Get-Content .\green_finance.sql -Raw | mysql -u root -p
```

**注意事项：**

- 若本机**已有**名为 `green_finance` 的库且需覆盖，请先自行备份，再删除库或注释掉 SQL 文件开头的 `create database green_finance;` 后仅执行建表与数据部分。
- 导入完成后，`DB_NAME` 应与脚本一致，默认为 **`green_finance`**。
- 确保用于连接的 MySQL 用户对该库有 **SELECT**（及后续若需维护则有相应权限）。

---

### 2. 后端：虚拟环境、依赖与 `.env`

**目录：`项目根目录/greenfianace_server/`**（该目录下有 `server.py`、`requirements.txt`。）

```bash
cd greenfianace_server
python -m venv .venv
```

激活虚拟环境：

- **Windows CMD：** `.venv\Scripts\activate`
- **Windows PowerShell：** `.\.venv\Scripts\Activate.ps1`
- **macOS / Linux：** `source .venv/bin/activate`

安装依赖（**仍在 `greenfianace_server` 目录下**）：

```bash
pip install -r requirements.txt
```

在 **`greenfianace_server/.env`** 中填写数据库连接（**仅后端读取此文件**；**不要提交到 Git**）：

| 变量 | 说明 |
|------|------|
| `DB_HOST` | 主机，本机一般为 `127.0.0.1` |
| `DB_USER` | MySQL 用户名 |
| `DB_PASSWORD` | 密码（须与步骤 1 所用账号一致） |
| `DB_NAME` | 数据库名，与导入脚本一致，一般为 `green_finance` |
| `DB_CHARSET` | 可选，默认 `utf8mb4` |

**注意事项：**

- 项目根目录下的 `.env`（含 `VITE_*`）**只给前端 Vite 使用**，**不会**被 Python 加载。
- MySQL 8 若使用 `caching_sha2_password`，需已安装 `cryptography`（已包含在 `requirements.txt`）；若终端提示缺少该包，重新执行 `pip install -r requirements.txt`。

---

### 3. 前端：安装依赖与可选配置

**目录：`项目根目录/`**（与 `package.json` 同级。）

```bash
cd /path/to/vue3-vite5-dashboard
pnpm install
```

**可选：** 在项目根目录维护 **`.env`** 或 **`.env.development`**，配置例如：

- `VITE_APP_TITLE`：页面标题  
- `VITE_BASE`：部署子路径（如 `/vue3-vite5-dashboard/`）；不设时以 `vite.config.ts` 默认为准  
- `VITE_APP_DOMAIN`：开发时代理前缀，常见为 `/api`

**注意：** 若配置了非根路径的 `VITE_BASE`，开发时访问地址为 `http://localhost:5173` + `VITE_BASE`（注意末尾斜杠与浏览器地址栏一致）。

---

### 4. 启动服务（先后端、再前端）

**终端 A — 后端（目录必须是 `greenfianace_server`）：**

```bash
cd greenfianace_server
# 若未激活：先激活 .venv
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

看到 Uvicorn 监听 `8000` 即表示后端进程正常；接口形如 `http://127.0.0.1:8000/api/...`。

**终端 B — 前端（目录为项目根目录）：**

```bash
cd /path/to/vue3-vite5-dashboard
pnpm run serve
```

默认前端开发地址为 **`http://localhost:5173`**（若改了端口，以终端输出为准）。

**注意事项：**

- 开发环境下，Vite 将 **`/api`** 代理到 **`http://127.0.0.1:8000`**；若使用自定义 `VITE_BASE`，代理规则见 `vite.config.ts`。
- 大屏请求数据时需**同时**运行后端与前端；仅开前端会出现接口失败或代理错误。

---

### 5. 验证与常见问题

- 浏览器打开前端地址后，切换需要数据的 Tab；若接口返回「数据库连接失败」，检查：MySQL 是否运行、**`greenfianace_server/.env`** 账号密码与库名、是否已导入 `green_finance.sql`。
- 后端终端若出现 `Access denied ... using password: NO`，说明 **`DB_PASSWORD` 未写入或未加载**。
- 后端终端若出现 `cryptography package is required for ...`，执行：`pip install -r requirements.txt`（在激活的 venv 中）。

---

### 6. 生产构建（可选）

**目录：项目根目录**

```bash
pnpm run build
pnpm run preview
```

`build` 会执行类型检查并输出到 `dist/`。部署在子路径时，请配置 `VITE_BASE` 与 Web 服务器路径一致。

---

## 项目结构（摘要）

```
├── greenfianace_server/
│   ├── server.py
│   ├── requirements.txt
│   ├── green_finance.sql    # 本地建库导数用
│   ├── .env                   # 后端数据库配置（勿提交）
│   └── analysis_models/
├── src/                       # 前端源码
├── vite.config.ts
└── package.json
```

## 许可证

MIT
