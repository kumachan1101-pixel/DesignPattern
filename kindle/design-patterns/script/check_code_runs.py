#!/usr/bin/env python3
"""掲載コードを連結・コンパイル・実行し、掲載した実行結果と照合する。

第0章は「上から順に1つの `.cpp` へ貼れば、そのまま1つのC++14プログラムとして
動きます」と読者へ約束している。読者が最初に試すのはこれなので、その約束が
守られているかを機械で確かめる。

各章の「現状コード」「完成コード」について、次を見る。

  1. 掲載ブロックを上から連結すると、C++14としてコンパイルできる
  2. 実行できる（異常終了しない）
  3. 本文に載せた実行結果が、実際の出力にそのまま含まれる

3は「説明・コード・実行結果の食い違い」を直接捕まえる。掲載結果のラベルだけ
直してコードの `std::cout` を直し忘れる、といった不整合はここで落ちる。

`main()` は「1定義1ブロック」の方針で複数ブロックへ割れることがあるため、
波括弧が閉じるまで続けて拾う。エラー出力は `std::cerr` へ出る章があるので、
標準エラーを標準出力へ合流させて順序ごと比較する。

    python3 script/check_code_runs.py --config books/<冊>/publishing/book.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]

# 連結して動かす対象の節と、その節が属するフェーズ区間の終わり。
TARGETS = (
    ("現状コード", r"##\s*🟣\s*フェーズ2"),
    ("完成コード", r"###\s*7-2"),
)


def normalize(text: str) -> str:
    return "\n".join(l.rstrip() for l in text.strip().split("\n") if l.strip())


def strip_literals(code: str) -> str:
    """波括弧を数えるために、文字列・文字・行コメントを落とす。"""
    code = re.sub(r'"(\\.|[^"\\])*"', '""', code)
    code = re.sub(r"'(\\.|[^'\\])*'", "''", code)
    return re.sub(r"//[^\n]*", "", code)


def gather_program(text: str, heading: str) -> tuple[str, int] | tuple[None, None]:
    """見出しから、main() が閉じるまでの cpp ブロックを順に連結する。"""
    found = re.search(rf"^####\s*{heading}\s*$", text, re.M)
    if not found:
        return None, None
    start = found.end()
    parts: list[str] = []
    end = start
    seen_main = False
    for block in re.finditer(r"```cpp\n(.*?)```", text[start:], re.S):
        parts.append(block.group(1))
        end = start + block.end()
        if re.search(r"\bint\s+main\s*\(", block.group(1)):
            seen_main = True
        if seen_main:
            joined = strip_literals("\n".join(parts))
            if joined.count("{") == joined.count("}"):
                break
    if not seen_main:
        return None, None
    return "\n".join(parts), end


def published_results(text: str, heading: str, phase_end: str) -> list[str]:
    """その節が属する区間の、言語指定なしブロックのうち実行結果に見えるもの。"""
    found = re.search(rf"^####\s*{heading}\s*$", text, re.M)
    if not found:
        return []
    tail = re.search(phase_end, text[found.end():])
    segment = text[found.end(): found.end() + (tail.start() if tail else len(text))]
    fenced = re.findall(r"^```(\w*)\n(.*?)^```", segment, re.S | re.M)
    return [body for lang, body in fenced
            if lang == "" and re.search(r"^--- 行\d", body, re.M)]


def check(config_path: Path) -> int:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    chapters = [BOOK_ROOT / c for c in data.get("chapters", [])]
    failures: list[str] = []
    checked = 0

    if not shutil.which("g++"):
        print("SKIP: g++ が無いため掲載コードの実行検査を行いません")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for path in chapters:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for heading, phase_end in TARGETS:
                program, _ = gather_program(text, heading)
                if program is None:
                    continue
                checked += 1
                source = work / f"{path.stem}_{heading}.cpp"
                source.write_text(program, encoding="utf-8")
                binary = source.with_suffix("")
                built = subprocess.run(
                    ["g++", "-std=c++14", "-o", str(binary), str(source)],
                    capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                )
                if built.returncode != 0:
                    first = next(
                        (l for l in built.stderr.splitlines() if "error:" in l), ""
                    )
                    failures.append(
                        f"{path.name} の「{heading}」を上から連結してもコンパイルできません"
                        f"（{len(program.splitlines())}行）: {first.strip()[:120]}"
                    )
                    continue
                try:
                    run = subprocess.run(
                        [str(binary)], stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True,
                        encoding="utf-8", errors="replace", timeout=30,
                    )
                except subprocess.TimeoutExpired:
                    failures.append(f"{path.name} の「{heading}」が30秒で終わりません")
                    continue
                if run.returncode != 0:
                    failures.append(
                        f"{path.name} の「{heading}」が終了コード {run.returncode} で落ちます"
                    )
                    continue
                actual = normalize(run.stdout)
                for block in published_results(text, heading, phase_end):
                    if normalize(block) not in actual:
                        head = normalize(block).split("\n")[0]
                        missing = next(
                            (l for l in normalize(block).split("\n")
                             if l not in actual), head
                        )
                        failures.append(
                            f"{path.name} の「{heading}」に載せた実行結果が、実際の出力に"
                            f"ありません（{head[:40]} … 一致しない行: {missing[:60]}）"
                        )

    if failures:
        print("\n".join(failures))
        print(f"\nFAILED: {len(failures)} code issue(s) in {config_path.name}")
        return 1
    print(f"OK: 掲載コード {checked} 本がコンパイル・実行でき、載せた実行結果と一致します")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="検査する冊の book.json")
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = BOOK_ROOT / config_path
    if not config_path.exists():
        print(f"FAILED: {config_path} がありません")
        return 1
    return check(config_path)


if __name__ == "__main__":
    sys.exit(main())
