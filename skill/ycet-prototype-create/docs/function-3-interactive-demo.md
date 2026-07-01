# 功能三：从高保真静态原型页面到可交互原型 demo

## 目标

将已完成的静态原型页面转换为完整可交互 demo，生成 `prototype/prototype.html` 或递增版本 `prototype/prototype-vN.html`。

凡涉及原型 HTML 或图片承载页面写入/修改，必须按 `shared-editlog-rules.md` 记录。

## 前置条件

- `prototype/index.html` 已存在。
- `prototype/pages/*.html` 已包含完整静态页面。
- `prototype/docs/Spec.md` 已存在，或用户已明确给出完整页面间交互流程。

## 工作流程

1. 读取 `shared-prototype-standards.md` 与 `shared-editlog-rules.md`。
2. 读取 `prototype/docs/Spec.md`，提取页面间交互流程。
3. 若用户已在当前对话提供完整交互流程，将其与 `Spec.md` 合并为最终流程。
4. 向用户展示整理后的交互流程并请求确认；用户已明确确认时可继续。
5. 读取 `prototype/index.html`，自动识别设备框架类型：`.phone-frame`、`.android-frame`、`.miniapp-frame`、`.browser-frame`、`.desktop-frame`。
6. 读取 `prototype/pages/` 下页面文件，确认文件名与交互流程对应。
7. 确定输出文件名：
   - 首次生成：`prototype/prototype.html`
   - 后续生成：`prototype/prototype-vN.html`
   - 用户指定文件名时使用用户指定名称。
8. 生成左右分栏可交互 demo。
9. 追加 `EditLog.md` 记录。

## 实现规范

- 左侧为页面导航，按交互逻辑分组。
- 右侧居中显示单个设备框架。
- 设备框架必须复用 `prototype/index.html` 已识别出的框架类型、尺寸和 iframe 样式。
- 通过 iframe 加载 `prototype/pages/*.html`，不得直接复制页面 HTML。
- 页面间跳转逻辑集中在 demo 文件脚本中管理。
- 支持左侧点击切换右侧 iframe。
- 若页面内部需要触发父级切换，使用 `postMessage` 或 `window.parent` 通信。

## 禁止事项

- 不得固定写死为 iPhone 框架。
- 不得修改静态页面内容来实现跨页面跳转，除非用户明确要求并记录 EditLog。
- 不得跳过交互流程确认。

## 完成标准

- 生成的 demo 文件位于 `prototype/`。
- 左右分栏布局可用。
- 设备框架与 `index.html` 一致。
- iframe 路径正确。
- `EditLog.md` 已记录生成可交互 demo 文件。
