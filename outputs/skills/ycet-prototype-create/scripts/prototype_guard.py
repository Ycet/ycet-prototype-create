#!/usr/bin/env python3
"""校验静态交互边界、功能三只读输入和图片原型运行时契约。"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


SNAPSHOT_SCHEMA_VERSION = 1
MOBILE_FILE_PATTERN = re.compile(r"prototype-mobile(?:-v(?P<version>\d+))?\.html")
MOBILE_REGISTRY_PATTERN = re.compile(
    r'<script id="ycet-mobile-pages" type="application/json">(.*?)</script>',
    re.DOTALL,
)
SAFE_NAV_TARGET = re.compile(r"^pages/[a-z0-9]+(?:-[a-z0-9]+)*\.html$")
SCRIPT_NAVIGATION_PATTERNS = (
    (re.compile(r"\b(?:(?:window|document)\s*\.\s*)?location\s*\.\s*href\b"), "location.href"),
    (re.compile(r"\b(?:(?:window|document)\s*\.\s*)?location\s*\.\s*(?:assign|replace)\s*\("), "Location 跳转"),
    (re.compile(r"\b(?:(?:window|document)\s*\.\s*)?location\s*=(?!=)"), "Location 赋值跳转"),
    (re.compile(r"\bwindow\s*\.\s*open\s*\("), "window.open"),
    (re.compile(r"\bhistory\s*\.\s*(?:pushState|replaceState|go|back|forward)\s*\("), "History 跳转"),
    (re.compile(r"\bwindow\s*\.\s*top\b|\btop\s*\.\s*location\b|\bparent\s*\.\s*location\b"), "顶层窗口跳转"),
    (re.compile(r"\brouter\s*\.\s*(?:push|replace)\s*\(|\bnavigate\s*\("), "路由器跳转"),
    (re.compile(r"(?:['\"]?type['\"]?)\s*:\s*['\"]navigate['\"]"), "navigate 消息"),
)


class StaticPageParser(HTMLParser):
    """只提取可能产生页面离开的 HTML 与脚本，不改写源文件。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.violations: list[str] = []
        self.nav_targets: list[tuple[int, str]] = []
        self.script_sources: list[tuple[int, str]] = []
        self._script_line: int | None = None
        self._script_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_tag(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_tag(tag, attrs)

    def _handle_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line, _column = self.getpos()
        values = {name.lower(): value for name, value in attrs}
        lowered_tag = tag.lower()

        if lowered_tag == "a" and "href" in values:
            href = (values.get("href") or "").strip()
            if not href.startswith("#"):
                self.violations.append(f"第 {line} 行：静态页 `<a href>` 会离开当前文档（{href!r}）")

        if lowered_tag == "form" and "action" in values:
            action = (values.get("action") or "").strip()
            if not action.startswith("#"):
                self.violations.append(f"第 {line} 行：静态页 form action 会离开当前文档（{action!r}）")

        if "formaction" in values:
            form_action = (values.get("formaction") or "").strip()
            if not form_action.startswith("#"):
                self.violations.append(f"第 {line} 行：静态页 formaction 会离开当前文档（{form_action!r}）")

        if lowered_tag == "base" and "href" in values:
            self.violations.append(f"第 {line} 行：静态页禁止通过 `<base href>` 改变导航基准")

        if lowered_tag == "meta" and (values.get("http-equiv") or "").strip().lower() == "refresh":
            self.violations.append(f"第 {line} 行：静态页禁止 meta refresh")

        target = values.get("data-ycet-nav-target")
        if target is not None:
            self.nav_targets.append((line, target.strip()))

        for name, value in values.items():
            if name.startswith("on") and value:
                self._audit_script(value, line, f"内联事件 {name}")

        if lowered_tag == "script":
            source = (values.get("src") or "").strip()
            if source:
                self.script_sources.append((line, source))
            else:
                self._script_line = line
                self._script_chunks = []

    def handle_data(self, data: str) -> None:
        if self._script_line is not None:
            self._script_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._script_line is not None:
            script = "".join(self._script_chunks)
            self._audit_script(script, self._script_line, "内联脚本")
            self._script_line = None
            self._script_chunks = []

    def _audit_script(self, script: str, line: int, source: str) -> None:
        for pattern, label in SCRIPT_NAVIGATION_PATTERNS:
            if pattern.search(script):
                self.violations.append(f"第 {line} 行：{source} 包含主动跨页实现（{label}）")


class ImageCarrierParser(HTMLParser):
    """提取功能四图片承载页的资源与跨页热区，不改写页面。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.is_image_prototype = False
        self.images: list[tuple[int, str]] = []
        self.nav_hotspots: list[tuple[int, set[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_tag(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_tag(tag, attrs)

    def _handle_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line, _column = self.getpos()
        values = {name.lower(): value for name, value in attrs}
        if (values.get("data-ycet-image-prototype") or "").strip().lower() == "true":
            self.is_image_prototype = True

        if tag.lower() == "img":
            source = (values.get("src") or "").strip()
            self.images.append((line, source))

        if "data-ycet-nav-target" in values:
            classes = set((values.get("class") or "").split())
            self.nav_hotspots.append((line, classes))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_files(prototype_dir: Path) -> list[Path]:
    index_path = prototype_dir / "index.html"
    pages_dir = prototype_dir / "pages"
    if not index_path.is_file():
        raise ValueError(f"受保护入口不存在：{index_path}")
    if not pages_dir.is_dir():
        raise ValueError(f"静态页面目录不存在：{pages_dir}")
    pages = sorted(path for path in pages_dir.rglob("*.html") if path.is_file())
    if not pages:
        raise ValueError(f"静态页面目录不含 HTML：{pages_dir}")
    return [index_path, *pages]


def build_snapshot(prototype_dir: Path) -> dict[str, object]:
    files: dict[str, dict[str, object]] = {}
    for path in protected_files(prototype_dir):
        relative = path.relative_to(prototype_dir).as_posix()
        files[relative] = {"sha256": sha256_file(path), "size": path.stat().st_size}
    return {"schemaVersion": SNAPSHOT_SCHEMA_VERSION, "files": files}


def command_snapshot(prototype_dir: Path, output: Path) -> int:
    snapshot = build_snapshot(prototype_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] 已记录 {len(snapshot['files'])} 个受保护文件：{output}")
    return 0


def command_verify(prototype_dir: Path, snapshot_path: Path) -> int:
    try:
        expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - 必须把快照解析错误完整报告给调用者
        print(f"[FAIL] 无法读取输入快照：{exc}")
        return 1

    if expected.get("schemaVersion") != SNAPSHOT_SCHEMA_VERSION or not isinstance(expected.get("files"), dict):
        print("[FAIL] 输入快照结构无效")
        return 1

    current = build_snapshot(prototype_dir)
    expected_files = expected["files"]
    current_files = current["files"]
    failures: list[str] = []

    for relative in sorted(set(expected_files) - set(current_files)):
        failures.append(f"文件被删除或重命名：{relative}")
    for relative in sorted(set(current_files) - set(expected_files)):
        failures.append(f"受保护目录新增 HTML：{relative}")
    for relative in sorted(set(expected_files) & set(current_files)):
        if expected_files[relative] != current_files[relative]:
            failures.append(f"文件字节发生变化：{relative}")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    print(f"[OK] 受保护输入未变化：{len(current_files)} 个文件")
    return 0


def resolve_local_script(page_path: Path, prototype_dir: Path, source: str) -> Path | None:
    parts = urlsplit(source)
    if parts.scheme or parts.netloc or source.startswith("/"):
        return None
    decoded = unquote(parts.path).replace("\\", "/")
    if not decoded:
        return None
    candidate = (page_path.parent / decoded).resolve()
    try:
        candidate.relative_to(prototype_dir.resolve())
    except ValueError:
        return None
    return candidate


def resolve_local_asset(page_path: Path, prototype_dir: Path, source: str) -> Path | None:
    """解析页面中的本地资源，并拒绝跳出原型目录的路径。"""
    parts = urlsplit(source)
    if parts.scheme or parts.netloc or source.startswith("/"):
        return None
    decoded = unquote(parts.path).replace("\\", "/")
    if not decoded:
        return None
    candidate = (page_path.parent / decoded).resolve()
    try:
        candidate.relative_to(prototype_dir.resolve())
    except ValueError:
        return None
    return candidate


def audit_static_page(page_path: Path, prototype_dir: Path, known_pages: set[str]) -> list[str]:
    parser = StaticPageParser()
    parser.feed(page_path.read_text(encoding="utf-8"))
    failures = list(parser.violations)

    for line, target in parser.nav_targets:
        parts = urlsplit(target)
        decoded_path = unquote(parts.path)
        if parts.scheme or parts.netloc or not SAFE_NAV_TARGET.fullmatch(decoded_path):
            failures.append(f"第 {line} 行：data-ycet-nav-target 不是安全的 pages/*.html 规范路径（{target!r}）")
        elif decoded_path not in known_pages:
            failures.append(f"第 {line} 行：data-ycet-nav-target 未指向已存在页面（{target!r}）")

    for line, source in parser.script_sources:
        script_path = resolve_local_script(page_path, prototype_dir, source)
        if script_path is None:
            failures.append(f"第 {line} 行：无法安全审计脚本 src（{source!r}）")
            continue
        if not script_path.is_file():
            failures.append(f"第 {line} 行：脚本 src 不存在（{source!r}）")
            continue
        script = script_path.read_text(encoding="utf-8")
        for pattern, label in SCRIPT_NAVIGATION_PATTERNS:
            if pattern.search(script):
                failures.append(f"第 {line} 行：外部脚本 {source!r} 包含主动跨页实现（{label}）")

    return failures


def command_static(prototype_dir: Path) -> int:
    pages_dir = prototype_dir / "pages"
    previews_dir = prototype_dir / "previews"
    page_paths = sorted(path for path in pages_dir.rglob("*.html") if path.is_file())
    preview_paths = sorted(path for path in previews_dir.rglob("*.html") if path.is_file()) if previews_dir.is_dir() else []
    if not page_paths:
        print(f"[FAIL] 未找到静态页面：{pages_dir}")
        return 1

    known_pages = {path.relative_to(prototype_dir).as_posix() for path in page_paths}
    failures: list[str] = []
    for path in [*page_paths, *preview_paths]:
        for failure in audit_static_page(path, prototype_dir, known_pages):
            failures.append(f"{path.relative_to(prototype_dir).as_posix()}：{failure}")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print(f"\n共 {len(failures)} 个静态交互边界问题。")
        return 1

    print(f"[OK] 静态交互边界通过：{len(page_paths)} 个页面，{len(preview_paths)} 个预览。")
    return 0


def is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def audit_image_carrier(page_path: Path, prototype_dir: Path, require_runtime: bool) -> tuple[bool, list[str]]:
    """检查图片承载页资源路径和运行时热区的可见性契约。"""
    text = page_path.read_text(encoding="utf-8")
    parser = ImageCarrierParser()
    parser.feed(text)
    if not parser.is_image_prototype:
        return False, []

    relative = page_path.relative_to(prototype_dir).as_posix()
    failures: list[str] = []
    images_dir = prototype_dir / "assets" / "images"
    if "source-images/" in text:
        failures.append(f"{relative}：图片承载页不得引用 pages/source-images/")
    if not parser.images:
        failures.append(f"{relative}：图片承载页缺少 <img>")

    for line, source in parser.images:
        resolved = resolve_local_asset(page_path, prototype_dir, source)
        if resolved is None:
            failures.append(f"{relative} 第 {line} 行：图片 src 不是安全的项目内相对路径（{source!r}）")
        elif not is_within(resolved, images_dir):
            failures.append(f"{relative} 第 {line} 行：图片 src 必须解析到 assets/images/（{source!r}）")
        elif not resolved.is_file():
            failures.append(f"{relative} 第 {line} 行：图片资源不存在（{source!r}）")

    if not require_runtime and parser.nav_hotspots:
        for line, _classes in parser.nav_hotspots:
            failures.append(f"{relative} 第 {line} 行：静态图片承载页不得包含跨页热区")

    if require_runtime and parser.nav_hotspots:
        for line, classes in parser.nav_hotspots:
            if "ycet-image-hotspot" not in classes:
                failures.append(f"{relative} 第 {line} 行：图片跨页热区必须使用 ycet-image-hotspot 类")

        default_style = re.compile(
            r"\.ycet-image-hotspot\s*\{(?=[^}]*outline\s*:\s*1px\s+dashed\s+transparent\s*)(?=[^}]*background\s*:\s*transparent\s*;)(?=[^}]*pointer-events\s*:\s*auto\s*;)[^}]*\}",
            re.DOTALL,
        )
        hover_style = re.compile(
            r"\.ycet-image-hotspot:hover\s*,\s*\.ycet-image-hotspot:focus-visible\s*\{[^}]*outline-color\s*:\s*rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*0?\.\d+\s*\)\s*;",
            re.DOTALL,
        )
        if not default_style.search(text):
            failures.append(f"{relative}：图片热区缺少默认透明虚线轮廓、透明背景或 pointer-events: auto")
        if not hover_style.search(text):
            failures.append(f"{relative}：图片热区缺少 hover/focus-visible 半透明虚线轮廓")

    return True, failures


def command_image(prototype_dir: Path, require_runtime: bool) -> int:
    pages_dir = prototype_dir / "pages"
    if not pages_dir.is_dir():
        print(f"[FAIL] 静态页面目录不存在：{pages_dir}")
        return 1

    static_paths = sorted(path for path in pages_dir.rglob("*.html") if path.is_file())
    static_carriers = 0
    failures: list[str] = []
    for path in static_paths:
        is_carrier, issues = audit_image_carrier(path, prototype_dir, require_runtime=False)
        if is_carrier:
            static_carriers += 1
            failures.extend(issues)

    if not static_carriers:
        failures.append("未找到带 data-ycet-image-prototype=\"true\" 的图片静态承载页")

    runtime_carriers = 0
    if require_runtime:
        runtime_dir = prototype_dir / "runtime-pages"
        if not runtime_dir.is_dir():
            failures.append(f"运行时页面目录不存在：{runtime_dir}")
        else:
            for path in sorted(path for path in runtime_dir.rglob("*.html") if path.is_file()):
                is_carrier, issues = audit_image_carrier(path, prototype_dir, require_runtime=True)
                if is_carrier:
                    runtime_carriers += 1
                    failures.extend(issues)
            if not runtime_carriers:
                failures.append("未找到带 data-ycet-image-prototype=\"true\" 的图片运行时副本")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    print(f"[OK] 图片原型资源与热区通过：{static_carriers} 个静态页，{runtime_carriers} 个运行时页。")
    return 0


def latest_mobile_file(prototype_dir: Path) -> Path:
    candidates: list[tuple[int, Path]] = []
    for path in prototype_dir.iterdir():
        if not path.is_file():
            continue
        match = MOBILE_FILE_PATTERN.fullmatch(path.name)
        if match:
            candidates.append((int(match.group("version") or 1), path))
    if not candidates:
        raise ValueError(f"未找到 prototype-mobile*.html：{prototype_dir}")
    return max(candidates, key=lambda item: item[0])[1]


def command_mobile(prototype_dir: Path, mobile_file: Path | None) -> int:
    """检查功能五输出的自包含注册表、目标白名单和外部依赖。"""
    path = latest_mobile_file(prototype_dir) if mobile_file is None else mobile_file
    if not path.is_absolute():
        path = prototype_dir / path
    path = path.resolve()
    if not is_within(path, prototype_dir) or not MOBILE_FILE_PATTERN.fullmatch(path.name):
        print(f"[FAIL] 手机版文件必须是 prototype/ 下的 prototype-mobile*.html：{path}")
        return 1
    if not path.is_file():
        print(f"[FAIL] 手机版文件不存在：{path}")
        return 1

    document = path.read_text(encoding="utf-8")
    failures: list[str] = []
    for token in (
        'data-ycet-mobile-prototype="true"',
        'id="mobile-screen"',
        'id="menu-button"',
        'id="navigation-drawer"',
    ):
        if token not in document:
            failures.append(f"移动端外壳缺少标记：{token}")
    if re.search(r"https?://|file:///", document, re.IGNORECASE):
        failures.append("手机版外层仍含远程或绝对文件依赖")

    match = MOBILE_REGISTRY_PATTERN.search(document)
    if not match:
        failures.append("缺少 ycet-mobile-pages 页面注册表")
        registry: list[object] = []
    else:
        try:
            parsed = json.loads(match.group(1))
            registry = parsed if isinstance(parsed, list) else []
            if not isinstance(parsed, list):
                failures.append("ycet-mobile-pages 页面注册表必须是数组")
        except json.JSONDecodeError as exc:
            failures.append(f"ycet-mobile-pages 页面注册表 JSON 无效：{exc}")
            registry = []

    if not registry:
        failures.append("页面注册表为空")

    ids: set[str] = set()
    aliases: set[str] = set()
    initial_count = 0
    valid_pages: list[dict[str, object]] = []
    for index, raw_page in enumerate(registry):
        if not isinstance(raw_page, dict):
            failures.append(f"页面注册表第 {index + 1} 项不是对象")
            continue
        page = raw_page
        valid_pages.append(page)
        page_id = page.get("id")
        if not isinstance(page_id, str) or not page_id or page_id in ids:
            failures.append(f"页面 ID 缺失或重复：{page_id!r}")
        else:
            ids.add(page_id)
        if page.get("initial") is True:
            initial_count += 1
        if page.get("order") != index:
            failures.append(f"页面 {page_id!r} 的 order 与注册表顺序不一致")
        for field, prefix in (("runtimePath", "runtime-pages/"), ("sourcePath", "pages/")):
            value = page.get(field)
            try:
                if not isinstance(value, str):
                    raise ValueError
                parts = urlsplit(value)
                decoded = unquote(parts.path)
                pure = Path(decoded.replace("/", os.sep))
                if parts.scheme or parts.netloc or not decoded.startswith(prefix) or ".." in pure.parts:
                    raise ValueError
                aliases.add(decoded)
            except ValueError:
                failures.append(f"页面 {page_id!r} 的 {field} 不安全：{value!r}")

        encoded = page.get("srcdocBase64")
        try:
            if not isinstance(encoded, str):
                raise ValueError
            srcdoc = base64.b64decode(encoded, validate=True).decode("utf-8")
        except (ValueError, UnicodeError):
            failures.append(f"页面 {page_id!r} 的 srcdocBase64 无效")
            continue
        if re.search(r"https?://|file:///", srcdoc, re.IGNORECASE):
            failures.append(f"页面 {page_id!r} 的 srcdoc 仍含远程或绝对文件依赖")
        if re.search(
            r"\b(?:src|poster|data)\s*=\s*(['\"])(?!data:|about:)[^'\"]+\1",
            srcdoc,
            re.IGNORECASE,
        ):
            failures.append(f"页面 {page_id!r} 的 srcdoc 仍含未内联资源属性")
        if re.search(r"<link\b[^>]*\bhref\s*=\s*(['\"])(?!data:)[^'\"]+\1", srcdoc, re.IGNORECASE):
            failures.append(f"页面 {page_id!r} 的 srcdoc 仍含未内联 link")

    if initial_count != 1:
        failures.append(f"页面注册表必须有且仅有一个初始页，当前为 {initial_count}")

    for page in valid_pages:
        page_id = page.get("id")
        targets = page.get("targets", [])
        if not isinstance(targets, list):
            failures.append(f"页面 {page_id!r} 的 targets 必须是数组")
            continue
        for target in targets:
            if not isinstance(target, str):
                failures.append(f"页面 {page_id!r} 存在非字符串目标")
                continue
            parts = urlsplit(target)
            pathname = unquote(parts.path)
            if parts.scheme or parts.netloc or target.startswith("/") or ".." in Path(pathname.replace("/", os.sep)).parts:
                failures.append(f"页面 {page_id!r} 存在不安全目标：{target!r}")
            elif pathname not in aliases:
                failures.append(f"页面 {page_id!r} 存在未登记目标：{target!r}")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    print(f"[OK] 手机版单文件通过：{path.name}，{len(valid_pages)} 个页面。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    static_parser = subparsers.add_parser("static", help="检查功能一页面没有主动跨页实现")
    static_parser.add_argument("--prototype-dir", required=True, type=Path)

    snapshot_parser = subparsers.add_parser("snapshot", help="记录功能三只读输入的 SHA-256")
    snapshot_parser.add_argument("--prototype-dir", required=True, type=Path)
    snapshot_parser.add_argument("--output", required=True, type=Path)

    verify_parser = subparsers.add_parser("verify", help="验证功能三只读输入未发生变化")
    verify_parser.add_argument("--prototype-dir", required=True, type=Path)
    verify_parser.add_argument("--snapshot", required=True, type=Path)

    image_parser = subparsers.add_parser("image", help="检查功能四图片资源路径与运行时热区")
    image_parser.add_argument("--prototype-dir", required=True, type=Path)
    image_parser.add_argument("--require-runtime", action="store_true", help="要求校验图片运行时副本与热区反馈")

    mobile_parser = subparsers.add_parser("mobile", help="检查功能五离线单文件结构与依赖")
    mobile_parser.add_argument("--prototype-dir", required=True, type=Path)
    mobile_parser.add_argument("--mobile-file", type=Path, help="待校验文件；省略时选择最新版本")

    args = parser.parse_args()
    prototype_dir = args.prototype_dir.resolve()
    try:
        if args.command == "static":
            return command_static(prototype_dir)
        if args.command == "snapshot":
            return command_snapshot(prototype_dir, args.output.resolve())
        if args.command == "image":
            return command_image(prototype_dir, args.require_runtime)
        if args.command == "mobile":
            return command_mobile(prototype_dir, args.mobile_file)
        return command_verify(prototype_dir, args.snapshot.resolve())
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
