#!/usr/bin/env python3
"""原型可视化编辑器工作区、服务与变更包回归测试。"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import urllib.error
import urllib.parse
import urllib.request
import warnings
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("prototype_workbench.py")
SPEC = importlib.util.spec_from_file_location("prototype_workbench", SCRIPT)
assert SPEC and SPEC.loader
workbench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workbench)


def write(path: Path, copy: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(copy, encoding="utf-8")
    return path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RunningService:
    def __init__(self, root: Path, token: str = "test-token"):
        self.service = workbench.WorkbenchService(root, token)
        self.server = workbench.ThreadingHTTPServer((workbench.HOST, 0), workbench.handler_factory(self.service))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://{workbench.HOST}:{self.server.server_address[1]}"
        self.token = token
        workbench.atomic_json(
            self.service.paths["server"],
            {"schemaVersion": 1, "projectRoot": str(root), "pid": os.getpid(), "port": self.server.server_address[1], "token": token, "url": self.url},
        )

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.service.stop()
        self.thread.join(timeout=2)

    def request(self, path: str, payload: dict | None = None, token: str | None = "test-token", host: str | None = None):
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["X-YCET-Token"] = token
        if host:
            headers["Host"] = host
        request = urllib.request.Request(self.url + path, data=body, headers=headers, method="POST" if payload is not None else "GET")
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, dict(response.headers), json.loads(response.read()) if response.headers.get_content_type() == "application/json" else response.read()


class WorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.prototype = self.root / "prototype"
        self.index = write(self.prototype / "index.html", "<!doctype html><title>index</title>")
        self.home = write(self.prototype / "pages" / "home.html", "<!doctype html><button id='buy'>购买</button>")
        self.runtime = write(self.prototype / "runtime-pages" / "home--prototype.html", "<!doctype html><script>const type='navigate'</script>")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_scan_groups_sort_and_workspace_location(self) -> None:
        workspace = workbench.Workspace(self.root)
        records = workspace.public()["files"]
        self.assertEqual([item["name"] for item in records], ["index.html", "home.html", "home--prototype.html"])
        self.assertEqual({item["automaticGroup"] for item in records}, {"", "pages", "runtime-pages"})
        self.assertTrue((self.root / ".ycet-editor" / "workspace.json").is_file())
        self.assertFalse((self.prototype / ".ycet-editor").exists())

    def test_external_registration_and_remove_never_deletes(self) -> None:
        with tempfile.TemporaryDirectory() as external_root:
            external = write(Path(external_root) / "external.html", "<p>outside</p>")
            workspace = workbench.Workspace(self.root)
            payload = workspace.scan([external])
            record = next(item for item in payload["files"] if item["source"] == "external")
            workspace.remove(record["id"])
            self.assertTrue(external.is_file())
            self.assertNotIn(record["id"], {item["id"] for item in workspace.public()["files"]})

    def test_project_remove_hides_without_delete_and_explicit_add_restores(self) -> None:
        workspace = workbench.Workspace(self.root)
        record = next(item for item in workspace.data["files"] if item["name"] == "home.html")
        workspace.remove(record["id"])
        self.assertTrue(self.home.is_file())
        self.assertNotIn(record["id"], {item["id"] for item in workspace.scan()["files"]})
        self.assertIn(record["id"], {item["id"] for item in workspace.scan([self.home])["files"]})

    def test_missing_registered_file_remains_visible(self) -> None:
        workspace = workbench.Workspace(self.root)
        identifier = next(item["id"] for item in workspace.data["files"] if item["name"] == "home.html")
        self.home.unlink()
        record = next(item for item in workspace.scan()["files"] if item["id"] == identifier)
        self.assertTrue(record["missing"])
        self.assertIsNone(record["sha256"])

    def test_cleanup_missing_only_removes_missing_workspace_records(self) -> None:
        workspace = workbench.Workspace(self.root)
        self.home.unlink()
        workspace.scan()

        cleaned = workspace.cleanup_missing()

        self.assertEqual(cleaned["removedFileIds"], [workbench.file_id(self.home.resolve())])
        self.assertFalse(any(item["missing"] for item in cleaned["files"]))
        self.assertTrue(self.index.is_file(), "清理缺失记录不得删除仍存在的源 HTML")

    def test_remove_only_removes_workspace_record(self) -> None:
        workspace = workbench.Workspace(self.root)
        record = next(item for item in workspace.data["files"] if item["name"] == "home.html")
        workspace.remove(record["id"])
        self.assertTrue(self.home.is_file(), "移除工作台文件不得删除本地 HTML")
        self.assertNotIn(record["id"], {item["id"] for item in workspace.public()["files"]})

    def test_manual_groups_order_and_zoom_persist(self) -> None:
        workspace = workbench.Workspace(self.root)
        home = next(item for item in workspace.data["files"] if item["name"] == "home.html")
        index = next(item for item in workspace.data["files"] if item["name"] == "index.html")
        workspace.update_preferences(
            {"groups": [{"id": "manual", "name": "营销"}], "assignments": {home["id"]: "manual"}, "order": [home["id"], index["id"]], "currentFileId": home["id"], "zoomByFile": {home["id"]: 135}}
        )
        restored = workbench.Workspace(self.root).public()
        restored_home = next(item for item in restored["files"] if item["id"] == home["id"])
        self.assertEqual(restored_home["manualGroup"], "manual")
        self.assertEqual(restored["zoomByFile"][home["id"]], 135)

    def test_sync_without_running_workbench_never_starts_service(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = workbench.command_sync(argparse.Namespace(project_root=str(self.root), add=[], no_open=True))
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertFalse(payload["running"])
        self.assertFalse((self.root / ".ycet-editor" / "server.json").exists())


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = write(self.root / "prototype" / "pages" / "home.html", "<!doctype html><button id='buy'>购买</button>")
        self.original_sha = digest(self.home)
        self.running = RunningService(self.root)

    def tearDown(self) -> None:
        self.running.close()
        self.temp.cleanup()

    def test_token_host_cookie_and_preview_injection(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as denied:
            self.running.request("/api/health", token=None)
        self.assertEqual(denied.exception.code, 403)
        denied.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as denied_host:
            self.running.request("/api/health", host="evil.example")
        self.assertEqual(denied_host.exception.code, 403)
        denied_host.exception.close()

        request = urllib.request.Request(f"{self.running.url}/?token={self.running.token}")
        with urllib.request.urlopen(request) as response:
            self.assertIn("HttpOnly", response.headers["Set-Cookie"])
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        file_id = self.running.service.workspace.data["files"][0]["id"]
        request = urllib.request.Request(f"{self.running.url}/preview/{file_id}/", headers={"X-YCET-Token": self.running.token})
        with urllib.request.urlopen(request) as response:
            body = response.read().decode()
            self.assertIn("preview-runtime.js", body)
            self.assertIn("Content-Security-Policy", response.headers)
        self.assertEqual(digest(self.home), self.original_sha)

    def test_preview_allows_the_legacy_tailwind_cdn(self) -> None:
        """旧页面仍使用官方 Tailwind CDN 时，预览不得被工作台 CSP 拦截。"""
        self.home.write_text(
            "<!doctype html><script src='https://cdn.tailwindcss.com'></script><main class='hidden'>内容</main>",
            encoding="utf-8",
        )
        file_id = self.running.service.workspace.data["files"][0]["id"]
        request = urllib.request.Request(
            f"{self.running.url}/preview/{file_id}/",
            headers={"X-YCET-Token": self.running.token},
        )
        with urllib.request.urlopen(request) as response:
            self.assertIn("https://cdn.tailwindcss.com", response.headers["Content-Security-Policy"])

    def test_remove_endpoint_keeps_source_html(self) -> None:
        record = self.running.service.workspace.data["files"][0]
        status, _headers, payload = self.running.request("/api/workspace/remove", {"fileId": record["id"]})
        self.assertEqual(status, 200)
        self.assertTrue(self.home.is_file())
        self.assertNotIn(record["id"], {item["id"] for item in payload["files"]})

    def test_refresh_recursively_scans_project_and_restores_removed_html(self) -> None:
        """用户主动刷新时，项目内未展示的 HTML 应重新加入工作台。"""
        nested = write(self.root / "docs" / "flows" / "prototype-note.html", "<!doctype html><p>流程说明</p>")
        record = self.running.service.workspace.data["files"][0]
        self.running.request("/api/workspace/remove", {"fileId": record["id"]})

        status, _headers, payload = self.running.request("/api/workspace/sync", {"restoreHidden": True})

        self.assertEqual(status, 200)
        paths = {item["path"] for item in payload["files"]}
        self.assertIn("prototype/pages/home.html", paths)
        self.assertIn("docs/flows/prototype-note.html", paths)
        self.assertTrue(nested.is_file())

    def test_function_four_page_loads_relative_image_from_prototype_assets(self) -> None:
        image = self.root / "prototype" / "assets" / "images" / "poster.png"
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"function-four-image")
        self.home.write_text("<!doctype html><img src='../assets/images/poster.png' alt='图片原型'>", encoding="utf-8")
        file_id = self.running.service.workspace.data["files"][0]["id"]
        preview_url = f"{self.running.url}/preview/{file_id}/"
        request = urllib.request.Request(preview_url, headers={"X-YCET-Token": self.running.token})
        with urllib.request.urlopen(request, timeout=3) as response:
            html = response.read().decode("utf-8")

        class BaseParser(HTMLParser):
            href: str | None = None

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                if tag == "base":
                    self.href = dict(attrs).get("href")

        parser = BaseParser()
        parser.feed(html)
        self.assertIsNotNone(parser.href, "预览响应缺少资源解析基准")
        document_base = urllib.parse.urljoin(preview_url, parser.href)
        image_url = urllib.parse.urljoin(document_base, "../assets/images/poster.png")
        image_request = urllib.request.Request(image_url, headers={"X-YCET-Token": self.running.token})
        with urllib.request.urlopen(image_request, timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), image.read_bytes())
        self.assertEqual(self.home.read_text(encoding="utf-8"), "<!doctype html><img src='../assets/images/poster.png' alt='图片原型'>")

    def test_path_traversal_is_rejected(self) -> None:
        file_id = self.running.service.workspace.data["files"][0]["id"]
        request = urllib.request.Request(f"{self.running.url}/preview/{file_id}/../../outside.txt", headers={"X-YCET-Token": self.running.token})
        with self.assertRaises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(request)
        self.assertEqual(denied.exception.code, 404)
        denied.exception.close()

    def test_system_fonts_endpoint_returns_service_font_families(self) -> None:
        self.running.service.fonts = ["Arial", "Inter", "Microsoft YaHei"]
        status, _headers, body = self.running.request("/api/fonts")
        self.assertEqual(status, 200)
        self.assertEqual(body["families"], ["Arial", "Inter", "Microsoft YaHei"])
        self.assertEqual(workbench._font_family_names("Artifakt Element Bold (True Type)"), ["Artifakt Element"])

    def test_file_dialog_is_parented_and_brought_to_front(self) -> None:
        selected = self.root / "selected.png"
        events: list[object] = []
        root_instance = None

        class FakeRoot:
            def __init__(self) -> None:
                nonlocal root_instance
                root_instance = self

            def withdraw(self) -> None:
                events.append("withdraw")

            def attributes(self, name: str, value: bool) -> None:
                events.append(("attributes", name, value))

            def update_idletasks(self) -> None:
                events.append("update_idletasks")

            def destroy(self) -> None:
                events.append("destroy")

        tkinter_module = types.ModuleType("tkinter")
        filedialog_module = types.ModuleType("tkinter.filedialog")
        tkinter_module.Tk = FakeRoot

        def askopenfilename(**kwargs):
            events.append(("askopenfilename", kwargs))
            return str(selected)

        filedialog_module.askopenfilename = askopenfilename
        tkinter_module.filedialog = filedialog_module
        previous = os.environ.pop("YCET_WORKBENCH_DIALOG_PATH", None)
        try:
            with mock.patch.dict(sys.modules, {"tkinter": tkinter_module, "tkinter.filedialog": filedialog_module}):
                result = workbench.choose_file("image")
        finally:
            if previous is not None:
                os.environ["YCET_WORKBENCH_DIALOG_PATH"] = previous

        self.assertEqual(result, selected.resolve())
        self.assertIn("update_idletasks", events)
        dialog_event = next(item for item in events if isinstance(item, tuple) and item[0] == "askopenfilename")
        self.assertIs(dialog_event[1].get("parent"), root_instance)
        self.assertIn(("attributes", "-topmost", True), events)
        self.assertEqual(events[-1], "destroy")

    def test_image_dialog_override_registers_asset_without_copy(self) -> None:
        external = write(self.root / "replacement.png", "png")
        previous = os.environ.get("YCET_WORKBENCH_DIALOG_PATH")
        os.environ["YCET_WORKBENCH_DIALOG_PATH"] = str(external)
        try:
            status, _headers, body = self.running.request("/api/dialog", {"kind": "image"})
        finally:
            if previous is None:
                os.environ.pop("YCET_WORKBENCH_DIALOG_PATH", None)
            else:
                os.environ["YCET_WORKBENCH_DIALOG_PATH"] = previous
        self.assertEqual(status, 200)
        self.assertFalse(body["cancelled"])
        self.assertEqual(body["name"], "replacement.png")
        self.assertEqual(Path(body["path"]), external.resolve())
        self.assertTrue(body["assetId"] in self.running.service.selected_assets)

    def test_html_dialog_kind_is_not_exposed(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as denied:
            self.running.request("/api/dialog", {"kind": "html"})
        self.assertEqual(denied.exception.code, 400)
        denied.exception.close()

    def test_dialog_chooser_runs_on_main_thread(self) -> None:
        external = write(self.root / "main-thread.png", "png")
        main_thread_id = threading.get_ident()
        original = workbench.choose_file
        outcome: dict[str, object] = {}

        def main_thread_only(_kind: str) -> Path:
            if threading.get_ident() != main_thread_id:
                raise RuntimeError("main thread is not in main loop")
            return external

        def request_dialog() -> None:
            try:
                outcome["response"] = self.running.request("/api/dialog", {"kind": "image"})
            except Exception as exc:  # noqa: BLE001 - 测试需要保留服务端原始错误
                outcome["error"] = exc

        workbench.choose_file = main_thread_only
        worker = threading.Thread(target=request_dialog)
        try:
            worker.start()
            deadline = time.time() + 3
            while worker.is_alive() and time.time() < deadline:
                dialogs = getattr(self.running.service, "dialogs", None)
                if dialogs:
                    dialogs.process_once(timeout=0.05)
                else:
                    time.sleep(0.01)
            worker.join(timeout=1)
        finally:
            workbench.choose_file = original
        self.assertFalse(worker.is_alive(), "文件对话框请求没有完成")
        self.assertNotIn("error", outcome, f"文件选择器仍在 HTTP 工作线程执行：{outcome.get('error')}")
        status, _headers, body = outcome["response"]
        self.assertEqual(status, 200)
        self.assertFalse(body["cancelled"])

    def test_watcher_marks_changed_dirty_file_stale(self) -> None:
        file_id = self.running.service.workspace.data["files"][0]["id"]
        self.running.request("/api/session/drafts", {"dirtyFileIds": [file_id]})
        self.home.write_text("<button id='buy'>已变化</button>", encoding="utf-8")
        deadline = time.time() + 4
        while time.time() < deadline and file_id not in self.running.service.stale_draft_file_ids:
            time.sleep(0.1)
        self.assertIn(file_id, self.running.service.stale_draft_file_ids)

    def test_ensure_reuses_live_instance(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = workbench.command_ensure(argparse.Namespace(project_root=str(self.root), add=[], no_open=True))
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(payload["reused"])
        self.assertEqual(payload["pid"], os.getpid())

    def test_ensure_reused_instance_always_scans_project_files(self) -> None:
        original_call_api = workbench.call_api
        calls: list[tuple[str, dict | None]] = []

        def record_call(state, path, payload=None, timeout=2):
            calls.append((path, payload))
            return original_call_api(state, path, payload, timeout)

        with mock.patch.object(workbench, "call_api", side_effect=record_call), contextlib.redirect_stdout(io.StringIO()):
            workbench.command_ensure(argparse.Namespace(project_root=str(self.root), add=[], no_open=True))

        self.assertIn(("/api/workspace/sync", {"paths": []}), calls)

    def test_shutdown_requires_token_and_requests_graceful_stop(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as denied:
            self.running.request("/api/shutdown", {}, token="wrong-token")
        self.assertEqual(denied.exception.code, 403)
        denied.exception.close()
        cross_origin = urllib.request.Request(
            self.running.url + "/api/shutdown",
            data=b"{}",
            headers={"Content-Type": "application/json", "X-YCET-Token": self.running.token, "Origin": "https://evil.example"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as denied_origin:
            urllib.request.urlopen(cross_origin, timeout=3)
        self.assertEqual(denied_origin.exception.code, 403)
        denied_origin.exception.close()
        self.assertFalse(self.running.service.shutdown_requested.is_set())

        status, _headers, body = self.running.request("/api/shutdown", {})
        self.assertEqual(status, 202)
        self.assertEqual(body, {"ok": True, "shuttingDown": True})
        deadline = time.time() + 1
        while time.time() < deadline and not self.running.service.shutdown_requested.is_set():
            time.sleep(0.01)
        self.assertTrue(self.running.service.shutdown_requested.is_set())

    def test_request_api_reports_and_cancels_pending_request(self) -> None:
        record = self.running.service.workspace.data["files"][0]
        payload = {
            "schemaVersion": 1,
            "files": [{
                "fileId": record["id"],
                "sha256": record["sha256"],
                "operations": [{"type": "annotation", "text": "调整按钮"}],
            }],
        }
        status, _headers, created = self.running.request("/api/requests", payload)
        self.assertEqual(status, 201)
        self.assertEqual(created["request"]["status"], "pending")
        self.assertEqual(created["request"]["fileCount"], 1)
        self.assertEqual(created["request"]["operationCount"], 1)

        _status, _headers, listing = self.running.request("/api/requests")
        self.assertEqual(listing["activeRequest"]["requestId"], created["requestId"])
        self.assertEqual(listing["activeRequest"]["fileIds"], [record["id"]])

        status, _headers, cancelled = self.running.request(f"/api/requests/{created['requestId']}/cancel", {})
        self.assertEqual(status, 200)
        self.assertEqual(cancelled["request"]["status"], "aborted")
        _status, _headers, listing = self.running.request("/api/requests")
        self.assertIsNone(listing["activeRequest"])

    def test_request_api_releases_success_when_agent_scratch_result_remains(self) -> None:
        record = self.running.service.workspace.data["files"][0]
        status, _headers, created = self.running.request("/api/requests", {
            "schemaVersion": 1,
            "files": [{
                "fileId": record["id"],
                "sha256": record["sha256"],
                "operations": [{"type": "style", "property": "color", "value": "red"}],
            }],
        })
        self.assertEqual(status, 201)
        request_id = created["requestId"]
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=request_id, request_action="begin", result=None, reason=""))
        self.home.write_text("<button id='buy' style='color:red'>购买</button>", encoding="utf-8")
        scratch = self.running.service.paths["requests"] / f"{request_id}.result.pending.json"
        scratch.write_text(json.dumps({"items": [{"fileId": record["id"], "status": "success"}]}), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=request_id, request_action="complete", result=str(scratch), reason=""))

        _status, _headers, listing = self.running.request("/api/requests")
        self.assertIsNone(listing["activeRequest"])
        self.assertEqual(listing["requests"][0]["status"], "success")

    def test_removed_undo_endpoint_returns_not_found(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as denied:
            self.running.request("/api/undo/request", {})
        self.assertEqual(denied.exception.code, 404)
        denied.exception.close()

    def test_cleanup_missing_endpoint_only_prunes_workspace_records(self) -> None:
        record = self.running.service.workspace.data["files"][0]
        self.home.unlink()
        self.running.service.workspace.scan()

        status, _headers, cleaned = self.running.request("/api/workspace/cleanup-missing", {})

        self.assertEqual(status, 200)
        self.assertEqual(cleaned["removedFileIds"], [record["id"]])
        self.assertFalse(cleaned["files"])


class LifecycleTests(unittest.TestCase):
    def test_real_process_shutdown_cleans_state_and_ensure_restarts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "prototype" / "index.html", "<!doctype html><title>index</title>")
            with socket.socket() as probe:
                probe.bind((workbench.HOST, 0))
                port = probe.getsockname()[1]
            token = "shutdown-process-token"
            process = subprocess.Popen(
                [sys.executable, str(SCRIPT), "serve", "--project-root", str(root), "--port", str(port), "--token", token],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                deadline = time.time() + 6
                state = None
                while time.time() < deadline:
                    state = workbench.live_state(root)
                    if state:
                        break
                    time.sleep(0.05)
                self.assertIsNotNone(state, "真实工作台进程未启动")
                workbench.call_api(state, "/api/shutdown", {})
                process.wait(timeout=6)
                self.assertFalse(workbench.state_paths(root)["server"].exists())
                self.assertIsNone(workbench.live_state(root))

                output = io.StringIO()
                with warnings.catch_warnings(), contextlib.redirect_stdout(output):
                    warnings.simplefilter("ignore", ResourceWarning)
                    workbench.command_ensure(argparse.Namespace(project_root=str(root), add=[], no_open=True))
                restarted = json.loads(output.getvalue())
                self.assertFalse(restarted["reused"])
                self.assertNotEqual(restarted["pid"], process.pid)
                restarted_state = workbench.live_state(root)
                self.assertIsNotNone(restarted_state)
                workbench.call_api(restarted_state, "/api/shutdown", {})
                deadline = time.time() + 6
                while time.time() < deadline and (workbench.live_state(root) or workbench.state_paths(root)["server"].exists()):
                    time.sleep(0.05)
                self.assertIsNone(workbench.live_state(root))
                time.sleep(0.15)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=3)
                live = workbench.live_state(root)
                if live:
                    try:
                        workbench.call_api(live, "/api/shutdown", {})
                    except OSError:
                        pass


class RequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.first = write(self.root / "prototype" / "pages" / "a.html", "<p id='a'>A</p>")
        self.second = write(self.root / "prototype" / "pages" / "b.html", "<p id='b'>B</p>")
        self.workspace = workbench.Workspace(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def package(self, operations_by_name: dict[str, list[dict]], dependency: str | None = None) -> dict:
        files = []
        for record in self.workspace.data["files"]:
            if record["name"] in operations_by_name:
                files.append({"fileId": record["id"], "sha256": record["sha256"], "operations": operations_by_name[record["name"]], "dependencyGroup": dependency})
        return workbench.validate_request(self.workspace, {"schemaVersion": 1, "files": files})

    def test_schema_rejects_dangerous_css(self) -> None:
        record = self.workspace.data["files"][0]
        with self.assertRaises(workbench.WorkbenchError):
            workbench.validate_request(self.workspace, {"files": [{"fileId": record["id"], "sha256": record["sha256"], "operations": [{"type": "css", "property": "background", "value": "url(https://example.com/a.png)"}]}]})

    def test_single_active_request_and_pending_cancel(self) -> None:
        payload = self.package({"a.html": [{"type": "annotation", "text": "a"}]})
        service = workbench.WorkbenchService(self.root, "token")
        try:
            created = service.create_request({"schemaVersion": 1, "files": [
                {"fileId": item["fileId"], "sha256": item["sha256"], "operations": item["operations"]}
                for item in payload["files"]
            ]})
            with self.assertRaises(workbench.WorkbenchError):
                service.create_request({"schemaVersion": 1, "files": [
                    {"fileId": item["fileId"], "sha256": item["sha256"], "operations": item["operations"]}
                    for item in payload["files"]
                ]})
            cancelled = service.cancel_request(created["requestId"])
            self.assertEqual(cancelled["status"], "aborted")
            with self.assertRaises(workbench.WorkbenchError):
                workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=created["requestId"], request_action="begin", result=None, reason=""))
            replacement = service.create_request({"schemaVersion": 1, "files": [
                {"fileId": item["fileId"], "sha256": item["sha256"], "operations": item["operations"]}
                for item in payload["files"]
            ]})
            self.assertNotEqual(replacement["requestId"], created["requestId"])
        finally:
            service.stop()

    def test_request_state_tracks_processing_and_rejects_repeat_begin(self) -> None:
        package = self.package({"a.html": [{"type": "annotation", "text": "a"}]})
        workbench.atomic_json(workbench.request_path(self.root, package["requestId"]), package)
        args = argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="begin", result=None, reason="")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(args)
        state = workbench.load_request_state(self.root, package["requestId"])
        self.assertEqual(state["status"], "processing")
        with self.assertRaises(workbench.WorkbenchError):
            workbench.command_request(args)

        with self.assertRaises(workbench.WorkbenchError):
            workbench.cancel_request(self.root, package["requestId"])
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="abort", result=None, reason="Agent 中止测试"))
        self.assertEqual(workbench.load_request_state(self.root, package["requestId"])["status"], "aborted")

    def test_partial_and_failed_results_update_request_state(self) -> None:
        package = self.package({"a.html": [{"type": "annotation", "text": "a"}], "b.html": [{"type": "annotation", "text": "b"}]})
        workbench.atomic_json(workbench.request_path(self.root, package["requestId"]), package)
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="begin", result=None, reason=""))
        first_id = next(item["fileId"] for item in package["files"] if item["displayPath"].endswith("a.html"))
        second_id = next(item["fileId"] for item in package["files"] if item["displayPath"].endswith("b.html"))
        self.first.write_text("<p id='a'>AA</p>", encoding="utf-8")
        result_path = self.root / "partial-result.json"
        result_path.write_text(json.dumps({"items": [
            {"fileId": first_id, "path": str(self.first), "status": "success"},
            {"fileId": second_id, "path": str(self.second), "status": "failed", "reason": "测试失败"},
        ]}), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="complete", result=str(result_path), reason=""))
        self.assertEqual(workbench.load_request_state(self.root, package["requestId"])["status"], "partial")

        failed = self.package({"b.html": [{"type": "annotation", "text": "b2"}]})
        workbench.atomic_json(workbench.request_path(self.root, failed["requestId"]), failed)
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=failed["requestId"], request_action="begin", result=None, reason=""))
        failed_path = self.root / "failed-result.json"
        failed_path.write_text(json.dumps({"items": [{"fileId": failed["files"][0]["fileId"], "status": "failed", "reason": "无法定位"}]}), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=failed["requestId"], request_action="complete", result=str(failed_path), reason=""))
        self.assertEqual(workbench.load_request_state(self.root, failed["requestId"])["status"], "failed")

    def test_legacy_request_state_is_inferred_from_result(self) -> None:
        package = self.package({"a.html": [{"type": "annotation", "text": "legacy"}]})
        workbench.atomic_json(workbench.request_path(self.root, package["requestId"]), package)
        workbench.atomic_json(workbench.request_result_path(self.root, package["requestId"]), {
            "schemaVersion": 1,
            "requestId": package["requestId"],
            "status": "failed",
            "completedAt": workbench.utc_now(),
            "items": [],
        })
        self.assertFalse(workbench.request_state_path(self.root, package["requestId"]).exists())
        self.assertEqual(workbench.load_request_state(self.root, package["requestId"])["status"], "failed")

    def test_request_listing_ignores_agent_result_scratch_file_after_success(self) -> None:
        package = self.package({"a.html": [{"type": "style", "property": "color", "value": "red"}]})
        workbench.atomic_json(workbench.request_path(self.root, package["requestId"]), package)
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="begin", result=None, reason=""))
        self.first.write_text("<p id='a' style='color:red'>A</p>", encoding="utf-8")
        result_path = workbench.state_paths(self.root)["requests"] / f"{package['requestId']}.result.pending.json"
        result_path.write_text(json.dumps({"items": [{"fileId": package["files"][0]["fileId"], "status": "success"}]}), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="complete", result=str(result_path), reason=""))

        summaries = workbench.list_request_summaries(self.root)
        self.assertEqual([item["requestId"] for item in summaries], [package["requestId"]])
        self.assertEqual(summaries[0]["status"], "success")
        self.assertIsNone(workbench.active_request_summary(self.root))

    def test_sync_pages_opportunity_requires_real_page_change_and_is_consumed(self) -> None:
        runtime = write(self.root / "prototype" / "runtime-pages" / "a--prototype.html", "<p id='a'>A runtime</p><script>const type='navigate'</script>")
        workspace = workbench.Workspace(self.root)
        source = next(item for item in workspace.data["files"] if item["path"].endswith("pages/a.html"))
        runtime_record = next(item for item in workspace.data["files"] if item["path"].endswith("runtime-pages/a--prototype.html"))
        package = workbench.validate_request(workspace, {"schemaVersion": 1, "files": [{
            "fileId": source["id"],
            "sha256": source["sha256"],
            "operations": [{"type": "style", "fingerprint": {"selector": "#a", "framePath": []}, "property": "color", "value": "red"}],
        }]})
        workbench.atomic_json(workbench.request_path(self.root, package["requestId"]), package)
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="begin", result=None, reason=""))
        self.first.write_text("<p id='a' style='color:red'>A</p>", encoding="utf-8")
        result_path = self.root / "page-result.json"
        result_path.write_text(json.dumps({"items": [{"fileId": source["id"], "status": "success"}]}), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="complete", result=str(result_path), reason=""))

        workspace.scan()
        opportunities = workbench.sync_page_opportunities(self.root, workspace)
        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0]["runtimeFileId"], runtime_record["id"])
        self.assertEqual(opportunities[0]["sourceFileId"], source["id"])
        self.assertEqual(opportunities[0]["sourceRequestId"], package["requestId"])
        self.assertEqual(opportunities[0]["previewOperations"][0]["property"], "color")

        sync_package = workbench.validate_request(workspace, {"schemaVersion": 1, "files": [{
            "fileId": runtime_record["id"],
            "sha256": workbench.sha256_file(runtime),
            "operations": [{
                "type": "sync-pages",
                "sourceFileId": source["id"],
                "sourceRequestId": package["requestId"],
                "sourceSha256": workbench.sha256_file(self.first),
                "runtimeSha256": workbench.sha256_file(runtime),
            }],
        }]})
        workbench.atomic_json(workbench.request_path(self.root, sync_package["requestId"]), sync_package)
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=sync_package["requestId"], request_action="begin", result=None, reason=""))
        runtime.write_text("<p id='a' style='color:red'>A runtime</p><script>const type='navigate'</script>", encoding="utf-8")
        sync_result_path = self.root / "sync-result.json"
        sync_result_path.write_text(json.dumps({"items": [{"fileId": runtime_record["id"], "status": "success"}]}), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=sync_package["requestId"], request_action="complete", result=str(sync_result_path), reason=""))

        workspace.scan()
        self.assertEqual(workbench.sync_page_opportunities(self.root, workspace), [])

    def test_independent_conflict_allows_partial_begin(self) -> None:
        package = self.package({"a.html": [{"type": "annotation", "text": "a"}], "b.html": [{"type": "annotation", "text": "b"}]})
        workbench.atomic_json(workbench.request_path(self.root, package["requestId"]), package)
        self.first.write_text("<p id='a'>外部修改</p>", encoding="utf-8")
        output = io.StringIO()
        args = argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="begin", result=None, reason="")
        with contextlib.redirect_stdout(output):
            workbench.command_request(args)
        result = json.loads(output.getvalue())
        second_id = next(item["id"] for item in self.workspace.data["files"] if item["name"] == "b.html")
        self.assertEqual(result["readyFileIds"], [second_id])
        self.assertEqual(result["conflicts"][0]["status"], "conflict")

    def test_dependency_conflict_blocks_whole_group(self) -> None:
        package = self.package({"a.html": [{"type": "annotation", "text": "a"}], "b.html": [{"type": "annotation", "text": "b"}]}, dependency="sync-group")
        workbench.atomic_json(workbench.request_path(self.root, package["requestId"]), package)
        self.first.write_text("changed", encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            workbench.command_request(argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="begin", result=None, reason=""))
        result = json.loads(output.getvalue())
        self.assertEqual(result["readyFileIds"], [])
        self.assertEqual(len(result["conflicts"]), 2)

    def test_complete_does_not_create_undo_state(self) -> None:
        package = self.package({"a.html": [{"type": "text", "index": 0, "value": "AA"}]})
        workbench.atomic_json(workbench.request_path(self.root, package["requestId"]), package)
        args = argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="begin", result=None, reason="")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(args)
        self.first.write_text("<p id='a'>AA</p>", encoding="utf-8")
        file_id = package["files"][0]["fileId"]
        result_path = self.root / "agent-result.json"
        result_path.write_text(json.dumps({"items": [{"fileId": file_id, "path": str(self.first), "status": "success"}]}), encoding="utf-8")
        complete = argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="complete", result=str(result_path), reason="")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(complete)
        self.assertEqual(workbench.load_request_state(self.root, package["requestId"])["status"], "success")
        self.assertFalse((self.root / ".ycet-editor" / "undo").exists())

    def test_added_image_and_editlog_can_join_request_transaction(self) -> None:
        package = self.package({"a.html": [{"type": "image-replace", "path": str(self.root / "source.png")}]})
        workbench.atomic_json(workbench.request_path(self.root, package["requestId"]), package)
        image = self.root / "prototype" / "assets" / "images" / "cover.png"
        editlog = write(self.root / "prototype" / "docs" / "EditLog.md", "# EditLog\n")
        begin_output = io.StringIO()
        begin = argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="begin", result=None, reason="", include=[str(image), str(editlog)])
        with contextlib.redirect_stdout(begin_output):
            workbench.command_request(begin)
        tracked = json.loads(begin_output.getvalue())["trackedFiles"]
        extra_ids = [item["fileId"] for item in tracked if item["fileId"].startswith("extra-")]
        self.first.write_text("<img src='../assets/images/cover.png'>", encoding="utf-8")
        write(image, "image-bytes")
        editlog.write_text("# EditLog\n- 替换图片\n", encoding="utf-8")
        primary = package["files"][0]["fileId"]
        result_path = self.root / "image-result.json"
        result_path.write_text(json.dumps({"items": [{"fileId": primary, "status": "success", "affectedFileIds": extra_ids}]}), encoding="utf-8")
        complete = argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="complete", result=str(result_path), reason="")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(complete)
        self.assertTrue(image.exists())
        self.assertIn("替换图片", editlog.read_text(encoding="utf-8"))
        self.assertEqual(self.first.read_text(encoding="utf-8"), "<img src='../assets/images/cover.png'>")
        self.assertFalse((workbench.state_paths(self.root)["transactions"] / package["requestId"]).exists())

    def test_removed_undo_cli_is_rejected(self) -> None:
        with self.assertRaises(SystemExit) as denied:
            workbench.main(["undo", "--project-root", str(self.root)])
        self.assertEqual(denied.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
