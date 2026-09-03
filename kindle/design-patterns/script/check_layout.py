#!/usr/bin/env python3
"""6インチのKindle端末で崩れる書き方を洗い出す。

紙とちがい、Kindleの本文幅は端末と文字サイズで変わる。1行に横へ詰めた並びは、
狭い幅では途中で折り返され、段の区切りが目で追えなくなる。この検査は、
**そのままでは読者に届かない形**を見る。

  L1 横へ詰めた手順
      「A（説明）→ B（説明）→ C（説明）」のように、3つ以上の段を矢印で
      つないだ1行。段ごとに補足が付くものは、折り返すと段の頭が見えなくなる。
      縦の番号付きリストにすれば、幅がいくつでも段が並ぶ。

  L2 折り返せない長い語
      改行できない欧文の連なり（識別子・パス・記号列）が40桁に達する。
      日本語はどこでも折り返せるが、欧文は語の途中で切れない。本文のCSSは
      `overflow-wrap: break-word` なので、1行に収まらない語だけが途中で
      割られる。6インチ端末の1行はおよそ35桁なので、40桁を超える連なりは
      必ずどこかで割れる。`Class::method()` 程度（30桁前後）は1行に収まる。

  L5 幅の広いコード
      掲載コードに64桁を超える行がある。コード画像は幅2000px・48pxの等幅で
      組まれるため、64桁を超えると勝手に折り返され、`= 0;` だけが次の行へ
      落ちるような読みにくい割れ方になる。`script/wrap_code.py` で、
      意味の切れ目へあらかじめ改行を入れる。

  L3 深い入れ子の括弧
      1文の中で括弧が3重以上になっている。折り返されると対応が取れない。

  L4 幅の広い擬似図
      言語指定なしのブロック（実行結果や構成図）に、80桁を超える行がある。
      コード画像として縮小されるため、文字が読めない大きさになる。

表のセル幅は check_volume.py の検査17が見る。

    python3 script/check_layout.py --config books/<冊>/publishing/book.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]

ARROW = re.compile(r"\s*(?:→|->)\s*")


def width(text: str) -> int:
    """全角を2、半角を1として表示幅を数える。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WFA" else 1 for c in text)


def segments(text: str):
    """(種別, 内容, 行番号)。種別は code / plain / prose。"""
    lines = text.split("\n")
    index = 0
    while index < len(lines):
        if lines[index].startswith("```"):
            lang = lines[index][3:].strip()
            start = index
            index += 1
            body: list[str] = []
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            index += 1
            yield (lang or "plain", "\n".join(body), start + 1)
            continue
        yield ("prose", lines[index], index + 1)
        index += 1


def scan(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures: list[str] = []

    for kind, body, line in segments(text):
        if kind != "prose" and kind != "plain":
            # Mermaidは画像として組まれ、幅は描画側が調整する。C++だけを見る。
            if kind != "cpp":
                continue
            for offset, row in enumerate(body.split("\n")):
                if len(row) > 64:
                    failures.append(
                        f"[L5] {path.name}:{line + offset + 1} コードの行が{len(row)}桁"
                        f"あります（64桁で折り返されます）: {row.strip()[:40]}…"
                    )
            continue

        if kind == "plain":
            for offset, row in enumerate(body.split("\n")):
                if width(row) > 80:
                    failures.append(
                        f"[L4] {path.name}:{line + offset + 1} 図・実行結果の行が"
                        f"{width(row)}桁あります（{row.strip()[:40]}…）"
                    )
            continue

        stripped = body.strip().lstrip("> ").lstrip()
        if stripped.startswith(("|", "#")) or not stripped:
            continue

        # L1 横へ詰めた手順
        # 文中に出る矢印（「10000円→9000円」など）は対象にしない。
        # 行そのものが手順の並びになっているものだけを見る。
        body_text = re.sub(r"^[-*\d.]+\s*", "", stripped)
        parts = [p.strip() for p in ARROW.split(body_text) if p.strip()]
        if len(parts) >= 3 and "。" not in body_text:
            detailed = sum(
                1 for p in parts if re.search(r"[（(][^）)]{4,}[）)]|`[^`]+`", p)
            )
            if detailed >= 2 and width(body_text) > 90:
                failures.append(
                    f"[L1] {path.name}:{line} {len(parts)}段の手順を1行へ詰めています"
                    f"（幅{width(body_text)}）。縦のリストへ分けてください"
                    f"（{body_text[:44]}…）"
                )

        # L2 折り返せない欧文の連なり
        for token in re.findall(r"[A-Za-z0-9_:()\[\]<>.*&|/\\+=-]{40,}", stripped):
            failures.append(
                f"[L2] {path.name}:{line} 途中で折り返せない{len(token)}桁の欧文"
                f"（{token[:40]}…）"
            )

        # L3 深い入れ子の括弧
        depth = 0
        deepest = 0
        for char in stripped:
            if char in "（(":
                depth += 1
                deepest = max(deepest, depth)
            elif char in "）)":
                depth = max(0, depth - 1)
        if deepest >= 3:
            failures.append(
                f"[L3] {path.name}:{line} 括弧が{deepest}重です"
                f"（{stripped[:44]}…）"
            )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = BOOK_ROOT / config_path
    data = json.loads(config_path.read_text(encoding="utf-8"))

    failures: list[str] = []
    for name in data.get("chapters", []):
        path = BOOK_ROOT / name
        if path.exists():
            failures += scan(path)

    if failures:
        print("\n".join(failures))
        print(f"\nFAILED: {len(failures)} layout issue(s) in {config_path.name}")
        return 1
    print("OK: 6インチ幅で崩れる書き方は見つかりませんでした")
    return 0


if __name__ == "__main__":
    sys.exit(main())
