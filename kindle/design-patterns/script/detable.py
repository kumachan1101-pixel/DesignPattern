#!/usr/bin/env python3
"""6インチ端末で読めない表を、定義リスト形式へ組み替える。

Kindleの表は列幅が均等に割られるため、4列の表は1列あたり日本語で約10字に
なる。1セルに文が入っている表は、17行の縦長の柱が4本並ぶ形で描かれ、
同じ行の内容を目で結べない。

そこで、長いセルを持つ表を次の形へ変える。列見出しがラベルになるので
情報は落ちず、横幅は端末の幅で自然に折り返る。

    | 課題ID | 採用構造 | 確認 |         **課題ID1（選択条件）**
    |---|---|---|                  →
    | 課題ID1（選択条件） | 長文 | 長文 |    - **採用構造**：長文
                                          - **確認**：長文

対象は次のどちらか。

  Tier1: どこか1セルが80桁を超える表
  Tier2: 4列以上で1セルが60桁超か1行合計200桁超、または3列で1行合計160桁超

全セルが短い表は、表のまま残す。2列でも値が文になっているものは崩す。表が読みやすい場面まで
散文へ崩すと、かえって一覧性が落ちるためである。

    python3 script/detable.py <ファイル> [--apply] [--tier1-only]
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


def to_definition_list(rows: list[list[str]]) -> list[str]:
    """先頭列を見出し、残りの列をラベル付き箇条書きにする。"""
    header, body = rows[0], rows[1:]
    out: list[str] = []

    if len(header) == 2:
        # 2列なら、ラベルは1つしかない。各行へ繰り返すと同じ語が
        # 何度も並ぶので、列見出しを先に1度だけ置く。
        name = header[1].strip().replace("**", "")
        if name and name not in {"—", "――", "-"}:
            out.append(f"**{name}**")
            out.append("")
        for row in body:
            key = row[0].strip().replace("**", "")
            value = row[1].strip() if len(row) > 1 else ""
            if not key and not value:
                continue
            out.append(f"- **{key}**：{value}" if value else f"- **{key}**")
        return out

    for row in body:
        key = row[0].strip()
        if not key or set(key) <= {"-", "—", "*"}:
            key = "（見出しなし）"
        # 先頭列がすでに強調されている場合は二重にしない
        label = key if key.startswith("**") else f"**{key}**"
        out.append(label)
        out.append("")
        for name, value in zip(header[1:], row[1:]):
            value = value.strip()
            if not value or value in {"—", "――", "-"}:
                continue
            name = name.strip().replace("**", "")
            out.append(f"- **{name}**：{value}")
        out.append("")
    while out and out[-1] == "":
        out.pop()
    return out


def convert(path: Path, apply: bool, tier1_only: bool) -> int:
    text = path.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    edits: list[tuple[int, int, list[str]]] = []
    counts = {"tier1": 0, "tier2": 0}

    for start, end, block in find_tables(lines):
        rows = [split_row(r) for r in block if not re.match(r"^\|[\s:-]+\|", r)]
        if not rows:
            continue
        kind = classify(rows)
        if kind == "keep" or (tier1_only and kind != "tier1"):
            continue
        counts[kind] += 1
        edits.append((start, start + len(block), to_definition_list(rows)))

    if not edits:
        print(f"{path.name}: 対象なし")
        return 0

    if apply:
        for start, end, replacement in reversed(edits):
            lines[start:end] = replacement
        path.write_bytes(newline.join(lines).encode("utf-8"))

    print(
        f"{path.name}: tier1 {counts['tier1']}表 / tier2 {counts['tier2']}表"
        f"{' を組み替えました' if apply else '（--apply で反映）'}"
    )
    return counts["tier1"] + counts["tier2"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--tier1-only", action="store_true")
    args = parser.parse_args()
    total = 0
    for name in args.files:
        total += convert(Path(name), args.apply, args.tier1_only)
    print(f"合計 {total} 表")
    return 0


if __name__ == "__main__":
    sys.exit(main())
