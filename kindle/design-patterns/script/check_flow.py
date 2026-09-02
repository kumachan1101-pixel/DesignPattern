#!/usr/bin/env python3
"""読者がつまずく箇所の候補を機械で洗い出す。

「論理の飛躍」は最終的には人が読んで判断するものだが、飛躍しているところには
文面上の兆候が出やすい。この検査は結論を出さず、**読むべき箇所を絞る**ために使う。

見る兆候は次の7つ。

  F1 根拠なしの帰結    段落が「つまり／したがって／そのため／よって」で始まるのに、
                       直前の段落が1文しかない（前提を1つも積まずに結論へ飛んでいる）
  F2 宙に浮いた指示語  見出し直後の段落が「これ／それ／この」で始まり、
                       その指示対象が見出しに現れない
  F3 説明のないコード  コードブロックの直後が、別のコードブロックか見出し
                       （読者はコードを自力で解釈することになる）
  F4 用語の先出し      本書固有の用語が、その用語を定義した見出しより前に出る
  F5 長すぎる一文      1文が120字を超える（読点で息継ぎできても係り受けを追えない）
  F6 実体のない識別子  本文が `Xxx` を挙げているのに、その章のコードに一度も出てこない
  F7 唐突な数値        本文の数値が、直前の表・コード・実行結果のどこにも現れない

    python3 script/check_flow.py --config books/<冊>/publishing/book.json [--only F1,F3]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]

# 本書固有の用語と、それを定義している見出しの手がかり。
GLOSSARY = {
    "接続点": "接続点",
    "変化の軸": "変化の軸",
    "変更ID": "変更",
    "要求ID": "要求",
    "課題ID": "課題",
    "原因ID": "原因",
    "リスクID": "リスク",
    "問題ID": "問題",
    "変更影響グラフ": "影響",
    "受入・回帰エビデンス": "エビデンス",
}

CONCLUSION_HEAD = re.compile(r"^\s*(?:つまり|したがって|ですから|そのため|よって|この結果)")
DEMONSTRATIVE = re.compile(r"^\s*(?:これ|それ|この点|そこ|ここ)(?![にはでを]おいて)")


def blocks(text: str):
    """(種別, 内容, 行番号) を上から順に返す。種別は heading/code/fence/para。"""
    lines = text.split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            lang = line[3:].strip()
            start = index
            index += 1
            body: list[str] = []
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            index += 1
            yield ("code" if lang else "fence", "\n".join(body), start + 1)
            continue
        if line.startswith("#"):
            yield ("heading", line, index + 1)
            index += 1
            continue
        if line.strip():
            start = index
            body = []
            while index < len(lines) and lines[index].strip() and not lines[index].startswith(("```", "#")):
                body.append(lines[index])
                index += 1
            yield ("para", "\n".join(body), start + 1)
            continue
        index += 1


def sentences(paragraph: str) -> list[str]:
    plain = re.sub(r"`[^`]*`", "", paragraph)
    return [s for s in re.split(r"(?<=[。？！])", plain) if s.strip()]


def scan(path: Path, only: set[str]) -> list[tuple[str, int, str]]:
    text = path.read_text(encoding="utf-8")
    items = list(blocks(text))
    hits: list[tuple[str, int, str]] = []

    def add(code: str, line: int, message: str) -> None:
        if not only or code in only:
            hits.append((code, line, message))

    # F1・F2・F3
    for position, (kind, body, line) in enumerate(items):
        previous = items[position - 1] if position else None
        following = items[position + 1] if position + 1 < len(items) else None

        if kind == "para" and CONCLUSION_HEAD.match(body):
            listish = previous and previous[1].lstrip().startswith(("|", "-", "*", "1.", ">"))
            if previous and previous[0] == "para" and not listish \
                    and len(sentences(previous[1])) <= 1:
                add("F1", line, f"帰結の接続詞で始まるが、直前が1文だけ: {body[:44]}")

        if kind == "para" and previous and previous[0] == "heading":
            match = DEMONSTRATIVE.match(body)
            if match:
                add("F2", line, f"見出し直後が指示語で始まる: {previous[1][:24]} → {body[:40]}")

        if kind == "code" and following and following[0] in {"code", "heading"}:
            add("F3", line, f"コードの直後に説明がない（次は{following[0]}）: {body.strip()[:40]}")

    # F4 用語の先出し
    for term, hint in GLOSSARY.items():
        first_use = None
        defined_at = None
        for kind, body, line in items:
            if kind == "heading" and hint in body and defined_at is None:
                defined_at = line
            if kind == "para" and term in body and first_use is None:
                first_use = line
        if first_use and defined_at and first_use < defined_at - 3:
            add("F4", first_use, f"用語「{term}」が定義見出し（{defined_at}行）より前に出ます")

    # F5 長すぎる一文
    for kind, body, line in items:
        if kind != "para" or body.lstrip().startswith(("|", ">", "-", "*")):
            continue
        for sentence in sentences(body):
            stripped = sentence.strip()
            if len(stripped) > 120:
                add("F5", line, f"{len(stripped)}字の一文: {stripped[:50]}…")

    # F6 実体のない識別子
    in_code: set[str] = set()
    for kind, body, line in items:
        if kind in {"code", "fence"}:
            in_code.update(re.findall(r"\b([A-Z][A-Za-z]{3,})\b", body))
    for kind, body, line in items:
        if kind != "para":
            continue
        for name in re.findall(r"`([A-Z][A-Za-z_]{3,})(?:::)?[^`]*`", body):
            if name not in in_code:
                add("F6", line, f"本文の `{name}` が、この章のコードに一度も出てきません")

    # F7 唐突な数値
    context = ""
    for kind, body, line in items:
        if kind != "para":
            context = body
            continue
        plain = re.sub(r"`[^`]*`", "", body)
        for number in set(re.findall(r"(?<![0-9A-Za-z])([1-9][0-9]{2,})(?![0-9])", plain)):
            if number not in context and number not in path.stem:
                add("F7", line, f"数値 {number} が直前の表・コード・実行結果にありません")
        context = body

    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--only", default="", help="F1,F3 のように絞る")
    parser.add_argument("--files", nargs="*", help="章ファイルを直接指定する")
    args = parser.parse_args()

    only = {c.strip() for c in args.only.split(",") if c.strip()}
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = BOOK_ROOT / config_path
    data = json.loads(config_path.read_text(encoding="utf-8"))
    targets = [BOOK_ROOT / c for c in (args.files or data.get("chapters", []))]

    total = 0
    for path in targets:
        if not path.exists():
            continue
        hits = scan(path, only)
        if not hits:
            continue
        print(f"\n===== {path.name}（{len(hits)}件）")
        for code, line, message in sorted(hits, key=lambda h: (h[0], h[1])):
            print(f"  [{code}] {path.name}:{line} {message}")
        total += len(hits)

    print(f"\n候補 {total} 件（これは違反数ではなく、読んで判断する箇所の一覧です）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
