# 功能二：UI 方向确认

## 功能二：UI 设计方向

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


## 设计方向预览

读取 shared-prototype-standards.md。生成 prototype/outputs/design-direction.html，内联色彩、字体、按钮、反馈组件与一个首页预览。全部使用直接 DOM，不生成首页独立文件，不使用 iframe。可使用 build_prototype.py 的 direction 类型；首页 fragment 放入 pages，设计组件放入 directionHtml。用户确认方向并继续后，进入功能三询问 A/B/C。重新设计按 shared-change-policy.md 决定文件策略。

方向预览中的设备尺寸是展示参考。后续选择 C 无框架类型时按产品端口和实际浏览器视口重排，不能把预览尺寸写成产品根宽高。修改已有方向预览同样遵守 prototype-validation.md：完成修改即结束，用户未要求时不追加验收。
