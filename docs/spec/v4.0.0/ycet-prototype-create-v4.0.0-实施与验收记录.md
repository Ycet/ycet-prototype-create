# ycet-prototype-create v4.0.0 实施与验收记录

日期：2026-09-15。实施对象：`skill-outputs/ycet-prototype-create/`。

## 交付结果

已实施五功能重组、统一单文件生成、原型类型与版本确认规则、工作台直接原文件修改、内容同步移除和自动 EditLog 取消。所有标准产物写入 `prototype/outputs/`，页面直接存在于同一 HTML，资源内联，素材可保留归档。

- Skill 入口：[SKILL.md](../../../skill-outputs/ycet-prototype-create/SKILL.md)
- 交付包：[ycet-prototype-create-v4.0.0.skill](../../../skill-outputs/ycet-prototype-create-v4.0.0.skill)
- 验证命令：[verification.md](../../../skill-outputs/ycet-prototype-create/docs/verification.md)
- 原方案：[执行方案](ycet-prototype-create-v4.0.0-执行方案.md)

未安装到全局目录、未发布到远程、未进行 Git 提交。历史测试截图、缓存和工作台运行状态保留在开发目录，但从交付包排除。

## 实现变更

| 模块 | 结果 |
| --- | --- |
| 功能一／二 | 原三阶段流程拆成需求完善和 UI 确认；设计方向也是独立 HTML |
| 功能三 | 统一 A/B/C 类型选择，只制作所选类型；新生成器 `build_prototype.py` 支持三类和 direction |
| 文件策略 | 各类型独立编号；局部原文件修改；三类高影响变更先问版本；工作台始终原文件修改 |
| 功能四 | 普通 UI 沿用、整体重设计确认；端口缺失／冲突时才问；原图承载与确认边界分割保留 |
| 框架与资源 | Manifest schemaVersion 2；框架为内联模板；去 iframe、srcdoc 与文件路径导航；复用严格资源内联器 |
| 工作台 | 递归扫描 prototype；指纹增加 pageId／elementId；完整移除 sync-pages；文件登记 CLI sync 保留 |
| 日志与保护 | 不创建／更新 EditLog；工作台请求、状态、事务、摘要和冲突保护仍保留 |
| 验证与发布 | 替换旧架构专用测试，保留服务与编辑器关键回归；更新校验器、30 个行为场景与发布排除规则 |

## 相对方案的具体实现选择

1. 工作台请求 schemaVersion 保持 1：pageId／elementId 为兼容的附加指纹字段，未进行不必要的协议破坏。移除的 sync-pages 操作由后端明确拒绝。
2. 框架技术说明迁为 `assets/frames/CONTRACT.md`，用于描述内部模板契约；没有创建带未知许可证信息的仓库 README。
3. 旧移动打包器被统一生成器替代；原离线资源解析能力进入 `prototype_document.py`，已删除运行时页面与 srcdoc 转换分支。
4. 原目录架构专用测试由 `test_prototype_v4.py`、`test_runtime_v4.cjs` 和 `test_workbench_v4.cjs` 承接。工作台 HTTP、事务和生命周期测试继续保留。
5. 构建器接受已经规范化的页面片段，不承诺自动转换任意框架源代码。复杂旧 HTML 由功能四指导 Agent 分析并重构；不支持的输入明确报错。

## 实际验证

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| Python 原型回归 | 14 项通过 | 四类产物、设备配置、版本独立、覆盖摘要、并发新文件冲突、资源内联、坏输入、CSS 作用域、SVG 外链、日志保护 |
| Python 工作台回归 | 42 项通过 | HTTP／令牌／Host、上传、关闭、复用、刷新、请求状态、部分成功、依赖冲突、原文件保护、同步操作拒绝 |
| Chrome 原型测试 | 四类通过 | 独立复制到中文及空格目录、file://、离线、零嵌套、静态不跨页、Demo 导航／返回、移动菜单／抽屉／旋转、三档桌面视口 |
| Chrome 工作台端到端 | 通过 | 同 HTML 两页元素定位、字体草稿、撤回、请求包页面和元素指纹、发送前源文件不变、没有同步控件或迭代文件 |
| JS 语法检查 | 通过 | 工作台 app.js、preview-runtime.js 及浏览器测试入口 |
| Skill 一致性检查 | 通过 | 文件、引用、版本、Manifest、模板及评估场景结构 |
| Git diff 空白检查 | 通过 | 没有新增尾随空格等差异格式问题 |

浏览器结果：[browser-results.json](v4.0.0-verification/browser-results.json)。

已检查的演示截图：[Chrome Demo](v4.0.0-verification/chrome-demo.png)。工作台验证截图：[工作台](v4.0.0-verification/workbench-v4.png)。截图内容是测试夹具，不是产品设计样例。

测试期间发现并处理：移动端菜单遮挡左上角业务操作，补回拖动避让；框架 CSS 类名进行命名空间隔离；工作台浏览器用例等待选择消息完成后再编辑，避免测试时序误判。

## 未验证项与实际限制

- Edge 当前未安装，Playwright Firefox 浏览器文件不存在；两者未运行，不能标为通过。
- Safari iOS、Chrome Android 等真机未运行；桌面手机视口只用于响应式与交互验证。
- `evals/evals.json` 的 30 项场景已更新，但本轮没有执行独立模型的完整多轮行为评估；不将其等同于 30 项自动通过测试。
- 静态守卫不能证明任意动态 JavaScript 都没有隐藏依赖，具体产品仍需逐页浏览器检查。构建器主动拒绝全局页面脚本、动态网络及不规范作用域等输入，由 Agent 先规范化再制作。
- 原图承载不能直接编辑图片内部文字；手机聊天附件查看器不一定执行 HTML，需要支持本地 HTML 的浏览器。
- 样例已验证关键路径，未声称覆盖任意复杂导入项目、任意素材格式或所有既有工作台视觉细节。
