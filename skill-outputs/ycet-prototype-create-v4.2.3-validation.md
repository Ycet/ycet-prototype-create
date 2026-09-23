# v4.2.3 展示壳风格同步

## 完成内容

- 构建输入新增 shellTheme：同一套参数控制展示壳背景、面板、导航与选中态、标题／说明、缩放工具栏的配色、字体、圆角、阴影及原生控件明暗。
- 功能二从产品设计方向提取参数，功能三直接复用。design-direction、prototype-pages、prototype-demo 不再另用默认浅灰蓝色外壳。无框架产物仅装饰辅助菜单／抽屉。
- 参数构建时转换为内联 CSS，保存到元数据，保持单 HTML 离线交付；无新增运行时依赖、网络请求、CSS 分析或轮询。
- 旧输入省略 shellTheme 时保留原样；既有原型局部修改不强制换肤，也不从过期 JSON 重建。主题同步不修改工作台。
- 外壳规则限定到导航、工具栏、方向说明等专用节点，不重写产品片段／业务脚本或设备系统栏，不改导航、缩放与滚动实现。

## 实际验证

| 检查 | 结果 |
| --- | --- |
| Python 原型／无框架／v4.2／主题回归 | 14 + 7 + 16 + 6 = 43 项通过 |
| 新主题浏览器回归 | 浅色绿色、深色紫色 × 四类产物，共八例通过；Chrome 离线运行，无网络请求、无 pageerror |
| 功能兼容 | 导航选中态、历史返回、页内计数、缩放、适应窗口、桌面／手机布局、抽屉与 Escape 通过 |
| 旧输入浏览器回归 | 四类产物通过，包括长导航、长页面滚动、缩放与独立分享 |
| 结构与发布 | 内置 validate_skill、Git diff 空白、ZIP 完整性、版本及打包源码一致性通过 |
| 通用 Skill quick_validate | 环境缺少 PyYAML，未运行成功；未安装新依赖。项目内置验证已通过 |

没有重复运行本次未改动的工作台服务测试。Edge、Firefox、WebKit 环境不可用，未验证；没有进行真实 Agent 行为评估，仅增加了对应评估场景。旧发布包保留，未全局安装或提交 Git。

## 使用边界

风格来源是已确认的产品设计参数，生成时由 Agent 复用；不会在运行时猜测任意 HTML 的 CSS。主题参数只指定字体栈，不负责下载字体。手工编写原型也遵守相同风格规则。多页面主题不同则使用品牌主主题，不随导航自动换肤。

## 预览

以下是用于验证主题机制的最小样本，不是完整产品设计：

- [浅色 Demo](ycet-prototype-create-v4.2.3-preview/light-demo.png)
- [深色 Demo](ycet-prototype-create-v4.2.3-preview/dark-demo.png)
- [浅色方向预览](ycet-prototype-create-v4.2.3-preview/light-direction.png)
- [深色方向预览](ycet-prototype-create-v4.2.3-preview/dark-direction.png)
- [主题浏览器结果](ycet-prototype-create-v4.2.3-preview/shell-results.json)
- [旧输入浏览器结果](ycet-prototype-create-v4.2.3-preview/legacy-browser-results.json)
