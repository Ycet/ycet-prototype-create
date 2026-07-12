# Shared Prototype Standards

生成、重构或验证原型 HTML 时读取本文件，同时读取 `../assets/frames/manifest.json`。Manifest 是设备规格唯一真源；本文件不维护第二套尺寸。

## 目录结构

```text
prototype/
  design-direction.html
  index.html
  prototype.html
  prototype-v2.html
  previews/
    home-preview.html
  pages/
    home.html
    ...
  assets/
    frames/
      frame-config.json
      <selected-frame>.html
  docs/
    Spec.md
    EditLog.md
```

## 技术栈

- CSS：Tailwind CSS CDN、Bootstrap 或项目已有样式体系。
- 图标：FontAwesome 或其他开源图标库。
- 页面内交互：Alpine.js 或轻量原生 JavaScript。
- 关键 HTML/CSS/JS 添加中文注释。

## Manifest 与项目配置

### 生成前检查

1. Manifest 可解析且 `schemaVersion` 受支持。
2. 框架 ID 唯一，文件存在。
3. 框架 HTML 的 `data-ycet-frame-id`、`data-logical-width`、`data-logical-height` 与 Manifest 一致。
4. 产品端口、宿主设备可映射为唯一框架。
5. `screen` 参数和消息协议字段完整。

任一检查失败时，新原型停止生成，不静默回退旧尺寸。

### 端口映射

- iOS、iPhone → `iphone-15-pro`
- Android → `android-pixel`
- iPad → `ipad-pro`
- 网页、网站 → `browser-chrome`
- 桌面端应用、Windows、macOS → `macbook`
- 微信小程序 → 默认 `iphone-15-pro`；仅在用户明确指定 Android 宿主时改用 `android-pixel`

端口映射必须由 Manifest 解析；本表用于解释业务规则，不替代 Manifest。

### 按需复制

只复制选中框架到 `prototype/assets/frames/`，并将选中条目写入 `frame-config.json`。配置快照至少包含：

- `schemaVersion`
- `frameId`
- `frameFile`
- `productPort`
- `hostDevice`
- `logicalViewport`
- `preview`
- `safeArea`
- `screenQueryParameter`

已交付项目不因 Skill Manifest 升级而静默变化；只有重新生成或明确迁移时更新快照。

## 系统 UI 与产品 UI

- 框架负责 Manifest `systemChrome` 声明的系统 UI。
- 页面负责 `productUiResponsibilities` 声明的产品 UI。
- 页面根画布匹配 `logicalViewport`，并按 `safeArea` 安排可交互内容。
- 移动端页面不再自行绘制状态栏、灵动岛、Home Indicator 或 Android 系统导航。
- App 顶部导航、Tab Bar、微信导航栏/胶囊按钮、网站导航、桌面应用菜单仍属于页面。

## 框架加载契约

外层页面统一使用：

```html
<iframe
  data-ycet-frame-id="iphone-15-pro"
  src="assets/frames/iphone-15-pro.html?screen=pages/home.html"
  title="首页"
></iframe>
```

- `screen` 进行 URL 编码，只指向 `pages/*.html`、`previews/*.html` 或 `about:blank`。
- 禁止远程 URL、绝对路径、上级目录和 `javascript:`。
- 框架 iframe 使用 Manifest `preview` 尺寸，不通过外层 CSS 强制压缩。
- 框架内部页面 iframe 使用 `logicalViewport` 尺寸。
- 所有路径为生成项目内相对路径。

## 页面文件

- 每个 `pages/*.html` 与 `previews/*.html` 都是独立完整 HTML。
- `html, body` 清除默认 margin，禁止文档级横向溢出。
- 页面只有一个与逻辑画布一致的根容器。
- 纵向滚动放在内部内容容器，不由 iframe 文档根节点承担。
- 产品固定导航使用根容器内部定位，不依赖外部 viewport。
- 内容图片使用真实图片资源；UI 操作图标使用图标库，不互相替代。

## `design-direction.html`

- 包含色彩、字体、按钮、反馈、必要补充组件和“首页预览”。
- 首页预览加载 `previews/home-preview.html`。
- 不创建独立“设备框架预览”模块。
- 不展示其他正式页面，不执行跨页面导航。

## `index.html`

1. 每张页面卡片通过选中设备框架加载一个 `pages/*.html`。
2. 卡片包含页面名称、文件名、框架预览和“打开页面html”链接。
3. 默认列数读取 Manifest `defaultColumns`；宽度不足时可减少列数或允许阵列外层横向滚动。
4. 框架与内部页面不得出现由阵列布局造成的滚动条。
5. 页面内交互可用；跨页面导航被忽略。

## 消息协议

消息固定包含：

```javascript
{
  channel: "ycet-prototype",
  version: 1,
  type: "navigate"
}
```

支持 `ready`、`navigate`、`set-screen`、`screen-changed`、`error`。

- 页面只向直接父级框架发送消息。
- 框架验证内部 iframe 的 `event.source` 后向外层中继。
- 外层验证当前框架、消息字段和页面白名单。
- 为兼容 `file://` 的 `origin: "null"`，不能只依赖 origin 字符串。
- 页面加载失败时保留当前页面并报告错误。

## 质量检查

- 所有原型产物位于 `prototype/`。
- Manifest、项目配置、Spec 和 HTML 框架 ID 一致。
- 页面逻辑画布、框架预览、缩放与安全区域一致。
- 系统 UI 和产品 UI 无重复。
- iframe 路径有效，无横向溢出、裁剪或留白。
- 页面内交互与图片资源正常。
- 本地 HTML、本地静态服务器和目录迁移场景均可用。
- `EditLog.md` 已记录本次变更。

## 旧框架兼容

`.phone-frame`、`.android-frame`、`.miniapp-frame`、`.browser-frame`、`.desktop-frame` 只用于识别已有项目。新生成项目不得继续使用这些类作为主框架方案，也不得把旧尺寸写入 Manifest。
