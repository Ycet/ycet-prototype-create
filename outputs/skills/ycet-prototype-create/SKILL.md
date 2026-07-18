---
name: ycet-prototype-create
description: Create high-fidelity static product prototypes, precisely edit prototype elements, generate interactive multi-page demos, normalize existing HTML/image prototypes, or package runtime pages as one offline mobile-preview HTML. Use when a user needs product requirements turned into prototype pages, wants UI design skills discovered and applied, provides CSS selectors plus HTML for a targeted edit, requests complete page-to-page interaction, needs an existing prototype migrated to the bundled Manifest-driven device-frame system, or asks for phone preview, mobile preview, a self-contained prototype-mobile.html, or an offline single-file prototype.
---

# YCET Prototype Creator

先完成功能路由，再读取对应功能文件。除当前功能明确要求外，不提前加载其他功能细节。

## 路由

### 直接路由

- 用户明确要求手机预览、移动端预览、离线单文件、单 HTML 文件或 `prototype-mobile.html`：读取 `docs/function-5-mobile-single-file.md`。
- 用户提供非本 Skill 生成的完整 HTML 原型文件并要求增加/修改页面或交互：读取 `docs/function-4-existing-prototype-edit.md`；即使同时提供 CSS 选择器或 HTML 片段，本规则也优先于功能二。
- 用户提供 PNG、JPG、JPEG、WebP 等整页原型图片并要求接管、编辑或生成交互原型：读取 `docs/function-4-existing-prototype-edit.md`。
- 用户同时提供 CSS 选择器、HTML 片段和明确元素修改要求：读取 `docs/function-2-precision-edit.md`。
- 用户明确指定功能一/二/三/四/五或对应名称：直接读取对应文件。

### 默认选择

无法直接路由时，只询问用户选择一项：

| 选项 | 功能 | 文件 |
| --- | --- | --- |
| A | 从产品需求到高保真静态原型 | `docs/function-1-static-prototype.md` |
| B | 通过浏览器开发者工具精准修改原型 | `docs/function-2-precision-edit.md` |
| C | 从静态页面到可交互原型 Demo | `docs/function-3-interactive-demo.md` |
| D | 现有 HTML 或图片原型规范化与编辑 | `docs/function-4-existing-prototype-edit.md` |
| E | 生成可单独发送到手机的离线单文件原型 | `docs/function-5-mobile-single-file.md` |

单次任务只执行一个功能；跨功能需求先完成当前功能，再说明后续入口。

## 全局规则

1. 所有原型产物放在项目根目录 `prototype/`。
2. `Spec.md` 固定为 `prototype/docs/Spec.md`；`EditLog.md` 固定为 `prototype/docs/EditLog.md`。
3. 生成、重构或验证原型 HTML 前读取 `docs/shared-prototype-standards.md` 与 `assets/frames/manifest.json`。
4. 写入或修改原型 HTML、设计预览、项目框架配置或项目内框架文件前读取 `docs/shared-editlog-rules.md`。
5. 新原型只使用 Manifest 驱动的框架；旧 CSS 框架类仅用于已有项目兼容。
6. 框架负责系统 UI，页面负责产品 UI；不得重复绘制状态栏、Home Indicator 或 Android 系统导航栏。
7. 若功能文件设置确认门禁，用户确认前不得继续。
8. 与用户使用中文交流；界面文字按产品实际语言决定。
9. 关键 HTML/CSS/JS 添加中文注释。
10. 不确定信息写入“待确认事项”或向用户确认，不得编造。
11. 不自动安装 Skill、打开外部网页、发布、部署或执行 Git 提交。
12. 内容图与网络获取的 UI 图标须按 `docs/shared-prototype-standards.md`「图片与图标」本地化到 `prototype/assets/images/` 与 `prototype/assets/icons/`；禁止灰占位或图标冒充内容图。
13. 功能一阶段一只完善产品需求，禁止询问或确定 UI 设计风格；视觉方向、UI Skill、色彩、字体和视觉参考只在阶段二处理。
14. 功能一的结构化 PRD 调用 `grill-me` 时，只可追问产品交互逻辑、各页面元素、业务规则、边界条件和异常处理场景，且只问文档中缺失、矛盾或含糊的内容；不得重新打开已给定的产品背景、定位、目标用户、使用场景、页面清单或功能目标。仅当产品端口或微信小程序宿主缺失并阻塞框架选择时，主流程可单独直接询问一次，该问题不交给 `grill-me`。
15. 功能一生成的 `pages/**/*.html` 与 `previews/**/*.html` 只允许页面内交互，禁止任何跨页面或离开当前文档的导航实现；跨页控件只保留 `data-ycet-nav-target` 意图元数据，实际导航只在功能三的运行时副本中实现。
16. 所有生成 HTML 必须遵守共享规范的跨浏览器无可见滚动条契约；不能只依赖 Chromium 的滚动条表现。
17. 功能三将 `prototype/index.html` 与既有 `prototype/pages/**/*.html` 视为只读输入；跨页逻辑写入 `prototype/runtime-pages/`，并在生成前后用 SHA-256 校验受保护输入未变化。
18. 功能四每次启动时，必须在读取或审计用户原型前询问并获得用户对当前产品端口的明确回复；禁止根据页面内容、尺寸、文件名、现有框架或配置自行判断。用户回复前不得继续，回复后按功能一相同的 Manifest 端口映射选择设备框架。
19. 功能四编辑非本 Skill 生成的 HTML 时，必须解析入口 HTML 及关联 HTML/CSS/JS/资源，直接生成 `prototype/docs/Spec.md`；不得调用 `brainstorming-solo` 或 `grill-me`。Spec 确认后复用功能一阶段二、阶段三；静态高保真原型完成后必须停止，只有再次获得用户明确确认才进入功能三。
20. 功能四接管 PNG/JPG 等整页图片时，必须将用户原图及确认后的固定区位图片段保存到 `prototype/assets/images/`，静态 `pages/**/*.html` 与功能三 `runtime-pages/**/*.html` 均从该目录使用同层级相对路径引用；不得继续把图片放在或引用为 `pages/source-images/`。默认先生成仅以完整原图为视觉内容的承载页和 `index.html`；只有用户明确提出固定区域并确认边界时，才可将原图无损位图分割为固定区与可滚动区，禁止将图片解构、OCR 还原或重绘为页面元素。图片运行时热区只写入副本，默认透明，鼠标悬停或键盘聚焦时必须显示半透明虚线轮廓。生成 `prototype.html` 前必须在静态产物完成后再次获得用户确认。
21. 功能五复用功能三的运行时页面和 `ycet-prototype` 消息协议。已有 `runtime-pages/**/*.html`、`pages/**/*.html`、`index.html`、`prototype.html`、框架、资源和其他项目文件均为只读输入；打包阶段只允许新增一个递增命名的 `prototype-mobile*.html`，不得覆盖旧版本或更新 EditLog。只有完全缺少运行时页面且已向用户确认页面跳转逻辑时，才可在打包前创建全新的 `runtime-pages/`；部分存在、目标悬空或来源冲突必须停止。

## 框架资产

- 唯一数据真源：`assets/frames/manifest.json`
- 框架说明：`assets/frames/README.md`
- 微信小程序默认映射 `iphone-15-pro`；仅当用户明确指定 Android 宿主时映射 `android-pixel`。
- 生成项目时只复制选中框架，并写入 `prototype/assets/frames/frame-config.json`。
- 生成文件必须使用相对路径，不得依赖本 Skill 的安装绝对路径；运行时页面路径统一以 `prototype/` 为 URL 根，具体格式读取 `docs/shared-prototype-standards.md`「路径与文件名契约」。

## 完成说明

每次完成后说明：

- 本次使用的功能；
- 生成或修改的文件及用途；
- 查看或继续方式；
- 使用的框架 ID；
- 内容图/图标是否已本地化，以及是否发生语义降级或近似顶替；
- 是否已记录 EditLog；
- 功能五须额外说明集成页面数、内联资源数、文件大小、只读校验与浏览器/真机验证结果；按单文件只写约束明确标注未修改 EditLog；
- 尚未解决的限制或待确认事项。
