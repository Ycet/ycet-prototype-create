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
    images/
      images-manifest.json
      <content-images>
    icons/
      <icon-files-or-icon-libraries>
  docs/
    Spec.md
    EditLog.md
```

## 技术栈

- CSS：Tailwind CSS CDN、Bootstrap 或项目已有样式体系。
- 图标：FontAwesome 或其他开源图标库；网络获取的图标须本地化到 `prototype/assets/icons/`，详见「图片与图标」。
- 内容图：真实图片资源，本地化到 `prototype/assets/images/`，详见「图片与图标」。
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
- 内容图片与 UI 操作图标遵守「图片与图标」专章；二者不互相替代。

## 图片与图标

生成、规范化或验证含内容图/图标的页面时，遵守本专章。细则优先于技术栈中的一句话摘要。

### 适用范围

| 功能 | 是否强制 | 说明 |
| --- | --- | --- |
| 功能一 静态原型 | **强制** | 生成 `design-direction` / `home-preview` / `pages` 时，内容图与网络图标必须本地化 |
| 功能二 精准修改 | 不强制全量审计 | 若修改引入新内容图或网络图标，按本专章本地化；纯文案/样式改动不动资源 |
| 功能三 交互 Demo | 不强制全量审计 | 不主动扫外链；若生成过程新增内容图或网络图标，按本专章本地化 |
| 功能四 HTML 规范化 | **强制** | 审计并本地化外链内容图与远程图标；整页图片原型走功能四既有导入流程 |

### 资源分类

| 类型 | 用途 | 存放位置 | 允许形式 | 禁止 |
| --- | --- | --- | --- | --- |
| UI 操作图标 | 导航、操作、状态、Tab、按钮旁图标等 | `prototype/assets/icons/` | 本地 SVG / 字体图标库；页面相对路径引用 | 用图标冒充内容图；交付态依赖未本地化的远程图标 URL/CDN |
| 内容图片 | 商品图、海报、头像、Banner、封面、列表缩略图、空状态插画位等 | `prototype/assets/images/` | 真实照片/插画；本地相对路径 | 灰占位、图标顶替、远程外链（无用户例外）、能匹配时仍用无关图 |

### 底线

1. 交付态内容图 `src` 与图标引用均不得依赖未本地化远程 URL（用户明确例外并记入 EditLog 的除外）。
2. 禁止灰色占位、skeleton-only 色块、或图标库图标代替内容图位。
3. 禁止 `picsum.photos`、`placehold.co`、`via.placeholder.com` 等占位图服务，以及纯色/渐变 div 冒充内容图。
4. 功能四整页截图/设计稿图片不套用本专章图库语义匹配阶梯，但文件必须在 `prototype/` 内且可离线打开。

### 图标本地化

1. 凡从网络获取的图标资源（远程 SVG/PNG、图标 CDN 的 CSS/字体、网上下载的单枚图标），交付前写入 `prototype/assets/icons/`（可含子路径，如 `icons/fontawesome/`），页面改为相对路径。
2. 推荐使用开源图标库的本地化拷贝（整库 CSS+字体或按需 SVG），而不是页面写远程 CDN。
3. 用户明确要求保留图标 CDN 时，须在完成说明与 EditLog 记录“图标仍依赖外网”；默认仍本地化。
4. 图标不得放入 `assets/images/`；内容图不得放入 `assets/icons/`。

### 命名

内容图格式：

```text
{page-or-module}-{role}-{semantic}[-{nn}].{ext}
```

| 段 | 规则 | 示例 |
| --- | --- | --- |
| page-or-module | 小写英文与短横线 | `home`、`product-detail` |
| role | 固定角色词 | `banner`、`avatar`、`product`、`cover`、`thumb`、`poster`、`hero` |
| semantic | 内容语义关键词 | `coffee`、`running-shoes`、`female-portrait` |
| nn | 同角色多图时两位序号 | `01`、`02` |
| ext | 优先 `jpg` / `jpeg` / `png` / `webp` | |

示例：`home-banner-summer-sale.jpg`、`home-product-running-shoes-01.jpg`、`profile-avatar-female-portrait.jpg`。

禁止：`img1.jpg`、`photo.png`、中文文件名、空格、无语义哈希名（除非用户明确要求）。

图标命名：

| 场景 | 约定 |
| --- | --- |
| 单枚 SVG/PNG | `{purpose}.svg` 或 `{purpose}-{variant}.svg`，如 `nav-home.svg` |
| 整库本地化 | 如 `icons/fontawesome/`，保持库内原始结构 |
| 页面引用 | 相对路径，如 `../assets/icons/nav-home.svg` |

### 语义匹配阶梯

生成或补内容图时按顺序执行，**不可跳级**：

1. **严格匹配**：按模块角色 + 业务语义检索。例：咖啡商品卡 → 咖啡/饮品实物；女性头像 → 女性人像；跑鞋 Banner → 跑鞋或跑步场景。
2. **大类匹配**（严格无可用图源时）：同业态/同视觉大类。例：咖啡 → 饮品/餐饮；跑鞋 → 运动鞋/运动。
3. **非匹配兜底**（大类仍失败时）：允许语义不匹配但风格尽量接近设计方向的真实图；**必须**在完成说明列出文件名、期望语义、实际语义与原因。
4. **近似图顶替**（下载失败时）：优先复用本项目 `assets/images/` 中语义最接近的已下载图；复用时**复制并按新图位重命名**；项目内无可复用图时回到阶梯 2→3 再检索；**禁止**改用灰占位或图标顶替。

每个内容图位生成前应确定：`page`、`role`、`semantic`、`query`（优先英文关键词）、`orientation`、`matchLevel`。同一列表多商品语义应区分，禁止整页复制同一张商品图糊弄（空状态/占位列表等合理重复除外）。

### 获取与下载

图库优先级：Unsplash → Pexels → Pixabay → 其他明确可免费使用的图源。使用可稳定下载的公开 URL + 通用 HTTP 工具即可，不强制专用 CLI 或付费 API。

推荐顺序：

1. 列出全部内容图位与图标需求。
2. 为每个内容图位确定 role、semantic、query、期望比例。
3. 按语义阶梯选图并下载到 `prototype/assets/images/`。
4. 将网络图标/图标库下载到 `prototype/assets/icons/`。
5. HTML/CSS 只写项目内相对路径。
6. 建议写入或更新 `prototype/assets/images/images-manifest.json`。
7. 质检路径存在、无未授权外链、无占位服务、降级已记录。

下载约束：优先中等体积（约 200KB–1.5MB 量级，非硬阈值）；保留合理宽高；不把远程 URL 留在交付 HTML。下载失败走近似顶替与再检索；仍失败则暂停并报告失败图位，不静默交付残缺包。

`images-manifest.json` 建议字段：

```json
{
  "schemaVersion": 1,
  "images": [
    {
      "file": "home-product-running-shoes-01.jpg",
      "page": "home",
      "role": "product",
      "semantic": "running shoes",
      "matchLevel": "strict",
      "source": "unsplash",
      "sourceUrl": "https://...",
      "downloadedAt": "2026-07-12",
      "usedBy": ["pages/home.html"]
    }
  ]
}
```

manifest 用于溯源与审计，非运行时强依赖；页面不得只靠 manifest 才能显示图片。

### HTML 引用

```html
<img src="../assets/images/home-product-running-shoes-01.jpg" alt="跑鞋商品图" />
<img src="../assets/icons/nav-home.svg" alt="" />
<link rel="stylesheet" href="../assets/icons/fontawesome/css/all.min.css" />
```

- `pages/*.html`、`previews/*.html` 使用 `../assets/images/` 与 `../assets/icons/`。
- 根目录 HTML（如 `design-direction.html`、`index.html`）使用 `assets/images/` 与 `assets/icons/`。
- 禁止本 Skill 安装目录绝对路径与 `file:///` 绝对本地路径。
- CSS `background-image` 中的内容图同样必须本地相对路径。

### 红线借口

| 借口 | 现实 |
| --- | --- |
| “先用 picsum/占位，下次再换真图” | 交付即须真图本地化；禁止占位交付 |
| “CDN 图标打开快，file 协议也能用” | 对方断网或打包内网会挂；默认本地化 |
| “语义差不多就行，随便下张图” | 先严格再大类；跳级须有失败原因 |
| “图片太多，只下 Banner” | 所有内容图位同等要求 |
| “外链写着，用户有网就行” | 本规范目标是打包离线可读 |
| “图标算 UI 不用本地” | 网络获取的图标同样本地化到 `assets/icons/` |
| “功能四原页面就有 Unsplash 链接，别动” | 规范化强制本地化外链内容图 |

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
- 内容图均在 `assets/images/`，网络图标均在 `assets/icons/`，HTML/CSS 为项目内相对路径。
- 无灰色占位、图标冒充内容图、占位图服务或未授权远程内容图/图标依赖。
- 内容图语义匹配可解释；降级/顶替已在完成说明列出。
- 断开外网后打开 `prototype/` 仍可看到内容图与图标。
- 建议存在 `assets/images/images-manifest.json` 且与实际文件大致一致。
- 页面内交互正常。
- 本地 HTML、本地静态服务器和目录迁移场景均可用。
- `EditLog.md` 已记录本次变更。

## 旧框架兼容

`.phone-frame`、`.android-frame`、`.miniapp-frame`、`.browser-frame`、`.desktop-frame` 只用于识别已有项目。新生成项目不得继续使用这些类作为主框架方案，也不得把旧尺寸写入 Manifest。
