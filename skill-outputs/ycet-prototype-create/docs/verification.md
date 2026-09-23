# Skill 开发验证（非日常原型修改）

仅开发／发布 Skill 源码时使用下列命令。用户修改产品原型遵循 prototype-validation.md，完成即结束，不自动执行本页测试。

脚本使用 Python 3.10+ 标准库。浏览器回归另需 Node.js、Playwright 和相应浏览器；使用环境现有依赖，不自动安装。

```sh
python scripts/test_prototype_v4.py
python scripts/test_prototype_workbench.py
python scripts/test_nonframe_v41.py
python scripts/test_prototype_v42.py
python scripts/test_shell_theme_v423.py
python scripts/test_shell_theme_v423.py --fixtures <空主题测试目录>
node scripts/test_shell_theme_v423.cjs <同一主题测试目录>
python scripts/validate_skill.py
python scripts/test_prototype_v4.py --fixtures <空测试目录>
node scripts/test_runtime_v4.cjs <同一测试目录>
python scripts/test_nonframe_v41.py --fixtures <同一测试目录>
node scripts/test_nonframe_v41.cjs <同一测试目录>
node scripts/test_workbench_v4.cjs <同一测试目录>
node scripts/test_preview_priority_v4.cjs
node scripts/test_inspector_v421.cjs <截图与结果目录>
node scripts/test_workbench_v422.cjs <截图与结果目录>
python scripts/release_audit.py --output <Skill目录外的发布包.skill>
```

Playwright 不在默认模块路径时设置 NODE_PATH；工作台浏览器测试可通过 PYTHON 指定标准库 Python。测试临时工作台仅绑定 127.0.0.1，测试后关闭。宿主禁止监听端口或启动浏览器时使用环境授权流程，不修改权限配置。

源码静态检查、功能回归与真实浏览器结果分开报告。行为评估场景在 evals/evals.json，不能将其文件存在声称为已完成 Agent 评估。浏览器不可用时报告未验证。

工作台 UI 全部行为规范见 workbench-maintenance.md，请求执行见 workbench-request.md。v4.2 回归覆盖结果完整性、元素标识、脚本文案与调用区别、选择器及扫描缓存。
