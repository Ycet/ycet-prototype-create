---
name: ycet-prototype-create
description: Use when the user needs product prototype creation, prototype page editing, interactive demo generation, or normalization/editing of existing HTML or image prototypes.
---

# YCET Prototype Creator

产品原型制作入口 skill。读取本文件后，必须先完成功能路由；除非路由规则要求，否则不要提前读取 `docs/` 下的功能细节文件。

## 路由总则

每次用户调用本 skill 后，必须先判断是否存在直接路由信号。

### 直接路由信号

若用户同时提供：

- 浏览器开发者工具复制的 CSS 选择器；
- 对应 HTML 片段；
- 明确要求修改某个页面元素；

则不再询问功能选择，直接读取并执行 `docs/function-2-precision-edit.md`。

若用户明确指定“功能一 / 功能二 / 功能三 / 功能四”或对应功能名称，也不再重复询问，直接读取对应功能文件。

### 默认选择问题

若无法直接路由，必须先向用户提问：

> 需要使用 ycet-prototype-create 的哪个功能？

可选项：

| 选项 | 功能 | 读取文件 |
| --- | --- | --- |
| A | 功能一：从「产品需求」到「高保真静态原型页面」 | `docs/function-1-static-prototype.md` |
| B | 功能二：通过浏览器开发者工具精准修改原型 | `docs/function-2-precision-edit.md` |
| C | 功能三：从「高保真静态原型页面」到「可交互原型demo」 | `docs/function-3-interactive-demo.md` |
| D | 功能四：HTML或图片原型规范化重构与编辑 | `docs/function-4-existing-prototype-edit.md` |

用户选择后，只读取对应功能文件及该功能文件要求的共享规范文件。

## 功能判定辅助表

| 用户意图或材料 | 功能 |
| --- | --- |
| 从 0 到 1 制作原型、根据产品想法/需求/PRD 生成高保真静态页面 | 功能一 |
| 提供 CSS 选择器 + HTML 片段，要求精准调整元素 | 功能二 |
| 已有 `prototype/index.html` 与 `prototype/pages/*.html`，要求生成完整页面间跳转 demo | 功能三 |
| 需要接管非本 skill 生成的 HTML 原型，或基于图片原型生成/编辑原型 | 功能四 |

## 全局强制规则

1. 单次任务只能执行一个功能；若用户需求跨功能，先完成当前功能并说明下一步。
2. 所有原型相关产物必须放在项目根目录的 `prototype/` 下。
3. `Spec.md` 必须保存为 `prototype/docs/Spec.md`。
4. `EditLog.md` 必须保存为 `prototype/docs/EditLog.md`。
5. 凡写入或修改 `prototype/index.html`、`prototype/prototype.html`、`prototype/prototype-vN.html`、`prototype/pages/*.html`，或生成承载图片原型的 HTML 页面，都必须按 `docs/shared-editlog-rules.md` 记录。
6. 即使用户后续没有主动调用本 skill，只要修改上述原型 HTML 文件，也必须记录 `EditLog.md`。
7. 若功能文件要求用户确认，未确认前不得进入下一阶段。
8. 与用户交流使用中文；原型界面文字按产品实际需要决定。
9. 关键 HTML/CSS/JS 代码必须添加中文注释。
10. 不确定的信息必须写入“待确认事项”或向用户确认，不得编造。

## 共享规范按需读取

- 涉及生成、重构或验证原型 HTML 时，读取 `docs/shared-prototype-standards.md`。
- 涉及任何原型 HTML 或图片承载页面的写入/修改时，读取 `docs/shared-editlog-rules.md`。

## 完成后说明

每次完成操作后，向用户说明：

- 本次使用的功能；
- 生成或修改了哪些文件；
- 文件位置和用途；
- 如何查看或继续下一步；
- 是否已记录 `EditLog.md`。
