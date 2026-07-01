# Shared Prototype Standards

本文件只在生成、重构或验证原型 HTML 时读取。

## 目录结构

```text
project-root/
  prototype/
    index.html
    design-direction.html
    prototype.html
    prototype-v2.html
    docs/
      Spec.md
      EditLog.md
    pages/
      home.html
      ...
    assets/
```

## 技术栈

- CSS：Tailwind CSS CDN 或 Bootstrap。
- 图标：FontAwesome 或其他开源图标库。
- 页面内交互：Alpine.js 或轻量原生 JavaScript。
- 关键代码添加中文注释。

## 设备框架与页面尺寸

| 端口 | 设备框架 CSS 类 | 页面根容器尺寸 | 框架边框 | 框架总尺寸 |
| --- | --- | --- | --- | --- |
| iOS | `.phone-frame` | `393×852px` | `4px solid` | `401×860px` |
| Android | `.android-frame` | `412×915px` | `4px solid` | `420×923px` |
| 微信小程序 | `.miniapp-frame` | `375×812px` | `3px solid` | `381×818px` |
| Web | `.browser-frame` | `1440×900px` | `2px solid` | `1444×904px` |
| 桌面端 | `.desktop-frame` | `1200×800px` | `2px solid` | `1204×804px` |

页面根容器尺寸必须与设备框架内部可用区域精确一致。

## `prototype/index.html` 规范

1. 作为主入口，使用 iframe 嵌入 `prototype/pages/*.html`。
2. 不直接写入各页面完整 HTML。
3. 移动端 / 小程序每行固定展示 4 个页面；Web / 桌面端每行固定展示 1 个页面。
4. 每个页面卡片包含页面名称、文件名、设备框架 iframe 预览、`打开页面html` 链接。
5. `index.html` 不实现跨页面跳转，只保留页面内交互。
6. iframe 必须设置 `display:block`、`border:0`、`overflow:hidden`、`scrolling="no"`。

## `prototype/pages/*.html` 规范

1. 每个页面都是独立完整 HTML 文件。
2. 页面内可以实现 Tab、弹窗、Toast、表单校验、loading、折叠、轮播等页面内交互。
3. 页面内不得实现跨页面跳转；跨页面导航统一交给功能三。
4. `html, body` 必须清除默认 margin 并禁止文档级横向溢出。
5. 移动端 / 小程序页面只能有一个固定尺寸根容器，如 `.app-screen`。
6. 纵向滚动只能发生在内部滚动容器，如 `.page-scroll`。
7. 移动端状态栏固定在页面画布顶部，不得放入 `.page-scroll`。
8. 底部导航栏使用根容器内部绝对定位，不使用相对 viewport 的 `fixed + left-1/2` 写法。

## 图片与图标

- UI 功能图标使用 FontAwesome 或其他开源图标库。
- 商品图、海报图、头像、Banner 等内容图片使用真实图片资源。
- 禁止用灰色占位图或功能图标代替内容图片。

## 质量检查

提交前至少检查：

- 所有原型文件位于 `prototype/`。
- iframe 路径正确。
- 页面根容器尺寸与设备框架内部尺寸一致。
- 页面无横向溢出。
- 页面内交互可用。
- 图片资源可加载。
- 移动端状态栏和底部导航栏位置正确。
- `EditLog.md` 已记录本次原型 HTML 变更。
