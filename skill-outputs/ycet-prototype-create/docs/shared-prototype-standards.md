# 单文件原型契约 v4

生成或修改前读取 shared-change-policy.md，展示规则读取 prototype-types.md，任务结束规则读取 prototype-validation.md。设备规格唯一真源为 assets/frames/manifest.json（schemaVersion 2）。

## 目录

所有生成 HTML 位于 prototype/outputs/。Spec 在 prototype/docs/Spec.md；原图、图标、字体保留 prototype/assets/ 归档。运行时仅依赖 HTML 本身，不读素材目录、Spec 或 Skill 路径。取消自动 EditLog，保留历史日志。

## 构建输入与命令

脚本接受已确认并规范化的 JSON，不自动迁移任意复杂旧源码。旧输入由功能四先分析并重构。

```json
{
  "type": "demo",
  "title": "产品演示",
  "frameId": "iphone-15-pro",
  "productPort": "ios",
  "initial": "home",
  "pages": [
    {"id":"home","label":"首页","html":"<button data-ycet-nav-target=\"detail\">详情</button>","css":":scope button { color: #2563eb; }","js":""},
    {"id":"detail","label":"详情","html":"<h1>详情</h1><button data-ycet-back>返回</button>","css":"","js":""}
  ]
}
```

```sh
python <skill>/scripts/build_prototype.py --input <JSON> --prototype-dir <项目>/prototype --mode create
python <skill>/scripts/prototype_guard.py <项目>/prototype/outputs/prototype-demo.html
```

mode 为 create／iterate／overwrite；覆盖必须显式 --target <现有文件名> --expected-sha <修改前摘要>。iterate 仅在用户已选择新增版本后使用。不能用过期 JSON 覆盖工作台已修改的 HTML；现有 HTML 是编辑事实来源。

pages 为全部页面片段，type 为 pages／demo／nonframe／direction。direction 必须一页，directionHtml 放设计组件说明。资源引用以 prototype 根为基准，构建时内联；构建器不访问网络，远程资源先获取并归档。

## 页面与脚本

每页直接 section[data-ycet-page-id]；页面 ID 唯一且 ASCII kebab-case。元素使用稳定 data-ycet-element-id，修改时保留。DOM id、SVG id、aria 引用、动画名应在页面间唯一；不把多个完整 HTML 文件直接拼接。

CSS 使用 :scope 表示页面根，每个选择器限定页面根。JS 通过 root 查询当前页，navigate(pageId) 执行业务导航；不要操作全局 document/window，不动态请求网络。静态类型的 navigate 无效，只保留页内交互。复杂脚本须先由 Agent 重构为页面闭包，不能删除业务后声称完成。

带框架类型固定元素相对页面根定位；nonframe 使用实际视口或产品局部容器，不继承框架的 contain/裁切。弹窗和滚动限于所属页面。隐藏页退出焦点与无障碍遍历。B/C 导航使用同文档 hash 历史，目标仅在当前注册表内。非法目标保留当前页并报告。

## 设备与展示

Manifest 决定 logicalViewport、preview、safeArea、defaultColumns。iPhone／Android／iPad／Web／Desktop 按 routing 映射，微信小程序默认 iPhone，明确 Android 宿主才覆盖。

设备框架作为构建时内联片段，保留系统 UI。产品不要重复绘制状态栏／Home Indicator；nonframe 不使用设备模板、固定逻辑尺寸或仿真系统栏；产品自己的导航／标题栏保留。框架中的 {{CONTENT}} 在构建时替换为实际页面 DOM，不做运行时文件加载。

所有显式滚动容器标记 data-ycet-scroll；Chrome／Edge／Firefox 隐藏原生滚动条但保留必要滚动。卡片外层与页内滚动职责分离。

## 内容图与离线

内容图与图标分开归档；保留原有严格语义→大类→真实图片兜底的匹配顺序，降级如实报告，不用灰占位或图标冒充内容图。图片原型保留原位图，固定区边界需确认。

CSS、JS、图片、srcset、SVG、图标、字体均内联；网络 URL 仅可作为不执行的溯源信息。自定义字体要内嵌，或使用已确认系统字体栈。禁止 iframe/srcdoc/object/embed 页面嵌套、外部 CSS/JS、动态接口和路径依赖。真实后端需明确为本地演示数据，无法实现时说明，不静默降级。

仅首次生成或用户明确要求此项验收时：复制单个 HTML 到含中文和空格的空目录，以 file:// 并断网逐页验证。修改完成即结束，不追加该步骤。机械检查不代表浏览器验收，更不能代表手机真机结果。

## 工作台边界

只有功能五启动工作台。编辑器宿主 iframe 是预览工具，不属于原型交付物；响应注入不得写进源 HTML。工作台图片先上传为草稿，执行请求时归档并内联。完成回复记录实际修改，不写 EditLog。


## 无框架构建与修改用途

C 使用 type=nonframe，必须指定有效 productPort；frameId 可省略，残留值会提示并忽略。支持 ios/iphone/android/mobile-h5/h5/wechat-mini-program、ipad/tablet、web/desktop/desktop-app/windows/macos 等 Manifest routing 端口。未知端口先澄清。元数据 frame=null，skillVersion=4.2.2，schemaVersion 仍为 1。

页面可选 layout=document（默认，自然长页面）或 app（占满视口，内部滚动）。app 的直接子节点 data-ycet-scroll 自动占据剩余高度，固定头尾为其兄弟节点；嵌套布局自行提供 min-width/min-height:0 和滚动区域。page CSS 不得把根重新固定为设备尺寸。图片按比例适宽；热区坐标跟随同一图片容器。

```json
{"type":"nonframe","productPort":"web","initial":"home","pages":[{"id":"home","layout":"document","html":"<h1>首页</h1>","css":"","js":""}]}
```

写入 mode 与任务 purpose 分开：create 默认 initial；iterate/overwrite 默认 modify。已交付目标原型后续转成新类型文件名即使使用 create，也必须传 --purpose modify。功能四首次基于 HTML／图片生成目标文件使用 create 和 --purpose initial，保留首次交付验收。修改模式不自动调用 audit；--validate 仅用于用户明确要求的验收。输入、资源内联和原子写入保护始终保留；命令返回文件路径表示写入成功，不等于浏览器验收通过。

旧 type=mobile 输入作为兼容别名转为 nonframe 并提示，需明确有效端口；旧 HTML 元数据仍可由守卫读取。历史 mobile 文件不改名、不占用 nonframe 编号。旧源码的局部修改直接编辑，不从旧 JSON 重建覆盖。
