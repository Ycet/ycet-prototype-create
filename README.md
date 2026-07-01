# 原型制作 Skill

## 项目简介

本项目维护 `ycet-prototype-create` skill，用于指导 Agent 从产品需求生成高保真原型、精准修改原型、生成可交互 demo，并接管已有 HTML 或图片原型进行规范化重构与编辑。

## 当前状态

开发中：正在将单体 `SKILL.md` 重构为总入口路由 + 独立功能文档 + 共享规范文档。

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
    SKILL.md
    docs/
      function-1-static-prototype.md
      function-2-precision-edit.md
      function-3-interactive-demo.md
      function-4-existing-prototype-edit.md
      shared-prototype-standards.md
      shared-editlog-rules.md
    agents/
    evals/
优化想法.txt
```

## 使用方式

将 `skill/ycet-prototype-create` 作为 Codex 或 Claude Code skill 目录使用。Agent 读取 `SKILL.md` 后，应先完成路由判断，再按需读取对应功能文档和共享规范文件。

## 文档索引

- `skill/ycet-prototype-create/SKILL.md`：总入口、路由规则、全局强制规则。
- `skill/ycet-prototype-create/docs/`：功能文档与共享规范。
- `skill/ycet-prototype-create/evals/evals.json`：技能行为评估用例。

## 已知限制

- 当前 skill 主要通过文档约束 Agent 行为，尚未提供自动化脚本来强制检查 `EditLog.md` 或原型尺寸。
