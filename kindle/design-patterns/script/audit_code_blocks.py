#!/usr/bin/env python3
"""掲載コードブロックの所属・分割・省略を監査し、残件一覧を出す。

DOC-001（AF-20260814-142〜143）の worklist ツール。著者指摘は次の3点。

    コードを略して記載している箇所が多い。せめてどのクラスのどの関数かは
    わかる形にしてほしい。コードブロックはなるべく分割して。1クラス1
    ブロックとまではいわないが、1クラスが大きいならその時点で分割して。

2026-08-14に残件が0件になったため、判定は `validate_book.py` の
`check_code_block_attribution()` へ移してゲートで固定した（負のテストは
`test_recurrence_checks.py` の DOC-001 4件）。例外リストは作らない。

このスクリプトは残件を章別・種別に数える一覧ツールとして残す。ゲートは
「違反があるか」しか答えないため、章を書き足す途中で「どこがあと何件か」を
見るときに使う。判定条件を変えるときは、必ず両方を同時に直す。

    python3 script/audit_code_blocks.py            # 残件一覧
    python3 script/audit_code_blocks.py --summary  # 章別の件数だけ

判定はフェーズ3・4・6・7のC++ブロックへ適用する。フェーズ1の現状コードは
1-4の通しコードとして読む前提なので対象外。
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

BOOK_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BOOK_ROOT / "output"

CORE_CHAPTERS = [
    "chapter01.md", "chapter02.md", "chapter03.md", "chapter04.md",
    "chapter05.md", "chapter06.md", "chapter07.md", "chapter08.md",
    "chapter09_2.md", "chapter10.md", "chapter11.md", "chapter12.md",
]

TARGET_PHASES = {"3", "4", "6", "7"}

# 1ブロックの上限。超えたら責任単位で割る。
MAX_LINES = 80
MAX_TYPES = 4

# 章の論点を隠す省略表現。定型処理の省略は本文側で範囲と掲載先を書く。
# 文字列リテラルの中の `...`（例：`"再試行します..."`）は省略ではないので、
# 判定前にリテラルを落とす。コメント内か、単独行の省略だけを見る。
STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\])*"')
# 散文の「…」（文の続き）、C++の仮引数名省略の説明、`{ /* メール送信 */ }` の
# ような「中身を一言で説明するコメント」は対象外。コードが抜けていると分かる
# 形だけを見る。判定を広げるときは、必ず実物を確認してから広げること。
ELLIPSIS = re.compile(
    r"中略"                                  # 「…（中略：…）…」
    r"|\{\s*/\*\s*(?:\.\.\.|…|省略)\s*\*/\s*\}"   # { /* ... */ }
    r"|^\s*(?://\s*)?(?:\.\.\.|…)[^\n]{0,12}$",  # 省略だけの行
    re.M,
)


def strip_strings(body: str) -> str:
    return STRING_LITERAL.sub('""', body)

# 所属が読み取れる手がかり。`Class::method(...)`、クラス名、main() など。
# 見出し・太字だけでなく、直前の散文や引用（「抜粋の前提」など）も見る。
OWNER_HINT = re.compile(
    r"`[A-Z]\w*::\w+|`[A-Z]\w*`|\bmain\s*\(|^\s*(?:class|struct)\s+\w+",
    re.M,
)


def phase_marks(text: str) -> list[tuple[int, str]]:
    return [
        (m.start(), m.group(1))
        for m in re.finditer(r"^## [^\n]*フェーズ(\d)", text, re.M)
    ]


def phase_at(marks: list[tuple[int, str]], pos: int) -> str:
    current = "1"
    for offset, phase in marks:
        if offset < pos:
            current = phase
    return current


def preceding_prose(text: str, pos: int) -> str:
    """直前のコードブロック以降の説明文を返す。

    見出しと太字ラベルだけでなく、引用（`> **抜粋の前提**`）や箇条書きも
    所属の手がかりになる。直前の ``` 以降を丸ごと見る。
    """
    window = text[max(0, pos - 1200):pos]
    last_fence = window.rfind("```")
    if last_fence >= 0:
        window = window[last_fence + 3:]
    return window


def preceding_label(text: str, pos: int) -> str:
    """一覧表示用に、直前の見出しまたは太字ラベルを返す。"""
    window = text[max(0, pos - 500):pos]
    labels = re.findall(r"(?m)^(?:#{3,5} .*|\*\*[^*\n]{1,90}\*\*)", window)
    return labels[-1] if labels else ""


def findings_for(path: Path) -> list[tuple[int, str, str]]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    marks = phase_marks(text)
    found: list[tuple[int, str, str]] = []
    for match in re.finditer(r"```cpp\n(.*?)```", text, re.S):
        body = match.group(1)
        pos = match.start()
        if phase_at(marks, pos) not in TARGET_PHASES:
            continue
        line_no = text[:pos].count("\n") + 1
        lines = [ln for ln in body.split("\n") if ln.strip()]
        types = len(re.findall(r"(?m)^\s*(?:class|struct)\s+\w+", body))
        label = preceding_label(text, pos)

        prose = preceding_prose(text, pos)
        if not OWNER_HINT.search(prose + "\n" + body[:300]):
            found.append((
                line_no, "所属不明",
                "直前のラベルとコード先頭から Class::method(signature) を"
                f"特定できません（ラベル: {label[:40] or 'なし'}）",
            ))
        if len(lines) > MAX_LINES:
            found.append((
                line_no, "過大",
                f"実質{len(lines)}行（上限{MAX_LINES}）。"
                "型・メンバー／公開操作／内部判定などの切れ目で分割してください",
            ))
        if types >= MAX_TYPES:
            found.append((
                line_no, "多型",
                f"1ブロックへ{types}型（上限{MAX_TYPES - 1}）。"
                "変わる理由が違う型を同じブロックへ置かないでください",
            ))
        if ELLIPSIS.search(strip_strings(body)):
            found.append((
                line_no, "省略記号",
                "コード内の省略で分岐・接続・責任が隠れていないか確認し、"
                "隠れているなら実コードへ戻してください",
            ))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    total = 0
    per_chapter: Counter[str] = Counter()
    per_kind: Counter[str] = Counter()
    for name in CORE_CHAPTERS:
        path = OUTPUT_DIR / name
        if not path.exists():
            continue
        found = findings_for(path)
        per_chapter[name] = len(found)
        total += len(found)
        for _, kind, _ in found:
            per_kind[kind] += 1
        if found and not args.summary:
            print(f"\n■ {name}")
            for line_no, kind, message in found:
                print(f"  {name}:{line_no} [{kind}] {message}")

    print("\n--- 残件 ---")
    for name in CORE_CHAPTERS:
        if per_chapter[name]:
            print(f"  {name:15} {per_chapter[name]:3}件")
    print(f"  {'種別':15} " + " / ".join(f"{k}{v}" for k, v in per_kind.items()))
    print(f"\n合計 {total} 件")
    if total == 0:
        print("OK: 所属・分割・省略の残件はありません。"
              "この判定を validate_book.py へ移してゲートで固定できます")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
