#!/usr/bin/env python3
"""将已准备好的运行时页面打包为离线 prototype-mobile*.html。"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import html
import json
import mimetypes
import os
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


MOBILE_NAME = re.compile(r"prototype-mobile(?:-v(?P<version>\d+))?\.html")
RUNTIME_VERSION = re.compile(r"^(?P<source>.+)--(?P<demo>prototype(?:-v\d+)?)\.html$")
REMOTE_SCHEMES = {"http", "https"}
FORBIDDEN_SCHEMES = {"file", "javascript", "blob"}
TEXT_MIME_TYPES = {
    ".css": "text/css",
    ".csv": "text/csv",
    ".html": "text/html",
    ".js": "text/javascript",
    ".json": "application/json",
    ".mjs": "text/javascript",
    ".svg": "image/svg+xml",
    ".txt": "text/plain",
    ".xml": "application/xml",
}
MIME_OVERRIDES = {
    ".avif": "image/avif",
    ".ico": "image/x-icon",
    ".wasm": "application/wasm",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}
CSS_IMPORT = re.compile(
    r"@import\s+(?:url\(\s*)?(?P<quote>['\"]?)(?P<path>[^'\"\)\s;]+)(?P=quote)\s*\)?(?P<media>[^;]*);",
    re.IGNORECASE,
)
CSS_URL = re.compile(r"url\(\s*(?P<quote>['\"]?)(?P<path>[^'\"\)]+)(?P=quote)\s*\)", re.IGNORECASE)
MODULE_SPECIFIER = re.compile(
    r"(?P<prefix>\b(?:import|export)\s+(?:(?![;\n]).)*?\bfrom\s*|\bimport\s*)"
    r"(?P<quote>['\"])(?P<path>[^'\"]+)(?P=quote)",
)
DYNAMIC_IMPORT = re.compile(
    r"(?P<prefix>\bimport\s*\(\s*)(?P<quote>['\"])(?P<path>[^'\"]+)(?P=quote)(?P<suffix>\s*\))"
)
FETCH_LITERAL = re.compile(
    r"(?P<prefix>\bfetch\s*\(\s*)(?P<quote>['\"])(?P<path>[^'\"]+)(?P=quote)"
)
NEW_URL_LITERAL = re.compile(
    r"(?P<prefix>\bnew\s+URL\s*\(\s*)(?P<quote>['\"])(?P<path>[^'\"]+)(?P=quote)"
    r"(?P<suffix>\s*,\s*import\.meta\.url\s*\))"
)
NETWORK_SCRIPT_PATTERNS = (
    (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
    (re.compile(r"\b(?:WebSocket|EventSource)\s*\("), "持续网络连接"),
    (re.compile(r"\bnavigator\.sendBeacon\s*\("), "sendBeacon"),
    (re.compile(r"\bserviceWorker\.register\s*\("), "Service Worker"),
)


class BuildError(RuntimeError):
    """表示无法在不降级的前提下完成单文件打包。"""


@dataclass
class PageSpec:
    page_id: str
    label: str
    source_path: str
    runtime_path: str
    runtime_file: Path
    initial: bool = False
    targets: tuple[str, ...] = ()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_snapshot(prototype_dir: Path, excluded_paths: tuple[Path, ...] = ()) -> dict[str, str]:
    """记录除本次目标和临时文件外的全部输入，历史手机版本也受保护。"""
    excluded = {path.resolve() for path in excluded_paths}
    result: dict[str, str] = {}
    for path in sorted(prototype_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.resolve() in excluded or path.name.startswith(".ycet-mobile-"):
            continue
        result[path.relative_to(prototype_dir).as_posix()] = sha256_file(path)
    return result


def ensure_within(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise BuildError(f"{label}路径越界：{path}") from exc
    return resolved


def mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    guessed = MIME_OVERRIDES.get(suffix) or TEXT_MIME_TYPES.get(suffix) or mimetypes.guess_type(path.name)[0]
    if not guessed:
        raise BuildError(f"无法确定资源 MIME 类型：{path}")
    return guessed


def decode_js_string(quote: str, value: str) -> str:
    try:
        return ast.literal_eval(f"{quote}{value}{quote}")
    except (SyntaxError, ValueError) as exc:
        raise BuildError(f"prototype.html 中存在无法解析的字符串：{value!r}") from exc


def field_from_object(body: str, field: str) -> str | None:
    match = re.search(
        rf"(?:^|[,{{])\s*['\"]?{re.escape(field)}['\"]?\s*:\s*(?P<quote>['\"])(?P<value>(?:\\.|(?!\1).)*?)(?P=quote)",
        body,
        re.DOTALL,
    )
    if not match:
        return None
    return decode_js_string(match.group("quote"), match.group("value"))


def safe_page_id(value: str, used: set[str]) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not normalized:
        normalized = "page-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    candidate = normalized
    index = 2
    while candidate in used:
        candidate = f"{normalized}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def canonical_project_path(value: str, required_prefix: str | None = None) -> str:
    if not value or "\\" in value or any(ord(char) < 32 for char in value):
        raise BuildError(f"页面路径不安全：{value!r}")
    parts = urlsplit(value)
    if parts.scheme or parts.netloc or value.startswith("/"):
        raise BuildError(f"页面路径不是项目内相对路径：{value!r}")
    decoded = unquote(parts.path)
    path = PurePosixPath(decoded)
    if path.is_absolute() or ".." in path.parts or path.suffix.lower() != ".html":
        raise BuildError(f"页面路径不安全：{value!r}")
    canonical = path.as_posix().removeprefix("./")
    if required_prefix and not canonical.startswith(required_prefix):
        raise BuildError(f"页面路径必须位于 {required_prefix}：{value!r}")
    return canonical


def page_title(path: Path) -> str:
    match = re.search(r"<title\b[^>]*>(.*?)</title>", path.read_text(encoding="utf-8"), re.IGNORECASE | re.DOTALL)
    if match:
        title = re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()
        if title:
            return title
    return path.stem.split("--", 1)[0]


def extract_registry(prototype_dir: Path, runtime_files: list[Path]) -> list[PageSpec]:
    prototype_path = prototype_dir / "prototype.html"
    by_relative = {path.relative_to(prototype_dir).as_posix(): path for path in runtime_files}
    used_ids: set[str] = set()
    pages: list[PageSpec] = []

    if prototype_path.is_file():
        text = prototype_path.read_text(encoding="utf-8")
        for match in re.finditer(
            r"\{(?P<body>[^{}]*['\"]?runtimePath['\"]?\s*:[^{}]*)\}",
            text,
            re.DOTALL,
        ):
            body = match.group("body")
            runtime_value = field_from_object(body, "runtimePath")
            if not runtime_value:
                continue
            runtime_path = canonical_project_path(runtime_value, "runtime-pages/")
            runtime_file = by_relative.get(runtime_path)
            if runtime_file is None:
                raise BuildError(f"prototype.html 登记的运行时页面不存在：{runtime_path}")
            source_value = field_from_object(body, "sourcePath")
            source_path = canonical_project_path(source_value) if source_value else infer_source_path(runtime_file.name)
            explicit_id = field_from_object(body, "id")
            page_id = safe_page_id(explicit_id or Path(source_path).stem, used_ids)
            label = field_from_object(body, "label") or page_title(runtime_file)
            initial = bool(re.search(r"(?:^|[,{{])\s*['\"]?initial['\"]?\s*:\s*true\b", body))
            pages.append(PageSpec(page_id, label, source_path, runtime_path, runtime_file, initial))
        if runtime_files and not pages:
            raise BuildError("prototype.html 存在但未找到有效页面注册表，不能推测交互来源")

    if not pages:
        groups: dict[str, list[Path]] = {}
        unsuffixed: list[Path] = []
        for path in runtime_files:
            match = RUNTIME_VERSION.match(path.name)
            if match:
                groups.setdefault(match.group("demo"), []).append(path)
            else:
                unsuffixed.append(path)
        if len(groups) > 1 or (groups and unsuffixed):
            raise BuildError("runtime-pages/ 包含多个版本或来源，缺少 prototype.html 时无法唯一选择")
        selected = next(iter(groups.values())) if groups else unsuffixed
        for runtime_file in sorted(selected, key=lambda item: item.relative_to(prototype_dir).as_posix()):
            runtime_path = runtime_file.relative_to(prototype_dir).as_posix()
            source_path = infer_source_path(runtime_file.name)
            page_id = safe_page_id(Path(source_path).stem, used_ids)
            pages.append(PageSpec(page_id, page_title(runtime_file), source_path, runtime_path, runtime_file))

    if not pages:
        raise BuildError(f"runtime-pages/ 中没有可打包的 HTML：{prototype_dir / 'runtime-pages'}")

    if not any(page.initial for page in pages):
        home = next((page for page in pages if page.page_id == "home"), None)
        (home or pages[0]).initial = True
    elif sum(page.initial for page in pages) > 1:
        raise BuildError("页面注册表登记了多个初始页面")
    return pages


def infer_source_path(runtime_name: str) -> str:
    match = RUNTIME_VERSION.match(runtime_name)
    source = match.group("source") if match else Path(runtime_name).stem
    return f"pages/{source}.html"


def normalize_target(target: str, pages: list[PageSpec]) -> str | None:
    target = html.unescape(target).strip()
    if not target or target.startswith("#"):
        return None
    if "\\" in target or any(ord(char) < 32 for char in target):
        raise BuildError(f"交互目标不安全：{target!r}")
    parts = urlsplit(target)
    if parts.scheme in REMOTE_SCHEMES or parts.netloc:
        raise BuildError(f"交互目标包含远程依赖：{target!r}")
    if parts.scheme or target.startswith("/"):
        raise BuildError(f"交互目标不是项目内相对路径：{target!r}")
    pathname = unquote(parts.path).removeprefix("./")
    if ".." in PurePosixPath(pathname).parts:
        raise BuildError(f"交互目标路径越界：{target!r}")

    aliases: dict[str, PageSpec] = {}
    basename_counts: dict[str, int] = {}
    for page in pages:
        for value in (page.runtime_path, page.source_path):
            aliases[value] = page
            basename_counts[PurePosixPath(value).name] = basename_counts.get(PurePosixPath(value).name, 0) + 1
    for page in pages:
        for value in (page.runtime_path, page.source_path):
            basename = PurePosixPath(value).name
            if basename_counts[basename] == 1:
                aliases[basename] = page

    page = aliases.get(pathname)
    if page is None:
        raise BuildError(f"交互目标未登记或悬空：{target!r}")
    suffix = (f"?{parts.query}" if parts.query else "") + (f"#{parts.fragment}" if parts.fragment else "")
    return page.runtime_path + suffix


def collect_targets(page: PageSpec, pages: list[PageSpec]) -> tuple[str, ...]:
    text = page.runtime_file.read_text(encoding="utf-8")
    raw_targets: list[str] = []
    raw_targets.extend(
        html.unescape(match.group("value"))
        for match in re.finditer(
            r"\bdata-ycet-nav-target\s*=\s*(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
    )
    raw_targets.extend(
        decode_js_string(match.group("quote"), match.group("value"))
        for match in re.finditer(
            r"['\"]?targetPage['\"]?\s*:\s*(?P<quote>['\"])(?P<value>(?:\\.|(?!\1).)*?)(?P=quote)",
            text,
            re.DOTALL,
        )
    )
    normalized = {target for value in raw_targets if (target := normalize_target(value, pages))}
    return tuple(sorted(normalized))


class ResourceBundler:
    """递归内联页面依赖；遇到无法离线等价处理的依赖立即失败。"""

    def __init__(self, prototype_dir: Path) -> None:
        self.root = prototype_dir.resolve()
        self.data_cache: dict[Path, str] = {}
        self.css_cache: dict[Path, str] = {}
        self.module_cache: dict[Path, str] = {}
        self.html_stack: set[Path] = set()
        self.resource_paths: set[Path] = set()

    def local_path(self, owner: Path, reference: str, label: str) -> tuple[Path, str]:
        value = html.unescape(reference).strip()
        parts = urlsplit(value)
        scheme = parts.scheme.lower()
        if scheme in REMOTE_SCHEMES or parts.netloc or value.startswith("//"):
            raise BuildError(f"{label}包含远程依赖：{reference!r}")
        if scheme in FORBIDDEN_SCHEMES or (scheme and scheme != "data"):
            raise BuildError(f"{label}包含不支持的协议：{reference!r}")
        if scheme == "data":
            raise BuildError(f"内部错误：不应再次解析 Data URL（{reference!r}）")
        if value.startswith(("/", "\\")):
            raise BuildError(f"{label}使用绝对路径：{reference!r}")
        decoded = unquote(parts.path).replace("\\", "/")
        if not decoded:
            raise BuildError(f"{label}缺少资源路径：{reference!r}")
        candidate = ensure_within(owner.parent / decoded, self.root, label)
        if not candidate.is_file():
            raise BuildError(f"资源不存在：{reference!r}（来源 {owner.relative_to(self.root).as_posix()}）")
        suffix = (f"?{parts.query}" if parts.query else "") + (f"#{parts.fragment}" if parts.fragment else "")
        return candidate, suffix

    def data_url(self, owner: Path, reference: str, label: str = "资源") -> str:
        value = reference.strip()
        if value.startswith("data:"):
            return value
        path, _suffix = self.local_path(owner, reference, label)
        if path not in self.data_cache:
            media_type = mime_type(path)
            payload = base64.b64encode(path.read_bytes()).decode("ascii")
            self.data_cache[path] = f"data:{media_type};base64,{payload}"
            self.resource_paths.add(path)
        # 查询参数通常只用于缓存控制；Data URL 只能保留 SVG 等资源的 fragment。
        fragment = urlsplit(html.unescape(reference).strip()).fragment
        return self.data_cache[path] + (f"#{fragment}" if fragment else "")

    def inline_css_file(self, path: Path, stack: tuple[Path, ...] = ()) -> str:
        path = ensure_within(path, self.root, "CSS")
        if path in self.css_cache:
            return self.css_cache[path]
        if path in stack:
            chain = " -> ".join(item.name for item in (*stack, path))
            raise BuildError(f"CSS @import 存在循环：{chain}")
        if not path.is_file():
            raise BuildError(f"CSS 资源不存在：{path}")
        self.resource_paths.add(path)
        css = path.read_text(encoding="utf-8")
        result = self.inline_css_text(css, path, (*stack, path))
        self.css_cache[path] = result
        return result

    def inline_css_text(self, css: str, owner: Path, stack: tuple[Path, ...] = ()) -> str:
        def replace_import(match: re.Match[str]) -> str:
            reference = match.group("path").strip()
            if reference.startswith("data:"):
                raise BuildError(f"CSS @import 不接受 Data URL：{reference!r}")
            imported, _suffix = self.local_path(owner, reference, "CSS @import")
            nested = self.inline_css_file(imported, stack)
            media = match.group("media").strip()
            return f"@media {media} {{\n{nested}\n}}" if media else nested

        css = CSS_IMPORT.sub(replace_import, css)

        def replace_url(match: re.Match[str]) -> str:
            reference = match.group("path").strip()
            if reference.startswith("data:") or reference.startswith("#"):
                return match.group(0)
            return f'url("{self.data_url(owner, reference, "CSS url()")}")'

        return CSS_URL.sub(replace_url, css)

    def module_data_url(self, owner: Path, reference: str, stack: tuple[Path, ...] = ()) -> str:
        if reference.startswith("data:"):
            return reference
        path, _suffix = self.local_path(owner, reference, "JavaScript 模块")
        if path in self.module_cache:
            return self.module_cache[path]
        if path in stack:
            chain = " -> ".join(item.name for item in (*stack, path))
            raise BuildError(f"JavaScript 模块循环当前无法安全打包：{chain}")
        source = path.read_text(encoding="utf-8")
        self.resource_paths.add(path)
        rewritten = self.rewrite_script(source, path, is_module=True, stack=(*stack, path))
        encoded = base64.b64encode(rewritten.encode("utf-8")).decode("ascii")
        value = f"data:text/javascript;base64,{encoded}"
        self.module_cache[path] = value
        return value

    def rewrite_script(self, source: str, owner: Path, is_module: bool, stack: tuple[Path, ...] = ()) -> str:
        if re.search(r"https?://|['\"]//[^'\"\s]+", source, re.IGNORECASE):
            raise BuildError(f"脚本包含远程依赖：{owner.relative_to(self.root).as_posix()}")
        for pattern, label in NETWORK_SCRIPT_PATTERNS:
            if pattern.search(source):
                raise BuildError(f"脚本包含无法离线打包的 {label}：{owner.relative_to(self.root).as_posix()}")

        if is_module:
            def replace_module(match: re.Match[str]) -> str:
                data = self.module_data_url(owner, match.group("path"), stack)
                return f'{match.group("prefix")}"{data}"'

            source = MODULE_SPECIFIER.sub(replace_module, source)
            source = DYNAMIC_IMPORT.sub(
                lambda match: f'{match.group("prefix")}"{self.module_data_url(owner, match.group("path"), stack)}"{match.group("suffix")}',
                source,
            )
            if re.search(r"\bimport\s*\(\s*(?!['\"])", source):
                raise BuildError(f"脚本包含无法枚举的动态 import：{owner.relative_to(self.root).as_posix()}")

        source = FETCH_LITERAL.sub(
            lambda match: f'{match.group("prefix")}"{self.data_url(owner, match.group("path"), "fetch")}"',
            source,
        )
        if re.search(r"\bfetch\s*\(\s*(?!['\"]data:)", source):
            raise BuildError(f"脚本包含无法枚举的 fetch：{owner.relative_to(self.root).as_posix()}")
        source = NEW_URL_LITERAL.sub(
            lambda match: f'{match.group("prefix")}"{self.data_url(owner, match.group("path"), "new URL")}"',
            source,
        )
        if re.search(r"\bnew\s+URL\s*\([^,]+,\s*import\.meta\.url", source):
            raise BuildError(f"脚本包含无法枚举的 import.meta.url 资源：{owner.relative_to(self.root).as_posix()}")
        return source

    def inline_html(self, path: Path) -> str:
        path = ensure_within(path, self.root, "HTML")
        if path in self.html_stack:
            raise BuildError(f"嵌套 HTML 存在循环引用：{path.relative_to(self.root).as_posix()}")
        self.html_stack.add(path)
        try:
            return self.inline_html_text(path.read_text(encoding="utf-8"), path)
        finally:
            self.html_stack.remove(path)

    def inline_html_text(self, source: str, owner: Path) -> str:
        parser = InlineHTMLParser(self, owner)
        parser.feed(source)
        parser.close()
        return parser.result()


class InlineHTMLParser(HTMLParser):
    """使用结构化 HTML 解析器替换资源属性并保留页面脚本。"""

    def __init__(self, bundler: ResourceBundler, owner: Path) -> None:
        super().__init__(convert_charrefs=False)
        self.bundler = bundler
        self.owner = owner
        self.output: list[str] = []
        self.script_mode: str | None = None
        self.script_chunks: list[str] = []
        self.style_depth = 0

    def result(self) -> str:
        if self.script_mode is not None or self.style_depth:
            raise BuildError(f"HTML 标签未闭合：{self.owner.relative_to(self.bundler.root).as_posix()}")
        return "".join(self.output)

    @staticmethod
    def render_tag(tag: str, attrs: list[tuple[str, str | None]], closed: bool = False) -> str:
        rendered = [f"<{tag}"]
        for name, value in attrs:
            rendered.append(f" {name}" if value is None else f' {name}="{html.escape(value, quote=True)}"')
        rendered.append(" />" if closed else ">")
        return "".join(rendered)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag.lower(), attrs, False)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag.lower(), attrs, True)

    def _start(self, tag: str, attrs: list[tuple[str, str | None]], closed: bool) -> None:
        values = {name.lower(): value for name, value in attrs}
        if tag == "base":
            raise BuildError(f"页面禁止使用 <base>：{self.owner.relative_to(self.bundler.root).as_posix()}")
        if tag == "meta" and (values.get("http-equiv") or "").strip().lower() == "refresh":
            raise BuildError(f"页面禁止使用 meta refresh：{self.owner.relative_to(self.bundler.root).as_posix()}")
        if tag == "script" and closed:
            raise BuildError(f"页面禁止使用自闭合 script：{self.owner.relative_to(self.bundler.root).as_posix()}")

        if tag == "link" and "stylesheet" in (values.get("rel") or "").lower().split():
            href = (values.get("href") or "").strip()
            if href.startswith("data:text/css"):
                self.output.append(self.render_tag(tag, attrs, closed))
                return
            path, _suffix = self.bundler.local_path(self.owner, href, "样式表")
            css = self.bundler.inline_css_file(path)
            media = (values.get("media") or "").strip()
            if media:
                css = f"@media {media} {{\n{css}\n}}"
            self.output.append(f"<style data-ycet-inlined=\"stylesheet\">{css}</style>")
            return

        rewritten: list[tuple[str, str | None]] = []
        script_source: str | None = None
        script_type = (values.get("type") or "").strip().lower()
        for name, value in attrs:
            lowered = name.lower()
            if value is None:
                rewritten.append((name, value))
                continue
            if tag == "script" and lowered == "src":
                script_source = value
                continue
            if lowered == "style":
                rewritten.append((name, self.bundler.inline_css_text(value, self.owner)))
                continue
            if lowered.startswith("on"):
                rewritten.append((name, self.bundler.rewrite_script(value, self.owner, is_module=False)))
                continue
            if lowered == "srcset":
                if value.strip().startswith("data:"):
                    if re.search(r"https?://|file:///", value, re.IGNORECASE):
                        raise BuildError(f"srcset 包含远程或绝对文件依赖：{value!r}")
                    rewritten.append((name, value))
                    continue
                candidates: list[str] = []
                for item in value.split(","):
                    pieces = item.strip().split()
                    if not pieces:
                        continue
                    pieces[0] = self.bundler.data_url(self.owner, pieces[0], "srcset")
                    candidates.append(" ".join(pieces))
                rewritten.append((name, ", ".join(candidates)))
                continue
            if lowered == "srcdoc":
                rewritten.append((name, self.bundler.inline_html_text(value, self.owner)))
                continue
            if tag == "iframe" and lowered == "src" and value.strip() != "about:blank":
                nested_path, _suffix = self.bundler.local_path(self.owner, value, "嵌套 HTML")
                nested = self.bundler.inline_html(nested_path)
                rewritten.append(("srcdoc", nested))
                continue
            if tag == "a" and lowered == "href":
                href = value.strip()
                scheme = urlsplit(href).scheme.lower()
                if href.startswith("#") or scheme in {"mailto", "tel"}:
                    rewritten.append((name, value))
                    continue
                raise BuildError(f"页面链接必须使用 ycet navigate 消息：{value!r}")
            if (tag == "form" and lowered == "action") or lowered == "formaction":
                action = value.strip()
                if action and not action.startswith("#"):
                    raise BuildError(f"表单提交无法离线等价处理：{value!r}")
                rewritten.append((name, value))
                continue
            if tag in {"use", "image"} and lowered in {"href", "xlink:href"}:
                rewritten.append((name, self.bundler.data_url(self.owner, value, "SVG href")))
                continue
            if (tag == "link" and lowered == "href") or lowered in {"src", "poster", "data"}:
                rewritten.append((name, self.bundler.data_url(self.owner, value, f"HTML {lowered}")))
                continue
            rewritten.append((name, value))

        self.output.append(self.render_tag(tag, rewritten, closed))
        if tag == "style" and not closed:
            self.style_depth += 1
        if tag == "script" and not closed:
            if self.script_mode is not None:
                raise BuildError(f"脚本标签嵌套异常：{self.owner.relative_to(self.bundler.root).as_posix()}")
            if script_source:
                path, _suffix = self.bundler.local_path(self.owner, script_source, "JavaScript")
                source = path.read_text(encoding="utf-8")
                self.bundler.resource_paths.add(path)
                source = self.bundler.rewrite_script(source, path, script_type == "module")
                self.output.append(source)
                self.script_mode = "external"
            else:
                self.script_mode = "json" if script_type in {"application/json", "application/ld+json"} else (
                    "module" if script_type == "module" else "classic"
                )
                self.script_chunks = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "script" and self.script_mode is not None:
            if self.script_mode not in {"external", "json"}:
                source = "".join(self.script_chunks)
                self.output.append(self.bundler.rewrite_script(source, self.owner, self.script_mode == "module"))
            elif self.script_mode == "json":
                self.output.extend(self.script_chunks)
            self.script_mode = None
            self.script_chunks = []
        if lowered == "style":
            self.style_depth -= 1
        self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self.script_mode in {"classic", "module", "json"}:
            self.script_chunks.append(data)
        elif self.style_depth:
            self.output.append(self.bundler.inline_css_text(data, self.owner))
        else:
            self.output.append(data)

    def handle_comment(self, data: str) -> None:
        self.output.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self.output.append(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self.output.append(f"<?{data}>")

    def handle_entityref(self, name: str) -> None:
        target = f"&{name};"
        if self.script_mode in {"classic", "module", "json"}:
            self.script_chunks.append(target)
        else:
            self.output.append(target)

    def handle_charref(self, name: str) -> None:
        target = f"&#{name};"
        if self.script_mode in {"classic", "module", "json"}:
            self.script_chunks.append(target)
        else:
            self.output.append(target)


def safe_json_script(value: object) -> str:
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        serialized.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def build_shell(registry: list[dict[str, object]]) -> str:
    registry_json = safe_json_script(registry)
    return f'''<!doctype html>
<html lang="zh-CN" data-ycet-mobile-prototype="true">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover" />
  <title>移动端原型预览</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; background: #fff; }}
    body {{ min-height: 100vh; min-height: 100dvh; font-family: system-ui, sans-serif; }}
    #mobile-screen {{ position: fixed; inset: 0; width: 100%; height: 100vh; height: 100dvh; border: 0; display: block; background: #fff; }}
    #menu-button, #drawer-close {{ width: 44px; height: 44px; border: 0; display: grid; place-items: center; cursor: pointer; }}
    #menu-button {{ position: fixed; z-index: 30; top: max(10px, env(safe-area-inset-top)); left: max(10px, env(safe-area-inset-left)); border-radius: 8px; background: rgba(17, 24, 39, .82); box-shadow: 0 2px 10px rgba(0,0,0,.2); }}
    .menu-icon, .menu-icon::before, .menu-icon::after {{ width: 20px; height: 2px; background: #fff; content: ""; display: block; position: relative; }}
    .menu-icon::before {{ position: absolute; top: -6px; }} .menu-icon::after {{ position: absolute; top: 6px; }}
    #drawer-overlay {{ position: fixed; z-index: 40; inset: 0; border: 0; padding: 0; background: rgba(0,0,0,.38); opacity: 0; visibility: hidden; transition: opacity .18s ease; }}
    #navigation-drawer {{ position: fixed; z-index: 50; inset: 0 auto 0 0; width: min(82vw, 320px); padding: max(12px, env(safe-area-inset-top)) 12px max(12px, env(safe-area-inset-bottom)); background: #fff; color: #111827; transform: translateX(-100%); transition: transform .18s ease; box-shadow: 8px 0 24px rgba(0,0,0,.18); overflow: auto; scrollbar-width: none; }}
    #navigation-drawer::-webkit-scrollbar {{ display: none; }}
    body.drawer-open #drawer-overlay {{ opacity: 1; visibility: visible; }} body.drawer-open #navigation-drawer {{ transform: translateX(0); }}
    .drawer-header {{ height: 48px; display: flex; align-items: center; justify-content: space-between; padding-left: 8px; border-bottom: 1px solid #e5e7eb; }}
    .drawer-title {{ font-size: 16px; font-weight: 650; }} #drawer-close {{ background: transparent; font-size: 24px; color: #374151; }}
    #page-list {{ display: grid; gap: 4px; padding: 10px 0; }}
    .page-button {{ min-height: 44px; border: 0; border-left: 3px solid transparent; padding: 10px 12px; background: transparent; color: #374151; text-align: left; font: inherit; cursor: pointer; }}
    .page-button[aria-current="page"] {{ border-left-color: #2563eb; background: #eff6ff; color: #1d4ed8; font-weight: 650; }}
    #preview-error {{ position: fixed; z-index: 60; left: 50%; bottom: max(16px, env(safe-area-inset-bottom)); max-width: calc(100% - 32px); transform: translateX(-50%); padding: 10px 12px; border-radius: 6px; background: #991b1b; color: #fff; font-size: 14px; visibility: hidden; }}
  </style>
</head>
<body>
  <iframe id="mobile-screen" title="产品原型" scrolling="no"></iframe>
  <button id="menu-button" type="button" aria-label="打开页面导航" title="打开页面导航"><span class="menu-icon" aria-hidden="true"></span></button>
  <button id="drawer-overlay" type="button" aria-label="关闭页面导航" tabindex="-1"></button>
  <aside id="navigation-drawer" aria-label="页面导航" aria-hidden="true">
    <div class="drawer-header"><span class="drawer-title">页面</span><button id="drawer-close" type="button" aria-label="关闭页面导航" title="关闭页面导航">&times;</button></div>
    <nav id="page-list"></nav>
  </aside>
  <div id="preview-error" role="status" aria-live="polite"></div>
  <script id="ycet-mobile-pages" type="application/json">{registry_json}</script>
  <script>
    (() => {{
      "use strict";
      const CHANNEL = "ycet-prototype";
      const VERSION = 1;
      const pages = JSON.parse(document.getElementById("ycet-mobile-pages").textContent);
      const byId = new Map(pages.map((page) => [page.id, page]));
      const aliases = new Map();
      for (const page of pages) {{ aliases.set(page.runtimePath, page.id); aliases.set(page.sourcePath, page.id); }}
      const frame = document.getElementById("mobile-screen");
      const drawer = document.getElementById("navigation-drawer");
      const menuButton = document.getElementById("menu-button");
      const pageList = document.getElementById("page-list");
      const errorBox = document.getElementById("preview-error");
      let currentId = pages.find((page) => page.initial)?.id || pages[0]?.id;
      let currentTarget = byId.get(currentId)?.runtimePath || "";
      let errorTimer = 0;

      function decodePage(page) {{
        const bytes = Uint8Array.from(atob(page.srcdocBase64), (char) => char.charCodeAt(0));
        return new TextDecoder("utf-8").decode(bytes);
      }}
      function showError(message) {{
        errorBox.textContent = message; errorBox.style.visibility = "visible";
        clearTimeout(errorTimer); errorTimer = setTimeout(() => {{ errorBox.style.visibility = "hidden"; }}, 3200);
      }}
      function setDrawer(open) {{
        document.body.classList.toggle("drawer-open", open); drawer.setAttribute("aria-hidden", String(!open));
        if (open) drawer.querySelector("button")?.focus(); else menuButton.focus();
      }}
      function parseTarget(value) {{
        if (typeof value !== "string" || !value || value.includes("\\\\") || /[\\u0000-\\u001f]/.test(value) || value.startsWith("/")) return null;
        if (/^[a-z][a-z0-9+.-]*:/i.test(value) || value.includes("../")) return null;
        const match = value.match(/^([^?#]*)(.*)$/); if (!match) return null;
        let pathname; try {{ pathname = decodeURIComponent(match[1]).replace(/^\\.\\//, ""); }} catch {{ return null; }}
        let id = aliases.get(pathname);
        if (!id) {{
          const candidates = pages.filter((page) => page.runtimePath.endsWith("/" + pathname) || page.sourcePath.endsWith("/" + pathname));
          if (candidates.length === 1) id = candidates[0].id;
        }}
        return id ? {{ id, target: byId.get(id).runtimePath + match[2] }} : null;
      }}
      function updateCurrent() {{
        for (const button of pageList.querySelectorAll("button[data-page-id]")) {{
          if (button.dataset.pageId === currentId) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
        }}
      }}
      function loadPage(id, target, push) {{
        const page = byId.get(id); if (!page) {{ showError("无法打开未登记页面"); return; }}
        currentId = id; currentTarget = target || page.runtimePath; frame.title = page.label; frame.srcdoc = decodePage(page); updateCurrent(); setDrawer(false);
        const state = {{ ycetMobile: true, pageId: id, target: currentTarget }};
        if (push) history.pushState(state, "", location.href); else history.replaceState(state, "", location.href);
      }}
      function navigate(value, push = true) {{
        const parsed = parseTarget(value); if (!parsed) {{ showError("已阻止未知或不安全的页面目标"); return; }}
        loadPage(parsed.id, parsed.target, push);
      }}
      pages.forEach((page, index) => {{
        const button = document.createElement("button"); button.type = "button"; button.className = "page-button";
        button.dataset.pageId = page.id; button.textContent = `${{index + 1}}. ${{page.label}}`;
        button.addEventListener("click", () => navigate(page.runtimePath)); pageList.append(button);
      }});
      menuButton.addEventListener("click", () => setDrawer(true));
      document.getElementById("drawer-close").addEventListener("click", () => setDrawer(false));
      document.getElementById("drawer-overlay").addEventListener("click", () => setDrawer(false));
      document.addEventListener("keydown", (event) => {{ if (event.key === "Escape" && document.body.classList.contains("drawer-open")) setDrawer(false); }});
      addEventListener("message", (event) => {{
        const message = event.data;
        if (event.source !== frame.contentWindow || !message || message.channel !== CHANNEL || message.version !== VERSION) return;
        if (message.type === "navigate") navigate(message.targetPage);
      }});
      addEventListener("popstate", (event) => {{
        const state = event.state;
        if (state?.ycetMobile && byId.has(state.pageId)) {{ currentId = state.pageId; currentTarget = state.target || byId.get(currentId).runtimePath; frame.title = byId.get(currentId).label; frame.srcdoc = decodePage(byId.get(currentId)); updateCurrent(); setDrawer(false); }}
      }});
      if (!currentId) showError("页面注册表为空"); else loadPage(currentId, currentTarget, false);
    }})();
  </script>
</body>
</html>
'''


def choose_output(prototype_dir: Path) -> Path:
    versions: list[int] = []
    for path in prototype_dir.iterdir():
        if not path.is_file():
            continue
        match = MOBILE_NAME.fullmatch(path.name)
        if match:
            versions.append(int(match.group("version") or 1))
    if not versions:
        return prototype_dir / "prototype-mobile.html"
    return prototype_dir / f"prototype-mobile-v{max(versions) + 1}.html"


def validate_output(document: str, registry: list[dict[str, object]]) -> None:
    required = ('data-ycet-mobile-prototype="true"', 'id="mobile-screen"', 'id="navigation-drawer"')
    for token in required:
        if token not in document:
            raise BuildError(f"生成结果缺少移动端外壳标记：{token}")
    if "http://" in document.lower() or "https://" in document.lower() or "file:///" in document.lower():
        raise BuildError("生成结果仍含远程或绝对文件依赖")
    for page in registry:
        try:
            decoded = base64.b64decode(str(page["srcdocBase64"]), validate=True).decode("utf-8")
        except (ValueError, UnicodeError) as exc:
            raise BuildError(f"页面 srcdoc 编码无效：{page.get('runtimePath')}") from exc
        if re.search(
            r"<(?:script|iframe|img|source|video|audio|embed)\b[^>]*\bsrc\s*=\s*(['\"])(?!data:|about:)[^'\"]+\1",
            decoded,
            re.IGNORECASE,
        ):
            raise BuildError(f"页面仍含未内联 src：{page.get('runtimePath')}")
        if re.search(r"<link\b[^>]*\bhref\s*=\s*(['\"])(?!data:)[^'\"]+\1", decoded, re.IGNORECASE):
            raise BuildError(f"页面仍含未内联 link：{page.get('runtimePath')}")


def build(prototype_dir: Path) -> Path:
    prototype_dir = prototype_dir.resolve()
    if not prototype_dir.is_dir():
        raise BuildError(f"prototype/ 目录不存在：{prototype_dir}")
    runtime_dir = prototype_dir / "runtime-pages"
    if not runtime_dir.is_dir():
        raise BuildError(f"runtime-pages/ 目录不存在：{runtime_dir}")
    runtime_files = sorted(path for path in runtime_dir.rglob("*.html") if path.is_file())
    if not runtime_files:
        raise BuildError(f"runtime-pages/ 中没有 HTML：{runtime_dir}")

    output = choose_output(prototype_dir)
    before = input_snapshot(prototype_dir, (output,))
    pages = extract_registry(prototype_dir, runtime_files)
    for page in pages:
        page.targets = collect_targets(page, pages)

    bundler = ResourceBundler(prototype_dir)
    registry: list[dict[str, object]] = []
    for order, page in enumerate(pages):
        srcdoc = bundler.inline_html(page.runtime_file)
        registry.append(
            {
                "id": page.page_id,
                "label": page.label,
                "sourcePath": page.source_path,
                "runtimePath": page.runtime_path,
                "targets": list(page.targets),
                "order": order,
                "initial": page.initial,
                "srcdocBase64": base64.b64encode(srcdoc.encode("utf-8")).decode("ascii"),
            }
        )

    document = build_shell(registry)
    validate_output(document, registry)
    if input_snapshot(prototype_dir, (output,)) != before:
        raise BuildError("打包期间受保护输入的文件集合或 SHA-256 发生变化")

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".ycet-mobile-",
            suffix=".tmp",
            dir=prototype_dir,
            delete=False,
        ) as target:
            target.write(document)
            target.flush()
            os.fsync(target.fileno())
            temporary = Path(target.name)
        if temporary.read_text(encoding="utf-8") != document:
            raise BuildError("临时输出复核失败")
        if output.exists():
            raise BuildError(f"目标版本已存在，拒绝覆盖：{output.name}")
        os.replace(temporary, output)
        temporary = None
        if input_snapshot(prototype_dir, (output,)) != before:
            output.unlink(missing_ok=True)
            raise BuildError("输出后复核发现受保护输入发生变化，已移除本次输出")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    resource_types = Counter(mime_type(path) for path in bundler.resource_paths)
    type_summary = "、".join(f"{name}={count}" for name, count in sorted(resource_types.items())) or "无额外资源"
    print(
        f"[OK] 已生成 {output.name}：{len(pages)} 个页面，"
        f"{len(bundler.resource_paths)} 个本地资源，{output.stat().st_size} 字节。"
    )
    print(f"[OK] 资源类型：{type_summary}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prototype-dir", required=True, type=Path, help="包含 runtime-pages/ 的 prototype 目录")
    args = parser.parse_args()
    try:
        build(args.prototype_dir)
    except (BuildError, OSError, UnicodeError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
