# 功能二：通过可视化工作台精准修改原型

## 目标

启动或复用本地原型可视化编辑器工作台，让用户直接选择真实页面元素、添加批注并预览属性修改；只有用户点击“发送给 AI”并提交变更包后，Agent 才允许修改源文件。

执行本功能前完整读取 `shared-workbench-protocol.md`。涉及项目内原型文件修改时同时读取 `shared-editlog-rules.md`；外部 HTML 不写 EditLog。

## 触发条件

- 用户明确选择功能二或要求打开可视化原型编辑器；
- 用户要精确修改现有原型页面；
- 用户提交工作台生成的请求 ID 或执行指令。

用户仍可提供 CSS 选择器或 HTML 片段作为补充证据，但不再要求用户打开 F12 或手工复制路径。未收到工作台变更包时只启动/展示编辑器，不猜测修改源文件。

## 启动工作台

```text
python <skill目录>/scripts/prototype_workbench.py ensure --project-root <项目根目录>
```

1. 健康实例存在时复用，不重新启动。
2. 自动扫描 `prototype/` 根级 HTML、`pages/`、`previews/` 与 `runtime-pages/`。
3. 项目没有 `prototype/` 或没有 HTML 时仍正常启动空工作台；服务保持运行，后续点击左栏刷新按钮即可补入新生成的项目 HTML。
4. `opened: false` 时必须把命令输出的 URL 发给用户。
5. 左栏只提供搜索、选择、分组折叠、项目文件刷新和侧栏折叠，不提供新增分组、外部 HTML 选择、拖拽排序或移出文件操作。

用户明确要求登记其他 HTML 时：

```text
python <skill目录>/scripts/prototype_workbench.py sync --project-root <项目根目录> --add <HTML绝对路径>
```

## 收到执行指令后

1. 从指令取得项目根和请求 ID。
2. 读取 `shared-workbench-protocol.md`，运行 `request show` 审查全部文件、摘要、指纹、操作与依赖组。
3. 运行 `request begin`；只修改返回的 `readyFileIds`，冲突文件或冲突依赖组保持原字节。
4. 每个元素必须用完整指纹唯一定位；匹配为零或多个时记录 `conflict`，不得按视觉或相似文本猜测。
5. 在暂存内容中应用 `annotation`、`style`、`text`、`image-replace`、`css` 和 `sync-pages` 操作，并执行对应功能守卫。
6. 项目内成功修改追加 EditLog；外部 HTML 直接修改原始路径，不写永久执行历史。
7. 写结果 JSON 并运行 `request complete`。互不依赖文件允许部分成功。
8. 最终回复列出成功文件、失败/冲突文件和逐项原因；工作台结果面板读取同一结果。

## `同步 pages` 保护

`sync-pages` 不是文件覆盖。Agent 必须在暂存副本中把 `pages/*.html` 的结构、内容和样式受控合并到对应 `runtime-pages/*.html`，同时保留功能三消息协议、页面注册表和 Demo 交互。静态源页与引用它的同步操作按同一依赖组执行；验证 `navigate`、`set-screen`、`screen-changed` 或 `prototype.html` 加载失败时整组不写。

## 撤回

收到撤回指令时运行：

```text
python <skill目录>/scripts/prototype_workbench.py undo --project-root <项目根目录>
```

摘要冲突时不得强制覆盖。成功后说明恢复文件；失败时列出冲突文件与原因。

## 完成标准

- 工作台启动或复用成功；无法自动打开时用户已获得 URL。
- 预览、选择、批注、属性草稿、清空和项目文件刷新未改变源 HTML SHA-256。
- 只有请求包被 Agent 执行后源文件才变化。
- 元素定位唯一，未引入无关修改。
- 部分成功、冲突与失败逐文件报告。
- 项目内普通修改已记录 EditLog；外部文件没有永久执行历史。
- 最近一次成功批次可以在摘要仍匹配时跨工作台重启撤回。
