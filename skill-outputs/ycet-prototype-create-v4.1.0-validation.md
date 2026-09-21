# ycet-prototype-create v4.1.0 版本说明与验证记录

## 版本定位

- 发布包：[ycet-prototype-create-v4.1.0.skill](ycet-prototype-create-v4.1.0.skill)
- 包含 41 个可安装文件，是从 v4.0.1 到无框架移动／桌面原型的功能版本。
- 详细记录：[v4.1.0 实施与验收记录](../docs/spec/v4.1.0/实施与验收记录.md)、[v4.1.0 优化执行方案](../docs/spec/v4.1.0/优化执行方案.md)。

## 核心变更

- 功能三 C 类型由移动端演示 Demo 调整为无框架交互 Demo，输出 `prototype-nonframe.html` 及独立迭代文件。
- 无框架类型同时支持 iPhone、小程序、移动 H5、Android 等移动端口，以及 Web、桌面端 App 等 PC 端口；按真实浏览器视口自然展示，不绘制设备外壳。
- 增加 `document` 自然长页面和 `app` 固定头尾加内部滚动两种布局；补齐安全区、动态视口、菜单拖动、抽屉焦点循环、背景滚动锁、切页滚动位置和历史返回。
- 扩展 Manifest 端口别名、标准端口和设备分类；旧 `mobile` 输入以兼容别名规范化为 `nonframe`，历史 HTML 不自动改名。
- 所有正式 HTML 继续自包含、直接 DOM、资源内联、无 iframe/srcdoc 和外部运行依赖；工作台既有通用文件登记和预览逻辑复用。
- 引入轻量化结束规则：已完成用户要求并保存的原型修改默认直接结束，不自动继续全量回归、浏览器验收或截图；首次生成和用户明确要求测试仍保留对应验收。

## 验证结果

| 检查 | 结果 |
| --- | --- |
| 原有 Python 测试 | 14 项生成器、42 项工作台通过 |
| v4.1 Python 专项 | 7 项通过，覆盖端口、输入校验、旧输入、编号、audit 边界和写入保护 |
| Chrome 原型回归 | pages、demo、nonframe、direction 四类通过 |
| Chrome 无框架专项 | iOS、Web、desktop-app 共 16 组视口通过，含长内容、根区域尺寸、app 滚动、抽屉焦点和图片热区 |
| Chrome 工作台 | 静态和 nonframe 原型属性编辑、撤回、请求指纹及源文件保护通过 |
| Skill／发布包检查 | 版本、文档引用、框架契约和过程文件过滤通过 |

## 未验证项与限制

- Edge、Firefox、WebKit、iOS Safari、Android 真机未验证；桌面视口模拟不替代真机。
- 无框架布局不能自动修复任意作者写死宽高的业务片段，制作时仍需按产品端口处理页面 CSS。
- 未执行独立 Agent 行为评估，也没有未经测量的耗时或 token 降幅承诺。

