# 功能三：原型制作

读取 shared-prototype-standards.md、shared-change-policy.md、prototype-types.md。完整需求与 UI 已确认后，必须先问用户选择：

- A：静态原型页面 prototype-pages.html
- B：可交互原型 Demo prototype-demo.html
- C：移动端演示原型 Demo prototype-mobile.html

等待实际回答，不自动选择。只生成所选类型；B/C 不要求静态中间产物。缺少页面逻辑时一次一问补齐并确认。已有明确结论不重复访谈。

## 执行

1. 列出页面 ID、内容、状态、导航关系、端口和资源。
2. 按变更策略识别目标文件及是否需版本确认，用户未答复时不得写入。
3. 把全部页面写成直接 DOM fragment，CSS 用 :scope 定位页面根，JS 在 root 参数内查询，跨页使用 navigate(pageId)。资源先归档再内联。
4. 按 shared-prototype-standards.md 准备构建 JSON，在临时目录保存；运行 scripts/build_prototype.py。构建器不推断业务，不代替 Agent 的确认。
5. 对具体交付文件运行 prototype_guard.py，并在可用浏览器验证所有页面和核心交互、无可见滚动条、独立离线运行。
6. 完成回复列文件、类型、版本策略、资源、测试与限制。不更新 EditLog，不自动启动工作台。

修改现有文件也可直接编辑其源码；保持元数据和稳定标识，重新运行同一守卫。不得从旧构建 JSON 覆盖工作台已经修改的内容。
