#!/usr/bin/env python3
"""6インチ端末で読みにくい可能性がある表を検出する。

Kindleの表は列幅が均等に割られるため、4列の表は1列あたり日本語で約10字に
なる。長文セルを持つ表は、列の統合や説明の削減が必要かを人が確認する。

以前は表を「見出し＋ラベル付き箇条書き」へ自動変換していた。しかし、その形式は
同じ観点を縦横に比較できず、列名も各項目で繰り返すため、かえって読みにくかった。
そのため自動変換は廃止し、このスクリプトは候補の検出だけを行う。

候補を直すときは、次の順で判断する。

  1. 読者の判断に使わない列、全行で同じ列、本文と重複する列を削る。
  2. 説明用の表は原則3列以内にする。
  3. 状態×操作やAPI差分など、縦横の対応自体に意味がある表は残す。
  4. 比較ではなく順序や補足を示す情報だけ、箇条書きや本文へ移す。

検出対象は次のどちらか。

  Tier1: どこか1セルが80桁を超える表
  Tier2: 4列以上で1セルが60桁超か1行合計200桁超、または3列で1行合計160桁超

全セルが短い表は候補にしない。

    python3 script/detable.py <ファイル> [--tier1-only]
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path


def width(text: str) -> int:
    """全角を2、半角を1として表示幅を数える。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WFA" else 1 for c in text)


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def find_tables(lines: list[str]):
    """(開始行, 終了行, 行リスト) を返す。コードブロック内は見ない。"""
    in_fence = False
    buffer: list[str] = []
    start = 0
    for index, line in enumerate(lines):
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.strip().startswith("|"):
            if not buffer:
                start = index
            buffer.append(line)
            continue
        if buffer:
            yield start, index, buffer
            buffer = []
    if buffer:
        yield start, len(lines), buffer


def classify(rows: list[list[str]]) -> str:
    """表の重さを判定する。"""
    if len(rows) < 2:
        return "keep"
    columns = len(rows[0])
    longest = max(width(c) for row in rows for c in row)
    widest = max(sum(width(c) for c in row) for row in rows)
    if columns == 2:
        # 2列は「見出し＋短い値」なら読める。値が文になったら崩す。
        return "tier1" if longest > 80 else "keep"
    if columns < 3:
        return "keep"
    if longest > 80:
        return "tier1"
    if columns >= 4 and (longest > 60 or widest > 200):
        return "tier2"
    if columns == 3 and widest > 160:
        return "tier2"
    return "keep"


def audit(path: Path, tier1_only: bool) -> int:
    text = path.read_text(encoding="utf-8")
    lines = text.replace("\r\n", "\n").split("\n")
    findings: list[tuple[int, str]] = []
    counts = {"tier1": 0, "tier2": 0}

    for start, end, block in find_tables(lines):
        rows = [split_row(r) for r in block if not re.match(r"^\|[\s:-]+\|", r)]
        if not rows:
            continue
        kind = classify(rows)
        if kind == "keep" or (tier1_only and kind != "tier1"):
            continue
        counts[kind] += 1
        findings.append((start + 1, kind))

    if not findings:
        print(f"{path.name}: 対象なし")
        return 0

    locations = ", ".join(f"{line}行({kind})" for line, kind in findings)
    print(f"{path.name}: tier1 {counts['tier1']}表 / tier2 {counts['tier2']}表")
    print(f"  要確認: {locations}")
    return counts["tier1"] + counts["tier2"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--apply", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--tier1-only", action="store_true")
    args = parser.parse_args()
    if args.apply:
        print(
            "--applyによる自動変換は廃止しました。候補を確認し、不要な列を削って"
            "比較可能な表として編集してください。",
            file=sys.stderr,
        )
        return 2
    total = 0
    for name in args.files:
        total += audit(Path(name), args.tier1_only)
    print(f"合計 {total} 表")
    return 0


if __name__ == "__main__":
    sys.exit(main())
