# 功能三：从静态原型到可交互 Demo

## 目标

将已完成的静态页面转换为完整可交互 Demo，生成 `prototype/prototype.html` 或递增版本 `prototype/prototype-vN.html`。保留既有交互流程确认、文件命名和左右分栏业务流程，只替换设备框架识别与通信方式。

开始前读取 `shared-prototype-standards.md`、`shared-editlog-rules.md` 与 `../assets/frames/manifest.json`。

## 前置条件

- `prototype/index.html` 存在。
- `prototype/pages/*.html` 包含完整静态页面。
- `prototype/docs/Spec.md` 存在，或用户给出完整页面间交互流程。
- 新框架项目应存在 `prototype/assets/frames/frame-config.json` 和选中框架文件。

## 工作流程

1. 从 Spec 提取页面间交互流程；合并用户当前对话中的补充。
2. 展示最终交互流程并请求确认；未确认不生成 Demo。
3. 读取所有页面文件，核对文件名与交互流程。
4. 识别项目框架。
5. 确定输出文件名。
6. 生成左右分栏 Demo，左侧页面导航、右侧单个设备框架。
7. 验证双向同步、返回历史、路径白名单和错误处理。
8. 追加 EditLog。

## 框架识别顺序

### 新框架模式

按优先级读取：

1. `prototype/assets/frames/frame-config.json`；
2. `index.html` 的 `data-ycet-frame-id`；
3. `index.html` 引用的框架文件名；
4. `Spec.md` 中的产品端口、宿主设备和框架 ID。

识别后验证：

- 配置 JSON 有效且版本受支持；
- 框架 ID、文件、逻辑画布、安全区域与 Manifest 相符；
- 项目内框架文件存在；
- `index.html` 与项目配置一致。

存在冲突时列出差异并请求用户确认，不静默覆盖。

### 旧框架兼容模式

新规则无法识别时，才检查 `.phone-frame`、`.android-frame`、`.miniapp-frame`、`.browser-frame`、`.desktop-frame`。旧项目可以继续生成 Demo，但完成说明必须标注“旧框架兼容模式”，不得把旧尺寸写入 Manifest。

## 文件命名

1. 用户指定名称时使用指定名称。
2. 首次生成使用 `prototype/prototype.html`。
3. 后续扫描 `prototype.html`、`prototype-v2.html` 等，使用下一个可用 `prototype-vN.html`。

## 新框架 Demo

### 布局

- 左侧约 280px，按核心流程、辅助功能、设置等分组展示页面。
- 右侧居中显示项目选中的单个设备框架。
- 使用项目内 `assets/frames/<frameFile>`；`frameFile` 已包含 `.html` 扩展名，不得重复追加，也不得引用 Skill 源目录。
- 小屏幕可改为上下布局或折叠侧栏，不改变页面逻辑画布。

### 页面注册表

根据 `prototype/pages/` 建立明确注册表：页面 ID、显示名称、文件名和允许来源。任何导航目标必须存在于注册表；拒绝远程 URL、绝对路径、上级目录和 `javascript:`。

注册表同时保存规范 pathname（如 `pages/home.html`）。收到带 query/hash 的目标时，先正规化并按 pathname 查询注册表，命中后才保留 query/hash；页面 ID、显示名称、裸文件名和规范路径不得混用。

### 双层 iframe 通信

固定协议：

```javascript
{
  channel: "ycet-prototype",
  version: 1,
  type: "navigate",
  targetPage: "pages/home.html"
}
```

兼容旧页面发送的 `targetPage: "home.html"`：框架中继前补全为 `pages/home.html`。新生成页面必须直接发送规范路径。

支持 `ready`、`navigate`、`set-screen`、`screen-changed`、`error`。

#### 左侧到右侧

1. 用户点击左侧页面。
2. 外层验证页面注册表。
3. 外层向设备框架发送 `set-screen`，screen 使用 `pages/<file>.html`。
4. 框架切换内部 iframe 并发送 `screen-changed`。
5. 外层更新高亮和历史。

#### 右侧到左侧

1. 内部页面向直接父级框架发送 `navigate`。
2. 框架验证 `event.source`，将目标正规化为项目根相对路径，补充框架 ID 并中继。
3. 外层验证当前框架、消息字段和页面注册表。
4. 外层切换页面并同步左侧高亮。

页面不得通过 `window.top` 绕过框架。

### 安全与错误

- 检查 channel、version、type、`event.source` 和页面白名单。
- 为兼容 `file://` 的 null origin，不能只依赖 origin。
- 未知消息忽略并记录调试提示。
- 加载失败时保留当前页面，展示错误，不切换到远程或占位地址。
- 配置无效、框架缺失或 Manifest 不一致时停止生成。

## 旧框架 Demo

保持原有单层 iframe 或外层 `src` 切换方式，不强制改动静态页面。旧兼容逻辑不得影响新框架主流程。

## 完成标准

- 输出文件位于 `prototype/`，命名正确。
- 交互流程已确认。
- 框架与 `index.html`、项目配置一致。
- 左右分栏、双向同步、返回历史和错误处理可用。
- 本地 HTML、静态服务器和目录迁移后均可使用。
- EditLog 已记录生成 Demo 和使用的框架 ID/兼容模式。
