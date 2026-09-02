#!/usr/bin/env python3
"""設計を言葉で説明している箇所が、コードのどこの話か特定できるかを見る。

設計の説明は抽象語で書けてしまう。「責任を分ける」「知識が漏れている」は、
それだけ読んでも、目の前のコードのどこを指しているのか分からない。この検査は、
**説明が具体物に着地しているか**を3つの角度から見る。

  A1 着地しない設計語
      「責任」「知識」「境界」「接続点」「痛み」「骨格」を含む段落に、
      識別子（`Xxx` / `foo()`）も行番号の手がかり（1-4、7-1 など）も無い。
      読者は「どこの話か」を推測することになる。

  A2 実体のない参照
      実践章の本文が `Xxx` を挙げているのに、その章のどのコードブロックにも
      `Xxx` が無い。読者が探しに行っても、指されたコードが存在しない。
      「はじめに」と第0章は、まだコードを持たない仮の例で設計を語る場所なので
      対象にしない。

「コードの直後に説明があるか」は check_flow.py の F3 が見る。ここで
「直後の段落が識別子を再掲しているか」までは求めない。日本語で
「1-1の入力『キャンペーンフラグ』です」と回収するのも正しい書き方だからである。

A1 は候補が多く出るので、既定では A2 だけを違反として扱う。
`--strict` を付けると A1 も違反にする。

    python3 script/check_anchor.py --config books/<冊>/publishing/book.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]

DESIGN_WORDS = ("責任", "知識", "境界", "接続点", "痛み", "骨格", "混在", "変化の軸")

# 具体物への着地とみなすもの。
IDENTIFIER = re.compile(r"`[A-Za-z_][\w:]*`|`\w+\(\)`")
LOCATION = re.compile(r"\d-\d|フェーズ\d|変更ID\d|要求ID\d|課題ID\d|原因ID\d|問題ID\d")

# 導入・まとめ・悩みどころは、具体物を指さずに考え方を述べる場所として認める。
SOFT_CONTEXT = re.compile(r"悩みどころ|このフェーズの考え方|まとめ|はじめに|おわりに")


def blocks(text: str):
    """(種別, 内容, 行番号)。種別は heading / code / para。"""
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
            yield ("code" if lang == "cpp" else "other", "\n".join(body), start + 1)
            continue
        if line.startswith("#"):
            yield ("heading", line, index + 1)
            index += 1
            continue
        if line.strip():
            start = index
            body = []
            while index < len(lines) and lines[index].strip() \
                    and not lines[index].startswith(("```", "#")):
                body.append(lines[index])
                index += 1
            yield ("para", "\n".join(body), start + 1)
            continue
        index += 1


def scan(path: Path) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    items = list(blocks(text))
    violations: list[str] = []
    candidates: list[str] = []
    reported: set[str] = set()

    in_code: set[str] = set()
    for kind, body, _ in items:
        if kind in {"code", "other"}:
            in_code.update(re.findall(r"\b([A-Za-z_]\w{3,})\b", body))

    section = ""
    for position, (kind, body, line) in enumerate(items):
        if kind == "heading":
            section = body
            continue

        # A1 着地しない設計語
        if kind == "para" and any(w in body for w in DESIGN_WORDS):
            if not IDENTIFIER.search(body) and not LOCATION.search(body) \
                    and not SOFT_CONTEXT.search(section + body) \
                    and not body.lstrip().startswith(("|", ">")):
                candidates.append(
                    f"[A1] {path.name}:{line} 設計語だけで、どのコードの話か分かりません"
                    f"（{body.strip()[:56]}）"
                )

        # A2 実体のない参照（実践章だけ）
        if kind == "para" and re.match(r"^\d+-chapter\d", path.stem):
            for name in re.findall(r"`([A-Z][A-Za-z_]{3,})(?:::|\()?[^`]*`", body):
                # ファイル名（`Discounts.h`、`Makefile`）はクラス名ではない。
                if re.search(r"`" + re.escape(name) + r"(?:\.(?:h|cpp))?`", body) \
                        and (name == "Makefile"
                             or re.search(r"`" + re.escape(name) + r"\.(?:h|cpp)`", body)):
                    continue
                if name not in in_code and name not in reported:
                    reported.add(name)
                    violations.append(
                        f"[A2] {path.name}:{line} 本文の `{name}` が、"
                        f"この章のコードにありません"
                    )

    return violations, candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--strict", action="store_true", help="A1 も違反として扱う")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = BOOK_ROOT / config_path
    data = json.loads(config_path.read_text(encoding="utf-8"))

    violations: list[str] = []
    candidates: list[str] = []
    for name in data.get("chapters", []):
        path = BOOK_ROOT / name
        if path.exists():
            found, maybe = scan(path)
            violations += found
            candidates += maybe

    if args.strict:
        violations += candidates
    elif candidates:
        print(f"（A1 候補 {len(candidates)} 件。--strict で一覧します）\n")

    if violations:
        print("\n".join(violations))
        print(f"\nFAILED: {len(violations)} anchoring issue(s) in {config_path.name}")
        return 1
    print("OK: 設計の説明が、いずれもコードの具体物へ着地しています")
    return 0


if __name__ == "__main__":
    sys.exit(main())
