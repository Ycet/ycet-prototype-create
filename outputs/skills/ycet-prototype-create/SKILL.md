---
name: ycet-prototype-create
description: Create high-fidelity static product prototypes, precisely edit prototype elements, generate interactive multi-page demos, or normalize existing HTML/image prototypes. Use when a user needs product requirements turned into prototype pages, wants UI design skills discovered and applied, provides CSS selectors plus HTML for a targeted edit, requests complete page-to-page interaction, or needs an existing prototype migrated to the bundled Manifest-driven device-frame system.
---

# YCET Prototype Creator

先完成功能路由，再读取对应功能文件。除当前功能明确要求外，不提前加载其他功能细节。

## 路由

### 直接路由

- 用户同时提供 CSS 选择器、HTML 片段和明确元素修改要求：读取 `docs/function-2-precision-edit.md`。
- 用户明确指定功能一/二/三/四或对应名称：直接读取对应文件。

### 默认选择

无法直接路由时，只询问用户选择一项：

| 选项 | 功能 | 文件 |
| --- | --- | --- |
| A | 从产品需求到高保真静态原型 | `docs/function-1-static-prototype.md` |
| B | 通过浏览器开发者工具精准修改原型 | `docs/function-2-precision-edit.md` |
| C | 从静态页面到可交互原型 Demo | `docs/function-3-interactive-demo.md` |
| D | 现有 HTML 或图片原型规范化与编辑 | `docs/function-4-existing-prototype-edit.md` |

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
14. 功能一生成的 `pages/**/*.html` 与 `previews/**/*.html` 只允许页面内交互，禁止任何跨页面或离开当前文档的导航实现；跨页控件只保留 `data-ycet-nav-target` 意图元数据，实际导航只在功能三的运行时副本中实现。
15. 所有生成 HTML 必须遵守共享规范的跨浏览器无可见滚动条契约；不能只依赖 Chromium 的滚动条表现。
16. 功能三将 `prototype/index.html` 与既有 `prototype/pages/**/*.html` 视为只读输入；跨页逻辑写入 `prototype/runtime-pages/`，并在生成前后用 SHA-256 校验受保护输入未变化。

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
- 尚未解决的限制或待确认事项。
