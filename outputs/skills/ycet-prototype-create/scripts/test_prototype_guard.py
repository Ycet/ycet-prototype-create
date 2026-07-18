#!/usr/bin/env python3
"""回归测试静态交互边界与功能三只读输入保护。"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


GUARD = Path(__file__).with_name("prototype_guard.py")


def run_guard(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(GUARD), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ycet-prototype-guard-") as temp:
        prototype = Path(temp) / "prototype"
        pages = prototype / "pages"
        previews = prototype / "previews"
        pages.mkdir(parents=True)
        previews.mkdir()
        (prototype / "index.html").write_text("<!doctype html><title>入口</title>", encoding="utf-8")
        (pages / "home.html").write_text(
            '<!doctype html><button type="button" data-ycet-nav-target="pages/detail.html">详情</button>',
            encoding="utf-8",
        )
        (pages / "detail.html").write_text(
            '<!doctype html><a href="#dialog">打开弹窗</a>',
            encoding="utf-8",
        )
        (previews / "home-preview.html").write_text(
            '<!doctype html><button type="button" data-ycet-nav-target="pages/home.html">首页</button>',
            encoding="utf-8",
        )

        # 合法的意图元数据与同文档 fragment 必须通过。
        result = run_guard("static", "--prototype-dir", str(prototype))
        assert result.returncode == 0, result.stdout + result.stderr

        # 主动导航必须被拒绝。
        original_home = (pages / "home.html").read_text(encoding="utf-8")
        (pages / "home.html").write_text(
            original_home + '<script>location.href = "detail.html";</script>',
            encoding="utf-8",
        )
        result = run_guard("static", "--prototype-dir", str(prototype))
        assert result.returncode == 1 and "location.href" in result.stdout, result.stdout + result.stderr
        (pages / "home.html").write_text(original_home, encoding="utf-8")

        (pages / "home.html").write_text(
            original_home + '<script>parent.postMessage({"type":"navigate"}, "*");</script>',
            encoding="utf-8",
        )
        result = run_guard("static", "--prototype-dir", str(prototype))
        assert result.returncode == 1 and "navigate 消息" in result.stdout, result.stdout + result.stderr
        (pages / "home.html").write_text(original_home, encoding="utf-8")

        snapshot = Path(temp) / "protected-inputs.json"
        result = run_guard(
            "snapshot",
            "--prototype-dir",
            str(prototype),
            "--output",
            str(snapshot),
        )
        assert result.returncode == 0, result.stdout + result.stderr

        # 运行时副本不属于受保护集合，不应影响校验。
        runtime_pages = prototype / "runtime-pages"
        runtime_pages.mkdir()
        (runtime_pages / "home--prototype.html").write_text("<!doctype html>", encoding="utf-8")
        result = run_guard(
            "verify",
            "--prototype-dir",
            str(prototype),
            "--snapshot",
            str(snapshot),
        )
        assert result.returncode == 0, result.stdout + result.stderr

        # 修改或新增静态页都必须触发失败。
        (pages / "home.html").write_text(original_home + "\n", encoding="utf-8")
        result = run_guard(
            "verify",
            "--prototype-dir",
            str(prototype),
            "--snapshot",
            str(snapshot),
        )
        assert result.returncode == 1 and "文件字节发生变化" in result.stdout, result.stdout + result.stderr
        (pages / "home.html").write_text(original_home, encoding="utf-8")
        (pages / "new-page.html").write_text("<!doctype html>", encoding="utf-8")
        result = run_guard(
            "verify",
            "--prototype-dir",
            str(prototype),
            "--snapshot",
            str(snapshot),
        )
        assert result.returncode == 1 and "新增 HTML" in result.stdout, result.stdout + result.stderr

        # 图片原型的静态页和运行时副本必须统一引用 assets/images，并提供可见热区反馈。
        image_prototype = Path(temp) / "image-prototype"
        image_pages = image_prototype / "pages"
        image_runtime = image_prototype / "runtime-pages"
        image_assets = image_prototype / "assets" / "images"
        image_pages.mkdir(parents=True)
        image_runtime.mkdir()
        image_assets.mkdir(parents=True)
        (image_assets / "home.png").write_bytes(b"image-placeholder")
        (image_prototype / "index.html").write_text("<!doctype html><title>图片原型</title>", encoding="utf-8")
        (image_pages / "home.html").write_text(
            '<!doctype html><body data-ycet-image-prototype="true"><img src="../assets/images/home.png" alt="首页" /></body>',
            encoding="utf-8",
        )
        runtime_path = image_runtime / "home--prototype.html"
        runtime_html = '''<!doctype html>
<style>
.ycet-image-hotspot {
  position: absolute;
  outline: 1px dashed transparent;
  background: transparent;
  pointer-events: auto;
}
.ycet-image-hotspot:hover,
.ycet-image-hotspot:focus-visible {
  outline-color: rgba(37, 99, 235, 0.72);
}
</style>
<body data-ycet-image-prototype="true">
  <img src="../assets/images/home.png" alt="首页" />
  <button class="ycet-image-hotspot" data-ycet-nav-target="runtime-pages/detail--prototype.html" aria-label="查看详情"></button>
</body>'''
        runtime_path.write_text(runtime_html, encoding="utf-8")

        result = run_guard("image", "--prototype-dir", str(image_prototype), "--require-runtime")
        assert result.returncode == 0, result.stdout + result.stderr

        static_path = image_pages / "home.html"
        static_html = static_path.read_text(encoding="utf-8")
        static_path.write_text(
            static_html.replace("</body>", '<button data-ycet-nav-target="pages/detail.html"></button></body>'),
            encoding="utf-8",
        )
        result = run_guard("image", "--prototype-dir", str(image_prototype))
        assert result.returncode == 1 and "静态图片承载页不得包含跨页热区" in result.stdout, result.stdout + result.stderr
        static_path.write_text(static_html, encoding="utf-8")

        runtime_path.write_text(
            runtime_html.replace("../assets/images/home.png", "../pages/source-images/home.png"),
            encoding="utf-8",
        )
        result = run_guard("image", "--prototype-dir", str(image_prototype), "--require-runtime")
        assert result.returncode == 1 and "assets/images" in result.stdout, result.stdout + result.stderr
        runtime_path.write_text(runtime_html, encoding="utf-8")

        runtime_path.write_text(
            runtime_html.replace(".ycet-image-hotspot:hover", ".image-hotspot:hover"),
            encoding="utf-8",
        )
        result = run_guard("image", "--prototype-dir", str(image_prototype), "--require-runtime")
        assert result.returncode == 1 and "hover/focus-visible" in result.stdout, result.stdout + result.stderr

    print("[OK] prototype_guard 回归测试通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
