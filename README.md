# 绿色金融与区域碳减排空间协同智能测算平台

基于 Vue 3 + Vite 5 + AntV L7 + ECharts 构建的数据可视化大屏，展示绿色金融与区域碳减排的空间协同分析；配套 FastAPI 后端提供省级/地级数据、宏观序列与 SDM 预测等接口。

## 功能模块（首页 Tab）

- **绿色金融监测**：全国/省 3D 地图下钻、七维雷达与 Top10 堆叠柱、数据看板
- **碳排放底色**：省级碳排放相关可视化
- **碳排放强度预测**：SDM 模型情景推演与历史/预测曲线（ECharts）
- **宏观经济动态**：GDP 与碳排放双轴趋势

## 技术栈

### 前端

- Vue 3 + TypeScript + Vite 5
- AntV L7 / L7-Maps（3D 地图）
- ECharts 6
- Element Plus 2
- Axios、Vue Router 4
- `unplugin-vue-components` / `unplugin-auto-import`（按需加载）
- 屏幕适配：`ScreenAdapter` + postcss px-to-viewport

### 后端（可选，本地联调）

- Python 3 + [FastAPI](https://fastapi.tiangolo.com/)
- MySQL（`pymysql` + DBUtils 连接池）
- 配置：`greenfianace_server/.env`（从 `.env.example` 复制），详见该目录内说明

## 环境准备（前端）

1. 安装 [Node.js](https://nodejs.org/) LTS（建议 ≥ 18）
2. 全局安装 pnpm：`npm install -g pnpm`
3. 在项目根目录安装依赖：

```bash
pnpm install
```

## 后端服务（大屏数据接口）

目录：`greenfianace_server/`

```bash
cd greenfianace_server
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
# 复制 .env.example 为 .env 并填写数据库等配置（勿将 .env 提交仓库）
# Windows: copy .env.example .env
# macOS/Linux: cp .env.example .env
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

开发环境下，Vite 将 `/api` 代理到 `http://127.0.0.1:8000`（若使用子路径部署 `VITE_BASE`，代理规则见 `vite.config.ts`）。

## 运行与构建（前端）

在项目根目录：

```bash
# 开发（默认 http://localhost:5173）
pnpm run serve

# 类型检查 + 生产构建
pnpm run build

# 预览构建产物
pnpm run preview
```

若部署在子路径，请在根目录配置 `.env` / `.env.production` 中的 `VITE_BASE`（与 `vite.config.ts` 中 `base` 一致）。

## 项目结构（摘要）

```
├── greenfianace_server/     # FastAPI 后端（MySQL、省级/地级、宏观、SDM 数据等）
│   ├── server.py
│   ├── requirements.txt
│   ├── .env.example
│   └── analysis_models/     # 计量/分析脚本（可选）
├── src/
│   ├── api/                 # HTTP 封装与接口模块
│   ├── assets/styles/       # 全局样式（含大屏 Element 下拉等）
│   ├── components/          # ScreenAdapter 等
│   ├── router/
│   └── views/home/
│       ├── index.vue        # 大屏入口（Tab + 时间轴）
│       ├── BizGreenFinance.vue
│       ├── BizCarbon.vue
│       ├── BizCarbonPrediction.vue
│       ├── BizMacro.vue
│       └── hooks/           # useMap、useChart、provinceData 等
├── vite.config.ts
└── package.json
```

## 许可证

MIT
