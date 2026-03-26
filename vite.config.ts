import { defineConfig, loadEnv } from 'vite';
import { resolve } from 'path';
import postcsspxtoviewport from 'postcss-px-to-viewport';

import presets from './presets/presets';

const pathSrc = resolve(__dirname, 'src');

// https://vitejs.dev/config/
export default defineConfig((env) => {
  // env 环境变量
  const viteEnv = loadEnv(env.mode, process.cwd());
  const normalizedBase = (viteEnv.VITE_BASE || '/').replace(/\/$/, '');

  return {
    base: viteEnv.VITE_BASE,
    // 插件
    plugins: [presets(env)],
    // 别名设置
    resolve: {
      alias: {
        '@': `${pathSrc}/`, // 把 @ 指向到 src 目录去
      },
    },
    // 服务设置
    server: {
      host: '0.0.0.0',
      port: 5173,
      open: true,
      // 带 VITE_BASE 子路径时，请求为 /{base}/api/...，需单独代理并重写为后端的 /api/...
      proxy: {
        ...(normalizedBase
          ? {
              [`${normalizedBase}/api`]: {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
                rewrite: (path) =>
                  path.replace(new RegExp(`^${normalizedBase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/api`), '/api'),
              },
            }
          : {}),
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      brotliSize: false,
      // 消除打包大小超过500kb警告
      chunkSizeWarningLimit: 2000,
      minify: 'terser',
      // 在生产环境移除console.log
      terserOptions: {
        compress: {
          drop_console: true,
          drop_debugger: true,
        },
      },
      assetsDir: 'static/assets',
      // 静态资源打包到dist下的不同目录
      rollupOptions: {
        output: {
          chunkFileNames: 'static/js/[name]-[hash].js',
          entryFileNames: 'static/js/[name]-[hash].js',
          assetFileNames: 'static/[ext]/[name]-[hash].[ext]',
        },
      },
    },
    css: {
      preprocessorOptions: {
        // 全局引入了 scss 的文件
        scss: {
          additionalData: `
          @import "@/assets/styles/variables.scss";
        `,
          javascriptEnabled: true,
        },
      },
      postcss: {
        plugins: [
          postcsspxtoviewport({
            unitToConvert: 'px', // 要转化的单位
            viewportWidth: 1600, // UI设计稿的宽度
            unitPrecision: 6, // 转换后的精度，即小数点位数
            propList: ['*'], // 指定转换的css属性的单位，*代表全部css属性的单位都进行转换
            viewportUnit: 'vw', // 指定需要转换成的视窗单位，默认vw
            fontViewportUnit: 'vw', // 指定字体需要转换成的视窗单位，默认vw
            selectorBlackList: ['ignore-'], // 指定不转换为视窗单位的类名，
            minPixelValue: 1, // 默认值1，小于或等于1px则不进行转换
            mediaQuery: true, // 是否在媒体查询的css代码中也进行转换，默认false
            replace: true, // 是否转换后直接更换属性值
            // exclude: [/node_modules/], // 设置忽略文件，用正则做目录名匹配
            exclude: [],
            landscape: false, // 是否处理横屏情况
          }),
        ],
      },
    },
  };
});
