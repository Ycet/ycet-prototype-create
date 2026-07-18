#!/usr/bin/env python3
"""使用当前可用浏览器验证功能五单文件的移动视口、导航和离线可移植性。"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


BUILDER = Path(__file__).with_name("build_mobile_prototype.py")
HOME = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>首页</title>
<style>html,body{width:100%;height:100%;margin:0;overflow:hidden}main{min-height:100%;padding:72px 16px;background:#f8fafc}</style></head>
<body><main id="home"><button id="next" type="button">查看详情</button></main>
<script>document.getElementById("next").onclick=()=>parent.postMessage({channel:"ycet-prototype",version:1,type:"navigate",targetPage:"runtime-pages/detail--prototype.html?from=home#top"},"*");</script>
</body></html>"""
DETAIL = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>详情</title>
<style>html,body{width:100%;height:100%;margin:0;overflow:hidden}main{min-height:100%;background:#fff}</style></head>
<body><main id="detail"><h1>详情</h1></main></body></html>"""
PROTOTYPE = """<!doctype html><script>
const pages = [
  { id: "home", label: "首页", sourcePath: "pages/home.html", runtimePath: "runtime-pages/home--prototype.html", initial: true },
  { id: "detail", label: "详情", sourcePath: "pages/detail.html", runtimePath: "runtime-pages/detail--prototype.html" }
];
</script>"""


def build_fixture(root: Path) -> Path:
    prototype = root / "prototype"
    runtime = prototype / "runtime-pages"
    runtime.mkdir(parents=True)
    (runtime / "home--prototype.html").write_text(HOME, encoding="utf-8")
    (runtime / "detail--prototype.html").write_text(DETAIL, encoding="utf-8")
    (prototype / "prototype.html").write_text(PROTOTYPE, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(BUILDER), "--prototype-dir", str(prototype)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)

    portable_dir = root / "项目外 手机预览"
    portable_dir.mkdir()
    portable = portable_dir / "prototype-mobile.html"
    shutil.copy2(prototype / "prototype-mobile.html", portable)
    return portable


def launch_browser(playwright, target: str):
    if target in {"chrome", "msedge"}:
        return playwright.chromium.launch(channel=target, headless=True)
    return getattr(playwright, target).launch(headless=True)


def exercise(browser, mobile_file: Path) -> None:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.set_offline(True)
    page = context.new_page()
    try:
        page.goto(mobile_file.as_uri(), wait_until="load")
        frame = page.frame_locator("#mobile-screen")
        frame.locator("#home").wait_for()

        size = page.locator("#mobile-screen").evaluate(
            "node => ({x: node.getBoundingClientRect().x, y: node.getBoundingClientRect().y, "
            "width: node.getBoundingClientRect().width, height: node.getBoundingClientRect().height})"
        )
        assert size == {"x": 0, "y": 0, "width": 390, "height": 844}, size
        scroll = page.locator("html").evaluate(
            "node => ({width: node.scrollWidth, clientWidth: node.clientWidth, height: node.scrollHeight, clientHeight: node.clientHeight})"
        )
        assert scroll["width"] == scroll["clientWidth"] and scroll["height"] == scroll["clientHeight"], scroll

        page.locator("#menu-button").click()
        assert page.locator("body").evaluate("node => node.classList.contains('drawer-open')")
        assert page.locator("#navigation-drawer").get_attribute("aria-hidden") == "false"
        assert page.locator('.page-button[aria-current="page"]').inner_text().endswith("首页")
        page.locator("#drawer-overlay").click(position={"x": 380, "y": 400})
        assert page.locator("#navigation-drawer").get_attribute("aria-hidden") == "true"

        frame.locator("#next").click()
        frame.locator("#detail").wait_for()
        page.wait_for_function("history.state && history.state.target.includes('?from=home#top')")
        assert page.locator('.page-button[aria-current="page"]').inner_text().endswith("详情")

        page.go_back()
        frame.locator("#home").wait_for()
        assert page.locator('.page-button[aria-current="page"]').inner_text().endswith("首页")

        page.locator("#menu-button").click()
        page.locator('.page-button[data-page-id="detail"]').click()
        frame.locator("#detail").wait_for()
        assert page.locator("#navigation-drawer").get_attribute("aria-hidden") == "true"

        page.set_viewport_size({"width": 844, "height": 390})
        page.wait_for_timeout(100)
        landscape = page.locator("#mobile-screen").evaluate(
            "node => ({width: node.getBoundingClientRect().width, height: node.getBoundingClientRect().height})"
        )
        assert landscape == {"width": 844, "height": 390}, landscape
    finally:
        context.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--browsers",
        default="chromium,chrome,msedge,firefox",
        help="逗号分隔的浏览器目标：chromium、chrome、msedge、firefox、webkit",
    )
    parser.add_argument("--require-browser", action="store_true", help="没有任何浏览器通过时返回失败")
    args = parser.parse_args()
    targets = [item.strip() for item in args.browsers.split(",") if item.strip()]

    passed: list[str] = []
    skipped: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ycet-mobile-runtime-") as temp:
        mobile_file = build_fixture(Path(temp))
        with sync_playwright() as playwright:
            for target in targets:
                try:
                    browser = launch_browser(playwright, target)
                except (AttributeError, PlaywrightError, OSError) as exc:
                    skipped.append(f"{target}: {exc}")
                    print(f"[SKIP] {target} 无法启动：{exc}")
                    continue
                try:
                    exercise(browser, mobile_file)
                    passed.append(target)
                    print(f"[OK] {target} 移动端离线单文件运行时通过。")
                except (AssertionError, PlaywrightError) as exc:
                    print(f"[FAIL] {target}：{exc}")
                    return 1
                finally:
                    browser.close()

    if not passed:
        print("[SKIP] 当前环境没有可运行的浏览器目标。")
        return 1 if args.require_browser else 0
    print(f"[OK] 已通过浏览器：{', '.join(passed)}；跳过：{len(skipped)}。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
