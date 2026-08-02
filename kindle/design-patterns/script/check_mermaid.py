#!/usr/bin/env python3
"""Render every Mermaid block in the published chapters with Mermaid CLI."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BOOK_ROOT / "output"


def find_mmdc() -> str | None:
    """Prefer the Windows command shim because PowerShell scripts may be blocked."""
    return shutil.which("mmdc.cmd") or shutil.which("mmdc")


def main() -> int:
    mmdc = find_mmdc()
    if not mmdc:
        print("FAILED: Mermaid CLI (mmdc) is not installed or is not on PATH")
        return 1

    chapter_paths = sorted(OUTPUT_DIR.glob("chapter*.md"))
    total_blocks = 0
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="design-pattern-mermaid-") as temp_name:
        temp_root = Path(temp_name)
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
                ],
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
