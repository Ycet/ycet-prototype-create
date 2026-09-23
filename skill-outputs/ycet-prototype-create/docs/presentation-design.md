# 原型外围设计：复用结构，定制产品语言

生成 direction／pages／demo 时读取本页；无需读取生成器、CSS 模板或历史示例。已有原型的普通局部修改继续沿用原结构。运行时仍是一个离线 HTML，工作台与设备模板不参与换肤。

## 一次准备，三类文件复用

从已选 UI Skill／确认方向提取 shellTheme 与 presentation，随产物元数据保存，后续正式文件直接复用。背景、正文／标题字体、主色、圆角和组件细节与产品保持同源；展示壳可以更安静，但不另选一套默认蓝灰风格。参考图的具体配色不固化为所有产品的默认。多个页面的主题不同则使用品牌主主题。

shellTheme 颜色与字体字段见 shared-prototype-standards.md。另支持 headingWeight（字符串 400–800，默认 600）、lineStyle（solid/dashed/dotted，默认 solid）、motion（0ms–300ms，默认 160ms；自动尊重减少动态效果）。presentation.summary 为简短产品说明，density 为 comfortable（默认）或 compact。样式选择由产品决定：例如手记可使用轻量虚线与衬线标题，数据工具可用紧凑间距、直线与清晰数字层级。

原有交互语义不随视觉风格改变：导航点击仍切页并双向高亮；缩放只作用于设备区；控件的悬停、焦点、按下、禁用反馈使用相同主题。需要演示产品特有状态时只补相应局部交互。

## 设计方向页是可视展板

使用 direction 对象组织内容，生成器自动排版标题、色板、字阶、组件卡片和设备首页。首页只保留一个，展示真实业务内容。标准信息自动从 shellTheme 得到，无需重复编写色板／网格 CSS。

- 色彩展示真实色块、名称、值和用途；默认从主题生成六色，也可提供完整品牌色板。
- 字体展示实际标题与正文样本，使用产品字体与字重；字体文件仍需内嵌或使用已确认的系统字体栈。
- components 写少量具有产品辨识度的实际组件：主要操作、输入／选择、反馈或业务特色状态。组件使用真实产品文案，反馈有可见状态；动效、折叠或提交演示需能操作。
- 说明用于解释已展示的设计决策，不用“主色 #…”“点击后有动画”这样的文字列表代替色板或交互。未经实际检查不声明“满足 WCAG AA”“性能优秀”。

```json
{
  "presentation": {"summary":"随手记录生活，回看值得留下的瞬间。","density":"comfortable"},
  "direction": {
    "titleSample":"把今天的心情写下来",
    "bodySample":"不必写得完整，一句话也能留住当下。",
    "components":[
      {"title":"记录操作","description":"主要操作与次要操作有明确层级。","html":"<button type=\"button\" data-save data-variant=\"primary\">保存手记</button><button type=\"button\" disabled>保存中…</button><span role=\"status\" data-status>尚未保存</span>"},
      {"title":"阅读偏好","description":"展开查看设置。","html":"<details><summary>阅读设置</summary><label>字号 <select><option>标准</option><option>大号</option></select></label></details>"}
    ]
  },
  "directionCss": ":scope [data-status]{font-size:12px;color:var(--ycet-shell-accent)}",
  "directionJs": "root.querySelector('[data-save]').addEventListener('click',()=>{root.querySelector('[data-status]').textContent='已保存';});"
}
```

需要额外品牌色时提供 direction.palette 数组，成员含 name、value（十六进制）、usage。组件 html 为片段；现有 directionHtml 仍可作为补充区域。directionCss 中每个选择器以 :scope 限定展板，动画名加 direction- 前缀；directionJs 仅通过 root 操作展板，不访问 document/window 或导航，不改产品页面脚本。内置按钮支持 data-variant="primary"，普通按钮、表单、details 提供基础状态样式；聊天气泡、特殊导航等特色组件只写局部片段和局部 CSS，沿用产品的实际组件外观。

## 静态页与 Demo

静态页自动生成产品标题、说明、页面数与页面卡片标题；可用 pages[].description 补充页面目的。沿用 Manifest 列数、设备尺寸和页面内交互，不增加跨文件链接。

Demo 自动生成品牌标题、说明、分组导航、选中态和工具栏。pages[].group 为导航组名，按页面输入顺序展示；description 可作短说明。保留长列表滚动、现有返回与缩放，不用截图中的 v3 多文件结构替代当前单文件实现。无框架类型仍仅装饰辅助菜单／抽屉，不添加外围展板。

## 轻量完成标准

首次生成时，在既有的一次浏览器检查中同时查看首屏、组件区与首页；检查产品与外围的文字层级、可视样本和主要交互，不另开完整审计流程。修正明显错位、无样式组件或失效交互后交付。不追加大量备选稿、网上搜模板、字体下载或全量回归。旧输入未提供 shellTheme 时仍兼容原有样式。
