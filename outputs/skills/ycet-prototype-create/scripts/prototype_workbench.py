#!/usr/bin/env python3
"""YCET 原型可视化工作台：本地服务、工作区、变更包和撤回事务。"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
HOST = "127.0.0.1"
SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = SKILL_ROOT / "assets" / "workbench"
ALLOWED_OPERATIONS = {"annotation", "style", "text", "image-replace", "css", "sync-pages"}
PROJECT_HTML_DIRS = ("pages", "previews", "runtime-pages")
HTML_MIME = "text/html; charset=utf-8"
FONT_STYLE_SUFFIX = re.compile(r"\s+(?:regular|bold|italic|oblique|light|medium|semi\s*bold|demi\s*bold|extra\s*bold|extra\s*light|black|thin)(?:\s+(?:italic|oblique))?$", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def file_id(path: Path) -> str:
    return hashlib.sha256(os.path.normcase(str(path.resolve())).encode("utf-8")).hexdigest()[:20]


def state_paths(project_root: Path) -> dict[str, Path]:
    root = project_root / ".ycet-editor"
    return {
        "root": root,
        "workspace": root / "workspace.json",
        "server": root / "server.json",
        "requests": root / "requests",
        "transactions": root / "transactions",
        "undo": root / "undo" / "latest",
        "lock": root / "mobile-pack.lock.json",
        "log": root / "server.log",
    }


class WorkbenchError(RuntimeError):
    """可安全展示给用户的工作台错误。"""


class Workspace:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.prototype_root = self.project_root / "prototype"
        self.paths = state_paths(self.project_root)
        self.paths["root"].mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.data = self._load()
        self.scan()

    def _default(self) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "projectRoot": str(self.project_root),
            "files": [],
            "groups": [],
            "hiddenProjectPaths": [],
            "currentFileId": None,
            "zoomByFile": {},
            "updatedAt": utc_now(),
        }

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.paths["workspace"].read_text(encoding="utf-8"))
            if data.get("schemaVersion") != SCHEMA_VERSION:
                raise WorkbenchError("workspace.json 版本不受支持")
            if Path(data.get("projectRoot", "")).resolve() != self.project_root:
                raise WorkbenchError("workspace.json 不属于当前项目")
            return data
        except FileNotFoundError:
            return self._default()
        except (json.JSONDecodeError, OSError, WorkbenchError) as exc:
            backup = self.paths["workspace"].with_suffix(f".invalid-{int(time.time())}.json")
            if self.paths["workspace"].exists():
                shutil.copy2(self.paths["workspace"], backup)
            data = self._default()
            data["recoveryWarning"] = str(exc)
            return data

    def save(self) -> None:
        self.data["updatedAt"] = utc_now()
        atomic_json(self.paths["workspace"], self.data)

    def _project_candidates(self) -> list[Path]:
        if not self.prototype_root.is_dir():
            return []
        candidates = list(self.prototype_root.glob("*.html"))
        for directory in PROJECT_HTML_DIRS:
            root = self.prototype_root / directory
            if root.is_dir():
                candidates.extend(root.rglob("*.html"))
        return sorted({path.resolve() for path in candidates}, key=lambda item: item.name.casefold())

    def _record(self, path: Path, source: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
        resolved = path.resolve()
        record = dict(existing or {})
        if source == "project":
            stored_path = resolved.relative_to(self.project_root).as_posix()
            relative = resolved.relative_to(self.prototype_root).as_posix()
            automatic_group = relative.split("/", 1)[0] if "/" in relative else ""
        else:
            stored_path = str(resolved)
            automatic_group = ""
        kind = "offline" if re.fullmatch(r"prototype-mobile(?:-v\d+)?\.html", resolved.name) else (
            "runtime" if automatic_group == "runtime-pages" else "html"
        )
        record.update(
            {
                "id": file_id(resolved),
                "source": source,
                "path": stored_path,
                "name": resolved.name,
                "kind": kind,
                "automaticGroup": automatic_group,
                "missing": not resolved.is_file(),
            }
        )
        if resolved.is_file():
            stat = resolved.stat()
            record["sha256"] = sha256_file(resolved)
            record["mtimeNs"] = stat.st_mtime_ns
        else:
            record["sha256"] = None
            record["mtimeNs"] = None
        record.setdefault("manualGroup", None)
        record.setdefault("order", None)
        return record

    def record_path(self, record: dict[str, Any]) -> Path:
        raw = Path(record["path"])
        return (self.project_root / raw).resolve() if record["source"] == "project" else raw.resolve()

    def scan(self, explicit: list[Path] | None = None) -> dict[str, Any]:
        with self._lock:
            before = json.dumps(self.data, ensure_ascii=False, sort_keys=True)
            existing = {item["id"]: item for item in self.data.get("files", [])}
            hidden = set(self.data.get("hiddenProjectPaths", []))
            discovered: list[dict[str, Any]] = []
            for path in self._project_candidates():
                stored = path.relative_to(self.project_root).as_posix()
                if stored in hidden:
                    continue
                discovered.append(self._record(path, "project", existing.get(file_id(path))))

            # 已登记但后来丢失的项目文件继续显示为“缺失”，直到用户主动移出工作区。
            discovered_ids = {item["id"] for item in discovered}
            for previous in existing.values():
                if previous.get("source") != "project" or previous["id"] in discovered_ids or previous.get("path") in hidden:
                    continue
                discovered.append(self._record(self.record_path(previous), "project", previous))

            # 外部文件不会被目录扫描；仅恢复用户已经明确登记的路径。
            for previous in existing.values():
                if previous.get("source") != "external":
                    continue
                path = self.record_path(previous)
                discovered.append(self._record(path, "external", previous))

            for path in explicit or []:
                resolved = path.resolve()
                if not resolved.is_file() or resolved.suffix.lower() != ".html":
                    raise WorkbenchError(f"不是可读取的 HTML 文件：{resolved}")
                source = "project" if is_within(resolved, self.prototype_root) else "external"
                if source == "project":
                    stored = resolved.relative_to(self.project_root).as_posix()
                    hidden.discard(stored)
                record = self._record(resolved, source, existing.get(file_id(resolved)))
                discovered = [item for item in discovered if item["id"] != record["id"]]
                discovered.append(record)

            order = {item["id"]: index for index, item in enumerate(self.data.get("files", []))}
            discovered.sort(key=lambda item: (item.get("manualGroup") or item["automaticGroup"], order.get(item["id"], 10**9), item["name"].casefold()))
            self.data["files"] = discovered
            self.data["hiddenProjectPaths"] = sorted(hidden)
            ids = {item["id"] for item in discovered}
            if self.data.get("currentFileId") not in ids:
                self.data["currentFileId"] = discovered[0]["id"] if discovered else None
            after = json.dumps(self.data, ensure_ascii=False, sort_keys=True)
            if before != after or not self.paths["workspace"].is_file():
                self.save()
            return self.public()

    def public(self) -> dict[str, Any]:
        payload = json.loads(json.dumps(self.data))
        payload["prototypeExists"] = self.prototype_root.is_dir()
        payload["projectName"] = self.project_root.name
        return payload

    def find(self, identifier: str) -> dict[str, Any]:
        for record in self.data.get("files", []):
            if record["id"] == identifier:
                return record
        raise WorkbenchError("文件未登记或已移出工作区")

    def ensure_record_for_path(self, path: Path, source: str) -> dict[str, Any]:
        identifier = file_id(path)
        try:
            return self.find(identifier)
        except WorkbenchError:
            return self._record(path, source)

    def remove(self, identifier: str) -> dict[str, Any]:
        with self._lock:
            record = self.find(identifier)
            if record["source"] == "project":
                hidden = set(self.data.get("hiddenProjectPaths", []))
                hidden.add(record["path"])
                self.data["hiddenProjectPaths"] = sorted(hidden)
            self.data["files"] = [item for item in self.data["files"] if item["id"] != identifier]
            if self.data.get("currentFileId") == identifier:
                self.data["currentFileId"] = self.data["files"][0]["id"] if self.data["files"] else None
            self.save()
            return self.public()

    def update_preferences(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            valid_ids = {item["id"] for item in self.data["files"]}
            groups = payload.get("groups", self.data.get("groups", []))
            clean_groups = []
            seen_groups: set[str] = set()
            for group in groups:
                identifier = str(group.get("id", "")).strip()
                name = str(group.get("name", "")).strip()
                if not identifier or not name or identifier in seen_groups:
                    continue
                seen_groups.add(identifier)
                clean_groups.append({"id": identifier, "name": name, "order": len(clean_groups)})
            assignments = payload.get("assignments", {})
            order = payload.get("order", [])
            order_map = {identifier: index for index, identifier in enumerate(order) if identifier in valid_ids}
            for record in self.data["files"]:
                group_id = assignments.get(record["id"], record.get("manualGroup"))
                record["manualGroup"] = group_id if group_id in seen_groups else None
                record["order"] = order_map.get(record["id"], record.get("order"))
            current = payload.get("currentFileId")
            if current in valid_ids:
                self.data["currentFileId"] = current
            zoom = payload.get("zoomByFile")
            if isinstance(zoom, dict):
                self.data["zoomByFile"] = {key: max(25, min(200, int(value))) for key, value in zoom.items() if key in valid_ids}
            self.data["groups"] = clean_groups
            self.save()
            return self.public()


def inject_runtime(html: str, config: dict[str, Any], base_url: str) -> bytes:
    # 原文只在响应内注入，磁盘 HTML 始终保持原字节。
    html = re.sub(r"<meta\s+[^>]*http-equiv=[\"']?content-security-policy[^>]*>", "", html, flags=re.I)
    encoded = json.dumps(config, ensure_ascii=False).replace("</", "<\\/")
    injection = (
        f'<base href="{base_url}">'
        f'<script>window.__YCET_EDITOR_CONFIG__={encoded};</script>'
        '<script src="/assets/preview-runtime.js"></script>'
    )
    if re.search(r"</head\s*>", html, flags=re.I):
        html = re.sub(r"</head\s*>", injection + "</head>", html, count=1, flags=re.I)
    else:
        html = injection + html
    return html.encode("utf-8")


def _font_family_names(display_name: str) -> list[str]:
    cleaned = re.sub(r"\s*\((?:True\s*Type|Open\s*Type|PostScript|All res)\)\s*$", "", display_name, flags=re.I).lstrip("@").strip()
    names = []
    for item in re.split(r"\s*&\s*", cleaned):
        family = FONT_STYLE_SUFFIX.sub("", item).strip()
        if family:
            names.append(family)
    return names


def list_system_fonts() -> list[str]:
    """使用标准库枚举本机字体族；浏览器可再用 Local Font Access 补全。"""
    families = {"Arial", "Georgia", "Microsoft YaHei", "Segoe UI"}
    if os.name == "nt":
        try:
            import winreg

            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, key_path) as key:
                        index = 0
                        while True:
                            try:
                                display_name = winreg.EnumValue(key, index)[0]
                            except OSError:
                                break
                            families.update(_font_family_names(display_name))
                            index += 1
                except OSError:
                    continue
        except (ImportError, OSError):
            pass
    else:
        try:
            result = subprocess.run(["fc-list", "--format=%{family}\n"], capture_output=True, text=True, timeout=5, check=False)
            for line in result.stdout.splitlines():
                families.update(item.strip() for item in line.split(",") if item.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    return sorted(families, key=str.casefold)


def choose_file(kind: str) -> Path | None:
    if kind != "image":
        raise WorkbenchError("文件选择类型无效")
    override = os.environ.get("YCET_WORKBENCH_DIALOG_PATH")
    if override:
        return Path(override).resolve()
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        try:
            root.withdraw()
            root.attributes("-topmost", True)
            root.update_idletasks()
            filetypes = [
                ("图片文件", "*.png *.jpg *.jpeg *.webp *.gif *.svg"),
                ("所有文件", "*.*"),
            ]
            selected = filedialog.askopenfilename(parent=root, title="选择替换图片", filetypes=filetypes)
            return Path(selected).resolve() if selected else None
        finally:
            root.destroy()
    except Exception as exc:  # noqa: BLE001 - Tk 在部分精简 Python 环境中不可用
        raise WorkbenchError(f"无法打开系统文件选择器：{exc}。可改用 CLI 的 --add 参数登记路径。") from exc


class DialogBroker:
    """把 ThreadingHTTPServer 的文件选择请求转交给 Python 主线程。"""

    def __init__(self) -> None:
        self._requests: queue.Queue[tuple[str, queue.Queue[Path | None | Exception]]] = queue.Queue()
        self._closed = threading.Event()

    def choose(self, kind: str) -> Path | None:
        # 测试/自动化覆盖不创建 Tk，可直接在请求线程返回。
        if os.environ.get("YCET_WORKBENCH_DIALOG_PATH"):
            return choose_file(kind)
        if self._closed.is_set():
            raise WorkbenchError("工作台正在关闭，无法打开文件选择器")
        response: queue.Queue[Path | None | Exception] = queue.Queue(maxsize=1)
        self._requests.put((kind, response))
        try:
            result = response.get(timeout=300)
        except queue.Empty as exc:
            raise WorkbenchError("系统文件选择器等待超时") from exc
        if isinstance(result, Exception):
            raise result
        return result

    def process_once(self, timeout: float = 0.1) -> bool:
        try:
            kind, response = self._requests.get(timeout=timeout)
        except queue.Empty:
            return False
        try:
            response.put(choose_file(kind))
        except Exception as exc:  # noqa: BLE001 - 原始错误需返回 HTTP 请求线程
            response.put(exc)
        return True

    def close(self) -> None:
        self._closed.set()
        while True:
            try:
                _kind, response = self._requests.get_nowait()
            except queue.Empty:
                break
            response.put(WorkbenchError("工作台已关闭"))


def validate_request(workspace: Workspace, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schemaVersion") not in (None, SCHEMA_VERSION):
        raise WorkbenchError("变更包版本不受支持")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise WorkbenchError("变更包没有文件修改")
    normalized_files = []
    for item in files:
        record = workspace.find(str(item.get("fileId", "")))
        path = workspace.record_path(record)
        if not path.is_file():
            raise WorkbenchError(f"文件不存在：{record['path']}")
        current = sha256_file(path)
        expected = item.get("sha256") or record.get("sha256")
        if expected != current:
            raise WorkbenchError(f"源文件已变化，拒绝发送旧草稿：{record['path']}")
        operations = item.get("operations", [])
        if not operations:
            continue
        for operation in operations:
            if operation.get("type") not in ALLOWED_OPERATIONS:
                raise WorkbenchError(f"不支持的操作类型：{operation.get('type')}")
            if operation.get("type") in {"css", "style"}:
                value = str(operation.get("value", ""))
                if re.search(r"url\s*\(|@import|javascript:|expression\s*\(|-moz-binding|behavior\s*:", value, re.I):
                    raise WorkbenchError("CSS 草稿包含网络、路径或危险值")
        normalized_files.append(
            {
                "fileId": record["id"],
                "source": record["source"],
                "path": str(path),
                "displayPath": record["path"],
                "kind": record["kind"],
                "sha256": current,
                "operations": operations,
                "dependencyGroup": item.get("dependencyGroup"),
            }
        )
    if not normalized_files:
        raise WorkbenchError("没有可发送的修改")
    request_id = str(payload.get("requestId") or uuid.uuid4())
    return {
        "schemaVersion": SCHEMA_VERSION,
        "requestId": request_id,
        "createdAt": utc_now(),
        "projectRoot": str(workspace.project_root),
        "files": normalized_files,
        "status": "pending",
    }


def request_instruction(project_root: Path, request_id: str) -> str:
    return (
        "请调用 $ycet-prototype-create 执行原型工作台变更包。"
        f"项目根目录：{project_root}；请求 ID：{request_id}。"
        "先读取 docs/shared-workbench-protocol.md，再用 prototype_workbench.py request show/begin/complete 执行并逐文件报告结果。"
    )


class WorkbenchService:
    def __init__(self, project_root: Path, token: str):
        self.workspace = Workspace(project_root)
        self.token = token
        self.dialogs = DialogBroker()
        self.fonts = list_system_fonts()
        self.selected_assets: dict[str, Path] = {}
        self.dirty_file_ids: set[str] = set()
        self.stale_draft_file_ids: set[str] = set()
        self.revision = 0
        self._revision_lock = threading.Lock()
        self._stop = threading.Event()
        self._known_sha = {item["id"]: item.get("sha256") for item in self.workspace.data["files"]}
        self._watcher = threading.Thread(target=self._watch_files, name="ycet-workbench-watch", daemon=True)
        self._watcher.start()

    @property
    def paths(self) -> dict[str, Path]:
        return self.workspace.paths

    def bump(self) -> None:
        with self._revision_lock:
            self.revision += 1

    def _watch_files(self) -> None:
        # 标准库轮询同时发现项目内新增 HTML 与已登记文件的外部变更。
        while not self._stop.wait(1.0):
            try:
                workspace = self.workspace.scan()
                current = {item["id"]: item.get("sha256") for item in workspace["files"]}
                changed = {identifier for identifier in set(current) | set(self._known_sha) if current.get(identifier) != self._known_sha.get(identifier)}
                if changed:
                    self.stale_draft_file_ids.update(changed & self.dirty_file_ids)
                    self._known_sha = current
                    self.bump()
            except (OSError, WorkbenchError):
                continue

    def stop(self) -> None:
        self._stop.set()
        self._watcher.join(timeout=2)

    def create_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.paths["lock"].exists():
            raise WorkbenchError("功能五打包锁已启用，暂时不能发送修改")
        if self.stale_draft_file_ids:
            raise WorkbenchError("源文件已变化，必须刷新并重新编辑后才能发送")
        package = validate_request(self.workspace, payload)
        path = self.paths["requests"] / f"{package['requestId']}.json"
        atomic_json(path, package)
        self.dirty_file_ids.clear()
        self.stale_draft_file_ids.clear()
        self.bump()
        return {
            "requestId": package["requestId"],
            "path": str(path),
            "instruction": request_instruction(self.workspace.project_root, package["requestId"]),
        }


def handler_factory(service: WorkbenchService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "YCETWorkbench/1.0"

        def log_message(self, format_string: str, *args: Any) -> None:
            message = f"[{utc_now()}] {self.address_string()} {format_string % args}\n"
            with service.paths["log"].open("a", encoding="utf-8") as stream:
                stream.write(message)

        def _allowed_host(self) -> bool:
            host = self.headers.get("Host", "").split(":", 1)[0]
            return host in {HOST, "localhost", "[::1]"}

        def _authorized(self) -> bool:
            if not self._allowed_host():
                return False
            supplied = self.headers.get("X-YCET-Token")
            if not supplied:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                supplied = query.get("token", [None])[0]
            if not supplied:
                # Cookie 名包含令牌摘要，避免多个项目在不同端口覆盖彼此的实例令牌。
                cookies = [part.split("=", 1)[1] for part in self.headers.get("Cookie", "").split(";") if "=" in part]
                supplied = next((value for value in cookies if secrets.compare_digest(value, service.token)), None)
            if not secrets.compare_digest(str(supplied or ""), service.token):
                return False
            origin = self.headers.get("Origin")
            if origin:
                parsed = urllib.parse.urlsplit(origin)
                if parsed.hostname not in {HOST, "localhost", "::1"}:
                    return False
            return True

        def _json_body(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 5 * 1024 * 1024:
                    raise WorkbenchError("请求体过大")
                return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise WorkbenchError("请求 JSON 无效") from exc

        def _send(self, status: int, payload: bytes, content_type: str, extra: dict[str, str] | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, payload: Any, status: int = 200) -> None:
            self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _error(self, status: int, message: str) -> None:
            self._send_json({"error": message}, status)

        def _static(self, relative: str, extra: dict[str, str] | None = None) -> None:
            target = (ASSET_ROOT / relative).resolve()
            if not is_within(target, ASSET_ROOT) or not target.is_file():
                self._error(404, "资源不存在")
                return
            mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            headers = {"Cache-Control": "no-store", **(extra or {})}
            self._send(200, target.read_bytes(), f"{mime}; charset=utf-8" if mime.startswith("text/") or mime == "application/javascript" else mime, headers)

        def _preview(self, identifier: str, relative: str) -> None:
            root_record = service.workspace.find(identifier)
            root_path = service.workspace.record_path(root_record)
            allowed_root = service.workspace.prototype_root if root_record["source"] == "project" else root_path.parent
            relative = urllib.parse.unquote(relative or "")
            target = (root_path.parent / relative).resolve() if relative else root_path
            if not is_within(target, allowed_root) or not target.is_file():
                self._error(404, "预览资源不存在或路径越界")
                return
            mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if target.suffix.lower() not in {".html", ".htm"}:
                self._send(200, target.read_bytes(), mime)
                return
            try:
                text = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = target.read_text(encoding="utf-8-sig")
            actual = service.workspace.ensure_record_for_path(target, root_record["source"])
            config = {
                "channel": "ycet-editor",
                "version": 1,
                "fileId": actual["id"],
                "rootFileId": identifier,
                "path": actual["path"],
                "sha256": sha256_file(target),
            }
            payload = inject_runtime(text, config, f"/preview/{actual['id']}/")
            csp = (
                "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; "
                "style-src 'self' 'unsafe-inline' data: blob:; img-src 'self' data: blob:; font-src 'self' data: blob:; "
                "connect-src 'self'; frame-src 'self' data: blob:; object-src 'none'; base-uri 'self'"
            )
            self._send(200, payload, HTML_MIME, {"Content-Security-Policy": csp, "Cache-Control": "no-store"})

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path
            try:
                if path == "/" or path == "/index.html":
                    query = urllib.parse.parse_qs(parsed.query)
                    supplied = query.get("token", [""])[0]
                    if not secrets.compare_digest(str(supplied), service.token):
                        self._error(403, "实例令牌无效")
                        return
                    cookie_name = f"YCET_{hashlib.sha256(service.token.encode()).hexdigest()[:12]}"
                    self._static("index.html", {"Set-Cookie": f"{cookie_name}={service.token}; Path=/; HttpOnly; SameSite=Strict"})
                    return
                if path.startswith("/assets/"):
                    self._static(path.removeprefix("/assets/"))
                    return
                if not self._authorized():
                    self._error(403, "实例令牌无效")
                    return
                if path == "/api/health":
                    self._send_json({"ok": True, "schemaVersion": SCHEMA_VERSION, "projectRoot": str(service.workspace.project_root), "revision": service.revision})
                elif path == "/api/workspace":
                    self._send_json(service.workspace.scan())
                elif path == "/api/fonts":
                    self._send_json({"families": service.fonts})
                elif path == "/api/results":
                    results = []
                    for item in sorted(service.paths["requests"].glob("*.result.json"), reverse=True):
                        try:
                            results.append(json.loads(item.read_text(encoding="utf-8")))
                        except (OSError, json.JSONDecodeError):
                            continue
                    self._send_json({"results": results[:20], "undoAvailable": (service.paths["undo"] / "manifest.json").is_file(), "revision": service.revision})
                elif path == "/api/state":
                    self._send_json({"dirtyFileIds": sorted(service.dirty_file_ids), "staleDraftFileIds": sorted(service.stale_draft_file_ids), "locked": service.paths["lock"].exists(), "revision": service.revision})
                elif path.startswith("/api/selected/"):
                    identifier = path.rsplit("/", 1)[-1]
                    selected = service.selected_assets.get(identifier)
                    if not selected or not selected.is_file():
                        self._error(404, "临时图片不存在")
                    else:
                        self._send(200, selected.read_bytes(), mimetypes.guess_type(selected.name)[0] or "application/octet-stream")
                elif path.startswith("/preview/"):
                    parts = path.split("/", 3)
                    identifier = parts[2]
                    relative = parts[3] if len(parts) > 3 else ""
                    self._preview(identifier, relative)
                else:
                    self._error(404, "接口不存在")
            except WorkbenchError as exc:
                self._error(400, str(exc))
            except Exception as exc:  # noqa: BLE001 - 服务端必须返回可诊断错误
                self._error(500, f"服务错误：{exc}")

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urllib.parse.urlsplit(self.path)
            if not self._authorized():
                self._error(403, "实例令牌无效")
                return
            try:
                payload = self._json_body()
                if parsed.path == "/api/workspace/sync":
                    paths = [Path(item) for item in payload.get("paths", [])]
                    self._send_json(service.workspace.scan(paths))
                elif parsed.path == "/api/workspace/preferences":
                    self._send_json(service.workspace.update_preferences(payload))
                    service.bump()
                elif parsed.path == "/api/dialog":
                    kind = payload.get("kind")
                    if kind != "image":
                        raise WorkbenchError("文件选择类型无效")
                    selected = service.dialogs.choose(kind)
                    if not selected:
                        self._send_json({"cancelled": True})
                    else:
                        if selected.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
                            raise WorkbenchError("请选择受支持的图片文件")
                        identifier = uuid.uuid4().hex
                        service.selected_assets[identifier] = selected
                        self._send_json({"cancelled": False, "assetId": identifier, "name": selected.name, "path": str(selected)})
                elif parsed.path == "/api/session/drafts":
                    valid = {item["id"] for item in service.workspace.data["files"]}
                    service.dirty_file_ids = {str(item) for item in payload.get("dirtyFileIds", []) if str(item) in valid}
                    service.stale_draft_file_ids.intersection_update(service.dirty_file_ids)
                    self._send_json({"dirtyFileIds": sorted(service.dirty_file_ids), "staleDraftFileIds": sorted(service.stale_draft_file_ids)})
                elif parsed.path == "/api/requests":
                    self._send_json(service.create_request(payload), 201)
                elif parsed.path == "/api/undo/request":
                    manifest = service.paths["undo"] / "manifest.json"
                    if not manifest.is_file():
                        raise WorkbenchError("没有可撤回的最近一次修改")
                    request = json.loads(manifest.read_text(encoding="utf-8"))
                    instruction = (
                        "请调用 $ycet-prototype-create 撤回原型工作台最近一次 AI 修改。"
                        f"项目根目录：{service.workspace.project_root}；事务 ID：{request.get('requestId')}。"
                        "执行 prototype_workbench.py undo，并报告恢复或冲突文件。"
                    )
                    self._send_json({"instruction": instruction, "requestId": request.get("requestId")})
                else:
                    self._error(404, "接口不存在")
            except WorkbenchError as exc:
                self._error(400, str(exc))
            except Exception as exc:  # noqa: BLE001
                self._error(500, f"服务错误：{exc}")

    return Handler


def read_server_state(project_root: Path) -> dict[str, Any] | None:
    path = state_paths(project_root)["server"]
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def call_api(state: dict[str, Any], path: str, payload: dict[str, Any] | None = None, timeout: float = 2) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        state["url"].rstrip("/") + path,
        data=data,
        headers={"X-YCET-Token": state["token"], "Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def live_state(project_root: Path) -> dict[str, Any] | None:
    state = read_server_state(project_root)
    if not state:
        return None
    try:
        health = call_api(state, "/api/health")
        return state if health.get("ok") and Path(health["projectRoot"]).resolve() == project_root.resolve() else None
    except (OSError, urllib.error.URLError, json.JSONDecodeError, KeyError):
        return None


def command_serve(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    token = args.token or secrets.token_urlsafe(24)
    service = WorkbenchService(project_root, token)
    server = ThreadingHTTPServer((HOST, args.port), handler_factory(service))
    port = server.server_address[1]
    state = {
        "schemaVersion": SCHEMA_VERSION,
        "projectRoot": str(project_root),
        "pid": os.getpid(),
        "port": port,
        "token": token,
        "url": f"http://{HOST}:{port}",
        "startedAt": utc_now(),
    }
    atomic_json(service.paths["server"], state)
    server_thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.25}, name="ycet-workbench-http", daemon=True)
    server_thread.start()
    try:
        while server_thread.is_alive():
            service.dialogs.process_once(timeout=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        service.dialogs.close()
        server.shutdown()
        server_thread.join(timeout=2)
        service.stop()
        server.server_close()
        current = read_server_state(project_root)
        if current and current.get("pid") == os.getpid():
            service.paths["server"].unlink(missing_ok=True)
    return 0


def command_ensure(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    explicit = [str(Path(item).resolve()) for item in (args.add or [])]
    state = live_state(project_root)
    reused = state is not None
    if not state:
        paths = state_paths(project_root)
        paths["root"].mkdir(parents=True, exist_ok=True)
        token = secrets.token_urlsafe(24)
        command = [sys.executable, str(Path(__file__).resolve()), "serve", "--project-root", str(project_root), "--port", "0", "--token", token]
        log = paths["log"].open("a", encoding="utf-8")
        kwargs: dict[str, Any] = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": log, "cwd": str(project_root)}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(command, **kwargs)  # noqa: S603 - 命令仅包含受控解释器和脚本参数
        deadline = time.time() + 8
        while time.time() < deadline:
            time.sleep(0.1)
            state = live_state(project_root)
            if state:
                break
        if not state:
            raise WorkbenchError(f"工作台服务未能启动，请查看日志：{paths['log']}")
    if explicit:
        call_api(state, "/api/workspace/sync", {"paths": explicit})
    url = f"{state['url']}/?token={urllib.parse.quote(state['token'])}"
    opened = False
    if not args.no_open:
        try:
            opened = bool(webbrowser.open(url, new=2))
        except Exception:  # noqa: BLE001
            opened = False
    print(json.dumps({"ok": True, "reused": reused, "opened": opened, "url": url, "pid": state["pid"]}, ensure_ascii=False))
    return 0


def command_status(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    state = live_state(project_root)
    print(json.dumps({"running": bool(state), "state": state}, ensure_ascii=False, indent=2))
    return 0 if state else 1


def command_sync(args: argparse.Namespace) -> int:
    """增量同步文件；实例不存在时按 ensure 的同一规则启动。"""
    proxy = argparse.Namespace(project_root=args.project_root, add=args.add, no_open=args.no_open)
    return command_ensure(proxy)


def request_path(project_root: Path, request_id: str) -> Path:
    return state_paths(project_root)["requests"] / f"{request_id}.json"


def load_request(project_root: Path, request_id: str) -> dict[str, Any]:
    path = request_path(project_root, request_id)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkbenchError(f"请求不存在：{request_id}") from exc


def command_request(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    paths = state_paths(project_root)
    if args.request_action == "list":
        items = []
        for path in sorted(paths["requests"].glob("*.json")):
            if path.name.endswith((".state.json", ".result.json")):
                continue
            try:
                package = json.loads(path.read_text(encoding="utf-8"))
                items.append({"requestId": package.get("requestId"), "createdAt": package.get("createdAt"), "status": package.get("status")})
            except json.JSONDecodeError:
                continue
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0
    package = load_request(project_root, args.request_id)
    if args.request_action == "show":
        print(json.dumps(package, ensure_ascii=False, indent=2))
        return 0
    transaction = paths["transactions"] / args.request_id
    manifest_path = transaction / "manifest.json"
    if args.request_action == "begin":
        if paths["lock"].exists():
            raise WorkbenchError("功能五打包锁已启用")
        entries = []
        before_dir = transaction / "before"
        if transaction.exists():
            raise WorkbenchError("该请求已经开始执行")
        before_dir.mkdir(parents=True)
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in package["files"]:
            key = str(item.get("dependencyGroup") or f"file:{item['fileId']}")
            groups.setdefault(key, []).append(item)
        conflicts = []
        ready_items = []
        for group, items in groups.items():
            invalid = []
            for item in items:
                target = Path(item["path"]).resolve()
                if not target.is_file() or sha256_file(target) != item["sha256"]:
                    invalid.append(item["displayPath"])
            if invalid:
                conflicts.extend({"fileId": item["fileId"], "path": item["displayPath"], "status": "conflict", "reason": f"依赖组摘要冲突：{'；'.join(invalid)}"} for item in items)
            else:
                ready_items.extend(items)
        for item in ready_items:
            target = Path(item["path"]).resolve()
            snapshot = before_dir / f"{item['fileId']}.bin"
            shutil.copy2(target, snapshot)
            entries.append({"fileId": item["fileId"], "source": item["source"], "path": str(target), "beforeExists": True, "beforeSha256": item["sha256"], "snapshot": str(snapshot), "requested": True})
        known_paths = {Path(item["path"]).resolve() for item in entries}
        for raw in getattr(args, "include", None) or []:
            target = Path(raw).resolve()
            if not is_within(target, project_root) or is_within(target, paths["root"]):
                raise WorkbenchError(f"附加事务文件必须位于项目内且不能属于 .ycet-editor：{target}")
            if target in known_paths:
                continue
            identifier = f"extra-{file_id(target)}"
            before_exists = target.is_file()
            snapshot = before_dir / f"{identifier}.bin"
            if before_exists:
                shutil.copy2(target, snapshot)
            entries.append({"fileId": identifier, "source": "project", "path": str(target), "beforeExists": before_exists, "beforeSha256": sha256_file(target) if before_exists else None, "snapshot": str(snapshot) if before_exists else None, "requested": False})
            known_paths.add(target)
        atomic_json(manifest_path, {"schemaVersion": 1, "requestId": args.request_id, "startedAt": utc_now(), "files": entries, "conflicts": conflicts})
        print(json.dumps({"ok": True, "transaction": str(transaction), "readyFileIds": [item["fileId"] for item in entries if item["requested"]], "trackedFiles": [{"fileId": item["fileId"], "path": item["path"]} for item in entries], "conflicts": conflicts}, ensure_ascii=False, indent=2))
        return 0
    if args.request_action == "abort":
        result = {"schemaVersion": 1, "requestId": args.request_id, "completedAt": utc_now(), "status": "aborted", "items": [], "reason": args.reason}
        atomic_json(paths["requests"] / f"{args.request_id}.result.json", result)
        if transaction.exists():
            shutil.rmtree(transaction)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.request_action == "complete":
        if not manifest_path.is_file():
            raise WorkbenchError("请先执行 request begin")
        result_path = Path(args.result).resolve()
        result = json.loads(result_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        reported = {item.get("fileId") for item in result.get("items", [])}
        result.setdefault("items", []).extend(item for item in manifest.get("conflicts", []) if item.get("fileId") not in reported)
        transaction_entries = {item["fileId"]: item for item in manifest["files"]}
        success_items = [item for item in result.get("items", []) if item.get("status") == "success"]
        affected_ids = set()
        for item in success_items:
            affected_ids.add(item.get("fileId"))
            affected_ids.update(str(identifier) for identifier in item.get("affectedFileIds", []))
        unknown = affected_ids - set(transaction_entries)
        if unknown:
            raise WorkbenchError(f"结果包含未纳入事务快照的文件：{sorted(unknown)}")
        changed_ids = set()
        after_by_id: dict[str, str] = {}
        for identifier, entry in transaction_entries.items():
            target = Path(entry["path"])
            after_exists = target.is_file()
            after_sha = sha256_file(target) if after_exists else None
            if after_exists != entry.get("beforeExists", True) or after_sha != entry.get("beforeSha256"):
                changed_ids.add(identifier)
                if after_sha:
                    after_by_id[identifier] = after_sha
        unreported = changed_ids - affected_ids
        if unreported:
            raise WorkbenchError(f"存在已变化但未在成功结果中登记的文件：{sorted(unreported)}")
        undo_files = []
        undo_dir = paths["undo"]
        if undo_dir.exists():
            shutil.rmtree(undo_dir)
        (undo_dir / "before").mkdir(parents=True)
        for item in success_items:
            entry = transaction_entries[item["fileId"]]
            item["beforeSha256"] = entry["beforeSha256"]
            item["afterSha256"] = after_by_id.get(item["fileId"], entry["beforeSha256"])
        for identifier in sorted(changed_ids & affected_ids):
            entry = transaction_entries[identifier]
            target = Path(entry["path"])
            if not target.is_file():
                raise WorkbenchError(f"当前 V1 撤回事务不支持成功操作删除文件：{target}")
            snapshot_target = None
            if entry.get("beforeExists", True):
                snapshot_target = undo_dir / "before" / f"{identifier}.bin"
                shutil.copy2(entry["snapshot"], snapshot_target)
            undo_files.append({**entry, "snapshot": str(snapshot_target) if snapshot_target else None, "afterSha256": after_by_id[identifier]})
        result.update({"schemaVersion": 1, "requestId": args.request_id, "completedAt": utc_now()})
        result["status"] = "success" if success_items and len(success_items) == len(result.get("items", [])) else ("partial" if success_items else "failed")
        atomic_json(paths["requests"] / f"{args.request_id}.result.json", result)
        if undo_files:
            atomic_json(undo_dir / "manifest.json", {"schemaVersion": 1, "requestId": args.request_id, "createdAt": utc_now(), "files": undo_files})
        elif undo_dir.exists():
            shutil.rmtree(undo_dir)
        shutil.rmtree(transaction)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    raise WorkbenchError("未知 request 操作")


def command_undo(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    undo_dir = state_paths(project_root)["undo"]
    manifest_path = undo_dir / "manifest.json"
    if not manifest_path.is_file():
        raise WorkbenchError("没有可撤回的最近一次事务")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    conflicts = []
    for item in manifest["files"]:
        target = Path(item["path"])
        if not target.is_file() or sha256_file(target) != item["afterSha256"]:
            conflicts.append(str(target))
    if conflicts:
        raise WorkbenchError("撤回摘要冲突：" + "；".join(conflicts))
    restored = []
    for item in manifest["files"]:
        target = Path(item["path"])
        if item.get("beforeExists", True):
            atomic_bytes(target, Path(item["snapshot"]).read_bytes())
        else:
            target.unlink()
        restored.append(str(target))
    shutil.rmtree(undo_dir)
    print(json.dumps({"ok": True, "requestId": manifest["requestId"], "restored": restored}, ensure_ascii=False, indent=2))
    return 0


def command_lock(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    path = state_paths(project_root)["lock"]
    if args.lock_action == "status":
        payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        print(json.dumps({"locked": bool(payload), "lock": payload}, ensure_ascii=False, indent=2))
        return 0
    if args.lock_action == "acquire":
        if path.exists():
            raise WorkbenchError("打包锁已经存在")
        state = live_state(project_root)
        if state:
            current = call_api(state, "/api/state")
            if current.get("dirtyFileIds"):
                raise WorkbenchError("相关工作台存在未发送草稿，请先发送或清空")
        token = uuid.uuid4().hex
        atomic_json(path, {"schemaVersion": 1, "token": token, "kind": "mobile-pack", "createdAt": utc_now(), "pid": os.getpid()})
        print(json.dumps({"ok": True, "token": token, "path": str(path)}, ensure_ascii=False))
        return 0
    if args.lock_action == "release":
        if not path.is_file():
            return 0
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("token") != args.token:
            raise WorkbenchError("打包锁令牌不匹配")
        path.unlink()
        print(json.dumps({"ok": True}, ensure_ascii=False))
        return 0
    raise WorkbenchError("未知 lock 操作")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YCET 原型可视化编辑器工作台")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="前台运行本地服务")
    serve.add_argument("--project-root", required=True)
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--token")
    serve.set_defaults(func=command_serve)

    ensure = subparsers.add_parser("ensure", help="复用或启动工作台并同步文件")
    ensure.add_argument("--project-root", required=True)
    ensure.add_argument("--add", action="append")
    ensure.add_argument("--no-open", action="store_true")
    ensure.set_defaults(func=command_ensure)

    status = subparsers.add_parser("status", help="检查项目工作台状态")
    status.add_argument("--project-root", required=True)
    status.set_defaults(func=command_status)

    sync = subparsers.add_parser("sync", help="增量同步 HTML；需要时启动工作台")
    sync.add_argument("--project-root", required=True)
    sync.add_argument("--add", action="append")
    sync.add_argument("--no-open", action="store_true")
    sync.set_defaults(func=command_sync)

    request = subparsers.add_parser("request", help="读取和管理工作台变更包")
    request.add_argument("request_action", choices=("list", "show", "begin", "complete", "abort"))
    request.add_argument("--project-root", required=True)
    request.add_argument("--request-id")
    request.add_argument("--result")
    request.add_argument("--include", action="append", help="begin 时额外纳入事务的项目内文件，可用于图片资源和 EditLog")
    request.add_argument("--reason", default="Agent 中止执行")
    request.set_defaults(func=command_request)

    undo = subparsers.add_parser("undo", help="安全撤回最近一次成功批次")
    undo.add_argument("--project-root", required=True)
    undo.set_defaults(func=command_undo)

    lock = subparsers.add_parser("lock", help="管理功能五打包锁")
    lock.add_argument("lock_action", choices=("acquire", "release", "status"))
    lock.add_argument("--project-root", required=True)
    lock.add_argument("--token")
    lock.set_defaults(func=command_lock)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "request" and args.request_action != "list" and not args.request_id:
        parser.error("request show/begin/complete/abort 必须提供 --request-id")
    if args.command == "request" and args.request_action == "complete" and not args.result:
        parser.error("request complete 必须提供 --result")
    if args.command == "lock" and args.lock_action == "release" and not args.token:
        parser.error("lock release 必须提供 --token")
    try:
        return int(args.func(args))
    except WorkbenchError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
