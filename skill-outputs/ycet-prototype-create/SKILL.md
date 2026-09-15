---
name: ycet-prototype-create
description: Refine product requirements, confirm UI direction, create self-contained static, interactive or mobile HTML prototypes, adapt existing HTML or screenshot prototypes, and edit them through a local visual workbench. Use for product prototyping, offline HTML demos, prototype modifications or workbench change requests.
---

# YCET Prototype Creator v4.0.0

## 路由

| 用户任务 | 入口 |
| --- | --- |
| 工作台请求 ID／执行指令，打开可视化工作台 | docs/function-5-workbench.md |
| 基于现有原型或图片制作／修改 | docs/function-4-existing-prototype-edit.md |
| 从零制作完整原型 | 功能一 → 功能二 → 功能三，阶段间确认 |
| 只完善需求 | docs/function-1-requirements.md |
| 只确认 UI 方向 | docs/function-2-ui-direction.md |
| 已有确认需求和方向，开始制作 | docs/function-3-prototype-production.md |

不能只因“单文件／离线”路由移动端。意图不明时一次只问一个路由问题，给多个答案。每个功能按需读取对应文档。

## 全局契约

- 全部生成 HTML 位于 prototype/outputs/；Spec 在 prototype/docs/Spec.md，素材归档 prototype/assets/。
- 生成前读 docs/shared-prototype-standards.md；修改前读 docs/shared-change-policy.md。
- 所有交付 HTML 使用直接 DOM、内联资源，无 iframe/srcdoc 和外部运行依赖，包含 design-direction.html。
- 功能三制作前必须询问 A 静态、B 交互、C 移动，实际回答后只生成所选类型。
- 破坏性变更、增删页面或全部页面同时修改，写入前询问版本策略，推荐新增迭代文件；普通局部修改直接改现有文件。
- 工作台请求是明确例外：原文件修改，不问类型／版本，不生成迭代文件。
- 三类原型独立维护，工作台不提供内容同步。取消自动创建／更新 EditLog，已有日志保留。
- 功能一只完善产品逻辑；UI 讨论在功能二。现有原型普通修改沿用 UI，重设计才进入功能二。端口仅缺失或冲突时询问。
- 图片保留完整位图承载，不元素化；固定区域分割先确认边界。
- 只有功能五启动工作台。其他功能不自动打开工作台、安装、发布或提交。
- 使用中文交流；关键代码中文注释。信息未知时说明，不编造资源、来源和测试结果。

## 完成

列出功能、文件、类型、版本策略、页面与资源内联情况、实际验证结果、限制及继续方式。未实际测试的浏览器／真机明确标注，不宣称已更新日志。
