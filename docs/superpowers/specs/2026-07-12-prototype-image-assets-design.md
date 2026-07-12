# 原型内容图与图标本地化规范设计

**日期**：2026-07-12  
**状态**：已批准并实现（文档）  
**关联 Skill**：`outputs/skills/ycet-prototype-create`  
**触发来源**：细化 `shared-prototype-standards.md` 中“内容图片使用真实图片资源；UI 操作图标使用图标库，不互相替代。”

## 1. 背景与问题

当前 `shared-prototype-standards.md` 仅有一句原则性要求，以及质量检查中的“图片资源正常”。缺少：

- 内容图与 UI 图标的职责边界
- 本地落盘目录与命名规则
- 语义匹配严格度与降级阶梯
- 图库获取与下载失败策略
- 打包离线可用的硬性验收
- 功能一 / 功能四流程中的嵌入点

结果是执行 agent 容易：

- 用灰色占位或图标冒充内容图
- 直接写 Unsplash / CDN 外链，打包发送后失效
- 商品位放风景、头像位放无关图
- 图标继续依赖外网 CDN

## 2. 目标

1. 内容图与功能模块语义匹配。
2. 内容图全部本地化到 `prototype/assets/images/`。
3. 网络获取的 UI 操作图标本地化到 `prototype/assets/icons/`。
4. 用户打包发送整个 `prototype/` 后，在无网环境下图片与图标仍可用。
5. 图标与内容图职责不互相替代。
6. 规则集中在共享规范专章，功能文件只做引用与检查项补充。

## 3. 非目标

- 不新增自动校验脚本或 CI（如 `validate_images.py`）。
- 不强制功能二、功能三对既有页面做全量外链审计。
- 不改变设备框架资产规则（框架仍不引用外部图片）。
- 不引入付费图库或 API Key 流程。
- 不默认使用 AI 生图。
- 不改变功能四“整页图片原型”的既有落盘与导入主流程。

## 4. 决策摘要

| 决策点 | 结论 |
| --- | --- |
| 内容图默认来源 | 免费图库（Unsplash / Pexels / Pixabay 等） |
| 下载方式 | 通用 HTTP 下载（curl 等），不强制专用 CLI |
| 下载失败 | 项目内近似图顶替；禁止灰占位 / 图标顶替 |
| 语义匹配 | 严格 → 大类 → 非匹配兜底（不可跳级） |
| 文件命名 | 语义文件名：`{page}-{role}-{semantic}[-nn].ext` |
| 强制范围 | 功能一、功能四 |
| 文档落点 | 方案 A：`shared-prototype-standards.md` 扩写专章 |
| 图标网络资源 | 同样本地化到 `assets/icons/` |

## 5. 适用范围

| 功能 | 是否强制 | 说明 |
| --- | --- | --- |
| 功能一 静态原型 | **强制** | 生成 `design-direction` / `home-preview` / `pages` 时，所有内容图与网络图标必须本地化 |
| 功能二 精准修改 | 不强制全量审计 | 若修改引入新内容图或网络图标，按本规范本地化；纯文案/样式改动不动资源 |
| 功能三 交互 Demo | 不强制全量审计 | 不主动扫外链；若生成过程新增内容图或网络图标，按本规范本地化 |
| 功能四 HTML 规范化 | **强制** | 审计并本地化外链内容图与远程图标；**整页图片原型**仍走功能四既有导入流程 |

## 6. 资源分类与硬边界

| 类型 | 用途 | 存放位置 | 允许形式 | 禁止 |
| --- | --- | --- | --- | --- |
| UI 操作图标 | 导航、操作、状态、Tab、按钮旁图标等 | `prototype/assets/icons/` | 本地 SVG / 字体图标库文件；页面相对路径引用 | 用图标冒充内容图；交付态依赖未本地化的远程图标 URL/CDN |
| 内容图片 | 商品图、海报、头像、Banner、封面、列表缩略图、空状态插画位等 | `prototype/assets/images/` | 真实照片/插画；本地相对路径 | 灰占位、图标顶替、远程外链（无用户例外）、能匹配时仍用无关图 |

### 6.1 图标本地化细则

1. 凡从网络获取的图标资源（远程 SVG/PNG、图标 CDN 的 CSS/字体、网上下载的单枚图标），交付前必须写入 `prototype/assets/icons/`（或其下合理子路径，如 `icons/fontawesome/`），页面改为相对路径引用。
2. 推荐优先使用开源图标库的本地化拷贝（整库 CSS+字体，或按需 SVG），而不是页面写 `https://cdn.../font-awesome.css`。
3. 例外仅在用户明确要求时启用，且必须在完成说明与 `EditLog` 中记录“图标仍依赖外网”；默认策略仍是本地化。
4. 图标文件不得放入 `assets/images/`；内容图不得放入 `assets/icons/`。

### 6.2 底线（不可协商）

1. 交付态页面中，内容图 `src` 与图标引用均不得依赖未本地化的远程 URL（用户明确例外并记录的除外）。
2. 禁止用灰色占位、skeleton-only 色块、或图标库图标代替内容图位。
3. 禁止交付态使用 `picsum.photos`、`placehold.co`、`via.placeholder.com`、纯色/渐变 div 冒充内容图等占位方案。
4. 功能四的整页截图/设计稿图片是另一类资产，不套用内容图“图库语义匹配阶梯”；但其文件必须在 `prototype/` 内且可离线打开。

## 7. 目录结构

在现有 `prototype/` 上扩展：

```text
prototype/
  assets/
    frames/                 # 既有：设备框架
    images/                 # 新增：内容图片
      images-manifest.json  # 建议：内容图清单（可选但推荐）
    icons/                  # 新增：UI 操作图标 / 本地化图标库
  pages/
  previews/
  docs/
  ...
```

说明：

- `images/` 只放内容图；`icons/` 只放 UI 图标与图标库文件。
- 不强制 `images/` / `icons/` 再分子目录；单页图很多时允许 `images/home/` 等语义子目录。
- 功能四整页图片原型默认**不改**既有落盘位置，只要求离线可用。

## 8. 命名规则

### 8.1 内容图

格式：

```text
{page-or-module}-{role}-{semantic}[-{nn}].{ext}
```

| 段 | 规则 | 示例 |
| --- | --- | --- |
| page-or-module | 小写英文与短横线，对应页面或模块 | `home`、`product-detail` |
| role | 固定角色词 | `banner`、`avatar`、`product`、`cover`、`thumb`、`poster`、`hero` |
| semantic | 内容语义关键词 | `coffee`、`running-shoes`、`female-portrait` |
| nn | 同角色多图时两位序号 | `01`、`02` |
| ext | 优先 `jpg` / `jpeg` / `png` / `webp` | |

示例：

- `home-banner-summer-sale.jpg`
- `home-product-running-shoes-01.jpg`
- `profile-avatar-female-portrait.jpg`
- `order-thumb-coffee-latte.png`

禁止：`img1.jpg`、`photo.png`、中文文件名、空格、无语义哈希名（除非用户明确要求）。

### 8.2 图标

| 场景 | 约定 |
| --- | --- |
| 单枚 SVG/PNG | `{purpose}.svg` 或 `{purpose}-{variant}.svg`，如 `nav-home.svg`、`action-share.svg` |
| 整库本地化 | `icons/fontawesome/` 等保持库内原始结构，不强制改每个文件名 |
| 页面引用 | 相对路径，如 `../assets/icons/nav-home.svg` 或 `../assets/icons/fontawesome/css/all.min.css` |

## 9. 语义匹配阶梯（内容图）

生成或补图时按顺序执行，**不可跳级**：

1. **严格匹配**  
   按模块角色 + 业务语义检索。  
   例：咖啡商品卡 → 咖啡/饮品实物图；女性用户头像 → 女性人像；跑步鞋 Banner → 跑鞋或跑步场景。

2. **大类匹配**（严格无可用图源时）  
   同业态/同视觉大类。  
   例：咖啡 → 饮品/餐饮；跑鞋 → 运动鞋/运动；人物头像 → 同类人像（性别/年龄大体一致）。

3. **非匹配兜底**（大类仍失败时）  
   允许使用语义不匹配但风格尽量接近设计方向的真实图。  
   **必须**在完成说明中列出：文件名、原期望语义、实际使用语义、原因。

4. **近似图顶替**（下载失败时）  
   - 优先复用本项目 `assets/images/` 中已下载、语义最接近的图。  
   - 复用时复制并按新图位重命名，避免多处共享同一文件导致后续替换互相影响。  
   - 若项目内无可复用图，再回到阶梯 2→3 重新检索下载。  
   - **禁止**因此改用灰占位或图标顶替。

### 9.1 检索词构造

每个内容图位在生成前应确定（可写在实现计划或内部清单，不必每次问用户）：

```text
{
  page: "home",
  role: "product",
  semantic: "running shoes",
  query: "running shoes product photo white background",
  orientation: "square" | "landscape" | "portrait",
  matchLevel: "strict" | "category" | "fallback"
}
```

规则：

- `query` 优先英文关键词检索免费图库。
- 同一列表多商品：语义应区分，禁止整页复制同一张商品图糊弄（空状态/占位列表等合理重复除外）。
- 头像注意人物属性大体一致；商品注意品类；Banner 注意场景与活动主题。

## 10. 获取与下载流程

### 10.1 图库优先级

1. Unsplash  
2. Pexels  
3. Pixabay  
4. 其他明确可免费使用的图源  

不绑定单一官方 API；使用可稳定下载的公开图片 URL + 通用 HTTP 工具即可。

### 10.2 推荐执行顺序

1. 根据页面结构列出全部内容图位与图标需求。  
2. 为每个内容图位确定 `role`、`semantic`、`query`、期望比例。  
3. 从图库检索候选图，按语义阶梯选图。  
4. 使用通用 HTTP 下载到 `prototype/assets/images/`，按命名规则落盘。  
5. 将网络图标/图标库下载到 `prototype/assets/icons/`。  
6. HTML / CSS 中只写项目内相对路径。  
7. 建议写入或更新 `prototype/assets/images/images-manifest.json`。  
8. 质检：路径存在、无未授权外链、无占位服务、语义降级已记录。

### 10.3 下载约束

- 优先中等体积，单张内容图建议控制在约 200KB–1.5MB（非硬阈值，避免过大二进制拖垮原型包）。  
- 保留合理宽高，避免明显拉伸。  
- 不把远程 URL 留在交付 HTML 中“以后再说”。  
- 下载失败：近似图顶替 → 再检索；仍失败则暂停并报告失败图位，不静默交付残缺包。

### 10.4 `images-manifest.json`（建议）

路径：`prototype/assets/images/images-manifest.json`

建议字段：

```json
{
  "schemaVersion": 1,
  "images": [
    {
      "file": "home-product-running-shoes-01.jpg",
      "page": "home",
      "role": "product",
      "semantic": "running shoes",
      "matchLevel": "strict",
      "source": "unsplash",
      "sourceUrl": "https://...",
      "downloadedAt": "2026-07-12",
      "usedBy": ["pages/home.html"]
    }
  ]
}
```

用途：溯源、EditLog、后续替换与审计。非运行时强依赖；页面不得只靠 manifest 才能显示图片。

## 11. HTML 引用约定

页面内示例：

```html
<!-- 内容图：真实本地资源 -->
<img
  src="../assets/images/home-product-running-shoes-01.jpg"
  alt="跑鞋商品图"
/>

<!-- UI 图标：本地 SVG 或本地图标库 -->
<img src="../assets/icons/nav-home.svg" alt="" />
<!-- 或 -->
<link rel="stylesheet" href="../assets/icons/fontawesome/css/all.min.css" />
<i class="fa-solid fa-house" aria-hidden="true"></i>
```

路径规则：

- `pages/*.html`、`previews/*.html` 使用相对路径指向 `../assets/images/` 与 `../assets/icons/`。
- 根目录 HTML（如 `design-direction.html`、`index.html`）使用 `assets/images/`、`assets/icons/`。
- 禁止本 Skill 安装目录的绝对路径。
- 禁止 `file:///...` 绝对本地路径。
- CSS `background-image` 中的内容图同样必须本地相对路径。

## 12. Skill 文档落点（方案 A）

| 文件 | 改动 |
| --- | --- |
| `docs/shared-prototype-standards.md` | **主战场**：扩写「图片与图标」专章；更新目录结构、技术栈图标说明、页面文件条款、质量检查清单 |
| `docs/function-1-static-prototype.md` | 产物树增加 `assets/images/`、`assets/icons/`；实现计划门禁与生成规则增加资源清单/本地化步骤；完成标准增加离线资源检查 |
| `docs/function-4-existing-prototype-edit.md` | HTML 审计增加外链内容图/远程图标项；规范化步骤增加下载本地化；明确与整页图片原型边界 |
| `docs/shared-editlog-rules.md` | 记录范围增加：下载/替换内容图、本地化图标、生成或更新 `images-manifest.json` |
| `SKILL.md` | 全局规则增加 1 条极简指针；细节以 shared 专章为准 |
| 功能二 / 功能三 | 不扩强制流程；新增资源时遵守 shared 专章（在适用范围表写明即可） |

**不做**：独立 `shared-image-assets.md`、校验脚本、下载 helper CLI。

## 13. 功能流程嵌入

### 13.1 功能一

```text
阶段二 生成 home-preview / design-direction
  → 列出内容图位 + 图标需求
  → 下载内容图到 assets/images/
  → 本地化图标到 assets/icons/
  → 页面只写相对路径
  → 写/更新 images-manifest.json

阶段三 生成 pages + index
  → 按页扩展图位清单（可复用阶段二已下载图）
  → 缺图按语义阶梯补齐
  → 质检：无外链内容图、无远程图标依赖（无用户例外）、路径存在、语义阶梯记录完整
```

实现计划门禁（用户确认项）增加：

- 预计内容图数量与主要语义类别
- 图标方案（本地化库名或单枚 SVG）
- 资源目录：`assets/images/`、`assets/icons/`
- 失败策略摘要：严格→大类→非匹配兜底；下载失败近似图顶替；禁止灰占位

### 13.2 功能四

HTML 规范化审计新增：

| 检查项 | 不合规表现 |
| --- | --- |
| 内容图外链 | `img[src^="http"]` 等指向非本地内容图 |
| 图标远程依赖 | 远程 font/icon CDN 或远程 SVG 图标 |
| 占位滥用 | 灰块/图标冒充内容图 |
| 路径失效 | 相对路径指向不存在文件 |

规范化动作：

1. 外链内容图 → 下载到 `assets/images/` 并改写 `src`  
2. 远程图标 → 下载到 `assets/icons/` 并改写引用  
3. 无法下载时：近似图顶替 / 阶梯兜底；仍失败则暂停并报告，不交付“假装完整”的包  
4. 更新 `images-manifest.json` 与 EditLog  

整页图片原型：不套用图库语义阶梯；文件保持功能四既有位置；保证离线可打开。

## 14. EditLog 与完成说明

### 14.1 EditLog 必记动作

- 批量下载内容图 / 本地化图标
- 按阶梯降级（大类匹配、非匹配兜底、近似图顶替）
- 用户授权的 CDN/外链例外
- 外链改本地路径的批量替换

建议记录：动作类型、涉及文件数、是否发生降级、例外说明。

### 14.2 完成说明须包含

- 内容图目录与数量；是否使用 `images-manifest.json`
- 图标是否已本地化及路径
- 发生过的匹配降级 / 顶替列表（若有）
- 用户例外（若有）
- 提醒：打包发送整个 `prototype/` 即可离线查看

## 15. 质量检查补充项

在既有质量检查上增加：

- [ ] 所有内容图位于 `prototype/assets/images/`，HTML/CSS 为相对路径
- [ ] 网络获取的图标位于 `prototype/assets/icons/`，无未授权远程图标依赖
- [ ] 无灰色占位 / 图标冒充内容图 / 占位图服务
- [ ] 内容图语义匹配可解释；降级项已在完成说明列出
- [ ] 断开外网后打开 `prototype/` 仍可看到内容图与图标
- [ ] 建议存在 `images-manifest.json` 且与实际文件大致一致
- [ ] `EditLog.md` 已记录资源下载/本地化/降级（若发生）

## 16. 红线与常见借口

| 借口 | 现实 |
| --- | --- |
| “先用 picsum/占位，下次再换真图” | 交付即须真图本地化；禁止占位交付 |
| “CDN 图标打开快，file 协议也能用” | 对方断网或打包内网会挂；默认本地化 |
| “语义差不多就行，随便下张图” | 先严格再大类；跳级须有失败原因 |
| “图片太多，只下 Banner” | 所有内容图位同等要求 |
| “外链写着，用户有网就行” | 本规范目标是打包离线可读 |
| “图标算 UI 不用本地” | 网络获取的图标同样本地化到 `assets/icons/` |
| “功能四原页面就有 Unsplash 链接，别动” | 规范化强制本地化外链内容图 |

## 17. 成功标准

1. Agent 执行功能一时，内容图均在 `assets/images/`，图标在 `assets/icons/`，HTML 相对路径可离线打开。  
2. 无灰占位 / 图标顶替内容图。  
3. 语义优先严格匹配，降级有记录。  
4. 功能四规范化后消除内容图外链与远程图标依赖（或显式用户例外）。  
5. `prototype/` 整体打包拷贝到无网环境仍可看图。  
6. 规范只集中在 shared 专章 + 功能文件引用，无平行第二套互相矛盾的规则。

## 18. 建议实现顺序（供后续 writing-plans）

1. 扩写 `shared-prototype-standards.md`「图片与图标」专章，并同步目录结构 / 技术栈 / 页面文件 / 质量检查。  
2. 更新 `function-1-static-prototype.md` 产物树、门禁、生成规则、完成标准。  
3. 更新 `function-4-existing-prototype-edit.md` 审计与规范化步骤。  
4. 更新 `shared-editlog-rules.md` 记录范围。  
5. 在 `SKILL.md` 增加一条全局指针。  
6. 用压力场景（占位诱惑、外链诱惑、语义偷懒、图标 CDN）验证 agent 是否遵守。  

## 19. 已确认的用户选择记录

- 内容图来源：免费图库下载  
- 下载失败：近似图顶替  
- 命名：语义文件名  
- 语义匹配：优先严格，找不到则大类，再找不到允许不匹配图  
- 强制范围：功能一 + 功能四  
- 图库工具：通用 HTTP 下载  
- 落地方式：共享规范专章（方案 A）  
- 追加要求：网络获取的 UI 操作图标也下载到 `assets/icons/`  
