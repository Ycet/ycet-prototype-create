#!/usr/bin/env python3
"""原型可视化编辑器工作区、服务、变更包与撤回回归测试。"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
import urllib.error
import urllib.request
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
        external = write(self.root / "outside" / "external.html", "<p>outside</p>")
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


class RequestAndUndoTests(unittest.TestCase):
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

    def test_complete_creates_cross_restart_undo_and_restores(self) -> None:
        package = self.package({"a.html": [{"type": "text", "index": 0, "value": "AA"}]})
        workbench.atomic_json(workbench.request_path(self.root, package["requestId"]), package)
        args = argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="begin", result=None, reason="")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(args)
        before = self.first.read_bytes()
        self.first.write_text("<p id='a'>AA</p>", encoding="utf-8")
        file_id = package["files"][0]["fileId"]
        result_path = self.root / "agent-result.json"
        result_path.write_text(json.dumps({"items": [{"fileId": file_id, "path": str(self.first), "status": "success"}]}), encoding="utf-8")
        complete = argparse.Namespace(project_root=str(self.root), request_id=package["requestId"], request_action="complete", result=str(result_path), reason="")
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_request(complete)
        self.assertTrue((self.root / ".ycet-editor" / "undo" / "latest" / "manifest.json").is_file())
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_undo(argparse.Namespace(project_root=str(self.root)))
        self.assertEqual(self.first.read_bytes(), before)

    def test_undo_refuses_after_digest_conflict(self) -> None:
        self.test_complete_creates_cross_restart_undo_and_restores()
        # 上一个辅助测试已撤回并删除事务，这里重新建立一个最小冲突事务。
        paths = workbench.state_paths(self.root)
        snapshot = paths["undo"] / "before" / "a.bin"
        snapshot.parent.mkdir(parents=True)
        snapshot.write_bytes(b"before")
        workbench.atomic_json(paths["undo"] / "manifest.json", {"schemaVersion": 1, "requestId": "undo-conflict", "files": [{"path": str(self.first), "snapshot": str(snapshot), "afterSha256": "0" * 64}]})
        with self.assertRaises(workbench.WorkbenchError):
            workbench.command_undo(argparse.Namespace(project_root=str(self.root)))

    def test_added_image_and_editlog_can_join_undo_transaction(self) -> None:
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
        with contextlib.redirect_stdout(io.StringIO()):
            workbench.command_undo(argparse.Namespace(project_root=str(self.root)))
        self.assertFalse(image.exists())
        self.assertEqual(editlog.read_text(encoding="utf-8"), "# EditLog\n")
        self.assertEqual(self.first.read_text(encoding="utf-8"), "<p id='a'>A</p>")


if __name__ == "__main__":
    unittest.main(verbosity=2)
