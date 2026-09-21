# 工作台请求执行

仅收到用户提供的请求 ID／包／执行指令后读取。预览和打开工作台只读 function-5-workbench.md。工作台由 Python 标准库运行，状态位于项目根 `.ycet-editor/`；请求执行不要求服务运行。

## 定位与写入条件

文件 SHA-256 与完整元素指纹共同定位：fileId、路径、framePath、pageId、elementId、选择器、标签、ID、类、文本、祖先链及兄弟序号。先核对摘要，再在对应页面内唯一定位；缺失、多匹配或特征冲突只报告冲突，不猜测。普通旧 HTML 可用唯一 CSS 指纹；嵌套预览的 framePath 也需核对。

只在暂存内容中落实请求操作：annotation、style、text、image-replace、css。内联样式按操作 priority 保持优先级；旧操作缺省为 important，只改目标属性。X/Y 是视口坐标，以新旧坐标差叠加原 left/top，静态元素先设相对定位。图片先归档到项目并内联；拒绝远程 URL、@import、javascript:、expression() 和越界路径，不把临时上传 URL 写入源码。

## 变更包

请求位于：

```text
.ycet-editor/requests/<request-id>.json
```

顶层使用 `schemaVersion: 1`，包含请求 ID、项目根、生成时间和文件列表。每个文件包含来源、原始路径、显示路径、原始 SHA-256、操作与可选依赖组。

动态状态独立保存为 `.ycet-editor/requests/<request-id>.state.json`，不得改写原始请求包。状态固定为：

| 状态 | 含义 |
| --- | --- |
| `pending` | 变更包已生成，等待用户交给 Agent |
| `processing` | Agent 已原子执行 `request begin` |
| `success` | 全部文件成功 |
| `partial` | 部分文件成功 |
| `failed` | 没有文件成功或执行失败 |
| `aborted` | 用户在领取前取消，或 Agent 主动中止 |

旧请求缺少状态文件时，按 `.result.json`、事务清单和请求包依次推导终态、`processing` 或 `pending`。

正式请求包必须满足“JSON 文件名去掉 `.json` 后与包内 `requestId` 一致”且包含 `files`。Agent 可使用独立临时文件准备结果，但 `*.result.pending.json`、`*.state.json`、`*.result.json` 等状态或临时结果不得被识别为新请求；正式请求进入终态后必须立即解除活动请求和发送锁。

同一项目同时只允许一个 `pending` 或 `processing` 请求：

- 存在活动请求时禁止再次发送；活动请求终止后恢复。
- 活动请求中列出的文件锁定编辑；其他 HTML 仍可准备新草稿，但必须等待当前请求终止后发送。
- `pending` 请求可从工作台取消；取消不会恢复发送时已经清空的草稿。
- `processing` 请求不得由网页强制取消，只能由执行 Agent `complete` 或 `abort`。
- `request begin` 必须用原子事务目录领取；重复领取、非 `pending` 状态或另一个活动请求存在时拒绝。

领取请求：

```text
python <skill目录>/scripts/prototype_workbench.py request show --project-root <项目根目录> --request-id <请求ID>
python <skill目录>/scripts/prototype_workbench.py request begin --project-root <项目根目录> --request-id <请求ID> [--include <项目内图片目标>]
```

`begin` 原子将状态从 `pending` 更新为 `processing`，建立修改前快照并按依赖组校验摘要。独立文件冲突不得阻断其他文件；同一依赖组任一文件冲突时整组不写。图片替换会新增/覆盖的项目内资源 必须在写入前通过重复 `--include` 纳入事务。新增且尚不存在的资源也要提供目标路径，事务会记录其“修改前不存在”。

Agent 执行规则：

1. 只处理 `begin` 返回的 `readyFileIds`。
2. 对每个元素重新解析源 HTML 并验证指纹唯一。
3. 在暂存内容中应用操作并保留摘要及原子写入保护；原型修改完成后不追加守卫或验收。
4. 成功修改仅在结果与完成回复记录，不写 EditLog。
5. 结果 JSON 的 `items` 逐文件包含 `fileId`、`path`、`status` 与可选 `reason`；状态为 `success`、`failed` 或 `conflict`。成功项通过 `affectedFileIds` 登记本次实际改变的附加事务文件 ID；不得漏报图片归档资源。
6. 多个互不依赖文件允许部分成功，最终回复必须列出成功文件、失败/冲突文件和原因。

完成或中止：

```text
python <skill目录>/scripts/prototype_workbench.py request complete --project-root <项目根目录> --request-id <请求ID> --result <结果JSON>
python <skill目录>/scripts/prototype_workbench.py request abort --project-root <项目根目录> --request-id <请求ID> --reason <原因>
```

`complete` 要求原请求每个文件恰好一个 success／failed／conflict 结果；已知摘要冲突自动合并，缺项、重复、未知项或冒报冲突项成功都会拒绝完成，修正结果后可重试。它将状态更新为 `success`、`partial` 或 `failed`；`abort` 更新为 `aborted`。工作台轮询状态与 `.result.json` 并展示逐文件结果；请求事务快照在完成或中止后清理，不提供用户撤回入口。

## v4 页面定位与写入

新原型使用同文件直接 DOM。指纹附带 pageId、elementId；先校验文件 SHA-256，再在页面根内唯一定位。缺失或多匹配报告冲突，不猜测。旧普通 HTML 可使用唯一 CSS 指纹，不提供旧多文件联动能力。

工作台请求一律改现有文件，不走功能三类型选择或版本询问，即使是增删页面、破坏性或全页修改也不新增迭代文件。图片替换需归档且内联到 HTML，不能写入上传临时 URL。修改保存后及时 complete，默认不运行 prototype_guard.py 或其他验收；仅用户明确要求测试时按指定范围执行，见 prototype-validation.md。

没有跨文件内容同步操作；旧 sync-pages 操作明确拒绝。CLI sync 仅登记 prototype 内文件，不启动服务。

只处理 readyFileIds，保留请求状态、原子领取、事务、摘要、部分成功、关闭及源文件冲突机制。不创建或更新 EditLog。现有历史日志保持不变。

属性预览不依赖 HTML 文件命名或元数据。显式 style/css 草稿使用内联 `!important` 覆盖源样式同名属性，新属性操作在请求中携带 `priority: "important"`；旧操作未提供 priority 时按 important 处理。Agent 落实操作时保持相同优先级，仅修改目标元素对应属性，不删除其他规则。撤回／清空恢复完整原始 style（包括原有优先级），预览不修改磁盘源文件。
