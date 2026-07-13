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

    print("[OK] prototype_guard 回归测试通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
