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
    for token in (
        "功能一的结构化 PRD 调用 `grill-me` 时",
        "只可追问产品交互逻辑、各页面元素、业务规则、边界条件和异常处理场景",
        "主流程可单独直接询问一次",
        "无损位图分割为固定区与可滚动区",
        "静态 `pages/**/*.html` 与功能三 `runtime-pages/**/*.html` 均从该目录",
        "鼠标悬停或键盘聚焦时必须显示半透明虚线轮廓",
    ):
        if token not in skill_md:
            fail(f"SKILL.md 缺少结构化 PRD 或图片固定区域强约束: {token}", failures)
    for token in (
        "手机预览、移动端预览、离线单文件、单 HTML 文件或 `prototype-mobile.html`",
        "| E | 生成可单独发送到手机的离线单文件原型 |",
        "功能五复用功能三的运行时页面和 `ycet-prototype` 消息协议",
        "打包阶段只允许新增一个递增命名的 `prototype-mobile*.html`",
        "部分存在、目标悬空或来源冲突必须停止",
    ):
        if token not in skill_md:
            fail(f"SKILL.md 缺少功能五路由或只读门禁: {token}", failures)
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
        "### 结构化 PRD 的 `grill-me` 专用边界",
        "仅提问或追问产品交互逻辑、各页面元素、业务规则、边界条件和异常处理场景",
        "不得重新询问产品背景、定位、目标用户、使用场景、既有页面清单、页面名称或已确认功能目标",
        "不能交给 `grill-me` 扩展为其他问题",
    ):
        if token not in function_one:
            fail(f"功能一缺少阶段或静态交互强约束: {token}", failures)
    require_order(
        function_one,
        (
            "### 结构化 PRD 的 `grill-me` 专用边界",
            "### 需求审计与提问",
            "### Spec 生成门槛",
        ),
        "功能一结构化 PRD 复核与 Spec 门禁",
        failures,
    )
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
        "除用户确认的固定区域位图分割外，禁止 OCR、元素识别",
        "固定区域承载页只能由根容器、固定顶部/底部 `<img>`、唯一的 `data-ycet-scroll`",
        "新项目不得创建或引用 `pages/source-images/`",
        '`data-ycet-image-prototype="true"`',
        "`hover` 和 `focus-visible` 必须显示半透明虚线轮廓",
        "确认前不得生成 `runtime-pages/` 或 `prototype*.html`",
        "### 功能五：移动端离线单文件",
        "每个运行时页面转为资源完全内联的独立 `srcdoc`",
        "不更新 EditLog",
        "prototype-mobile.html",
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
        '`data-ycet-image-prototype="true"` 标记',
        "prototype_guard.py image",
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
    for token in ("def command_image", "ycet-image-hotspot", "--require-runtime", "def command_mobile"):
        if token not in guard_script.read_text(encoding="utf-8"):
            fail(f"图片原型守卫缺少资源或热区校验: {token}", failures)

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
        "### 固定区域位图分割（仅在用户明确需求时）",
        "### 图片运行时热区",
        "只有用户明确要求“顶部区域固定”“底部区域固定”或等效的固定区域效果时",
        "保留未修改的完整原图，并仅按用户确认的水平边界在",
        "不得 OCR、元素识别、语义切分、逐元素导出",
        "`prototype/assets/images/`",
        '`data-ycet-image-prototype="true"`',
        "ycet-image-hotspot",
        "outline: 1px dashed transparent",
        "outline-color: rgba(37, 99, 235, 0.72)",
        "新项目不得创建或引用 `pages/source-images/`",
        "必须先完成这两类静态文件",
        "单独询问是否确认生成 `prototype.html`",
        "运行时副本必须继续以完整原图或已确认片段组合为视觉基底",
        "SHA-256 未变化",
        "| iOS、iPhone | `iphone-15-pro` |",
        "| Android | `android-pixel` |",
        "| iPad | `ipad-pro` |",
        "| 网页、网站 | `browser-chrome` |",
        "| 桌面端应用、Windows、macOS | `macbook` |",
        "| 微信小程序 | 默认 `iphone-15-pro`；用户明确指定 Android 宿主时使用 `android-pixel` |",
        "CSS `url()` / `@import`",
        "模块 import",
        "scripts/prototype_guard.py image --prototype-dir <prototype目录> --require-runtime",
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
    fixed_image_section = image_section.split("### 固定区域位图分割（仅在用户明确需求时）", 1)[-1].split(
        "### 图片处理流程", 1
    )[0]
    require_order(
        fixed_image_section,
        (
            "先向用户确认每张图片的固定区域",
            "保留未修改的完整原图",
            "承载页的根容器按 `frame-config.json.logicalViewport` 建立局部坐标",
            "验收时核对完整原图仍保留",
        ),
        "功能四图片固定区域确认、位图分割与验收",
        failures,
    )
    require_order(
        image_section,
        (
            "将原始整页图片保存到 `prototype/assets/images/`",
            "为每张图片生成带 `data-ycet-image-prototype=\"true\"` 的原图承载型",
            "静态文件完成后停止任务",
            "用户明确确认后才读取并执行功能三",
        ),
        "功能四图片静态产物与 prototype.html 门禁",
        failures,
    )

    function_five_path = ROOT / "docs" / "function-5-mobile-single-file.md"
    if not function_five_path.is_file():
        fail("缺少功能五流程文档 function-5-mobile-single-file.md", failures)
    else:
        function_five = function_five_path.read_text(encoding="utf-8")
        for token in (
            "## 输入审计与确认门禁",
            "部分存在、目标悬空、多个版本或来源冲突",
            "用户确认前不得创建 `runtime-pages/`",
            "build_mobile_prototype.py --prototype-dir",
            "一个无边框 `iframe srcdoc`",
            "prototype-mobile-v2.html",
            "打包阶段只新增一个手机版文件",
            "prototype_guard.py mobile",
            "桌面移动视口不能冒充 Safari iOS",
            "不得修改 EditLog",
        ):
            if token not in function_five:
                fail(f"功能五缺少状态、打包或验收门禁: {token}", failures)
        require_order(
            function_five,
            (
                "## 输入审计与确认门禁",
                "## 完全缺失时的运行时准备",
                "## 离线打包",
                "## 验证",
                "## 完成标准",
            ),
            "功能五审计、确认、打包与验收",
            failures,
        )

    builder_script = ROOT / "scripts" / "build_mobile_prototype.py"
    builder_test = ROOT / "scripts" / "test_build_mobile_prototype.py"
    browser_test = ROOT / "scripts" / "test_mobile_prototype_runtime.py"
    if not builder_script.is_file():
        fail("缺少功能五确定性打包器 build_mobile_prototype.py", failures)
    else:
        builder_text = builder_script.read_text(encoding="utf-8")
        for token in ("def input_snapshot", "class ResourceBundler", "def build_shell", "os.replace"):
            if token not in builder_text:
                fail(f"功能五打包器缺少只读、资源或原子输出能力: {token}", failures)
    if not builder_test.is_file():
        fail("缺少功能五打包器回归测试", failures)
    if not browser_test.is_file():
        fail("缺少功能五移动视口浏览器测试", failures)

    editlog_rules = (ROOT / "docs" / "shared-editlog-rules.md").read_text(encoding="utf-8")
    for token in ("功能五是唯一例外", "打包阶段只新增一个手机版文件", "| 功能五 | 不写 EditLog"):
        if token not in editlog_rules:
            fail(f"EditLog 规则缺少功能五只写例外: {token}", failures)

    openai_yaml = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    if "离线手机预览单文件" not in openai_yaml:
        fail("agents/openai.yaml 未体现功能五手机单文件能力", failures)

    evals_path = ROOT / "evals" / "evals.json"
    try:
        evals = json.loads(evals_path.read_text(encoding="utf-8"))
        eval_items = evals.get("evals", [])
        if len(eval_items) < 14:
            fail("评估用例少于 14 个，未完整覆盖功能一至五", failures)
        if not any("prototype-mobile" in str(item.get("prompt", "")) for item in eval_items):
            fail("评估用例缺少功能五 prototype-mobile 场景", failures)
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
