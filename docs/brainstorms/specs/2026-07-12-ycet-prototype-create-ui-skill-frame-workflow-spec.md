---
title: YCET Prototype Create UI Skill 发现与设备框架体系优化
date: 2026-07-12
status: approved
topic: ycet-prototype-create-ui-skill-frame-workflow
source_skill: brainstorming-solo
related_plan: ../plan/2026-07-12-ycet-prototype-create-ui-skill-frame-workflow-plan.md
---

# Agent 交接摘要

- 目标：优化 `ycet-prototype-create` 的功能一需求完善与 UI 设计流程，并建立由 Manifest 驱动、可被功能一/三/四共同复用的设备框架体系。
- 已确认方案：不完整需求改用 `brainstorming-solo`；混合发现并展示全部 UI 相关 Skill；用户一次选择一个主 Skill；设备框架按需复制；框架负责系统 UI；使用 `manifest.json` 作为框架库唯一真源，并为生成项目写入 `frame-config.json` 快照。
- 范围边界：覆盖功能一、共享规范、功能三、功能四、总入口、README、EditLog 规则及相关评估规则；不改变功能三和功能四的既有业务流程。
- 明确不做：不修改功能二业务逻辑；不自动安装 UI Skill；不自动打开外部网页；不允许多个主 UI Skill；不自动发布、安装、提交或执行优化实现。
- 验收标准摘要：UI Skill 发现与降级可执行；端口映射正确；Manifest、框架源码和 README 一致；设计方向页、静态入口和交互 Demo 共用框架体系；双层 iframe 双向通信可用；旧框架兼容；本地文件和静态服务器两种方式均可运行；生成目录可独立移动。
- 待决问题：无。
- 相关计划：`../plan/2026-07-12-ycet-prototype-create-ui-skill-frame-workflow-plan.md`。

# 背景与目标

## 背景

当前 `ycet-prototype-create` 已拆分为总入口、四个功能文档和共享规范。功能一仍在不完整需求场景调用 `superpowers:brainstorming`，阶段二仅笼统询问用户是否指定 UI Skill。现有静态原型依赖 `.phone-frame`、`.android-frame` 等 CSS 模拟框架，框架类型、页面尺寸和设备外壳规则散落在多个文档中。

项目根目录已有五个可复用框架 HTML，但尚未纳入 Skill 包，且框架源码、README 与共享规范的尺寸存在冲突。新框架通过 `?screen=` 嵌套页面，会令交互 Demo 从单层 iframe 变为“外层 Demo → 设备框架 → 页面”的双层 iframe；如果不同时调整功能三和功能四，将导致框架识别、双向导航和旧原型接管不一致。

## 目标

1. 将功能一的不完整需求完善流程切换为 `brainstorming-solo`。
2. 在功能一阶段二动态发现、分析和展示当前 Agent 的全部 UI 相关 Skill。
3. 让用户明确选择一个主 UI Skill，或选择不使用 Skill 并逐项确认设计方向。
4. 将设备框架作为 Skill 内置资产，按产品端口复制到生成项目。
5. 以 `manifest.json` 统一端口、逻辑画布、预览尺寸、安全区域、系统 UI 和加载协议。
6. 让 `design-direction.html`、`index.html` 和交互 Demo 复用同一套框架。
7. 让功能三、功能四兼容新框架，同时保留旧框架兼容模式。
8. 保证生成的 `prototype/` 不依赖 Skill 安装绝对路径，可独立移动、压缩和交付。

# 用户场景

1. 用户只提供产品想法或零散需求，Agent 使用 `brainstorming-solo` 逐项完善需求，再生成并确认 `Spec.md`。
2. 用户进入 UI 设计阶段，Agent 展示当前会话和本地环境中可发现的所有 UI 相关 Skill，说明其用途、来源、调用状态和前置条件。
3. 用户选择一个 UI Skill，Agent按该 Skill 的规则确定设计方向；或用户选择不使用 Skill，从参考产品/网站开始逐项确认设计风格和色彩。
4. Agent 使用产品端口对应的真实设备框架生成设计方向页首页预览，并在设计确认后生成静态页面阵列。
5. 用户随后调用功能三，Agent 读取项目框架配置并生成双向同步的交互 Demo。
6. 用户接管旧 CSS 框架或非本 Skill 生成的原型，功能四按 Manifest 体系审计并分级迁移。

# 已确认需求

## 功能一阶段一

- 一句产品想法、零散需求、口述功能点或未成体系需求文档必须读取并使用 `brainstorming-solo`。
- 无法判断是否为完整 PRD 时，按不完整需求处理并使用 `brainstorming-solo`。
- 结构化 PRD、需求说明书或较完整材料继续使用 `grill-me`。
- 被调用 Skill 未完成前不得生成 `prototype/docs/Spec.md`。
- `Spec.md` 未经用户确认不得进入阶段二。

## UI Skill 发现

- 采用混合发现：优先读取当前会话提供的 Skill 清单，再扫描 `~/.agents/skills/`、`~/.codex/skills/`、`~/.claude/skills/`。
- 读取 `SKILL.md` 的 `name`、`description` 等元数据，按 Skill 名称、真实路径和 junction 情况去重。
- 所有结构有效的 UI 相关 Skill 都必须展示且可选，不因属于生成、规范、品牌、审核或润色类型而隐藏。
- 每个 Skill 至少展示名称、功能摘要、类型、适用场景、来源、当前可调用状态、前置条件和特殊链接。
- 用户一次只能选择一个主 UI Skill。所选 Skill 对本轮设计方向拥有唯一指导权。
- 用户可以在生成 `design-direction.html` 前更换主 Skill；生成后更换必须重新生成并确认设计方向。
- Skill 已安装但当前不可调用时仍可展示，但必须明确标注；用户选择后不得擅自替换为相似 Skill。

## 特殊 UI Skill 链接

- 选择 `ui-design-system-governor` 时必须提供 `https://open-design.ai/zh/plugins/systems/`。
- 选择 `ui-ux-pro-max` 时必须提供 `https://ui-ux-pro-max-skill.com/zh/#styles`。
- 链接必须以可点击形式出现在回复中。
- 仅当环境支持且用户明确要求时代为打开；打开失败不阻塞流程，也不得编造网页内容。

## 不使用 UI Skill

- 采用逐项询问，每轮只推进一个主题。
- 第一问固定为是否有参考产品或网站，接受产品名称、URL、截图或“没有”。
- 后续顺序为：设计风格、色彩方案、其他补充要求。
- 用户回答没有参考对象后直接进入设计风格，不重复追问。
- 全部问题完成后汇总设计方向并请求确认。

## 首页预览与正式首页

- `design-direction.html` 中原“设备框架预览”和“首页 UI 效果展示”合并为“首页预览”。
- 阶段二生成独立的 `prototype/previews/home-preview.html`。
- 首页预览通过当前端口框架的 `?screen=` 加载该预览页。
- 阶段三再生成正式 `prototype/pages/home.html`。
- 预览页保留为设计基线，不加入 `index.html` 页面阵列，也不进入功能三交互流程。

## 框架资产与按需复制

- 标准框架库存放于 `skill/ycet-prototype-create/assets/frames/`。
- 框架库包含 `manifest.json`、`README.md`、`iphone-15-pro.html`、`android-pixel.html`、`ipad-pro.html`、`browser-chrome.html`、`macbook.html`。
- 生成原型时只复制当前项目使用的框架到 `prototype/assets/frames/`。
- 同时生成项目配置快照 `prototype/assets/frames/frame-config.json`。
- 所有生成页面使用相对路径，不写入 Skill 安装目录绝对路径。

## 系统 UI 与产品 UI

- 框架负责状态栏、灵动岛、Home Indicator、Android 系统导航栏、浏览器外壳等系统级 UI。
- `pages/*.html` 和 `previews/*.html` 只负责产品 UI。
- App 顶部导航、产品 Tab Bar、微信导航栏、胶囊按钮、网站导航和桌面应用菜单仍由页面负责。
- 页面必须根据 Manifest 中的安全区域安排产品 UI，不得重复绘制系统 UI。

## 端口映射

- iOS / iPhone 使用 `iphone-15-pro.html`。
- Android 使用 `android-pixel.html`。
- iPad 使用 `ipad-pro.html`。
- Web 使用 `browser-chrome.html`。
- Windows 和 macOS 桌面应用使用 `macbook.html`。
- 微信小程序默认使用 `iphone-15-pro.html`；用户明确指定 Android 宿主时切换为 `android-pixel.html`。
- `Spec.md` 必须分别记录产品端口、宿主设备和最终框架 ID。

## 框架逻辑画布

- `iphone-15-pro`：`390×844`。
- `android-pixel`：`412×900`。
- `ipad-pro`：`834×1194`。
- `browser-chrome`：`1440×900`。
- `macbook`：`1440×900`。
- Manifest 同时记录逻辑画布、预览尺寸、缩放比例、安全区域和系统 UI。
- 安全区域必须从最终框架源码测量和验证，不得把未经验证的示例数值写成事实。

## 下游兼容

- 功能三优先读取 `frame-config.json`，使用框架 ID 和项目配置生成交互 Demo。
- 功能三不再将旧 CSS 框架类作为新原型的主要识别方式。
- 功能四按 Manifest 审计框架文件、逻辑画布、安全区域和系统 UI 归属。
- 功能三和功能四的业务流程、文件命名、交互确认和分级重构门禁保持不变。
- 旧 CSS 框架仅作为已有项目的兼容线索。

## EditLog

- `prototype/design-direction.html`、`prototype/previews/*.html`、`prototype/index.html`、`prototype/pages/*.html`、交互 Demo、`frame-config.json`、项目内框架文件和图片承载页面的生成或修改均须记录 `prototype/docs/EditLog.md`。
- 阶段二记录“生成 UI 设计方向、首页预览及项目框架配置”。
- 阶段三记录“生成静态原型页面和页面阵列”。
- 功能三、功能四及框架升级按具体动作记录。
- Skill 源目录的框架库开发不写入某个原型项目的 EditLog。

# 范围与非范围

## 范围

- `skill/ycet-prototype-create/SKILL.md` 的端口、目录和共享规则。
- 功能一的需求完善、UI Skill 选择、首页预览和静态页面生成规则。
- 共享原型规范与 EditLog 规则。
- 框架 HTML、Manifest 和框架 README。
- 功能三的新框架识别、复用和双层 iframe 通信。
- 功能四的新框架审计、迁移和修复规则。
- 项目 README、Agent 元数据以及仍在项目范围内的相关评估规则。
- 新旧框架兼容和可移植性验证。

## 非范围

- 不修改功能二精准编辑的业务逻辑。
- 不自动安装、下载、删除或升级 UI Skill。
- 不使用固定白名单代替动态发现。
- 不允许一次选择多个主 UI Skill。
- 不自动打开外部网页。
- 不重设计功能三或功能四的业务流程。
- 不自动发布或安装新版 Skill。
- 不自动执行 Git add、commit、push 或 PR。
- 本纪要本身不授权开始实现。

# 方案比较与最终决策

## 方案 A

- 做法：使用 `manifest.json` 维护框架库统一数据契约，并在生成项目中写入选中框架的配置快照。
- 优点：数据真源唯一；功能一、三、四可稳定复用；新增框架只注册一次；可增加自动验证。
- 代价/风险：Manifest 与框架源码可能漂移，需要一致性验证。

## 方案 B

- 做法：在每个框架 HTML 中使用 `<meta>` 或 `data-*` 自描述规格，由各功能解析 HTML。
- 优点：框架文件自身携带规格，按需复制时无需额外清单。
- 代价/风险：解析脆弱、字段扩展困难、跨功能重复解析，错误发现较晚。

## 方案 C

- 做法：继续在共享规范和各功能文档中分别硬编码框架映射与尺寸。
- 优点：不增加新文件，短期修改量较小。
- 代价/风险：多处重复维护，容易再次发生规范与源码不一致，不符合唯一真源目标。

## 最终决策

采用方案 A：以 Skill 框架库中的 `manifest.json` 为机器可读唯一真源；生成项目保存 `frame-config.json` 快照。框架 HTML、Manifest 和 README 必须同步验证。

# 设计说明

## 核心流程

1. 功能一阶段一根据输入完整度调用 `brainstorming-solo` 或 `grill-me`，完成后生成并确认 `Spec.md`。
2. 阶段二混合发现 UI Skill，展示全部有效候选，用户选择一个主 Skill或不使用 Skill。
3. 所选 Skill 完成自身流程，或按参考产品/网站、设计风格、色彩、补充要求逐项确认设计方向。
4. 根据端口和宿主设备读取 Manifest，按需复制框架，生成 `frame-config.json`、首页预览和 `design-direction.html`。
5. 用户确认设计方向页后，阶段三展示实现计划；确认后生成正式页面、`index.html` 和 EditLog。
6. 功能三读取项目框架配置和交互流程，使用新框架生成双向同步 Demo。
7. 功能四按 Manifest 审计新原型，或按兼容模式识别并分级迁移旧框架。

## 模块、组件或接口边界

### Skill 框架库

```text
skill/ycet-prototype-create/assets/frames/
  manifest.json
  README.md
  iphone-15-pro.html
  android-pixel.html
  ipad-pro.html
  browser-chrome.html
  macbook.html
```

### 生成项目

```text
prototype/
  design-direction.html
  index.html
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

### iframe 加载接口

- 所有框架必须支持 `?screen=<encoded-relative-path>`。
- `screen` 是所有框架唯一必需查询参数；可选装饰参数不能成为功能一、三、四的依赖。
- 外层框架 iframe 使用 `data-ycet-frame-id` 标记框架 ID。
- 页面路径相对于承载框架的外层页面解析，并且必须在允许的预览或页面目录内。

### 消息接口

统一消息包含：

- `channel: "ycet-prototype"`
- `version: 1`
- `type`
- 对应的目标页面或状态数据

必要类型为 `ready`、`navigate`、`set-screen`、`screen-changed`、`error`。

- 页面向设备框架发送导航消息。
- 设备框架验证来源并向外层 Demo 中继。
- 外层 Demo 验证页面白名单、同步左侧导航，并向框架发送 `set-screen`。
- 页面不得依赖 `window.top` 绕过框架。

## 数据与状态

### Manifest

Manifest 顶层至少包含：

- `schemaVersion`
- `screenQueryParameter`
- `frames`
- `routing`

每个框架至少包含：

- `id`
- `displayName`
- `file`
- `platforms`
- `logicalViewport`
- `preview`
- `safeArea`
- `systemChrome`
- `productUiResponsibilities`

路由数据记录默认框架和微信小程序的宿主覆盖规则。

### 项目框架配置

`frame-config.json` 至少包含：

- `schemaVersion`
- `frameId`
- `frameFile`
- `productPort`
- `hostDevice`
- `logicalViewport`
- `preview`
- `safeArea`
- `screenQueryParameter`

该文件是生成项目的稳定配置快照。Skill 框架库升级不得静默改变已交付项目；只有重新生成或明确迁移时更新快照。

### 页面状态

- `design-direction.html` 只加载首页预览，不执行跨页面导航。
- `index.html` 每张卡片独立加载页面，保留页面内交互，不执行跨页面导航。
- 交互 Demo 由外层统一维护当前页面、左侧高亮和返回历史。
- 页面阵列默认列数：手机/微信宿主 4，iPad 2，Browser/MacBook 1；小屏幕可减少列数，但不得改变逻辑画布。

## 错误处理与边界情况

### UI Skill

- 某个发现来源不可访问时继续扫描其他来源。
- 同名多版本优先当前会话可调用版本，其次真实安装目录；junction 不重复展示。
- 所有来源均无结果时如实说明，进入“不使用 Skill”分支。
- 不可调用 Skill 需标注；用户选择后要求重新选择或不使用 Skill，不得自动替换。

### Manifest 与框架

- 新原型生成时，Manifest 缺失、无效或版本不支持必须阻止生成，不得回退旧文档尺寸。
- Manifest 指向文件缺失、尺寸不符、缺少 `screen` 协议、安全区域不符时，功能一和功能三停止，功能四报告差异。
- 项目配置存在但无效时不得静默跳过；可以推导候选配置，但修复前必须请求用户确认。
- 功能三识别顺序为：项目配置、`index.html` 框架 ID、框架文件名、`Spec.md` 端口与宿主，仍不唯一时向用户确认。

### 路径与通信

- 只允许相对项目路径，不允许任意远程 URL、绝对文件路径或 `javascript:` URL。
- 页面切换失败时保留当前页面并报告错误。
- 消息必须校验 channel、version、type、`event.source` 和页面白名单。
- 本地 `file://` 可能产生 `origin: "null"`，安全判断不得只依赖 origin 字符串。

### 旧原型

- 功能三可以按旧框架兼容模式继续生成 Demo，但必须明确标注。
- 功能四 Level 1 补齐新框架与配置，Level 2 修复尺寸/滚动/安全区域/重复系统 UI，Level 3 才规范化重写并请求确认。
- 旧原型兼容不得把旧尺寸写回 Manifest。

# 验收标准

1. 不完整需求已改为调用 `brainstorming-solo`，完整 PRD 仍调用 `grill-me`。
2. UI Skill 发现覆盖会话清单、本地目录、重名、junction、无效 Skill、不可调用 Skill和零结果场景。
3. 用户只能选择一个主 UI Skill；不使用 Skill 时按“参考产品/网站 → 设计风格 → 色彩 → 补充要求”逐项提问。
4. 两个特殊 UI Skill 的链接在对应选择下正确展示，且不会未经允许自动打开。
5. Manifest 可解析、ID 唯一、框架文件存在、尺寸/安全区域/协议与源码一致。
6. 所有已确认端口映射正确，微信小程序默认 iPhone、指定 Android 时覆盖成功。
7. `design-direction.html` 只有合并后的“首页预览”，加载 `previews/home-preview.html`，且无重复系统 UI。
8. `index.html` 使用项目框架和 `data-ycet-frame-id`，按默认列数展示，并保留“打开页面html”链接。
9. 静态入口不实现跨页面跳转，交互 Demo 的左右双向切换、返回历史和错误处理可用。
10. 功能三新框架模式和旧框架兼容模式均通过代表性测试。
11. 功能四覆盖缺配置、配置冲突、旧框架、重复状态栏、尺寸错误、框架缺失及 Level 1/2/3 代表性案例。
12. 设计方向、预览页、静态页面、交互 Demo、框架迁移和配置升级均正确写入 EditLog。
13. 原型可通过本地 HTML 和本地静态服务器打开；整个 `prototype/` 移动目录后仍可加载与通信。
14. 相关评估规则覆盖路由、Skill 发现、端口映射、Manifest 失败、双层 iframe、旧原型兼容和日志。
15. 实施不得覆盖用户已有的无关工作区修改。

# 风险与约束

- Manifest 与框架源码可能漂移，必须增加一致性验证。
- 双层 iframe 可能导致消息丢失、错误来源或左侧状态不同步，必须统一中继协议。
- 本地文件 origin 可能为 `null`，必须联合校验消息来源、协议字段和页面白名单。
- 框架缩放可能造成裁剪、模糊或滚动条，必须区分逻辑画布与预览尺寸并进行视觉验收。
- UI Skill 安装位置和会话可调用状态不完全一致，必须分别展示。
- 旧原型兼容仅面向已有项目，新生成项目不得继续依赖旧 CSS 类。
- 当前工作区可能存在未提交、未跟踪或删除状态；实施前必须检查 Git 状态，只修改本 Spec 范围内文件，不恢复或覆盖用户修改。
- 相关评估文件如在实施时处于用户删除状态，不得擅自恢复；应先核对当前工作区意图，再决定更新方式。

# 待决问题

无。

# 后续交接说明

后续 Agent 在获得用户对本 Spec 的明确批准后，可以据此修改 `ycet-prototype-create` 的入口、功能文档、共享规范、框架库、README 和相关评估规则。实施前必须重新检查当前工作区状态，确认哪些文件属于用户已有修改。

必须遵守：

- 以本 Spec 的已确认需求和范围为边界；
- 先让 Manifest、框架源码和 README 达成一致，再修改功能一、三、四引用规则；
- 保留功能二及功能三/四既有业务流程；
- 为关键 HTML/CSS/JS 添加中文注释；
- 验证本地文件、静态服务器、目录移动、双向通信和旧原型兼容；
- 不自动安装 Skill，不自动发布，不自动执行 Git 提交；
- 不处理与本次优化无关的工作区变更。

本 Spec 已于 2026-07-12 获得用户明确批准。执行护栏计划见 `../plan/2026-07-12-ycet-prototype-create-ui-skill-frame-workflow-plan.md`。
