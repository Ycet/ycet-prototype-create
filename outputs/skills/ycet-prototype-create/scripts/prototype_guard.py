#!/usr/bin/env python3
"""校验功能一静态交互边界，并保护功能三的只读输入。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


SNAPSHOT_SCHEMA_VERSION = 1
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

    args = parser.parse_args()
    prototype_dir = args.prototype_dir.resolve()
    try:
        if args.command == "static":
            return command_static(prototype_dir)
        if args.command == "snapshot":
            return command_snapshot(prototype_dir, args.output.resolve())
        return command_verify(prototype_dir, args.snapshot.resolve())
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
