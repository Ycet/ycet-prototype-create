# 功能三：原型制作

读取 shared-prototype-standards.md、shared-change-policy.md、prototype-types.md 与 prototype-validation.md。完整需求与 UI 已确认后，必须先问用户选择：

- A：静态原型页面 prototype-pages.html
- B：可交互原型 Demo prototype-demo.html
- C：无框架交互原型 Demo prototype-nonframe.html

等待实际回答，不自动选择。只生成所选类型；B/C 不要求静态中间产物。缺少页面逻辑时一次一问补齐并确认。已有明确结论不重复访谈。

## 执行

1. 列出页面 ID、内容、状态、导航关系、端口和资源。选择 C 时沿用已确认端口；缺失／冲突才补问，使用 nonframe 类型及 document/app 布局，不以设备框架尺寸限制页面。
2. 按变更策略识别目标文件及是否需版本确认，用户未答复时不得写入。
3. 把全部页面写成直接 DOM fragment，CSS 用 :scope 定位页面根，JS 在 root 参数内查询，跨页使用 navigate(pageId)。资源先归档再内联。
4. 首次构建按 shared-prototype-standards.md 准备 JSON 并运行 scripts/build_prototype.py。修改优先直接编辑现有源码；确需构建器时使用 --purpose modify，包括已交付原型后续创建新类型基名的转换任务；功能四首次生成目标文件使用 --mode create --purpose initial。iterate/overwrite 默认属于修改；仅用户明确要求验证才传 --validate。
5. 修改任务保存后直接进入交付，不运行额外守卫或验收。仅首次生成（含功能四首次生成目标文件）或用户明确要求测试时按 prototype-validation.md 执行；首次 build 已成功的静态守卫不重复运行。
6. 完成回复列文件、类型、版本策略、资源、测试与限制。不更新 EditLog，不自动启动工作台。

修改现有文件也可直接编辑其源码；保持元数据和稳定标识，完成修改后直接结束。不得从旧构建 JSON 覆盖工作台已经修改的内容。

选择 B 时必须遵守 `prototype-types.md` 的 Demo 滚动与缩放规则，包括长导航纵向滚动、右上角独立缩放、默认完整适配和右侧纵向滚动；全部 prototype-demo 迭代版本一致。
