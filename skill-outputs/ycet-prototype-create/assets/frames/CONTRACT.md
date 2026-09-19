# 设备框架内联契约

Manifest schemaVersion 2 是设备规格与端口映射真源。各 HTML 文件是构建模板，包含作用域 CSS 与 {{CONTENT}} 插槽；build_prototype.py 在构建时内联页面及框架。没有运行时页面路径、iframe 或 postMessage 中继。

保留逻辑视口、预览尺寸、系统 UI、安全区和默认列数。修改模板时运行 test_prototype_v4.py 及 test_runtime_v4.cjs，不直接把片段当独立原型交付。独立原型统一写 prototype/outputs/。

nonframe 仅复用 Manifest 的端口分类，不读取这些模板，也不使用固定逻辑尺寸、安全区或 preview 参数。routing 中 canonicalPort 规范化别名，deviceCategory 标识 mobile/tablet/desktop；带框架类型继续使用 defaultFrameId 和 hostOverrides。
