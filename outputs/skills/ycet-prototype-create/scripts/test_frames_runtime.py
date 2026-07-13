#!/usr/bin/env python3
"""使用真实浏览器验证设备框架的加载、尺寸、消息中继与可移植性。"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


INDEX_TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<style>
html, body {{ margin: 0; scrollbar-width: none; -ms-overflow-style: none; }}
html::-webkit-scrollbar, body::-webkit-scrollbar {{ width: 0; height: 0; display: none; }}
</style>
<iframe id="frame" src="assets/frames/{frame_file}?screen=pages/one.html"
  scrolling="no"
  style="width:{preview_width}px;height:{preview_height}px;border:0;overflow:hidden"></iframe>
<script>
window.events = [];
window.addEventListener('message', (event) => {{
  const message = event.data || {{}};
  if (message.channel !== 'ycet-prototype' || message.version !== 1) return;
  window.events.push(message);
  if (message.type === 'navigate') {{
    document.getElementById('frame').contentWindow.postMessage({{
      channel: 'ycet-prototype', version: 1, type: 'set-screen', screen: message.targetPage
    }}, '*');
  }}
}});
</script>"""

PAGE_ROOT_STYLE = """<style>
html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; scrollbar-width: none; -ms-overflow-style: none; }
html::-webkit-scrollbar, body::-webkit-scrollbar { width: 0; height: 0; display: none; }
</style>"""

PAGE_ONE = """<!doctype html><meta charset="utf-8">""" + PAGE_ROOT_STYLE + """<button id="next">下一页</button><script>
document.getElementById('next').onclick = () => parent.postMessage({
  channel:'ycet-prototype', version:1, type:'navigate', targetPage:'two.html'
}, '*');
</script>"""

PAGE_TWO = """<!doctype html><meta charset="utf-8">""" + PAGE_ROOT_STYLE + """<main id="page-two">第二页</main>"""
UNICODE_PAGE = """<!doctype html><meta charset="utf-8">""" + PAGE_ROOT_STYLE + """<main id="unicode-page">中文空格页面</main>"""
PREVIEW_PAGE = """<!doctype html><meta charset="utf-8">""" + PAGE_ROOT_STYLE + """<main id="home-preview">首页预览</main>"""
RUNTIME_PAGE = """<!doctype html><meta charset="utf-8">""" + PAGE_ROOT_STYLE + """<main id="runtime-page">运行时页面</main><button id="runtime-next">运行时下一页</button><script>
document.getElementById('runtime-next').onclick = () => parent.postMessage({
  channel:'ycet-prototype', version:1, type:'navigate', targetPage:'runtime-pages/runtime-two--prototype.html'
}, '*');
</script>"""
RUNTIME_PAGE_TWO = """<!doctype html><meta charset="utf-8">""" + PAGE_ROOT_STYLE + """<main id="runtime-page-two">运行时第二页</main>"""

DESIGN_TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<style>
html, body {{ margin: 0; scrollbar-width: none; -ms-overflow-style: none; }}
html::-webkit-scrollbar, body::-webkit-scrollbar {{ width: 0; height: 0; display: none; }}
</style>
<iframe id="frame" src="assets/frames/{frame_file}?screen=previews/home-preview.html"
  scrolling="no"
  style="width:{preview_width}px;height:{preview_height}px;border:0;overflow:hidden"></iframe>"""


class QuietHandler(SimpleHTTPRequestHandler):
    """关闭请求日志，避免测试输出被静态服务器噪声淹没。"""

    def log_message(self, _format: str, *args: object) -> None:
        return


def build_fixture(skill_dir: Path, fixture_dir: Path, frame: dict[str, object]) -> None:
    """复制框架资产并生成最小双层 iframe 测试页面。"""

    shutil.copytree(skill_dir / "assets" / "frames", fixture_dir / "assets" / "frames")
    pages_dir = fixture_dir / "pages"
    pages_dir.mkdir(parents=True)
    (pages_dir / "one.html").write_text(PAGE_ONE, encoding="utf-8")
    (pages_dir / "two.html").write_text(PAGE_TWO, encoding="utf-8")
    (pages_dir / "中文 页面.html").write_text(UNICODE_PAGE, encoding="utf-8")
    previews_dir = fixture_dir / "previews"
    previews_dir.mkdir(parents=True)
    (previews_dir / "home-preview.html").write_text(PREVIEW_PAGE, encoding="utf-8")
    runtime_pages_dir = fixture_dir / "runtime-pages"
    runtime_pages_dir.mkdir(parents=True)
    (runtime_pages_dir / "runtime-page--prototype.html").write_text(RUNTIME_PAGE, encoding="utf-8")
    (runtime_pages_dir / "runtime-two--prototype.html").write_text(RUNTIME_PAGE_TWO, encoding="utf-8")
    preview = frame["preview"]
    (fixture_dir / "index.html").write_text(
        INDEX_TEMPLATE.format(
            frame_file=frame["file"],
            preview_width=preview["width"],
            preview_height=preview["height"],
        ),
        encoding="utf-8",
    )
    (fixture_dir / "design-direction.html").write_text(
        DESIGN_TEMPLATE.format(
            frame_file=frame["file"],
            preview_width=preview["width"],
            preview_height=preview["height"],
        ),
        encoding="utf-8",
    )


def exercise_frame_page(page, frame: dict[str, object], expect_empty_referrer: bool) -> None:
    """在已打开的 index 页面验证路径、尺寸、消息兼容与安全拦截。"""

    page.wait_for_load_state("networkidle")
    outer_frame = page.frame_locator("#frame")
    inner_frame = outer_frame.frame_locator("#screen")
    inner_frame.locator("#next").wait_for()

    host_scroll_style = page.locator("html").evaluate(
        "node => ({ scrollbarWidth: getComputedStyle(node).scrollbarWidth, scrollable: node.scrollHeight > node.clientHeight })"
    )
    assert host_scroll_style["scrollbarWidth"] == "none", (frame["id"], host_scroll_style)
    if host_scroll_style["scrollable"]:
        page.evaluate("window.scrollTo(0, 100)")
        assert page.evaluate("window.scrollY") > 0, (frame["id"], "宿主滚动能力丢失")
        page.evaluate("window.scrollTo(0, 0)")

    assert page.locator("#frame").get_attribute("scrolling") == "no", frame["id"]
    assert outer_frame.locator("#screen").get_attribute("scrolling") == "no", frame["id"]
    frame_root_style = outer_frame.locator("html").evaluate(
        "node => ({ overflow: getComputedStyle(node).overflow, scrollbarWidth: getComputedStyle(node).scrollbarWidth })"
    )
    assert frame_root_style == {"overflow": "hidden", "scrollbarWidth": "none"}, (
        frame["id"],
        frame_root_style,
    )

    if expect_empty_referrer:
        referrer = outer_frame.locator("body").evaluate("() => document.referrer")
        assert referrer == "", (frame["id"], referrer)

    logical = frame["logicalViewport"]
    size = outer_frame.locator("#screen").evaluate(
        "node => ({ width: node.clientWidth, height: node.clientHeight })"
    )
    assert size == {"width": logical["width"], "height": logical["height"]}, (
        frame["id"],
        size,
    )

    # 旧页面仍可发送裸文件名，但框架必须规范化后再向外中继。
    inner_frame.locator("#next").click()
    inner_frame.locator("#page-two").wait_for()
    page.wait_for_function(
        "window.events.some(event => event.type === 'navigate' && event.targetPage === 'pages/two.html')"
    )

    # query/hash 在 pathname 通过白名单后保留。
    page.locator("#frame").evaluate(
        "node => node.contentWindow.postMessage({channel:'ycet-prototype',version:1,type:'set-screen',screen:'pages/two.html?tab=detail#section'}, '*')"
    )
    inner_frame.locator("#page-two").wait_for()
    location_parts = inner_frame.locator("#page-two").evaluate(
        "node => ({search: node.ownerDocument.location.search, hash: node.ownerDocument.location.hash})"
    )
    assert location_parts == {"search": "?tab=detail", "hash": "#section"}, (
        frame["id"],
        location_parts,
    )

    # 接管旧项目时支持安全的中文和空格页面名。
    page.locator("#frame").evaluate(
        "node => node.contentWindow.postMessage({channel:'ycet-prototype',version:1,type:'set-screen',screen:'pages/中文 页面.html'}, '*')"
    )
    inner_frame.locator("#unicode-page").wait_for()

    # 功能三运行时副本必须通过同一受控白名单加载。
    page.locator("#frame").evaluate(
        "node => node.contentWindow.postMessage({channel:'ycet-prototype',version:1,type:'set-screen',screen:'runtime-pages/runtime-page--prototype.html'}, '*')"
    )
    inner_frame.locator("#runtime-page").wait_for()
    inner_frame.locator("#runtime-next").click()
    inner_frame.locator("#runtime-page-two").wait_for()
    page.wait_for_function(
        "window.events.some(event => event.type === 'navigate' && event.targetPage === 'runtime-pages/runtime-two--prototype.html')"
    )

    # 普通及编码后的目录穿越都必须被拒绝，并保留当前页面。
    for invalid in ("../evil.html", "pages/%2e%2e/evil.html", "https://example.com/evil.html"):
        previous_errors = page.evaluate(
            "window.events.filter(event => event.type === 'error').length"
        )
        page.locator("#frame").evaluate(
            "(node, screen) => node.contentWindow.postMessage({channel:'ycet-prototype',version:1,type:'set-screen',screen}, '*')",
            invalid,
        )
        page.wait_for_function(
            "count => window.events.filter(event => event.type === 'error').length > count",
            arg=previous_errors,
        )
        inner_frame.locator("#runtime-page-two").wait_for()


def exercise_preview(page, frame: dict[str, object]) -> None:
    """验证 design-direction 的首页预览可加载。"""

    page.wait_for_load_state("networkidle")
    scrollbar_width = page.locator("html").evaluate("node => getComputedStyle(node).scrollbarWidth")
    assert scrollbar_width == "none", (frame["id"], scrollbar_width)
    page.frame_locator("#frame").frame_locator("#screen").locator("#home-preview").wait_for()


def test_frame(browser, skill_dir: Path, frame: dict[str, object]) -> None:
    """通过 HTTP、file 协议和移动目录验证单个框架。"""

    with tempfile.TemporaryDirectory(prefix="YCET 可移植 测试 ") as temp:
        temp_dir = Path(temp)
        fixture_dir = temp_dir / "原始 项目"
        build_fixture(skill_dir, fixture_dir, frame)
        handler = lambda *args, **kwargs: QuietHandler(*args, directory=fixture_dir, **kwargs)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
            exercise_frame_page(page, frame, expect_empty_referrer=False)
            page.goto(f"http://127.0.0.1:{server.server_port}/design-direction.html")
            exercise_preview(page, frame)
            page.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        # 复制整个项目后再通过 file:// 打开，覆盖空 referrer、中文和空格目录。
        moved_dir = temp_dir / "移动 后 项目"
        shutil.copytree(fixture_dir, moved_dir)
        page = browser.new_page()
        try:
            page.goto((moved_dir / "index.html").as_uri())
            exercise_frame_page(page, frame, expect_empty_referrer=True)
            page.goto((moved_dir / "design-direction.html").as_uri())
            exercise_preview(page, frame)
        finally:
            page.close()


def launch_browser(playwright, target: str):
    """启动指定浏览器；Chrome/Edge 使用系统安装通道。"""

    if target in {"chrome", "msedge"}:
        return playwright.chromium.launch(channel=target, headless=True)
    if target in {"chromium", "firefox", "webkit"}:
        return getattr(playwright, target).launch(headless=True)
    raise ValueError(f"不支持的浏览器目标：{target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="待验证的 ycet-prototype-create Skill 目录",
    )
    parser.add_argument(
        "--browsers",
        default="chromium,chrome,msedge,firefox",
        help="逗号分隔的浏览器目标：chromium、chrome、msedge、firefox、webkit",
    )
    parser.add_argument(
        "--require-firefox",
        action="store_true",
        help="Firefox 不可启动时也判定测试失败",
    )
    args = parser.parse_args()
    skill_dir = args.skill_dir.resolve()
    manifest = json.loads((skill_dir / "assets" / "frames" / "manifest.json").read_text(encoding="utf-8"))
    targets = [target.strip() for target in args.browsers.split(",") if target.strip()]
    if not targets:
        print("[FAIL] 未指定浏览器目标")
        return 1

    with sync_playwright() as playwright:
        tested_targets: list[str] = []
        skipped_targets: list[str] = []
        for target in targets:
            try:
                browser = launch_browser(playwright, target)
            except (PlaywrightError, ValueError) as exc:
                first_line = str(exc).splitlines()[0]
                print(f"[SKIP] {target}: {first_line}")
                skipped_targets.append(target)
                continue

            try:
                for frame in manifest["frames"]:
                    test_frame(browser, skill_dir, frame)
                    print(f"[OK] {target}/{frame['id']}")
                tested_targets.append(target)
            finally:
                browser.close()

    if not tested_targets:
        print("[FAIL] 没有可启动的浏览器，运行时验证未执行")
        return 1
    if args.require_firefox and "firefox" not in tested_targets:
        print("[FAIL] 已要求 Firefox，但 Firefox 未完成运行时验证")
        return 1

    print(
        f"[OK] 运行时验证通过：{len(manifest['frames'])} 个框架；"
        f"已测试 {', '.join(tested_targets)}；跳过 {', '.join(skipped_targets) or '无'}。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
