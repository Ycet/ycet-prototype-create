# 原型内容图与图标本地化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已批准的内容图/图标本地化规范写入 `ycet-prototype-create` skill，使功能一生成与功能四规范化时默认产出可离线打包的真实图片资源。

**Architecture:** 规则集中在 `docs/shared-prototype-standards.md` 新增「图片与图标」专章；功能一/四、EditLog、SKILL 仅做薄引用与检查项补充。不新增脚本或独立文档。

**Tech Stack:** Markdown skill 文档；验证用文件内容检索与对照设计规格。

**Spec:** `docs/superpowers/specs/2026-07-12-prototype-image-assets-design.md`

## Global Constraints

- 内容图：`prototype/assets/images/`；网络图标：`prototype/assets/icons/`
- 语义匹配：严格 → 大类 → 非匹配兜底；下载失败：项目内近似图顶替
- 禁止灰占位、图标顶替内容图、交付态未授权外链/占位图服务
- 强制范围：功能一、功能四；功能二/三仅新增资源时遵守
- 不新增校验脚本；不改功能四整页图片原型落盘主流程
- 中文文档；与现有 skill 文风一致（短句、表格、清单）

## File Map

| 文件 | 职责 |
| --- | --- |
| `outputs/skills/ycet-prototype-create/docs/shared-prototype-standards.md` | 主规范：目录、分类、命名、阶梯、下载、引用、质检、红线 |
| `outputs/skills/ycet-prototype-create/docs/function-1-static-prototype.md` | 产物树、门禁、生成规则、完成标准嵌入 |
| `outputs/skills/ycet-prototype-create/docs/function-4-existing-prototype-edit.md` | HTML 审计与规范化嵌入 |
| `outputs/skills/ycet-prototype-create/docs/shared-editlog-rules.md` | 资源类变更的日志范围与粒度 |
| `outputs/skills/ycet-prototype-create/SKILL.md` | 全局规则一条指针 + 完成说明补充 |

---

### Task 1: 扩写 shared-prototype-standards.md

**Files:**
- Modify: `outputs/skills/ycet-prototype-create/docs/shared-prototype-standards.md`

- [ ] **Step 1: 更新目录结构示意**

在「目录结构」代码块中加入：

```text
  assets/
    frames/
      frame-config.json
      <selected-frame>.html
    images/
      images-manifest.json
      <content-images>
    icons/
      <icon-files-or-icon-libraries>
```

- [ ] **Step 2: 更新技术栈图标条款**

将：

```markdown
- 图标：FontAwesome 或其他开源图标库。
```

改为：

```markdown
- 图标：FontAwesome 或其他开源图标库；网络获取的图标须本地化到 `prototype/assets/icons/`，详见「图片与图标」。
- 内容图：真实图片资源，本地化到 `prototype/assets/images/`，详见「图片与图标」。
```

- [ ] **Step 3: 替换页面文件中的单句规则**

将：

```markdown
- 内容图片使用真实图片资源；UI 操作图标使用图标库，不互相替代。
```

改为：

```markdown
- 内容图片与 UI 操作图标遵守「图片与图标」专章；二者不互相替代。
```

- [ ] **Step 4: 在「页面文件」与「design-direction」之间插入完整「图片与图标」专章**

专章必须覆盖 spec 第 5–11、15–16 节要点，标题与顺序如下：

```markdown
## 图片与图标

### 适用范围
（功能一/四强制表；功能二/三新增资源时遵守）

### 资源分类
（内容图 vs UI 图标表；存放位置；禁止项）

### 底线
1. 交付态内容图与网络图标不得依赖未本地化远程 URL（用户明确例外并记 EditLog 除外）
2. 禁止灰占位 / skeleton-only 色块 / 图标库图标代替内容图
3. 禁止 picsum.photos、placehold.co、via.placeholder.com 等占位服务
4. 功能四整页图片原型不套用图库语义阶梯，但须在 prototype/ 内离线可用

### 图标本地化
（网络图标 → assets/icons/；推荐本地库拷贝；用户 CDN 例外须记录）

### 命名
内容图：`{page-or-module}-{role}-{semantic}[-nn].ext`
图标：单枚 purpose 命名；整库保留原结构

### 语义匹配阶梯
1 严格 → 2 大类 → 3 非匹配兜底（须完成说明记录）→ 下载失败时项目内近似图顶替（复制并重命名）
禁止跳级；禁止因此改用灰占位或图标

### 获取与下载
图库：Unsplash → Pexels → Pixabay → 其他可免费图源
方式：通用 HTTP；先列图位再下载再写相对路径
建议 images-manifest.json 字段示例
失败：近似顶替 → 再检索；仍失败暂停报告

### HTML 引用
pages/previews 用 `../assets/images/` 与 `../assets/icons/`
根目录 HTML 用 `assets/images/` 与 `assets/icons/`
禁止 Skill 绝对路径与 file:/// 绝对路径
CSS background-image 同样适用

### 红线借口表
（spec 第 16 节整表）
```

- [ ] **Step 5: 扩展质量检查清单**

在「质量检查」中把“页面内交互与图片资源正常”扩展/补充为：

```markdown
- 内容图均在 `assets/images/`，网络图标均在 `assets/icons/`，HTML/CSS 为项目内相对路径。
- 无灰色占位、图标冒充内容图、占位图服务或未授权远程内容图/图标依赖。
- 内容图语义匹配可解释；降级/顶替已在完成说明列出。
- 断开外网后打开 `prototype/` 仍可看到内容图与图标。
- 建议存在 `assets/images/images-manifest.json` 且与实际文件大致一致。
- 页面内交互正常。
```

- [ ] **Step 6: 验证专章关键词齐全**

Run（在 skill 目录）：

```bash
grep -n "assets/images\|assets/icons\|语义匹配\|images-manifest\|placehold\|近似图顶替\|图片与图标" docs/shared-prototype-standards.md
```

Expected: 均有命中；专章标题 `## 图片与图标` 存在。

- [ ] **Step 7: Commit（若用户要求提交时再执行）**

```bash
git add "outputs/skills/ycet-prototype-create/docs/shared-prototype-standards.md"
git commit -m "$(cat <<'EOF'
[260712] 扩写原型图片与图标本地化共享规范
EOF
)"
```

本任务默认先不提交，等全部 Task 完成后由用户决定是否 commit。

---

### Task 2: 更新 function-1-static-prototype.md

**Files:**
- Modify: `outputs/skills/ycet-prototype-create/docs/function-1-static-prototype.md`

- [ ] **Step 1: 更新产物树**

在目标产物代码块中 `assets/frames/...` 后增加：

```text
  assets/images/
  assets/icons/
```

- [ ] **Step 2: 更新实现计划门禁**

在「实现计划门禁」列表中增加：

```markdown
- 内容图数量与主要语义类别、图标本地化方案；
- 资源目录 `assets/images/` 与 `assets/icons/`；
- 图片失败策略：严格→大类→非匹配兜底，下载失败近似图顶替，禁止灰占位；
```

- [ ] **Step 3: 更新生成规则**

在「生成规则」增加：

```markdown
- 生成 HTML 前列出内容图位与图标需求，按 `shared-prototype-standards.md`「图片与图标」下载到本地并只写相对路径。
- 建议维护 `assets/images/images-manifest.json`。
- 阶段二已下载的图可在阶段三复用；缺图按语义阶梯补齐。
```

- [ ] **Step 4: 更新完成标准**

增加：

```markdown
- 内容图与网络图标已本地化；无未授权外链与占位图。
- 断开外网后页面内容图与图标仍可显示。
- 语义降级/近似顶替（若有）已在完成说明列出。
```

- [ ] **Step 5: 验证**

```bash
grep -n "assets/images\|assets/icons\|语义\|images-manifest\|灰占位" docs/function-1-static-prototype.md
```

Expected: 产物树、门禁、生成规则、完成标准均有相关行。

---

### Task 3: 更新 function-4-existing-prototype-edit.md

**Files:**
- Modify: `outputs/skills/ycet-prototype-create/docs/function-4-existing-prototype-edit.md`

- [ ] **Step 1: HTML 审计清单增加资源项**

在「HTML 审计」检查列表增加：

```markdown
- 是否存在外链内容图（如 `img[src^="http"]`）或 CSS 远程内容背景图；
- 是否存在远程图标 CDN / 远程 SVG 图标依赖；
- 是否用灰色占位或图标冒充内容图；
- 本地图片/图标相对路径是否指向存在文件；
```

- [ ] **Step 2: HTML 处理流程增加本地化步骤**

在步骤 5（规范化页面与入口）后、步骤 6（用户编辑）前插入实质要求，或扩展步骤 5：

```markdown
5. 规范化页面与入口；将外链内容图下载到 `assets/images/`、远程图标下载到 `assets/icons/` 并改写为相对路径；无法下载时按近似图顶替/语义阶梯处理，仍失败则暂停报告。
6. 执行用户明确要求的编辑。
7. 分别记录“规范化重构”和“用户要求的编辑”；资源本地化与降级一并记入 EditLog。
```

（保持编号连续；若原 6/7 顺延则全文编号一致。）

- [ ] **Step 3: 图片原型流程加边界说明**

在「图片原型流程」末或标题下增加：

```markdown
整页图片原型不套用内容图图库语义匹配阶梯；文件保持本流程落盘约定，须在 `prototype/` 内离线可打开。页面内插图类内容图仍遵守 `shared-prototype-standards.md`「图片与图标」。
```

- [ ] **Step 4: 完成标准增加**

```markdown
- 外链内容图与远程图标已本地化，或已记录用户明确例外。
- 无灰色占位/图标冒充内容图；断网后资源仍可显示。
```

- [ ] **Step 5: 验证**

```bash
grep -n "assets/images\|assets/icons\|外链\|远程图标\|整页图片" docs/function-4-existing-prototype-edit.md
```

Expected: 审计、流程、完成标准均命中。

---

### Task 4: 更新 shared-editlog-rules.md

**Files:**
- Modify: `outputs/skills/ycet-prototype-create/docs/shared-editlog-rules.md`

- [ ] **Step 1: 适用范围增加资源文件**

在适用范围列表增加：

```markdown
- `prototype/assets/images/` 下内容图及 `images-manifest.json`
- `prototype/assets/icons/` 下图标与本地化图标库
```

- [ ] **Step 2: 记录粒度表增加场景**

```markdown
| 内容图/图标本地化 | 下载或替换资源、路径改写、匹配降级或近似顶替、用户外链例外 |
| 图片清单更新 | 生成或更新 images-manifest.json |
```

- [ ] **Step 3: 验证**

```bash
grep -n "images\|icons\|images-manifest\|降级\|顶替" docs/shared-editlog-rules.md
```

Expected: 范围与粒度均命中。

---

### Task 5: 更新 SKILL.md

**Files:**
- Modify: `outputs/skills/ycet-prototype-create/SKILL.md`

- [ ] **Step 1: 全局规则增加第 12 条**

```markdown
12. 内容图与网络获取的 UI 图标须按 `docs/shared-prototype-standards.md`「图片与图标」本地化到 `prototype/assets/images/` 与 `prototype/assets/icons/`；禁止灰占位或图标冒充内容图。
```

- [ ] **Step 2: 完成说明增加资源项**

```markdown
- 内容图/图标是否已本地化，以及是否发生语义降级或近似顶替；
```

- [ ] **Step 3: 验证**

```bash
grep -n "图片与图标\|assets/images\|assets/icons\|降级" SKILL.md
```

Expected: 全局规则与完成说明命中。

---

### Task 6: 全量对照 spec 验收

**Files:**
- Read-only 对照：`docs/superpowers/specs/2026-07-12-prototype-image-assets-design.md`
- 已改 skill 文档

- [ ] **Step 1: 关键词矩阵检查**

确认以下概念在 standards 专章出现，且 f1/f4/editlog/SKILL 无矛盾：

| Spec 要求 | 落点文件 |
| --- | --- |
| 功能一/四强制 | standards + f1 + f4 |
| images/ 与 icons/ | standards + f1 + f4 + SKILL |
| 语义阶梯三级 + 近似顶替 | standards（主）+ f1 门禁摘要 |
| 禁止占位服务 | standards |
| images-manifest 建议 | standards + f1 |
| EditLog 资源记录 | editlog |
| 整页图不套语义阶梯 | f4 |
| 无新脚本 | 全库未新增 validate_images 等 |

- [ ] **Step 2: 更新设计文档状态**

将 spec 头部 `**状态**：待用户审阅` 改为 `**状态**：已批准并实现（文档）`。

- [ ] **Step 3: 向用户汇总 diff 与后续可选 commit**

---

## Spec Coverage Checklist

- [x] 范围与强制功能 → Task 1, 2, 3, 5
- [x] 资源分类与底线 → Task 1
- [x] 目录与命名 → Task 1, 2
- [x] 语义阶梯与下载 → Task 1, 2
- [x] HTML 引用 → Task 1
- [x] 功能一嵌入 → Task 2
- [x] 功能四嵌入 → Task 3
- [x] EditLog → Task 4
- [x] SKILL 指针 → Task 5
- [x] 红线借口 → Task 1
- [x] 非目标（无脚本等）→ 全任务不引入脚本

## Execution Note

用户已确认开始修改 skill：本会话采用 **Inline Execution**，按 Task 1→6 顺序直接改文件，不派发 subagent。
