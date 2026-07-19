# 原型可视化编辑器工作台协议

## 适用范围

本协议供功能一至五共享。工作台负责本地预览、元素选择、批注、预览级草稿、变更包、结果展示和最近一次撤回；Agent 仍是唯一可以在用户点击“发送给 AI”后修改源文件的一方。

工作台入口：

```text
scripts/prototype_workbench.py
```

工作台只依赖 Python 3 标准库与浏览器原生能力。服务绑定 `127.0.0.1`，项目状态位于项目根目录 `.ycet-editor/`，不得写入 `prototype/`，也不得自动修改 `.gitignore`。

## 生命周期命令

首次需要展示项目或服务可能未运行时：

```text
python <skill目录>/scripts/prototype_workbench.py ensure --project-root <项目根目录> --add <HTML绝对路径>
```

- 同项目健康实例存在时必须复用，只增量同步 `--add` 文件。
- 实例不存在时在随机本机端口启动并尝试打开浏览器。
- 命令 JSON 输出始终包含 URL；`opened: false` 时必须把 URL 发给用户手动打开。
- 用户可以手动关闭服务。后续功能再次需要工作台时才调用 `ensure`，不得后台自动重启。
- 可重复提供多个 `--add`；未提供时扫描 `prototype/` 根级 HTML、`pages/`、`previews/` 与 `runtime-pages/`。

明确只做增量同步时可用：

```text
python <skill目录>/scripts/prototype_workbench.py sync --project-root <项目根目录> --add <HTML绝对路径>
```

`sync` 在实例不存在时按 `ensure` 的相同规则启动。检查状态使用：

```text
python <skill目录>/scripts/prototype_workbench.py status --project-root <项目根目录>
```

## 工作区边界

- `workspace.json` 保存文件登记、来源、缺失状态、当前文件和缩放偏好，并兼容读取旧版本留下的分组与排序数据；网页端不再提供修改分组或排序的入口。
- 未发送批注、属性、文本、图片、CSS 和 `同步 pages` 草稿只保存在浏览器内存，关闭工作台即丢失。
- 左栏只读展示已登记文件；刷新按钮扫描 `prototype/` 根级及约定子目录并补入尚未登记的项目 HTML，不删除、移动、重命名或重新排序任何磁盘文件。
- 外部 HTML 不再通过网页系统文件对话框登记；只有用户明确要求 Agent 使用 CLI `--add` 时才可登记，并在原始绝对路径修改。
- 没有 `prototype/` 或没有 HTML 时正常启动空工作台，不得关闭服务或伪造文件。
- 图片选择只登记原始绝对路径并用于预览；发送前不复制、不修改图片或 HTML。
- 图片替换的系统文件对话框必须由 Python 进程主线程执行；`ThreadingHTTPServer` 请求线程只能提交任务并等待结果，禁止直接创建 Tk 根窗口。
- 文件监听发现外部变化时，无草稿文件刷新摘要与预览；有草稿文件标记冲突并禁止发送，直到用户刷新源文件并重新编辑。

## 预览与定位

服务只在 HTTP 响应中注入 `preview-runtime.js`，源 HTML 字节不变。选择结果必须包含：

- `fileId`、原始路径和文件 SHA-256；
- iframe `framePath`；
- CSS 选择器、标签、ID、类名和文本特征；
- 祖先链与兄弟序号。

画布交互固定为：普通鼠标滚轮滚动当前 HTML 页面，`Ctrl+鼠标滚轮`以指针为中心缩放，中键按住进行二维平移。关闭“选择元素”后必须隐藏悬浮框、已选框、元素名称和批注入口；再次开启后需重新点击元素才显示选区。

预览运行时必须上报页面真实内容宽度，工作台据此扩展 iframe 逻辑宽度，避免固定预览宽度裁切页面；预览高度使用中央画布可用高度，超出部分由 HTML 页面自身纵向滚动。静态或相对定位元素的 X/Y 编辑必须转化为可生效的定位与相对位移，不能只写对 `position: static` 无效的 `left/top`。

Agent 必须以文件摘要和完整元素指纹共同定位。选择器不唯一、摘要不匹配、iframe 路径失效或文本特征冲突时，只报告冲突，不猜测修改。

草稿操作类型固定为：

| 类型 | 用途 |
| --- | --- |
| `annotation` | 元素批注 |
| `style` | 设计面板样式差异 |
| `text` | 文本节点替换 |
| `image-replace` | 本地图片替换 |
| `css` | 任意 CSS 属性和值 |
| `sync-pages` | 静态页到运行时页的受控同步 |

CSS 与样式值在预览中可自由应用；Agent 落实时必须拒绝远程 URL、`@import`、`javascript:`、`expression()`、越界路径和违反当前功能守卫的值。

## 会话草稿规则

- 切换 HTML 保留当前会话内各文件草稿，文件图标左侧显示红点。
- “清空修改”只清当前文件的样式、文本、图片、CSS 与 `同步 pages` 草稿，保留该文件批注和其他文件草稿。
- 用户可单独编辑或删除批注。
- “发送给 AI”聚合所有文件草稿。请求包成功写入磁盘后清空全部会话草稿；写入失败时全部保留。
- 发送仅生成机器可读变更包和可复制执行指令，V1 不直接控制 Codex、Claude Code、OpenCode 或其他 Agent 会话。

## 变更包

请求位于：

```text
.ycet-editor/requests/<request-id>.json
```

顶层使用 `schemaVersion: 1`，包含请求 ID、项目根、生成时间和文件列表。每个文件包含来源、原始路径、显示路径、原始 SHA-256、操作与可选依赖组。

领取请求：

```text
python <skill目录>/scripts/prototype_workbench.py request show --project-root <项目根目录> --request-id <请求ID>
python <skill目录>/scripts/prototype_workbench.py request begin --project-root <项目根目录> --request-id <请求ID> [--include <项目内图片目标或EditLog路径>]
```

`begin` 建立修改前快照并按依赖组校验摘要。独立文件冲突不得阻断其他文件；同一依赖组任一文件冲突时整组不写。图片替换会新增/覆盖的项目内资源和本次需要更新的 `prototype/docs/EditLog.md` 必须在写入前通过重复 `--include` 纳入事务；外部 HTML 不包含 EditLog。新增且尚不存在的资源也要提供目标路径，事务会记录其“修改前不存在”。

Agent 执行规则：

1. 只处理 `begin` 返回的 `readyFileIds`。
2. 对每个元素重新解析源 HTML 并验证指纹唯一。
3. 在暂存内容中应用操作并运行当前功能要求的守卫。
4. 项目内普通成功修改按 `shared-editlog-rules.md` 追加 `prototype/docs/EditLog.md`；外部文件不写永久执行历史。
5. 结果 JSON 的 `items` 逐文件包含 `fileId`、`path`、`status` 与可选 `reason`；状态为 `success`、`failed` 或 `conflict`。成功项通过 `affectedFileIds` 登记本次实际改变的附加事务文件 ID；不得漏报图片资源或 EditLog。
6. 多个互不依赖文件允许部分成功，最终回复必须列出成功文件、失败/冲突文件和原因。

完成或中止：

```text
python <skill目录>/scripts/prototype_workbench.py request complete --project-root <项目根目录> --request-id <请求ID> --result <结果JSON>
python <skill目录>/scripts/prototype_workbench.py request abort --project-root <项目根目录> --request-id <请求ID> --reason <原因>
```

只有 `complete` 登记为成功的实际文件进入最近一次撤回事务。工作台轮询 `.result.json` 并展示逐文件结果。

## `同步 pages`

`runtime-pages/*.html` 可映射到 `pages/*.html` 时展示“同步 pages”。点击只添加 `sync-pages` 草稿；必须发送后才允许 Agent 修改。

执行时不得用静态文件直接覆盖运行时文件。必须在暂存副本中受控合并结构、内容和样式，并保留或重新生成功能三的：

- `channel: "ycet-prototype"` 与 `version: 1`；
- `navigate`、`set-screen`、`screen-changed`；
- 页面注册表、目标白名单、`event.source` 校验和框架中继。

静态源页与引用其修改的同步操作属于同一依赖组。写入前后必须验证 `prototype.html` 或当前版本 Demo 仍加载目标运行时页，功能三守卫与浏览器交互失败时整组不写。

## 最近一次撤回

撤回事务位于 `.ycet-editor/undo/latest/`，可跨工作台重启使用，但只保留最近一次成功批次的修改前内容和修改后摘要，不构成永久历史。

用户点击“撤回”后工作台只生成 Agent 指令。Agent 执行：

```text
python <skill目录>/scripts/prototype_workbench.py undo --project-root <项目根目录>
```

命令仅在所有目标仍匹配修改后摘要时恢复；存在后续修改便拒绝覆盖并报告冲突。撤回完成后事务删除。

## 功能五锁

打包前：

```text
python <skill目录>/scripts/prototype_workbench.py lock acquire --project-root <项目根目录>
```

- 健康工作台存在相关未发送草稿时命令失败，Agent 必须要求用户先发送或清空；不得自动处理草稿。
- 获取成功后保存返回的锁令牌。锁期间禁止发送工作台变更，但允许只读预览。
- 在 `finally` 路径释放，避免成功、失败或取消后遗留锁：

```text
python <skill目录>/scripts/prototype_workbench.py lock release --project-root <项目根目录> --token <锁令牌>
```

功能五仍只允许确定性打包器新增一个递增 `prototype-mobile*.html`。打包成功后用 `sync --add <新增文件>` 加入工作台；不得同步旧离线文件、自动重打包或反向修改运行时页。

## 安全红线

- 不直接写源 HTML，不把预览 DOM 当作源文件或打包输入。
- 不接受目录遍历、远程资源、危险协议、未登记路径或非本机 Host/Origin。
- 不以工作台规避功能一静态页、功能三只读输入、功能四确认门禁或功能五全项目 SHA-256 保护。
- 不把外部文件修改写入项目 EditLog；不把撤回事务当作永久执行历史。
