#!/usr/bin/env python3
"""回归测试功能五离线单文件打包器。"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


BUILDER = Path(__file__).with_name("build_mobile_prototype.py")
REGISTRY_PATTERN = re.compile(
    r'<script id="ycet-mobile-pages" type="application/json">(.*?)</script>',
    re.DOTALL,
)
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def run_builder(prototype: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(BUILDER), "--prototype-dir", str(prototype), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_snapshot(prototype: Path) -> dict[str, str]:
    return {
        path.relative_to(prototype).as_posix(): sha256(path)
        for path in sorted(prototype.rglob("*"))
        if path.is_file() and not re.fullmatch(r"prototype-mobile(?:-v\d+)?\.html", path.name)
    }


def create_valid_fixture(root: Path, include_prototype: bool = True) -> Path:
    prototype = root / "prototype"
    runtime = prototype / "runtime-pages"
    styles = prototype / "assets" / "styles"
    scripts = prototype / "assets" / "scripts"
    data = prototype / "assets" / "data"
    images = prototype / "assets" / "images"
    fonts = prototype / "assets" / "fonts"
    for directory in (runtime, styles, scripts, data, images, fonts):
        directory.mkdir(parents=True, exist_ok=True)

    (images / "pixel.png").write_bytes(PNG_1X1)
    (images / "icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><symbol id="mark"><path d="M0 0h1v1H0z" /></symbol></svg>',
        encoding="utf-8",
    )
    (fonts / "ui.woff2").write_bytes(b"woff2-placeholder")
    (styles / "theme.css").write_text(":root { --accent: #2563eb; }", encoding="utf-8")
    (styles / "main.css").write_text(
        """@import "./theme.css";
@font-face { font-family: Demo; src: url("../fonts/ui.woff2") format("woff2"); }
html, body { margin: 0; font-family: Demo, sans-serif; }
.hero { background-image: url("../images/pixel.png?v=1"); }
""",
        encoding="utf-8",
    )
    (scripts / "page.js").write_text(
        '//comment-without-space-is-not-a-network-url\n'
        'document.documentElement.dataset.scriptLoaded = "true";\n'
        'fetch("../data/info.json").then((response) => response.json());',
        encoding="utf-8",
    )
    (scripts / "module-helper.js").write_text('export const label = "module-ok";', encoding="utf-8")
    (scripts / "module-entry.js").write_text(
        'import { label } from "./module-helper.js";\n'
        'document.documentElement.dataset.moduleLoaded = label;',
        encoding="utf-8",
    )
    (data / "info.json").write_text('{"offline":true}', encoding="utf-8")
    (runtime / "home--prototype.html").write_text(
        """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>首页</title>
  <link rel="stylesheet" href="../assets/styles/main.css" />
</head>
<body>
  <main class="hero">
    <img src="../assets/images/pixel.png" srcset="../assets/images/pixel.png 1x" alt="像素图" />
    <svg aria-hidden="true"><use href="../assets/images/icon.svg#mark"></use></svg>
    <button type="button" onclick='fetch("../assets/data/info.json")'>离线数据</button>
    <button id="open-detail" type="button">进入详情</button>
  </main>
  <script src="../assets/scripts/page.js"></script>
  <script type="module" src="../assets/scripts/module-entry.js"></script>
  <script>
    document.getElementById("open-detail").addEventListener("click", function () {
      window.parent.postMessage({
        channel: "ycet-prototype",
        version: 1,
        type: "navigate",
        "targetPage": "runtime-pages/detail--prototype.html?from=home#top"
      }, "*");
    });
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )
    (runtime / "detail--prototype.html").write_text(
        """<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8" /><title>详情</title></head>
<body><h1>详情页</h1><p>安全文本：&lt;/script&gt;、中文和空格。</p></body>
</html>
""",
        encoding="utf-8",
    )
    (prototype / "index.html").write_text("<!doctype html><title>静态入口</title>", encoding="utf-8")
    if include_prototype:
        (prototype / "prototype.html").write_text(
            """<!doctype html><script>
const pages = [
  { "id": "home", "label": "首页", "sourcePath": "pages/home.html", "runtimePath": "runtime-pages/home--prototype.html" },
  { id: "detail", label: "详情", sourcePath: "pages/detail.html", runtimePath: "runtime-pages/detail--prototype.html" }
];
</script>
""",
            encoding="utf-8",
        )
    return prototype


def read_mobile_registry(path: Path) -> list[dict[str, object]]:
    match = REGISTRY_PATTERN.search(path.read_text(encoding="utf-8"))
    assert match, "手机版文件缺少页面注册表"
    return json.loads(match.group(1))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ycet-mobile-builder-") as temp:
        root = Path(temp)
        prototype = create_valid_fixture(root / "complete")
        before = protected_snapshot(prototype)

        result = run_builder(prototype)
        assert result.returncode == 0, result.stdout + result.stderr
        first = prototype / "prototype-mobile.html"
        assert first.is_file(), "首次输出文件不存在"
        first_sha256 = sha256(first)
        assert protected_snapshot(prototype) == before, "首次打包修改了受保护输入"

        mobile = first.read_text(encoding="utf-8")
        assert 'data-ycet-mobile-prototype="true"' in mobile
        assert 'id="mobile-screen"' in mobile
        assert 'id="menu-button"' in mobile
        assert 'id="navigation-drawer"' in mobile
        registry = read_mobile_registry(first)
        assert [page["id"] for page in registry] == ["home", "detail"]
        home_srcdoc = base64.b64decode(str(registry[0]["srcdocBase64"])).decode("utf-8")
        assert "data:image/png;base64," in home_srcdoc
        assert "data:font/woff2;base64," in home_srcdoc
        assert "document.documentElement.dataset.scriptLoaded" in home_srcdoc
        assert 'fetch("data:application/json;base64,' in home_srcdoc
        assert "data:text/javascript;base64," in home_srcdoc
        assert "srcset=\"data:image/png;base64," in home_srcdoc
        assert "data:image/svg+xml;base64," in home_srcdoc and "#mark" in home_srcdoc
        assert 'id="ycet-mobile-viewport-adapter"' in home_srcdoc
        assert "?v=1" not in home_srcdoc
        assert "../assets/" not in home_srcdoc
        assert "http://" not in home_srcdoc and "https://" not in home_srcdoc

        result = run_builder(prototype)
        assert result.returncode == 0, result.stdout + result.stderr
        assert (prototype / "prototype-mobile-v2.html").is_file(), "二次输出未递增版本"
        assert sha256(first) == first_sha256, "二次生成覆盖了首个手机版本"
        assert protected_snapshot(prototype) == before, "二次打包修改了受保护输入"

        runtime_only = create_valid_fixture(root / "runtime-only", include_prototype=False)
        result = run_builder(runtime_only)
        assert result.returncode == 0, result.stdout + result.stderr
        runtime_registry = read_mobile_registry(runtime_only / "prototype-mobile.html")
        assert {page["id"] for page in runtime_registry} == {"home", "detail"}

        missing_runtime = root / "missing-runtime" / "prototype"
        missing_runtime.mkdir(parents=True)
        (missing_runtime / "prototype.html").write_text("<!doctype html>", encoding="utf-8")
        result = run_builder(missing_runtime)
        assert result.returncode == 1 and "runtime-pages" in result.stdout, result.stdout + result.stderr
        assert not (missing_runtime / "prototype-mobile.html").exists()

        missing_asset = create_valid_fixture(root / "missing-asset")
        (missing_asset / "assets" / "images" / "pixel.png").unlink()
        result = run_builder(missing_asset)
        assert result.returncode == 1 and "资源不存在" in result.stdout, result.stdout + result.stderr
        assert not (missing_asset / "prototype-mobile.html").exists()

        remote_asset = create_valid_fixture(root / "remote-asset")
        home_path = remote_asset / "runtime-pages" / "home--prototype.html"
        home_path.write_text(
            home_path.read_text(encoding="utf-8").replace(
                "../assets/images/pixel.png",
                "https://example.com/pixel.png",
            ),
            encoding="utf-8",
        )
        result = run_builder(remote_asset)
        assert result.returncode == 1 and "远程依赖" in result.stdout, result.stdout + result.stderr
        assert not (remote_asset / "prototype-mobile.html").exists()

        dangling_target = create_valid_fixture(root / "dangling-target")
        dangling_home = dangling_target / "runtime-pages" / "home--prototype.html"
        dangling_home.write_text(
            dangling_home.read_text(encoding="utf-8").replace(
                "runtime-pages/detail--prototype.html?from=home#top",
                "runtime-pages/missing--prototype.html",
            ),
            encoding="utf-8",
        )
        result = run_builder(dangling_target)
        assert result.returncode == 1 and "悬空" in result.stdout, result.stdout + result.stderr
        assert not (dangling_target / "prototype-mobile.html").exists()

        traversal_asset = create_valid_fixture(root / "traversal-asset")
        traversal_home = traversal_asset / "runtime-pages" / "home--prototype.html"
        traversal_home.write_text(
            traversal_home.read_text(encoding="utf-8").replace(
                "../assets/images/pixel.png",
                "../../outside.png",
                1,
            ),
            encoding="utf-8",
        )
        result = run_builder(traversal_asset)
        assert result.returncode == 1 and "路径越界" in result.stdout, result.stdout + result.stderr
        assert not (traversal_asset / "prototype-mobile.html").exists()

        conflicting_versions = create_valid_fixture(root / "conflicting-versions", include_prototype=False)
        conflict_runtime = conflicting_versions / "runtime-pages"
        for source in ("home", "detail"):
            original = conflict_runtime / f"{source}--prototype.html"
            (conflict_runtime / f"{source}--prototype-v2.html").write_bytes(original.read_bytes())
        result = run_builder(conflicting_versions)
        assert result.returncode == 1 and "多个版本" in result.stdout, result.stdout + result.stderr
        assert not (conflicting_versions / "prototype-mobile.html").exists()

        remote_form = create_valid_fixture(root / "remote-form")
        form_home = remote_form / "runtime-pages" / "home--prototype.html"
        form_home.write_text(
            form_home.read_text(encoding="utf-8").replace(
                '<main class="hero">',
                '<form action="https://example.com/submit"><main class="hero">',
            ).replace("</main>", "</main></form>", 1),
            encoding="utf-8",
        )
        result = run_builder(remote_form)
        assert result.returncode == 1 and "表单提交" in result.stdout, result.stdout + result.stderr
        assert not (remote_form / "prototype-mobile.html").exists()

    print("[OK] 功能五单文件打包器回归测试通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
