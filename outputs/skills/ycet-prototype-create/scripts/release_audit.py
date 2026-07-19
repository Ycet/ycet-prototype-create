"""检查 ycet-prototype-create 交付目录是否满足发布前的基本卫生要求。"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


REQUIRED_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "assets/frames/manifest.json",
    "assets/workbench/index.html",
    "assets/workbench/styles.css",
    "assets/workbench/app.js",
    "assets/workbench/preview-runtime.js",
    "docs/shared-workbench-protocol.md",
    "docs/function-1-static-prototype.md",
    "docs/function-2-precision-edit.md",
    "docs/function-3-interactive-demo.md",
    "docs/function-4-existing-prototype-edit.md",
    "docs/function-5-mobile-single-file.md",
    "scripts/prototype_workbench.py",
)


def digest(path: Path) -> str:
    """按字节计算文件摘要，避免编码差异影响版本比较。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(skill_root: Path, installed_root: Path | None = None) -> list[str]:
    findings: list[str] = []
    for relative in REQUIRED_FILES:
        if not (skill_root / relative).is_file():
            findings.append(f"缺少必需文件：{relative}")

    skill_file = skill_root / "SKILL.md"
    if skill_file.is_file():
        lines = skill_file.read_text(encoding="utf-8").splitlines()
        if len(lines) > 500:
            findings.append(f"SKILL.md 超过 500 行：{len(lines)} 行")
        if "可视化工作台" not in skill_file.read_text(encoding="utf-8"):
            findings.append("SKILL.md 没有声明可视化工作台路由")

    # 过程截图和 Python 缓存不能进入可复制的 Skill 交付包。
    generated_dirs = (skill_root / "test-artifacts", skill_root / "scripts" / "__pycache__")
    for directory in generated_dirs:
        if directory.exists():
            findings.append(f"交付目录包含测试生成目录：{directory.relative_to(skill_root)}")
    generated_files = list(skill_root.rglob("*.pyc"))
    for generated_file in generated_files:
        findings.append(f"交付目录包含 Python 缓存：{generated_file.relative_to(skill_root)}")

    if (skill_root / "README.md").exists():
        findings.append("Skill 根目录不应包含 README.md，应使用上层项目 README")

    if installed_root is not None:
        for relative in ("SKILL.md", "agents/openai.yaml"):
            source = skill_root / relative
            installed = installed_root / relative
            if source.is_file() and installed.is_file() and digest(source) != digest(installed):
                findings.append(f"全局 Skill 与交付目录不一致：{relative}")
            elif source.is_file() and not installed.is_file():
                findings.append(f"全局 Skill 缺少文件：{relative}")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="审计 ycet-prototype-create 交付目录")
    parser.add_argument("skill_root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--installed-skill", type=Path, help="可选：比较当前实际安装的 Skill 目录")
    args = parser.parse_args()

    findings = audit(args.skill_root.resolve(), args.installed_skill.resolve() if args.installed_skill else None)
    if findings:
        for finding in findings:
            print(f"[FAIL] {finding}")
        return 1
    print("[OK] 交付目录通过发布卫生审计。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
