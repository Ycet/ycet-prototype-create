# YCET Prototype Create

`ycet-prototype-create` 是一套面向 Codex、Claude Code 等 Agent 的产品原型制作 Skill，覆盖需求澄清、UI 方向确认、高保真静态原型、精准页面修改、多页面交互 Demo，以及已有原型接管与迁移。

## 当前版本

- 版本：V2.x 开发分支（V2.1 基线）
- 状态：稳定性优化中；结构、静态交互边界与跨浏览器框架运行时需要在每次修改后重新验证
- 交付目录：`outputs/skills/ycet-prototype-create/`
- 基线目录：`skill/ycet-prototype-create/`
- 对应提交：`8762a2e`（`[260712] V2.1开发完成`）

基线目录用于保留优化前的 Skill；后续使用、验证或安装时应以交付目录为准。

## 功能范围

### 功能一：高保真静态原型

- 对零散想法或不完整需求调用 `brainstorming-solo` 完善需求；阶段一只处理产品需求，UI 风格、色彩、字体、视觉参考与 UI Skill 均推迟到阶段二。对较完整的结构化 PRD 调用 `grill-me` 时，只复核交互逻辑、页面元素、业务规则、边界条件和异常处理，不重新访谈已给定的产品背景、定位、用户、页面范围或功能目标。
- 发现当前 Agent 可访问的全部 UI 相关 Skill，展示名称、功能、来源、可调用状态和前置条件，再由用户选择一个主 Skill或不使用 Skill。
- 未使用 UI Skill 时，依次确认参考产品或网站、设计风格、色彩方案和其他要求。
- 生成设计方向、首页预览、独立页面和静态原型入口。
- 静态页只允许页面内交互；未来跨页控件只声明 `data-ycet-nav-target`，不得执行跳转或发送 `navigate`。
- Chrome、Edge、Firefox 使用统一的无可见滚动条规则，必要滚动能力保留在阵列和页面内部容器。

### 功能二：原型页面精准修改

- 根据 CSS 选择器、HTML 片段和修改要求定位目标元素。
- 只修改目标范围，并按共享日志规范记录变更。
- V2.1 未改变该功能的业务流程。

### 功能三：可交互原型 Demo

- 从静态页面生成多页面交互 Demo。
- 通过 `navigate`、`set-screen`、`screen-changed` 等消息完成双层 iframe 导航中继。
- 将 `pages/**/*.html` 与 `index.html` 作为只读基线，以 SHA-256 保护；跨页逻辑只写入版本专用 `runtime-pages/` 副本和 `prototype*.html`。旧项目框架缺少运行时白名单时生成 Demo 专用框架副本，不覆盖原框架。
- 支持按框架文件名或映射元数据识别设备，并保留旧框架兼容模式。

## 当前稳定性约束

- 功能一阶段一不得询问或确定任何 UI 设计风格；用户主动提供的视觉偏好只记录为阶段二待处理输入。
- 功能一的 `pages/`、`previews/` 不得包含跨页链接、Location/History API、路由器跳转、顶层窗口控制或 `navigate` 消息。
- `scrollbar-width: none`、`-ms-overflow-style: none`、`::-webkit-scrollbar` 与 iframe `scrolling="no"` 共同构成跨浏览器兼容契约。
- 功能三用 `runtime-pages/<源页面>--<Demo版本>.html` 承载跨页逻辑，生成前后校验静态输入文件集合和 SHA-256；旧框架兼容增强只写入 `runtime-assets/frames/` 的版本专用副本。

### 功能四：已有原型接管与迁移

- 每次启动功能四时，必须先询问并获得用户对当前产品端口的明确回复；在此之前不得读取、审计或处理用户原型，也不得根据页面内容、尺寸、文件名或既有配置自行判断端口。
- 用户确认端口后，按与功能一完全一致的 Manifest 映射选择设备框架；微信小程序须同时确认宿主设备或由用户明确选择默认宿主。
- 编辑非本 Skill HTML 时，解析入口及关联 HTML/CSS/JS/资源并直接生成 `prototype/docs/Spec.md`，不调用 `brainstorming-solo` 或 `grill-me`；Spec 确认后复用功能一阶段二和阶段三。
- HTML 静态高保真原型完成后必须停止；任务开始时的交互要求不算二次确认，只有用户在静态完成后明确确认才进入功能三。
- PNG/JPG 等整页图片必须先将用户原图及确认后的固定区位图片段存入 `prototype/assets/images/`，再生成承载页与 `index.html`；`pages/` 和 `runtime-pages/` 均从该目录引用图片，禁止使用 `pages/source-images/`。禁止把图片解构或重绘为页面元素；只有用户明确要求固定顶部/底部区域并确认边界时，才可从原图无损分割固定区与可滚动区位图承载。
- 图片静态产物完成并经用户确认后才生成 `prototype.html`；交互只写入功能三运行时副本，静态 `pages/` 与 `index.html` 保持不变。
- 图片运行时热区默认透明；鼠标悬停或键盘聚焦时显示半透明虚线轮廓，不遮挡原图或阻断未覆盖区域滚动。

## V2.1 核心变化

- 使用 `brainstorming-solo` 替换原需求完善 Skill。
- 阶段二改为动态发现并展示已安装的 UI 相关 Skill。
- `design-direction.html` 将设备框架与首页效果合并为“首页预览”。
- 引入 Manifest 驱动的设备框架体系，统一尺寸、安全区域、端口映射和消息协议。
- 框架只负责状态栏、Home Indicator、Android 系统导航栏和浏览器/设备外壳。
- `pages/*.html` 与 `previews/*.html` 只负责产品 UI；App 顶部导航、Tab Bar、微信胶囊按钮和网站导航仍由页面实现。
- 功能三、功能四同步兼容新框架，同时保留旧项目识别能力。

## 产品端口与设备框架

| 产品端口 | 默认框架 |
| --- | --- |
| iOS、iPhone | `iphone-15-pro.html` |
| Android | `android-pixel.html` |
| iPad | `ipad-pro.html` |
| 网页、网站 | `browser-chrome.html` |
| 桌面端、Windows、macOS | `macbook.html` |
| 微信小程序 | 默认 `iphone-15-pro.html`；明确指定 Android 宿主时使用 `android-pixel.html` |

端口映射、逻辑画布、预览尺寸、安全区域和消息协议以 `assets/frames/manifest.json` 为唯一数据真源。

## 项目结构

```text
.
├─ skill/                              # 优化前的基线 Skill
├─ outputs/skills/ycet-prototype-create/
│  ├─ SKILL.md                         # V2.1 总入口与功能路由
│  ├─ agents/openai.yaml               # Codex 展示与调用元数据
│  ├─ assets/frames/                   # Manifest 和五类设备框架
│  ├─ docs/                            # 四项功能流程与共享规范
│  ├─ evals/evals.json                 # Agent 行为评估用例
│  └─ scripts/                         # 静态与运行时校验脚本
├─ assets/frames/                      # 本轮框架设计源文件
├─ docs/brainstorms/                   # 已确认规格和执行计划
├─ V1.0优化想法.txt
└─ V1.1优化想法.txt
```

## 使用方式

将以下目录作为 Skill 根目录：

```text
outputs/skills/ycet-prototype-create
```

Agent 应先读取 `SKILL.md` 完成功能路由，再按需读取对应功能文档、共享规范及 `assets/frames/manifest.json`。生成的原型统一写入目标项目的 `prototype/` 目录，不得依赖本 Skill 的绝对安装路径。

新原型中的设备框架按以下形式加载产品页面：

```html
<iframe
  data-ycet-frame-id="iphone-15-pro"
  src="assets/frames/iphone-15-pro.html?screen=pages/home.html"
  title="首页"
></iframe>
```

`screen` 只允许指向项目内的 `pages/*.html`、`previews/*.html`、`runtime-pages/*.html` 或 `about:blank`，并始终相对于 `prototype/` 项目根解析。框架不依赖 `document.referrer`，因此本地 `file://`、静态服务器和移动目录场景使用同一契约。

## 环境与验证

基础要求：

- Python 3
- 运行浏览器验证时需要 Python Playwright；测试器会依次尝试 Playwright Chromium、系统 Chrome、系统 Edge 和 Playwright Firefox，未安装的目标会明确标记为 `[SKIP]`

结构与规则校验：

```powershell
python outputs\skills\ycet-prototype-create\scripts\validate_skill.py
python outputs\skills\ycet-prototype-create\scripts\test_prototype_guard.py
```

五类框架运行时验证：

```powershell
python outputs\skills\ycet-prototype-create\scripts\test_frames_runtime.py
```

要求 Firefox 必须实际运行时使用：

```powershell
python outputs\skills\ycet-prototype-create\scripts\test_frames_runtime.py --require-firefox
```

运行时测试覆盖 HTTP 与 `file://` 页面加载、设计方向首页预览、逻辑视口尺寸、iframe 无可见滚动条契约、`runtime-pages/` 白名单、双层 iframe 消息中继、旧裸文件名兼容、中文/空格页面名、query/hash、编码遍历拦截，以及移动到带空格和中文目录后的可移植性。

对实际原型执行功能一边界校验和功能三只读保护：

```powershell
python outputs\skills\ycet-prototype-create\scripts\prototype_guard.py static --prototype-dir <prototype目录>
python outputs\skills\ycet-prototype-create\scripts\prototype_guard.py snapshot --prototype-dir <prototype目录> --output <临时快照文件>
python outputs\skills\ycet-prototype-create\scripts\prototype_guard.py verify --prototype-dir <prototype目录> --snapshot <临时快照文件>
```

## 文档索引

- `outputs/skills/ycet-prototype-create/SKILL.md`：总入口、功能路由和全局规则。
- `outputs/skills/ycet-prototype-create/docs/function-1-static-prototype.md`：静态高保真原型流程。
- `outputs/skills/ycet-prototype-create/docs/function-2-precision-edit.md`：页面精准修改流程。
- `outputs/skills/ycet-prototype-create/docs/function-3-interactive-demo.md`：交互 Demo 流程和消息协议。
- `outputs/skills/ycet-prototype-create/docs/function-4-existing-prototype-edit.md`：已有原型审计、接管和迁移流程。
- `outputs/skills/ycet-prototype-create/docs/shared-prototype-standards.md`：目录、框架、画布和页面规范。
- `outputs/skills/ycet-prototype-create/docs/shared-editlog-rules.md`：原型变更日志规则。
- `outputs/skills/ycet-prototype-create/assets/frames/README.md`：设备框架使用说明。
- `outputs/skills/ycet-prototype-create/scripts/prototype_guard.py`：功能一静态跨页禁令检查，以及功能三只读输入 SHA-256 快照/复核。
- `docs/brainstorms/specs/`：V2.1 已确认需求规格。
- `docs/brainstorms/plan/`：V2.1 执行计划。

## 已知限制与注意事项

- 当前自动化脚本验证 Skill 结构、框架配置和浏览器运行时行为，尚未自动执行完整的 Agent 对话评估。
- Skill 不会自动安装自身、替换全局 Skill、发布、部署、推送远程仓库或创建 PR。
- 当前交付目录未包含 `outputs/skills/ycet-prototype-create/evals/evals.json`；该文件仍存在于 V2.1 提交 `8762a2e` 中。恢复前，`validate_skill.py` 会因缺少评估文件而报告唯一失败，其余结构与本轮新增契约检查可正常完成。
