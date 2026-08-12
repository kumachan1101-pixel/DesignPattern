#!/usr/bin/env python3
"""Render every Mermaid block in the published chapters with Mermaid CLI."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BOOK_ROOT / "output"


TOOLS_DIR = BOOK_ROOT / "script" / ".mermaid-tools"

# Puppeteer が自前で落としてくる Chrome ではなく、環境にすでにある Chromium を使う。
# CI（ubuntu-latest）と Playwright 同梱環境の両方で見つかるパスを順に見る。
CHROMIUM_CANDIDATES = (
    "/opt/pw-browsers/chromium",          # Playwright 同梱（Claude Code 実行環境など）
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
)


def find_mmdc() -> str | None:
    """PATH の mmdc を優先し、無ければリポジトリ内へ入れたものを使う。

    Windows では PowerShell スクリプトの実行が止められることがあるため、
    先に `.cmd` シムを見る。
    """
    found = shutil.which("mmdc.cmd") or shutil.which("mmdc")
    if found:
        return found
    for name in ("mmdc.cmd", "mmdc"):
        local = TOOLS_DIR / "node_modules" / ".bin" / name
        if local.exists():
            return str(local)
    return None


def find_chromium() -> str | None:
    """mermaid-cli へ渡す Chromium を探す。"""
    explicit = os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    if explicit and Path(explicit).exists():
        return explicit
    for candidate in CHROMIUM_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return shutil.which("chromium") or shutil.which("google-chrome")


def puppeteer_config(temp_root: Path) -> list[str]:
    """`-p` へ渡す puppeteer 設定を作る。見つからなければ何も渡さない。

    mermaid-cli は PUPPETEER_EXECUTABLE_PATH などの環境変数を読まず、`-p` の
    設定ファイルしか見ない。CI やコンテナは root で動くので --no-sandbox も要る。
    """
    chromium = find_chromium()
    if not chromium:
        return []
    config = temp_root / "puppeteer-config.json"
    config.write_text(
        json.dumps({
            "executablePath": chromium,
            "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        }),
        encoding="utf-8",
    )
    return ["-p", str(config)]


def main() -> int:
    mmdc = find_mmdc()
    if not mmdc:
        print("FAILED: Mermaid CLI (mmdc) is not installed or is not on PATH")
        print("  導入: bash kindle/design-patterns/script/setup_mermaid.sh")
        return 1

    chapter_paths = sorted(OUTPUT_DIR.glob("chapter*.md"))
    total_blocks = 0
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="design-pattern-mermaid-") as temp_name:
        temp_root = Path(temp_name)
        pptr_args = puppeteer_config(temp_root)
        for path in chapter_paths:
            text = path.read_text(encoding="utf-8")
            blocks = re.findall(r"```mermaid\s*\n(.*?)\n```", text, re.DOTALL)
            if not blocks:
                continue
            total_blocks += len(blocks)
            for index, block in enumerate(blocks, 1):
                if r"\n" in block:
                    failures.append(
                        f"{path.name}: Mermaid block {index} contains literal \\n; use <br/>"
                    )

            artefacts = temp_root / f"{path.stem}-artefacts"
            rendered_markdown = temp_root / path.name
            result = subprocess.run(
                [
                    mmdc,
                    "-i", str(path),
                    "-o", str(rendered_markdown),
                    "-a", str(artefacts),
                    "-q",
                ] + pptr_args,
                cwd=BOOK_ROOT,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                details = (result.stderr or result.stdout).strip()
                failures.append(
                    f"{path.name}: Mermaid CLI failed\n{details}"
                )
                continue
            rendered_count = len(list(artefacts.glob("*.svg")))
            if rendered_count != len(blocks):
                failures.append(
                    f"{path.name}: rendered {rendered_count}/{len(blocks)} diagrams"
                )
            else:
                print(f"OK: {path.name} rendered {rendered_count} diagram(s)")

    if failures:
        print("\n".join(failures))
        print(f"\nFAILED: {len(failures)} Mermaid issue(s)")
        return 1
    print(
        f"OK: rendered all {total_blocks} Mermaid diagrams "
        f"from {len(chapter_paths)} chapter files"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
