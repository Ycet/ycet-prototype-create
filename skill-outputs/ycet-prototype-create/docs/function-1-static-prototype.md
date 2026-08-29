# 功能一：从产品需求到高保真静态原型

## 目标与产物

根据产品想法、零散需求或 PRD，按确认门禁生成：

```text
prototype/
  docs/Spec.md
  docs/EditLog.md
  design-direction.html
  previews/home-preview.html
  index.html
  pages/*.html
  assets/frames/frame-config.json
  assets/frames/<selected-frame>.html
  assets/images/
  assets/icons/
```

涉及原型写入时读取 `shared-editlog-rules.md`；生成 HTML 前读取 `shared-prototype-standards.md` 与 `../assets/frames/manifest.json`。

## 阶段一：产品需求完善

### 输入分类

| 输入类型                  | 必须动作                                 |
| --------------------- | ------------------------------------ |
| 产品想法、零散需求、口述功能、未成体系材料 | 先读取并整理已有材料，再进入“一次一问提问协议”             |
| 结构化 PRD、需求说明书、较完整功能清单 | 先读取已有结论，只针对缺口进入“一次一问提问协议”，不得重复确认已有结论 |
| 无法判断完整度               | 按需求缺口审计处理，进入“一次一问提问协议”               |

阶段一不调用任何外部需求访谈 Skill。一次一问提问和需求完整度审计未结束前，不生成 `Spec.md`，也不提前进入 UI 设计。

### 阶段一强制范围

阶段一只澄清产品问题：产品端口、背景与定位、目标用户、使用场景、页面清单、信息与功能、业务流程、业务规则、边界条件和异常处理。页面元素可以按“需要什么信息或操作”讨论，但不得讨论其视觉呈现。

本阶段只通过当前 Agent 的内置提问框完善产品需求。禁止询问、推荐、比较或确定 UI 设计风格、设计语言、色彩、字体、排版观感、视觉布局、图标/插画/图片风格、动效风格、视觉参考对象和 UI Skill；不得启动视觉伴侣或生成视觉方向。上述内容全部留到 YCET 功能一阶段二。

阶段一禁止：

- 询问“喜欢什么风格、颜色、字体、品牌调性或参考网站视觉”；
- 推荐 UI 风格、设计系统、配色、字体组合或视觉素材；
- 发现、选择或调用 UI 设计类 Skill；
- 将视觉结论写成阶段一的确认项或 Spec 决策。

如果用户主动提供 UI 偏好，只按原意记录到 Spec 的“阶段二待处理输入”，不追问、不细化、不确认；阶段一结束前再审计一次，不得残留已确认的 UI 设计决策。

### 一次一问提问协议

阶段一必须由当前 Agent 的内置提问框承载提问和回答建议，不得调用外部需求访谈 Skill。每一轮严格只问一个问题，用户也可以不选择建议而手动输入回答。

每轮必须遵循以下规则：

1. 只选择当前最高优先级的一个需求缺口、矛盾或未决业务规则，不把多个主题合并成一个问题。
2. 在内置提问框中提供 3–4 个互斥或足够区分的回答建议；建议中必须恰好一个标记为“（推荐）”，推荐项应说明它为何最适合当前已知上下文。
3. 保留手动输入入口；用户手动输入后，按用户原意记录，不擅自替换为推荐项。
4. 问题必须使用产品语言，明确说明回答对象和影响范围；不要用“还有什么”“请继续补充”等无法收敛的泛问句。
5. 记录本轮答案及其依据，更新需求矩阵后再决定下一轮最高优先级缺口；不得预先展示一组问题等待用户一次性回答。

推荐的单轮展示结构如下，实际交互通过内置提问框呈现：

```text
第 N 轮 / 常规目标 10-30 轮
主题：<本轮唯一主题>
问题：<只包含一个可回答的问题>
回答建议：
1. <建议 A>（推荐）
2. <建议 B>
3. <建议 C>
4. <建议 D，可选>
```

### 提问轮次与完整度判断

1. 常规提问目标为 10–30 轮。轮次是控制访谈深度的范围，不是为了凑数；已有 PRD 中明确的结论直接记录，不重复提问。
2. 每轮结束后都要检查需求矩阵。矩阵至少覆盖：产品端口与宿主设备、背景与定位、目标用户、使用场景、页面清单、页面元素与操作、页面状态、交互逻辑、业务流程、业务规则、权限与数据约束、边界条件、空/加载/禁用状态、异常处理、页面间关系和待确认事项。
3. 当轮次达到 10 轮前已无关键缺口时，必须再做一次覆盖审计；若所有字段均有明确结论且用户确认汇总，可以提前结束，不继续填充低价值问题。
4. 达到 10 轮仍存在关键缺口时继续提问；达到 30 轮仍存在关键缺口时停止无效追问，列出阻塞项并请求用户补充，不生成未经确认的 `Spec.md`。
5. 结束提问的标准不是固定轮数，而是：需求矩阵已覆盖交互逻辑、页面元素、边界条件、业务规则和异常处理；核心页面和流程没有未决的关键歧义；所有主动给出的 UI 偏好均只进入“阶段二待处理输入”；Agent 汇总完整需求并获得用户确认。

提问结束时，先展示需求摘要、页面清单、核心流程、业务规则、边界与异常处理、待确认事项和实际提问轮数，再询问用户是否确认进入阶段二。用户未确认时，只针对其指出的缺口继续一次一问，不得生成 `Spec.md`。

### Spec 生成门槛

仅当以下条件成立时生成 `prototype/docs/Spec.md`：

1. 产品端口已确定；微信小程序还需记录宿主设备。
2. 页面清单可列出。
3. 每个核心功能至少覆盖功能说明、页面元素、业务流程和异常处理。
4. 核心页面流转关系可描述。
5. 最终框架 ID 可根据 Manifest 唯一确定。
6. 未确定内容进入“待确认事项”。
7. 一次一问提问已结束，完整度审计通过，且用户已确认需求摘要。

Spec 重点记录页面、组件、页面内交互、页面间流程、异常、业务规则、边界、产品端口、宿主设备和框架 ID。用户主动给出的 UI 偏好只能原样进入“阶段二待处理输入”，不得在阶段一细化。用户确认后才能进入阶段二。

## 阶段二：UI 设计方向

### 发现 UI 相关 Skill

按顺序发现：

1. 当前会话提供的 Skill 清单；
2. `~/.agents/skills/`；
3. `~/.codex/skills/`；
4. `~/.claude/skills/`。

读取可访问 `SKILL.md` 的 `name` 与 `description`，按名称、真实路径和 junction 去重。某个来源不可访问时继续其他来源；所有来源均无结果时如实说明，不使用示例冒充已安装 Skill。

展示全部结构有效的 UI 相关 Skill，不按生成、品牌、审核或润色类型过滤。每项至少展示：

- 名称与功能摘要；
- 类型和适用场景；
- 来源与当前可调用状态；
- 前置条件；
- 特殊预览链接。

用户一次只能选择一个主 UI Skill，也可以选择“不使用 Skill”。已安装但不可调用的 Skill必须标注；用户选择后要求重新选择或不使用 Skill，不擅自替换。

### 特殊链接

- 选择 `ui-design-system-governor`：始终提供 <https://open-design.ai/zh/plugins/systems/>。
- 选择 `ui-ux-pro-max`：始终提供 <https://ui-ux-pro-max-skill.com/zh/#styles>。
- 仅在用户明确要求且环境支持时打开；失败时保留可点击链接并继续。

### 选择 Skill

完整读取并遵循所选 Skill 的输入要求、输出格式和确认门禁。生成 `design-direction.html` 前允许更换；生成后更换必须重新生成并重新确认。

### 不使用 Skill

每轮只问一个主题，顺序固定为：

1. 是否有参考产品或网站；
2. 设计风格；
3. 色彩方案；
4. 其他补充要求。

用户回答没有参考对象后直接进入设计风格。全部确认后汇总设计方向并请求确认。

### 生成设计方向与首页预览

1. 读取 Manifest，根据端口、宿主设备选择唯一框架。
2. 若 Manifest 缺失、无效、版本不支持或框架文件不存在，停止并报告，不回退旧尺寸。
3. 只复制选中框架到 `prototype/assets/frames/`。
4. 按共享规范的字段映射，将选中 Manifest 条目、Manifest 顶层路径字段和已确认端口/宿主合并写入 `prototype/assets/frames/frame-config.json`；`frameFile` 保留 Manifest `file` 中已有的 `.html` 扩展名。
5. 生成 `prototype/previews/home-preview.html`；页面只包含产品 UI，并按 `safeArea` 避让系统 UI。
6. 生成 `prototype/design-direction.html`。
7. 不启动工作台；用户后续明确选择功能二时，再由功能二扫描并打开本次生成的 HTML。

`design-direction.html` 至少包含色彩、字体、按钮、反馈组件、必要补充组件和一个合并后的“首页预览”。首页预览通过以下模式加载：

```html
<iframe
  data-ycet-frame-id="<frame-id>"
  src="assets/frames/<frame-file>?screen=previews/home-preview.html"
  title="首页预览"
  width="<preview.width>"
  height="<preview.height>"
  scrolling="no"
  style="width:<preview.width>px;height:<preview.height>px;border:0;display:block;overflow:hidden;"
></iframe>
```

宽高必须替换为当前框架 `preview` 固定像素，不得二次缩放。不得另设“设备框架预览”模块，也不得展示其他正式页面。用户确认后才能进入阶段三。

## 阶段三：静态原型生成

### 实现计划门禁

写 HTML 前，先展示并请求确认：

- 页面文件清单与功能映射；
- 产品端口、宿主设备、框架 ID；
- 逻辑画布、预览尺寸和默认列数；
- 只实现页面内交互，不实现跨页面跳转；
- 内容图数量与主要语义类别、图标本地化方案；
- 资源目录 `assets/images/` 与 `assets/icons/`；
- 图片失败策略：严格→大类→非匹配兜底，下载失败近似图顶替，禁止灰占位；
- 共享规范与日志规则；
- 路径、尺寸、溢出、交互、图片、框架配置和日志验证项。

### 生成规则

- 正式页面写入 `prototype/pages/*.html`。
- 新页面与预览文件名使用小写 ASCII kebab-case；未来跨页目标只写为 `data-ycet-nav-target="pages/<file>.html"` 意图元数据，不在静态页中发送导航消息。
- 页面根画布匹配 `frame-config.json.logicalViewport`。
- 页面不得绘制系统 UI；App 导航、Tab Bar、微信胶囊按钮、网站导航等产品 UI保留。
- 生成 HTML 前列出内容图位与图标需求，按 `shared-prototype-standards.md`「图片与图标」下载到本地并只写相对路径。
- 建议维护 `assets/images/images-manifest.json`。
- 阶段二已下载的图可在阶段三复用；缺图按语义阶梯补齐。
- `prototype/index.html` 使用选中框架的 `?screen=pages/<file>.html` 加载每个页面，并设置 `data-ycet-frame-id`。
- 每个 `pages/**/*.html`、`previews/**/*.html` 与 `index.html` 必须使用项目内或内联 CSS/JS，禁止生成 Tailwind CDN 等远程运行时依赖；工作台仅在用户后续通过功能二打开时扫描这些文件。
- `index.html` 与 `design-direction.html` 中的框架 iframe 宽高必须等于 `frame-config.json.preview` 固定像素；禁止百分比、外层 scale 或 overflow 小盒二次适配；滚动分层遵守 `shared-prototype-standards.md`「`index.html`」专节。
- 默认列数读取 Manifest：手机/微信宿主 4、iPad 2、Browser/MacBook 1；小屏幕可减少列数，不改变逻辑画布与 preview 像素。
- 每张页面卡片保留页面名、文件名和“打开页面html”链接。
- `pages/**/*.html` 与 `previews/**/*.html` 只实现页面内状态变化：Tab、弹窗/抽屉、Toast、表单校验、loading、折叠、轮播、筛选和排序等均可工作，但操作前后必须仍停留在同一 HTML 文档。
- 代表未来跨页动作的控件保留视觉与可访问语义，优先使用 `<button type="button" data-ycet-nav-target="pages/detail.html">`；功能一中不得为该控件绑定跨页处理器。`data-ycet-nav-target` 只是功能三读取的声明，不是导航实现。
- 静态页禁止使用 `<a href="其他页面">`、表单跨页 `action`、`location.href`、`location.assign()`、`location.replace()`、`window.open()`、`history.pushState()`、路由器跳转、`window.top`、`parent.location`，以及发送 `type: "navigate"` 的 `postMessage`。同文档 `#fragment` 可用于页面内交互。
- `index.html` 不执行产品跨页导航；卡片中的“打开页面html”是用于检查独立交付文件的工具链接，不属于产品交互，是唯一例外。

### 静态交互验收门禁

生成完成后必须运行 `scripts/prototype_guard.py static --prototype-dir <prototype目录>`，并人工复核所有 `data-ycet-nav-target` 都指向已登记的 `pages/*.html`。发现任一主动导航实现即视为功能一未完成，必须只移除跨页实现，不得删除页面内交互或导航控件视觉。

### 完成标准

- 设计方向、首页预览、静态页面、入口、框架文件和项目配置均存在且路径有效。
- Manifest、`frame-config.json`、`Spec.md` 和 `data-ycet-frame-id` 一致。
- 框架系统 UI 与页面产品 UI 不重复。
- 框架 iframe 尺寸等于 preview 固定像素；无框架原生滚动条、裁剪或留白；产品页仅内部容器滚动。
- Chrome、Edge 与 Firefox 中均不显示浏览器原生滚动条；需要滚动的阵列和页面内部容器仍可通过滚轮、触控与键盘滚动。
- 静态交互验收通过；`pages/**/*.html` 与 `previews/**/*.html` 不含主动跨页实现，跨页控件仅保留安全的 `data-ycet-nav-target`。
- `design-direction.html`、正式静态页与 `index.html` 已完成，供用户后续通过功能二打开工作台时扫描；工作台预览或草稿操作未改变其源文件摘要。
- 内容图与网络图标已本地化；无未授权外链与占位图。
- 断开外网后页面内容图与图标仍可显示。
- 语义降级/近似顶替（若有）已在完成说明列出。
- 本地 HTML 与本地静态服务器均可打开。
- 将整个 `prototype/` 移动目录后仍可加载。
- `EditLog.md` 记录阶段二和阶段三生成动作。
- 完成后说明可在后续单独使用功能三生成交互 Demo。

