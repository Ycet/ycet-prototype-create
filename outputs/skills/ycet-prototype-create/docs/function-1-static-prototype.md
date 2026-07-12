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
```

涉及原型写入时读取 `shared-editlog-rules.md`；生成 HTML 前读取 `shared-prototype-standards.md` 与 `../assets/frames/manifest.json`。

## 阶段一：产品需求完善

### 输入分类

| 输入类型 | 必须动作 |
| --- | --- |
| 产品想法、零散需求、口述功能、未成体系材料 | 读取并使用 `brainstorming-solo` |
| 结构化 PRD、需求说明书、较完整功能清单 | 读取并使用 `grill-me` |
| 无法判断完整度 | 按不完整需求处理，使用 `brainstorming-solo` |

被调用 Skill 未结束前，不生成 `Spec.md`，也不提前进入 UI 设计。

### 需求审计与提问

先检查产品端口、产品背景、定位、页面清单、核心功能、页面元素、业务流程、边界条件、异常处理和补充需求。每轮只询问一个最高优先级问题，并提供推荐选项。

### Spec 生成门槛

仅当以下条件成立时生成 `prototype/docs/Spec.md`：

1. 产品端口已确定；微信小程序还需记录宿主设备。
2. 页面清单可列出。
3. 每个核心功能至少覆盖功能说明、页面元素、业务流程和异常处理。
4. 核心页面流转关系可描述。
5. 最终框架 ID 可根据 Manifest 唯一确定。
6. 未确定内容进入“待确认事项”。

Spec 重点记录页面、组件、页面内交互、页面间流程、异常、业务规则、边界、产品端口、宿主设备和框架 ID。用户确认后才能进入阶段二。

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
4. 将选中 Manifest 条目写入 `prototype/assets/frames/frame-config.json`，作为项目配置快照。
5. 生成 `prototype/previews/home-preview.html`；页面只包含产品 UI，并按 `safeArea` 避让系统 UI。
6. 生成 `prototype/design-direction.html`。

`design-direction.html` 至少包含色彩、字体、按钮、反馈组件、必要补充组件和一个合并后的“首页预览”。首页预览通过以下模式加载：

```html
<iframe
  data-ycet-frame-id="<frame-id>"
  src="assets/frames/<frame-file>?screen=previews/home-preview.html"
  title="首页预览"
></iframe>
```

不得另设“设备框架预览”模块，也不得展示其他正式页面。用户确认后才能进入阶段三。

## 阶段三：静态原型生成

### 实现计划门禁

写 HTML 前，先展示并请求确认：

- 页面文件清单与功能映射；
- 产品端口、宿主设备、框架 ID；
- 逻辑画布、预览尺寸和默认列数；
- 只实现页面内交互，不实现跨页面跳转；
- 共享规范与日志规则；
- 路径、尺寸、溢出、交互、图片、框架配置和日志验证项。

### 生成规则

- 正式页面写入 `prototype/pages/*.html`。
- 页面根画布匹配 `frame-config.json.logicalViewport`。
- 页面不得绘制系统 UI；App 导航、Tab Bar、微信胶囊按钮、网站导航等产品 UI保留。
- `prototype/index.html` 使用选中框架的 `?screen=pages/<file>.html` 加载每个页面，并设置 `data-ycet-frame-id`。
- 默认列数读取 Manifest：手机/微信宿主 4、iPad 2、Browser/MacBook 1；小屏幕可减少列数，不改变逻辑画布。
- 每张页面卡片保留页面名、文件名和“打开页面html”链接。
- `index.html` 不执行跨页面导航；页面内 Tab、弹窗、Toast、表单、loading、折叠和轮播可以工作。

### 完成标准

- 设计方向、首页预览、静态页面、入口、框架文件和项目配置均存在且路径有效。
- Manifest、`frame-config.json`、`Spec.md` 和 `data-ycet-frame-id` 一致。
- 框架系统 UI 与页面产品 UI 不重复。
- iframe 无非预期滚动条、裁剪或留白。
- 本地 HTML 与本地静态服务器均可打开。
- 将整个 `prototype/` 移动目录后仍可加载。
- `EditLog.md` 记录阶段二和阶段三生成动作。
- 完成后说明可在后续单独使用功能三生成交互 Demo。
