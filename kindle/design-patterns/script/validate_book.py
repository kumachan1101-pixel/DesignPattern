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

PHASE6_BASELINE_HEADING = (
    "#### ステップ1の比較元：仕様変更後の痛みコードをおさらいする"
)

# Phase 3で追加した代表要素。各改善ステップでコードとして扱うか、
# 差分抜粋なら「維持している」と説明し、仕様を消さない。
PHASE6_CONTINUITY_TOKENS = {
    "chapter01.md": ["isSummerSale", "isCampaignActive"],
    "chapter02.md": ["txId", "requestOTP"],
    "chapter03.md": ["Held", "Waitlisted"],
    "chapter04.md": ["EC", "checkFormatVersion"],
    "chapter05.md": ["undo", "removeExpense"],
    "chapter06.md": ["Matcha", "Choco"],
    "chapter07.md": ["SMS"],
    "chapter08.md": ["PayPay", "PaymentResult"],
    "chapter09_2.md": ["corporate", "Pending"],
    "chapter10.md": ["SystemC", "Slack"],
    "chapter11.md": ["履歴", "replay"],
    "chapter12.md": ["緊急", "決済部門"],
}

# Phase 3の変更途中コードで追加した代表要素が、採用後の完成コードと
# 変更シナリオ表まで同じ対象として追われていることを確認する。
PHASE7_SCENARIO_TOKENS = {
    "chapter01.md": ["サマーセール", "逐次"],
    "chapter02.md": ["取引ID"],
    "chapter03.md": ["キャンセル待ち", "一時保留"],
    "chapter04.md": ["EC", "形式バージョン"],
    "chapter05.md": ["Undo", "Redo"],
    "chapter06.md": ["Matcha", "Choco"],
    "chapter07.md": ["SMS", "非同期"],
    "chapter08.md": ["PayPay", "PaymentResult"],
    "chapter09_2.md": ["保留中", "法人"],
    "chapter10.md": ["C社", "Slack"],
    "chapter11.md": ["月次", "再実行"],
    "chapter12.md": ["緊急申請", "決済部門", "却下"],
}

PHASE7_CODE_TOKENS = {
    **PHASE6_CONTINUITY_TOKENS,
    "chapter11.md": ["履歴", "再実行"],
    "chapter12.md": ["SubmitEmergency", "決済部門"],
}

# 中間フェーズが中心ロジックの差分抜粋でも、フェーズ1から維持する
# DB・Repository・外部境界を削除したように見せないための継続契約。
PHASE_BOUNDARY_CONTINUITY_TOKENS = {
    "chapter01.md": ["CustomerDatabase", "CheckoutResultRenderer"],
    "chapter02.md": ["AccountDatabase", "TransferHistory"],
    "chapter03.md": ["EventDatabase"],
    "chapter05.md": ["CategoryDatabase"],
    "chapter06.md": ["MenuDatabase"],
    "chapter07.md": ["ProductDatabase"],
    "chapter08.md": ["ProcessorRegistry", "PaymentLog"],
    "chapter09_2.md": ["UserDatabase"],
    "chapter10.md": ["PartnerDatabase"],
    "chapter11.md": ["TemplateRegistry", "ReportRenderingApi"],
}

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
    (
        re.compile(r"構造（[^）]{1,20}）構造"),
        "「〜構造（…）構造」の重複表記（一括置換の破損）が残っています",
    ),
    (
        re.compile(r"を?修正必要が"),
        "「修正必要が」という置換破損の文が残っています",
    ),
    (
        re.compile(
            r"一般的な(?:設計|構成|実装|考え方|ルール|手順)です|"
            r"珍しくありません|珍しくない仕様|"
            r"標準的な(?:設計|手順)|広く採用され|業界標準"
        ),
        "根拠のない「一般的・標準的」断定が残っています（範囲を「この章のシステムでは」に限定するか削除する）",
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


def check_required_chapter_structures(text: str, path: Path) -> list[Issue]:
    """Check recurring structures that previously depended on visual review."""
    markers = {
        "1-1": "### 1-1：このシステムの仕様",
        "1-2": "### 1-2：動作例",
        "1-3": "### 1-3：登場クラスとクラス構成図",
        "1-4": "### 1-4：現状コード",
        "1-5": "### 1-5：変更要求",
        "phase2": "## 🔵 フェーズ2：仮説立案",
    }
    offsets = {name: text.find(marker) for name, marker in markers.items()}
    if any(offset < 0 for offset in offsets.values()):
        # Missing headings are already reported by find_in_order.
        return []

    section11 = text[offsets["1-1"]:offsets["1-2"]]
    section13 = text[offsets["1-3"]:offsets["1-4"]]
    section15 = text[offsets["1-5"]:offsets["phase2"]]
    issues: list[Issue] = []

    if "仕様項目" not in section11 or "具体例" not in section11:
        issues.append(Issue(path, line_number(text, offsets["1-1"]),
                            "1-1に具体例付きの仕様要点表がありません"))
    if "仕様整理図" not in section11 or "```mermaid" not in section11:
        issues.append(Issue(path, line_number(text, offsets["1-1"]),
                            "1-1に仕様説明後の仕様整理図がありません"))

    class_table = section13.find("| クラス名")
    class_diagram = section13.find("```mermaid")
    if class_table < 0 or class_diagram < 0 or class_table > class_diagram:
        issues.append(Issue(path, line_number(text, offsets["1-3"]),
                            "1-3は登場クラス表をクラス構成図より前に置いてください"))
    if "担当する仕様" not in section13[:class_diagram]:
        issues.append(Issue(path, line_number(text, offsets["1-3"]),
                            "1-3の登場クラス表に担当する仕様がありません"))

    if "変更前後の入力・判定・加工・出力差分" not in section15:
        issues.append(Issue(path, line_number(text, offsets["1-5"]),
                            "1-5に変更前後の入出力差分表がありません"))
    if "```mermaid" not in section15:
        issues.append(Issue(path, line_number(text, offsets["1-5"]),
                            "1-5に変更後の仕様整理図がありません"))
    return issues


def check_phase6_baseline(text: str, path: Path) -> list[Issue]:
    """Require a visible code baseline before phase 6 step 1.

    An introductory sentence saying that phase 6 starts from the phase 3
    code is insufficient: readers must be able to compare the actual code.
    """
    issues: list[Issue] = []
    phase6 = text.find("## 🔴 フェーズ6：対策検討")
    baseline = text.find(PHASE6_BASELINE_HEADING, phase6)
    step1 = text.find("### ステップ1：", phase6)
    if baseline < 0:
        return [Issue(path, line_number(text, phase6), "フェーズ6のステップ1前に、仕様変更後の痛みコードのおさらいがありません")]
    if step1 < 0 or not (phase6 < baseline < step1):
        issues.append(Issue(path, line_number(text, baseline), "痛みコードのおさらいはフェーズ6のステップ1直前に置いてください"))
        return issues
    recap = text[baseline:step1]
    if "フェーズ3の変更途中コード（対策前）" not in recap:
        issues.append(Issue(path, line_number(text, baseline), "比較元がフェーズ3の変更途中コードだと明記されていません"))
    if "```cpp" not in recap:
        issues.append(Issue(path, line_number(text, baseline), "ステップ1の比較元となるC++コードが再掲されていません"))
    return issues


def check_phase6_continuity(text: str, path: Path) -> list[Issue]:
    """Check that every improvement step keeps phase 3 additions visible."""
    tokens = PHASE6_CONTINUITY_TOKENS.get(path.name)
    if not tokens:
        return []
    phase6 = text.find("## 🔴 フェーズ6：対策検討")
    adoption = text.find("### 採用する形を決める", phase6)
    section = text[phase6:adoption]
    matches = list(re.finditer(r"(?m)^### ステップ(\d+)：", section))
    issues: list[Issue] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        step_text = section[match.start():end]
        for token in tokens:
            if token not in step_text:
                absolute = phase6 + match.start()
                issues.append(
                    Issue(
                        path,
                        line_number(text, absolute),
                        f"ステップ{match.group(1)}で仕様変更要素「{token}」が消えています。コードで保持するか、差分抜粋なら継続を明記してください",
                    )
                )
    return issues


def check_phase6_step_chain(text: str, path: Path) -> list[Issue]:
    """Require step 2+ to identify the immediately preceding comparison."""
    phase6 = text.find("## 🔴 フェーズ6：対策検討")
    adoption = text.find("### 採用する形を決める", phase6)
    section = text[phase6:adoption]
    matches = list(re.finditer(r"(?m)^### ステップ(\d+)：", section))
    issues: list[Issue] = []
    for index in range(1, len(matches)):
        match = matches[index]
        step_number = int(match.group(1))
        previous = step_number - 1
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        step_text = section[match.start():end]
        if f"ステップ{previous}" not in step_text:
            absolute = phase6 + match.start()
            issues.append(
                Issue(
                    path,
                    line_number(text, absolute),
                    f"ステップ{step_number}に直前のステップ{previous}との差が明記されていません",
                )
            )
    return issues


def check_phase7_continuity(text: str, path: Path) -> list[Issue]:
    """Keep the changed specification through final code and 7-4."""
    code_tokens = PHASE7_CODE_TOKENS.get(path.name, [])
    scenario_tokens = PHASE7_SCENARIO_TOKENS.get(path.name, [])
    phase7 = text.find("## 🟢 フェーズ7：対策実施")
    section72 = text.find("### 7-2：", phase7)
    section74 = text.find("### 7-4：変更シナリオ表", phase7)
    after74 = text.find("\n---", section74)
    code = text[phase7:section72]
    scenarios = text[section74:after74]
    issues: list[Issue] = []
    for token in code_tokens:
        if token not in code:
            issues.append(
                Issue(
                    path,
                    line_number(text, phase7),
                    f"フェーズ7の最終コードで仕様変更要素「{token}」が消えています",
                )
            )
    for token in scenario_tokens:
        if token not in scenarios:
            issues.append(
                Issue(
                    path,
                    line_number(text, section74),
                    f"7-4で今回の変更要求「{token}」を再評価していません",
                )
            )
    return issues


def check_intermediate_boundary_continuity(
    text: str, path: Path
) -> list[Issue]:
    """Require retained boundaries to remain explicit in phases 3 and 6."""
    tokens = PHASE_BOUNDARY_CONTINUITY_TOKENS.get(path.name, [])
    if not tokens:
        return []
    phase3 = text.find("## 🟣 フェーズ3：問題特定")
    phase4 = text.find("## 🟠 フェーズ4：原因分析", phase3)
    phase6 = text.find("## 🔴 フェーズ6：対策検討")
    phase7 = text.find("## 🟢 フェーズ7：対策実施", phase6)
    sections = [
        ("フェーズ3", phase3, text[phase3:phase4]),
        ("フェーズ6", phase6, text[phase6:phase7]),
    ]
    issues: list[Issue] = []
    for label, offset, section in sections:
        if "中間コードの継続条件" not in section:
            issues.append(
                Issue(path, line_number(text, offset),
                      f"{label}に中間コードの継続条件がありません")
            )
        for token in tokens:
            if token not in section:
                issues.append(
                    Issue(
                        path,
                        line_number(text, offset),
                        f"{label}で維持する境界「{token}」が不明です",
                    )
                )
    return issues


def check_chapter(path: Path, core: bool) -> list[Issue]:
    text = path.read_text(encoding="utf-8")
    issues = check_fences(text, path)
    issues.extend(check_duplicate_headings(text, path))
    issues.extend(check_banned_patterns(text, path))
    if core:
        issues.extend(find_in_order(text, REQUIRED_PHASES, path))
        issues.extend(find_in_order(text, REQUIRED_NUMBERED_SECTIONS, path))
        issues.extend(check_required_chapter_structures(text, path))
        issues.extend(check_phase6_baseline(text, path))
        issues.extend(check_phase6_continuity(text, path))
        issues.extend(check_phase6_step_chain(text, path))
        issues.extend(check_phase7_continuity(text, path))
        issues.extend(check_intermediate_boundary_continuity(text, path))
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
