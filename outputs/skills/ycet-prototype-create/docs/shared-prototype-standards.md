# Shared Prototype Standards

生成、重构或验证原型 HTML 时读取本文件，同时读取 `../assets/frames/manifest.json`。Manifest 是设备规格唯一真源；本文件不维护第二套尺寸。

## 可视化工作台边界

需要展示、选择、批注或预览修改 HTML 时同时读取 `shared-workbench-protocol.md`。工作台状态固定在项目根 `.ycet-editor/`，该目录与 `prototype/` 同级，不是原型产物；不得把 `workspace.json`、请求、结果、事务、服务状态或运行时注入脚本复制进 `prototype/`。

工作台预览路由只在 HTTP 响应中注入编辑运行时。未发送草稿、选择覆盖层、批注标记、缩放和平移都不得写入 HTML，也不得成为功能三运行时副本或功能五离线打包输入。左栏移出只更新工作区配置，绝不删除磁盘文件。

## 目录结构

```text
prototype/
  design-direction.html
  index.html
  prototype.html
  prototype-v2.html
  prototype-mobile.html
  prototype-mobile-v2.html
  previews/
    home-preview.html
  pages/
    home.html
    ...
  runtime-pages/
    home--prototype.html
    ...
  runtime-assets/
    frames/
      prototype--<selected-frame>.html
  assets/
    frames/
      frame-config.json
      <selected-frame>.html
    images/
      images-manifest.json
      <content-images>
      imported-screen.png
    icons/
      <icon-files-or-icon-libraries>
  docs/
    Spec.md
    EditLog.md
```

## 路径与文件名契约

- `prototype/` 是所有运行时页面路径的唯一 URL 根；下文称“项目根”。
- `screen`、`navigate.targetPage`、`set-screen.screen` 与 `screen-changed.screen` 均使用相对于项目根的规范路径，如 `pages/home.html`、`previews/home-preview.html` 或 `runtime-pages/home--prototype.html`。
- 新生成的 `pages/*.html` 与 `previews/*.html` 文件名使用小写 ASCII kebab-case。接管旧项目时允许保留安全的中文、空格等文件名，但消息中的路径必须由 URL 正规化并编码。
- `runtime-pages/` 保存从静态页派生的可交互运行时副本。通常只由功能三生成；功能五仅在该目录完全没有 HTML 且用户已确认页面跳转逻辑时，才可按功能三规范一次性创建完整集合。功能一不得创建该目录。运行时副本保持与 `pages/` 相同的目录深度，使 `../assets/` 相对引用继续有效。
- `prototype-mobile.html` 与 `prototype-mobile-vN.html` 是功能五的自包含输出。首次使用无版本名，后续按已有最大版本递增，禁止覆盖旧文件。它们可以保存页面 pathname 作为注册表数据，但不得在运行时从 pathname、项目目录、绝对路径或网络读取资源。
- `runtime-assets/frames/` 只用于兼容尚未允许 `runtime-pages/` 的旧版 Manifest 框架。功能三可在此生成版本专用框架副本，但不得修改项目原有 `assets/frames/`、`index.html` 或静态页；副本仍按 `../../` 解析项目根。
- `screen` pathname 只允许位于 Manifest `allowedScreenPrefixes` 下并以 `.html` 结尾；允许保留 query/hash，但白名单与页面注册表先按解码后的 pathname 匹配，再把 query/hash 原样传给已登记页面。
- `frameFile` 包含 `.html` 扩展名，是相对于 `prototype/assets/frames/` 的纯文件名；消费者不得再次追加扩展名。
- 框架固定放在 `prototype/assets/frames/`，必须按 Manifest `frameProjectRootRelativePath` 从框架自身 URL 推导项目根；禁止依赖 `document.referrer`，以兼容 `file://`。
- `navigate.targetPage` 的规范格式与 `screen` 相同。兼容旧页面发送的裸文件名（如 `home.html`）时，框架只可将其补全为 `pages/home.html` 后再中继；新页面不得继续生成裸文件名。
- 禁止远程 URL、绝对路径、上级目录、控制字符和 `javascript:`。解析后目标必须仍位于项目根及允许目录内。

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
- `screenPathBase`
- `frameProjectRootRelativePath`
- `allowedScreenPrefixes`

配置不是原样复制单个框架条目：`frameId` 取条目 `id`，`frameFile` 取条目 `file`，端口与宿主来自已确认 Spec，其余路径字段取 Manifest 顶层。生成时按上述字段构造快照，不得在 `file`/`frameFile` 之间混用名称。

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
  width="414"
  height="868"
  scrolling="no"
  style="width:414px;height:868px;border:0;display:block;overflow:hidden;"
></iframe>
```

上例中的 `414×868` 取自 Manifest / `frame-config.json` 的 `preview`，生成时必须替换为当前项目实际 preview 像素，不得照抄示例数字。

- `screen` 按「路径与文件名契约」正规化和 URL 编码，只指向 `pages/*.html`、`previews/*.html`、`runtime-pages/*.html` 或 `about:blank`，并始终相对于项目根解析。
- 禁止远程 URL、绝对路径、上级目录和 `javascript:`。
- **外层框架 iframe**（`index.html`、`design-direction.html` 中嵌入的设备框架）宽高必须等于当前项目 `preview.width` × `preview.height` 固定像素；属性与 CSS 一致，禁止用百分比、`max-width`、`height: auto` 或外层 `transform: scale()` 二次压缩。
- **框架内部页面 iframe** 使用 `logicalViewport` 尺寸；缩放只允许发生在框架 HTML 内部（由 Manifest `preview.scale` 决定），外层不得再缩放。
- 所有路径为生成项目内相对路径。
- 滚动分层与 `index.html` 尺寸细则见下方「`index.html`」专节；`design-direction.html` 的首页预览 iframe 遵守同一契约。

## 页面文件

- 每个 `pages/*.html` 与 `previews/*.html` 都是独立完整 HTML。
- `html, body` 清除默认 margin，禁止文档级横向溢出。
- 页面只有一个与逻辑画布一致的根容器。
- 纵向滚动放在内部内容容器，不由 iframe 文档根节点承担。
- 产品固定导航使用根容器内部定位，不依赖外部 viewport。
- 内容图片与 UI 操作图标遵守「图片与图标」专章；二者不互相替代。

### 功能四整页图片承载页

- `assets/images/` 保存 PNG/JPG/JPEG/WebP 等用户提供的原始整页图片及其已确认固定区域位图片段；每张图片必须一一对应一个 `pages/**/*.html` 承载页。新项目不得创建或引用 `pages/source-images/`。
- 默认承载页只使用必要根容器、带 `data-ycet-scroll` 的适配容器和 `<img>` 显示完整原图。用户明确要求固定顶部/底部区域并确认原图边界时，允许从同一原图无损生成固定区和滚动区位图片段；除用户确认的固定区域位图分割外，禁止 OCR、元素识别或用 DOM/CSS 重绘图片中的标题、按钮、卡片、列表和导航。
- 承载页不绘制或嵌入设备外壳；由 `index.html` 的 Manifest 框架 iframe 通过 `?screen=pages/<file>.html` 加载，使图片显示在设备屏幕区域。
- 图片保持原始宽高比，不拉伸；默认按逻辑画布宽度适配且不裁剪，超出可视高度时仅由内部 `data-ycet-scroll` 容器纵向滚动。固定区域例外只能按用户确认的水平边界无损裁出位图片段，完整原图必须保留。
- 固定区域承载页只能由根容器、固定顶部/底部 `<img>`、唯一的 `data-ycet-scroll` 中间 `<img>` 和必要无障碍属性组成。固定区使用逻辑画布局部定位，滚动区位于其间；所有片段按同一比例显示，禁止 `position: fixed`、CSS 裁剪、补绘系统 UI 或把图片内容转换为元素。
- 图片承载页的 `<body>` 使用 `data-ycet-image-prototype="true"`。静态页和运行时副本都按所在文件位置引用同一 `assets/images/` 资源：根级 `pages/*.html` 与 `runtime-pages/*.html` 均写 `../assets/images/<file>`；嵌套页面保持等价相对路径，禁止运行时临时改为 `../pages/source-images/...`。

### 功能四图片运行时热区

- 热区只允许生成在用户确认后的 `runtime-pages/` 副本中，使用带 `data-ycet-nav-target` 和 `aria-label` 的 `<button class="ycet-image-hotspot ...">`；静态图片承载页不得包含该按钮或导航脚本。
- 热区默认透明，不得用遮罩或实色边框改变原图视觉；`hover` 和 `focus-visible` 必须显示半透明虚线轮廓。使用 `outline: 1px dashed transparent` 作为默认状态，并在 `.ycet-image-hotspot:hover, .ycet-image-hotspot:focus-visible` 中设定半透明 `outline-color`；热区须 `pointer-events: auto`、高于对应位图。
- 热区必须位于与目标图片相同的局部定位容器：滚动图片的热区跟随 `data-ycet-scroll` 滚动，固定片段的热区留在对应固定容器。未覆盖区域仍须可滚动。

## 分阶段交互契约

### 功能一：静态页

- `pages/**/*.html` 与 `previews/**/*.html` 只能改变当前文档内的状态，不得加载、打开或替换成另一个页面。
- 未来跨页控件只声明 `data-ycet-nav-target="pages/<file>.html"`；该属性不得配套导航监听器、`navigate` 消息或 URL 修改。
- 禁止跨页 `<a href>`、表单 `action`、Location/History API、`window.open()`、路由器跳转、顶层窗口控制和 `type: "navigate"` 消息。同文档 `#fragment` 不在禁用范围内。
- `index.html` 卡片的“打开页面html”工具链接用于检查独立交付物，不属于产品交互例外之外的导航能力。

### 功能三：运行时副本

- `index.html` 与既有 `pages/**/*.html` 是只读输入，生成前后必须按原始字节计算 SHA-256 并验证文件集合与摘要完全一致。
- 跨页逻辑只写入 `runtime-pages/*.html` 与 `prototype*.html`；旧项目如需白名单兼容，只能另写版本专用 `runtime-assets/frames/*.html`。运行时副本可读取静态页中的 `data-ycet-nav-target` 并映射到已登记的 `runtime-pages/` 目标。
- 不得为省事向 `pages/` 注入脚本、修改 `href`、增加事件属性、格式化文件、重命名或创建新的源页面。

### 功能四：静态重构与功能三交接

- 非本 Skill HTML 必须先从入口及关联 HTML/CSS/JS/资源直接生成 `prototype/docs/Spec.md`，不得调用 `brainstorming-solo` 或 `grill-me`；Spec 确认后复用功能一阶段二、阶段三。
- HTML 静态高保真原型完成后必须停止。任务开始时的交互要求不能替代静态完成后的再次确认；确认前不得生成 `runtime-pages/` 或 `prototype*.html`。
- 整页图片必须先生成默认只显示完整原图、或按用户确认固定区域承载的 `pages/**/*.html` 与 `index.html`。确认生成 Demo 前，禁止生成 `prototype.html`、运行时副本或交互热点；固定区域边界不明确时不得生成静态页。
- 图片 Demo 的 `runtime-pages/` 可叠加已确认的透明交互热点；热点默认透明、悬停或聚焦时显示半透明虚线轮廓。Demo 必须继续以完整原图或其已确认位图片段组合作为视觉基底，不得将图片替换为元素化 DOM。

### 功能五：移动端离线单文件

- 明确的手机预览、移动端预览、单 HTML 或离线单文件意图直接进入功能五。完整运行时页面存在时不再询问跳转逻辑。
- 已有运行时页面、静态页、入口、桌面 Demo、框架、配置、资源和日志均为只读输入。打包阶段只新增一个递增命名的 `prototype-mobile*.html`，不更新 EditLog。
- 只有运行时 HTML 完全缺失且用户已确认跳转图时，功能五才可先创建全新的完整 `runtime-pages/` 集合；部分存在、目标悬空、多个版本或来源冲突时必须停止。
- 每个运行时页面转为资源完全内联的独立 `srcdoc`，再以 Base64 安全存入页面注册表。禁止把多个页面合并到同一 DOM，也禁止依赖 Blob URL、本地路径、远程 URL、CDN、登录态或真实后端。
- 运行时页如使用固定像素逻辑画布，功能五只在离线 `srcdoc` 中追加视口适配层，使其宽高随实际手机可视区域变化；`runtime-pages/` 源文件继续只读，且不能因固定画布在任意手机尺寸上发生裁切。
- 外层只提供一个全屏无边框 iframe、左上角菜单按钮、覆盖式左侧导航抽屉、注册表白名单和历史管理。默认不显示设备框架、常驻导航或调试信息。
- 内部跨页继续使用 `channel: "ycet-prototype"`、`version: 1` 的 `navigate` 消息；外层验证 `event.source`、消息字段和规范目标。合法 query/hash 在 pathname 命中注册表后保留。
- 首次输出 `prototype-mobile.html`，后续输出下一个 `prototype-mobile-vN.html`。临时构建通过机械校验和输入 SHA-256 复核后才原子落盘，失败不得留下半成品。
- 完整流程、状态矩阵、脚本命令和验收门禁读取 `function-5-mobile-single-file.md`。

## 跨浏览器无可见滚动条契约

目标是“保留需要的滚动能力，但不显示浏览器原生滚动条”。只写 `overflow: hidden` 或 `::-webkit-scrollbar` 不足以覆盖 Firefox；所有生成 HTML 必须同时包含 Firefox 与 Chromium/WebKit 规则。

页面文档根和所有显式滚动容器使用以下基础规则；需要滚动的容器添加 `data-ycet-scroll`，并自行设置 `overflow: auto` 或 `overflow-y: auto`：

```css
/* 文档根不承担产品内容滚动，并隐藏各浏览器原生滚动条。 */
html,
body {
  width: 100%;
  height: 100%;
  margin: 0;
  scrollbar-width: none;      /* Firefox */
  -ms-overflow-style: none;   /* 旧版 Edge / IE 兼容兜底 */
}

[data-ycet-scroll] {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

html::-webkit-scrollbar,
body::-webkit-scrollbar,
[data-ycet-scroll]::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none;
}
```

分层要求：

- `pages/*`、`previews/*`、`runtime-pages/*` 的 `html/body` 另设 `overflow: hidden`；长内容只放入带 `data-ycet-scroll` 的内部容器。
- `index.html`、`design-direction.html`、`prototype*.html` 如需整页或阵列滚动，不得用 `overflow: hidden` 阻断滚轮、触控或键盘；只应用上述隐藏样式。
- 外层框架 iframe 与框架内部页面 iframe 同时设置 `scrolling="no"` 和 `overflow: hidden`。`scrolling="no"` 是兼容兜底，不能替代 CSS。
- 设备框架自身的 `html/body` 必须同时使用 `overflow: hidden`、`scrollbar-width: none`、`-ms-overflow-style: none` 和 WebKit 滚动条隐藏规则。
- 不得用裁剪内容、禁用页面内部滚动或缩短画布来达到“无滚动条”。

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

- `pages/*.html`、`previews/*.html` 与同深度的 `runtime-pages/*.html` 使用 `../assets/images/` 与 `../assets/icons/`；嵌套页面按自身目录深度计算等价相对路径。
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
- 首页预览使用的设备框架 iframe 遵守与 `index.html` 相同的 preview 固定像素尺寸与滚动分层契约。
- 不创建独立“设备框架预览”模块。
- 不展示其他正式页面，不执行跨页面导航。

## `index.html`

`index.html` 是页面阵列入口。生成时必须同时满足：卡片信息完整、框架 iframe 尺寸匹配 preview、三层滚动职责正确。

### 卡片与阵列

1. 每张页面卡片通过选中设备框架加载一个 `pages/*.html`。
2. 卡片至少包含：页面名称、文件名、框架预览 iframe、“打开页面html”链接。
3. 默认列数读取 Manifest `defaultColumns`；视口宽度不足时可减少列数，或允许**阵列外层容器**横向滚动。
4. 页面内交互可用；跨页面导航被忽略。

### 三层滚动（允许 / 禁止）

```text
index.html 阵列外层
  └─ 框架 iframe（设备壳，尺寸 = preview）
       └─ 产品页 iframe（尺寸 = logicalViewport，由框架内部管理）
```

| 层级 | 允许 | 禁止 |
| --- | --- | --- |
| `index.html` 阵列外层 | 窄屏下整页/阵列横向滚动；页面纵向滚动浏览多卡片；按无可见滚动条契约隐藏原生轨道 | 用滚动条“挤出”被压小的框架；卡片内再套一层滚动包住框架；为隐藏滚动条而禁用必要滚动 |
| 框架 iframe（外层嵌入） | 无原生滚动条；完整显示设备壳与屏幕 | 出现纵向/横向原生滚动条；被父级裁剪、遮挡或二次缩放 |
| 产品页文档根（`pages/*`） | 根画布固定为 logicalViewport | `html/body` 级滚动或文档级横向溢出 |
| 产品页内部内容容器 | 长列表/长内容在**内部容器**纵向滚动 | 把滚动交给 iframe 文档根或框架壳 |

说明：产品页**内部**滚动是预期行为；“无非预期滚动条”指框架 iframe 与阵列挤压导致的条，不是禁止页面内容滚动。

### 尺寸契约（防嵌入大小不匹配）

1. 读取 `prototype/assets/frames/frame-config.json`（或生成时的 Manifest 选中条目）的 `preview.width` / `preview.height`。
2. 每个框架 iframe 的 `width`/`height` 属性与 CSS `width`/`height` 均写为上述固定像素，二者一致。
3. 卡片中承载 iframe 的容器宽度/高度**不得小于** preview；可用 padding 包住卡片标题与链接，但不得让 padding/border 挤占 iframe 的约定显示区域。
4. 框架 iframe 必须同时设置 `scrolling="no"`，样式至少包含：`border: 0; display: block; overflow: hidden;`（或等价写法），避免 Firefox 等浏览器显示 iframe 原生滚动条。
5. **禁止**对框架 iframe 或其直接父级使用：`width: 100%`、`height: 100%`（相对弹性父级）、`max-width` 压缩、`height: auto`、`transform: scale(...)`、`object-fit` 等方式二次适配。
6. **禁止**用 `overflow: auto|scroll` 的小盒子包住 oversized 框架来“假装适配”；正确做法是保持 preview 像素，并在阵列层减列或横向滚动。
7. 缩放只发生在框架 HTML 内部（`logicalViewport` → `preview.scale`）；`index.html` 不得再缩放。

### 最小结构示例

生成时将 `414`/`868` 替换为当前项目实际 `preview` 值：

```html
<section class="page-card">
  <header>
    <h2>首页</h2>
    <p>pages/home.html</p>
    <a href="pages/home.html" target="_blank" rel="noopener">打开页面html</a>
  </header>
  <iframe
    data-ycet-frame-id="iphone-15-pro"
    src="assets/frames/iphone-15-pro.html?screen=pages/home.html"
    title="首页"
    width="414"
    height="868"
    scrolling="no"
    style="width:414px;height:868px;border:0;display:block;overflow:hidden;"
  ></iframe>
</section>
```

### 常见错误

| 错误写法 | 后果 |
| --- | --- |
| iframe 设 `width:100%` 塞进响应式卡片 | 框架被压扁/裁切，或内部出现原生滚动条 |
| 外层再 `transform: scale(0.5)` | 与框架内缩放叠加，preview 契约失效 |
| 卡片 `overflow:auto` 且小于 preview | 卡片内出现滚动条，看起来像“嵌入页滚动条” |
| 只写 `height:auto` / 不写固定高 | iframe 默认高度过小，页面被裁切 |
| 把产品页长内容滚动做成 `body` 滚动 | 框架内出现文档级滚动条，固定导航错位 |

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

- `navigate.targetPage`、`set-screen.screen`、`screen-changed.screen` 使用同一规范路径格式；外层页面注册表保存规范 pathname。
- 为兼容旧页面，框架可接收 `navigate.targetPage: "home.html"`，但向外层中继时必须规范化为 `pages/home.html`。
- query/hash 不参与页面是否已登记的判断；pathname 通过注册表后才允许保留并下发。

- 页面只向直接父级框架发送消息。
- 框架验证内部 iframe 的 `event.source` 后向外层中继。
- 外层验证当前框架、消息字段和页面白名单。
- 为兼容 `file://` 的 `origin: "null"`，不能只依赖 origin 字符串。
- 页面加载失败时保留当前页面并报告错误。

功能五没有设备框架中继层，运行时页直接向全屏 iframe 的父窗口发送同一协议的 `navigate` 消息。手机版外层只消费已登记页面目标，不新增另一套业务消息格式。

## 质量检查

- 所有原型产物位于 `prototype/`。
- Manifest、项目配置、Spec 和 HTML 框架 ID 一致。
- 页面逻辑画布、框架预览、缩放与安全区域一致。
- 系统 UI 和产品 UI 无重复。
- iframe 路径有效，无横向溢出、裁剪或留白。
- `index.html` / `design-direction.html` 中每个框架 iframe 的宽高等于当前 `preview` 固定像素，未二次缩放。
- 框架 iframe 无原生滚动条；阵列仅允许外层在窄屏下横向滚动，且 Chrome、Edge、Firefox 均不显示原生滚动条轨道。
- 产品页文档根不滚动；长内容仅在页面内部容器滚动。
- 内容图均在 `assets/images/`，网络图标均在 `assets/icons/`，HTML/CSS 为项目内相对路径。
- 无灰色占位、图标冒充内容图、占位图服务或未授权远程内容图/图标依赖。
- 内容图语义匹配可解释；降级/顶替已在完成说明列出。
- 断开外网后打开 `prototype/` 仍可看到内容图与图标。
- 建议存在 `assets/images/images-manifest.json` 且与实际文件大致一致。
- 页面内交互正常。
- 本地 HTML、本地静态服务器和目录迁移场景均可用。
- `EditLog.md` 已记录本次变更。
- 功能五例外：为遵守单文件只写边界，不修改 `EditLog.md`；完成说明必须记录输出版本、页面数、内联资源数、文件大小、只读校验和浏览器/真机结果。

## 旧框架兼容

`.phone-frame`、`.android-frame`、`.miniapp-frame`、`.browser-frame`、`.desktop-frame` 只用于识别已有项目。新生成项目不得继续使用这些类作为主框架方案，也不得把旧尺寸写入 Manifest。
