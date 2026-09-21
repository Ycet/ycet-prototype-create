"""单文件资源内联与严格依赖解析。"""
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
from prototype_syntax import script_problem



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
        if tag in {"iframe", "object", "embed"} or any(k.lower() == "srcdoc" for k, _ in attrs):
            raise BuildError("v4 页面必须使用直接 DOM")
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
                # 事件属性与页面 JS 共用隔离规则；保留 this/event 的本地交互。
                problem = script_problem(value, page=True)
                if problem:
                    raise BuildError(problem)
                rewritten.append((name, value))
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
                rewritten.append((name, value if value.startswith("#") else self.bundler.data_url(self.owner, value, "SVG href")))
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

def assign_element_ids(source: str, page_id: str) -> str:
    """先保留显式标识，再给未标识元素分配唯一 ID；不重写原始标签。"""
    class Tags(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tags = []
        def handle_starttag(self, tag, attrs):
            self.tags.append((self.getpos(), self.get_starttag_text(), attrs))
        handle_startendtag = handle_starttag
    parser = Tags()
    parser.feed(source)
    used = set()
    for _position, _tag, attrs in parser.tags:
        values = [value for name, value in attrs if name == 'data-ycet-element-id']
        if len(values) > 1 or values and (not values[0] or values[0] in used):
            raise BuildError('页面内元素 ID 缺失或重复：' + page_id)
        used.update(values)
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    changes = []
    number = 1
    for (line, column), tag, attrs in parser.tags:
        if any(name == 'data-ycet-element-id' for name, _value in attrs):
            continue
        while f'{page_id}-el-{number}' in used:
            number += 1
        identifier = f'{page_id}-el-{number}'
        used.add(identifier)
        number += 1
        end = offsets[line - 1] + column + len(tag) - (2 if tag.endswith('/>') else 1)
        changes.append((end, ' data-ycet-element-id="' + identifier + '"'))
    # 一次拼接，避免大图片内联页面被每个标签反复复制。
    chunks, cursor = [], 0
    for offset, value in changes:
        chunks.extend((source[cursor:offset], value))
        cursor = offset
    chunks.append(source[cursor:])
    return ''.join(chunks)

def safe_json_script(value: object) -> str:
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        serialized.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
