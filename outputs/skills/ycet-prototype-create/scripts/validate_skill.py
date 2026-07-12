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
    if allowed_prefixes != ["pages/", "previews/"]:
        fail("Manifest allowedScreenPrefixes 必须为 pages/ 与 previews/", failures)

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
            'const ALLOWED_SCREEN_PREFIXES = ["pages/", "previews/"]': "页面路径白名单",
            "new URL(FRAME_PROJECT_ROOT_RELATIVE_PATH, location.href)": "项目根解析",
            "normalizeNavigationTarget": "旧导航路径规范化",
            "new URL(screen, PROJECT_ROOT_URL)": "项目根页面解析",
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

    function_one = (ROOT / "docs" / "function-1-static-prototype.md").read_text(encoding="utf-8")
    if "brainstorming-solo" not in function_one or "superpowers:brainstorming" in function_one:
        fail("功能一未正确切换到 brainstorming-solo", failures)
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
    ):
        if token not in shared_standards:
            fail(f"共享规范缺少路径契约: {token}", failures)

    function_three = (ROOT / "docs" / "function-3-interactive-demo.md").read_text(encoding="utf-8")
    for token in ('targetPage: "pages/home.html"', "assets/frames/<frameFile>", "规范 pathname"):
        if token not in function_three:
            fail(f"功能三缺少规范路径说明: {token}", failures)
    if "assets/frames/<frame-file>.html" in function_three:
        fail("功能三仍可能对 frameFile 重复追加 .html", failures)

    function_four = (ROOT / "docs" / "function-4-existing-prototype-edit.md").read_text(encoding="utf-8")
    for token in ("CSS `url()` / `@import`", "模块 import", "pages/source-images/"):
        if token not in function_four:
            fail(f"功能四缺少迁移路径规则: {token}", failures)

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
