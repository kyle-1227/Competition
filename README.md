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

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器（http://localhost:5173）
npm run serve
```

## 构建

```bash
npm run build
```

## 项目结构

```
src/
├── api/                  # API 接口
├── assets/               # 静态资源
├── components/           # 通用组件（ScreenAdapter 屏幕适配）
├── router/               # 路由配置
├── store/                # 状态管理
├── utils/                # 工具函数
└── views/
    └── home/             # 大屏首页
        ├── index.vue     # 入口（标题 + 布局）
        ├── BizWrap.vue   # 左中右三栏布局
        └── hooks/
            ├── useMap.ts   # 中心地图可视化
            └── useChart.ts # 左右图表
```

