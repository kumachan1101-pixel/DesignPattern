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
    "#### 課題箇所のおさらい（フェーズ3の関連コード）"
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

# 「対策検討のクラス図」システム構造フォーマットで章ごとに変わる語彙。
# ハードコードを避け、章の題材に合わせて主要クラス・完成形比較・7-3結果を
# 定義する。定義が無い章でこのフォーマットを使うと検証が抜けるため、
# 未定義は明示的な指摘にする（検証を弱めない）。
SYSTEM_STRUCTURE_CLASS_TOKENS = {
    "chapter01.md": [
        "PaymentCalculator", "OrderProcessor", "CartPreviewService",
        "CampaignContext", "IDiscountRule", "RuleSelector",
        "PremiumDiscount", "CampaignDiscount", "SummerSaleDiscount",
    ],
    "chapter02.md": [
        "TransferProcessor", "BatchTransferProcessor",
        "BankGateway", "SecurityAuthenticator",
        "IBankTransferService", "BankTransferService",
        "AccountDatabase", "TransferHistory",
    ],
}
SYSTEM_STRUCTURE_FINAL_FORMS = {
    "chapter01.md": [
        "ルールエンジン", "条件関数と計算関数の登録システム",
        "具象ルールの登録システム",
    ],
    "chapter02.md": ["設定駆動ゲートウェイ", "手順関数テーブル", "窓口クラス"],
}
SYSTEM_STRUCTURE_RESULT_TOKENS = {
    "chapter01.md": [
        "変更要求：サマーセール追加", "SummerSaleDiscount",
        "main / Composition Root", "CampaignContext", "RuleSelector",
    ],
    "chapter02.md": [
        "変更要求：認証フロー変更", "BankTransferService",
        "Application", "TransferProcessor",
    ],
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
        re.compile(r"私の経験でも|頭をよぎ[るり]|不安が頭|胸をなでおろ|私自身.{0,12}気づ"),
        "架空の著者体験・作り物の心情が本文に残っています（フェーズ1は事実記述にする）",
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
        "1-4": "### 1-4：実装コード（現状）",
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


def _phase6_section(text: str) -> tuple[int, str]:
    p6 = text.find("## 🔴 フェーズ6")
    if p6 < 0:
        return -1, ""
    p7 = text.find("## 🟢 フェーズ7", p6)
    return p6, text[p6:(p7 if p7 > 0 else len(text))]


def is_new_phase6(text: str) -> bool:
    """設計先行フォーマット（6-1 構造の見立て…）かどうか。"""
    _, sec = _phase6_section(text)
    return "### 6-1" in sec


def is_system_structure_phase6(section: str) -> bool:
    """既存クラス図の責任と依存を更新してコード案を導く新フォーマット。"""
    return "### 対策検討のクラス図：1-3の責任と依存をどう変えるか" in section


def check_system_structure_phase6(
        text: str, path: Path, p6: int, sec: str,
        phase5_sec: str, handoff_table_heading: str) -> list[Issue]:
    """変更軸の統合→システム構造→段階実装→全体判定を検証する。"""
    ln = line_number(text, p6)
    issues: list[Issue] = []
    required = [
        ("### 6-1", "フェーズ6に段階的なコード検討（6-1）がありません"),
        ("### 6-2", "フェーズ6に契約・データ配置（6-2）がありません"),
        ("#### 3-2の変更影響を、システム構造の材料へ統合する",
         "フェーズ6にP1・P2をシステム構造の材料へ統合する説明がありません"),
        ("| 課題ID | 変化軸と現在の影響 | 構造で移す責任 | 変えたくない範囲 |",
         "フェーズ6に変化軸・移す責任・守る範囲の統合表がありません"),
        ("#### システム全体の完了条件を固定する",
         "フェーズ6にシステム全体の完了条件がありません"),
        ("#### システム全体の最終構造を決める",
         "フェーズ6にコード作成前のシステム構造決定がありません"),
        ("| 最終システム構造 | 責任配置と依存の差 | 施策追加時に触る場所 | 判断 |",
         "構造差分のある完成システム同士の比較がありません"),
        ("### 対策検討のクラス図：1-3の責任と依存をどう変えるか",
         "フェーズ6に既存クラス図を使った責任見直しがありません"),
        ("変更前のクラス図（1-3を責任見直し用に再掲）",
         "責任見直しに変更前クラス図がありません"),
        ("採用した変更後のクラス図",
         "責任見直しに変更後クラス図がありません"),
        ("【残す】", "変更前クラス図に残す責任の表示がありません"),
        ("【移す】", "変更前クラス図に移す責任の表示がありません"),
        ("【新設】", "変更後クラス図に新設する責任の表示がありません"),
        ("classDef focus", "責任見直しの着目クラスを示す色定義がありません"),
        ("cssClass", "責任見直しの着目クラスへ色が適用されていません"),
        ("| 課題ID | クラス図をどう変えるか | コードレベルで何をするか | 実装ステップ |",
         "クラス図の変更とコード変更を対応させる表がありません"),
        ("採用するクラス図と責任配置は、コードを書く前に確定しています",
         "段階コードが採用設計の実装順だと明文化されていません"),
        ("#### 課題箇所のおさらい（フェーズ3の関連コード）",
         "フェーズ6に課題箇所だけのコードおさらいがありません"),
        ("#### システム全体のコード適用結果",
         "フェーズ6にシステム全体のコード適用結果がありません"),
        ("| システム全体の完了条件 | 対応する構造とコード | 変更後に残る作業 | 判定 |",
         "フェーズ6にシステム全体の完了条件とコードの対応表がありません"),
        ("| 共通の問い | システム全体での答え | 変えたくない側が知らなくなる詳細 |",
         "全章共通の分離・生成・依存注入・実行の問いと第1章の対応がありません"),
        ("#### 実装ステップ1", "採用設計の実装ステップ1がありません"),
        ("#### 実装ステップ2", "採用設計の実装ステップ2がありません"),
        ("#### 実装ステップ3", "採用設計の実装ステップ3がありません"),
        ("**システム全体の実装結果：達成。**",
         "採用設計によるシステム全体の達成確認がありません"),
    ]
    for token, msg in required:
        if token not in sec:
            issues.append(Issue(path, ln, msg))

    order_tokens = [
        "#### 3-2の変更影響を、システム構造の材料へ統合する",
        "#### システム全体の完了条件を固定する",
        "#### システム全体の最終構造を決める",
        "### 対策検討のクラス図：1-3の責任と依存をどう変えるか",
        "#### 課題箇所のおさらい（フェーズ3の関連コード）",
        "### 6-1",
        "### 6-2",
        "#### システム全体のコード適用結果",
    ]
    positions = [sec.find(token) for token in order_tokens]
    if min(positions) >= 0 and positions != sorted(positions):
        issues.append(Issue(
            path, ln,
            "フェーズ6は変更軸の統合→全体条件→最終構造→クラス図→関連コード→"
            "段階実装→システム全体の判定の順にしてください",
        ))

    structure_start = sec.find("### 対策検討のクラス図：1-3の責任と依存をどう変えるか")
    structure_end = sec.find("#### 課題箇所のおさらい（フェーズ3の関連コード）")
    structure_sec = sec[structure_start:structure_end]
    if structure_sec.count("```mermaid") < 2:
        issues.append(Issue(path, ln, "責任見直しに変更前と変更後のクラス図を2図示してください"))
    if structure_sec.count("classDiagram") < 2:
        issues.append(Issue(path, ln, "責任見直しの2図は既存図と同じクラス図にしてください"))
    if "flowchart" in structure_sec or "graph " in structure_sec:
        issues.append(Issue(path, ln, "責任見直しにクラス図以外の新しい図を追加しないでください"))
    class_tokens = SYSTEM_STRUCTURE_CLASS_TOKENS.get(path.name)
    if class_tokens is None:
        issues.append(Issue(path, ln,
                            "システム構造フォーマットの主要クラス語彙が未定義です"))
        class_tokens = []
    for token in class_tokens:
        if token not in structure_sec:
            issues.append(Issue(path, ln, f"責任見直しのクラス図に主要クラス {token} がありません"))

    final_forms = SYSTEM_STRUCTURE_FINAL_FORMS.get(path.name)
    if final_forms is None:
        issues.append(Issue(path, ln,
                            "システム構造フォーマットの完成形比較語彙が未定義です"))
        final_forms = []
    for final_form in final_forms:
        if final_form not in sec:
            issues.append(Issue(path, ln, f"完成形の比較に {final_form} がありません"))

    if len(extract_cpp_blocks(sec)) < 5:
        issues.append(Issue(path, ln, "フェーズ6に段階判断を確認できるコードが不足しています"))

    issue_table = "| 課題ID | 変化軸と現在の影響 | 構造で移す責任 | 変えたくない範囲 |"
    issue_start = sec.find(issue_table)
    structure_heading = sec.find("### 対策検討のクラス図：1-3の責任と依存をどう変えるか")
    issue_ids = re.findall(
        r"(?m)^\|\s*(P\d+)\s*\|",
        sec[issue_start:structure_heading],
    ) if min(issue_start, structure_heading) >= 0 else []
    handoff_start = phase5_sec.find(handoff_table_heading)
    handoff_ids = re.findall(
        r"(?m)^\|\s*(P\d+)\s*\|",
        phase5_sec[handoff_start:],
    ) if handoff_start >= 0 else []
    phase7_start = text.find("#### 変更軸ごとの完成コード追跡", p6)
    phase72 = text.find("### 7-2", phase7_start)
    phase7_ids = re.findall(
        r"(?m)^\|\s*(P\d+)\s*\|",
        text[phase7_start:phase72],
    ) if min(phase7_start, phase72) >= 0 else []
    if not issue_ids:
        issues.append(Issue(path, ln, "変更軸の統合表に課題ID行がありません"))
    else:
        expected = [f"P{i}" for i in range(1, len(issue_ids) + 1)]
        if issue_ids != expected:
            issues.append(Issue(path, ln, f"課題IDは連番にしてください: {issue_ids}"))
        for label, ids in (("フェーズ5", handoff_ids), ("完成コード追跡", phase7_ids)):
            if ids != issue_ids:
                issues.append(Issue(
                    path, ln,
                    f"{label}の課題IDを変更軸の統合表と一致させてください: {ids} != {issue_ids}",
                ))

    p7 = text.find("## 🟢 フェーズ7", p6)
    result_graph = text.find("### 7-3：変更影響グラフ（改善後）", p7)
    if result_graph < 0:
        issues.append(Issue(path, ln, "変更影響グラフの結果確認は完成コード後の7-3に置いてください"))
    else:
        graph_end = text.find("### 7-4", result_graph)
        result_sec = text[result_graph:graph_end]
        result_tokens = SYSTEM_STRUCTURE_RESULT_TOKENS.get(path.name)
        if result_tokens is None:
            issues.append(Issue(path, ln,
                                "システム構造フォーマットの7-3結果語彙が未定義です"))
            result_tokens = []
        for token in result_tokens:
            if token not in result_sec:
                issues.append(Issue(path, ln, f"7-3の結果確認に {token} がありません"))
    return issues


def check_phase6_design(text: str, path: Path) -> list[Issue]:
    """痛みグラフから構造変更・コード適用・完成結果までの追跡を確認する。"""
    if not is_new_phase6(text):
        return []
    p6, sec = _phase6_section(text)
    ln = line_number(text, p6)
    issues: list[Issue] = []
    p5 = text.find("## 🟡 フェーズ5")
    phase5_sec = text[p5:p6] if 0 <= p5 < p6 else ""
    handoff_heading = "#### フェーズ6へ渡す課題"
    handoff_table_heading = "| 課題ID | 現在の変更影響 | 変えたくない範囲 |"
    if handoff_heading not in phase5_sec:
        issues.append(Issue(path, ln, "フェーズ5末尾にフェーズ6へ渡す課題がありません"))
    if handoff_table_heading not in phase5_sec:
        issues.append(Issue(
            path, ln,
            "フェーズ5の引き渡し表に課題ID・現在の変更影響・変えたくない範囲がありません",
        ))
    if is_system_structure_phase6(sec):
        issues.extend(check_system_structure_phase6(
            text, path, p6, sec, phase5_sec, handoff_table_heading,
        ))
        return issues
    checks = [
        ("### 6-1", "フェーズ6に痛みコードの分解（6-1）がありません"),
        ("### 6-2", "フェーズ6に契約・データ配置（6-2）がありません"),
        ("### 6-3", "フェーズ6に構造の見立て（6-3）がありません"),
        ("```mermaid", "フェーズ6に構造のクラス図（mermaid）がありません"),
        ("### 6-4", "フェーズ6に影響範囲（6-4）がありません"),
        ("### 採用する形を決める", "フェーズ6に採用判断がありません"),
        ("#### 問題定義の変更影響を、どの構造で変えるか",
         "フェーズ6に問題定義の変更影響と構造を対応させたグラフがありません"),
        ('subgraph Pain["問題定義：変更前の変更影響"]',
         "構造変更グラフに問題定義で得た変更前の変更影響がありません"),
        ('subgraph TargetStructure["影響を切る構造の形"]',
         "構造変更グラフに影響を切るクラス・契約・依存関係がありません"),
        ('subgraph Result["同じ要求を再適用した変更影響"]',
         "構造変更グラフに同じ要求を再適用した変更影響がありません"),
        ("#### 構造と変更後の影響から、課題と候補を一続きで導く",
         "フェーズ6にグラフから課題・候補を一続きで導く表がありません"),
        ("| 課題ID | 変更の到達点 | 最初に試すコード変更 | 残る問題に対する次のコード変更 |",
         "フェーズ6に差・境界・完了条件・候補を同じ課題IDで結ぶ表がありません"),
        ("#### 課題箇所のおさらい（フェーズ3の関連コード）",
         "フェーズ6に課題カードで指定した関連コードのおさらいがありません"),
        ("#### 課題IDごとのコード適用結果",
         "フェーズ6に課題IDごとのコード適用結果がありません"),
        ("| 課題ID | 候補を適用したコード | 段階的なコード変更と結果 | 守った契約・完了条件の判定 |",
         "フェーズ6に適用コード・段階的なコード変更・結果・契約・完了判定の対応表がありません"),
    ]
    for token, msg in checks:
        if token not in sec:
            issues.append(Issue(path, ln, msg))
    if len(extract_cpp_blocks(sec)) < 3:
        issues.append(Issue(path, ln,
                            "フェーズ6に課題箇所のおさらい・2段階以上の関連コードがありません"))
    stale = [
        "#### 採用候補の完全コード",
        "この変換は断片コードでは示しません",
        "完全な接続コードはこのフェーズの後半で示す",
        "#### 振り返り：現行コード全体（フェーズ1）",
        "#### 候補をコードで検討するための課題カード",
        "| 課題ID | フェーズ4で見えた原因 | フェーズ5で定めた課題 | フェーズ6で試す候補 |",
        "#### 理想の変更影響グラフを先に組み立てる",
        "#### 理想グラフとの差から課題カードを導く",
        "#### 課題カードから検討候補を出す",
    ]
    for token in stale:
        if token in sec:
            issues.append(Issue(
                path, ln,
                f"完成コード先出しの旧表現が残っています: {token}",
            ))

    graph_heading = "#### 問題定義の変更影響を、どの構造で変えるか"
    trace_heading = "#### 構造と変更後の影響から、課題と候補を一続きで導く"
    trace_table_heading = (
        "| 課題ID | 変更の到達点 | 最初に試すコード変更 | 残る問題に対する次のコード変更 |"
    )
    recap_heading = "#### 課題箇所のおさらい（フェーズ3の関連コード）"
    code_result_heading = "#### 課題IDごとのコード適用結果"
    code_result_table_heading = (
        "| 課題ID | 候補を適用したコード | 段階的なコード変更と結果 | "
        "守った契約・完了条件の判定 |"
    )
    graph_heading_start = sec.find(graph_heading)
    trace_start = sec.find(trace_heading)
    trace_table_start = sec.find(trace_table_heading)
    recap_start = sec.find(recap_heading)
    code_result_start = sec.find(code_result_heading)
    code_result_table_start = sec.find(code_result_table_heading)
    step63_start = sec.find("### 6-3")
    starts = [
        graph_heading_start, trace_start, trace_table_start, recap_start,
        code_result_start, code_result_table_start, step63_start,
    ]
    if min(starts) >= 0:
        if starts != sorted(starts):
            issues.append(Issue(
                path, ln,
                "フェーズ6は痛みグラフ→課題候補表→関連コード→コード適用結果→構造の順にしてください",
            ))

        trace_rows = re.findall(
            r"(?m)^\|\s*P\d+\s*\|.*$",
            sec[trace_table_start:recap_start],
        )
        trace_ids = [
            re.match(r"^\|\s*(P\d+)\s*\|", row).group(1)
            for row in trace_rows
        ]
        code_result_rows = re.findall(
            r"(?m)^\|\s*P\d+\s*\|.*$",
            sec[code_result_table_start:step63_start],
        )
        code_result_ids = [
            re.match(r"^\|\s*(P\d+)\s*\|", row).group(1)
            for row in code_result_rows
        ]

        trace_required_labels = (
            "**現在→理想の差：**",
            "**切る境界・守る契約：**",
            "**完了条件：**",
            "**候補：**",
            "**減る影響：**",
        )
        for row in trace_rows:
            task_id = re.match(r"^\|\s*(P\d+)\s*\|", row).group(1)
            missing = [label for label in trace_required_labels if label not in row]
            if missing:
                issues.append(Issue(
                    path, ln,
                    f"{task_id}の一続き表に必須の対応項目がありません: {missing}",
                ))

        code_result_required_labels = (
            "**段階的な変更：**",
            "**結果：**",
            "**守った契約：**",
            "**判定：**",
        )
        for row in code_result_rows:
            task_id = re.match(r"^\|\s*(P\d+)\s*\|", row).group(1)
            missing = [
                label for label in code_result_required_labels if label not in row
            ]
            if missing:
                issues.append(Issue(
                    path, ln,
                    f"{task_id}のコード適用結果に必須の対応項目がありません: {missing}",
                ))
            if "`" not in row:
                issues.append(Issue(
                    path, ln,
                    f"{task_id}のコード適用結果にクラス・関数・メソッド名がありません",
                ))
        graph_start = sec.find("```mermaid", graph_heading_start, trace_start)
        graph_end = sec.find("```", graph_start + len("```mermaid"))
        graph_text = (
            sec[graph_start:graph_end]
            if graph_start >= 0 and graph_end >= 0 else ""
        )
        graph_ids = (
            re.findall(r"P\d+", graph_text)
            if graph_start >= 0 and graph_end >= 0 else []
        )
        target_match = re.search(
            r"subgraph TargetStructure.*?\n(.*?)\n\s*end",
            graph_text,
            re.DOTALL,
        )
        if target_match:
            target_structure = target_match.group(1)
            if re.search(r"P\d+-変更\d+|変更[１２12]", target_structure):
                issues.append(Issue(
                    path, ln,
                    "中央のTargetStructureを変更1→変更2の作業フローにせず、"
                    "クラス・契約・依存関係の形を描いてください",
                ))
            structure_nodes = re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\[", target_structure)
            if len(structure_nodes) < 3 or "-->" not in target_structure:
                issues.append(Issue(
                    path, ln,
                    "中央のTargetStructureには、影響を切る3つ以上の構造要素と"
                    "依存関係を描いてください",
                ))
        graph_explanation = sec[graph_end + 3:trace_start]
        if "中央" not in graph_explanation:
            issues.append(Issue(
                path, ln,
                "構造変更グラフの直後に、中央の構造で左の影響が右へどう変わるか"
                "言語化してください",
            ))
        handoff_table_start = phase5_sec.find(handoff_table_heading)
        handoff_ids = (
            re.findall(
                r"(?m)^\|\s*(P\d+)\s*\|",
                phase5_sec[handoff_table_start:],
            )
            if handoff_table_start >= 0 else []
        )

        phase7_result_heading = "#### 課題IDごとの完成コード結果"
        phase7_result_table_heading = (
            "| 課題ID | 完成コードの適用先 | 実装後に起きたこと | 完了条件の最終確認 |"
        )
        phase7_result_start = text.find(phase7_result_heading, p6)
        phase7_result_table_start = text.find(phase7_result_table_heading, p6)
        phase72_start = text.find("### 7-2", p6)
        phase7_result_ids = (
            re.findall(
                r"(?m)^\|\s*(P\d+)\s*\|",
                text[phase7_result_table_start:phase72_start],
            )
            if min(phase7_result_start, phase7_result_table_start, phase72_start) >= 0
            else []
        )
        if phase7_result_start < 0 or phase7_result_table_start < 0:
            issues.append(Issue(path, ln, "フェーズ7に課題IDごとの完成コード結果がありません"))

        if not trace_ids:
            issues.append(Issue(path, ln, "課題・候補の一続き表に課題ID行がありません"))
        else:
            expected_ids = [f"P{i}" for i in range(1, len(trace_ids) + 1)]
            if trace_ids != expected_ids:
                issues.append(Issue(
                    path, ln,
                    "課題・候補表の課題IDは重複・欠番なしの連番にしてください: "
                    f"実際={trace_ids}, 期待={expected_ids}",
                ))
            if code_result_ids != trace_ids:
                issues.append(Issue(
                    path, ln,
                    "コード適用結果の課題IDは課題・候補表と同じ順序・一課題一行にしてください: "
                    f"適用結果={code_result_ids}, 課題={trace_ids}",
                ))
            if set(graph_ids) != set(trace_ids):
                issues.append(Issue(
                    path, ln,
                    "構造変更グラフは全課題IDだけを使って変更前の影響→構造上の境界→変更後の影響を追跡してください: "
                    f"グラフ={sorted(set(graph_ids))}, 課題={trace_ids}",
                ))
            if handoff_ids != trace_ids:
                issues.append(Issue(
                    path, ln,
                    "フェーズ5の引き渡し課題IDは課題・候補表と同じ連番にしてください: "
                    f"引き渡し={handoff_ids}, 課題={trace_ids}",
                ))
            if phase7_result_ids != trace_ids:
                issues.append(Issue(
                    path, ln,
                    "完成コード結果の課題IDは課題・候補表と同じ順序・一課題一行にしてください: "
                    f"完成結果={phase7_result_ids}, 課題={trace_ids}",
                ))
    return issues


def extract_cpp_blocks(section: str) -> list[str]:
    """Return C++ blocks with their internal formatting preserved."""
    return [
        match.group(1).strip()
        for match in re.finditer(r"```cpp\s*\n(.*?)```", section, re.DOTALL)
    ]


def check_phase6_complete_comparison_code(text: str, path: Path) -> list[Issue]:
    """課題関連コード・段階コード・完成コードの役割分担を確認する。"""
    stage_end_marker = (
        "#### システム全体のコード適用結果"
        if "#### システム全体のコード適用結果" in text
        else "### 6-3："
    )
    markers = {
        "recap": "#### 課題箇所のおさらい（フェーズ3の関連コード）",
        "step61": "### 6-1：",
        "stage_end": stage_end_marker,
        "section71": "### 7-1：",
        "section72": "### 7-2：",
    }
    offsets = {name: text.find(marker) for name, marker in markers.items()}
    if any(offset < 0 for offset in offsets.values()):
        missing = [name for name, offset in offsets.items() if offset < 0]
        return [Issue(path, 1, f"フェーズ6比較の必須要素がありません: {', '.join(missing)}")]

    recap_blocks = extract_cpp_blocks(
        text[offsets["recap"]:offsets["step61"]]
    )
    stage_blocks = extract_cpp_blocks(
        text[offsets["step61"]:offsets["stage_end"]]
    )
    phase7_code = "\n\n".join(extract_cpp_blocks(
        text[offsets["section71"]:offsets["section72"]]
    ))
    issues: list[Issue] = []

    if not recap_blocks:
        issues.append(Issue(
            path, line_number(text, offsets["recap"]),
            "フェーズ6の課題箇所のおさらいに関連C++コードがありません",
        ))
    if len(stage_blocks) < 2:
        issues.append(Issue(
            path, line_number(text, offsets["step61"]),
            "6-1/6-2に最小変更と次の変更を示す段階C++コードが不足しています",
        ))
    if not phase7_code:
        issues.append(Issue(
            path, line_number(text, offsets["section71"]),
            "7-1に統合後の完成C++コードがありません",
        ))
    return issues


def check_phase6_baseline(text: str, path: Path) -> list[Issue]:
    """Require a visible code baseline before phase 6 step 1.

    An introductory sentence saying that phase 6 starts from the phase 3
    code is insufficient: readers must be able to compare the actual code.
    """
    if is_new_phase6(text):
        return []
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
    if is_new_phase6(text):
        return []
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
    if is_new_phase6(text):
        return []
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
    ]
    if not is_new_phase6(text):
        # 設計先行フェーズ6には「中間コード」が無いため、この継続契約は課さない。
        sections.append(("フェーズ6", phase6, text[phase6:phase7]))
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


def _tables_in(lines: list[str]) -> list[tuple[int, int]]:
    """Return (start_line, end_line) index pairs for each markdown table run."""
    tables: list[tuple[int, int]] = []
    in_tbl = False
    start = 0
    in_fence = False
    for idx, ln in enumerate(lines):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
        is_row = (not in_fence) and ln.lstrip().startswith("|")
        if is_row and not in_tbl:
            in_tbl = True
            start = idx
        elif not is_row and in_tbl:
            in_tbl = False
            tables.append((start, idx - 1))
    if in_tbl:
        tables.append((start, len(lines) - 1))
    return tables


def check_error_condition_last(text: str, path: Path) -> list[Issue]:
    """Require the エラー条件表 to be the last spec table in 1-1.

    正常系の仕様（図・各種仕様表）をすべて説明した後、エラー条件表を 1-1 の
    最後（1-2 の直前）に置く。システム説明の途中でエラーを差し込まない。
    """
    i11 = text.find("### 1-1")
    i12 = text.find("### 1-2", i11)
    if i11 < 0 or i12 < 0:
        return []
    sec = text[i11:i12]
    marker = sec.rfind("**エラー条件**")
    if marker < 0:
        return [Issue(path, line_number(text, i11),
                      "1-1にエラー条件表（**エラー条件**）がありません")]
    lines = sec.splitlines(keepends=True)
    offsets = []
    pos = 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln)
    marker_line = 0
    for idx, off in enumerate(offsets):
        if off > marker:
            break
        marker_line = idx
    tables = _tables_in(lines)
    err_tbl = next(((s, e) for (s, e) in tables if s >= marker_line), None)
    if err_tbl is None:
        return [Issue(path, line_number(text, i11 + marker),
                      "エラー条件表の本体（表）が見つかりません")]
    issues: list[Issue] = []
    later_tbl = next(((s, e) for (s, e) in tables if s > err_tbl[1]), None)
    if later_tbl is not None:
        issues.append(Issue(path, line_number(text, i11 + offsets[later_tbl[0]]),
                            "エラー条件表より後に正常系の仕様表があります。"
                            "エラー条件表を1-1の最後（1-2の直前）に置いてください"))
    for idx in range(err_tbl[1] + 1, len(lines)):
        stripped = lines[idx].strip()
        if re.match(r"^\*\*[^*]+\*\*$", stripped):
            issues.append(Issue(path, line_number(text, i11 + offsets[idx]),
                                f"エラー条件表より後に仕様見出し「{stripped}」があります。"
                                "エラー条件表を1-1の最後に置いてください"))
            break
    return issues


def check_boundary_error_marker(text: str, path: Path) -> list[Issue]:
    """External-boundary failures in the error table must state their stub handling.

    掲載コードは print/固定データで外部I/Oを代替するため、ファイルオープン失敗・
    DB保存失敗・API送信失敗などは掲載コードでは発生しない。エラー条件へ挙げる場合は
    「実システムの境界」「掲載コードでは発生しない」「詳細扱いなし」等の扱いを明記する。
    """
    i11 = text.find("### 1-1")
    i12 = text.find("### 1-2", i11)
    if i11 < 0 or i12 < 0:
        return []
    marker = text.find("**エラー条件**", i11, i12)
    if marker < 0:
        return []
    block = text[marker:i12]
    boundary_re = re.compile(
        r"ファイル.{0,4}開け|ファイルオープン|外部.{0,4}API|API.{0,4}(呼び出し|失敗)|"
        r"送信.{0,4}失敗|通信.{0,6}(失敗|タイムアウト)|描画API|ファイル出力.{0,4}失敗|"
        r"DB保存|決済API"
    )
    if not boundary_re.search(block):
        return []
    marker_re = re.compile(
        r"実システム|掲載コードでは|詳細扱いなし|境界|発生しない|スタブ|"
        r"リトライ|再試行|実運用"
    )
    if marker_re.search(block):
        return []
    return [Issue(path, line_number(text, marker),
                  "外部境界の失敗をエラー条件に挙げていますが、掲載コードでの扱い"
                  "（発生しない/実システム境界/詳細扱いなし）が明記されていません")]


def _cpp_class_names(section: str) -> set[str]:
    cpp = "\n".join(extract_cpp_blocks(section))
    return set(re.findall(r"\bclass\s+(\w+)", cpp))


def _diagram_class_names(diagram: str) -> set[str]:
    names = set(re.findall(r"\bclass\s+(\w+)", diagram))
    relation = re.compile(
        r"^\s*(\w+)\s+(?:<\|--|<\|\.\.|-->|\.\.>|o-->|\*-->|--\|>)\s*(\w+)",
        re.MULTILINE,
    )
    for match in relation.finditer(diagram):
        names.update(match.groups())
    return names


def check_class_diagram_completeness(text: str, path: Path) -> list[Issue]:
    """現状・採用構造・完成コードの全classを対応するクラス図へ載せる。"""
    ranges = []
    s13 = text.find("### 1-3：")
    s14 = text.find("### 1-4：")
    s15 = text.find("### 1-5：", s14)
    if min(s13, s14, s15) >= 0:
        ranges.append(("1-3", s13, s14, text[s14:s15]))

    s71 = text.find("### 7-1：")
    diagram_heading = text.find("#### 解決後のクラス構成", s71)
    if min(s71, diagram_heading) >= 0:
        final_code = text[s71:diagram_heading]
        system_structure = text.find(
            "### 対策検討のクラス図：1-3の責任と依存をどう変えるか"
        )
        system_structure_end = text.find(
            "#### 課題箇所のおさらい（フェーズ3の関連コード）",
            system_structure,
        )
        if min(system_structure, system_structure_end) >= 0:
            phase6_diagrams = list(re.finditer(
                r"classDiagram", text[system_structure:system_structure_end]
            ))
            if phase6_diagrams:
                last_diagram = system_structure + phase6_diagrams[-1].start()
                ranges.append((
                    "フェーズ6採用構造",
                    last_diagram,
                    system_structure_end,
                    final_code,
                ))
        else:
            s63 = text.find("### 6-3：")
            s64 = text.find("### 6-4：", s63)
            if min(s63, s64) >= 0:
                phase6_diagrams = list(re.finditer(
                    r"classDiagram", text[s63:s64]
                ))
                if phase6_diagrams:
                    last_diagram = s63 + phase6_diagrams[-1].start()
                    ranges.append(("6-3対策後", last_diagram, s64, final_code))
        ranges.append(("7-1", diagram_heading, len(text),
                       final_code))

    issues: list[Issue] = []
    for label, diagram_start, diagram_limit, code_section in ranges:
        class_diagram = text.find("classDiagram", diagram_start, diagram_limit)
        if class_diagram < 0:
            issues.append(Issue(
                path, line_number(text, diagram_start),
                f"{label}に対応するclassDiagramがありません",
            ))
            continue
        diagram_end = text.find("```", class_diagram)
        diagram = text[class_diagram:diagram_end]
        missing = sorted(
            _cpp_class_names(code_section) - _diagram_class_names(diagram)
        )
        if missing:
            issues.append(Issue(
                path, line_number(text, class_diagram),
                f"{label}のコードにあるクラスがクラス図にありません: "
                + ", ".join(missing),
            ))
    return issues


def check_state_automation(text: str, path: Path) -> list[Issue]:
    """State章の自動昇格・数値ログ・状態不変エラーを機械確認する。"""
    if path.name != "chapter03.md":
        return []
    s71 = text.find("### 7-1：")
    s72 = text.find("### 7-2：", s71)
    final = text[s71:s72]
    required = {
        "ReservationWaitlist": "キャンセル待ちキューが完成コードにありません",
        "promoteNextWaitlisted": "キャンセル後の自動昇格呼び出しがありません",
        "50/50": "満席の予約数ログがありません",
        "49/50": "キャンセル・自動昇格の予約数ログがありません",
        "利用側が昇格メソッドを呼ぶ行はありません":
            "自動昇格であることの実行結果説明がありません",
    }
    issues: list[Issue] = []
    for token, message in required.items():
        if token not in final:
            issues.append(Issue(path, line_number(text, s71), message))
    if re.search(r"\w+\.upgrade\s*\(", final):
        issues.append(Issue(
            path, line_number(text, s71),
            "完成コードの利用側がキャンセル待ち昇格を手動実行しています",
        ))
    state_diagrams = re.findall(
        r"```mermaid\s*\nstateDiagram-v2(.*?)```", text, re.DOTALL
    )
    for diagram in state_diagrams:
        for match in re.finditer(
            r"^\s*(\w+)\s*-->\s*\1\s*:\s*(.*)$", diagram, re.MULTILINE
        ):
            if re.search(r"失敗|エラー|不可|拒否", match.group(2)):
                issues.append(Issue(
                    path, line_number(text, text.find(match.group(0))),
                    "状態不変のエラーを状態遷移図の自己遷移に含めています",
                ))
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
        issues.extend(check_error_condition_last(text, path))
        issues.extend(check_boundary_error_marker(text, path))
        issues.extend(check_phase6_design(text, path))
        issues.extend(check_phase6_complete_comparison_code(text, path))
        issues.extend(check_phase6_baseline(text, path))
        issues.extend(check_phase6_continuity(text, path))
        issues.extend(check_phase6_step_chain(text, path))
        issues.extend(check_phase7_continuity(text, path))
        issues.extend(check_intermediate_boundary_continuity(text, path))
        issues.extend(check_class_diagram_completeness(text, path))
        issues.extend(check_state_automation(text, path))
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
