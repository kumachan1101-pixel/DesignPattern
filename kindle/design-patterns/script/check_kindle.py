#!/usr/bin/env python3
"""Check Kindle-specific formatting invariants of the design-pattern book.

validate_book.py と audit_book.py が対象にしていない、Kindle 表示向けの
機械判定ルールだけを確認する。

- コードブロック（```cpp）の各行が 80 文字（文字数）以内か。
- Markdown 表のデータ列が 4 列以内か。

意味の正しさやレイアウトの良し悪しは、章レビューで別途確認する。
違反があれば一覧を出力し、終了コード 1 で終わる。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BOOK_ROOT / "output"

MAX_CODE_LINE = 80
MAX_TABLE_COLUMNS = 4


@dataclass
class Finding:
    chapter: str
    line: int
    category: str
    detail: str


def check_code_line_length(name: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    in_cpp = False
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.rstrip("\n")
        if stripped.startswith("```cpp"):
            in_cpp = True
            continue
        if stripped.startswith("```"):
            in_cpp = False
            continue
        if in_cpp and len(stripped) > MAX_CODE_LINE:
            findings.append(
                Finding(name, i, "code80",
                        f"コード行が{len(stripped)}文字（上限{MAX_CODE_LINE}）")
            )
    return findings


def is_separator_row(cells: list[str]) -> bool:
    body = [c.strip() for c in cells if c.strip()]
    return bool(body) and all(set(c) <= set("-: ") for c in body)


def check_table_columns(name: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = stripped.split("|")[1:-1]
        if is_separator_row(cells):
            continue
        columns = len(cells)
        if columns > MAX_TABLE_COLUMNS:
            findings.append(
                Finding(name, i, "table4",
                        f"表のデータ列が{columns}列（上限{MAX_TABLE_COLUMNS}）")
            )
    return findings


def main() -> int:
    files = sorted(OUTPUT_DIR.glob("chapter*.md"))
    if not files:
        print("出力章ファイルが見つかりません:", OUTPUT_DIR)
        return 1
    findings: list[Finding] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        findings.extend(check_code_line_length(path.name, text))
        findings.extend(check_table_columns(path.name, text))
    if not findings:
        print(f"OK: {len(files)} chapter files passed Kindle formatting checks")
        return 0
    findings.sort(key=lambda f: (f.chapter, f.line))
    for f in findings:
        print(f"{f.chapter}:{f.line}: [{f.category}] {f.detail}")
    code80 = sum(f.category == "code80" for f in findings)
    table4 = sum(f.category == "table4" for f in findings)
    print(f"---\nNG: 80文字超コード行 {code80} 件 / 4列超の表 {table4} 件")
    return 1


if __name__ == "__main__":
    sys.exit(main())
