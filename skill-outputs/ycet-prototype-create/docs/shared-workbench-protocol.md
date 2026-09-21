# 工作台协议入口

按当前任务只读取一个分支，同一上下文不重复读取未变文件：

- 打开、预览、刷新、关闭或查询工作台：function-5-workbench.md。
- 收到请求 ID／请求包并需要执行修改：workbench-request.md；执行 request show/begin/complete，收尾遵循 prototype-validation.md。
- 开发、排错或检查工作台交互：workbench-maintenance.md；涉及请求状态再读取 workbench-request.md。

五功能路由、原文件修改、草稿、定位、事务和关闭行为保持原契约。编辑器宿主 iframe 不属于交付 HTML。
