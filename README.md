# 绿色金融与区域碳减排空间协同智能测算平台

基于 Vue3 + Vite5 + AntV L7 构建的数据可视化大屏平台，用于展示绿色金融与区域碳减排的空间协同分析。

## 功能特性

- 🗺️ AntV L7 3D 中国地图可视化（3D 挤出地图、飞线动画、柱状图、涟漪效果）
- 📊 AntV G2 数据图表（柱状图、玫瑰图等）
- 📐 px2vw 横向自适应 + 高度居中适配方案
- ⌨️ Enter 键全屏模式切换

## 技术栈

- ⚡️ [Vue 3](https://github.com/vuejs/vue-next) + [Vite 5](https://github.com/vitejs/vite)
- 💪 [TypeScript](https://www.typescriptlang.org/)
- 🗺️ [AntV L7](https://l7.antv.antgroup.com/) - 地理空间数据可视化引擎
- 📊 [AntV G2](https://g2.antv.antgroup.com/) - 可视化图表库
- 🎉 [Element Plus](https://github.com/element-plus/element-plus) - UI 组件库
- 🍍 [Pinia](https://pinia.esm.dev/) - 状态管理
- 💡 [Vue Router 4](https://router.vuejs.org/zh/) - 路由管理
- 📦 [unplugin-vue-components](https://github.com/antfu/unplugin-vue-components) - 组件自动按需加载
- 📥 [unplugin-auto-import](https://github.com/antfu/unplugin-auto-import) - API 自动按需加载

## 环境准备

### 1. 安装 Node.js

前往 [Node.js 官网](https://nodejs.org/zh-cn) 下载 **LTS（长期支持）** 版本并安装（>= 16）。

安装完成后，打开终端验证：

```bash
node -v
npm -v
```

能正常输出版本号即表示安装成功。

### 2. 安装 pnpm

本项目使用 [pnpm](https://pnpm.io/zh/) 作为包管理器。在终端中执行：

```bash
npm install -g pnpm
```

验证安装：

```bash
pnpm -v
```

### 3. 安装项目依赖

进入项目根目录，执行：

```bash
pnpm install
```

## 运行与构建

```bash
# 启动开发服务器（默认地址 http://localhost:5173）
pnpm run serve

# 生产环境构建
pnpm run build

# 本地预览构建产物
pnpm run preview
```

## 项目结构

```
src/
├── api/                  # API 接口与请求封装
├── assets/               # 静态资源（字体、图片、样式）
├── components/           # 通用组件（ScreenAdapter 屏幕适配）
├── router/               # 路由配置
├── store/                # Pinia 状态管理
├── utils/                # 工具函数
└── views/
    └── home/             # 大屏首页
        ├── index.vue     # 入口（标题 + 布局）
        ├── BizWrap.vue   # 左中右三栏布局
        └── hooks/
            ├── useMap.ts      # 中心 3D 地图可视化
            ├── useChart.ts    # 左右数据图表
            └── provinceData.ts # 省份数据
```

