# 原型制作 Skill

## 项目简介

本项目维护 `ycet-prototype-create` skill，用于指导 Agent 从产品需求生成高保真原型、精准修改原型、生成可交互 demo，并接管已有 HTML 或图片原型进行规范化重构与编辑。

## 当前状态

测试中：原始版本保留在 `skill/ycet-prototype-create/`，本轮优化版本输出到 `outputs/skills/ycet-prototype-create/`。

## 功能范围

- 功能一：从产品需求到高保真静态原型页面。
- 功能二：通过浏览器开发者工具信息精准修改原型元素。
- 功能三：从高保真静态原型页面生成可交互原型 demo。
- 功能四：HTML 或图片原型规范化重构与编辑。

暂不包含：

- 自动发布 skill 到远程仓库。
- 自动安装或替换 Claude Code / Codex 的全局 skill 引用。

## 项目结构

```text
skill/
  ycet-prototype-create/
outputs/
  skills/
    ycet-prototype-create/
      SKILL.md
      agents/
      assets/frames/
      docs/
      evals/
      scripts/
```

## 使用方式

使用本轮优化结果时，将 `outputs/skills/ycet-prototype-create` 作为 Codex 或 Claude Code skill 目录。Agent 读取 `SKILL.md` 后，应先完成路由判断，再按需读取对应功能文档和共享规范文件。

验证命令：

```powershell
python outputs\skills\ycet-prototype-create\scripts\validate_skill.py
python outputs\skills\ycet-prototype-create\scripts\test_frames_runtime.py
```

## 文档索引

- `outputs/skills/ycet-prototype-create/SKILL.md`：优化版总入口、路由规则和全局强制规则。
- `outputs/skills/ycet-prototype-create/docs/`：功能文档与共享规范。
- `outputs/skills/ycet-prototype-create/assets/frames/`：Manifest 与五类设备框架。
- `outputs/skills/ycet-prototype-create/evals/evals.json`：技能行为评估用例。

## 已知限制

- 自动化脚本覆盖 Skill 结构、框架元数据和设备框架运行时行为；尚未自动执行完整的 Agent 对话评估。
