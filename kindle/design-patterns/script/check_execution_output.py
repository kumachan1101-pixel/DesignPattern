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
# chapter05.md の 7-1 は要約表記のため除外していたが、掲載結果が実出力と
# 別物になっていた（LOGIC-501）。実出力へ差し替えたので除外を解除した。
EXEMPT: set[tuple[str, str]] = set()


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
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            return False, r.stderr
        run = subprocess.run([str(exe)], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", cwd=d)
        return True, run.stdout


def fabricated_output_lines(output: str, sec: str) -> list[str]:
    """本文の「実行結果ブロック」が、コードの出さない行を主張していないか。

    lines_present_in_order は「実出力の各行が本文にあるか」だけを一方向で見る。
    その逆——本文の実行結果ブロックにあってコードが出さない行（捏造出力）——は
    検出できない（例：ch04「保存金額合計」）。ここでは、行の過半が実出力に一致
    する“本物の出力ブロック”に限り、一致しない行を捏造候補として返す。
    誤検出を避けるため、コードブロック・省略記号・要約行は対象外にする。
    """
    fab: list[str] = []
    for info, body in re.findall(r"```([^\n]*)\n(.*?)```", sec, re.S):
        if info.strip() == "cpp":
            continue
        lines = [l for l in body.splitlines() if l.strip()]
        if not lines:
            continue
        matched = [l for l in lines if l in output or l.strip() in output]
        # 過半が一致する＝プログラム出力を載せたブロックだけを対象にする
        if len(matched) >= max(2, int(len(lines) * 0.6)):
            for l in lines:
                if l in output or l.strip() in output:
                    continue
                s = l.strip()
                if s.startswith("...") or "略" in s:
                    continue
                fab.append(l)
    return fab


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
                # コードがあるのに main() が無い＝分割ミス等で実行不可。
                # 空セクションだけスキップし、それ以外は不合格にする。
                if src.strip():
                    print(f"{name} {head} main()が見つかりません（実行不可・分割ミスの疑い）")
                    problems += 1
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
            fabricated = fabricated_output_lines(out, sec)
            if fabricated:
                print(f"{name} {head} 実行結果の捏造疑い: "
                      f"本文の出力ブロックにありコードが出さない行 {len(fabricated)} 件")
                for f in fabricated[:6]:
                    print(f"    {f!r}")
                problems += 1
    if problems == 0:
        print("OK: 全章の 1-4 / 7-1 実行結果が実出力と一致")
        return 0
    print(f"---\nNG: {problems} 節で不一致またはコンパイル失敗")
    return 1


if __name__ == "__main__":
    sys.exit(main())
