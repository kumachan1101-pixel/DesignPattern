#!/usr/bin/env python3
"""読者向け本文へ、著者向けメモと先取り（ネタバレ）が混ざっていないか見る。

EDIT-002（著者指摘）の検査。

    ネタバレや著者向けメモが多数散見されます。フェーズ前半に多いです。

本文は読者へ向けて書く。執筆の段取り（「この段階では決めません」）、掲載の
都合（「Kindleで追いやすいよう」）、原稿内の相互参照ラベル（「実行対象
コード：」）は、読者にとっては情報にならない。必要なことは、題材の言葉で
書き直す。`CLAUDE.md` の執筆ルールにある「執筆者向けの進行管理を読者へ
言わない」「必要なら『次に何を確認するか』へ言い換える」を機械で支える。

先取りは、フェーズ1〜3の散文がフェーズ6・7でしか出てこない型名を名指しする
形で起きる。読者がまだ知らない解決構造の名前を先に見せると、そこから逆算して
読むことになり、痛みを自分で観測する機会が失われる。フェーズ3の変更試行で
新しく作る型は先取りではないので、対象から外す。

    python3 script/check_author_notes.py

例外リストは作らない。判定を変えるときは、必ず実物を確認してから変える。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BOOK_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BOOK_ROOT / "output"

CORE_CHAPTERS = [
    "chapter01.md", "chapter02.md", "chapter03.md", "chapter04.md",
    "chapter05.md", "chapter06.md", "chapter07.md", "chapter08.md",
    "chapter09_2.md", "chapter10.md", "chapter11.md", "chapter12.md",
]
MANUSCRIPT_CHAPTERS = sorted(path.name for path in OUTPUT_DIR.glob("chapter*.md"))

# 著者が本文へ直接書き込んだ確認印。第0章は方法論章のフェーズ見出しを
# 持たないため、従来のCORE_CHAPTERSだけの検査では残っていても見逃していた。
AUTHOR_MARK = re.compile(r"★")

# 原稿内の相互参照ラベル。読者は直前のコードを見ているので、
# 「何を実行したか」より「何を見ればよいか」を散文で書く。
CROSS_REFERENCE_LABEL = re.compile(
    r"^(?:実行対象コード|対応する動作例|確認したいこと|確認対象)：", re.M)

# 抜粋の範囲を伝えるのは読者に必要だが、「抜粋の前提」は編集側の言い方。
EXCERPT_PREMISE = re.compile(r"抜粋の前提")

# 執筆の段取りを読者へ言う文。「何を決めないか」ではなく
# 「ここで決めるのはどこまでか」を書く。
PROCESS_DECLARATION = re.compile(
    r"(?:ここでは|この段階では|この時点では|このフェーズでは)"
    r"[^。\n]{0,120}(?:決めません|実装しません|追加しません|増やしません|"
    r"示しません|評価しません|読みません)"
    r"|ここでは[^。\n]*(?:評価はしません|決めつけません)"
    r"|この時点では[^。\n]*決めつけません"
    r"|まだ実装はしません"
    r"|(?:クラス名|インターフェース|生成方法|分離先)[^。\n]*まだ決めません"
    r"|どのクラスへ分けるかは決めません"
    r"|先取り(?:しません|せず)"
    r"|ここからは三つを別々の設計判断として扱いません"
    r"|ここでは新しい役割を増やしません"
    r"|構成にはしません")

# 掲載の都合を読者へ言う文。
LAYOUT_NOTE = re.compile(
    r"Kindleで追いやすいよう|別々の断片ではなく|紙面|掲載上の都合|読みやすいよう")

# ID体系の配線説明。第0章で1度説明すれば足りる。
ID_WIRING_NOTE = re.compile(
    r"この(?:問題|原因|課題)IDが、[^。\n]*へ順につながります")

CHECKS = [
    ("相互参照ラベル", CROSS_REFERENCE_LABEL,
     "原稿内の参照ラベルではなく、この実行で何を見ればよいかを散文で書いてください"),
    ("抜粋の前提", EXCERPT_PREMISE,
     "「抜粋の前提」は編集側の言い方です。読者向けに、どこを抜き出し何を変えていないかを書いてください"),
    ("掲載の都合", LAYOUT_NOTE,
     "掲載の都合ではなく、題材の言葉で分け方の理由を書いてください"),
    ("ID配線の説明", ID_WIRING_NOTE,
     "ID体系のつながりは第0章で説明済みです。各章では題材の言葉で次に見ることを書いてください"),
]


def process_declaration_issues(name: str, text: str) -> list[str]:
    """全章（第0章を含む）の否定形の進行管理を検出する。"""
    prose = code_free(text)
    return [
        f"{name}: [執筆の段取り] 「何をしないか」ではなく、"
        "現在確認する事実・目的・次に確定する対象を書いてください"
        f"（該当: {match.group(0).strip()[:40]}）"
        for match in PROCESS_DECLARATION.finditer(prose)
    ]

TYPE_DECLARATION = re.compile(r"(?m)^\s*(?:class|struct)\s+([A-Z]\w*)")
# 先取り判定から外す語。題材の名前が偶然クラス名と同じ場合がある。
SPOILER_ALLOWED = {"Milk", "Whip", "Syrup", "Matcha", "Choco"}


def code_free(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.S)


def types_between(text: str, head: str, tail: str) -> set[str]:
    start = text.find(head)
    end = text.find(tail, start)
    if min(start, end) < 0:
        return set()
    joined = "".join(re.findall(r"```cpp\n(.*?)```", text[start:end], re.S))
    return set(TYPE_DECLARATION.findall(joined))


def line_of(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def author_marker_issues(name: str, text: str) -> list[str]:
    return [
        f"{name}:{line_of(text, match.start())}: [著者確認印] "
        "読者向け本文に`★`が残っています。質問へ回答する本文に書き直してください"
        for match in AUTHOR_MARK.finditer(text)
    ]


def chapter_issues(name: str) -> list[str]:
    text = (OUTPUT_DIR / name).read_bytes().decode("utf-8").replace("\r\n", "\n")
    issues: list[str] = []

    body_start = text.find("## 🔵 フェーズ1")
    if body_start < 0:
        return []
    prose = code_free(text[body_start:])
    for label, pattern, advice in CHECKS:
        for match in pattern.finditer(prose):
            issues.append(
                f"{name}: [{label}] {advice}"
                f"（該当: {match.group(0).strip()[:40]}）")

    phase4 = text.find("## 🟠 フェーズ4：", body_start)
    if phase4 < 0:
        return issues
    solution_types = (types_between(text, "### 7-1", "### 7-2")
                      - types_between(text, "### 1-4", "### 1-5")
                      - types_between(text, "### 3-1", "### 3-2")
                      - SPOILER_ALLOWED)
    if not solution_types:
        return issues
    spoiler = re.compile(
        r"\b(" + "|".join(re.escape(k) for k in sorted(solution_types)) + r")\b")
    # コードブロックは飛ばし、散文の行だけを実際の行番号つきで見る。
    in_fence = False
    base = text[:body_start].count("\n")
    for offset, line in enumerate(text[body_start:phase4].split("\n"), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        found = spoiler.search(line)
        if found:
            issues.append(
                f"{name}:{base + offset}: [先取り] フェーズ1〜3の本文が、"
                f"フェーズ7でしか出てこない `{found.group(1)}` を名指ししています。"
                "読者が痛みを自分で観測する前に解決構造の名前を見せないでください")
    return issues


def main() -> int:
    issues: list[str] = []
    for name in MANUSCRIPT_CHAPTERS:
        text = (OUTPUT_DIR / name).read_bytes().decode("utf-8").replace("\r\n", "\n")
        issues.extend(author_marker_issues(name, text))
        issues.extend(process_declaration_issues(name, text))
    for name in CORE_CHAPTERS:
        if (OUTPUT_DIR / name).exists():
            issues.extend(chapter_issues(name))
    for issue in issues:
        print(issue)
    if issues:
        print(f"\nNG: {len(issues)} 件の著者向けメモ・先取りがあります")
        return 1
    print("OK: 読者向け本文に著者向けメモと先取りはありません")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
