#!/usr/bin/env python3
"""出版パッケージとして成立しているかを検査する（GATE-001）。

本文ゲート（run_completion_gate.py）は「原稿が書けているか」を見る。
こちらは「その原稿を1冊へ束ねられるか」を見る。判定を分けているのは、
manuscript ready と KDP package ready が別物だからである。原稿がすべて
PASSしていても、目次から章が抜けていれば本は組めない。

検査するもの:
  1. toc.md のファイル対応表に挙げた出力ファイルが実在する
  2. output/ にあるのに対応表へ載っていない原稿がない（載せ漏れ）
  3. 対応表の章名が、本文の見出しと一致する
  4. 本文が参照する画像が実在する
  5. 結合順が対応表から一意に決まり、はじめに→本文→おわりにの順になっている

EPUB／KPFの生成物そのものの検査は PUBLISH-001（出版ビルド）が入った後に
足す。ここは生成前でも回せる範囲に絞っている。

    python3 script/check_publish_package.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BOOK_ROOT / "output"
TOC_PATH = BOOK_ROOT / "toc.md"

# 結合順の先頭・末尾に来るべきもの（本文の章はこの間に入る）
FRONT_MATTER = ("chapter00_1.md", "chapter00_2.md")
BACK_MATTER = ("epilogue.md",)


def toc_file_rows() -> list[tuple[str, str]]:
    """ファイル対応表から (役割, 出力ファイル名) を読む。"""
    text = TOC_PATH.read_text(encoding="utf-8")
    start = text.find("## ファイル対応表")
    if start < 0:
        return []
    section = text[start:]
    rows: list[tuple[str, str]] = []
    for line in section.splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|[^|]*\|\s*output/([\w.]+\.md)\s*\|", line)
        if m:
            rows.append((m.group(1).strip(), m.group(2)))
    return rows


def toc_chapter_titles() -> dict[str, str]:
    """全体構成表から「第N章」→ 章名 を読む。"""
    text = TOC_PATH.read_text(encoding="utf-8")
    titles: dict[str, str] = {}
    for m in re.finditer(
        r"^\|\s*\*\*(第\d+章)\*\*\s*([^|]+?)\s*\|[^|]*\|\s*(chapter[\w.]+\.md)\s*\|",
        text, re.M,
    ):
        titles[m.group(3)] = f"{m.group(1)} {m.group(2).strip()}"
    return titles


def body_heading(path: Path) -> str:
    """本文の最初の見出し（# か ##）を返す。"""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return ""


def normalize(title: str) -> str:
    """比較用に表記ゆれを吸収する（全角ダッシュ・空白・強調）。"""
    t = title.replace("**", "")
    t = t.replace("――", "―").replace("——", "―").replace("--", "―")
    t = re.sub(r"\s+", "", t)
    return t


def main() -> int:
    failures: list[str] = []

    rows = toc_file_rows()
    if not rows:
        print("FAILED: toc.md にファイル対応表が見つかりません")
        return 1
    listed = [name for _, name in rows]

    # 1. 対応表のファイルが実在するか
    for role, name in rows:
        if not (OUTPUT_DIR / name).exists():
            failures.append(f"目次の「{role}」が指す output/{name} がありません")

    # 2. output/ の載せ漏れ
    actual = sorted(p.name for p in OUTPUT_DIR.glob("*.md"))
    for name in actual:
        if name not in listed:
            failures.append(
                f"output/{name} が toc.md のファイル対応表に載っていません"
                f"（本へ入らない原稿になります）"
            )

    # 3. 章名と本文見出しの一致
    for name, toc_title in toc_chapter_titles().items():
        path = OUTPUT_DIR / name
        if not path.exists():
            continue
        head = body_heading(path)
        # 目次は「第1章 変わるものを…」、本文は「第1章 変わるものを… ―― Strategy パターン」
        if not normalize(head).startswith(normalize(toc_title).split("―")[0]):
            failures.append(
                f"{name}: 目次の章名「{toc_title}」と本文見出し「{head}」が一致しません"
            )

    # 4. 画像参照の実在
    for path in sorted(OUTPUT_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for ref in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
            if ref.startswith(("http://", "https://", "data:")):
                continue
            target = (path.parent / ref).resolve()
            if not target.exists():
                failures.append(f"{path.name}: 画像 {ref} がありません")

    # 5. 結合順
    for name in FRONT_MATTER + BACK_MATTER:
        if name not in listed:
            failures.append(f"結合順に必須の {name} が対応表にありません")
    if listed:
        if listed[0] != FRONT_MATTER[0]:
            failures.append(
                f"結合順の先頭が {listed[0]} です（{FRONT_MATTER[0]} から始めてください）"
            )
        if listed[-1] != BACK_MATTER[-1]:
            failures.append(
                f"結合順の末尾が {listed[-1]} です（{BACK_MATTER[-1]} で終えてください）"
            )
        chapters = [n for n in listed if re.match(r"chapter\d", n)]
        if chapters != sorted(chapters):
            failures.append(f"対応表の章順が昇順になっていません: {chapters}")

    if failures:
        print("\n".join(failures))
        print(f"\nFAILED: {len(failures)} publish package issue(s)")
        return 1

    print(f"OK: 目次と原稿 {len(listed)} 件が対応し、結合順も決まっています")
    print("     （EPUB／KPF生成物の検査は PUBLISH-001 で追加）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
