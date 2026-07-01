# Shared EditLog Rules

## 适用范围

凡写入或修改以下文件，必须更新 `prototype/docs/EditLog.md`：

- `prototype/index.html`
- `prototype/prototype.html`
- `prototype/prototype-vN.html`
- `prototype/pages/*.html`
- 承载图片原型的 HTML 页面

即使用户没有主动调用 `ycet-prototype-create`，只要修改上述文件，也必须记录。

## 文件位置

`EditLog.md` 固定保存为：

```text
prototype/docs/EditLog.md
```

若目录或文件不存在，必须先创建。

## 表格格式

`EditLog.md` 必须使用 Markdown 表格：

```markdown
| 修改时间 | 修改内容 | 修改文件 |
| --- | --- | --- |
| 20260604 14:50 | 删除首页底部导航栏，修复 index.html 显示异常 | home.html、index.html |
```

时间格式固定为 `YYYYMMDD HH:mm`，使用当前系统时间。

## 记录粒度

| 场景 | 记录方式 |
| --- | --- |
| 功能一首次生成 `index.html` 与 `pages/*.html` | 记录一条“生成静态原型页面” |
| 功能二修改页面元素 | 每次记录具体修改内容和文件 |
| 功能三生成 `prototype.html` 或 `prototype-vN.html` | 记录生成可交互 demo 文件 |
| 功能四规范化重构 HTML | 分别记录“规范化重构”和“用户要求的编辑” |
| 图片原型保存到 `pages/` | 记录“导入图片原型资源” |
| 为图片原型生成承载页面或 `index.html` | 记录对应 HTML 写入/修改 |

## 执行要求

1. 修改原型文件前，先确认是否需要更新 `EditLog.md`。
2. 修改完成后立即追加记录，不要等到最终回复再补。
3. 修改多个文件时，`修改文件` 用顿号分隔。
4. 不要记录与原型 HTML 无关的普通文档改动。
