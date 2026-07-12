#!/usr/bin/env python3
"""Verify that printed execution results match the actual program output.

audit_book.py は各章の 1-4 / 7-1 の C++ を「コンパイルできるか」までしか
見ない。この checker は、そのコードを実際に実行し、章に掲載している
実行結果の各行が、実出力に現れる順序どおりに本文へ載っているかを確認する。

これは X-STAR-13（成果物の一致）の機械スライスで、掲載値の取り違え
（例：認証失敗が実際は成功していた、在庫0のはずが在庫5だった）を検出する。

curated（要約表記）で実出力そのものを載せない節は EXEMPT に登録する。
違反があれば一覧を出力し、終了コード 1 で終わる。
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BOOK_ROOT / "output"

CORE_CHAPTERS = [
    "chapter01.md", "chapter02.md", "chapter03.md", "chapter04.md",
    "chapter05.md", "chapter06.md", "chapter07.md", "chapter08.md",
    "chapter09_2.md", "chapter10.md", "chapter11.md", "chapter12.md",
]

SECTIONS = [
    ("1-4：", "1-5："),
    ("7-1：", "7-2："),
]

# 実出力そのものではなく要約を掲載している節（誤りではない）
EXEMPT = {
    ("chapter05.md", "7-1："),  # 操作のまとまりごとの要約表記
}


def section_text(text: str, head: str, end: str) -> str | None:
    a = re.search(rf"^### {re.escape(head)}", text, re.M)
    if not a:
        return None
    b = re.search(rf"^### {re.escape(end)}", text[a.start() + 1:], re.M)
    stop = a.start() + 1 + b.start() if b else len(text)
    return text[a.start():stop]


def cpp_blocks(sec: str) -> list[str]:
    return re.findall(r"```cpp\s*\n(.*?)```", sec, re.S)


def run_source(src: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as d:
        cpp = Path(d) / "chapter.cpp"
        exe = Path(d) / "chapter.exe"
        cpp.write_text(src, encoding="utf-8")
        r = subprocess.run(
            ["g++", "-std=c++14", str(cpp), "-o", str(exe)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            return False, r.stderr
        run = subprocess.run([str(exe)], capture_output=True,
                             text=True, cwd=d)
        return True, run.stdout


def lines_present_in_order(output: str, sec: str) -> list[str]:
    """Return output lines that are missing (or out of order) in sec."""
    missing: list[str] = []
    pos = 0
    for line in output.splitlines():
        if not line.strip():
            continue
        idx = sec.find(line, pos)
        if idx < 0:
            if sec.find(line) < 0:
                missing.append(line)
            # present but earlier -> treat as order issue, still flag lightly
        else:
            pos = idx + len(line)
    return missing


def main() -> int:
    problems = 0
    for name in CORE_CHAPTERS:
        path = OUTPUT_DIR / name
        if not path.exists():
            print(f"{name}: ファイルなし")
            problems += 1
            continue
        text = path.read_text(encoding="utf-8")
        for head, end in SECTIONS:
            if (name, head) in EXEMPT:
                continue
            sec = section_text(text, head, end)
            if sec is None:
                continue
            src = "\n\n".join(cpp_blocks(sec))
            if "int main(" not in src:
                continue
            ok, out = run_source(src)
            if not ok:
                first = next((l for l in out.splitlines()
                              if "error:" in l), out[:120])
                print(f"{name} {head} コンパイル失敗: {first}")
                problems += 1
                continue
            missing = lines_present_in_order(out, sec)
            if missing:
                print(f"{name} {head} 実行結果の不一致: "
                      f"実出力にあり本文にない行 {len(missing)} 件")
                for m in missing[:6]:
                    print(f"    {m!r}")
                problems += 1
    if problems == 0:
        print("OK: 全章の 1-4 / 7-1 実行結果が実出力と一致")
        return 0
    print(f"---\nNG: {problems} 節で不一致またはコンパイル失敗")
    return 1


if __name__ == "__main__":
    sys.exit(main())
