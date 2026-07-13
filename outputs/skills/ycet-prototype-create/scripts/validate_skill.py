#!/usr/bin/env python3
"""验证 YCET Prototype Creator 的 Manifest、框架和关键文档契约。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRAMES_DIR = ROOT / "assets" / "frames"
MANIFEST_PATH = FRAMES_DIR / "manifest.json"


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def require_order(text: str, tokens: tuple[str, ...], label: str, failures: list[str]) -> None:
    """验证强门禁在文档中的先后顺序，避免只有关键词但执行顺序倒置。"""
    positions = [text.find(token) for token in tokens]
    if -1 in positions:
        return
    if positions != sorted(positions):
        fail(f"{label}顺序错误: {' → '.join(tokens)}", failures)


def main() -> int:
    failures: list[str] = []

    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - 校验器需要报告所有解析错误
        print(f"[FAIL] 无法读取 Manifest: {exc}")
        return 1

    if manifest.get("schemaVersion") != 1:
        fail("Manifest schemaVersion 必须为 1", failures)
    if manifest.get("screenQueryParameter") != "screen":
        fail("Manifest screenQueryParameter 必须为 screen", failures)
    if manifest.get("screenPathBase") != "prototype-root":
        fail("Manifest screenPathBase 必须为 prototype-root", failures)
    if manifest.get("frameProjectRootRelativePath") != "../../":
        fail("Manifest frameProjectRootRelativePath 必须为 ../../", failures)
    allowed_prefixes = manifest.get("allowedScreenPrefixes")
    if allowed_prefixes != ["pages/", "previews/", "runtime-pages/"]:
        fail("Manifest allowedScreenPrefixes 必须为 pages/、previews/ 与 runtime-pages/", failures)

    frames = manifest.get("frames")
    if not isinstance(frames, list) or not frames:
        fail("Manifest frames 必须是非空数组", failures)
        frames = []

    ids: set[str] = set()
    for frame in frames:
        frame_id = frame.get("id")
        if not frame_id or frame_id in ids:
            fail(f"框架 ID 缺失或重复: {frame_id}", failures)
            continue
        ids.add(frame_id)

        required = ["file", "platforms", "logicalViewport", "preview", "safeArea", "systemChrome", "defaultColumns"]
        for field in required:
            if field not in frame:
                fail(f"{frame_id} 缺少字段 {field}", failures)

        frame_path = FRAMES_DIR / str(frame.get("file", ""))
        if not frame_path.is_file():
            fail(f"{frame_id} 框架文件不存在: {frame_path.name}", failures)
            continue

        html = frame_path.read_text(encoding="utf-8")
        logical = frame.get("logicalViewport", {})
        checks = {
            f'data-ycet-frame-id="{frame_id}"': "HTML 框架 ID",
            f'data-logical-width="{logical.get("width")}"': "逻辑宽度",
            f'data-logical-height="{logical.get("height")}"': "逻辑高度",
            'const CHANNEL = "ycet-prototype"': "消息 channel",
            'const VERSION = 1': "消息版本",
            'message.type === "set-screen"': "set-screen 协议",
            "screen-changed": "screen-changed 协议",
            "event.source === inner.contentWindow": "内部消息来源校验",
            'const SCREEN_QUERY_PARAMETER = "screen"': "screen 查询参数常量",
            'const FRAME_PROJECT_ROOT_RELATIVE_PATH = "../../"': "项目根相对路径常量",
            'const ALLOWED_SCREEN_PREFIXES = ["pages/", "previews/", "runtime-pages/"]': "页面路径白名单",
            "new URL(FRAME_PROJECT_ROOT_RELATIVE_PATH, location.href)": "项目根解析",
            "normalizeNavigationTarget": "旧导航路径规范化",
            "new URL(screen, PROJECT_ROOT_URL)": "项目根页面解析",
            "scrollbar-width: none": "Firefox 滚动条隐藏规则",
            "-ms-overflow-style: none": "旧版 Edge 滚动条隐藏兜底",
            "::-webkit-scrollbar": "Chromium/WebKit 滚动条隐藏规则",
            'scrolling="no"': "iframe 滚动条兼容属性",
        }
        for token, label in checks.items():
            if token not in html:
                fail(f"{frame_id} 缺少{label}", failures)
        if "document.referrer" in html:
            fail(f"{frame_id} 仍依赖 document.referrer 解析页面路径", failures)

    routing = manifest.get("routing", {})
    for route, config in routing.items():
        default_id = config.get("defaultFrameId")
        if default_id not in ids:
            fail(f"路由 {route} 指向未知框架 {default_id}", failures)
        for host_id in config.get("hostOverrides", {}).values():
            if host_id not in ids:
                fail(f"路由 {route} 的宿主覆盖指向未知框架 {host_id}", failures)

    skill_md = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = re.match(r"^---\n(.*?)\n---", skill_md, re.DOTALL)
    if not frontmatter:
        fail("SKILL.md 缺少 YAML frontmatter", failures)
    else:
        keys = re.findall(r"^([A-Za-z0-9_-]+):", frontmatter.group(1), re.MULTILINE)
        if keys != ["name", "description"]:
            fail(f"SKILL.md frontmatter 只能包含 name 和 description，当前为 {keys}", failures)
    for token in (
        "即使同时提供 CSS 选择器或 HTML 片段，本规则也优先于功能二",
        "PNG、JPG、JPEG、WebP 等整页原型图片",
        "功能四每次启动时",
        "用户回复前不得继续",
        "按功能一相同的 Manifest 端口映射",
        "直接生成 `prototype/docs/Spec.md`",
        "不得调用 `brainstorming-solo` 或 `grill-me`",
        "静态高保真原型完成后必须停止",
        "禁止将图片解构、OCR 还原或重绘为页面元素",
        "生成 `prototype.html` 前必须",
    ):
        if token not in skill_md:
            fail(f"SKILL.md 缺少功能四前置、静态或交互门禁: {token}", failures)
    require_order(
        skill_md,
        (
            "用户提供非本 Skill 生成的完整 HTML 原型文件",
            "用户同时提供 CSS 选择器、HTML 片段和明确元素修改要求",
        ),
        "功能四与功能二直接路由优先级",
        failures,
    )

    function_one = (ROOT / "docs" / "function-1-static-prototype.md").read_text(encoding="utf-8")
    if "brainstorming-solo" not in function_one or "superpowers:brainstorming" in function_one:
        fail("功能一未正确切换到 brainstorming-solo", failures)
    for token in (
        "### 阶段一强制范围",
        "不得启动视觉伴侣",
        "阶段二待处理输入",
        'data-ycet-nav-target="pages/<file>.html"',
        "location.href",
        'type: "navigate"',
        "prototype_guard.py static",
    ):
        if token not in function_one:
            fail(f"功能一缺少阶段或静态交互强约束: {token}", failures)
    for url in ("https://open-design.ai/zh/plugins/systems/", "https://ui-ux-pro-max-skill.com/zh/#styles"):
        if url not in function_one:
            fail(f"功能一缺少特殊 UI Skill 链接: {url}", failures)

    shared_standards = (ROOT / "docs" / "shared-prototype-standards.md").read_text(encoding="utf-8")
    for token in (
        "## 路径与文件名契约",
        "frameProjectRootRelativePath",
        "allowedScreenPrefixes",
        "navigate.targetPage",
        "禁止依赖 `document.referrer`",
        "## 分阶段交互契约",
        "## 跨浏览器无可见滚动条契约",
        "scrollbar-width: none",
        "[data-ycet-scroll]",
        'scrolling="no"',
        "runtime-pages/",
        "### 功能四整页图片承载页",
        "### 功能四：静态重构与功能三交接",
        "禁止 OCR、切片、元素识别",
        "确认前不得生成 `runtime-pages/` 或 `prototype*.html`",
    ):
        if token not in shared_standards:
            fail(f"共享规范缺少路径契约: {token}", failures)

    function_three = (ROOT / "docs" / "function-3-interactive-demo.md").read_text(encoding="utf-8")
    for token in (
        'targetPage: "runtime-pages/detail--prototype.html"',
        "assets/frames/<frameFile>",
        "规范 pathname",
        "只读输入保护门禁",
        "SHA-256",
        "prototype_guard.py verify",
        "runtime-pages/<源文件stem>--<Demo文件stem>.html",
        "runtime-assets/frames/<Demo文件stem>--<frameFile>",
    ):
        if token not in function_three:
            fail(f"功能三缺少规范路径说明: {token}", failures)
    if "assets/frames/<frame-file>.html" in function_three:
        fail("功能三仍可能对 frameFile 重复追加 .html", failures)

    guard_script = ROOT / "scripts" / "prototype_guard.py"
    if not guard_script.is_file():
        fail("缺少静态交互与只读输入保护脚本 prototype_guard.py", failures)
    if not (ROOT / "scripts" / "test_prototype_guard.py").is_file():
        fail("缺少 prototype_guard 回归测试", failures)

    function_four = (ROOT / "docs" / "function-4-existing-prototype-edit.md").read_text(encoding="utf-8")
    for token in (
        "## 产品端口确认门禁",
        "当前产品原型是什么产品端口",
        "即使用户的初始描述",
        "不得开始读取或审计用户原型",
        "与功能一完全一致",
        "使用默认宿主",
        "## 非本 Skill HTML 原型编辑流程",
        "直接生成 `prototype/docs/Spec.md`",
        "本分支不得调用 `brainstorming-solo` 或 `grill-me`",
        "源视觉证据",
        "静态高保真原型完成后必须停止当前任务",
        "任务开始时提出“增加交互”",
        "只有用户明确确认生成可交互原型后",
        "## 图片原型静态承载与交互门禁",
        "绝对不得将图片 OCR、切片、解构、识别或重绘",
        "必须先完成这两类静态文件",
        "单独询问是否确认生成 `prototype.html`",
        "运行时副本必须继续以完整原图为视觉基底",
        "SHA-256 未变化",
        "| iOS、iPhone | `iphone-15-pro` |",
        "| Android | `android-pixel` |",
        "| iPad | `ipad-pro` |",
        "| 网页、网站 | `browser-chrome` |",
        "| 桌面端应用、Windows、macOS | `macbook` |",
        "| 微信小程序 | 默认 `iphone-15-pro`；用户明确指定 Android 宿主时使用 `android-pixel` |",
        "CSS `url()` / `@import`",
        "模块 import",
        "pages/source-images/",
    ):
        if token not in function_four:
            fail(f"功能四缺少端口确认门禁或迁移路径规则: {token}", failures)

    html_section = function_four.split("## 非本 Skill HTML 原型编辑流程", 1)[-1].split(
        "## 图片原型静态承载与交互门禁", 1
    )[0]
    require_order(
        html_section,
        (
            "直接生成 `prototype/docs/Spec.md`",
            "生成后展示 Spec 摘要并请求用户确认",
            "Spec 确认后进入功能一阶段二",
            "静态高保真原型完成后必须停止当前任务",
            "只有用户明确确认生成可交互原型后",
        ),
        "功能四 HTML 的 Spec、静态与功能三门禁",
        failures,
    )
    image_section = function_four.split("## 图片原型静态承载与交互门禁", 1)[-1].split("## 迁移规则", 1)[0]
    require_order(
        image_section,
        (
            "为每张图片生成对应的原图承载型 `pages/**/*.html`",
            "静态文件完成后停止任务",
            "用户明确确认后才读取并执行功能三",
        ),
        "功能四图片静态产物与 prototype.html 门禁",
        failures,
    )

    evals_path = ROOT / "evals" / "evals.json"
    try:
        evals = json.loads(evals_path.read_text(encoding="utf-8"))
        if len(evals.get("evals", [])) < 8:
            fail("评估用例少于 8 个", failures)
    except Exception as exc:  # noqa: BLE001
        fail(f"评估 JSON 无效: {exc}", failures)

    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        print(f"\n共 {len(failures)} 个问题。")
        return 1

    print(f"[OK] 验证通过：{len(frames)} 个框架、{len(routing)} 条端口路由。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
