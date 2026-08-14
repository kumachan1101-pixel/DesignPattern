#!/usr/bin/env python3
"""1-1の代表入力が、そのまま動かせて掲載どおりの結果を出すかを確認する。

RUN-002（著者指摘）の検査。

    各章の最初の実行に関して、1行実行が多いが、何回か実行してステータス
    変化を見る場合は、そのようなところまで見せて欲しい。あとは、入力の
    準備とかも。

読者が最初に見るのは1-1の代表実行である。ここが1行だけだと、
(1) その1行を呼ぶまでに何を用意するのか、(2) 続けて呼ぶと状態がどう動くのか
が分からない。1-1は章の入口なので、ここで動きが見えないと以降が読めない。

そこで、1-1の代表入力コードを1-4のクラス定義へ結合して**実際にコンパイル・
実行し**、掲載している実行結果と一致するかを見る。これにより次を同時に担保する。

- 代表入力だけで完結している（使う実体をその抜粋の中で用意している）
- 掲載している実行結果が、その入力から実際に出る出力である
- 読者が貼り付けてそのまま動かせる

`check_execution_output.py` は1-4と7-1の**全体**を見る。こちらは1-1の**抜粋**が
単体で成立するかを見るもので、対象が違う。

    python3 script/check_representative_run.py
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

EXCERPT_LABEL = "**代表入力（1-4の`main()`から抜粋）：**"
RESULT_LEAD = "この入力に対する代表的な実行結果"

# 1-1で最低限見せる呼び出し回数。1回だと状態の移り変わりが見えない。
MIN_CALLS = 2


def cpp_blocks(text: str) -> list[str]:
    return re.findall(r"```cpp\n(.*?)```", text, re.S)


def chapter_issues(name: str) -> list[str]:
    path = OUTPUT_DIR / name
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    issues: list[str] = []

    label_at = text.find(EXCERPT_LABEL)
    if label_at < 0:
        return [f"{name}: 1-1に「{EXCERPT_LABEL}」がありません"]
    result_at = text.find(RESULT_LEAD, label_at)
    if result_at < 0:
        return [f"{name}: 代表入力の後に「{RESULT_LEAD}」がありません"]

    excerpt_match = re.search(
        r"```cpp\n(.*?)```", text[label_at:result_at], re.S)
    if not excerpt_match:
        return [f"{name}: 代表入力のC++ブロックがありません"]
    excerpt = excerpt_match.group(1)

    published_match = re.search(
        r"```\n(.*?)```", text[result_at:result_at + 4000], re.S)
    if not published_match:
        return [f"{name}: 代表入力に対応する実行結果ブロックがありません"]
    published = published_match.group(1)

    # 公開操作の呼び出し行を数える。`r = obj.op(...);` の代入形と、
    # `obj.op(...);` `freeFunc(...);` の文の形をどちらも拾う。
    calls = len(re.findall(
        r"^\s*(?:[\w:<>&*\s]+?=\s*)?[A-Za-z_]\w*(?:\.\w+)+\s*\("
        r"|^\s*[a-z_]\w*\s*\(",
        excerpt, re.M))
    if calls < MIN_CALLS:
        issues.append(
            f"{name}: 代表入力の呼び出しが{calls}回です（下限{MIN_CALLS}）。"
            "入力の準備から、続けて呼んだときに状態がどう変わるかまで見せてください"
        )

    start = text.find("### 1-4")
    end = text.find("### 1-5", start)
    if min(start, end) < 0:
        return issues + [f"{name}: 1-4が見つかりません"]
    current = "".join(cpp_blocks(text[start:end]))
    main_at = re.search(r"(?m)^int main\(\)\s*\{", current)
    if not main_at:
        return issues + [f"{name}: 1-4に main() がありません"]

    source = (current[:main_at.start()]
              + "int main() {\n" + excerpt + "\n    return 0;\n}\n")
    with tempfile.TemporaryDirectory() as work:
        cpp = Path(work) / "excerpt.cpp"
        cpp.write_text(source, encoding="utf-8")
        binary = Path(work) / "excerpt"
        built = subprocess.run(
            ["g++", "-std=c++14", str(cpp), "-o", str(binary)],
            capture_output=True)
        if built.returncode:
            head = built.stderr.decode("utf-8", "replace").strip().split("\n")
            issues.append(
                f"{name}: 代表入力だけではコンパイルできません。"
                "使う実体をこの抜粋の中で用意してください（"
                + " / ".join(head[:2]) + "）")
            return issues
        run = subprocess.run([str(binary)], capture_output=True, cwd=work)
        actual = run.stdout.decode("utf-8", "replace")

    if actual.strip() != published.strip():
        issues.append(
            f"{name}: 掲載している実行結果が、代表入力の実出力と違います")
    return issues


def main() -> int:
    issues: list[str] = []
    for name in CORE_CHAPTERS:
        if not (OUTPUT_DIR / name).exists():
            continue
        issues.extend(chapter_issues(name))

    for issue in issues:
        print(issue)
    if issues:
        print(f"\nNG: {len(issues)} 件")
        return 1
    print(f"OK: {len(CORE_CHAPTERS)} 章の代表入力が、"
          "そのまま動いて掲載どおりの結果を出します")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
