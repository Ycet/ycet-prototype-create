# 功能二：UI 方向确认

## 功能二：UI 设计方向

### 发现 UI 相关 Skill

优先使用当前会话 Skill 清单中的名称、描述和可调用状态，按当前产品需求推荐最合适的 2–3 个（不足时如实展示），同时提供“不使用 Skill”和“查看全部”选项。用户已指定主 UI Skill 时直接使用，不重复选择。

默认只读取选中 Skill 的正文，不扫描其他目录。仅当当前清单无合适结果、用户要求查看全部或指定 Skill 未找到时，再按 `~/.agents/skills/`、`~/.codex/skills/`、`~/.claude/skills/` 补充发现；只提取 frontmatter，以解析后的真实路径去重。不可访问的来源跳过并说明；不安装新 Skill。

推荐项展示名称、适用原因、来源和可调用状态；有前置条件或特殊链接时一起展示。“查看全部”保留所有结构有效的 UI 相关 Skill，包括生成、品牌、审核和润色类型，不把推荐列表当作全部列表。

用户一次选择一个主 UI Skill，也可以不使用。已安装但不可调用的项明确标注，不能擅自替换用户选择。

### 特殊链接

- 选择 `ycet-design-system-governor`（兼容旧名 `ui-design-system-governor`）：始终提供 <https://open-design.ai/zh/plugins/systems/>。
- 选择 `ui-ux-pro-max`：始终提供 <https://ui-ux-pro-max-skill.com/zh/#styles>。
- 仅在用户明确要求且环境支持时打开；失败时保留可点击链接并继续。

### 选择 Skill

读取所选 Skill 并应用其视觉设计方法、设计约束和必要输入。主流程、阶段确认、单文件格式、写入策略与工作台边界由本 Skill 统一管理；外部 Skill 不另开一套访谈、不自动发布或生成正式原型。复用已经确认的需求和视觉输入；外部规则与本 Skill 产物契约冲突时保留视觉意图并适配到当前产物，无法适配才说明具体冲突。生成 `design-direction.html` 前允许更换；生成后更换必须重新生成并重新确认。

### 不使用 Skill

仅补问尚未明确的主题，每轮一个，按以下顺序检查；已提供的结论直接沿用：

1. 是否有参考产品或网站；
2. 设计风格；
3. 色彩方案；
4. 其他补充要求。

用户回答没有参考对象后直接进入设计风格。全部确认后汇总设计方向并请求确认。


## 设计方向预览

读取 shared-prototype-standards.md。生成 prototype/outputs/design-direction.html，内联色彩、字体、按钮、反馈组件与一个首页预览。全部使用直接 DOM，不生成首页独立文件，不使用 iframe。可使用 build_prototype.py 的 direction 类型；首页 fragment 放入 pages，设计组件放入 directionHtml。外围展示壳与首页共用同一视觉方向，按 shared-prototype-standards.md 提供 shellTheme，并将其沿用到正式产物。用户确认方向并继续后，进入功能三询问 A/B/C。重新设计按 shared-change-policy.md 决定文件策略。

方向预览中的设备尺寸是展示参考。后续选择 C 无框架类型时按产品端口和实际浏览器视口重排，不能把预览尺寸写成产品根宽高。修改已有方向预览同样遵守 prototype-validation.md：完成修改即结束，用户未要求时不追加验收。
