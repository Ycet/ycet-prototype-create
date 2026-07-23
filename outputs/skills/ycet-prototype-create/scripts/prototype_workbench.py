#!/usr/bin/env python3
"""YCET 原型可视化工作台：本地服务、工作区和变更包。"""

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
ACTIVE_REQUEST_STATUSES = {"pending", "processing"}
TERMINAL_REQUEST_STATUSES = {"success", "partial", "failed", "aborted"}
IGNORED_PROJECT_HTML_DIRS = {".git", ".ycet-editor", "__pycache__", "node_modules", ".venv", "venv", ".cache", ".pytest_cache", ".mypy_cache", ".tox"}
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
        if not self.project_root.is_dir():
            return []
        candidates = [
            path.resolve()
            for path in self.project_root.rglob("*.html")
            if is_within(path, self.project_root)
            and not any(part in IGNORED_PROJECT_HTML_DIRS for part in path.relative_to(self.project_root).parts)
        ]
        return sorted({path.resolve() for path in candidates}, key=lambda item: item.name.casefold())

    def _record(self, path: Path, source: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
        resolved = path.resolve()
        record = dict(existing or {})
        if source == "project":
            project_relative = resolved.relative_to(self.project_root)
            stored_path = project_relative.as_posix()
            if is_within(resolved, self.prototype_root):
                prototype_relative = resolved.relative_to(self.prototype_root).as_posix()
                automatic_group = prototype_relative.split("/", 1)[0] if "/" in prototype_relative else ""
            else:
                parent = project_relative.parent.as_posix()
                automatic_group = "" if parent == "." else parent
        else:
            stored_path = str(resolved)
            automatic_group = ""
        kind = "offline" if re.fullmatch(r"prototype-mobile(?:-v\d+)?\.html", resolved.name) else (
            "runtime" if automatic_group == "runtime-pages" or automatic_group.startswith("runtime-pages/") else "html"
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

    def scan(self, explicit: list[Path] | None = None, restore_hidden: bool = False) -> dict[str, Any]:
        with self._lock:
            before = json.dumps(self.data, ensure_ascii=False, sort_keys=True)
            existing = {item["id"]: item for item in self.data.get("files", [])}
            hidden = set(self.data.get("hiddenProjectPaths", []))
            discovered: list[dict[str, Any]] = []
            for path in self._project_candidates():
                stored = path.relative_to(self.project_root).as_posix()
                if stored in hidden and not restore_hidden:
                    continue
                if restore_hidden:
                    hidden.discard(stored)
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
                source = "project" if is_within(resolved, self.project_root) else "external"
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

    def cleanup_missing(self) -> dict[str, Any]:
        """仅清理工作区中已缺失文件的登记记录，绝不操作磁盘文件。"""
        with self._lock:
            removed = [item["id"] for item in self.data["files"] if item.get("missing")]
            if not removed:
                payload = self.public()
                payload["removedFileIds"] = []
                return payload
            removed_ids = set(removed)
            self.data["files"] = [item for item in self.data["files"] if item["id"] not in removed_ids]
            self.data["zoomByFile"] = {
                identifier: zoom
                for identifier, zoom in self.data.get("zoomByFile", {}).items()
                if identifier not in removed_ids
            }
            if self.data.get("currentFileId") in removed_ids:
                self.data["currentFileId"] = self.data["files"][0]["id"] if self.data["files"] else None
            self.save()
            payload = self.public()
            payload["removedFileIds"] = removed
            return payload

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
            if operation.get("type") == "sync-pages":
                opportunity = next((candidate for candidate in sync_page_opportunities(workspace.project_root, workspace) if candidate["runtimeFileId"] == record["id"]), None)
                if not opportunity:
                    raise WorkbenchError("对应静态页没有尚未同步的成功修改")
                if (
                    operation.get("sourceFileId") != opportunity["sourceFileId"]
                    or operation.get("sourceRequestId") != opportunity["sourceRequestId"]
                    or operation.get("sourceSha256") != opportunity["sourceAfterSha256"]
                ):
                    raise WorkbenchError("同步 pages 草稿与最近一次静态页成功修改不一致")
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
        self._request_lock = threading.RLock()
        self._stop = threading.Event()
        self.shutdown_requested = threading.Event()
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

    def request_shutdown(self) -> None:
        """通知主线程优雅停止服务，避免 HTTP 请求线程直接关闭服务器。"""
        self.shutdown_requested.set()

    def create_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._request_lock:
            if self.paths["lock"].exists():
                raise WorkbenchError("功能五打包锁已启用，暂时不能发送修改")
            if self.stale_draft_file_ids:
                raise WorkbenchError("源文件已变化，必须刷新并重新编辑后才能发送")
            active = active_request_summary(self.workspace.project_root)
            if active:
                raise WorkbenchError(f"请求 {active['requestId'][:8]} 尚未完成，暂时不能再次发送")
            package = validate_request(self.workspace, payload)
            path = request_path(self.workspace.project_root, package["requestId"])
            state_path = request_state_path(self.workspace.project_root, package["requestId"])
            try:
                atomic_json(path, package)
                write_request_state(self.workspace.project_root, package["requestId"], "pending")
            except Exception:
                path.unlink(missing_ok=True)
                state_path.unlink(missing_ok=True)
                raise
            self.dirty_file_ids.clear()
            self.stale_draft_file_ids.clear()
            self.bump()
            summary = request_summary(self.workspace.project_root, package["requestId"])
            return {
                "requestId": package["requestId"],
                "path": str(path),
                "instruction": summary["instruction"],
                "request": summary,
                "revision": self.revision,
            }

    def cancel_request(self, request_id: str) -> dict[str, Any]:
        with self._request_lock:
            summary = cancel_request(self.workspace.project_root, request_id)
            self.bump()
            return summary


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
            allowed_root = service.workspace.project_root if root_record["source"] == "project" else root_path.parent
            relative = urllib.parse.unquote(relative or "")
            # 预览路由以项目根为 URL 边界，保留原 HTML 的目录层级和相对资源语义。
            target = (allowed_root / relative).resolve() if relative else root_path
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
            parent_relative = target.parent.relative_to(allowed_root).as_posix()
            parent_route = "" if parent_relative == "." else urllib.parse.quote(parent_relative, safe="/") + "/"
            payload = inject_runtime(text, config, f"/preview/{identifier}/{parent_route}")
            # 仅兼容历史产物使用的官方 Tailwind CDN；新生成页面必须使用本地或内联 CSS。
            csp = (
                "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: https://cdn.tailwindcss.com; "
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
                elif path == "/api/requests":
                    summaries = list_request_summaries(service.workspace.project_root)
                    self._send_json({
                        "activeRequest": next((item for item in summaries if item["status"] in ACTIVE_REQUEST_STATUSES), None),
                        "requests": summaries[:20],
                        "syncPages": sync_page_opportunities(service.workspace.project_root, service.workspace),
                        "revision": service.revision,
                    })
                elif path == "/api/results":
                    self._send_json({"results": list_request_results(service.workspace.project_root)[:20], "revision": service.revision})
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
                    # 仅用户点击刷新时恢复此前从工作台移除、但磁盘仍存在的项目 HTML。
                    self._send_json(service.workspace.scan(paths, restore_hidden=payload.get("restoreHidden") is True))
                elif parsed.path == "/api/workspace/cleanup-missing":
                    cleaned = service.workspace.cleanup_missing()
                    removed = set(cleaned["removedFileIds"])
                    service.dirty_file_ids.difference_update(removed)
                    service.stale_draft_file_ids.difference_update(removed)
                    if removed:
                        service.bump()
                    self._send_json(cleaned)
                elif parsed.path == "/api/workspace/remove":
                    identifier = str(payload.get("fileId", ""))
                    if not identifier:
                        raise WorkbenchError("缺少待移除的文件 ID")
                    workspace = service.workspace.remove(identifier)
                    service.dirty_file_ids.discard(identifier)
                    service.stale_draft_file_ids.discard(identifier)
                    service.bump()
                    self._send_json(workspace)
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
                elif parsed.path == "/api/shutdown":
                    self._send_json({"ok": True, "shuttingDown": True}, 202)
                    service.request_shutdown()
                elif re.fullmatch(r"/api/requests/[^/]+/cancel", parsed.path):
                    request_id = urllib.parse.unquote(parsed.path.split("/")[-2])
                    self._send_json({"request": service.cancel_request(request_id), "revision": service.revision})
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
        while server_thread.is_alive() and not service.shutdown_requested.is_set():
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
        with paths["log"].open("a", encoding="utf-8") as log:
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
    # 即使未显式传入文件，也要在复用实例时重新扫描项目，补入功能一、三、四、五刚生成的 HTML。
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
    """增量登记文件；仅复用功能二已启动的工作台，绝不自行打开服务。"""
    project_root = Path(args.project_root).resolve()
    explicit = [Path(item).resolve() for item in (args.add or [])]
    if live_state(project_root):
        proxy = argparse.Namespace(project_root=args.project_root, add=args.add, no_open=args.no_open)
        return command_ensure(proxy)
    workspace = Workspace(project_root)
    payload = workspace.scan(explicit)
    print(json.dumps({"ok": True, "reused": False, "opened": False, "running": False, "files": len(payload["files"])}, ensure_ascii=False))
    return 0


def request_path(project_root: Path, request_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", request_id) or request_id in {".", ".."}:
        raise WorkbenchError("请求 ID 无效")
    return state_paths(project_root)["requests"] / f"{request_id}.json"


def request_state_path(project_root: Path, request_id: str) -> Path:
    request_path(project_root, request_id)
    return state_paths(project_root)["requests"] / f"{request_id}.state.json"


def request_result_path(project_root: Path, request_id: str) -> Path:
    request_path(project_root, request_id)
    return state_paths(project_root)["requests"] / f"{request_id}.result.json"


def load_request(project_root: Path, request_id: str) -> dict[str, Any]:
    path = request_path(project_root, request_id)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkbenchError(f"请求不存在：{request_id}") from exc


def load_request_state(project_root: Path, request_id: str) -> dict[str, Any]:
    """读取动态状态；旧请求按结果文件和事务目录推导，保持向后兼容。"""
    package = load_request(project_root, request_id)
    state_path = request_state_path(project_root, request_id)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        status = state.get("status")
        if status not in ACTIVE_REQUEST_STATUSES | TERMINAL_REQUEST_STATUSES:
            raise WorkbenchError(f"请求状态无效：{status}")
        return state
    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, OSError) as exc:
        raise WorkbenchError(f"请求状态文件无效：{request_id}") from exc

    result_path = request_result_path(project_root, request_id)
    if result_path.is_file():
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise WorkbenchError(f"请求结果文件无效：{request_id}") from exc
        status = result.get("status", "failed")
        if status not in TERMINAL_REQUEST_STATUSES:
            status = "failed"
        return {
            "schemaVersion": SCHEMA_VERSION,
            "requestId": request_id,
            "status": status,
            "createdAt": package.get("createdAt"),
            "completedAt": result.get("completedAt"),
            "reason": result.get("reason"),
        }
    manifest = state_paths(project_root)["transactions"] / request_id / "manifest.json"
    if manifest.is_file():
        try:
            started_at = json.loads(manifest.read_text(encoding="utf-8")).get("startedAt")
        except (json.JSONDecodeError, OSError):
            started_at = None
        return {
            "schemaVersion": SCHEMA_VERSION,
            "requestId": request_id,
            "status": "processing",
            "createdAt": package.get("createdAt"),
            "startedAt": started_at,
        }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "requestId": request_id,
        "status": "pending",
        "createdAt": package.get("createdAt"),
    }


def write_request_state(project_root: Path, request_id: str, status: str, **updates: Any) -> dict[str, Any]:
    if status not in ACTIVE_REQUEST_STATUSES | TERMINAL_REQUEST_STATUSES:
        raise WorkbenchError(f"请求状态无效：{status}")
    package = load_request(project_root, request_id)
    try:
        current = json.loads(request_state_path(project_root, request_id).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        current = {}
    state = {
        "schemaVersion": SCHEMA_VERSION,
        "requestId": request_id,
        "createdAt": current.get("createdAt") or package.get("createdAt") or utc_now(),
        **current,
        "status": status,
        **{key: value for key, value in updates.items() if value is not None},
    }
    atomic_json(request_state_path(project_root, request_id), state)
    return state


def request_summary(project_root: Path, request_id: str) -> dict[str, Any]:
    package = load_request(project_root, request_id)
    state = load_request_state(project_root, request_id)
    files = package.get("files", [])
    locked_file_ids = {item["fileId"] for item in files}
    for item in files:
        locked_file_ids.update(
            str(operation["sourceFileId"])
            for operation in item.get("operations", [])
            if operation.get("type") == "sync-pages" and operation.get("sourceFileId")
        )
    return {
        "requestId": request_id,
        "status": state["status"],
        "createdAt": state.get("createdAt") or package.get("createdAt"),
        "startedAt": state.get("startedAt"),
        "completedAt": state.get("completedAt"),
        "reason": state.get("reason"),
        "fileIds": sorted(locked_file_ids),
        "fileCount": len(files),
        "operationCount": sum(len(item.get("operations", [])) for item in files),
        "instruction": request_instruction(project_root.resolve(), request_id),
    }


def request_packages(project_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    """只返回文件名与包内 requestId 一致的正式请求，忽略 Agent 临时结果文件。"""
    packages = []
    for path in state_paths(project_root)["requests"].glob("*.json"):
        try:
            package = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        request_id = path.name.removesuffix(".json")
        if package.get("requestId") != request_id or not isinstance(package.get("files"), list):
            continue
        packages.append((path, package))
    return packages


def list_request_summaries(project_root: Path) -> list[dict[str, Any]]:
    summaries = []
    for path, _package in request_packages(project_root):
        try:
            summaries.append(request_summary(project_root, path.name.removesuffix(".json")))
        except WorkbenchError:
            continue
    return sorted(summaries, key=lambda item: item.get("createdAt") or "", reverse=True)


def list_request_results(project_root: Path) -> list[dict[str, Any]]:
    """按正式请求读取结果，防止 *.result.pending.json 被当成请求或结果。"""
    results = []
    for _path, package in request_packages(project_root):
        request_id = package["requestId"]
        path = request_result_path(project_root, request_id)
        if not path.is_file():
            continue
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if result.get("requestId") == request_id:
            results.append(result)
    return sorted(results, key=lambda item: item.get("completedAt") or "", reverse=True)


def sync_page_opportunities(project_root: Path, workspace: Workspace) -> list[dict[str, Any]]:
    """返回尚未同步到运行时页的最近一次真实静态页修改。"""
    records = {item["id"]: item for item in workspace.data["files"]}
    events = []
    for _path, package in request_packages(project_root):
        result_path = request_result_path(project_root, package["requestId"])
        if not result_path.is_file():
            continue
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if result.get("status") not in {"success", "partial"}:
            continue
        events.append((result.get("completedAt") or "", package, result))

    latest_changes: dict[str, dict[str, Any]] = {}
    successful_syncs: dict[tuple[str, str], tuple[str | None, str | None]] = {}
    for _completed_at, package, result in sorted(events, key=lambda item: item[0]):
        success_items = {str(item.get("fileId")): item for item in result.get("items", []) if item.get("status") == "success"}
        for file_item in package.get("files", []):
            file_id_value = str(file_item.get("fileId"))
            result_item = success_items.get(file_id_value)
            if not result_item:
                continue
            record = records.get(file_id_value)
            if record and record.get("automaticGroup") == "pages":
                before_sha = result_item.get("beforeSha256")
                after_sha = result_item.get("afterSha256")
                if before_sha and after_sha and before_sha != after_sha:
                    preview_operations = [
                        {key: value for key, value in operation.items() if key not in {"fileId", "_key", "previewUrl"}}
                        for operation in file_item.get("operations", [])
                        if operation.get("type") in {"style", "css", "text"}
                    ]
                    latest_changes[file_id_value] = {
                        "sourceRequestId": package["requestId"],
                        "sourceBeforeSha256": before_sha,
                        "sourceAfterSha256": after_sha,
                        "previewOperations": preview_operations,
                    }
                else:
                    # 最近一次成功任务没有真实改写该静态页时，不沿用更早批次的同步入口。
                    latest_changes.pop(file_id_value, None)
            for operation in file_item.get("operations", []):
                if operation.get("type") != "sync-pages":
                    continue
                source_id = str(operation.get("sourceFileId") or "")
                successful_syncs[(file_id_value, source_id)] = (
                    operation.get("sourceRequestId"),
                    operation.get("sourceSha256"),
                )

    opportunities = []
    pages_by_name = {
        item["name"]: item
        for item in workspace.data["files"]
        if item.get("automaticGroup") == "pages" and not item.get("missing")
    }
    for runtime in workspace.data["files"]:
        if runtime.get("automaticGroup") != "runtime-pages" or runtime.get("missing"):
            continue
        source_name = re.sub(r"--[^.]+(?=\.html$)", "", runtime["name"])
        source = pages_by_name.get(source_name)
        if not source:
            continue
        change = latest_changes.get(source["id"])
        if not change or source.get("sha256") != change["sourceAfterSha256"]:
            continue
        synced_request_id, synced_source_sha = successful_syncs.get((runtime["id"], source["id"]), (None, None))
        if synced_request_id == change["sourceRequestId"] or synced_source_sha == change["sourceAfterSha256"]:
            continue
        opportunities.append({
            "runtimeFileId": runtime["id"],
            "sourceFileId": source["id"],
            "sourcePath": source["path"],
            "runtimePath": runtime["path"],
            **change,
        })
    return opportunities


def active_request_summary(project_root: Path) -> dict[str, Any] | None:
    return next((item for item in list_request_summaries(project_root) if item["status"] in ACTIVE_REQUEST_STATUSES), None)


def cancel_request(project_root: Path, request_id: str) -> dict[str, Any]:
    transaction = state_paths(project_root)["transactions"] / request_id
    try:
        transaction.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise WorkbenchError("请求已被 Agent 领取，不能从工作台取消") from exc
    try:
        state = load_request_state(project_root, request_id)
        if state["status"] != "pending":
            raise WorkbenchError("只有等待 Agent 领取的请求可以从工作台取消")
        completed_at = utc_now()
        result = {
            "schemaVersion": SCHEMA_VERSION,
            "requestId": request_id,
            "completedAt": completed_at,
            "status": "aborted",
            "items": [],
            "reason": "用户在 Agent 领取前取消请求",
        }
        atomic_json(request_result_path(project_root, request_id), result)
        write_request_state(project_root, request_id, "aborted", completedAt=completed_at, reason=result["reason"])
        return request_summary(project_root, request_id)
    finally:
        shutil.rmtree(transaction, ignore_errors=True)


def command_request(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    paths = state_paths(project_root)
    if args.request_action == "list":
        print(json.dumps(list_request_summaries(project_root), ensure_ascii=False, indent=2))
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
        try:
            transaction.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise WorkbenchError("该请求已经开始执行") from exc
        entries = []
        conflicts = []
        try:
            state = load_request_state(project_root, args.request_id)
            if state["status"] != "pending":
                raise WorkbenchError(f"请求状态为 {state['status']}，不能重复领取")
            active = active_request_summary(project_root)
            if active and active["requestId"] != args.request_id:
                raise WorkbenchError(f"请求 {active['requestId'][:8]} 尚未完成，请先处理该请求")
            before_dir = transaction / "before"
            before_dir.mkdir()
            groups: dict[str, list[dict[str, Any]]] = {}
            for item in package["files"]:
                key = str(item.get("dependencyGroup") or f"file:{item['fileId']}")
                groups.setdefault(key, []).append(item)
            ready_items = []
            for _group, items in groups.items():
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
            started_at = utc_now()
            atomic_json(manifest_path, {"schemaVersion": 1, "requestId": args.request_id, "startedAt": started_at, "files": entries, "conflicts": conflicts})
            write_request_state(project_root, args.request_id, "processing", startedAt=started_at)
        except Exception:
            shutil.rmtree(transaction, ignore_errors=True)
            raise
        print(json.dumps({"ok": True, "transaction": str(transaction), "readyFileIds": [item["fileId"] for item in entries if item["requested"]], "trackedFiles": [{"fileId": item["fileId"], "path": item["path"]} for item in entries], "conflicts": conflicts}, ensure_ascii=False, indent=2))
        return 0
    if args.request_action == "abort":
        state = load_request_state(project_root, args.request_id)
        if state["status"] not in ACTIVE_REQUEST_STATUSES:
            raise WorkbenchError(f"请求状态为 {state['status']}，不能中止")
        completed_at = utc_now()
        result = {"schemaVersion": 1, "requestId": args.request_id, "completedAt": completed_at, "status": "aborted", "items": [], "reason": args.reason}
        atomic_json(request_result_path(project_root, args.request_id), result)
        write_request_state(project_root, args.request_id, "aborted", completedAt=completed_at, reason=args.reason)
        if transaction.exists():
            shutil.rmtree(transaction)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.request_action == "complete":
        state = load_request_state(project_root, args.request_id)
        if state["status"] != "processing":
            raise WorkbenchError(f"请求状态为 {state['status']}，不能完成")
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
        for item in success_items:
            entry = transaction_entries[item["fileId"]]
            item["beforeSha256"] = entry["beforeSha256"]
            item["afterSha256"] = after_by_id.get(item["fileId"], entry["beforeSha256"])
        result.update({"schemaVersion": 1, "requestId": args.request_id, "completedAt": utc_now()})
        result["status"] = "success" if success_items and len(success_items) == len(result.get("items", [])) else ("partial" if success_items else "failed")
        atomic_json(request_result_path(project_root, args.request_id), result)
        write_request_state(project_root, args.request_id, result["status"], completedAt=result["completedAt"])
        shutil.rmtree(transaction)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    raise WorkbenchError("未知 request 操作")


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

    sync = subparsers.add_parser("sync", help="增量登记 HTML；不会启动工作台")
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
