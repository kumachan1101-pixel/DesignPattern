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

# 直近の★指摘を横断反映した全パターン章。
REVIEWED_CHAPTERS = set(CORE_CHAPTERS)

# 第3ラウンドの「システム全体図／内部図＋現状型完全一致」を
# 全章の継続契約として検証する。
PHASE1_SYSTEM_MODEL_V3 = set(CORE_CHAPTERS)

# クラスでない組み立て役だけが接続する補助型は、架空の依存線を描かず、
# 登場型表・実行シーケンス・コードで説明する。
PHASE1_DIAGRAM_OMISSIONS = {
    "chapter04.md": {"SampleFileStore"},
}

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
    "### 2-5：変わる見込みと今回維持する範囲を確定する",
    "### 3-1：変更を試みる",
    "### 3-2：変更影響グラフ",
    "### 3-3：痛みの言語化",
    "### 4-1：痛みの根源を探る",
    "### 4-2：今回変える責任/ほかの変更から守る責任",
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
    # Chapter 1の完成形は施策ごとのbool追加をやめ、汎用コードで状態を渡す。
    # 変更要求の連続性は、対応する名前付きコードが最終コードに残ることで確認する。
    "chapter01.md": ["CampaignCode::SummerSale", "CampaignCode::RegularCampaign"],
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
    "chapter09_2.md": ["Pending", "法人"],
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
    "chapter10.md": [
        "SyncRequest",
        "SyncDataCatalog",
        "PartnerDatabase",
        "DeliveryResult",
        "BatchLog",
    ],
    "chapter11.md": ["TemplateRegistry", "ReportRenderingApi"],
}

# 仕様変更の対象外として、変更前コードと完成コードの両方に残す基盤。
# 1-5でも「変更なし」と明示し、設計改善と無関係な差分を防ぐ。
UNCHANGED_BASELINE_TOKENS = {
    "chapter01.md": ["CustomerDatabase", "CheckoutResultRenderer"],
    "chapter02.md": ["AccountDatabase", "TransferHistory"],
    "chapter03.md": ["EventDatabase"],
    "chapter04.md": ["ImportResult", "SchemaRegistry"],
    "chapter05.md": ["CategoryDatabase"],
    "chapter06.md": ["MenuDatabase", "MenuItem"],
    "chapter07.md": ["ProductDatabase"],
    "chapter08.md": ["PaymentRequest", "PaymentResult", "PaymentLog"],
    "chapter09_2.md": ["Ticket", "TicketRepository", "UserDatabase"],
    "chapter10.md": [
        "SyncRequest",
        "SyncDataCatalog",
        "DeliveryResult",
        "BatchRecord",
        "BatchLog",
    ],
    "chapter11.md": [
        "DataReader",
        "TemplateRegistry",
        "ReportRenderingApi",
    ],
    "chapter12.md": [
        "WorkflowCaseRepository",
        "ApproverDatabase",
        "NotificationTargetRepository",
    ],
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
        "SecurityAuthenticator", "verifyAccount",
        "IBankTransferService", "BankTransferService",
        "AccountDatabase", "TransferHistory",
    ],
    "chapter03.md": [
        "IReservationState", "TicketReservation", "AvailableState",
        "ReservedState", "WaitlistedState", "HeldState",
        "ReservationWaitlist", "EventDatabase",
    ],
    "chapter04.md": [
        "AbstractImporter", "StoreDataImporter", "FCDataImporter",
        "ECDataImporter", "SchemaRegistry", "ImportFileGateway",
        "SalesImportRepository", "parseData",
    ],
    "chapter05.md": [
        "IAction", "AddExpenseAction", "AddIncomeAction",
        "ActionHistory", "ExpenseManager", "IncomeManager",
        "BudgetApp", "LedgerRepository",
    ],
    "chapter06.md": [
        "IDrink", "Coffee", "ToppingWrapper", "Milk",
        "ToppingCatalog", "OrderAssembler", "CustomDrink", "MenuDatabase",
    ],
    "chapter07.md": [
        "INotification", "EmailNotifier", "DashboardUpdater",
        "ChatNotifier", "SMSNotifier", "InventoryManager",
        "ProductDatabase", "StockEventLog",
    ],
    "chapter08.md": [
        "PaymentApplication", "IPaymentProcessor", "CreditCardProcessor",
        "BankTransferProcessor", "ConvenienceStoreProcessor",
        "ProcessorRegistry", "PaymentGatewayClient", "createProcessor",
    ],
    "chapter09_2.md": [
        "ITicketPhase", "TicketService", "OpenPhase", "PendingPhase",
        "EscalatedPhase", "IPriorityRule", "CorporatePriority",
        "NormalPriority", "TicketRepository", "StaffDirectory",
        "UserDatabase", "TicketPolicySet",
    ],
    "chapter10.md": [
        "IExternalClient", "SystemAClient", "INotifier", "SlackNotifier",
        "IClientCreator", "SystemAClientCreator", "BatchExecutor",
        "ManualTriggerController", "SyncRequest", "SyncDataCatalog",
    ],
    "chapter11.md": [
        "ReportSkeleton", "MonthlyReport", "ExecutiveMonthlyReport",
        "ReportFeature", "GraphFeature", "LogoFeature",
        "WatermarkFeature", "IReportAction", "GenerateReportAction",
        "ReportActionHistory", "ReportAssembler",
    ],
    "chapter12.md": [
        "IWorkflowPhase", "WorkflowManager", "DraftPhase", "PendingPhase",
        "INotificationListener", "EmailNotifier", "IApprovalRule",
        "ManagerApprovalRule",
    ],
}
SYSTEM_STRUCTURE_FINAL_FORMS = {
    "chapter01.md": ["具象ルールの登録システム"],
    "chapter02.md": ["窓口構造"],
    "chapter03.md": ["状態分離構造", "待ち行列分離構造"],
    "chapter04.md": ["骨格固定構造"],
    "chapter05.md": ["台帳正本型", "残高集約型"],
    "chapter06.md": ["トッピングリスト構造", "装飾連結構造"],
    "chapter07.md": ["通知分離構造"],
    "chapter08.md": ["生成分離構造"],
    "chapter09_2.md": ["状態分離構造", "ルール差し替え構造"],
    "chapter10.md": ["窓口構造", "通知分離構造", "生成分離構造"],
    "chapter11.md": ["骨格固定構造", "装飾連結構造", "操作記録構造"],
    "chapter12.md": ["状態分離構造", "通知分離構造", "ルール差し替え構造"],
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
    "chapter03.md": [
        "変更要求：状態追加", "IReservationState",
        "ReservationWaitlist", "TicketReservation",
    ],
    "chapter04.md": [
        "変更要求：EC店形式の追加", "ECDataImporter",
        "AbstractImporter", "SchemaRegistry",
    ],
    "chapter05.md": [
        "変更要求：新しい操作の追加", "TransferAction",
        "ActionHistory", "IAction",
    ],
    "chapter06.md": [
        "変更要求：抹茶トッピングの追加", "Matcha",
        "ToppingCatalog", "IDrink",
    ],
    "chapter07.md": [
        "変更要求：SMS通知の追加", "SMSNotifier",
        "InventoryManager", "INotification",
    ],
    "chapter08.md": [
        "変更要求：PayPay決済の追加", "PayPayProcessor",
        "ProcessorRegistry", "IPaymentProcessor",
    ],
    "chapter09_2.md": [
        "変更要求：状態追加", "ITicketPhase",
        "IPriorityRule", "TicketService",
    ],
    "chapter10.md": [
        "変更要求：連携先の追加", "IExternalClient",
        "IClientCreator", "INotifier",
    ],
    "chapter11.md": [
        "変更要求：役員向け月次本文", "ExecutiveMonthlyReport",
        "変更要求：装飾機能の追加", "ReportFeature",
        "変更要求：再実行・取消", "IReportAction",
    ],
    "chapter12.md": [
        "変更要求：状態・遷移の追加", "IWorkflowPhase",
        "IApprovalRule", "INotificationListener",
    ],
}

# フェーズ6「構想を採用する」での候補比較は章の問題で決まる。
#   select : 本当に競合する複数案から1つを選ぶ（比較表を要求）
#   single : 分解の結果、構造が一意に定まる（比較不要、一意の宣言を要求）
#   combine: 複数のパターン構造を組み合わせる（組み合わせ表を要求）
# 未登録章は既定の select（比較表を要求し検証を弱めない）。
SYSTEM_STRUCTURE_MODE = {
    "chapter01.md": "single",
    "chapter02.md": "single",
    "chapter03.md": "combine",
    "chapter04.md": "single",
    "chapter05.md": "select",
    "chapter06.md": "select",
    "chapter07.md": "single",
    "chapter08.md": "single",
    "chapter09_2.md": "combine",
    "chapter10.md": "combine",
    "chapter11.md": "combine",
    "chapter12.md": "combine",
}

# 2026-07-20 第1章確定版（RESTRUCTURE_PLAN.md）。全章で、フェーズ5は
# 接続点表1枚、フェーズ6は分離・配置・組み立てへ直接接続する。
# 重複する引き渡し表・受け入れ条件再掲・変更影響の再統合表は置かない。
SYSTEM_STRUCTURE_V2 = set(CORE_CHAPTERS)
SYSTEM_STRUCTURE_DIRECT_FLOW = set(CORE_CHAPTERS)

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
    (
        re.compile(r"\*\*この章が扱う複雑さ\*\*"),
        "著者向けの分類見出しではなく、題材固有の処理・変更点・確認点で名付けてください",
    ),
    (
        re.compile(r"\*\*本章での簡易実現モデル\*\*"),
        "変更要求固有の模擬方法は、認証・補償など対象を見出しへ出してください",
    ),
]


# validate_book.py が本文へ要求する表頭。テンプレートとも共有するため定数化する。
# ここを変えたら templates/chapter-template.md も同じ語へ直す
# （check_validator_template_sync が片方だけの変更を検出する）。
PHASE5_CAUSE_HEADER = (
    "| 原因ID・確定した事実 | そのままだと残る痛み | 課題候補 | 候補を導いた理由 |"
)
PHASE5_ISSUE_HEADER = (
    "| 課題ID・接続点 | 接続するもの・変わる側 | 守る側 | 完了条件 |"
)

# 5-2は課題別の手段比較表にせず、全原因を解ける境界への
# 統合／分割判断を本文で説明する。テンプレートと同期する表頭は5-1と5-3のみ。
REQUIRED_TABLE_HEADERS = (PHASE5_CAUSE_HEADER, PHASE5_ISSUE_HEADER)


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
    has_spec_diagram = (
        "仕様整理図" in section11
        or (
            "システム全体図" in section11
            and "システム内部図" in section11
        )
    )
    if not has_spec_diagram or "```mermaid" not in section11:
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
    """現在の構想先行フォーマットかどうか。"""
    _, sec = _phase6_section(text)
    return "### 構想を決める" in sec


def extract_cpp_blocks(section: str) -> list[str]:
    """Return C++ blocks with their internal formatting preserved."""
    return [
        match.group(1).strip()
        for match in re.finditer(r"```cpp\s*\n(.*?)```", section, re.DOTALL)
    ]


def check_phase6_complete_comparison_code(text: str, path: Path) -> list[Issue]:
    """対策検討は要点コード、対策実施は完成コードを担う。"""
    p6, phase6 = _phase6_section(text)
    p7 = text.find("## 🟢 フェーズ7", p6)
    section72 = text.find("### 7-2：", p7)
    phase7 = text[p7:section72] if 0 <= p7 < section72 else ""
    issues: list[Issue] = []
    if p6 < 0 or p7 < 0 or section72 < 0:
        return [Issue(path, 1, "フェーズ6・7のコード役割を照合できません")]
    if len(extract_cpp_blocks(phase6)) < 5:
        issues.append(Issue(
            path, line_number(text, p6),
            "フェーズ6に契約・具体・生成や受け渡し・実行を連続確認する要点C++コードが不足しています",
        ))
    if not extract_cpp_blocks(phase7):
        issues.append(Issue(
            path, line_number(text, p7),
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
        # 求めるのは「抜粋の範囲を読者へ伝えていること」であって、
        # 「抜粋の前提」という編集側のラベルではない（EDIT-002）。
        if "この抜粋の外は、現状のままです。" not in section:
            issues.append(
                Issue(path, line_number(text, offset),
                      f"{label}に、どこを抜き出し周辺を変えていないかの断りが"
                      "ありません（`> **この抜粋の外は、現状のままです。**`）")
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


def check_unchanged_baseline(text: str, path: Path) -> list[Issue]:
    """Require declared unchanged data contracts in both before/after code."""
    tokens = UNCHANGED_BASELINE_TOKENS.get(path.name, [])
    if not tokens:
        return []

    s14 = text.find("### 1-4：")
    s15 = text.find("### 1-5：", s14)
    phase2 = text.find("## 🟣 フェーズ2：", s15)
    s71 = text.find("### 7-1：")
    s72 = text.find("### 7-2：", s71)
    if min(s14, s15, phase2, s71, s72) < 0:
        return []

    before_code = text[s14:s15]
    change_request = text[s15:phase2]
    final_code = text[s71:s72]
    issues: list[Issue] = []
    for token in tokens:
        if token not in before_code:
            issues.append(Issue(
                path,
                line_number(text, s14),
                f"変更対象外の共通基盤「{token}」が1-4にありません",
            ))
        if token not in final_code:
            issues.append(Issue(
                path,
                line_number(text, s71),
                f"変更対象外の共通基盤「{token}」が7-1にありません",
            ))
        if token not in change_request:
            issues.append(Issue(
                path,
                line_number(text, s15),
                f"1-5で共通基盤「{token}」を変更なしと確認していません",
            ))
    if "変更なし" not in change_request:
        issues.append(Issue(
            path,
            line_number(text, s15),
            "1-5に変更対象外の共通基盤を「変更なし」とする行がありません",
        ))
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
    # enum class は列挙型でありクラス図の対象外なので除外する。
    return set(re.findall(r"(?<!enum )\bclass\s+(\w+)", cpp))


def _cpp_type_names(section: str) -> set[str]:
    """掲載C++に定義されたclass/structを取得する（enum classは除外）。"""
    cpp = "\n".join(extract_cpp_blocks(section))
    return set(re.findall(r"(?<!enum )\b(?:class|struct)\s+(\w+)", cpp))


def _diagram_class_names(diagram: str) -> set[str]:
    names = set(re.findall(r"\bclass\s+(\w+)", diagram))
    relation = re.compile(
        r"^\s*(\w+)\s+(?:<\|--|<\|\.\.|-->|\.\.>|o-->|\*-->|--\|>)\s*(\w+)",
        re.MULTILINE,
    )
    for match in relation.finditer(diagram):
        names.update(match.groups())
    return names


def _diagram_relation_degrees(diagram: str) -> dict[str, int]:
    names = _diagram_class_names(diagram)
    degrees = {name: 0 for name in names}
    relation = re.compile(
        r"^\s*(\w+)\s+"
        r"(?:<\|--|--\|>|<\|\.\.|\.\.\|>|\*--|o--|-->|"
        r"\.\.>|--|\.\.)\s*(\w+)",
        re.MULTILINE,
    )
    for match in relation.finditer(diagram):
        left, right = match.groups()
        if left in degrees:
            degrees[left] += 1
        if right in degrees:
            degrees[right] += 1
    return degrees


def check_phase1_system_model_v3(text: str, path: Path) -> list[Issue]:
    """システム仕様図と現状コードの型を、修正済み章で完全照合する。"""
    if path.name not in PHASE1_SYSTEM_MODEL_V3:
        return []

    s11 = text.find("### 1-1：")
    s12 = text.find("### 1-2：", s11)
    s13 = text.find("### 1-3：", s12)
    s14 = text.find("### 1-4：", s13)
    s15 = text.find("### 1-5：", s14)
    if min(s11, s12, s13, s14, s15) < 0:
        return []

    section11 = text[s11:s12]
    section12 = text[s12:s13]
    section13 = text[s13:s14]
    section14 = text[s14:s15]
    issues: list[Issue] = []

    whole = section11.find("システム全体図")
    internal = section11.find("システム内部図")
    if whole < 0 or internal < 0 or whole > internal:
        issues.append(Issue(
            path,
            line_number(text, s11),
            "1-1はシステム全体図の後にシステム内部図を置いてください",
        ))
    if path.name in REVIEWED_CHAPTERS and whole >= 0 and internal > whole:
        whole_diagram = section11[whole:internal]
        if "最も大きな境界" not in whole_diagram:
            issues.append(Issue(
                path,
                line_number(text, s11 + whole),
                "システム全体図の前に、利用者→対象システム→外部サービスの"
                "最も大きな境界を説明してください",
            ))
        if "subgraph " not in whole_diagram:
            issues.append(Issue(
                path,
                line_number(text, s11 + whole),
                "システム全体図は対象システムをsubgraphで囲み、"
                "内部データと外部サービスの境界を明示してください",
            ))

    implementation_name = re.compile(
        r"\b[A-Z][A-Za-z0-9_]*"
        r"(?:Database|Repository|Client|Service|Gateway|Manager|Executor|"
        r"Application|Result|Request|Config|Notifier)\b"
    )
    # 代表入力は1-4 mainからの実コード抜粋なので型名を許可する。ここで禁じるのは、
    # 仕様説明・システム図が1-3より前に実装設計を先取りすること。
    section11_without_cpp = re.sub(r"```cpp\s*\n.*?```", "", section11, flags=re.S)
    leaked = sorted(set(implementation_name.findall(section11_without_cpp)))
    if leaked:
        issues.append(Issue(
            path,
            line_number(text, s11),
            "1-1に1-3より前の実装型名があります: " + ", ".join(leaked),
        ))

    future_tokens = {
        "chapter10.md": [
            "Slack",
            "C社",
            "D社",
            "BatchJob",
        ],
    }
    mixed = [
        token for token in future_tokens.get(path.name, [])
        if token in section11 or token in section12
    ]
    if mixed:
        issues.append(Issue(
            path,
            line_number(text, s11),
            "1-1/1-2に変更要求後の要素が混ざっています: "
            + ", ".join(mixed),
        ))

    if "| クラス名" in section12:
        issues.append(Issue(
            path,
            line_number(text, s12),
            "登場型表は1-2ではなく1-3へ置いてください",
        ))

    diagram_match = re.search(
        r"```mermaid\s*\n(classDiagram.*?)```",
        section13,
        re.DOTALL,
    )
    if not diagram_match:
        return issues
    diagram = diagram_match.group(1)
    code_types = _cpp_type_names(section14)
    diagram_types = _diagram_class_names(diagram)

    table_start = section13.find("| クラス名")
    diagram_start = section13.find("```mermaid")
    table_types: set[str] = set()
    if table_start >= 0 and diagram_start > table_start:
        table_types = set(re.findall(
            r"^\|\s*`([A-Za-z_]\w*)`\s*\|",
            section13[table_start:diagram_start],
            re.MULTILINE,
        ))

    # main()などクラスではない組み立て役だけが両者をつなぐ場合、
    # 実コードにない依存線を捏造せず、型は表とシーケンスで説明する。
    diagram_omissions = PHASE1_DIAGRAM_OMISSIONS.get(path.name, set())
    comparisons = [
        ("登場型表に不足", code_types - table_types),
        ("登場型表に現状コード外の型", table_types - code_types),
        ("クラス図に不足", code_types - diagram_types - diagram_omissions),
        ("クラス図に現状コード外の型", diagram_types - code_types),
    ]
    for label, names in comparisons:
        if names:
            issues.append(Issue(
                path,
                line_number(text, s13),
                f"1-3の{label}があります: " + ", ".join(sorted(names)),
            ))

    if len(diagram_types) > 1:
        degrees = _diagram_relation_degrees(diagram)
        floating = sorted(name for name, degree in degrees.items()
                          if degree == 0)
        if floating:
            issues.append(Issue(
                path,
                line_number(text, s13 + diagram_start),
                "1-3のクラス図に関係線のない型があります: "
                + ", ".join(floating),
            ))

    return issues


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
        required = _cpp_class_names(code_section)
        if label == "1-3":
            required -= PHASE1_DIAGRAM_OMISSIONS.get(path.name, set())
        missing = sorted(required - _diagram_class_names(diagram))
        if missing:
            issues.append(Issue(
                path, line_number(text, class_diagram),
                f"{label}のコードにあるクラスがクラス図にありません: "
                + ", ".join(missing),
            ))
    return issues


def check_phase1_input_contract_use(text: str, path: Path) -> list[Issue]:
    """仕様入力が現状・完成コードで実際のデータ選択まで使われるか確認する。"""
    s11 = text.find("### 1-1：")
    s14 = text.find("### 1-4：")
    s15 = text.find("### 1-5：", s14)
    issues: list[Issue] = []

    core_chapters = {
        "chapter01.md", "chapter02.md", "chapter03.md",
        "chapter04.md", "chapter05.md", "chapter06.md",
        "chapter07.md", "chapter08.md", "chapter09_2.md",
        "chapter10.md",
    }
    if path.name in core_chapters:
        if min(s11, s14, s15) < 0:
            return issues
        current = text[s14:s15]
        headings = (
            "#### 仕様入力が現状コードで使われるまで",
            "#### 現状コードを読んだ後の入力追跡",
        )
        if not any(heading in current for heading in headings):
            issues.append(Issue(
                path, line_number(text, s14),
                "1-4に仕様入力→受け取り口→利用箇所→結果の追跡表がありません",
            ))
        for column in (
            "仕様入力", "コード上の受け取り口",
            "実際に使う箇所", "結果への現れ方",
        ):
            if column not in current:
                issues.append(Issue(
                    path, line_number(text, s14),
                    f"1-4の仕様入力追跡表に「{column}」列がありません",
                ))

        required_current_tokens = {
            "chapter01.md": ("Order::items", "customerId", "isCampaignActive"),
            "chapter02.md": ("TransferProcessor::transfer", "amount", "verifyOTP"),
            "chapter03.md": ("eventId", "reserve()", "status"),
            "chapter04.md": ("SampleFileStore::get", "rawLines", "ImportResult"),
            "chapter05.md": ("onAddExpenseClick", "categoryId", "balance"),
            "chapter06.md": ("itemId", "hasMilk", "getPrice()"),
            "chapter07.md": ("productId", "quantity", "alertThreshold"),
            "chapter08.md": ("methodId", "orderId", "amount"),
            "chapter09_2.md": ("ticketId", "userId", "assigneeId"),
            "chapter10.md": ("partnerId", "request.target", "send(data)"),
        }
        for token in required_current_tokens[path.name]:
            if token not in current:
                issues.append(Issue(
                    path, line_number(text, s14),
                    f"1-4で仕様入力「{token}」の利用経路を追えません",
                ))

        phase1 = text[s11:s15]
        forbidden_positive_descriptions = {
            "chapter05.md": (
                "| `deque` | Undo/Redo対象を実行順に保持する",
                "成功した操作だけを履歴へ積み",
            ),
            "chapter06.md": (
                "生ポインタは包む対象への参照",
                "| `std::vector` | 注文したトッピング列を保持する",
            ),
            "chapter07.md": (
                "| `algorithm` | 通知先の検索・登録解除を行う",
                "`vector`を登録一覧に使う",
            ),
            "chapter08.md": ("double feeRate;",),
        }
        for phrase in forbidden_positive_descriptions.get(path.name, ()):
            if phrase in phase1:
                issues.append(Issue(
                    path, line_number(text, s14),
                    "1-5以降で追加する設計要素が現状説明へ混入しています: "
                    + phrase,
                ))

    if path.name != "chapter10.md":
        return issues

    s71 = text.find("### 7-1：")
    s72 = text.find("### 7-2：", s71)
    if min(s11, s14, s15, s71, s72) < 0:
        return issues

    section11 = text[s11:text.find("### 1-2：", s11)]
    current = text[s14:s15]
    final = text[s71:s72]

    required = [
        (section11, "連携先ID・同期対象",
         "1-1に同期要求の入力契約がありません", s11),
        (current, "execute(const SyncRequest& request)",
         "1-4のexecute()がSyncRequestを受け取っていません", s14),
        (current, "dataCatalog.load(request.target)",
         "1-4で同期対象がデータ取得先の選択に使われていません", s14),
        (current, "client.send(data)",
         "1-4で取得した同期データが外部送信へ渡っていません", s14),
        (final, "const SyncRequest& request",
         "7-1でSyncRequestが実行入口から消えています", s71),
        (final, "dataCatalog.load(request.target)",
         "7-1で同期対象がデータ取得先の選択に使われていません", s71),
        (final, "client.send(data, apiHealthy)",
         "7-1で取得した同期データが外部送信へ渡っていません", s71),
    ]
    for section, token, message, start in required:
        if token not in section:
            issues.append(Issue(path, line_number(text, start), message))

    fabricated = re.search(
        r"(?:client\.|client->)send\(\"(?:data|manualData)\"",
        current + final,
    )
    if fabricated:
        issues.append(Issue(
            path,
            line_number(text, s14),
            "仕様の同期対象を使わず固定文字列を外部送信しています",
        ))
    return issues


def check_recent_star_contracts(text: str, path: Path) -> list[Issue]:
    """直近の★指摘から抽出した全パターン章の横断契約を確認する。"""
    if path.name not in REVIEWED_CHAPTERS:
        return []

    issues: list[Issue] = []
    if "★" in text:
        issues.append(Issue(
            path, line_number(text, text.find("★")),
            "パターン章に未対応の★指摘が残っています",
        ))
    for block in extract_cpp_blocks(text):
        match = re.search(r"\b(?:unique_ptr|make_unique)\b", block)
        if match:
            issues.append(Issue(
                path, line_number(text, text.find(block) + match.start()),
                "掲載コードではスマートポインタを使わず、"
                "生成・所有・破棄を生ポインタで明示してください",
            ))

    p3 = text.find("## 🟣 フェーズ3")
    p4 = text.find("## 🟠 フェーズ4", p3)
    phase3 = text[p3:p4] if 0 <= p3 < p4 else ""
    for token, message in (
        ("int main(", "フェーズ3に変更要求を実行するmain()がありません"),
        # 原稿内の参照ラベルではなく、読者へ「何を見るか」を書いたかを見る。
        ("見るのは", "フェーズ3の実行結果に、何を見ればよいかの説明がありません"),
        ("実行結果", "フェーズ3に動作する変更コードの実行結果がありません"),
    ):
        if token not in phase3:
            issues.append(Issue(path, line_number(text, p3), message))
    for block in extract_cpp_blocks(phase3):
        if re.search(r"\.\.\.|既存フィールド|既存部分|も同様|同様に", block):
            issues.append(Issue(
                path, line_number(text, p3 + phase3.find(block)),
                "フェーズ3の変更コードを省略記号や「同様」で隠さず、"
                "既存の類似処理と変更前後が分かる関連範囲を示してください",
            ))

    p5 = text.find("## 🟡 フェーズ5")
    p6 = text.find("## 🔴 フェーズ6", p5)
    phase5 = text[p5:p6] if 0 <= p5 < p6 else ""
    for token in (
        "### 5-1：原因から課題候補を洗い出す",
        "### 5-2：課題候補の重複と依存を整理する",
        "### 5-3：課題IDと接続点を確定する",
        "| 課題ID・接続点 | 接続するもの・変わる側 | 守る側 | 完了条件 |",
    ):
        if token not in phase5:
            issues.append(Issue(
                path, line_number(text, p5),
                f"フェーズ5の原因→候補→評価→確定に「{token}」がありません",
            ))

    _, phase6 = _phase6_section(text)
    for token, message in (
        ("### 構想を決める",
         "フェーズ6に全体の成立条件を先に示す構想節がありません"),
        ("### 構想をコードでつなぐ",
         "フェーズ6に契約から実行までを連続確認する要点コード節がありません"),
        ("### 構想を採用する",
         "フェーズ6に課題とリスクを照合する採用判断節がありません"),
    ):
        if token not in phase6:
            issues.append(Issue(path, line_number(text, p6), message))

    s42 = text.find("### 4-2：")
    s43 = text.find("### 4-3：", s42)
    phase42 = text[s42:s43] if 0 <= s42 < s43 else ""
    if "「今回守る」と「変わらない」は異なります" not in phase42:
        issues.append(Issue(
            path, line_number(text, s42),
            "4-2で、今回守る責任を恒久的に変わらない性質と"
            "取り違えないよう説明してください",
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


def _mermaid_diagrams(section: str, diagram_type: str) -> list[str]:
    """Extract Mermaid definitions of one type from a Markdown section."""
    return re.findall(
        rf"```mermaid\s*\n({re.escape(diagram_type)}.*?)(?=\n```)",
        section,
        re.DOTALL,
    )


def _normalized_diagram(diagram: str) -> str:
    return "\n".join(line.rstrip() for line in diagram.splitlines() if line.strip())


def _require_sequential_ids(
    ids: list[str], prefix: str, path: Path, line: int, label: str,
    width: int = 0,
) -> list[Issue]:
    if not ids:
        return [Issue(path, line, f"{label}にID行がありません")]
    expected = [
        f"{prefix}{index:0{width}d}" if width else f"{prefix}{index}"
        for index in range(1, len(ids) + 1)
    ]
    if ids != expected:
        return [Issue(
            path, line,
            f"{label}のIDは重複・欠番なしの連番にしてください: "
            f"実際={ids}, 期待={expected}",
        )]
    return []


def check_phase5_phase6_reasoning_contract(
    text: str, path: Path,
) -> list[Issue]:
    """Check the cause-to-issue reasoning and adopted-design implementation flow."""
    issues: list[Issue] = []
    p5 = text.find("## 🟡 フェーズ5")
    p6 = text.find("## 🔴 フェーズ6", p5)
    p7 = text.find("## 🟢 フェーズ7", p6)
    if min(p5, p6, p7) < 0:
        return issues
    phase5 = text[p5:p6]
    phase6 = text[p6:p7]

    p4 = text.find("## 🟠 フェーズ4", 0, p5)

    h51 = phase5.find("### 5-1：原因から課題候補を洗い出す")
    h52 = phase5.find("### 5-2：課題候補の重複と依存を整理する")
    h53 = phase5.find("### 5-3：課題IDと接続点を確定する")
    if min(h51, h52, h53) < 0 or not (h51 < h52 < h53):
        issues.append(Issue(
            path, line_number(text, p5),
            "フェーズ5は原因→課題候補→システム全体評価→課題確定の順にしてください",
        ))
        return issues

    if p4 >= 0:
        premature = re.search(r"課題ID\d+", text[p4:p5 + h53])
        if premature:
            issues.append(Issue(
                path,
                line_number(text, p4 + premature.start()),
                "課題IDは5-3で確定するため、それ以前は原因IDまたは課題候補で参照してください",
            ))

        p3 = text.find("フェーズ3", 0, p4)
        phase3 = text[p3:p4] if p3 >= 0 else ""
        phase4 = text[p4:p5]
        defined_problem_ids = {
            match.group(1)
            for match in re.finditer(r"(?m)^\|\s*(問題ID\d+)\s*\|", phase3)
        }

        cause_pairs: set[tuple[str, str]] = set()
        for line in phase4.splitlines():
            if not re.match(r"^\|\s*原因ID\d+\s*\|", line):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            cause_id = cells[0]
            for problem_id in re.findall(r"問題ID\d+", cells[-1]):
                cause_pairs.add((problem_id, cause_id))

        trace_pairs: set[tuple[str, str]] = set()
        for line in phase5[h53:].splitlines():
            if not re.match(r"^\|\s*問題ID\d+", line):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            for problem_id in re.findall(r"問題ID\d+", cells[0]):
                for cause_id in re.findall(r"原因ID\d+", cells[1]):
                    trace_pairs.add((problem_id, cause_id))

        cause_problem_ids = {problem_id for problem_id, _ in cause_pairs}
        trace_problem_ids = {problem_id for problem_id, _ in trace_pairs}
        for problem_id in sorted(defined_problem_ids - cause_problem_ids):
            issues.append(Issue(
                path, line_number(text, p4),
                f"{problem_id}がフェーズ4の原因ID表へ接続されていません",
            ))
        for problem_id in sorted(defined_problem_ids - trace_problem_ids):
            issues.append(Issue(
                path, line_number(text, p5 + h53),
                f"{problem_id}が5-3の問題ID→原因ID→課題ID表へ接続されていません",
            ))
        if cause_pairs and trace_pairs and cause_pairs != trace_pairs:
            missing = sorted(cause_pairs - trace_pairs)
            extra = sorted(trace_pairs - cause_pairs)
            issues.append(Issue(
                path, line_number(text, p5 + h53),
                "原因ID表と5-3追跡表の問題ID対応が一致しません: "
                f"追跡表に不足={missing}, 追跡表だけ={extra}",
            ))

    for token, message in (
        (PHASE5_CAUSE_HEADER,
         "5-1に原因から候補を導いた理由がありません"),
        (PHASE5_ISSUE_HEADER,
         "5-3に接続点と完了条件を持つ確定課題表がありません"),
        ("変更IDと課題IDは一対一とは限らない",
         "変更IDと課題IDを別管理する理由がありません"),
        ("📌 **システム全体の完了状態**",
         "課題別ではなくシステム全体の完了状態がありません"),
    ):
        if token not in phase5:
            issues.append(Issue(path, line_number(text, p5), message))

    issue_ids = re.findall(
        r"(?m)^\|\s*(課題ID\d+)：[^|]+\|", phase5[h53:]
    )
    issues.extend(_require_sequential_ids(
        issue_ids, "課題ID", path, line_number(text, p5 + h53), "5-3の課題",
    ))

    # フェーズ5で確定した課題は、フェーズ6の採用判断まで同じIDで回収する。
    for issue_id in issue_ids:
        if issue_id not in phase6:
            issues.append(Issue(
                path, line_number(text, p6),
                f"フェーズ6の構想と採用判断に{issue_id}がありません",
            ))

    # フェーズ6の部分クラス図は判断対象だけを示すため許可する。
    # 完成図の先出しや部分図の範囲不明は、
    # check_phase6_overview_diagram で一元的に検査する。
    completed_start = text.find("#### 完成後のクラス図", p7)
    completed_end = text.find("#### 完成後の実行シーケンス", completed_start)
    completed = (
        text[completed_start:completed_end]
        if 0 <= completed_start < completed_end else ""
    )
    if not _mermaid_diagrams(completed, "classDiagram"):
        issues.append(Issue(
            path, line_number(text, p7),
            "フェーズ7の「完成後のクラス図」にclassDiagramがありません",
        ))
    return issues



def check_requirement_baseline_contract(text: str, path: Path) -> list[Issue]:
    """Keep current requirements, change requests, final requirements, and evidence separate."""
    issues: list[Issue] = []
    current_start = text.find("#### 現行要求ベースライン")
    current_end = text.find("### 1-2：", current_start)
    change_start = text.find("### 1-5：変更要求")
    phase2_start = re.search(r"(?m)^## .*?フェーズ2", text[change_start:])
    phase2 = change_start + phase2_start.start() if phase2_start else -1
    final_start = text.find("#### 変更後要求ベースライン", change_start, phase2)
    evidence_start = text.find("#### 最終要求の実装・受入エビデンス")
    evidence_end = text.find("\n#### ", evidence_start + 5)
    if min(current_start, current_end, change_start, phase2, final_start,
           evidence_start, evidence_end) < 0:
        issues.append(Issue(
            path, 1,
            "現行要求→変更依頼→変更後要求→受入エビデンスの管理節が不足しています",
        ))
        return issues

    current_section = text[current_start:current_end]
    change_section = text[change_start:phase2]
    final_section = text[final_start:phase2]
    evidence_section = text[evidence_start:evidence_end]
    current_rows = re.findall(
        r"(?m)^\|\s*(要求ID\d+)\s*\|\s*([^|]+?)\s*\|", current_section
    )
    change_rows = re.findall(
        r"(?m)^\|\s*(変更ID\d+)\s*\|\s*([^|]+?)\s*\|", change_section
    )
    # フェーズ1末の「変更ID一覧」で同じIDを再掲する締め（#94）を二重計上しない。
    _seen: set[str] = set()
    change_rows = [(cid, mean) for cid, mean in change_rows
                   if not (cid in _seen or _seen.add(cid))]
    final_rows = re.findall(
        r"(?m)^\|\s*(要求ID\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
        final_section,
    )
    # 変更後ベースライン直後の「変更前→変更後の要求対照」表（#92）で同じ
    # 要求IDを再掲するため、二重計上しないよう最初の出現だけ残す。
    _seen_final: set[str] = set()
    final_rows = [(rid, col2, col3) for rid, col2, col3 in final_rows
                  if not (rid in _seen_final or _seen_final.add(rid))]
    evidence_rows = re.findall(
        r"(?m)^\|\s*(要求ID\d+)\s*\|\s*([^|]+?)\s*\|", evidence_section
    )
    current_ids = [row[0] for row in current_rows]
    change_ids = [row[0] for row in change_rows]
    final_ids = [row[0] for row in final_rows]
    evidence_ids = [row[0] for row in evidence_rows]
    line = line_number(text, current_start)
    issues.extend(_require_sequential_ids(
        current_ids, "要求ID", path, line, "現行要求ベースライン",
    ))
    issues.extend(_require_sequential_ids(
        change_ids, "変更ID", path, line_number(text, change_start), "変更依頼",
    ))
    issues.extend(_require_sequential_ids(
        final_ids, "要求ID", path, line_number(text, final_start), "変更後要求ベースライン",
    ))
    missing_existing = [req_id for req_id in current_ids if req_id not in final_ids]
    if missing_existing:
        issues.append(Issue(
            path, line_number(text, final_start),
            "変更後要求から既存要求が消失しています: " + ", ".join(missing_existing),
        ))
    for change_id in change_ids:
        if not re.search(rf"\b{re.escape(change_id)}\b", final_section):
            issues.append(Issue(
                path, line_number(text, final_start),
                f"{change_id}が変更後要求の根拠変更IDに反映されていません",
            ))
    summary_marker = "フェーズ1のまとめ：今回追う変更ID一覧"
    summary_start = change_section.find(summary_marker)
    if summary_start >= 0:
        summary = change_section[summary_start:]
        mapped_requirements: dict[str, set[str]] = {}
        for match in re.finditer(
            r"(?m)^\|\s*(変更ID\d+)\s*\|[^|]*\|\s*([^|]+?)\s*\|",
            summary,
        ):
            mapped_requirements[match.group(1)] = set(
                re.findall(r"要求ID\d+", match.group(2))
            )
        for req_id, root_cell, _ in final_rows:
            for change_id in re.findall(r"変更ID\d+", root_cell):
                if req_id not in mapped_requirements.get(change_id, set()):
                    issues.append(Issue(
                        path, line_number(text, final_start),
                        f"{req_id}は{change_id}を根拠にしていますが、フェーズ1末の変更ID一覧で対応付けられていません",
                    ))
    if evidence_ids != final_ids:
        issues.append(Issue(
            path, line_number(text, evidence_start),
            "最終要求エビデンスは変更後ベースラインの全要求IDを"
            f"同じ順序で照合してください: {evidence_ids} != {final_ids}",
        ))
    final_meaning = {req_id: " ".join(meaning.split()) for req_id, _, meaning in final_rows}
    for req_id, meaning in evidence_rows:
        normalized = " ".join(meaning.split())
        if final_meaning.get(req_id) != normalized:
            issues.append(Issue(
                path, line_number(text, evidence_start),
                f"{req_id}の最終要求文が変更後ベースラインと一致しません",
            ))
    if re.search(r"(?m)^\|\s*変更ID\d+\s*[/／]\s*課題ID\d+", evidence_section):
        issues.append(Issue(
            path, line_number(text, evidence_start),
            "要求受入表で変更IDと課題IDを一行に統合しないでください",
        ))
    return issues


def check_new_end_to_end_traceability(text: str, path: Path) -> list[Issue]:
    """Check separate requirement evidence, design-effect evidence, and invariants."""
    issues: list[Issue] = []
    section72 = text.find("### 7-2：動作シーケンス図")
    required = (
        (
            "#### 最終要求の実装・受入エビデンス",
            ("要求ID", "最終要求", "適用コード", "実行シナリオ・観測結果", "判定"),
            r"(?m)^\|\s*要求ID\d+\s*\|",
        ),
        (
            "#### 設計課題の構造改善結果",
            ("課題ID", "構造差分・コード適用先", "確認できた効果", "残る変更先"),
            r"(?m)^\|\s*課題ID\d+\s*\|",
        ),
        (
            "#### 変更前→変更後の不変条件照合",
            ("変更対象外", "変更前", "変更後", "確認根拠"),
            r"(?m)^\|[^-\n][^\n]*\|$",
        ),
    )
    positions: list[int] = []
    for heading, tokens, row_pattern in required:
        start = text.find(heading)
        positions.append(start)
        if start < 0:
            issues.append(Issue(path, 1, f"{heading}がありません"))
            continue
        if section72 >= 0 and start > section72:
            issues.append(Issue(
                path, line_number(text, start),
                f"{heading}は完成コード直後、7-2より前に置いてください",
            ))
        end = text.find("\n#### ", start + len(heading))
        if end < 0 or (section72 >= 0 and end > section72):
            end = section72 if section72 >= 0 else len(text)
        section = text[start:end]
        for token in tokens:
            if token not in section:
                issues.append(Issue(
                    path, line_number(text, start), f"{heading}に「{token}」がありません",
                ))
        if not re.search(row_pattern, section):
            issues.append(Issue(
                path, line_number(text, start), f"{heading}に具体的な照合行がありません",
            ))
    if all(position >= 0 for position in positions) and positions != sorted(positions):
        issues.append(Issue(
            path, line_number(text, min(positions)),
            "完成コード後は要求受入→設計課題の効果→不変条件の順で照合してください",
        ))
    if "#### 要求→課題→構造→コード→結果の追跡" in text:
        issues.append(Issue(
            path, 1,
            "要求と設計課題を強制的に一表へ統合する旧追跡表が残っています",
        ))
    if "|`n|" in text:
        issues.append(Issue(path, 1, "Markdown表に文字列`nが残っています"))
    return issues


def check_end_to_end_traceability(text: str, path: Path) -> list[Issue]:
    """Require the two semantic hand-off tables introduced by CONS-007/038."""
    issues: list[Issue] = []
    trace_heading = "#### 要求→課題→構造→コード→結果の追跡"
    invariant_heading = "#### 変更前→変更後の不変条件照合"
    section72 = text.find("### 7-2：動作シーケンス図")

    for heading, required_tokens in (
        (
            trace_heading,
            (
                "確定要求ID",
                "課題ID",
                "構造差分",
                "コード適用先",
                "実行結果",
                "残る変更先",
            ),
        ),
        (
            invariant_heading,
            ("変更対象外", "変更前", "変更後", "確認根拠"),
        ),
    ):
        start = text.find(heading)
        if start < 0:
            issues.append(Issue(path, 1, f"{heading} がありません"))
            continue
        if section72 >= 0 and start > section72:
            issues.append(Issue(
                path,
                line_number(text, start),
                f"{heading} は完成コード直後、7-2より前に置いてください",
            ))
        end = text.find("\n#### ", start + len(heading))
        if end < 0 or (section72 >= 0 and end > section72):
            end = section72 if section72 >= 0 else len(text)
        section = text[start:end]
        for token in required_tokens:
            if token not in section:
                issues.append(Issue(
                    path,
                    line_number(text, start),
                    f"{heading} に「{token}」がありません",
                ))
        data_rows = re.findall(r"(?m)^\|[^-\n][^\n]*\|$", section)
        if len(data_rows) < 2:
            issues.append(Issue(
                path,
                line_number(text, start),
                f"{heading} に具体的な照合行がありません",
            ))
    return issues


def check_requirement_semantics_and_phase7_order(
    text: str, path: Path
) -> list[Issue]:
    """Keep requirement meaning, final design, and code in one checked chain."""
    issues: list[Issue] = []
    requirement_start = text.find("### 1-5：変更要求")
    phase2_start = text.find("## 🟣 フェーズ2", requirement_start)
    trace_heading = "#### 要求→課題→構造→コード→結果の追跡"
    trace_start = text.find(trace_heading)
    trace_end = text.find("\n#### ", trace_start + len(trace_heading))
    if min(requirement_start, phase2_start, trace_start, trace_end) < 0:
        return issues

    requirement_table_start = text.find(
        "| 要求ID | 確定要求", requirement_start, phase2_start
    )
    requirement_table_end = text.find("\n\n", requirement_table_start)
    requirement_section = (
        text[requirement_table_start:requirement_table_end]
        if requirement_table_start >= 0 and requirement_table_end >= 0
        else text[requirement_start:phase2_start]
    )
    trace_section = text[trace_start:trace_end]
    requirement_rows = re.findall(
        r"(?m)^\|\s*(R\d+)\s*\|\s*([^|]+)", requirement_section
    )
    trace_rows = re.findall(
        r"(?m)^\|\s*(R\d+)([^|]*)\|", trace_section
    )
    requirement_ids = [item[0] for item in requirement_rows]
    trace_ids = [item[0] for item in trace_rows]
    expected_ids = [f"R{index}" for index in range(1, len(requirement_ids) + 1)]
    if not requirement_ids:
        issues.append(Issue(
            path, line_number(text, requirement_start),
            "1-5に入力・受入条件を持つ確定要求IDがありません",
        ))
    elif requirement_ids != expected_ids:
        issues.append(Issue(
            path, line_number(text, requirement_start),
            f"確定要求IDはR1から連番にしてください: {requirement_ids}",
        ))
    if trace_ids != requirement_ids:
        issues.append(Issue(
            path, line_number(text, trace_start),
            f"1-5と完成コード追跡の要求IDを同じ順序にしてください: "
            f"{requirement_ids} != {trace_ids}",
        ))
    trace_by_id = dict(trace_rows)
    for requirement_id, meaning in requirement_rows:
        normalized_meaning = " ".join(meaning.split())
        trace_label = " ".join(trace_by_id.get(requirement_id, "").split())
        if normalized_meaning not in trace_label:
            issues.append(Issue(
                path, line_number(text, trace_start),
                f"{requirement_id}の意味が1-5から完成コード追跡へ"
                f"同じ文言で引き継がれていません: {normalized_meaning}",
            ))

    phase7_start = text.find("### 7-1：", phase2_start)
    phase7_end = text.find("### 7-2：", phase7_start)
    if min(phase7_start, phase7_end) < 0:
        return issues
    phase7 = text[phase7_start:phase7_end]
    ordered = [
        "#### 完成後のクラス一覧",
        "#### 完成後のクラス図",
        "#### 完成後の実行シーケンス",
        "#### 完成コード",
        "```cpp",
    ]
    cursor = 0
    positions: dict[str, int] = {}
    for token in ordered:
        position = phase7.find(token, cursor)
        if position < 0:
            issues.append(Issue(
                path, line_number(text, phase7_start),
                f"フェーズ7のコード前に「{token}」を置いてください",
            ))
            break
        positions[token] = position
        cursor = position + len(token)

    if all(token in positions for token in ordered):
        diagram_start = positions["#### 完成後のクラス図"]
        diagram_end = positions["#### 完成後の実行シーケンス"]
        code_start = positions["#### 完成コード"]
        diagram = phase7[diagram_start:diagram_end]
        code = phase7[code_start:]
        diagram_classes = set(re.findall(
            r"(?m)^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", diagram
        ))
        cpp = "\n".join(re.findall(
            r"```cpp\s*\n(.*?)```", code, re.DOTALL
        ))
        code_classes = set(re.findall(
            r"(?m)^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", cpp
        ))
        code_types = set(re.findall(
            r"(?m)^\s*(?:class|struct|namespace)\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)", cpp
        ))
        code_types.update(re.findall(
            r"(?m)^\s*enum\s+class\s+([A-Za-z_][A-Za-z0-9_]*)", cpp
        ))
        missing_from_diagram = sorted(code_classes - diagram_classes)
        missing_from_code = sorted(diagram_classes - code_types)
        if missing_from_diagram or missing_from_code:
            issues.append(Issue(
                path, line_number(text, phase7_start + diagram_start),
                "完成クラス図と完成コードのクラス集合が一致しません: "
                f"図に不足={missing_from_diagram}, "
                f"コードに不足={missing_from_code}",
            ))

    return issues


def check_future_risk_traceability(text: str, path: Path) -> list[Issue]:
    """Trace future risks into design evaluation without implementing them."""
    issues: list[Issue] = []
    risk_start = text.find("### 2-4：ヒアリングで判明した将来リスク")
    risk_end = text.find("### 2-5：", risk_start)
    phase6_start = text.find("## 🔴 フェーズ6：")
    phase7_start = text.find("## 🟢 フェーズ7：", phase6_start)
    design_heading = "#### 将来リスクに対して構想を確認する"
    design_start = text.find(design_heading, phase6_start, phase7_start)
    if min(risk_start, risk_end, phase6_start, phase7_start) < 0:
        return issues

    risk_section = text[risk_start:risk_end]
    if "| リスクID | 将来リスク | 時期の目安 | 根拠 |" not in risk_section:
        issues.append(Issue(
            path, line_number(text, risk_start),
            "2-4の将来リスク表を「リスクID・将来リスク・時期・根拠」の4列にしてください",
        ))
    risk_rows = re.findall(
        r"(?m)^\|\s*(リスクID\d+)\s*\|\s*([^|]+)\|",
        risk_section,
    )
    risk_ids = [risk_id for risk_id, _ in risk_rows]
    expected_ids = [f"リスクID{index}" for index in range(1, len(risk_ids) + 1)]
    if not risk_ids:
        issues.append(Issue(
            path, line_number(text, risk_start),
            "2-4にリスクID1から始まる将来リスクIDがありません",
        ))
    elif risk_ids != expected_ids:
        issues.append(Issue(
            path, line_number(text, risk_start),
            f"将来リスクIDはリスクID1から連番にしてください: {risk_ids}",
        ))

    phase3_start = text.find("## 🟣 フェーズ3：", risk_end)
    forecast_section = text[risk_end:phase3_start]
    forecast_header = (
        "| リスクID・変化軸 | 変わる見込み | 変えられるようにする部分 | "
        "今回維持する部分 |"
    )
    if forecast_header not in forecast_section:
        issues.append(Issue(
            path, line_number(text, risk_end),
            "2-5をリスクID・変わる見込み・変えられる部分・守る部分の4列にしてください",
        ))
    forecast_rows = re.findall(
        r"(?m)^\|\s*(リスクID\d+)\s*[：:]\s*([^|]+)\|\s*([^|]+)\|",
        forecast_section,
    )
    forecast_ids = [risk_id for risk_id, _, _ in forecast_rows]
    if forecast_ids != risk_ids:
        issues.append(Issue(
            path, line_number(text, risk_end),
            "2-4と2-5のリスクIDを同じ順序で対応させてください: "
            f"{risk_ids} != {forecast_ids}",
        ))
    forecast_by_id = {
        risk_id: (meaning, outlook)
        for risk_id, meaning, outlook in forecast_rows
    }
    for risk_id, meaning in risk_rows:
        expected_meaning = " ".join(meaning.split())
        actual_meaning, outlook = forecast_by_id.get(risk_id, ("", ""))
        if " ".join(actual_meaning.split()) != expected_meaning:
            issues.append(Issue(
                path, line_number(text, risk_end),
                f"{risk_id}の将来リスクが2-4から2-5へ"
                f"同じ文言で引き継がれていません: {expected_meaning}",
            ))
        if " ".join(outlook.split()) != "はい":
            issues.append(Issue(
                path, line_number(text, risk_end),
                f"{risk_id}の変わる見込みを「はい」として設計条件へ渡してください",
            ))
    for token in ("フェーズ6", "設計条件"):
        if token not in forecast_section:
            issues.append(Issue(
                path, line_number(text, risk_end),
                f"2-5に目的を示す「{token}」がありません",
            ))

    if design_start < 0:
        issues.append(Issue(
            path, line_number(text, phase6_start),
            "フェーズ6にリスクIDを採用構想へ再適用する確認表がありません",
        ))
        return issues

    design_section = text[design_start:phase7_start]
    required_tokens = (
        "リスクID・将来リスク",
        "現在の構造による備え",
        "リスク発生時の変更先",
        "守れる範囲・残る弱点",
    )
    for token in required_tokens:
        if token not in design_section:
            issues.append(Issue(
                path, line_number(text, design_start),
                f"構想採用前の将来リスク確認に「{token}」がありません",
            ))

    design_rows = re.findall(
        r"(?m)^\|\s*(リスクID\d+)\s*[：:]\s*([^|]+)\|",
        design_section,
    )
    design_ids = [risk_id for risk_id, _ in design_rows]
    if design_ids != risk_ids:
        issues.append(Issue(
            path, line_number(text, design_start),
            "2-4と6-4のリスクIDを同じ順序で対応させてください: "
            f"{risk_ids} != {design_ids}",
        ))

    design_by_id = dict(design_rows)
    for risk_id, meaning in risk_rows:
        normalized_meaning = " ".join(meaning.split())
        design_meaning = " ".join(design_by_id.get(risk_id, "").split())
        if normalized_meaning != design_meaning:
            issues.append(Issue(
                path, line_number(text, design_start),
                f"{risk_id}の将来リスクが2-4から6-4へ"
                f"同じ文言で引き継がれていません: {normalized_meaning}",
            ))

    weakness_words = re.compile(
        r"残る|弱点|必要|未|ない|外側|保証|運用|規則|管理|再設計|"
        r"再検討|変わる|課題|増える|複雑|競合|生存期間|順序|性能|制約"
    )
    for match in re.finditer(
        r"(?m)^\|\s*リスクID\d+\s*[：:].*\|$", design_section
    ):
        cells = [cell.strip() for cell in match.group(0).strip("|").split("|")]
        final_cell = cells[-1] if cells else ""
        if "完成コードへ追加しない" in final_cell:
            issues.append(Issue(
                path, line_number(text, design_start + match.start()),
                "6-4の結論を将来機能の非実装だけにせず、守れる範囲と残る弱点を評価してください",
            ))
        elif not weakness_words.search(final_cell):
            issues.append(Issue(
                path, line_number(text, design_start + match.start()),
                "6-4の最終列に、現在守れる範囲と残る弱点・制約を具体的に書いてください",
            ))

    phase4_start = text.find("## 🟠 フェーズ4：", phase3_start)
    phase7_end = text.find("## 整理", phase7_start)
    scoped_sections = (
        ("フェーズ3", phase3_start, text[phase3_start:phase4_start]),
        ("フェーズ7", phase7_start, text[phase7_start:phase7_end]),
    )
    for label, offset, section in scoped_sections:
        match = re.search(
            r"将来|未来|リスクID|この先|もし、さらに|"
            r"増えるたび|追加するたび|変わるたび|変更のたび|予告された|"
            r"^\|\s*リスクID\d+\s*[：:]",
            section,
            re.MULTILINE,
        )
        if match:
            issues.append(Issue(
                path, line_number(text, offset + match.start()),
                f"{label}にはリスクIDや未確定の変化を持ち込まず、"
                "今回確定した変更ID／変更後要求IDだけを扱ってください",
            ))

    requirement_start = text.find("### 1-5：変更要求")
    phase2_start = text.find("## 🟣 フェーズ2：", requirement_start)
    requirement_section = text[requirement_start:phase2_start]
    change_rows = re.findall(
        r"(?m)^\|\s*(変更ID\d+)\s*\|\s*([^|]+)\|",
        requirement_section,
    )
    # フェーズ1末の変更ID一覧（#94）の再掲を二重計上しない。文言照合は初出を使う。
    _seen2: set[str] = set()
    change_rows = [(cid, mean) for cid, mean in change_rows
                   if not (cid in _seen2 or _seen2.add(cid))]
    scenario_start = text.find("### 7-4：変更シナリオ表", phase7_start)
    scenario_section = text[scenario_start:phase7_end]
    if (
        "| 変更依頼 | フェーズ1の現状構造での影響 | 完成構造での結果 |"
        not in scenario_section
    ):
        issues.append(Issue(
            path, line_number(text, scenario_start),
            "7-4を変更依頼・現状構造の影響・完成構造の結果の3列にしてください",
        ))
    scenario_rows = re.findall(
        r"(?m)^\|\s*(変更ID\d+)\s*[：:]\s*([^|]+)\|",
        scenario_section,
    )
    change_ids = [change_id for change_id, _ in change_rows]
    scenario_ids = [change_id for change_id, _ in scenario_rows]
    if scenario_ids != change_ids:
        issues.append(Issue(
            path, line_number(text, scenario_start),
            "1-5と7-4の変更IDを同じ順序で対応させてください: "
            f"{change_ids} != {scenario_ids}",
        ))
    scenario_by_id = dict(scenario_rows)
    for change_id, meaning in change_rows:
        expected_meaning = " ".join(meaning.split())
        scenario_meaning = " ".join(
            scenario_by_id.get(change_id, "").split()
        )
        if scenario_meaning != expected_meaning:
            issues.append(Issue(
                path, line_number(text, scenario_start),
                f"{change_id}の変更依頼が1-5から7-4へ"
                f"同じ文言で引き継がれていません: {expected_meaning}",
            ))

    return issues


def check_overview_phase_scope(text: str, path: Path) -> list[Issue]:
    """Keep the overview's phase 3 and 7 descriptions on confirmed work."""
    if path.name != "chapter00_2.md":
        return []
    issues: list[Issue] = []
    phase3_start = text.find("## 🟣 フェーズ3：")
    phase4_start = text.find("## 🟠 フェーズ4：", phase3_start)
    phase7_start = text.find("## 🟢 フェーズ7：")
    phase7_end = text.find("### 設計構造とデザインパターンの関係", phase7_start)
    sections = (
        ("第0章のフェーズ3", phase3_start, text[phase3_start:phase4_start]),
        ("第0章のフェーズ7", phase7_start, text[phase7_start:phase7_end]),
    )
    forbidden = re.compile(
        r"将来|未来|リスクID|この先|もし、さらに|"
        r"増えるたび|追加するたび|変わるたび|変更のたび|予告された"
    )
    for label, offset, section in sections:
        match = forbidden.search(section)
        if match:
            issues.append(Issue(
                path,
                line_number(text, offset + match.start()),
                f"{label}には未確定の変化を持ち込まず、"
                "今回確定した変更ID／変更後要求IDだけを説明してください",
            ))
    return issues


def check_explanation_regression(text: str, path: Path) -> list[Issue]:
    """Keep the reader-facing explanation that structural checks cannot infer."""
    issues: list[Issue] = []

    for heading in (
        "### フェーズとこの章でやったこと",
        "### 「この章を読むと得られること」は手に入ったか",
    ):
        if heading not in text:
            issues.append(Issue(
                path, 1, f"章末の学習内容を回収する「{heading}」がありません",
            ))

    pattern_start = text.find("## パターン解説：")
    if pattern_start < 0:
        issues.append(Issue(path, 1, "章末のパターン解説がありません"))
    else:
        pattern_section = text[pattern_start:]
        if pattern_section.count("```mermaid") < 2:
            issues.append(Issue(
                path, line_number(text, pattern_start),
                "パターン解説には抽象構造図と章固有の対応図を置いてください",
            ))

    if path.name != "chapter11.md":
        return issues

    required_tokens = (
        "見当は、次の順で作ります。",
        # 課題別H3節へ分けず、二つの判断を一つの節で扱う。3つの課題の原因は
        # 冒頭の【課題の原因】でまとめて示すので、原因IDの並びで担保する。
        "【課題の原因】",
        "原因ID1（共通順が本文IDと本文内容を持つ）",
        "原因ID2（文書生成が装飾種類・順序を持つ）",
        "原因ID3（生成本体が履歴規則を持つ）",
        "**クラス図に出てくる主なメンバーと操作**",
        "+generate(request) bool",
        "+writePreview(document, path, format) bool",
        "#### 内部デバッグログ",
        "**DebugLog**",
        "**DebugLog（1-4のまま）**",
        "class DebugLog",
        "現行システムに最初からある内部基盤",
        "`DebugLog`は変更対象外の内部基盤として維持します",
        "デバッグログ件数: 0->1・event=generate・result=success",
        "デバッグログ件数: 6",
        "要求履歴4件と診断ログ6件",
        "### パターンの骨格",
        "### この章の実装との対応",
        "### 抽象骨格の実行シーケンス",
        "### 過剰適用になる例",
    )
    for token in required_tokens:
        if token not in text:
            issues.append(Issue(
                path, 1, f"第11章の説明デグレ防止要素がありません: {token}",
            ))

    explanation_ranges: list[tuple[str, int, int]] = []
    current_start = text.find("### 1-4：実装コード（現状）")
    current_end = text.find("### 1-5：変更要求", current_start)
    final_start = text.find("#### 完成コード")
    final_end = text.find("#### 実行結果", final_start)
    if min(current_start, current_end, final_start, final_end) >= 0:
        explanation_ranges = [
            ("1-4", current_start, current_end),
            ("7-1", final_start, final_end),
        ]

    for label, start, end in explanation_ranges:
        section = text[start:end]
        blocks = list(re.finditer(r"```cpp\s*\n(.*?)```", section, re.DOTALL))
        for index, block in enumerate(blocks):
            next_start = (
                blocks[index + 1].start()
                if index + 1 < len(blocks)
                else len(section)
            )
            explanation = section[block.end():next_start]
            # 掲載単位（1定義1ブロック）では説明の下限は1行。箇条書きを
            # 強制すると、名前を言い換えるだけの水増しを誘発する。
            # ここで守るのは「説明が付いていること」だけにする。
            prose = [
                ln for ln in explanation.split("\n")
                if ln.strip() and not ln.startswith("```")
                and not ln.startswith("**") and not ln.startswith("#")
                and not ln.startswith("---")
            ]
            if not prose:
                issues.append(Issue(
                    path,
                    line_number(text, start + block.start()),
                    f"第11章{label}のC++ブロック直後に説明がありません。"
                    "そのブロックで何を見るかを最低1行書いてください",
                ))

    if explanation_ranges:
        current_cpp = "\n".join(re.findall(
            r"```cpp\s*\n(.*?)```",
            text[current_start:current_end],
            re.DOTALL,
        ))
        final_cpp = "\n".join(re.findall(
            r"```cpp\s*\n(.*?)```",
            text[final_start:final_end],
            re.DOTALL,
        ))
        debug_pattern = re.compile(
            r"class\s+DebugLog\s*\{.*?\n\};",
            re.DOTALL,
        )
        current_debug = debug_pattern.search(current_cpp)
        final_debug = debug_pattern.search(final_cpp)
        if not current_debug or not final_debug:
            issues.append(Issue(
                path, 1,
                "第11章の現状コードと完成コードの両方にDebugLogが必要です",
            ))
        elif current_debug.group(0) != final_debug.group(0):
            issues.append(Issue(
                path, line_number(text, final_start),
                "第11章のDebugLogは仕様変更せず、現状と完成後で同じ実装を維持してください",
            ))

    for case_id in ("A1", "A2", "A3", "A4"):
        # 定義（`{` で始まる本体）を探す。main を先に見せるための
        # 前方宣言（`;` で終わる）はスキップする。
        function_token = f"void scenario{case_id}(ReportApplication& application) {{"
        function_start = text.find(function_token)
        code_end = text.find("```", function_start)
        # 長いケースは「実行結果（A4：submit()…）」のように処理単位で
        # 分割してよい。ケースIDまでを共通アンカーにする。
        result_label = f"実行結果（{case_id}"
        result_start = text.find(result_label, code_end)
        next_cpp = text.find("```cpp", code_end + 3)
        if (
            function_start < 0
            or code_end < 0
            or result_start < 0
            or (next_cpp >= 0 and result_start > next_cpp)
        ):
            issues.append(Issue(
                path,
                line_number(text, max(function_start, 0)),
                f"第11章{case_id}の実行コード直後に対応結果がありません",
            ))
            continue
        output_start = text.find("```", result_start)
        output_end = text.find("```", output_start + 3)
        expected_output = f"--- {case_id}:"
        if (
            output_start < 0
            or output_end < 0
            or expected_output not in text[output_start:output_end]
        ):
            issues.append(Issue(
                path,
                line_number(text, result_start),
                f"第11章{case_id}の結果ブロックが実行ケースと対応していません",
            ))

    phase7_start = text.find("### 7-1：解決後のコード（全体）")
    list_start = text.find("#### 完成後のクラス一覧", phase7_start)
    diagram_start = text.find("#### 完成後のクラス図", list_start)
    sequence_start = text.find("#### 完成後の実行シーケンス", diagram_start)
    code_start = text.find("#### 完成コード", sequence_start)
    result_start = text.find("#### 実行結果", code_start)
    if min(
        phase7_start, list_start, diagram_start,
        sequence_start, code_start, result_start,
    ) >= 0:
        listing = text[list_start:diagram_start]
        diagram = text[diagram_start:sequence_start]
        cpp = "\n".join(re.findall(
            r"```cpp\s*\n(.*?)```",
            text[code_start:result_start],
            re.DOTALL,
        ))
        declared_types = set(re.findall(
            r"(?m)^\s*(?:class|struct)\s+([A-Za-z_]\w*)", cpp
        ))
        declared_types.update(re.findall(
            r"(?m)^\s*enum\s+class\s+([A-Za-z_]\w*)", cpp
        ))
        missing_from_list = sorted(
            name for name in declared_types
            if not re.search(rf"\b{re.escape(name)}\b", listing)
        )
        missing_from_diagram = sorted(
            name for name in declared_types
            if not re.search(rf"(?m)^\s*class\s+{re.escape(name)}\b", diagram)
        )
        if missing_from_list:
            issues.append(Issue(
                path, line_number(text, list_start),
                "第11章の完成後クラス一覧に型名が不足しています: "
                + ", ".join(missing_from_list),
            ))
        if missing_from_diagram:
            issues.append(Issue(
                path, line_number(text, diagram_start),
                "第11章の完成後クラス図に型名が不足しています: "
                + ", ".join(missing_from_diagram),
            ))

    return issues


def check_standard_id_glossary(text: str, path: Path) -> list[Issue]:
    """標準IDを日本語で定義し、英字略語や標準外IDを残さない。"""
    issues: list[Issue] = []
    if path.name == "chapter00_2.md":
        for token in (
            "### 本書の番号の読み方",
            "| 表記例 | 意味 | 採番する場所 | 何を追うか |",
            "| 要求ID1 | システムが満たす要求 |",
            "| 変更ID1 | 今回届いた変更依頼 |",
            "| リスクID1 | 将来変わる可能性 |",
            "| 問題ID1 | 変更を試して観測した痛み |",
            "| 原因ID1 | 痛みを生む構造上の原因 |",
            "| 課題ID1 | 構造として解く設計課題 |",
        ):
            if token not in text:
                issues.append(Issue(
                    path, 1, f"第0章の標準ID用語表に「{token}」がありません",
                ))
    if path.name in REVIEWED_CHAPTERS and re.search(r"\bH\d+\b", text):
        issues.append(Issue(
            path, line_number(text, re.search(r"\bH\d+\b", text).start()),
            "標準外のH-IDを使わず、仮説の内容名を日本語で示してください",
        ))
    if path.name in REVIEWED_CHAPTERS:
        old_tracking_id = re.search(
            r"(?m)^\|\s*(?:REQ-\d+|CR\d+|F\d+|P\d+)\s*[|：:]", text,
        )
        if old_tracking_id:
            issues.append(Issue(
                path, line_number(text, old_tracking_id.start()),
                "追跡番号は要求ID・変更ID・リスクID・課題IDの日本語表記にしてください",
            ))
    return issues


def check_phase1_system_overview(text: str, path: Path) -> list[Issue]:
    """代表操作と結果をケースごとに隣接させ、システム全体像へつなぐ。"""
    issues: list[Issue] = []
    phase11 = text.find("### 1-1：")
    phase12 = text.find("### 1-2：", phase11)
    if min(phase11, phase12) < 0:
        return issues

    section = text[phase11:phase12]
    result_heading = "#### まず代表入力と実行結果から動きをつかむ"
    input_label = "**代表入力（1-4の`main()`から抜粋）：**"
    # 単一ケースは従来ラベル、複数ケースは「N回目の実行結果」を使う。
    result_label = "この入力に対する代表的な実行結果"
    heading = "#### 最初にシステム全体をつかむ"
    result_heading_pos = section.find(result_heading)
    result = section.find(result_label)
    if result < 0:
        split_result = re.search(r"^\d+回目の実行結果", section, re.M)
        if split_result:
            result = split_result.start()
            result_label = split_result.group(0)
    input_example = section.find(input_label)
    overview = section.find(heading)
    baseline = section.find("#### 現行要求ベースライン")

    for token, position, message in (
        (result_heading, result_heading_pos,
         "1-1冒頭に代表実行結果の見出しがありません"),
        (input_label, input_example,
         "代表実行結果に対応する入力・mainの説明がありません"),
        (result_label, result,
         "代表入力に対応する実行結果のラベルがありません"),
    ):
        if position < 0:
            issues.append(Issue(
                path, line_number(text, phase11), f"{message}: {token}",
            ))

    if overview < 0:
        issues.append(Issue(
            path, line_number(text, phase11),
            "1-1冒頭にシステム全体を説明する見出しがありません: " + heading,
        ))
        return issues

    ordered_positions = (
        result_heading_pos, input_example, result, overview, baseline,
    )
    if all(position >= 0 for position in ordered_positions) and not (
        result_heading_pos < input_example < result < overview < baseline
    ):
        issues.append(Issue(
            path, line_number(text, phase11),
            "1-1は代表入力・main→実行結果→結果の読み方→システム全体要約→現行要求の順にしてください",
        ))

    if result >= 0 and overview >= 0:
        result_text = section[result:overview]
        if "```" not in result_text:
            issues.append(Issue(
                path, line_number(text, phase11 + result),
                "代表実行結果に、読者が最初に確認できる出力ブロックがありません",
            ))
        if "この入力と出力から" not in result_text:
            issues.append(Issue(
                path, line_number(text, phase11 + result),
                "代表実行結果の直後に、一連の動きの読み方がありません",
            ))

    if input_example >= 0 and result >= 0:
        input_text = section[input_example:result]
        if "```cpp" not in input_text:
            issues.append(Issue(
                path, line_number(text, phase11 + input_example),
                "代表実行結果に対応する入力・mainのC++抜粋がありません",
            ))

    # 1-1で複数回呼ぶ場合は、各呼び出しの直後へ同じ番号の結果を置く。
    # 「全呼び出し→全結果」へ戻ると、どの結果がどの操作から出たか読者が
    # 対応づけ直さなければならないため、行数にかかわらず不合格とする。
    calls = {
        int(number): match.start()
        for match in re.finditer(r"//\s*(\d+)回目", section)
        for number in (match.group(1),)
    }
    results = {
        int(number): match.start()
        for match in re.finditer(r"^(\d+)回目の実行結果", section, re.M)
        for number in (match.group(1),)
    }
    if len(calls) >= 2:
        if set(calls) != set(results):
            issues.append(Issue(
                path, line_number(text, phase11 + input_example),
                "1-1の複数呼び出しには、同じ番号の実行結果を各1件置いてください",
            ))
        else:
            numbers = sorted(calls)
            for index, number in enumerate(numbers):
                next_call = calls[numbers[index + 1]] if index + 1 < len(numbers) else overview
                if not (calls[number] < results[number] < next_call):
                    issues.append(Issue(
                        path, line_number(text, phase11 + calls[number]),
                        f"{number}回目の呼び出し直後へ、{number}回目の実行結果を置いてください",
                    ))

    if baseline < 0 or overview > baseline:
        issues.append(Issue(
            path, line_number(text, phase11 + overview),
            "システム全体の要約は現行要求ベースラインより前に置いてください",
        ))

    overview_end = section.find("\n#### ", overview + len(heading))
    if overview_end < 0:
        overview_end = len(section)
    overview_text = section[overview:overview_end]
    for token in (
        "**入力：**",
        "**処理：**",
        "**出力：**",
        "**掲載コードでの代替：**",
    ):
        if token not in overview_text:
            issues.append(Issue(
                path, line_number(text, phase11 + overview),
                f"1-1の全体要約に「{token}」がありません",
            ))
    if "以降" not in overview_text or "詳細" not in overview_text:
        issues.append(Issue(
            path, line_number(text, phase11 + overview),
            "1-1の全体要約から後続の体系的な詳細説明への接続がありません",
        ))
    return issues


def check_phase2_interview_plan(text: str, path: Path) -> list[Issue]:
    """2-1の見当を質問へ変換してから2-3で回答する流れを確認する。"""
    issues: list[Issue] = []
    phase21 = text.find("### 2-1：")
    phase22 = text.find("### 2-2：", phase21)
    phase23 = text.find("### 2-3：", phase22)
    phase24 = text.find("### 2-4：", phase23)
    if min(phase21, phase22, phase23, phase24) < 0:
        return issues

    planning = text[phase21:phase22]
    interview = text[phase23:phase24]
    heading = "#### ヒアリングで確認すること"
    headers = (
        "| 確認したい仮説 | 確認する質問 | 確認先 |",
        "| 見当 | 現時点の仮説 | 確認する質問 | 確認先 |",
    )
    if heading not in planning:
        issues.append(Issue(
            path, line_number(text, phase21),
            f"2-1で見当を質問へ変換する「{heading}」がありません",
        ))
    if not any(header in planning for header in headers):
        issues.append(Issue(
            path, line_number(text, phase21),
            "2-1に確認したい仮説・質問・確認先の表がありません",
        ))

    plan_start = planning.find(heading)
    plan_table = planning[plan_start:] if plan_start >= 0 else ""
    rows = [
        line for line in plan_table.splitlines()
        if re.match(r"^\|.+\|.+\|.+\|$", line)
        and line not in headers
        and not re.match(r"^\|[-:|]+\|$", line.replace(" ", ""))
    ]
    if not rows:
        issues.append(Issue(
            path, line_number(text, phase21),
            "2-1のヒアリング計画に具体的な質問行がありません",
        ))
    interviewer_count = interview.count("開発者")
    if interviewer_count < len(rows):
        issues.append(Issue(
            path, line_number(text, phase23),
            "2-3は2-1で決めた各質問へ答える順で構成してください: "
            f"計画={len(rows)}件, 開発者の質問={interviewer_count}件",
        ))
    return issues


def check_phase22_change_list(text: str, path: Path) -> list[Issue]:
    """2-2は1-5で確定した変更IDを、独自分類せず同じ一覧で受け取る。"""
    change_start = text.find("### 1-5：変更要求")
    phase2 = text.find("## 🟣 フェーズ2：", change_start)
    phase22 = text.find("### 2-2：", phase2)
    phase23 = text.find("### 2-3：", phase22)
    if min(change_start, phase2, phase22, phase23) < 0:
        return []

    change_section = text[change_start:phase2]
    rows = re.findall(
        r"(?m)^\|\s*(変更ID\d+)\s*\|\s*([^|]+?)\s*\|", change_section
    )
    expected: list[tuple[str, str]] = []
    seen: set[str] = set()
    for change_id, summary in rows:
        if change_id not in seen:
            expected.append((change_id, summary.strip()))
            seen.add(change_id)

    section = text[phase22:phase23]
    actual = [
        (change_id, summary.strip())
        for change_id, summary in re.findall(
            r"(?m)^- \*\*(変更ID\d+)：(.+?)\*\*\s*$", section
        )
    ]
    issues: list[Issue] = []
    if actual != expected:
        issues.append(Issue(
            path, line_number(text, phase22),
            "2-2の変更ID一覧が1-5の確定一覧と一致しません: "
            f"1-5={expected} / 2-2={actual}",
        ))
    # EDIT-006：節番号の初出へ節名を併記したので、定型文も併記つきにする。
    required_intro = (
        "1-5（変更要求）で確定した変更IDを、"
        "そのまま今回確実に変わることとして確認します。"
    )
    if required_intro not in section:
        issues.append(Issue(
            path, line_number(text, phase22),
            "2-2は1-5の確定済み変更IDを受け取る共通導入へ統一してください",
        ))
    if re.search(r"(?m)^\|", section) or "🔴" in section or "🟢" in section:
        issues.append(Issue(
            path, line_number(text, phase22),
            "2-2へ章固有の表・色分類を足さず、変更IDの箇条書きへ統一してください",
        ))
    return issues


def check_representative_input_preparation(text: str, path: Path) -> list[Issue]:
    """1-1の代表入力は、業務入力の生成から公開操作への受け渡しまで示す。"""
    label = "**代表入力（1-4の`main()`から抜粋）：**"
    start = text.find(label)
    if start < 0:
        return []
    overview = text.find("#### 最初にシステム全体をつかむ", start)
    section = text[start:overview if overview >= 0 else start + 3200]
    blocks = re.findall(r"```cpp\s*\n(.*?)```", section, re.S)
    if not blocks:
        return []
    code = "\n".join(blocks)
    issues: list[Issue] = []

    declared = set(re.findall(r"(?m)^\s*[A-Z][A-Za-z0-9_:<>]*\s+([a-z_]\w*)\b", code))
    assigned_roots = set(re.findall(r"(?m)^\s*([a-z_]\w*)\.\w+\s*=", code))
    for name in sorted(assigned_roots - declared):
        issues.append(Issue(
            path, line_number(text, start),
            f"代表入力 `{name}` の値を設定していますが、この抜粋内で入力を生成していません",
        ))

    pseudo = set(re.findall(r"(?m)^//.*?\b([a-z_]\w*)\s*=\s*\{", code))
    for name in sorted(pseudo - declared):
        issues.append(Issue(
            path, line_number(text, start),
            f"代表入力 `{name}` をコメントだけで準備せず、実コードで生成してください",
        ))
    return issues


def check_phase14_input_trace_position(text: str, path: Path) -> list[Issue]:
    """1-4の入力追跡表が現状コードと実行結果を読んだ後にあるか確認する。"""
    s14 = text.find("### 1-4：")
    s15 = text.find("### 1-5：", s14)
    if not (0 <= s14 < s15):
        return []

    heading = "#### 仕様入力が現状コードで使われるまで"
    phase14 = text[s14:s15]
    count = phase14.count(heading)
    if count != 1:
        return [Issue(
            path,
            line_number(text, s14),
            "1-4にはコード読解後の入力追跡表を1件だけ置いてください",
        )]

    trace_pos = phase14.find(heading)
    last_fence = phase14.rfind("```")
    if last_fence >= 0 and trace_pos < last_fence:
        return [Issue(
            path,
            line_number(text, s14 + trace_pos),
            "仕様入力の追跡表は、1-4の現状コードと実行結果を読んだ後へ置いてください",
        )]
    return []


def check_payment_timeout_contract(text: str, path: Path) -> list[Issue]:
    """第8章のTIMEOUT契約を簡略化表・コード・実行結果で一致させる。"""
    if path.name != "chapter08.md":
        return []

    start = text.find("**この章での簡略化**")
    end = text.find("### 1-4：", start)
    simplification = text[start:end] if 0 <= start < end else ""
    required_rules = (
        "| カード認証 | トークンが `ERROR` で始まる | 認証失敗・再試行不可 |",
        "| カード認証 | トークンが `TIMEOUT` で始まり、同じ注文IDでの初回試行 | 通信タイムアウト・再試行可能 |",
        "| カード認証 | `TIMEOUT` の同じ注文IDでの2回目以降 | 認証成功 |",
    )
    issues: list[Issue] = []
    for rule in required_rules:
        if rule not in simplification:
            issues.append(Issue(
                path,
                line_number(text, start),
                f"第8章のスタブ判定規則にTIMEOUT契約が不足しています: {rule}",
            ))

    phase1_end = text.find("## 🟣 フェーズ2")
    phase1 = text[:phase1_end if phase1_end >= 0 else len(text)]
    for token, message in (
        ('card.cardToken.find("TIMEOUT") == 0 && attempt == 1',
         "TIMEOUTの初回だけ失敗するコードがありません"),
        ('true, "NETWORK_TIMEOUT"',
         "TIMEOUT失敗が再試行可能な結果を返していません"),
        ("TIMEOUT_ONCE", "TIMEOUTの代表入力がありません"),
        ("再試行可能なため再試行します", "TIMEOUT後の再試行結果がありません"),
    ):
        if token not in phase1:
            issues.append(Issue(path, line_number(text, start), message))
    return issues


_CPP_BLOCK_RE = re.compile(r"```cpp\n(.*?)```", re.DOTALL)
# 関数呼び出しの引数位置に直接 `new` を書く「投げっぱなしnew」。所有者へ束ねず
# その場で渡すため、誰も delete しないリークか、共有シングルトン設計との矛盾に
# なりやすい（ch03 setState(new ...)、ch05 run(new ...) の実欠陥がこの形だった）。
# 代入形 `X* p = new Y` / 返却形 `return new Y` / 装飾連結 `p = new Deco(p,..)` は
# 所有が明確なため対象外。
_ARG_NEW_RE = re.compile(r"[A-Za-z_]\w*\s*\(\s*new\s+[A-Z]")


def check_raw_new_argument_ownership(text: str, path: Path) -> list[Issue]:
    """cppブロック内で、関数/コンストラクタ引数位置の生 `new` を検出する。

    掲載コードは生ポインタ方式で、所有は代入・返却・装飾連結で明示し、破棄は
    所有者のデストラクタか使用直後の delete で行う規約。引数位置へ直接 new する形は
    所有者が定まらずリーク/設計矛盾になりやすいため、機械的に検出して見直しを促す。
    """
    issues: list[Issue] = []
    for m in _CPP_BLOCK_RE.finditer(text):
        block = m.group(1)
        block_start = m.start(1)
        for hit in _ARG_NEW_RE.finditer(block):
            ln = line_number(text, block_start + hit.start())
            issues.append(Issue(
                path, ln,
                "引数位置の生 `new`（投げっぱなしnew）です。所有者を定めて"
                "代入・返却・装飾連結の形にし、破棄先を明示してください: "
                f"{hit.group(0)}",
            ))
    return issues


def check_problem_cause_id_lists(text: str, path: Path) -> list[Issue]:
    """各方法論章はフェーズ3末に問題ID一覧、フェーズ4末に原因ID一覧を持つ。

    設計線 変更ID→問題ID→原因ID→課題ID を追跡可能にするため、フェーズ3の痛みへ
    問題ID、フェーズ4の構造原因へ原因IDを採番し、5-3末で通し一覧に束ねる。
    """
    issues: list[Issue] = []
    checks = [
        ("| 問題ID |", "フェーズ3末に問題ID一覧の表がありません（変更ID→問題IDの採番）"),
        ("問題ID1", "問題ID1が定義されていません（フェーズ3の痛みへの採番）"),
        ("| 原因ID |", "フェーズ4末に原因ID一覧の表がありません（問題ID→原因IDの対応）"),
        ("原因ID1", "原因ID1が定義されていません（フェーズ4の構造原因への採番）"),
        (
            "| 問題ID（フェーズ3の痛み） | 原因ID（フェーズ4の構造原因） | 課題ID（達成目標） |",
            "5-3末に問題ID→原因ID→課題IDの通し一覧がありません",
        ),
    ]
    for token, msg in checks:
        if token not in text:
            issues.append(Issue(path, 1, msg))
    return issues


def _section_between(text: str, head: str, end: str) -> tuple[int, str]:
    """`### head` から `### end` の直前までを返す。無ければ (-1, "")。"""
    a = re.search(rf"^### {re.escape(head)}", text, re.M)
    if not a:
        return -1, ""
    b = re.search(rf"^### {re.escape(end)}", text[a.start() + 1:], re.M)
    stop = a.start() + 1 + b.start() if b else len(text)
    return a.start(), text[a.start():stop]


def check_evidence_scenario_reference(text: str, path: Path) -> list[Issue]:
    """7-1の受入エビデンス表が、実行結果に存在しない観測結果を主張していないか。

    2026-08-12のロジック監査（LOGIC-001）で9章に見つかった症状。エビデンス表は
    「合格」と書いているのに、その受入条件を確認する実行シナリオが7-1の実行結果に
    無い、という食い違いが検出できなかった。

    完全な意味照合は機械にはできないため、ここでは「観測結果欄が参照している
    シナリオ名・ラベルが、同じ7-1節の実行結果ブロックに実在するか」だけを見る。
    観測結果欄がラベルを1つも参照していない場合は対象外（従来どおりの散文記述を
    許す）。ラベルを参照しているのに実行結果へ無ければ、書いた本人が実行して
    いない可能性が高い。
    """
    issues: list[Issue] = []
    start, section = _section_between(text, "7-1：", "7-2：")
    if start < 0:
        return issues
    marker = "#### 最終要求の実装・受入エビデンス"
    at = section.find(marker)
    if at < 0:
        return issues
    evidence = section[at:]
    # 実行結果ブロック（```text / ``` のうち cpp 以外）を集める
    outputs = "\n".join(
        body for info, body in re.findall(r"```([^\n]*)\n(.*?)```", section, re.S)
        if info.strip() != "cpp"
    )
    # 観測結果欄が参照しがちなラベル表記
    label_re = re.compile(r"(?:シナリオ|ケース|行|回帰|エラー例|A)\s?([0-9]+[a-z]?)")
    for row in re.findall(r"(?m)^\|\s*(要求ID\d+)\s*\|([^\n]*)$", evidence):
        req_id, rest = row
        cells = [c.strip() for c in rest.split("|")]
        if len(cells) < 3:
            continue
        observed = cells[2]
        if "判定" not in observed:
            continue
        for label in set(label_re.findall(observed)):
            # 「行1」「シナリオ4b」「A5」「回帰2」などが実行結果に現れるか
            if not re.search(rf"(?:シナリオ|ケース|行|回帰|エラー例|A){re.escape(label)}\b",
                             outputs):
                issues.append(Issue(
                    path, line_number(text, start + at),
                    f"{req_id}の観測結果が参照するシナリオ「{label}」が"
                    f"7-1の実行結果にありません（受入エビデンスは実行した範囲だけを書く）",
                ))
    return issues


def check_phase6_phase7_contract_match(text: str, path: Path) -> list[Issue]:
    """フェーズ6で示した契約クラスのメソッド集合が、7-1完成コードと一致するか。

    2026-08-12のロジック監査（LOGIC-003）で9章に見つかった症状。フェーズ6が
    「確定します」「採用後コード」と示した契約が、7-1では別シグネチャ・別
    メソッド名になっていた（第8章はコンパイルできない断片だった）。

    対象は `class I...` で仮想関数を持つ契約クラス。純粋仮想が1つも無く、
    既定実装だけを持つ契約（具体側が上書きしたい操作だけを差し替える形）も含める。
    フェーズ6は抜粋なので、7-1に無いメソッドがフェーズ6にある場合だけを警告する
    （7-1側が多いのは「後で追加する」と書けば許される）。
    """
    issues: list[Issue] = []
    p6_start, p6 = _phase6_section(text)
    if p6_start < 0:
        return issues
    _, p7 = _section_between(text, "7-1：", "7-2：")
    if not p7:
        return issues

    def contracts(section: str) -> dict[str, set[str]]:
        found: dict[str, set[str]] = {}
        for block in re.findall(r"```cpp\s*\n(.*?)```", section, re.S):
            for m in re.finditer(
                r"class\s+(I[A-Z]\w*)\s*(?:final\s*)?\{(.*?)\n\};", block, re.S
            ):
                name, body = m.group(1), m.group(2)
                methods = set(re.findall(r"virtual[^;{]*?\b(\w+)\s*\(", body))
                # 純粋仮想が1つも無い契約もある（既定実装だけを持ち、
                # 具体側は上書きしたい操作だけを差し替える形）。
                # `I` で始まる型に仮想関数があれば契約として扱う。
                if not methods:
                    continue
                found.setdefault(name, set()).update(methods)
        return found

    p6_contracts = contracts(p6)
    p7_contracts = contracts(p7)
    for name, p6_methods in p6_contracts.items():
        if name not in p7_contracts:
            continue
        missing = p6_methods - p7_contracts[name] - {"~" + name}
        missing = {m for m in missing if not m.startswith("~")}
        if missing:
            issues.append(Issue(
                path, line_number(text, p6_start),
                f"フェーズ6の契約 {name} にあるメソッド {sorted(missing)} が"
                f"7-1完成コードにありません（フェーズ6の契約は7-1から抜粋する）",
            ))
    return issues


def check_change_id_requirement_scope(text: str, path: Path) -> list[Issue]:
    """「フェーズ1のまとめ：変更ID一覧」の列名と中身が食い違っていないか。

    2026-08-12のロジック監査（LOGIC-007）で見つかった症状。列名が「対象の現行
    要求ID」なのに、現行ベースラインに無い追加要求IDが並んでいた（テンプレート
    由来で全12章が同じ列名を持っていた）。

    列名が「現行」を名乗る場合だけ、挙がっている要求IDが現行ベースラインに
    実在するかを検査する。
    """
    issues: list[Issue] = []
    m = re.search(r"(?m)^\|\s*変更ID\s*\|\s*変更依頼の要点\s*\|\s*([^|]+?)\s*\|", text)
    if not m:
        return issues
    column = m.group(1)
    if "現行" not in column:
        return issues
    # 現行要求ベースライン（1-1）の要求ID集合
    head = text.find("| 要求ID | 現行要求 | 受入条件 |")
    if head < 0:
        return issues
    tail = text.find("\n\n", head)
    current = set(re.findall(r"要求ID\d+", text[head:tail if tail > 0 else head + 2000]))
    rows = re.findall(r"(?m)^\|\s*(変更ID\d+)\s*\|[^|]*\|([^|]*)\|", text[m.start():])
    for change_id, cell in rows:
        for req in re.findall(r"要求ID\d+", cell):
            if req not in current:
                issues.append(Issue(
                    path, line_number(text, m.start()),
                    f"変更ID一覧の列名が「{column}」なのに、{change_id}の行へ現行"
                    f"ベースラインに無い{req}が入っています"
                    f"（列名を『関係する要求ID（追加は変更後ID）』等へ）",
                ))
    return issues


def check_step_reference_target(text: str, path: Path) -> list[Issue]:
    """本文の「ステップN」参照に、対応する見出しが同じ章にあるか。

    2026-08-12のロジック監査（LOGIC-008）で9章に見つかった症状。第0章と
    実章の構成がずれ、「フェーズ6のステップ3」のような参照先のない記述が
    残っていた。現在のフェーズ6は契約・組み立て・実行の意味名で参照する。

    フェーズ6・フェーズ7を指すステップ参照だけを対象にする（処理手順としての
    「4ステップの流れ」「差し替えるステップ」は正当な用法なので除外）。
    """
    issues: list[Issue] = []
    pattern = re.compile(
        r"(フェーズ[67]の|実装)?ステップ([0-9１-９]+)(?:〜[0-9１-９]+)?"
    )
    for m in pattern.finditer(text):
        prefix = text[max(0, m.start() - 12):m.start()]
        in_scope = (
            m.group(1) is not None
            or "フェーズ6の" in prefix
            or "フェーズ7の" in prefix
        )
        if not in_scope:
            continue
        num = m.group(2)
        # 対応する見出し（### ステップN / **ステップN** など）があるか
        if re.search(rf"(?m)^#+\s*.*ステップ{num}", text):
            continue
        if re.search(rf"(?m)^\s*ステップ{num}：", text):
            continue
        issues.append(Issue(
            path, line_number(text, m.start()),
            f"「ステップ{num}」を参照していますが、対応する見出しが章内にありません"
            f"（フェーズ6は契約・組み立て・実行の意味名で参照します）",
        ))
    return issues


def check_validator_template_sync(_text: str, path: Path) -> list[Issue]:
    """validate_book.py が期待する表頭が、テンプレートと本文で生きているか。

    2026-08-13に起きた症状。著者指摘AF-20260813-093を受けてフェーズ5-1の表頭を
    `原因として確定した事実` から `原因ID・確定した事実` へ変えたとき、全12章と
    第0章は直したが templates/chapter-template.md と validate_book.py が旧語の
    ままだった。結果、全12章が同じ検査で落ち、CIが赤くなった。

    recurrence-prevention.md は「テンプレートの項目名を変えたら validator も
    同じ語へ更新する」と定めているが、破ったことを検出する手段が無かった。
    ここでは validator が本文へ要求する表頭が、テンプレートにも存在するかを
    見る。どちらかを直し忘れれば落ちる。

    章ごとに回す必要はないので、先頭の章を処理するときだけ実行する。
    """
    issues: list[Issue] = []
    if path.name != CORE_CHAPTERS[0]:
        return issues
    template = BOOK_ROOT / "templates" / "chapter-template.md"
    if not template.exists():
        return issues
    template_text = template.read_text(encoding="utf-8")
    for header in REQUIRED_TABLE_HEADERS:
        if header not in template_text:
            issues.append(Issue(
                template, 1,
                f"validate_book.py が本文へ要求する表頭がテンプレートにありません: "
                f"{header}（片方だけ直すと全章が同じ検査で落ちます）",
            ))

    # フェーズ6の構造も、本文だけ／テンプレートだけが旧構成へ戻らないようにする。
    phase6_tokens = (
        PHASE6_EXACT_HEADING,
        *PHASE6_DECISION_HEADINGS,
        "#### 契約：",
        "#### 具体：",
        "#### 生成・所有・受け渡しを決める",
        "#### 実行骨格：組み立てた実体を契約から呼ぶ",
        "#### 公開入口から具体の実行まで追う",
        "#### 課題から採用構想までを照合する",
        "#### 将来リスクに対して構想を確認する",
    )
    for token in phase6_tokens:
        if token not in template_text:
            issues.append(Issue(
                template, 1,
                f"フェーズ6の本文規約が章テンプレートにありません: {token}",
            ))
    for token in (
        "第0章「掲載コードを手元で動かす」",
        "トップレベルの`class`、`struct`、`enum class`を1ブロックに1つ",
        "入力・取得、判定、選択・計算、状態変更・保存、通知・返却",
    ):
        if token not in template_text:
            issues.append(Issue(
                template, 1,
                f"コード掲載規約が章テンプレートにありません: {token}",
            ))

    chapter0_template = BOOK_ROOT / "templates" / "chapter0-template.md"
    if chapter0_template.exists():
        chapter0_text = chapter0_template.read_text(encoding="utf-8")
        for token in (
            "フェーズ6：対策検討 ―― 構想を一つのコード経路へ変える",
            "契約→代表具体→生成・所有・登録または選択→受け渡し→実行骨格→公開入口",
            "生成・登録・選択・注入を同じ語でまとめず",
            "課題IDとの対応と将来リスク",
            "掲載コードの読み方と実ファイルの分け方",
            "`.h`へ公開契約・クラス宣言",
            "`main.cpp`へ生成・登録・注入",
        ):
            if token not in chapter0_text:
                issues.append(Issue(
                    chapter0_template, 1,
                    f"第0章テンプレートにフェーズ6の共通語がありません: {token}",
                ))
    return issues


def _table_cell_count(row: str) -> int:
    """表の行のセル数を数える。バッククォート内の `|` は区切りにしない。"""
    body = row.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    cells = 1
    in_code = False
    for ch in body:
        if ch == "`":
            in_code = not in_code
        elif ch == "|" and not in_code:
            cells += 1
    return cells


def check_table_column_consistency(text: str, path: Path) -> list[Issue]:
    """表の各行のセル数を、その表の表頭とそろえる。

    2026-08-13に見つかった症状。第0章「本書の番号の読み方」の原因ID行が
    `| 原因ID1：痛みを生む構造上の原因 | フェーズ4 | … |` と3列になっており、
    表頭4列に対して「表記例」と「意味」が1セルへ潰れていた。Kindleでは列が
    ずれて表示される。

    既存の check_kindle.py は「4列を超えないか」だけを見るため、列が足りない
    行は素通りしていた。check_standard_id_glossary も原因ID行を見ていなかった。
    ここでは表頭とデータ行のセル数一致を全表で見る。
    """
    issues: list[Issue] = []
    lines = text.split("\n")
    for start, end in _tables_in(lines):
        header_cells = _table_cell_count(lines[start])
        for idx in range(start + 1, end + 1):
            row = lines[idx]
            if re.fullmatch(r"\|[\s:\-|]+\|", row.strip()):
                continue
            cells = _table_cell_count(row)
            if cells != header_cells:
                issues.append(Issue(
                    path, idx + 1,
                    f"表の列数が表頭と違います（表頭{header_cells}列・この行"
                    f"{cells}列）。区切りの `|` の過不足を直してください",
                ))
    return issues


CLASS_STYLE_NAMES = (
    "focus", "pain", "stable", "changed", "normal", "pending",
    "data", "decision", "process", "input", "output", "result",
    "actor", "boundary", "external", "system",
)


def check_class_diagram_focus_syntax(text: str, path: Path) -> list[Issue]:
    """classDiagram で `class X focus`（スペース形）を禁止する。

    Mermaid の classDiagram では `class X focus` は着色ではなく
    「Xfocus」という別ノードの新規宣言と解釈され、関係線を持たない
    phantom（浮きクラス）を生む。着色は `class X:::focus` か
    `cssClass "X" focus` を使う。flowchart では逆にスペース形が正しい
    ため、classDiagram ブロックだけを対象にする。
    """
    issues: list[Issue] = []
    style_alt = "|".join(CLASS_STYLE_NAMES)
    phantom = re.compile(
        rf"^\s*class\s+[A-Za-z_]\w*\s+(?:{style_alt})\s*$", re.MULTILINE
    )
    for m in re.finditer(r"```mermaid\s*\n(.*?)```", text, re.DOTALL):
        body = m.group(1)
        first = body.strip().splitlines()[0].strip() if body.strip() else ""
        if not first.startswith("classDiagram"):
            continue
        if phantom.search(body):
            bad = phantom.search(body).group(0).strip()
            issues.append(Issue(
                path, line_number(text, m.start()),
                f"classDiagramの着色は `:::` を使ってください（phantom浮きクラスを生む禁止構文）: {bad}",
            ))
    return issues


def check_class_diagram_direction(text: str, path: Path) -> list[Issue]:
    """classDiagram に明記する向きは TB へ統一する。"""
    issues: list[Issue] = []
    for match in re.finditer(
        r"```mermaid\s*\n(classDiagram.*?)(?=\n```)", text, re.DOTALL
    ):
        diagram = match.group(1)
        direction = re.search(r"(?m)^\s*direction\s+(\w+)\s*$", diagram)
        if direction and direction.group(1) != "TB":
            issues.append(Issue(
                path,
                line_number(text, match.start(1) + direction.start()),
                "classDiagramの向きはdirection TBへ統一してください",
            ))
    return issues


def check_common_phase_headings(text: str, path: Path) -> list[Issue]:
    """全パターン章で共通に使うフェーズ小見出しを固定する。"""
    issues: list[Issue] = []
    required = (
        "### 4-3：",
    )
    for heading in required:
        if heading not in text:
            issues.append(Issue(
                path,
                1,
                f"共通見出しがありません: {heading}",
            ))
    return issues


def check_phase42_comparison_header(text: str, path: Path) -> list[Issue]:
    """4-2の比較軸を全パターン章で同じ2列へ固定する。"""
    start = text.find("### 4-2：")
    end = text.find("### 4-3：", start)
    if start < 0 or end < 0:
        return []
    section = text[start:end]
    expected = "| **今回変える責任** | **ほかの変更から守る責任** |"
    if expected in section:
        return []
    return [Issue(
        path,
        line_number(text, start),
        "4-2の比較表は `今回変える責任` / `ほかの変更から守る責任` の2列へ統一してください",
    )]


def check_phase6_overview_diagram(text: str, path: Path) -> list[Issue]:
    """フェーズ6は判断ごとの部分図、フェーズ7は統合後の完成図に分ける。"""
    p6, section = _phase6_section(text)
    if p6 < 0:
        return []
    issues: list[Issue] = []

    class_diagrams = _mermaid_diagrams(section, "classDiagram")
    complete_markers = (
        "#### 完成後のクラス図",
        "#### 完成クラス図",
        "システム全体の完成図",
        "統合した完成クラス図",
    )
    if class_diagrams and any(marker in section for marker in complete_markers):
        issues.append(Issue(
            path, line_number(text, p6),
            "フェーズ6に完成クラス図を先出ししないでください。"
            "ここでは今判断する関係だけの部分クラス図、"
            "統合した完成図はフェーズ7に置きます",
        ))
    if class_diagrams and "部分クラス図" not in section:
        issues.append(Issue(
            path, line_number(text, p6),
            "フェーズ6のクラス図は、判断対象だけの部分クラス図だと明記してください",
        ))
    if class_diagrams and not re.search(r"省(?:い|く|け|か|略|くと)", section):
        issues.append(Issue(
            path, line_number(text, p6),
            "フェーズ6の部分クラス図に、その判断では対象外として省いた範囲を書いてください",
        ))
    concept_end = section.find("### 構想をコードでつなぐ")
    concept = section[:concept_end] if concept_end >= 0 else section
    if not (
        "**構想上のコード経路：**" in concept
        or "起動時：main()" in concept
    ):
        issues.append(Issue(
            path, line_number(text, p6),
            "フェーズ6の冒頭に、主要なクラス名と処理名を含む構想上のコード経路がありません",
        ))
    return issues


def check_observed_problem_only(text: str, path: Path) -> list[Issue]:
    """問題IDの行へ、試していない変更の「見込み」を書かない。

    2026-08-13に見つかった症状。第6章のフェーズ3は変更ID1（Matcha・Choco追加）
    しか当てておらず、変更ID2の入力順と変更ID3の販売可否は試していないのに、
    問題ID3として
    `販売停止・表示順を足すと…（変更ID1の試行から見込まれる痛み）`
    と表へ載せていた。問題IDの列見出しは「観測した痛み」であり、
    見込みを観測として記録すると、後続の原因ID・課題IDが実測でない前提の上に積む。

    3-1のコードは 1-4 / 7-1 と違って audit_book.py の実行検査対象ではないため、
    「コードが無いのに痛みだけ書いてある」状態を機械では検出できていなかった。
    ここでは推量の語だけを見る。痛みが未観測なら、表へ載せる前に実際に当てる。

    初版の語彙に「予見され」が無く、第2章の問題ID2と第10章の問題ID3にあった
    「（変更ID1・ID2の試行から予見される痛み）」を素通りさせた。同じ書き方の
    ゆれを取りこぼさないよう、語を足すときは全章へ試走して誤検出を確かめる。
    """
    issues: list[Issue] = []
    guess = re.compile(
        r"見込ま|想定され|予想され|予見され|見込み|と思われ|だろう|かもしれ"
    )
    for m in re.finditer(r"(?m)^\|\s*問題ID\d+\s*\|.*$", text):
        row = m.group(0)
        g = guess.search(row)
        if g:
            issues.append(Issue(
                path, line_number(text, m.start()),
                f"問題IDの行に推量の語「{g.group(0)}」があります。問題IDは"
                "観測した痛みだけを書く欄なので、実際に変更を当ててから記録して"
                "ください",
            ))
    return issues


def check_scenario_label_literal(text: str, path: Path) -> list[Issue]:
    """動作例の行ラベルは、変数から組み立てず文字列リテラルで出す。

    2026-08-13に見つかった症状。第6章の1-4が
    `void showOrder(MenuDatabase& db, int row, ...)` として行番号を引数で受け、
    `cout << "--- 行" << row << " ---"` と組み立てていた。呼び出し側は
    「モバイルアプリを想定」と書かれているのに、動作例テーブルの何行目かを
    渡さないと呼べない。行番号はどの要求IDにも無い執筆上の目印であり、
    それを業務コードの入力へ混ぜていた。

    check_unused_cpp_inputs.py は「使われない引数」を見るが、この row は
    表示に使われていたため素通りした。ここでは行ラベルを変数から作る書き方を
    禁じる。ラベルは main() 側のリテラルで出せば、呼び出し規約を汚さない。
    """
    issues: list[Issue] = []
    pattern = re.compile(r'"-{2,}\s*行"\s*<<|<<\s*"\s*行"\s*<<')
    for block in re.finditer(r"```cpp\s*\n(.*?)```", text, re.S):
        m = pattern.search(block.group(1))
        if m:
            issues.append(Issue(
                path, line_number(text, block.start(1) + m.start()),
                "動作例の行ラベルを変数から組み立てないでください。行番号は"
                "要求ではなく執筆上の目印なので、呼び出し側へ渡させず "
                "main() のリテラルで出します",
            ))
    return issues


def check_ignored_verification_results(text: str, path: Path) -> list[Issue]:
    """成否を返す既知の検証・照会呼び出しが単独文で捨てられていないか。"""
    issues: list[Issue] = []
    call_pattern = re.compile(
        r"(?m)^\s*[A-Za-z_]\w*\s*(?:\.|->)\s*"
        r"(?:verifyOTP|verifyAccount|checkBalance)\s*\([^;\n]*\)\s*;"
        r"\s*(?://.*)?$"
    )
    for block in re.finditer(r"```cpp\s*\n(.*?)```", text, re.DOTALL):
        for call in call_pattern.finditer(block.group(1)):
            issues.append(Issue(
                path,
                line_number(text, block.start(1) + call.start()),
                "検証・照会メソッドの戻り値を捨てず、判定・保存・返却に使ってください",
            ))
    return issues


def check_long_text_blocks(text: str, path: Path) -> list[Issue]:
    """Kindleで追いにくい長大な実行結果・整形済みテキストを禁止する。"""
    issues: list[Issue] = []
    # 実行結果は言語指定なしのフェンスも使うため、textだけに限定しない。
    # cpp/mermaid等のソースブロックは対象外。
    for block in re.finditer(r"```([^\n`]*)\n(.*?)```", text, re.DOTALL):
        language = block.group(1).strip()
        if language not in ("", "text"):
            continue
        line_count = len(block.group(2).splitlines())
        if line_count >= 25:
            issues.append(Issue(
                path,
                line_number(text, block.start()),
                f"textブロックが{line_count}行あります。ケース単位に分け、各コードの直後へ対応結果を置いてください",
            ))
    return issues


def check_run_locally_section(text: str, path: Path) -> list[Issue]:
    """全パターン章に「手元で動かすには」を1回だけ置く。

    2026-08-14に見つかった症状。12章中10章にあり、第8章と第11章だけ欠けていた。
    第11章は成果物ファイルを実際に書き出す章、第8章は非同期の完了確認がある章で、
    むしろ手元で動かす説明が要る側だった。

    節の中身が正しいかまでは機械で見られない（第4章は「保存件数が1件減る」、
    第10章は「DBへ足せばその連携先でも実行できる」と、実際には起きないことを
    書いていた）。ここでは有無だけを見る。中身は rules/checklist.md の観点で
    「勧める操作を実際に実行して確かめたか」を人が確認する。
    """
    heading = "> **手元で動かすには**"
    count = text.count(heading)
    if count != 1:
        return [Issue(
            path, 1,
            f"1-4の掲載コードと実行結果の後へ `{heading}` を1回だけ置いてください"
            f"（現在{count}回）。読者が貼り付けて動かす手順と、その章で"
            "実際に確認できる結果を書きます",
        )]
    file_note = "> **掲載用1ファイルと実務の分割：**"
    if text.count(file_note) != 1:
        return [Issue(
            path, line_number(text, text.find(heading)),
            "「手元で動かすには」に、掲載用の1つの.cppと実務の"
            ".h／.cpp／main.cpp分割を区別する共通注記を置いてください",
        )]
    return []


def check_chapter0_file_layout_guidance(text: str, path: Path) -> list[Issue]:
    """第0章で読解用ブロックと実務ファイル配置を分けて説明する。"""
    if path.name != "chapter00_2.md":
        return []
    tokens = (
        "### 掲載ブロックと実ファイルの分け方",
        "1つだけ置きます",
        "IDiscountRule.h",
        "PremiumDiscount.cpp",
        "`main.cpp`",
        "1掲載ブロック＝1ファイルではなく",
    )
    missing = [token for token in tokens if token not in text]
    if not missing:
        return []
    return [Issue(
        path, 1,
        "第0章の掲載ブロック／実ファイル分割説明が不足しています: "
        + ", ".join(missing),
    )]


def check_standard_simplification_section(text: str, path: Path) -> list[Issue]:
    """全パターン章で簡略化境界を1-3と1-4の間へ一度だけ置く。"""
    heading = "**この章での簡略化**"
    count = text.count(heading)
    if count != 1:
        return [Issue(
            path, 1,
            f"簡略化節は全章共通見出し `{heading}` で1回だけ置いてください（現在{count}回）",
        )]
    s13 = text.find("### 1-3：")
    simple = text.find(heading)
    s14 = text.find("### 1-4：", simple)
    issues: list[Issue] = []
    if min(s13, simple, s14) < 0 or not (s13 < simple < s14):
        issues.append(Issue(
            path, line_number(text, simple if simple >= 0 else 0),
            "簡略化節は1-3の後、1-4の前へ置いてください",
        ))
        return issues
    opening = text[simple + len(heading):simple + len(heading) + 240]
    if re.search(r"1-3で.*(?:確認|整理)|現状コードへ進", opening):
        issues.append(Issue(
            path, line_number(text, simple),
            "簡略化節を章構成のメタ説明から始めず、実行すること・代替すること・扱わないことを直接説明してください",
        ))
    return issues


def check_core_thesis(text: str, path: Path) -> list[Issue]:
    """「この章の核心」は題材名でなく、思考の型の判断軸を説明する。"""
    start = text.find("### この章の核心")
    if start < 0:
        return [Issue(path, 1, "「この章の核心」見出しがありません")]
    end = text.find("### ", start + len("### この章の核心"))
    section = text[start:end if end >= 0 else start + 1200]
    issues: list[Issue] = []
    for token in ("場面では", "兆候", "判断軸"):
        if token not in section:
            issues.append(Issue(
                path, line_number(text, start),
                f"この章の核心に思考の型を示す「{token}」がありません",
            ))
    return issues


# フェーズ6の断片コードは、直前の1行で出どころまたは確認対象を宣言する。
# 散文へ織り込むだけだと、読者はブロックを見た時点で所属が分からず、
# 前の段落まで戻って探すことになる（著者指摘 AF-20260814-150）。
FRAGMENT_LOCATION = re.compile(
    r"^\*\*(?:変更前から抜き出す箇所|ここで確認するコード|比較用コード)：.*?"
    r"`(?:[A-Za-z_]\w*(?:::[A-Za-z_]\w*)?|main)(?:\s*\(|`)", re.M)
# 型宣言そのものを載せるブロックと、`void Class::method(...)` のクラス外定義は、
# コード自身が掲載箇所を宣言しているのでラベルを求めない。
TYPE_DECLARATION_HEAD = re.compile(r"\s*(?:class|struct|enum|namespace)\s")
QUALIFIED_DEFINITION_HEAD = re.compile(r"\s*[\w:<>&\*\s]+?\b[A-Z]\w*::\w+\s*\(")


def check_phase6_fragment_location(text: str, path: Path) -> list[Issue]:
    """フェーズ6の断片コードへ、出どころ／確認対象ラベルがあるかを見る。"""
    body_text = text.replace("\r\n", "\n")
    marks = _phase_marks(body_text)
    issues: list[Issue] = []
    for match in re.finditer(r"```cpp\n(.*?)```", body_text, re.S):
        if _phase_at(marks, match.start()) != "6":
            continue
        before = body_text[:match.start()].rstrip("\n")
        last_line = before.split("\n")[-1] if before else ""
        if not FRAGMENT_LOCATION.match(last_line.strip()):
            issues.append(Issue(
                path, line_number(body_text, match.start()),
                "フェーズ6の断片コードの直前へ、既存コードなら"
                "`**変更前から抜き出す箇所：**`、新しく決めたコードなら"
                "`**ここで確認するコード：**`を書き、対象メソッドを示してください。"
                "散文へ織り込むだけでは、読者がブロックを見た時点で"
                "どのクラスのどの関数かを判断できません",
            ))
            continue

        # タイトルへ複数の型名を書きながら、実際のブロックが1型だけという
        # 旧形式を防ぐ。引数型などは全角括弧より後ろへ書く規約なので、
        # タイトルの主語部分だけを比較する。
        top_type = re.search(
            r"(?m)^(?:class|struct|enum(?:\s+class)?)\s+([A-Za-z_]\w*)",
            match.group(1),
        )
        if top_type:
            title_subject = re.split(r"（|――", last_line, maxsplit=1)[0]
            title_types = re.findall(r"`([A-Za-z_]\w*)`", title_subject)
            if title_types != [top_type.group(1)]:
                issues.append(Issue(
                    path, line_number(body_text, match.start()),
                    "フェーズ6のコードブロック名と実際の型が一致しません。"
                    f"タイトル={title_types or ['なし']}、コード={top_type.group(1)}。"
                    "1ブロックのタイトルには、そのブロックで定義する1型だけを書いてください",
                ))
    return issues


# フェーズ6は、全体構想を先に置き、その同じ経路を要点コードで確かめる。
PHASE6_DECISION_HEADINGS = (
    "### 構想を決める",
    "### 構想をコードでつなぐ",
    "### 構想を採用する",
)
PHASE6_EXACT_HEADING = "## 🔴 フェーズ6：対策検討 ―― 構想を一つのコード経路へ変える"
LEGACY_PHASE6_TOKENS = (
    "## 🔴 フェーズ6：対策検討 ―― 全体のデータと実体の流れを決める",
    "#### 全体経路を組み立てる判断",
    "### 全体のデータと実体の流れを先に決める",
    "### 全体の流れを実現するコードを決める",
    "#### 1. 契約と具体をセットで決める（分離）",
    "#### 2. 全体経路をコードで組み立てる",
    "#### システム全体の最終構造を決める",
    "### 6-1：決めた流れとコードの照合",
    "| 実行順・ポイント | 担う場所 |",
    "**掲載箇所：",
    "## 🔴 フェーズ6：対策検討 ―― 分離と組み立てを決める",
    "### 6-1：分離と組み立てのまとめ",
    "#### 代表ケースの実行接続",
    "#### 2. 生成・注入・実行をセットで決める（組み立て）",
    "生成の検討",
    "注入の確認",
    "**ここから決めること：**",
    "**出発点。**",
    "**ここでコードとして確定すること：**",
    "6段で解く",
    "### 6-1：生成・所有・実行順のまとめ",
    "【安定骨格】",
    "【利用開始】",
    "| 型 | 骨格の正体 | 契約の置き場 | 見分け方 |",
    "| 形 | 実装が決まる決め手 | 入る瞬間 | この本での例 |",
    "#### システム全体のコード適用結果",
    "**システム全体の実装結果：達成。**",
    "**どう解決するか（方針）：**",
)


def check_phase6_exact_heading(text: str, path: Path) -> list[Issue]:
    """フェーズ6がある原稿では、0章・本文とも同じ見出しを使う。"""
    headings = re.findall(r"(?m)^## 🔴 フェーズ6：[^\n]+$", text)
    if not headings:
        return []
    if headings == [PHASE6_EXACT_HEADING]:
        return []
    return [Issue(
        path,
        line_number(text, text.find(headings[0])),
        "フェーズ6の見出しを第0章・テンプレート・全章で"
        "「対策検討 ―― 構想を一つのコード経路へ変える」へ統一してください",
    )]


NON_CANONICAL_STRUCTURE_NAMES = (
    "規則差し替え構造",
    "窓口集約構造",
    "操作の部品化構造",
    "骨格・ステップ分離",
    "分離・配置・組み立て",
    "分離・配置・生成・所有・注入・実行",
)


def check_structure_name_consistency(text: str, path: Path) -> list[Issue]:
    """導出時・要約・0章で日本語の構造名が途中で変わるのを防ぐ。"""
    issues: list[Issue] = []
    for token in NON_CANONICAL_STRUCTURE_NAMES:
        for match in re.finditer(re.escape(token), text):
            issues.append(Issue(
                path,
                line_number(text, match.start()),
                f"設計用語が0章・テンプレート・章内で一致しません: {token}",
            ))
    return issues


def check_phase6_point_separation(text: str, path: Path) -> list[Issue]:
    """フェーズ6が構想→連続した要点コード→採用の順か確認する。"""
    issues: list[Issue] = []
    start = text.find("## 🔴 フェーズ6：")
    end = text.find("## 🟢 フェーズ7：", start)
    if min(start, end) < 0:
        return issues
    section = text[start:end]

    for heading in PHASE6_DECISION_HEADINGS:
        count = section.count(heading)
        if count != 1:
            issues.append(Issue(
                path, line_number(text, start),
                f"フェーズ6の大判断見出しは1回だけ置いてください: {heading}（現在{count}回）",
            ))

    positions = [section.find(heading) for heading in PHASE6_DECISION_HEADINGS]
    if min(positions) < 0 or positions != sorted(positions):
        issues.append(Issue(
            path, line_number(text, start),
            "フェーズ6は「構想を決める→構想をコードでつなぐ→構想を採用する」の順にしてください",
        ))

    code_start = section.find(PHASE6_DECISION_HEADINGS[1])
    adoption_start = section.find(PHASE6_DECISION_HEADINGS[2])
    code_section = (
        section[code_start:adoption_start]
        if 0 <= code_start < adoption_start else ""
    )
    if "> **コードの読み方：**" not in code_section:
        issues.append(Issue(
            path, line_number(text, start + max(code_start, 0)),
            "構想の要点コードの前に、変更前抜粋と新規コードの読み分けを示してください",
        ))
    code_steps = (
        "#### 契約：",
        "#### 具体：",
        "#### 生成・所有・受け渡しを決める",
        "#### 実行骨格：組み立てた実体を契約から呼ぶ",
        "#### 公開入口から具体の実行まで追う",
    )
    step_positions = [code_section.find(step) for step in code_steps]
    if min(step_positions) < 0 or step_positions != sorted(step_positions):
        issues.append(Issue(
            path, line_number(text, start + max(code_start, 0)),
            "構想の要点コードは、契約→具体→生成・所有・受け渡し→実行骨格→公開入口からの実行の順に続けてください",
        ))

    concept = section[:code_start] if code_start >= 0 else ""
    for row in (
        "| 契約と具体 |",
        "| 生成・所有・受け渡し |",
        "| 公開入口からの実行 |",
    ):
        if concept.count(row) != 1:
            issues.append(Issue(
                path, line_number(text, start),
                f"構想の対応表に {row} を1行だけ置いてください",
            ))
    if not ("**構想上のコード経路：**" in concept or "起動時：main()" in concept):
        issues.append(Issue(
            path, line_number(text, start),
            "要点コードへ入る前に、主要な名前を含む構想上のコード経路を示してください",
        ))

    adoption = section[adoption_start:] if adoption_start >= 0 else ""
    for heading in (
        "#### 課題から採用構想までを照合する",
        "#### 将来リスクに対して構想を確認する",
    ):
        if adoption.count(heading) != 1:
            issues.append(Issue(
                path, line_number(text, start + max(adoption_start, 0)),
                f"構想の採用判断に見出しがありません: {heading}",
            ))
    # 判断対象だけの部分クラス図はここに置ける。
    # 完成図の先出しと部分図の範囲明記は
    # check_phase6_overview_diagram で検査する。
    for legacy in (
        "【安定骨格】",
        "【利用開始】",
        "#### システム全体のコード適用結果",
        "**システム全体の実装結果：達成。**",
        "**どう解決するか（方針）：**",
        "| 形 | 実装が決まる決め手 | 入る瞬間 | この本での例 |",
        "| 型 | 骨格の正体 | 契約の置き場 | 見分け方 |",
    ):
        if legacy in section:
            issues.append(Issue(
                path, line_number(text, start + section.find(legacy)),
                f"フェーズ6に廃止した分割・重複説明が残っています: {legacy}",
            ))
    return issues



def check_chapter01_rule_lifecycle_terms(text: str, path: Path) -> list[Issue]:
    """第1章でルールの生成・登録・選択・注入を混同していないか確認する。"""
    if path.name != "chapter01.md":
        return []
    start = text.find("## 🔴 フェーズ6：")
    end = text.find("## 🟢 フェーズ7：", start)
    if min(start, end) < 0:
        return []
    section = text[start:end]
    required = (
        "`DiscountRuleSet discountRules;`がルール集合を**生成**し、5つの具体ルールはそのメンバーとして同時に生成・所有されます。",
        "`DiscountRuleSet`の`ruleSelector.add(...)`が、生成済み実体への参照の**優先順登録**を表します。",
        "`main()`は個々のルール名や登録順を扱わず、完成したルール集合を利用側へ接続します。",
        "`selector.select()`が、生成・登録済みのルールから1つを**選択**する。",
        "`select()`自身は注入ではありません。",
        "`PaymentCalculator calculator(rule)`がCalculatorを生成し、同時に選択済みルールへの参照を**注入**する。",
    )
    issues: list[Issue] = []
    for statement in required:
        if statement not in section:
            issues.append(Issue(
                path, line_number(text, start),
                "第1章ではルールの生成・登録・選択とCalculatorへの注入を別の操作として明記してください: "
                + statement,
            ))
    main_label = "**ここで確認するコード：`main()`**"
    main_at = section.find(main_label)
    if main_at >= 0:
        fence_at = section.find("```cpp", main_at)
        fence_end = section.find("```", fence_at + len("```cpp"))
        if min(fence_at, fence_end) >= 0:
            main_block = section[fence_at:fence_end]
            concrete_names = (
                "PremiumDiscount", "SummerSaleAndCampaignDiscount",
                "SummerSaleDiscount", "CampaignDiscount", "NoDiscount",
            )
            if ".add(" in main_block or any(name in main_block for name in concrete_names):
                issues.append(Issue(
                    path, line_number(text, start + main_at),
                    "第1章のmain()へ具体ルール名や登録順を置かず、DiscountRuleSetへ閉じてください",
                ))
    return issues


def check_phase6_numbered_step_titles(text: str, path: Path) -> list[Issue]:
    """番号だけの旧段階見出しと、課題別H3への再分解を禁止する。"""
    start = text.find("## 🔴 フェーズ6：")
    end = text.find("## 🟢 フェーズ7：", start)
    if min(start, end) < 0:
        return []
    section = text[start:end]
    issues: list[Issue] = []
    for pattern, message in (
        (r"(?m)^### 課題ID\d+：", "課題別H3へ分けず、全課題を一つのH3で扱ってください"),
        (r"(?m)^#### 実装ステップ\d+", "旧実装ステップ形式を使わないでください"),
        (r"(?m)^\*\*\d+\.[^\n]*【(?:契約|安定骨格|具体|生成|注入|利用開始)】",
         "六段の番号付き見出しへ戻さないでください"),
    ):
        match = re.search(pattern, section)
        if match:
            issues.append(Issue(
                path, line_number(text, start + match.start()), message,
            ))
    return issues


def check_stable_skeleton_explanation(text: str, path: Path) -> list[Issue]:
    """フェーズ6で安定する制御骨格を「なし」と扱わない。

    骨格はTemplate Methodの基底アルゴリズムだけではない。Strategyの選択・
    委譲、Observerの登録・反復、Commandの履歴移動など、具体実装が増減しても
    維持する利用側の制御を、冒頭構想と要点コードで説明する。
    """
    start = text.find("## 🔴 フェーズ6：")
    end = text.find("## 🟢 フェーズ7：", start)
    if min(start, end) < 0:
        return []
    section = text[start:end]
    match = re.search(
        r"骨格(?:は|も)?(?:無し|なし)|骨格を持たない", section
    )
    if not match:
        return []
    return [Issue(
        path, line_number(text, start + match.start()),
        "フェーズ6の構想と要点コードで、具体実装が変わっても維持する選択・委譲・反復・履歴移動などの骨格を示してください",
    )]


def check_responsibility_table_scope(text: str, path: Path) -> list[Issue]:
    """1-4へクラス責任表を置かない（著者判断 2026-08-30）。

    1-3が「クラス名・役割・担当する仕様」の一覧とクラス図を持つ。1-4へ
    同じ責任を数行へ縮めた表を置くと、1-3の部分集合を粒度違いで再掲する
    だけになり、章によって対象がクラス名・メンバー変数・処理名へばらつく。
    1-4はコードと、そのコードを読むのに要る実データ表だけを置く。
    """
    s14 = text.find("### 1-4：")
    if s14 < 0:
        return []
    end = text.find("### 1-5：", s14)
    if end < 0:
        end = text.find("## 🟣", s14)
    section = text[s14:end if end > 0 else len(text)]
    issues: list[Issue] = []
    for banned, why in (
            ("#### コードを読む前に：クラスの責任と境界",
             "1-3のクラス一覧とクラス図が同じ情報を持つ"),
            ("#### このシステムの登場クラス",
             "1-3のクラス一覧の再掲になる")):
        if banned in section:
            issues.append(Issue(
                path, line_number(text, s14 + section.find(banned)),
                f"1-4へクラス責任表（`{banned.removeprefix('#### ')}`）を"
                f"置かないでください：{why}。1-4はコードと、"
                "そのコードを読むのに要る実データ表だけを置きます",
            ))
    return issues


# --- DOC-001：掲載コードの所属・分割・省略 ------------------------------
# コードの所属、省略、長さはフェーズ3・4・6・7で確認する。トップレベルの
# 型数と意味段階の空行は、現状コードを含む全C++ブロックへ適用する。
BLOCK_MAX_LINES = 80
BLOCK_MAX_TYPES = 2

_TOP_LEVEL_TYPE_DEFINITION = re.compile(
    r"(?m)^(?:class|struct|enum\s+class)\s+([A-Za-z_]\w*)[^\n{;]*\{"
)
_ONE_LINE_GUARD = re.compile(
    r"^if\s*\(.*\)\s*(?:return|continue|break)\b.*;$"
)
_CONTROL_START = re.compile(r"^(?:if|for|while|switch)\s*\(")

# 判定前に文字列リテラルを落とす。`"再試行します..."` は省略ではない。
_STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\])*"')
# 散文の「…」や `{ /* メール送信 */ }` のような一言説明は対象外。コードが
# 抜けていると分かる形だけを見る。判定を広げるときは実物を確認してから。
_CODE_ELLIPSIS = re.compile(
    r"中略"
    r"|\{\s*/\*\s*(?:\.\.\.|…|省略)\s*\*/\s*\}"
    r"|^\s*(?://\s*)?(?:\.\.\.|…)[^\n]{0,12}$",
    re.M,
)
# 所属の手がかり。`Class::method`、`ClassName`、main()、行頭のclass/struct。
_OWNER_HINT = re.compile(
    r"`[A-Z]\w*::\w+|`[A-Z]\w*`|\bmain\s*\("
    r"|^\s*(?:class|struct|enum)\s+\w+"
    r"|^\s*enum\s+class\s+\w+"
    # `void TicketService::create(...)` のクラス外定義と、桁位置0から
    # 始まる自由関数の宣言・定義は、コード自身が正体を明かしている。
    # 断片は必ず字下げされているので、桁位置0かどうかで区別できる。
    r"|^[\w:<>&*\s]*?\b[A-Z]\w*::[\w~]+\s*\("
    r"|^[A-Za-z_][\w:<>&*]*\s+[\w~]+\s*\([^;{]*\)\s*[{;]",
    re.M,
)
_ATTRIBUTION_PHASES = {"3", "4", "6", "7"}


def _phase_marks(text: str) -> list[tuple[int, str]]:
    return [
        (m.start(), m.group(1))
        for m in re.finditer(r"^## [^\n]*フェーズ(\d)", text, re.M)
    ]


def _phase_at(marks: list[tuple[int, str]], pos: int) -> str:
    current = "1"
    for offset, phase in marks:
        if offset < pos:
            current = phase
    return current


def _preceding_prose(text: str, pos: int) -> str:
    """直前のコードフェンス以降の説明文を返す。

    見出しと太字ラベルだけでなく、引用（`> **抜粋の前提**`）や箇条書きも
    所属の手がかりになるので、直前の ``` 以降を丸ごと見る。
    """
    window = text[max(0, pos - 1200):pos]
    last_fence = window.rfind("```")
    if last_fence >= 0:
        window = window[last_fence + 3:]
    return window


def check_code_block_attribution(text: str, path: Path) -> list[Issue]:
    """断片コードの所属明示・ブロック分割・省略記号を確認する（DOC-001）。"""
    body_text = text.replace("\r\n", "\n")
    body_text = re.sub(r"(?m)^> ?", "", body_text)
    marks = _phase_marks(body_text)
    issues: list[Issue] = []
    for match in re.finditer(r"```cpp\n(.*?)```", body_text, re.S):
        body = match.group(1)
        pos = match.start()
        if _phase_at(marks, pos) not in _ATTRIBUTION_PHASES:
            continue
        line = line_number(body_text, pos)
        lines = [ln for ln in body.split("\n") if ln.strip()]
        types = len(_TOP_LEVEL_TYPE_DEFINITION.findall(body))
        prose = _preceding_prose(body_text, pos)
        if not _OWNER_HINT.search(prose + "\n" + body[:300]):
            issues.append(Issue(
                path, line,
                "断片コードの直前に所属を書いてください。どのクラスのどの関数の"
                "どの部分かを `Class::method()` または `main()` の形で示します",
            ))
        if len(lines) > BLOCK_MAX_LINES:
            issues.append(Issue(
                path, line,
                f"C++ブロックが実質{len(lines)}行あります（上限"
                f"{BLOCK_MAX_LINES}）。型・メンバー／公開操作／内部判定などの"
                "切れ目で分割してください（連結すれば同じ1本のコードです）",
            ))
        if types >= BLOCK_MAX_TYPES:
            issues.append(Issue(
                path, line,
                f"1ブロックへ{types}型あります（上限{BLOCK_MAX_TYPES - 1}）。"
                "短い兄弟型も含め、トップレベルの型は1ブロックに1つだけ置いてください",
            ))
        if _CODE_ELLIPSIS.search(_STRING_LITERAL.sub('""', body)):
            issues.append(Issue(
                path, line,
                "コード内の省略で分岐・接続・責任が隠れています。"
                "実コードへ戻すか、省略範囲と掲載先を本文へ書いてください",
            ))
    return issues


def check_cpp_semantic_spacing(text: str, path: Path) -> list[Issue]:
    """判定・実行・保存・返却の切り替わりを空行で読めるようにする。"""
    body_text = text.replace("\r\n", "\n")
    body_text = re.sub(r"(?m)^> ?", "", body_text)
    issues: list[Issue] = []
    for match in re.finditer(r"```cpp\n(.*?)```", body_text, re.S):
        lines = match.group(1).split("\n")
        for index in range(len(lines) - 1):
            line = lines[index]
            following_line = lines[index + 1]
            if not line.strip() or not following_line.strip():
                continue

            current = line.strip()
            following = following_line.strip()
            same_indent = (
                len(line) - len(line.lstrip(" "))
                == len(following_line) - len(following_line.lstrip(" "))
            )
            if not same_indent:
                continue

            missing = False
            if current == "}" and not following.startswith((
                "else", "catch", "while", "case ", "default:", "}", ");", ";"
            )):
                missing = True
            elif _ONE_LINE_GUARD.match(current) and not _ONE_LINE_GUARD.match(following):
                missing = True
            elif (
                current.endswith(";")
                and _CONTROL_START.match(following)
                and not current.startswith(("if ", "for ", "while "))
            ):
                missing = True
            elif (
                following.startswith("return ")
                and current not in {"{", "}"}
                and not current.startswith(("if ", "else", "return ", "//"))
            ):
                missing = True

            if missing:
                issues.append(Issue(
                    path,
                    line_number(body_text, match.start()) + index + 1,
                    "処理の意味が切り替わる箇所に空行がありません。"
                    "入力・取得、判定、選択・計算、保存、通知・返却の境目を1行空けてください",
                ))
                break
    return issues


def check_one_top_level_type_per_block(text: str, path: Path) -> list[Issue]:
    """現状コードを含むすべてのC++ブロックで1型1ブロックを守る。"""
    body_text = text.replace("\r\n", "\n")
    body_text = re.sub(r"(?m)^> ?", "", body_text)
    issues: list[Issue] = []
    for match in re.finditer(r"```cpp\n(.*?)```", body_text, re.S):
        types = _TOP_LEVEL_TYPE_DEFINITION.findall(match.group(1))
        if len(types) <= 1:
            continue
        issues.append(Issue(
            path,
            line_number(body_text, match.start()),
            "1つのC++ブロックに複数のトップレベル型があります: "
            + ", ".join(types)
            + "。短くても1型ずつ別ブロックへ分けてください",
        ))
    return issues


def check_long_final_cpp_blocks(text: str, path: Path) -> list[Issue]:
    """7-1の長い複数責任コードを、再結合可能な責任単位へ分割する。"""
    start = text.find("### 7-1：")
    end = text.find("### 7-2：", start)
    if min(start, end) < 0:
        return []
    issues: list[Issue] = []
    section = text[start:end]
    for block in re.finditer(r"```cpp\s*\n(.*?)```", section, re.S):
        code = block.group(1)
        lines = len(code.splitlines())
        types = _TOP_LEVEL_TYPE_DEFINITION.findall(code)
        if lines > 120 and len(types) > 1:
            issues.append(Issue(
                path, line_number(text, start + block.start()),
                f"7-1のC++ブロックが{lines}行・{len(types)}型あります。責任・クラス単位へ分割してください",
            ))
    return issues


def check_executed_test_helpers(text: str, path: Path) -> list[Issue]:
    """7-1に掲載したテスト関数を未呼び出しのまま残さない。"""
    start = text.find("### 7-1：")
    end = text.find("### 7-2：", start)
    if min(start, end) < 0:
        return []
    section = text[start:end]
    code = "\n".join(re.findall(r"```cpp\s*\n(.*?)```", section, re.S))
    issues: list[Issue] = []
    names = set(re.findall(
        r"\b(?:void|bool|int)\s+((?:test\w*|run\w*Tests?))\s*\(",
        code, re.I,
    ))
    for name in names:
        # 宣言・定義の行を除いた「呼び出し」だけを数える。宣言と定義を
        # 分けると出現が2回になるため、単純な出現数では検出できない。
        calls = [
            line for line in code.split("\n")
            if re.search(rf"\b{re.escape(name)}\s*\(", line)
            and not re.search(
                rf"\b(?:void|bool|int)\s+(?:\w+::)?{re.escape(name)}\s*\(",
                line)
        ]
        if not calls:
            issues.append(Issue(
                path, line_number(text, start),
                f"7-1のテスト関数 `{name}()` が実行経路から呼ばれていません",
            ))
    return issues


def check_class_diagram_glossary(text: str, path: Path) -> list[Issue]:
    """第0章に、実例図と見た目・意味・使い分けの説明を固定する。"""
    if path.name != "chapter00_2.md":
        return []
    start = text.find("### クラス図の読み方（全章共通の規約）")
    end = text.find("対策検討では", start)
    section = text[start:end] if 0 <= start < end else ""
    required = (
        "ShippingFeeRule <|-- ExpressShippingFeeRule",
        "IDiscountRule <|.. MemberDiscountRule",
        'Order "1" *-- "0..*" OrderLine',
        'DiscountCatalog "1" o-- "0..*" IDiscountRule',
        'CheckoutService "0..*" --> "1" IDiscountRule',
        'Order "0..*" --> "1" Customer',
        "CheckoutService ..> PaymentResult",
        "<<abstract>>",
        "<<interface>>",
        "インターフェースはC++では抽象クラスの一種",
        "ステレオタイプなし",
        "型名が`I`で始まるかどうかでは決めません",
        "`+` / `-`",
        "`名前: 型`",
        "線の両端にある`1`はちょうど1個、`0..*`は0個以上",
        "実線＋白抜き三角",
        "点線＋白抜き三角",
        "実線＋黒ひし形",
        "実線＋白ひし形",
        "単にポインタや参照を保持して破棄しないだけなら、白ひし形とは限らず",
        "この線を使う場面",
    )
    missing = [token for token in required if token not in section]
    if not missing:
        return []
    return [Issue(
        path, 1,
        "第0章のクラス図実例または使い分け説明が不足しています: "
        + ", ".join(missing),
    )]


_CLASS_DIAGRAM_RE = re.compile(
    r"```mermaid\s*\nclassDiagram\b(.*?)```", re.S
)
_MERMAID_CLASS_RE = re.compile(
    r"\bclass\s+([A-Za-z_]\w*)\s*\{(.*?)\}", re.S
)
_CPP_CLASS_START_RE = re.compile(
    r"\bclass\s+([A-Za-z_]\w*)\b[^;{]*\{"
)


def _cpp_class_bodies(text: str) -> dict[str, list[str]]:
    """本文のC++ブロックから、クラスごとの波括弧内を取り出す。"""
    body_text = re.sub(r"(?m)^> ?", "", text.replace("\r\n", "\n"))
    result: dict[str, list[str]] = {}
    for block in re.finditer(r"```cpp\s*\n(.*?)```", body_text, re.S):
        code = block.group(1)
        for start in _CPP_CLASS_START_RE.finditer(code):
            depth = 1
            index = start.end()
            while index < len(code) and depth:
                if code[index] == "{":
                    depth += 1
                elif code[index] == "}":
                    depth -= 1
                index += 1
            if depth == 0:
                result.setdefault(start.group(1), []).append(
                    code[start.end():index - 1]
                )
    return result


def check_qualified_method_references(text: str, path: Path) -> list[Issue]:
    """本文の `Class::method()` が掲載コードの実在メソッドを指すか確認する。"""
    if path.name == "chapter00_2.md":
        # 第0章後半は各章の実例名を参照するため、このファイル単体では照合しない。
        return []

    body_text = re.sub(r"(?m)^> ?", "", text.replace("\r\n", "\n"))
    cpp = "\n".join(extract_cpp_blocks(body_text))
    class_bodies = _cpp_class_bodies(body_text)
    bases: dict[str, str] = {}
    for match in re.finditer(
        r"\bclass\s+([A-Za-z_]\w*)\s*"
        r"(?:\:\s*public\s+([A-Za-z_]\w*))?[^;{]*\{",
        cpp,
    ):
        if match.group(2):
            bases[match.group(1)] = match.group(2)

    def declares(class_name: str, method_name: str, seen: set[str]) -> bool:
        if class_name in seen:
            return False
        seen.add(class_name)
        if any(
            re.search(rf"\b{re.escape(method_name)}\s*\(", body)
            for body in class_bodies.get(class_name, [])
        ):
            return True
        if re.search(
            rf"\b{re.escape(class_name)}::{re.escape(method_name)}\s*\(", cpp
        ):
            return True
        base = bases.get(class_name)
        if base and declares(base, method_name, seen):
            return True
        # 完成コードは、長い1クラスを責任単位の複数ブロックへ分けることがある。
        # その場合はクラスの波括弧が1ブロック内で閉じず、所属解析ができないため、
        # 同じ章のC++に同名メソッドの定義が実在することまでを最低条件にする。
        return bool(re.search(rf"\b{re.escape(method_name)}\s*\(", cpp))

    issues: list[Issue] = []
    reported: set[tuple[str, str]] = set()
    for match in re.finditer(
        r"`([A-Z][A-Za-z0-9_]*)::([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        body_text,
    ):
        class_name, method_name = match.group(1), match.group(2)
        key = (class_name, method_name)
        if key in reported or class_name not in class_bodies:
            continue
        if declares(class_name, method_name, set()):
            continue
        reported.add(key)
        issues.append(Issue(
            path,
            line_number(body_text, match.start()),
            f"本文の `{class_name}::{method_name}()` は掲載コードの"
            "クラス宣言・基底クラス・クラス外定義のいずれにも存在しません。"
            "コードブロック名や説明に古いメソッド名が残っていないか確認してください",
        ))
    return issues


def check_class_diagram_type_semantics(text: str, path: Path) -> list[Issue]:
    """ステレオタイプ、白三角の線種、C++基底型の中身を照合する。"""
    issues: list[Issue] = []
    class_bodies = _cpp_class_bodies(text)
    stereotypes: dict[str, set[str]] = {}
    reported: set[tuple[str, str]] = set()

    for diagram_match in _CLASS_DIAGRAM_RE.finditer(text):
        diagram = diagram_match.group(1)
        diagram_types: dict[str, str] = {}
        for class_match in _MERMAID_CLASS_RE.finditer(diagram):
            stereotype = re.search(
                r"<<(interface|abstract)>>", class_match.group(2)
            )
            if stereotype:
                name = class_match.group(1)
                kind = stereotype.group(1)
                diagram_types[name] = kind
                stereotypes.setdefault(name, set()).add(kind)

        relations: list[tuple[str, str]] = []
        for relation in re.finditer(
            r"(?m)^\s*([A-Za-z_]\w*)\s+(<\|\.\.|<\|--)\s+"
            r"([A-Za-z_]\w*)", diagram
        ):
            relations.append((
                relation.group(1),
                "interface" if ".." in relation.group(2) else "inheritance",
            ))
        for relation in re.finditer(
            r"(?m)^\s*([A-Za-z_]\w*)\s+(\.\.\|>|--\|>)\s+"
            r"([A-Za-z_]\w*)", diagram
        ):
            relations.append((
                relation.group(3),
                "interface" if relation.group(2).startswith("..") else "inheritance",
            ))

        for base, relation_kind in relations:
            stereotype = diagram_types.get(base)
            problem = ""
            if relation_kind == "interface" and stereotype != "interface":
                problem = (
                    f"`{base}`への点線白三角は契約の実装ですが、"
                    "同じ図で`<<interface>>`になっていません"
                )
            elif relation_kind == "inheritance" and stereotype == "interface":
                problem = (
                    f"`{base}`は`<<interface>>`ですが、実線白三角で"
                    "実装継承として描かれています"
                )
            elif relation_kind == "interface" and stereotype == "abstract":
                problem = (
                    f"`{base}`は`<<abstract>>`ですが、点線白三角で"
                    "契約実装として描かれています"
                )
            if problem and (base, problem) not in reported:
                reported.add((base, problem))
                issues.append(Issue(
                    path,
                    line_number(text, diagram_match.start()),
                    problem,
                ))

    for name, kinds in stereotypes.items():
        if len(kinds) > 1:
            issues.append(Issue(
                path, 1,
                f"`{name}`が同じ章で`<<interface>>`と`<<abstract>>`の"
                "両方として描かれています",
            ))
            continue
        bodies = class_bodies.get(name, [])
        if not bodies:
            continue
        kind = next(iter(kinds))
        has_pure_virtual = any(re.search(r"=\s*0\s*;", body) for body in bodies)
        if not has_pure_virtual:
            issues.append(Issue(
                path, 1,
                f"`{name}`を`<<{kind}>>`としていますが、掲載C++に"
                "純粋仮想関数がありません",
            ))
            continue
        if kind != "interface":
            continue
        shared_virtual = any(re.search(
            r"\bvirtual\s+(?!~)[^;{}]*\([^;{}]*\)[^;{}]*\{",
            body, re.S,
        ) for body in bodies)
        shared_helper = any(re.search(
            r"(?m)^\s*(?!virtual\b|if\b|for\b|while\b|switch\b)"
            r"(?:static\s+)?[A-Za-z_:][\w:<>,*& ]+\s+[A-Za-z_]\w*"
            r"\s*\([^;{}]*\)[^;{}]*\{",
            body,
        ) for body in bodies)
        data_member = any(re.search(
            r"(?m)^\s*(?!using\b|typedef\b|return\b|class\b|struct\b|enum\b)"
            r"[A-Za-z_:][\w:<>,*& ]+\s+[A-Za-z_]\w*_?\s*"
            r"(?:=[^;]+)?;\s*(?://.*)?$",
            body,
        ) for body in bodies)
        if shared_virtual or shared_helper or data_member:
            issues.append(Issue(
                path, 1,
                f"`{name}`を`<<interface>>`としていますが、掲載C++に"
                "業務上の共通実装またはデータメンバーがあります",
            ))
    return issues


def check_no_main_class_in_diagrams(text: str, path: Path) -> list[Issue]:
    """main()は関数なので、クラス図へ架空のMainクラスを置かない。"""
    issues: list[Issue] = []
    for block in re.finditer(
        r"```mermaid\s*\nclassDiagram\b(.*?)```", text, re.S
    ):
        diagram = block.group(1)
        match = re.search(r"(?m)^\s*class\s+Main(?:\s|\{|$)", diagram)
        if match:
            issues.append(Issue(
                path,
                line_number(text, block.start(1) + match.start()),
                "main()は関数です。クラス図へ架空のMainクラスを置かず、"
                "生成・注入は注記、対応表、コードで示してください",
            ))
    return issues


def check_chapter04_assembly_relation(text: str, path: Path) -> list[Issue]:
    """入力提供側がImporterを知る、実コードにない逆向き依存を描かない。"""
    if path.name != "chapter04.md":
        return []
    match = re.search(
        r"(?m)^\s*SampleFileStore\s+\.\.>\s+(?:StoreDataImporter|FCDataImporter)\b",
        text,
    )
    if not match:
        return []
    return [Issue(
        path,
        line_number(text, match.start()),
        "SampleFileStoreはCSV行を返すだけでImporterを知りません。"
        "main()による取得・生成は実行シーケンスとコードで示してください",
    )]


def check_pattern_name_reveal(text: str, path: Path) -> list[Issue]:
    """パターン名は、問題を解いた後の移行文で初めて本文へ出す。"""
    heading = text.find("## パターン解説：")
    if heading < 0:
        return []

    reveal = text.rfind("ここまで問題から導いた", 0, heading)
    if reveal < 0 or heading - reveal > 800:
        return [Issue(
            path,
            line_number(text, heading),
            "パターン解説の直前に、問題から導いた構造とパターン名を結ぶ"
            "移行文を置いてください",
        )]

    # 章タイトルは検索性のために名称を出してよい。コード、図、識別子は
    # 設計結果の実装名を含むため除外し、読者向け散文だけを調べる。
    first_newline = text.find("\n") + 1
    prose = text[first_newline:reveal]
    prose = re.sub(r"```.*?```", "", prose, flags=re.S)
    prose = re.sub(r"`[^`\n]+`", "", prose)
    pattern = re.compile(
        r"(?<![A-Za-z])(?:Strategy|Facade|State|Template Method|Command|"
        r"Decorator|Observer|Factory Method)(?![A-Za-z])"
    )
    match = pattern.search(prose)
    if not match:
        return []
    absolute = first_newline + match.start()
    return [Issue(
        path,
        line_number(text, absolute),
        "パターン解説前の本文にパターン名が出ています。問題から導いた"
        "構造名を使い、名称は解説直前の移行文で初めて結び付けてください",
    )]


ADDED_DEF = "classDef added fill:#1565c0,stroke:#0b3d76,stroke-width:3px,color:#ffffff;"
TOUCHED_DEF = ("classDef touched fill:#ffffff,stroke:#1565c0,"
               "stroke-width:5px,color:#0b3d76;")


def check_diagram_marks_are_two_kinds(text: str, path: Path) -> list[Issue]:
    """図の印は「新しく作る」と「開いて直す」の2種類にそろえる。

    この本の主張は「既にあるコードを開かずに済むか」なので、図の色も
    その2つを分ける。1色の `changed` では、新規1クラスで済んだのか
    既存3クラスを開いたのかが絵から読めない。塗りの値も本全体で1つにする。
    """
    issues: list[Issue] = []
    for found in re.finditer(r"^\s*classDef\s+(\w+)\s+(.+?);?$", text, re.M):
        name, body = found.group(1), found.group(2)
        if name == "changed":
            issues.append(Issue(
                path, line_number(text, found.start()),
                "図の印は `changed` ではなく `added`（新しく作る）と "
                "`touched`（開いて直す）へ分けてください",
            ))
        elif name == "added" and body.rstrip(";") != ADDED_DEF.split(" ", 2)[2].rstrip(";"):
            issues.append(Issue(
                path, line_number(text, found.start()),
                f"新規ノードの塗りは本文共通の `{ADDED_DEF}` を使ってください",
            ))
        elif name == "touched" and body.rstrip(";") != TOUCHED_DEF.split(" ", 2)[2].rstrip(";"):
            issues.append(Issue(
                path, line_number(text, found.start()),
                f"既存ノードの枠は本文共通の `{TOUCHED_DEF}` を使ってください",
            ))
    return issues


def check_diagram_marks_leave_contrast(text: str, path: Path) -> list[Issue]:
    """全ノードへ印が付いた図には、印を付けない。

    対比する相手が図の中に無いと、地の色が変わっただけになる。
    コード画像の帯へ入れてある8割ルールと同じ考え方。
    """
    issues: list[Issue] = []
    for block in re.finditer(r"```mermaid\s*\n(.*?)```", text, re.S):
        body = block.group(1)
        if ":::added" not in body and ":::touched" not in body:
            continue
        nodes = set(re.findall(r"^\s*class (\w+)", body, re.M))
        if not nodes:                      # flowchart は末尾の class 行で指定する
            continue
        marked = set(re.findall(r"^\s*class (\w+):::(?:added|touched)", body, re.M))
        if nodes and marked == nodes:
            issues.append(Issue(
                path, line_number(text, block.start()),
                "全ノードに印が付いています。対比する相手が図に無いので、"
                "印を外し、全部が新規である旨を本文で1行書いてください",
            ))
    return issues


def check_excerpt_keeps_signature(text: str, path: Path) -> list[Issue]:
    """抜粋のシグネチャを書き直さない。

    フェーズ2・4の抜粋で引数や戻り値を簡略化すると、痛みの見えない
    コードになり、「この程度ならクラスを分けなくてよい」という逆の
    結論を読者へ渡してしまう。
    """
    # `Class::method(` のように `::` が直前に来る形も拾う。
    signature = re.compile(
        r"^[ \t]*[\w:&<>~\*\s]*?(\w+)\s*\(([^)]*)\)\s*(?:const\s*)?\{", re.M)
    keywords = {"if", "for", "while", "switch", "catch", "return", "else"}
    baseline: dict[str, set[str]] = {}
    current = text.find("### 1-4")
    end = text.find("## 🟣 フェーズ2", current)
    if min(current, end) < 0:
        return []
    for block in re.finditer(r"```cpp\n(.*?)```", text[current:end], re.S):
        for found in signature.finditer(block.group(1)):
            if found.group(1) in keywords:
                continue
            baseline.setdefault(found.group(1), set()).add(
                " ".join(found.group(2).split()))

    issues: list[Issue] = []
    later = text[end:text.find("## 🟡 フェーズ5") if "## 🟡 フェーズ5" in text else len(text)]
    for block in re.finditer(r"```cpp\n(.*?)```", later, re.S):
        body = block.group(1)
        if "【守る】" not in body and "【変わる】" not in body:
            continue
        for found in signature.finditer(body):
            name, params = found.group(1), " ".join(found.group(2).split())
            if name in keywords:
                continue
            if name in baseline and params not in baseline[name]:
                issues.append(Issue(
                    path, line_number(text, end + block.start()),
                    f"抜粋の `{name}()` の引数が現状コードと違います。"
                    "抜粋は掲載コードから切り出し、書き直さないでください",
                ))
    return issues


def check_change_diagram_highlight(text: str, path: Path) -> list[Issue]:
    """1-5の変更後flowchartで、変更箇所だけを共通色で示す。"""
    start = text.find("### 1-5：")
    end = text.find("## 🟣 フェーズ2：", start)
    if min(start, end) < 0:
        return []
    section = text[start:end]
    issues: list[Issue] = []
    for block in re.finditer(
        r"```mermaid\s*\nflowchart\b(.*?)```", section, re.S
    ):
        diagram = block.group(0)
        if "classDef changed" not in diagram or not re.search(
            r"(?m)^\s*class\s+[^;]+\s+changed\s*;", diagram
        ):
            issues.append(Issue(
                path, line_number(text, start + block.start()),
                "変更後flowchartは追加・変更ノードだけを共通の `changed` 色で示してください",
            ))
    return issues


def check_number_namespace(text: str, path: Path) -> list[Issue]:
    """フェーズ別の読解番号を混用せず、機械置換の副作用も残さない。"""
    issues: list[Issue] = []
    corrupted = text.find("?6?")
    if corrupted >= 0:
        issues.append(Issue(
            path, line_number(text, corrupted),
            "番号の機械置換でC++三項演算子が `?6?` に破損しています",
        ))

    phase6 = text.find("## 🔴 フェーズ6：")
    phase7 = text.find("## 🟢 フェーズ7：", phase6)
    if min(phase6, phase7) < 0:
        return issues

    for match in re.finditer(r"[①②③④⑤⑥⑦⑧⑨⑩]", text):
        if not (phase6 <= match.start() < phase7):
            issues.append(Issue(
                path, line_number(text, match.start()),
                "丸数字は使わず、フェーズ6は契約・組み立て・実行の意味名で示し、"
                "フェーズ1は `(1)`、フェーズ3は `[試行1]`、"
                "フェーズ7は `【1】` を使ってください",
            ))
    return issues


CORRUPTED_PHASE_REFERENCE_TOKENS = (
    "フェーズ契約の確認",
    "フェーズ分離の検算",
    "フェーズ具体の確認",
    "フェーズ生成の検討",
    "フェーズ注入の確認",
)


def check_phase_reference_residue(text: str, path: Path) -> list[Issue]:
    """フェーズ6の意味名置換が、フェーズ1〜5の参照を壊していないか確認する。"""
    issues: list[Issue] = []
    for token in CORRUPTED_PHASE_REFERENCE_TOKENS:
        for match in re.finditer(re.escape(token), text):
            issues.append(Issue(
                path, line_number(text, match.start()),
                f"見出し置換で壊れたフェーズ参照が残っています: {token}。"
                "フェーズ番号と項目名（例: フェーズ4「原因分析」）で示してください",
            ))
    local_names = (
        "契約の確認|分離の検算|具体の確認|生成の検討|注入の確認|"
        "全体経路の準備コード|全体経路の受け渡し"
    )
    for pattern in (
        rf"(?:行|ケース|シナリオ|課題ID|問題ID|原因ID|変更ID|要求ID|リスクID)(?:{local_names})",
        rf"1対(?:{local_names})",
        r"課題ID(?:契約|分離|具体|生成|注入)(?=で|の|を|へ)",
    ):
        for match in re.finditer(pattern, text):
            issues.append(Issue(
                path, line_number(text, match.start()),
                f"番号がフェーズ6の意味名へ置換されています: {match.group(0)}",
            ))
    return issues


PHASE6_LOCAL_REFERENCE_TOKENS = (
    "契約の確認",
    "分離の検算",
    "具体の確認",
    "生成の検討",
    "注入の確認",
    "全体経路の準備コード",
    "全体経路の受け渡し",
)


def check_phase6_reference_scope(text: str, path: Path) -> list[Issue]:
    """フェーズ6の意味名が、行番号やケース番号などへ誤置換されていないか確認する。"""
    start = text.find("## 🔴 フェーズ6：")
    end = text.find("## 🟢 フェーズ7：", start)
    if min(start, end) < 0:
        return []
    issues: list[Issue] = []
    for token in PHASE6_LOCAL_REFERENCE_TOKENS:
        for match in re.finditer(re.escape(token), text):
            if start <= match.start() < end:
                continue
            issues.append(Issue(
                path, line_number(text, match.start()),
                f"フェーズ6専用の意味名がフェーズ6の外にあります: {token}。"
                "行番号・ケース番号・フェーズ1〜5の参照が置換されていないか確認してください",
            ))
    return issues


def check_chapter(path: Path, core: bool) -> list[Issue]:
    text = path.read_text(encoding="utf-8")
    issues = check_fences(text, path)
    issues.extend(check_phase6_exact_heading(text, path))
    issues.extend(check_structure_name_consistency(text, path))
    issues.extend(check_class_diagram_focus_syntax(text, path))
    issues.extend(check_class_diagram_direction(text, path))
    issues.extend(check_class_diagram_glossary(text, path))
    issues.extend(check_class_diagram_type_semantics(text, path))
    issues.extend(check_qualified_method_references(text, path))
    issues.extend(check_chapter0_file_layout_guidance(text, path))
    issues.extend(check_no_main_class_in_diagrams(text, path))
    issues.extend(check_chapter04_assembly_relation(text, path))
    issues.extend(check_ignored_verification_results(text, path))
    issues.extend(check_long_text_blocks(text, path))
    issues.extend(check_one_top_level_type_per_block(text, path))
    issues.extend(check_cpp_semantic_spacing(text, path))
    issues.extend(check_long_final_cpp_blocks(text, path))
    issues.extend(check_executed_test_helpers(text, path))
    issues.extend(check_duplicate_headings(text, path))
    issues.extend(check_banned_patterns(text, path))
    issues.extend(check_overview_phase_scope(text, path))
    issues.extend(check_standard_id_glossary(text, path))
    issues.extend(check_table_column_consistency(text, path))
    issues.extend(check_scenario_label_literal(text, path))
    issues.extend(check_observed_problem_only(text, path))
    issues.extend(check_raw_new_argument_ownership(text, path))
    if core:
        issues.extend(check_standard_simplification_section(text, path))
        issues.extend(check_run_locally_section(text, path))
        issues.extend(check_core_thesis(text, path))
        issues.extend(check_responsibility_table_scope(text, path))
        issues.extend(check_code_block_attribution(text, path))
        issues.extend(check_phase6_fragment_location(text, path))
        issues.extend(check_phase6_numbered_step_titles(text, path))
        issues.extend(check_phase6_point_separation(text, path))
        issues.extend(check_chapter01_rule_lifecycle_terms(text, path))
        issues.extend(check_stable_skeleton_explanation(text, path))
        issues.extend(check_number_namespace(text, path))
        issues.extend(check_phase_reference_residue(text, path))
        issues.extend(check_phase6_reference_scope(text, path))
        issues.extend(check_pattern_name_reveal(text, path))
        issues.extend(check_change_diagram_highlight(text, path))
        issues.extend(check_excerpt_keeps_signature(text, path))
        issues.extend(check_common_phase_headings(text, path))
        issues.extend(check_phase42_comparison_header(text, path))
        issues.extend(check_phase6_overview_diagram(text, path))
        issues.extend(find_in_order(text, REQUIRED_PHASES, path))
        issues.extend(find_in_order(text, REQUIRED_NUMBERED_SECTIONS, path))
        issues.extend(check_required_chapter_structures(text, path))
        issues.extend(check_phase1_system_overview(text, path))
        issues.extend(check_error_condition_last(text, path))
        issues.extend(check_boundary_error_marker(text, path))
        issues.extend(check_phase2_interview_plan(text, path))
        issues.extend(check_phase22_change_list(text, path))
        issues.extend(check_representative_input_preparation(text, path))
        issues.extend(check_phase14_input_trace_position(text, path))
        issues.extend(check_payment_timeout_contract(text, path))
        issues.extend(check_phase5_phase6_reasoning_contract(text, path))
        issues.extend(check_problem_cause_id_lists(text, path))
        issues.extend(check_phase6_complete_comparison_code(text, path))
        issues.extend(check_phase6_baseline(text, path))
        issues.extend(check_phase6_continuity(text, path))
        issues.extend(check_requirement_baseline_contract(text, path))
        issues.extend(check_future_risk_traceability(text, path))
        issues.extend(check_phase6_step_chain(text, path))
        issues.extend(check_phase7_continuity(text, path))
        issues.extend(check_intermediate_boundary_continuity(text, path))
        issues.extend(check_unchanged_baseline(text, path))
        issues.extend(check_class_diagram_completeness(text, path))
        issues.extend(check_phase1_system_model_v3(text, path))
        issues.extend(check_phase1_input_contract_use(text, path))
        issues.extend(check_recent_star_contracts(text, path))
        issues.extend(check_state_automation(text, path))
        issues.extend(check_new_end_to_end_traceability(text, path))
        issues.extend(check_explanation_regression(text, path))
        issues.extend(check_evidence_scenario_reference(text, path))
        issues.extend(check_phase6_phase7_contract_match(text, path))
        issues.extend(check_change_id_requirement_scope(text, path))
        issues.extend(check_step_reference_target(text, path))
        issues.extend(check_validator_template_sync(text, path))
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
