# Shared EditLog Rules

## 适用范围

写入或修改以下内容时，必须更新 `prototype/docs/EditLog.md`：

- `prototype/design-direction.html`
- `prototype/previews/*.html`
- `prototype/index.html`
- `prototype/pages/*.html`
- `prototype/pages/source-images/*`
- `prototype/prototype.html`
- `prototype/prototype-vN.html`
- `prototype/assets/frames/frame-config.json`
- 项目内复制、替换或升级的设备框架 HTML
- 承载图片原型的 HTML 页面
- `prototype/assets/images/` 下内容图及 `images-manifest.json`
- `prototype/assets/icons/` 下图标与本地化图标库

即使用户后续未主动调用本 Skill，只要修改上述原型内容，也需要记录。

Skill 源目录 `assets/frames/` 的开发不写入某个原型项目的 EditLog。

## 文件与格式

固定位置：

```text
prototype/docs/EditLog.md
```

目录或文件不存在时先创建。使用 Markdown 表格：

```markdown
| 修改时间 | 修改内容 | 修改文件 |
| --- | --- | --- |
| 20260712 14:50 | 生成 UI 设计方向、首页预览及项目框架配置 | design-direction.html、home-preview.html、frame-config.json、iphone-15-pro.html |
```

时间格式固定为 `YYYYMMDD HH:mm`，使用当前系统时间。

## 记录粒度

| 场景 | 记录内容 |
| --- | --- |
| 功能一阶段二首次生成 | 生成 UI 设计方向、首页预览及项目框架配置 |
| 功能一阶段二重新生成 | 按新设计方向更新首页预览和设计方向页 |
| 功能一阶段三 | 生成静态原型页面和页面阵列 |
| 功能二 | 记录目标元素、修改内容和文件 |
| 功能三 | 生成可交互 Demo 与版本专用 `runtime-pages/` 副本；不得记录为修改 `pages/` 或 `index.html` |
| 功能四迁移 | 迁移到 Manifest 框架体系 |
| 功能四 HTML 解析重构 | 记录源 HTML/关联文件解析、直接生成 Spec 与重构等级；后续 UI 方向和静态生成按功能一阶段分别记录 |
| 图片原型 | 导入原图并生成原图承载型 `pages` 页面与 `index.html`；用户确认后的 Demo 按功能三另行记录 |
| 内容图/图标本地化 | 下载或替换资源、路径改写、匹配降级或近似顶替、用户外链例外 |
| 图片清单更新 | 生成或更新 images-manifest.json |
| 项目框架升级 | 更新项目框架及配置快照 |

## 执行要求

1. 修改前确认是否触发日志。
2. 修改完成后立即追加，不等到最终回复。
3. 多个文件使用顿号分隔。
4. 同一阶段的一组原子生成动作可以合并一条记录。
5. 不记录与原型 HTML、预览、项目框架和配置无关的普通文档改动。
6. 功能四的“规范化重构”和“用户要求的编辑”分别记录。
