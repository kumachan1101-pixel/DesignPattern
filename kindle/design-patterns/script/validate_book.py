#!/usr/bin/env python3
"""Validate structural invariants of the design-pattern book.

This checker intentionally covers rules that can be decided mechanically.
Semantic correctness, domain modeling, and explanatory quality still require
the chapter review process.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BOOK_ROOT / "output"

CORE_CHAPTERS = [
    "chapter01.md",
    "chapter02.md",
    "chapter03.md",
    "chapter04.md",
    "chapter05.md",
    "chapter06.md",
    "chapter07.md",
    "chapter08.md",
    "chapter09_2.md",
    "chapter10.md",
    "chapter11.md",
    "chapter12.md",
]

REQUIRED_PHASES = [
    "## 🔵 フェーズ1：現状把握",
    "## 🟣 フェーズ2：仮説立案",
    "## 🟣 フェーズ3：問題特定",
    "## 🟠 フェーズ4：原因分析",
    "## 🟡 フェーズ5：課題定義",
    "## 🔴 フェーズ6：対策検討",
    "## 🟢 フェーズ7：対策実施",
]

REQUIRED_NUMBERED_SECTIONS = [
    "### 1-1：",
    "### 1-2：",
    "### 1-3：登場クラスとクラス構成図",
    "### 1-4：実装コード（現状）",
    "### 1-5：変更要求",
    "### 2-1：",
    "### 2-2：今回の変更で確実に変わること",
    "### 2-3：関係者ヒアリング",
    "### 2-4：ヒアリングで判明した将来リスク",
    "### 2-5：変わる見込みと当面安定の前提を確定する",
    "### 3-1：変更を試みる",
    "### 3-2：変更影響グラフ",
    "### 3-3：痛みの言語化",
    "### 4-1：痛みの根源を探る",
    "### 4-2：変わるもの/変わってほしくないもの",
    "### 4-3：",
    "### 7-1：解決後のコード（全体）",
    "### 7-2：動作シーケンス図",
    "### 7-3：変更影響グラフ（改善後）",
    "### 7-4：変更シナリオ表",
]

BANNED_PATTERNS = [
    (
        re.compile(r"直接（直差し）|間接（アダプター経由）"),
        "廃止した4つの接続形態の表現が残っています",
    ),
    (
        re.compile(r"具体×直接|抽象×直接|具体×間接|抽象×間接"),
        "廃止した接続形態の分類名が残っています",
    ),
    (
        re.compile(r"\[cite:\s*\d+\]"),
        "生成AI由来の引用マーカーが残っています",
    ),
    (
        re.compile(
            r"準備完了|添付ファイル.*読み込み|ai-context|"
            r"フェーズ\d.*執筆します|章.*記述します"
        ),
        "生成AIのメタ命令が本文に残っています",
    ),
    (
        re.compile(r"★第[一二三四五六七八九十0-9]"),
        "編集メモが本文に残っています",
    ),
    (
        re.compile(r"ステップ\s*S[0-8]|S[0-8]\s*ステップ|S[0-8][：:]"),
        "旧9ステップ表記が本文に残っています",
    ),
    (
        re.compile(r"別途\s*テスト.{0,12}(?:ください|お願いします)"),
        "読者にテストを丸投げする表現が残っています",
    ),
]


@dataclass
class Issue:
    path: Path
    line: int
    message: str


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def find_in_order(text: str, tokens: list[str], path: Path) -> list[Issue]:
    issues: list[Issue] = []
    cursor = 0
    for token in tokens:
        index = text.find(token, cursor)
        if index < 0:
            issues.append(Issue(path, 1, f"必須要素がありません: {token}"))
            continue
        cursor = index + len(token)
    return issues


def check_fences(text: str, path: Path) -> list[Issue]:
    issues: list[Issue] = []
    opened_at: int | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("```"):
            continue
        if opened_at is None:
            opened_at = number
        else:
            opened_at = None
    if opened_at is not None:
        issues.append(Issue(path, opened_at, "コードフェンスが閉じられていません"))
    return issues


def check_duplicate_headings(text: str, path: Path) -> list[Issue]:
    issues: list[Issue] = []
    seen: dict[str, int] = {}
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not (line.startswith("## ") or re.match(r"^### \d+-\d", line)):
            continue
        heading = line.strip()
        if heading in seen:
            issues.append(
                Issue(
                    path,
                    number,
                    f"同一見出しが重複しています（初出: {seen[heading]}行）: {heading}",
                )
            )
        else:
            seen[heading] = number
    return issues


def check_banned_patterns(text: str, path: Path) -> list[Issue]:
    issues: list[Issue] = []
    for pattern, message in BANNED_PATTERNS:
        for match in pattern.finditer(text):
            issues.append(Issue(path, line_number(text, match.start()), message))
    return issues


def check_chapter(path: Path, core: bool) -> list[Issue]:
    text = path.read_text(encoding="utf-8")
    issues = check_fences(text, path)
    issues.extend(check_duplicate_headings(text, path))
    issues.extend(check_banned_patterns(text, path))
    if core:
        issues.extend(find_in_order(text, REQUIRED_PHASES, path))
        issues.extend(find_in_order(text, REQUIRED_NUMBERED_SECTIONS, path))
    return issues


def main() -> int:
    issues: list[Issue] = []
    chapter_paths = sorted(OUTPUT_DIR.glob("chapter*.md"))
    core_names = set(CORE_CHAPTERS)
    for path in chapter_paths:
        issues.extend(check_chapter(path, path.name in core_names))

    if issues:
        for issue in issues:
            relative = issue.path.relative_to(BOOK_ROOT.parent.parent)
            print(f"{relative}:{issue.line}: {issue.message}")
        print(f"\nFAILED: {len(issues)} issue(s)")
        return 1

    print(
        f"OK: {len(chapter_paths)} chapter files passed structural and residue checks"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
