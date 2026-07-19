#!/usr/bin/env python3
"""用可用的 Chromium/Chrome、Edge 与 Firefox 验证工作台浏览器交互。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


SCRIPT = Path(__file__).with_name("prototype_workbench.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, copy: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(copy, encoding="utf-8")
    return path


def free_port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return int(server.getsockname()[1])


def wait_server(url: str, token: str) -> None:
    deadline = time.time() + 12
    while time.time() < deadline:
        try:
            request = urllib.request.Request(url + "/api/health", headers={"X-YCET-Token": token})
            with urllib.request.urlopen(request, timeout=1) as response:
                if json.loads(response.read()).get("ok"):
                    return
        except Exception:  # noqa: BLE001 - 服务启动轮询
            time.sleep(0.1)
    raise RuntimeError("工作台服务启动超时")


def browser_targets(playwright):
    chrome = Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe"
    edge = Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe"
    targets = [("chromium", playwright.chromium, None)]
    if chrome.is_file():
        targets.append(("chrome", playwright.chromium, str(chrome)))
    if edge.is_file():
        targets.append(("edge", playwright.chromium, str(edge)))
    targets.append(("firefox", playwright.firefox, None))
    return targets


def assert_layout(page, viewport: dict[str, int]) -> None:
    page.set_viewport_size(viewport)
    page.wait_for_timeout(120)
    boxes = {name: page.locator(selector).bounding_box() for name, selector in {"sidebar": "#sidebar", "workspace": ".workspace", "inspector": ".inspector"}.items()}
    if not all(boxes.values()):
        raise AssertionError(f"布局区域缺失：{boxes}")
    if boxes["sidebar"]["x"] + boxes["sidebar"]["width"] > boxes["workspace"]["x"]:
        raise AssertionError("左栏与中央预览重叠")
    if boxes["workspace"]["x"] + boxes["workspace"]["width"] > boxes["inspector"]["x"]:
        raise AssertionError("中央预览与右侧属性栏重叠")
    if page.evaluate("document.body.scrollWidth") > viewport["width"] + 1:
        raise AssertionError("页面出现横向溢出")


def exercise(browser, name: str, url: str, home: Path, project: Path, screenshot_dir: Path) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    errors = []
    http_errors = []
    regression_failures = []
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" and "Failed to load resource" not in message.text else None)
    page.on("response", lambda response: http_errors.append(f"{response.status} {response.url}") if response.status >= 400 and not response.url.endswith("/favicon.ico") else None)
    original = sha256(home)
    page.goto(url, wait_until="networkidle")
    page.locator("#file-tree .file-row").first.wait_for()
    page.wait_for_timeout(120)
    if page.locator("#font-family option").count() <= 4:
        regression_failures.append("字体选择器没有加载本机字体清单")

    # 文件树只保留项目扫描与查看能力，不得暴露增删、分组或拖拽排序入口。
    for selector in ("#add-group", "#add-external", "#group-dialog", ".group-remove", ".remove-file"):
        if page.locator(selector).count():
            regression_failures.append(f"文件树仍保留已移除的操作入口：{selector}")
    if page.locator("#file-tree .file-row[draggable='true']").count():
        regression_failures.append("文件行仍可拖拽排序或分组")
    if page.locator("#refresh-files").count() != 1:
        regression_failures.append("左侧文件栏缺少项目文件刷新按钮")
    refreshed = write(project / "prototype/pages/refreshed.html", "<!doctype html><p>刷新补入</p>")
    page.locator("#refresh-files").click()
    page.get_by_text("refreshed.html", exact=True).wait_for()
    if not refreshed.is_file():
        regression_failures.append("刷新项目文件意外改动或删除了源 HTML")
    page.get_by_text("index.html", exact=True).click()
    page.locator("#current-path").filter(has_text="prototype/index.html").wait_for()

    # 根入口中的同源 iframe 与 srcdoc 都必须选择到真实元素。
    nested = page.frame_locator("#preview-frame").frame_locator("#nested-page").locator("#buy")
    nested.wait_for()
    nested.click()
    page.locator("#selected-name").filter(has_text="button").wait_for()
    nested_frame = page.frame_locator("#preview-frame").locator("#nested-page")
    nested_body = page.frame_locator("#preview-frame").frame_locator("#nested-page").locator("body")
    nested_body.evaluate("element => element.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: element.ownerDocument.defaultView }))")
    page.locator("#selected-name").filter(has_text="body").wait_for()
    page.wait_for_timeout(60)
    nested_frame_bounds = nested_frame.bounding_box()
    nested_selection_bounds = page.frame_locator("#preview-frame").locator(".ycet-editor-selected").bounding_box()
    if (
        nested_selection_bounds["x"] < nested_frame_bounds["x"] - 2
        or nested_selection_bounds["y"] < nested_frame_bounds["y"] - 2
        or nested_selection_bounds["x"] + nested_selection_bounds["width"] > nested_frame_bounds["x"] + nested_frame_bounds["width"] + 2
        or nested_selection_bounds["y"] + nested_selection_bounds["height"] > nested_frame_bounds["y"] + nested_frame_bounds["height"] + 2
    ):
        regression_failures.append(f"嵌套页面选区没有按 iframe 可见区域裁剪：frame={nested_frame_bounds} selection={nested_selection_bounds}")
    page.frame_locator("#preview-frame").frame_locator("#inline-page").locator("#srcdoc-action").click()
    page.locator("#selected-path").filter(has_text="index.html").wait_for()

    # 直接页面的草稿预览、批注、跨文件保留和清空语义。
    page.get_by_text("home.html", exact=True).click()
    page.locator("#current-path").filter(has_text="pages/home.html").wait_for()
    target = page.frame_locator("#preview-frame").locator("#buy")
    target.wait_for()

    # 宽页面不能在 iframe 内发生横向裁切，预览高度应使用画布可用空间。
    shell_box = page.locator("#preview-shell").bounding_box()
    canvas_box = page.locator("#canvas-viewport").bounding_box()
    page_widths = target.evaluate("element => ({inner: innerWidth, scroll: document.scrollingElement.scrollWidth})")
    if page_widths["scroll"] > page_widths["inner"] + 1:
        regression_failures.append(f"HTML 页面横向被裁切：{page_widths}")
    if shell_box["height"] < canvas_box["height"] - 90:
        regression_failures.append(f"预览高度未使用画布空间：shell={shell_box['height']} canvas={canvas_box['height']}")

    target.click()
    if not page.locator("#font-family").input_value():
        regression_failures.append("选择元素后字体下拉框显示为空")

    # 批注入口必须位于选区外，避免遮挡正在检查的组件。
    preview = page.frame_locator("#preview-frame")
    selection_box = preview.locator(".ycet-editor-selected")
    annotate_button = preview.locator(".ycet-editor-annotate")
    selected_bounds = selection_box.bounding_box()
    annotate_bounds = annotate_button.bounding_box()
    overlaps = not (
        annotate_bounds["x"] + annotate_bounds["width"] <= selected_bounds["x"]
        or selected_bounds["x"] + selected_bounds["width"] <= annotate_bounds["x"]
        or annotate_bounds["y"] + annotate_bounds["height"] <= selected_bounds["y"]
        or selected_bounds["y"] + selected_bounds["height"] <= annotate_bounds["y"]
    )
    if overlaps:
        regression_failures.append(f"批注按钮遮挡选中元素：selection={selected_bounds} annotate={annotate_bounds}")

    # 文本对齐只能使用图标表达，并保留无障碍名称。
    alignment_buttons = page.locator(".alignment button")
    if alignment_buttons.count() != 4:
        regression_failures.append("文本对齐按钮数量不正确")
    for index in range(alignment_buttons.count()):
        button = alignment_buttons.nth(index)
        if button.inner_text().strip() or button.locator("svg").count() != 1 or not button.get_attribute("aria-label"):
            regression_failures.append("文本对齐按钮仍在使用文字或缺少图标/无障碍名称")
            break

    # 关闭选择模式后不得保留任何选区框或批注入口。
    page.locator("#select-mode").click()
    page.wait_for_timeout(60)
    if preview.locator(".ycet-editor-selected").is_visible() or preview.locator(".ycet-editor-annotate").is_visible():
        regression_failures.append("关闭选择模式后仍显示选区框或批注按钮")
    page.locator("#select-mode").click()
    target.click()

    # static 元素的 X/Y 修改也必须改变实际位置。
    before_position = target.bounding_box()
    inspector_x = float(page.locator("#position-x").input_value())
    inspector_y = float(page.locator("#position-y").input_value())
    page.locator("#position-x").fill(str(round(inspector_x + 40)))
    page.locator("#position-x").dispatch_event("input")
    page.locator("#position-y").fill(str(round(inspector_y + 30)))
    page.locator("#position-y").dispatch_event("input")
    page.wait_for_timeout(100)
    after_position = target.bounding_box()
    if after_position["x"] < before_position["x"] + 35 or after_position["y"] < before_position["y"] + 25:
        regression_failures.append(f"X/Y 修改未移动元素：before={before_position} after={after_position}")

    page.locator("#width").fill("320")
    page.locator("#width").dispatch_event("input")
    page.locator("#rotation").fill("15")
    page.locator("#rotation").dispatch_event("input")
    page.wait_for_timeout(100)
    if target.evaluate("element => element.style.width") != "320px":
        raise AssertionError("属性修改没有实时应用到预览")

    # 位移、尺寸和旋转改变后，选区必须跟随实际元素外接矩形。
    target_bounds = target.bounding_box()
    selected_bounds = selection_box.bounding_box()
    for key in ("x", "y", "width", "height"):
        if abs(target_bounds[key] - selected_bounds[key]) > 2:
            regression_failures.append(f"变换后选区未跟随元素：target={target_bounds} selection={selected_bounds}")
            break

    # 颜色面板与效果面板必须锚定触发按钮，并支持多个独立效果。
    color_button = page.locator('[data-color-property="background-color"]')
    color_button.click()
    color_dialog = page.locator("#color-dialog[open]")
    color_dialog.wait_for()
    color_trigger_bounds = color_button.bounding_box()
    color_dialog_bounds = color_dialog.bounding_box()
    color_form_bounds = color_dialog.locator("form").bounding_box()
    if abs(color_dialog_bounds["width"] - color_form_bounds["width"]) > 2:
        regression_failures.append(f"颜色面板右侧存在多余空白：dialog={color_dialog_bounds} form={color_form_bounds}")
    horizontal_gap = max(color_trigger_bounds["x"] - color_dialog_bounds["x"] - color_dialog_bounds["width"], color_dialog_bounds["x"] - color_trigger_bounds["x"] - color_trigger_bounds["width"], 0)
    vertical_gap = max(color_trigger_bounds["y"] - color_dialog_bounds["y"] - color_dialog_bounds["height"], color_dialog_bounds["y"] - color_trigger_bounds["y"] - color_trigger_bounds["height"], 0)
    if (horizontal_gap ** 2 + vertical_gap ** 2) ** 0.5 > 24:
        regression_failures.append("颜色面板没有显示在颜色按钮附近")
    if not color_dialog.locator("#color-sv").count() or not color_dialog.locator("#color-hue").count():
        regression_failures.append("颜色面板缺少 SV 色板或色相滑杆")
    if name == "chrome":
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        color_dialog.screenshot(path=str(screenshot_dir / "color-picker-chrome.png"))
    color_dialog.locator("button[value='cancel']").last.click()

    page.locator("#add-effect").click()
    page.locator("#add-effect").click()
    effect_rows = page.locator("#effect-list .effect-row")
    if effect_rows.count() != 2:
        regression_failures.append("阴影与模糊不能添加多个效果")
    else:
        effect_rows.nth(1).locator("select").select_option("inset")
        settings_button = effect_rows.nth(0).locator(".effect-settings")
        settings_button.click()
        effect_dialog = page.locator("#effect-dialog[open]")
        effect_dialog.wait_for()
        settings_bounds = settings_button.bounding_box()
        effect_dialog_bounds = effect_dialog.bounding_box()
        horizontal_gap = max(settings_bounds["x"] - effect_dialog_bounds["x"] - effect_dialog_bounds["width"], effect_dialog_bounds["x"] - settings_bounds["x"] - settings_bounds["width"], 0)
        vertical_gap = max(settings_bounds["y"] - effect_dialog_bounds["y"] - effect_dialog_bounds["height"], effect_dialog_bounds["y"] - settings_bounds["y"] - settings_bounds["height"], 0)
        if (horizontal_gap ** 2 + vertical_gap ** 2) ** 0.5 > 24:
            regression_failures.append("效果设置面板没有显示在设置按钮附近")
        if not effect_dialog.locator("#shadow-color").count():
            regression_failures.append("投影设置缺少投影颜色")
        effect_dialog.locator("button[value='cancel']").click()
        shadow = target.evaluate("element => getComputedStyle(element).boxShadow")
        if shadow.count("rgb") < 2:
            regression_failures.append(f"多个投影没有组合应用到元素：{shadow}")

    # 选择另一个组件时，整个属性栏都必须切换到该组件自己的状态。
    secondary = page.frame_locator("#preview-frame").locator("#secondary")
    secondary.click()
    page.wait_for_timeout(80)
    if page.locator("#selected-name").inner_text() != "button#secondary":
        regression_failures.append("元素切换后属性栏仍指向前一个组件")
    if abs(float(page.locator("#width").input_value()) - 180) > 1 or page.locator("#font-size").input_value() != "22":
        regression_failures.append("元素切换后尺寸或文本属性仍残留前一个组件的值")
    if page.locator("#rotation").input_value() not in ("0", "0.0") or effect_rows.count():
        regression_failures.append("元素切换后旋转或效果状态仍残留前一个组件的值")
    target.click()
    page.wait_for_timeout(80)
    page.frame_locator("#preview-frame").locator(".ycet-editor-annotate").click()
    page.locator("#annotation-copy").fill("按钮宽度改为 320px")
    page.locator("#save-annotation").click()
    page.frame_locator("#preview-frame").locator(".ycet-editor-marker").wait_for()
    if sha256(home) != original:
        raise AssertionError("发送前源 HTML 被工作台改写")

    page.get_by_text("index.html", exact=True).click()
    page.locator(".file-row.pending", has_text="home.html").wait_for()
    page.get_by_text("home.html", exact=True).click()
    target = page.frame_locator("#preview-frame").locator("#buy")
    target.wait_for()
    page.locator("#clear-current").click()
    page.wait_for_timeout(100)
    if target.evaluate("element => element.style.width"):
        raise AssertionError("清空修改没有恢复原始样式")
    page.frame_locator("#preview-frame").locator(".ycet-editor-marker").wait_for()

    # 普通滚轮滚动 HTML；只有 Ctrl+滚轮才以鼠标为中心缩放。
    target.click()
    selection_box.wait_for()
    viewport = page.locator("#canvas-viewport").bounding_box()
    frame_box = page.locator("#preview-frame").bounding_box()
    start_x = frame_box["x"] + frame_box["width"] * 0.5
    start_y = frame_box["y"] + frame_box["height"] * 0.5
    page.mouse.move(start_x, start_y)
    page.mouse.wheel(0, 1200)
    page.wait_for_timeout(80)
    if selection_box.is_visible() or annotate_button.is_visible():
        regression_failures.append("选中元素滚出页面后选区框或批注按钮仍停留在画布中")
    page.mouse.wheel(0, -1200)
    page.wait_for_timeout(80)
    if not selection_box.is_visible():
        regression_failures.append("选中元素滚回页面后选区框没有恢复")
    else:
        restored_target_bounds = target.bounding_box()
        restored_selection_bounds = selection_box.bounding_box()
        if any(abs(restored_target_bounds[key] - restored_selection_bounds[key]) > 2 for key in ("x", "y", "width", "height")):
            regression_failures.append(f"滚动恢复后选区与元素位置不一致：target={restored_target_bounds} selection={restored_selection_bounds}")
    zoom_before_scroll = page.locator("#zoom-value").inner_text()
    page.mouse.wheel(0, 360)
    page.wait_for_timeout(80)
    scroll_y = target.evaluate("element => scrollY")
    if scroll_y <= 0 or page.locator("#zoom-value").inner_text() != zoom_before_scroll:
        regression_failures.append("普通滚轮没有只滚动 HTML 页面")
    page.keyboard.down("Control")
    page.mouse.wheel(0, -120)
    page.keyboard.up("Control")
    page.wait_for_timeout(80)
    if page.locator("#zoom-value").inner_text() == zoom_before_scroll:
        regression_failures.append("Ctrl+滚轮没有调整缩放")
    before_transform = page.locator("#preview-shell").get_attribute("style") or ""
    page.mouse.down(button="middle")
    page.mouse.move(start_x + 37, start_y + 29)
    page.mouse.up(button="middle")
    after_transform = page.locator("#preview-shell").get_attribute("style") or ""
    if before_transform == after_transform or "translate" not in after_transform:
        raise AssertionError("中键二维平移没有更新画布")

    # 仅剩批注也应生成请求，成功写入后清空全部会话草稿。
    page.locator("#send-ai").click()
    page.locator("#request-dialog[open]").wait_for()
    if "请求 ID" not in page.locator("#request-instruction").input_value():
        raise AssertionError("发送后未生成 Agent 执行指令")
    page.locator("#request-dialog button[value='cancel']").click()
    page.wait_for_timeout(80)
    if page.locator(".file-row.pending").count():
        raise AssertionError("请求写入成功后仍保留草稿红点")
    if sha256(home) != original:
        raise AssertionError("生成变更包后源 HTML 被改写")
    requests = [path for path in (project / ".ycet-editor" / "requests").glob("*.json") if not path.name.endswith((".state.json", ".result.json"))]
    if not requests:
        raise AssertionError("变更包未写入 .ycet-editor/requests")
    if regression_failures:
        raise AssertionError("；".join(regression_failures))

    for size in ({"width": 1440, "height": 900}, {"width": 1280, "height": 720}, {"width": 1024, "height": 768}):
        assert_layout(page, size)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    page.set_viewport_size({"width": 1440, "height": 900})
    page.screenshot(path=str(screenshot_dir / f"workbench-{name}.png"), full_page=True)
    if errors or http_errors:
        raise AssertionError("浏览器错误：" + "；".join(errors + http_errors))
    context.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="YCET 工作台浏览器运行时测试")
    parser.add_argument("--require-firefox", action="store_true")
    parser.add_argument("--screenshot-dir", default=str(Path(tempfile.gettempdir()) / "ycet-workbench-artifacts"))
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] Python Playwright 未安装")
        return 1 if args.require_firefox else 0

    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp)
        home = write(project / "prototype/pages/home.html", "<!doctype html><html><head><style>html,body{margin:0;min-width:1400px}main{height:1800px;padding:24px}#secondary{display:block;width:180px;margin-top:120px;font-size:22px;color:rgb(170,0,0)}</style></head><body><main><button id='buy' style='height:42px'>购买</button><button id='secondary'>次要操作</button><img id='cover' alt='封面' src='data:image/gif;base64,R0lGODlhAQABAAAAACw='></main></body></html>")
        write(project / "prototype/index.html", "<!doctype html><html><body><iframe id='nested-page' src='pages/home.html'></iframe><iframe id='inline-page' srcdoc=\"<button id='srcdoc-action'>内联操作</button>\"></iframe></body></html>")
        write(project / "prototype/runtime-pages/home--prototype.html", "<!doctype html><button>运行时</button><script>const type='navigate'</script>")
        port = free_port()
        token = "runtime-test-token"
        base_url = f"http://127.0.0.1:{port}"
        process = subprocess.Popen([sys.executable, str(SCRIPT), "serve", "--project-root", str(project), "--port", str(port), "--token", token], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            wait_server(base_url, token)
            passed = []
            skipped = []
            with sync_playwright() as playwright:
                for name, browser_type, executable in browser_targets(playwright):
                    try:
                        options = {"headless": True}
                        if executable:
                            options["executable_path"] = executable
                        browser = browser_type.launch(**options)
                    except Exception as exc:  # noqa: BLE001 - 缺失浏览器明确跳过
                        skipped.append((name, str(exc).splitlines()[0]))
                        print(f"[SKIP] {name}: {skipped[-1][1]}")
                        continue
                    try:
                        exercise(browser, name, f"{base_url}/?token={token}", home, project, Path(args.screenshot_dir))
                        passed.append(name)
                        print(f"[OK] {name}: 工作台运行时与三档布局通过")
                    finally:
                        browser.close()
            if args.require_firefox and "firefox" not in passed:
                print("[FAIL] Firefox 未实际通过")
                return 1
            if not passed:
                print("[FAIL] 没有可用浏览器完成工作台测试")
                return 1
            print(json.dumps({"passed": passed, "skipped": skipped, "screenshots": args.screenshot_dir}, ensure_ascii=False))
            return 0
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
