# 功能三：从静态原型到可交互 Demo

## 目标

将已确认的静态页面转换为完整可交互 Demo，生成 `prototype/prototype.html` 或递增版本 `prototype/prototype-vN.html`，并在 `prototype/runtime-pages/` 生成该版本专用的页面副本。保留交互流程确认、文件命名、左右分栏、双向同步、历史与错误处理等既有能力。

`prototype/index.html` 与功能一交付的 `prototype/pages/**/*.html` 是只读基线。功能三只能读取它们，不得注入脚本、修改属性或链接、格式化、重命名、删除、覆盖或新增 `pages/` 内的 HTML。跨页面逻辑只允许写入 `runtime-pages/` 和本次 `prototype*.html`。

开始前读取 `shared-prototype-standards.md`、`shared-editlog-rules.md` 与 `../assets/frames/manifest.json`。生成运行时页、运行时框架副本和 `prototype*.html` 不得启动工作台；用户后续明确选择功能二时，再由功能二扫描这些 HTML。本功能对 `index.html` 与 `pages/**/*.html` 的只读保护不变。

## 前置条件

- `prototype/index.html` 存在。
- `prototype/pages/*.html` 包含完整静态页面。
- `prototype/docs/Spec.md` 存在，或用户给出完整页面间交互流程。
- 新框架项目应存在 `prototype/assets/frames/frame-config.json` 和选中框架文件。
- Manifest 与项目配置的 `allowedScreenPrefixes` 支持 `runtime-pages/`；旧项目不支持时使用下文“Demo 专用框架副本”，不得退回到修改静态页的做法。

## 工作流程

1. 从 Spec 提取页面间交互流程，合并用户当前对话中的补充。
2. 展示最终交互流程并请求确认；未确认不生成 Demo。
3. 读取所有页面文件，核对文件名、`data-ycet-nav-target` 与交互流程。
4. 对 `index.html` 和既有 `pages/**/*.html` 建立原始字节 SHA-256 快照。
5. 识别项目框架并确定输出文件名；必要时生成 Demo 专用框架副本。
6. 为本版本生成 `runtime-pages/` 副本，只在副本中实现跨页面交互。
7. 生成左右分栏 Demo：左侧页面导航，右侧单个设备框架。
8. 验证双向同步、返回历史、路径白名单、错误处理与跨浏览器无可见滚动条。
9. 再次计算受保护文件的 SHA-256；文件集合或摘要有任一变化即判定失败，不得宣称完成。
10. 追加 EditLog；日志只记录 Demo、运行时副本和框架信息，不得把静态页记为已修改。

## 只读输入保护门禁

受保护集合固定为：

- `prototype/index.html`；
- 快照时已经存在的全部 `prototype/pages/**/*.html`；
- `pages/` 下 HTML 文件的相对路径集合，防止新增、删除或重命名被摘要遗漏。

开始任何写入前运行：

```text
python <skill目录>/scripts/prototype_guard.py snapshot --prototype-dir <prototype目录> --output <系统临时目录>/ycet-prototype-inputs.json
```

全部生成和日志写入完成后运行：

```text
python <skill目录>/scripts/prototype_guard.py verify --prototype-dir <prototype目录> --snapshot <系统临时目录>/ycet-prototype-inputs.json
```

两次命令之间禁止对受保护集合执行任何写操作，包括仅格式化或“顺便修正”静态页。校验失败时保留证据并报告差异；不得用重新计算快照掩盖变化，也不得覆盖无法确认来源的并发修改。

## 框架识别顺序

### 新框架模式

按优先级只读读取：

1. `prototype/assets/frames/frame-config.json`；
2. `index.html` 的 `data-ycet-frame-id`；
3. `index.html` 引用的框架文件名；
4. `Spec.md` 中的产品端口、宿主设备和框架 ID。

识别后验证：

- 配置 JSON 有效且版本受支持；
- 框架 ID、文件、逻辑画布、安全区域与 Manifest 相符；
- 项目内框架文件存在；
- `index.html` 与项目配置一致；
- 记录项目框架是否原生包含 `runtime-pages/` 白名单。

存在冲突时列出差异并请求用户确认，不静默覆盖 `index.html`、静态页或项目配置。

### 旧版新框架的无损兼容

如果项目已经使用 Manifest 框架，但项目内 `frame-config.json` 或框架 HTML 尚未允许 `runtime-pages/`：

1. 保持 `prototype/assets/frames/<frameFile>` 与原 `frame-config.json` 只读，不更新、不覆盖。
2. 从项目内框架生成 `prototype/runtime-assets/frames/<Demo文件stem>--<frameFile>`，目录深度仍为项目根下两级，继续使用 `frameProjectRootRelativePath: "../../"`。
3. 只在该副本中增加 `runtime-pages/` 白名单及跨浏览器滚动条兼容规则；框架 ID、逻辑画布、preview、安全区域、系统 UI 与消息协议不得改变。
4. 本次 `prototype*.html` 只引用 Demo 专用框架副本；`index.html` 继续引用原框架，因此静态交付行为不变。
5. 生成并校验副本失败时停止功能三并报告，不得修改源框架、`pages/` 或 `index.html` 兜底。

### 旧框架兼容模式

新规则无法识别时，才检查 `.phone-frame`、`.android-frame`、`.miniapp-frame`、`.browser-frame`、`.desktop-frame`。旧项目可使用单层 iframe 直接加载运行时副本，但仍须通过只读输入保护门禁。完成说明必须标注“旧框架兼容模式”，不得把旧尺寸写入 Manifest。

## 文件命名与运行时副本

### Demo 文件

1. 用户指定名称时使用安全的指定名称。
2. 首次生成使用 `prototype/prototype.html`。
3. 后续扫描 `prototype.html`、`prototype-v2.html` 等，使用下一个可用 `prototype-vN.html`。

### 运行时页面

1. 每个静态页生成一个同层级副本，命名为 `runtime-pages/<源文件stem>--<Demo文件stem>.html`。例如 `pages/home.html` 对应 `runtime-pages/home--prototype.html`，`prototype-v2.html` 对应 `runtime-pages/home--prototype-v2.html`。
2. 运行时副本与 `pages/` 保持相同目录深度，继续使用 `../assets/...`，不得复制或改写共享图片、图标和样式资产。功能四图片承载页必须保留 `data-ycet-image-prototype="true"` 标记，静态页与运行时页中的原图、固定区和滚动区均从 `assets/images/` 以同层级相对路径引用；根级页面的规范写法均为 `../assets/images/<file>`，不得改写为 `pages/source-images/` 或依赖运行时页面位置猜测路径。
3. 页面内交互原样保留；只在副本中增加已确认的跨页监听器。
4. 优先读取 `data-ycet-nav-target="pages/detail.html"`。若接管的旧静态页没有该属性，可按已确认流程在副本中绑定目标，但不得回写源页。
5. 本次 Demo 的所有运行时副本都使用同一 Demo stem，禁止覆盖其他 Demo 版本的副本。
6. 若生成 Demo 专用框架副本，其文件名同样包含 Demo stem，避免不同 Demo 版本相互覆盖。
7. 旧静态页若已经含有直接跨页链接或导航脚本，只在运行时副本中将其改为注册表驱动的 `runtime-pages/` 目标；不得原样保留会跳回 `pages/` 的逻辑，也不得修改源页。

## 新框架 Demo

### 布局

- 左侧约 280px，按核心流程、辅助功能、设置等分组展示页面。
- 右侧居中显示项目选中的单个设备框架。
- 优先使用项目内 `assets/frames/<frameFile>`；`frameFile` 已包含 `.html` 扩展名，不得重复追加。旧项目缺少运行时白名单时改用本版本的 `runtime-assets/frames/<Demo文件stem>--<frameFile>`。两种模式都不得引用 Skill 源目录。
- 小屏幕可改为上下布局或折叠侧栏，不改变页面逻辑画布。
- 外层与内部 iframe 均设置 `scrolling="no"` 和 `overflow: hidden`；页面、阵列及内部滚动容器遵守共享规范的 Firefox/Chromium 滚动条隐藏规则。

### 演示视口自适应（强制）

`prototype.html` 与每个 `prototype-vN.html` 都必须在浏览器默认 **100% 缩放**下完整显示左侧导航、设备框架和当前页面，不要求演示者先调整浏览器缩放，也不得因显示器尺寸不同把设备框架或导航栏整体缩得过小、放得过大或裁切。

1. 根布局使用 `width: 100%; min-height: 100dvh; height: 100dvh; overflow: hidden`，桌面端采用 `grid-template-columns: clamp(220px, 18vw, 296px) minmax(0, 1fr)`。导航栏独立于设备缩放，禁止对导航栏、外层 Demo 或 `body` 使用 `transform: scale(...)`、浏览器缩放模拟或基于窗口宽度的固定像素放大。
2. 设备展示区必须保留 `min-width: 0; min-height: 0`，从当前 `frame-config.json` 的 `preview.width` / `preview.height` 写入 `--frame-preview-width` 与 `--frame-preview-height`。iframe 始终保持这两个原始预览尺寸；只允许其外层承载盒按 `--demo-frame-scale` 缩放，缩放原点为左上，避免双重缩放和框架裁切。
3. 生成 `ResizeObserver` 监听设备展示区。每次尺寸变化按可用宽高计算 `--demo-frame-scale = min(1, availableWidth / framePreviewWidth, availableHeight / framePreviewHeight)`，并扣除不少于 24px 的安全边距；不得设置会迫使小视口溢出的最小缩放值。展示区使用缩放后的盒子尺寸居中，而不是用 `overflow: auto` 裁切 oversized 框架。
4. 导航条目过多时，仅导航列表自身允许纵向滚动；在窄屏断点（建议 `max-width: 760px`）改为顶部横向导航或可折叠抽屉，设备展示区仍按同一 `ResizeObserver` 规则完整容纳框架。导航文字、图标和按钮不得随设备缩放。
5. 生成后在 Chrome、Edge、Firefox 的 1440×900、1280×720 与 1024×768 视口、浏览器 100% 缩放下验证：导航宽度处于 220–296px（窄屏布局除外）、设备框架四边均在展示区可见、外层无横向溢出、页面 iframe 与框架均未出现原生滚动条。任一项失败必须调整 Demo 外层布局后再交付，不得改动静态输入页或设备逻辑画布兜底。

### 双路径页面注册表

根据 `prototype/pages/` 建立明确注册表，每项同时保存：页面 ID、显示名称、源 pathname、运行时 pathname 和允许来源。例如：

```javascript
{
  id: "home",
  sourcePath: "pages/home.html",
  runtimePath: "runtime-pages/home--prototype.html"
}
```

`data-ycet-nav-target` 和 Spec 使用源 pathname；实际 `screen`、`navigate.targetPage`、`set-screen.screen` 与 `screen-changed.screen` 使用本版本对应的运行时 pathname。收到带 query/hash 的目标时，先按解码后的规范 pathname 查询注册表，命中后才保留 query/hash。拒绝远程 URL、绝对路径、上级目录、`javascript:` 和未登记目标。

### 双层 iframe 通信

运行时副本发送规范目标：

```javascript
{
  channel: "ycet-prototype",
  version: 1,
  type: "navigate",
  targetPage: "runtime-pages/detail--prototype.html"
}
```

框架继续兼容旧页面发送的 `targetPage: "home.html"`，并补全为 `pages/home.html`；该兼容能力只用于已有项目，不得用于新运行时副本。支持 `ready`、`navigate`、`set-screen`、`screen-changed`、`error`。

#### 左侧到右侧

1. 用户点击左侧页面。
2. 外层按源页面 ID 查询本版本的运行时 pathname。
3. 外层向设备框架发送 `set-screen`，screen 使用 `runtime-pages/<file>.html`。
4. 框架切换内部 iframe 并发送 `screen-changed`。
5. 外层更新高亮和历史。

#### 右侧到左侧

1. 运行时副本根据 `data-ycet-nav-target` 查找注册表映射，并向直接父级框架发送 `navigate`。
2. 框架验证 `event.source`，正规化运行时目标，补充框架 ID 并中继。
3. 外层验证当前框架、消息字段和运行时页面注册表。
4. 外层切换页面并同步左侧高亮与历史。

页面不得通过 `window.top` 绕过框架。

### 安全与错误

- 检查 channel、version、type、`event.source` 和页面白名单。
- 为兼容 `file://` 的 null origin，不能只依赖 origin。
- 未知消息忽略并记录调试提示。
- 加载失败时保留当前页面并展示错误，不切换到远程或占位地址。
- 配置无效、框架缺失或 Manifest 不一致时停止生成；缺少 `runtime-pages/` 白名单时只有 Demo 专用框架副本通过验证才可继续。
- 不得通过修改 `pages/` 或 `index.html` 规避任何错误。

## 完成标准

- 输出 Demo、版本专用运行时副本及必要的 Demo 专用框架副本位于 `prototype/`，命名正确且未覆盖其他版本。
- 交互流程已确认；页面内原有交互仍可用，跨页交互只存在于运行时副本。
- 框架与 `index.html`、项目配置一致。
- 左右分栏、双向同步、返回历史和错误处理可用。
- `prototype.html` 与 `prototype-vN.html` 在默认 100% 缩放下完整展示可读的导航栏、设备框架和当前页面；已完成演示视口自适应的三档桌面视口与三浏览器验证。
- Chrome、Edge 与 Firefox 中无可见浏览器原生滚动条，必要滚动能力仍可用。
- 本地 HTML、静态服务器和目录迁移后均可使用。
- 生成前后 `index.html`、`pages/**/*.html` 的文件集合与 SHA-256 完全一致。
- 若本次包含功能四图片承载页，静态与运行时页面中的图片均可从 `assets/images/` 本地加载；每个跨页图片热区默认透明，鼠标悬停或键盘聚焦时显示半透明虚线轮廓，并通过 `scripts/prototype_guard.py image --prototype-dir <prototype目录> --require-runtime` 校验通过。
- EditLog 已记录 Demo、运行时副本和使用的框架 ID/兼容模式，未声称修改静态页。
- 新运行时页与 Demo 入口已完成，供用户后续通过功能二扫描；若用户通过“同步 pages”提交变更包，必须按共享协议在依赖组暂存合并并重新验证 `navigate`、`set-screen`、`screen-changed` 和 `prototype.html` 交互，禁止直接覆盖运行时文件。
