# 设备框架资产契约

本目录是 `ycet-prototype-create` 的设备框架库。`manifest.json` 是端口映射、逻辑画布、预览尺寸、安全区域与消息协议的唯一数据真源；框架 HTML 和本文件必须与其保持一致。

## 文件

```text
assets/frames/
  manifest.json
  iphone-15-pro.html
  android-pixel.html
  ipad-pro.html
  browser-chrome.html
  macbook.html
```

## 生成项目时的用法

只复制当前端口使用的框架到 `prototype/assets/frames/`，并生成 `frame-config.json` 配置快照。承载页面通过相对路径加载框架：

```html
<iframe
  data-ycet-frame-id="iphone-15-pro"
  src="assets/frames/iphone-15-pro.html?screen=pages/home.html"
  title="首页"
></iframe>
```

`screen` 参数只接受 URL 编码后的 `pages/*.html` 或 `previews/*.html` 相对路径。生成文件不得依赖 Skill 安装目录的绝对路径。

## 职责边界

- 框架负责系统 UI：状态栏、灵动岛、Home Indicator、Android 系统导航、浏览器外壳等。
- 内部页面负责产品 UI：App 顶部导航、Tab Bar、微信胶囊按钮、网站导航、桌面应用菜单和业务内容。
- 页面根据 Manifest 的 `safeArea` 避让系统 UI，不重复绘制系统元素。

## 消息协议

框架使用以下固定协议中继内外层消息：

```javascript
{
  channel: "ycet-prototype",
  version: 1,
  type: "navigate"
}
```

支持 `ready`、`navigate`、`set-screen`、`screen-changed`、`error`。框架必须验证 `event.source`、channel、版本、类型和页面路径；为兼容本地 `file://`，不能只依赖 origin 字符串。

## 维护规则

1. 每个文件只实现一个设备框架。
2. 不引用外部图片、字体或脚本；设备装饰使用内联 CSS/SVG。
3. 修改逻辑尺寸、预览尺寸、安全区域、系统 UI 或协议时，同步更新 Manifest 和本说明。
4. 页面 iframe 始终以 Manifest 的 `logicalViewport` 渲染，再由框架整体缩放到预览尺寸。
5. 框架必须支持 `?screen=about:blank` 以外的受控项目页面；无页面时显示中性空白画布。
6. 未知消息、非法路径和加载异常不得导致框架跳转到远程地址。
