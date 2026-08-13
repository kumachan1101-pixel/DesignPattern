#!/usr/bin/env python3
"""再発防止チェックが、実際に起きた違反を検出できるか確認する。

2026-08-12のロジック監査（logic-audit-20260812.md）で見つかった152件のうち、
機械判定へ落とせた13系統について「わざと壊した本文を検出できるか」を見る。
validate_book.py 本体は「現在の本文が通るか」しか見ないため、チェックが
空振りしていても気づけない。この負のテストで、検査が生きていることを担保する。

    python3 script/test_recurrence_checks.py

対応する監査ID：
  LOGIC-001  受入エビデンスが実行していないシナリオを参照する
  LOGIC-003  フェーズ6の契約が7-1完成コードと食い違う
  LOGIC-007  変更ID一覧の列名が「現行」なのに追加要求IDが並ぶ
  LOGIC-008  参照先のない「フェーズ6のステップN」
  REVIEW-001 クラス図の向きが章内で横向きへ戻る
  REVIEW-002 共通フェーズ見出しが章独自の表記へ戻る
  REVIEW-003 検証・照会メソッドの戻り値を捨てる
  REVIEW-004 著者向けの分類見出しを公開本文へ出す
  REVIEW-005 フェーズ6全体像をテキストだけへ戻す
  REVIEW-006 複数ケースの実行結果を長い一括ブロックへ戻す
  REVIEW-007 変更固有の模擬方法を著者向け共通見出しへ戻す
  REVIEW-008 完成コードのoverride宣言と実装を分断する
  REVIEW-009 4-2の比較表を章独自の列見出しへ戻す
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path("script").resolve()))
import validate_book as V

OUT = Path("output")
cases = []

# 1) LOGIC-001: エビデンスが実行結果にないシナリオを参照する
t = (OUT/"chapter11.md").read_text(encoding="utf-8")
broken = t.replace("A5で未登録IDを拒否し成果物なし", "A9で未登録IDを拒否し成果物なし")
cases.append(("LOGIC-001 エビデンス参照", V.check_evidence_scenario_reference, broken))

# 2) LOGIC-003: フェーズ6契約に7-1へ無いメソッドがある
t = (OUT/"chapter09_2.md").read_text(encoding="utf-8")
broken = t.replace(
    '    virtual ITicketPhase* sendBack() { return reject("差し戻し"); }\nprotected:',
    '    virtual ITicketPhase* sendBack() { return reject("差し戻し"); }\n'
    '    virtual ITicketPhase* archive()  { return reject("封棚"); }\nprotected:', 1)
cases.append(("LOGIC-003 契約不一致", V.check_phase6_phase7_contract_match, broken))

# 3) LOGIC-007: 列名が「現行」なのに追加要求IDが入る
t = (OUT/"chapter10.md").read_text(encoding="utf-8")
broken = t.replace("| 変更ID | 変更依頼の要点 | 関係する要求ID（追加は変更後ID） |",
                   "| 変更ID | 変更依頼の要点 | 対象の現行要求ID |", 1)
cases.append(("LOGIC-007 要求ID列", V.check_change_id_requirement_scope, broken))

# 4) LOGIC-008: 参照先のないステップN
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace("フェーズ6で確定した通知分離構造を実装し",
                   "フェーズ6のステップ3を実装し", 1)
cases.append(("LOGIC-008 ステップ参照", V.check_step_reference_target, broken))

# 5) REVIEW-001: classDiagram が横向きへ戻る
t = (OUT/"chapter04.md").read_text(encoding="utf-8")
broken = t.replace("direction TB", "direction LR", 1)
cases.append(("REVIEW-001 クラス図の向き", V.check_class_diagram_direction, broken))

# 6) REVIEW-002: 6-1 の共通見出しが章独自表記へ戻る
t = (OUT/"chapter11.md").read_text(encoding="utf-8")
broken = t.replace("### 6-1：生成・所有・実行順のまとめ",
                   "### 6-1：生成と破棄のまとめ", 1)
cases.append(("REVIEW-002 共通見出し", V.check_common_phase_headings, broken))

# 7) REVIEW-003: 検証結果を使わず単独で呼ぶ
t = (OUT/"chapter02.md").read_text(encoding="utf-8")
broken = t.replace('if (!auth.verifyOTP(otp)) return false;',
                   'auth.verifyOTP(otp);', 1)
cases.append(("REVIEW-003 戻り値の破棄", V.check_ignored_verification_results, broken))

# 8) REVIEW-004: 著者向けの分類名を公開本文の見出しへ戻す
t = (OUT/"chapter04.md").read_text(encoding="utf-8")
broken = t.replace("**変更後の取込手順と確認点**",
                   "**この章が扱う複雑さ**", 1)
cases.append(("REVIEW-004 著者向け見出し", V.check_banned_patterns, broken))

# 9) REVIEW-005: フェーズ6全体像のMermaid図をtextへ戻す
t = (OUT/"chapter04.md").read_text(encoding="utf-8")
start = t.index("#### まず全体像")
end = t.index("まだクラスの中身は見ません", start)
broken = t[:start] + t[start:end].replace("```mermaid\nflowchart TB", "```text", 1) + t[end:]
cases.append(("REVIEW-005 全体像の図", V.check_phase6_overview_diagram, broken))

# 10) REVIEW-006: 長い実行結果を一括掲載する
t = (OUT/"chapter04.md").read_text(encoding="utf-8")
broken = t + "\n```text\n" + "\n".join(f"出力{i}" for i in range(1, 26)) + "\n```\n"
cases.append(("REVIEW-006 長い実行結果", V.check_long_text_blocks, broken))

# 11) REVIEW-007: 変更固有の節を著者向け分類名へ戻す
t = (OUT/"chapter02.md").read_text(encoding="utf-8")
broken = t.replace("**変更要求を試すための認証・補償モデル**",
                   "**本章での簡易実現モデル**", 1)
cases.append(("REVIEW-007 簡易実現見出し", V.check_banned_patterns, broken))

# 12) REVIEW-008: 7-1でoverrideを宣言だけに戻す
t = (OUT/"chapter03.md").read_text(encoding="utf-8")
broken = t.replace(
    "void reserve(TicketReservation* reservation) override {",
    "void reserve(TicketReservation* reservation) override;\n"
    "    void reserveBody(TicketReservation* reservation) {", 1)
cases.append(("REVIEW-008 override分断", V.check_separated_final_overrides, broken))

# 13) REVIEW-009: 4-2の比較表を章独自の列見出しへ戻す
t = (OUT/"chapter04.md").read_text(encoding="utf-8")
broken = t.replace(
    "| **変わり続けるもの** | **変わってほしくないもの** |",
    "| **変わり続けるもの（取込形式）** | **変わってほしくないもの（登録処理）** |", 1)
cases.append(("REVIEW-009 4-2比較表", V.check_phase42_comparison_header, broken))

# 14) TABLE-001: 第0章の番号表で「表記例」と「意味」を1セルへ潰す
t = (OUT/"chapter00_2.md").read_text(encoding="utf-8")
broken = t.replace(
    "| 原因ID1 | 痛みを生む構造上の原因 |",
    "| 原因ID1：痛みを生む構造上の原因 |", 1)
cases.append(("TABLE-001 表の列数", V.check_table_column_consistency, broken))

# 15) INPUT-001: 第6章の表示ヘルパーへ行番号を引数で戻す
t = (OUT/"chapter06.md").read_text(encoding="utf-8")
broken = t.replace(
    "void showOrder(MenuDatabase& db, const string& itemId,\n"
    "               bool milk, bool whip, bool syrup) {\n",
    "void showOrder(MenuDatabase& db, int row, const string& itemId,\n"
    "               bool milk, bool whip, bool syrup) {\n"
    '    cout << "--- 行" << row << " ---" << endl;\n', 1)
cases.append(("INPUT-001 行ラベルの組み立て", V.check_scenario_label_literal, broken))

print("再発防止チェックの負のテスト（わざと壊した本文を検出できるか）\n")
# 5) 2026-08-13: validator とテンプレートの表頭同期漏れ
#    本文だけ直してテンプレート／validator を放置すると全12章が同じ検査で落ちる
_tmpl = Path("templates/chapter-template.md")
_orig = _tmpl.read_text(encoding="utf-8")
try:
    _tmpl.write_text(
        _orig.replace(V.REQUIRED_TABLE_HEADERS[0],
                      "| 原因として確定した事実 | そのままだと残る痛み | 課題候補 | 候補を導いた理由 |"),
        encoding="utf-8")
    _found = V.check_validator_template_sync("", OUT / V.CORE_CHAPTERS[0])
finally:
    _tmpl.write_text(_orig, encoding="utf-8")
cases.append(("SYNC-001 テンプレート同期", lambda *_: _found, ""))

ng = 0
for name, fn, txt in cases:
    found = fn(txt, Path("dummy.md"))
    mark = "検出OK" if found else "見逃し"
    if not found:
        ng += 1
    print(f"[{mark}] {name}: {len(found)}件")
    for i in found[:1]:
        print(f"         → {i.message[:90]}")
print()
if ng:
    print(f"FAILED: {ng} 件のチェックが違反を見逃しました")
else:
    print(f"OK: {len(cases)} 件のチェックがすべて違反を検出しました")
sys.exit(1 if ng else 0)
