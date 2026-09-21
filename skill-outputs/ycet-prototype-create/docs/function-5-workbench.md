# 功能五：原型工作台

仅打开或预览无需加载其他协议。通过 scripts/prototype_workbench.py ensure --project-root <项目根> 启动或复用工作台；自动打开失败时提供返回 URL。

递归展示 prototype/ 下所有 HTML，包含 outputs、设计方向和历史版本。没有 prototype 时仍启动空工作台。刷新恢复磁盘中存在的原型登记；移出只移出登记，不删除文件。

收到请求 ID／请求包／执行指令后才读取 workbench-request.md 并修改，执行 request show/begin/complete。直接修改包内现有文件，不进入功能三、不询问类型或版本、不生成迭代文件，包含全页修改也是如此。只处理 readyFileIds，以摘要和唯一指纹定位，独立文件允许部分成功。

保留预览、批注、属性修改、图片替换、撤回草稿、缩放平移与关闭。没有跨文件同步能力。修改完成后不运行守卫、局部／全量回归或浏览器验收，按 prototype-validation.md 及时结束请求事务；新增图片归档并内联，临时 URL 不写回。无需 EditLog；请求状态和事务数据仍保存 .ycet-editor/。

nonframe、旧 mobile 与任意命名 HTML 均按元数据／原路径登记。工作台请求成功表示修改已执行，不额外表示测试通过。

启动用 `python <skill>/scripts/prototype_workbench.py ensure --project-root <项目根>`，可重复 `--add <prototype内HTML绝对路径>`。同项目健康实例复用；无 HTML 时保留空工作台。URL 始终由命令返回，opened=false 时提供链接。查询用 status；sync 只更新登记，不启动服务。

服务仅绑定 127.0.0.1，状态保存在项目根 .ycet-editor/。关闭用工作台已有二次确认按钮，保留已发送请求和结果；有未发送草稿时提示丢失范围。服务关闭后不后台重启。维护或排查选择、批注、属性、撤回、图片、缩放等行为时才读取 workbench-maintenance.md。
