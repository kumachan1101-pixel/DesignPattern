#!/usr/bin/env python3
"""Detect unused inputs in the published current and final C++ programs."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from check_execution_output import (
    BOOK_ROOT,
    SECTIONS,
    configured_chapter_paths,
    cpp_blocks,
    section_text,
)


def warning_errors(source: str) -> list[str]:
    """Compile with warnings as errors and return the relevant diagnostics."""
    with tempfile.TemporaryDirectory() as directory:
        cpp = Path(directory) / "chapter.cpp"
        executable = Path(directory) / "chapter.exe"
        cpp.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [
                "g++", "-std=c++14", "-Wall", "-Wextra", "-Werror",
                str(cpp), "-o", str(executable),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    if result.returncode == 0:
        return []
    diagnostics = [
        line for line in result.stderr.splitlines()
        if "error:" in line or "[-Werror" in line
    ]
    return diagnostics or result.stderr.splitlines()[:5]


def unused_struct_fields(source: str) -> list[str]:
    """Return public data fields that appear only in their declaration."""
    unused: list[str] = []
    for match in re.finditer(r"\bstruct\s+(\w+)\s*\{(.*?)\};", source, re.S):
        struct_name, body = match.group(1), match.group(2)
        for raw_line in body.splitlines():
            line = raw_line.split("//", 1)[0].strip()
            if (
                not line
                or "(" in line
                or line.startswith((
                    "using ", "enum ", "struct ", "class ", "template",
                ))
            ):
                continue
            field_match = re.match(
                r"(?:[\w:<>]+(?:\s*[&*])?\s+)+(\w+)"
                r"\s*(?:\{[^;]*\}|=[^;]*)?;",
                line,
            )
            if not field_match:
                continue
            field = field_match.group(1)
            if len(re.findall(rf"\b{re.escape(field)}\b", source)) < 2:
                unused.append(f"{struct_name}::{field}")
    return unused


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        help="分冊のbook.json。省略時は元の全章を検査する",
    )
    args = parser.parse_args()
    config = Path(args.config) if args.config else None
    if config is not None and not config.is_absolute():
        config = BOOK_ROOT / config
    if config is not None and not config.exists():
        print(f"FAILED: {config} がありません")
        return 1

    problems = 0
    for path in configured_chapter_paths(config):
        chapter = path.name
        if not path.exists():
            print(f"{chapter}: ファイルなし")
            problems += 1
            continue
        text = path.read_text(encoding="utf-8")
        for heading, end_heading in SECTIONS:
            section = section_text(text, heading, end_heading)
            if section is None:
                continue
            source = "\n\n".join(cpp_blocks(section))
            if "int main(" not in source:
                continue

            diagnostics = warning_errors(source)
            if diagnostics:
                problems += 1
                print(f"{chapter} {heading} 警告または未使用入力があります")
                for diagnostic in diagnostics[:5]:
                    print(f"    {diagnostic}")

            fields = unused_struct_fields(source)
            if fields:
                problems += 1
                print(
                    f"{chapter} {heading} 宣言だけで参照されない入力フィールド: "
                    + ", ".join(fields)
                )

    if problems:
        print(f"NG: 未使用入力の疑いがある節 {problems} 件")
        return 1
    print("OK: 対象章の1-4・7-1に未使用の引数・変数・入力フィールドはありません")
    return 0


if __name__ == "__main__":
    sys.exit(main())
