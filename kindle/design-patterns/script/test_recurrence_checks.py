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
  REVIEW-009 4-2の比較表を章独自の列見出しへ戻す
  DOC-001   断片コードの所属明示・ブロック分割・省略記号
  DOC-003   フェーズ6の断片コードの掲載箇所ラベル
  RUN-002   1-1の代表実行が1行だけで準備も状態変化も見せない
  EDIT-002  著者向けメモと、フェーズ前半での解決構造の先出し
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
    '    virtual Transition sendBack() const { return reject("差し戻し"); }',
    '    virtual Transition sendBack() const { return reject("差し戻し"); }\n'
    '    virtual Transition archive() const  { return reject("封棚"); }', 1)
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

# 16) TRIAL-001: 未試行の変更の痛みを問題ID表へ戻す
t = (OUT/"chapter06.md").read_text(encoding="utf-8")
broken = t.replace(
    "| 問題ID3 | 種類を`string`で受けるため、",
    "| 問題ID3 | 販売停止・表示順を足すと、価格計算以外の条件も "
    "`CustomDrink` へ増える（変更ID1の試行から見込まれる痛み）。", 1)
cases.append(("TRIAL-001 未試行の痛み", V.check_observed_problem_only, broken))

# 17) STRUCTURE-001: 全章共通の簡略化節を欠落させる
t = (OUT/"chapter02.md").read_text(encoding="utf-8")
broken = t.replace("**この章での簡略化**", "**掲載上の省略**", 1)
cases.append(("STRUCTURE-001 簡略化節", V.check_standard_simplification_section, broken))

# 18) CORE-001: 核心から思考の型の判断軸を落とす
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace("判断軸", "目安", 1)
cases.append(("CORE-001 核心の判断軸", V.check_core_thesis, broken))

# 19) ORDER-001: 代表入力を結果の後へ戻す旧ラベル
t = (OUT/"chapter03.md").read_text(encoding="utf-8")
broken = t.replace("**代表入力（1-4の`main()`から抜粋）：**",
                   "**この結果を生む入力（1-4の`main()`から抜粋）：**", 1)
cases.append(("ORDER-001 代表入力の順", V.check_phase1_system_overview, broken))

# 20) RISK-001: 6-4を非実装の断り中心の旧形式へ戻す
t = (OUT/"chapter06.md").read_text(encoding="utf-8")
broken = t.replace("守れる範囲・残る弱点", "今回の判断", 1)
cases.append(("RISK-001 将来リスク評価", V.check_future_risk_traceability, broken))

# 21) STEP-001: フェーズ6のポイント見出しへ★指摘を残す
t = (OUT/"chapter06.md").read_text(encoding="utf-8")
broken = t.replace("**【契約】：共通契約 `IDrink` を定義する。**",
                   "**【契約】：共通契約 `IDrink` を定義する。★要確認**", 1)
cases.append(("STEP-001 見出しの★残り", V.check_phase6_numbered_step_titles, broken))

# 22) BLOCK-001: 7-1へ複数責任を詰めた長大ブロックを戻す
t = (OUT/"chapter03.md").read_text(encoding="utf-8")
long_block = "```cpp\nclass TooLongA {};\nclass TooLongB {};\n" + \
             "\n".join("// filler" for _ in range(121)) + "\n```\n"
broken = t.replace("### 7-2：", long_block + "\n### 7-2：", 1)
cases.append(("BLOCK-001 長大完成コード", V.check_long_final_cpp_blocks, broken))

# 23) TEST-001: 掲載した回帰テストを実行経路から外す
t = (OUT/"chapter06.md").read_text(encoding="utf-8")
broken = t.replace("    app.runRegressionTests();\n", "", 1)
cases.append(("TEST-001 未実行テスト", V.check_executed_test_helpers, broken))

# 24) DIAGRAM-001: 第0章の実現記法を欠落させる
t = (OUT/"chapter00_2.md").read_text(encoding="utf-8")
broken = t.replace("`Contract <|.. Concrete`", "`Contract ..|> Concrete`", 1)
cases.append((
    "DIAGRAM-001 クラス図記法",
    lambda txt, _: V.check_class_diagram_glossary(txt, OUT/"chapter00_2.md"),
    broken,
))

# 25) SCOPE-001: 1-4責任表へ簡略化列を重複させる
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace("| 対象 | 主な責任 | 接続先・結果 |",
                   "| 対象 | 主な責任 | 掲載上の表現 |", 1)
cases.append(("SCOPE-001 責任表の目的", V.check_responsibility_table_scope, broken))

# 26) CHANGE-DIAGRAM-001: 変更後図から差分色を外す
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace("    classDef changed fill:#fff2cc,stroke:#d6b656,stroke-width:2px,color:#111827;\n", "", 1)
cases.append(("CHANGE-DIAGRAM-001 変更図の差分色", V.check_change_diagram_highlight, broken))

# 27) SKELETON-001: フェーズ6の安定骨格を「なし」へ戻す
t = (OUT/"chapter06.md").read_text(encoding="utf-8")
broken = t.replace(
    "【安定骨格】内側へ委譲して結果を合成する安定骨格",
    "【安定骨格】骨格は無し", 1)
cases.append(("SKELETON-001 安定骨格の省略", V.check_stable_skeleton_explanation, broken))

# 28) REQUIREMENT-ROOT-001: 変更ID一覧にない要求IDへ変更根拠を付ける
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace(
    "| 要求ID5 | 継続<br/>根拠: — |",
    "| 要求ID5 | 変更<br/>根拠: 変更ID1 |", 1)
cases.append(("REQUIREMENT-ROOT-001 要求と変更IDの対応", V.check_requirement_baseline_contract, broken))

# 29) NUMBER-001: フェーズ7の完成コード番号をフェーズ6の丸数字へ戻す
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace("**【1】 商品マスタ", "**① 商品マスタ", 1)
cases.append(("NUMBER-001 番号名前空間", V.check_number_namespace, broken))

# 30) REWRITE-001: 番号置換の副作用でC++三項演算子を壊す
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace('? "あり" : "なし"', '?6? "あり" : "なし"', 1)
cases.append(("REWRITE-001 三項演算子の破損", V.check_number_namespace, broken))

# 31) PHASE22-001: 2-2から1-5の変更IDを一つ落とす
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace(
    "- **変更ID2：既存キャンペーンと重なる場合は逐次割引する**\n", "", 1)
cases.append(("PHASE22-001 変更ID一覧の横並び", V.check_phase22_change_list, broken))

# 32) REPRESENTATIVE-INPUT-001: 入力生成をコメントだけへ戻す
t = (OUT/"chapter08.md").read_text(encoding="utf-8")
broken = t.replace("PaymentRequest r1;", "// PaymentRequest r1 = { ... };", 1)
cases.append((
    "REPRESENTATIVE-INPUT-001 代表入力の生成",
    V.check_representative_input_preparation, broken,
))

# 33) INPUT-TRACE-001: 入力追跡表をコード読解前へ戻す
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
trace_heading = "#### 仕様入力が現状コードで使われるまで\n"
broken = t.replace(trace_heading, "", 1)
broken = broken.replace(
    "### 1-4：実装コード（現状）\n",
    "### 1-4：実装コード（現状）\n\n" + trace_heading,
    1,
)
cases.append((
    "INPUT-TRACE-001 入力追跡表の配置",
    V.check_phase14_input_trace_position, broken,
))

# 34) TIMEOUT-001: 簡略化節からTIMEOUTの初回失敗契約を落とす
t = (OUT/"chapter08.md").read_text(encoding="utf-8")
broken = t.replace(
    "| カード認証 | トークンが `TIMEOUT` で始まり、同じ注文IDでの初回試行 | 通信タイムアウト・再試行可能 |\n",
    "", 1,
)
cases.append((
    "TIMEOUT-001 スタブ契約の同期",
    lambda txt, _: V.check_payment_timeout_contract(
        txt, OUT/"chapter08.md"),
    broken,
))

# RUN-001: 「手元で動かすには」節を欠落させる
t = (OUT/"chapter08.md").read_text(encoding="utf-8")
broken = t.replace("> **手元で動かすには**", "> **メモ**", 1)
cases.append(("RUN-001 手元で動かすには", V.check_run_locally_section, broken))

# DOC-002: 【安定骨格】と【利用開始】を一つの見出しへ戻す
t = (OUT/"chapter12.md").read_text(encoding="utf-8")
broken = t.replace("**【安定骨格】 状態委譲の安定骨格。**",
                   "**【安定骨格】【利用開始】状態委譲は現在状態へ委ねるだけ。**", 1)
cases.append(("DOC-002 骨格と利用開始の統合", V.check_phase6_point_separation, broken))

# DOC-002: 実行接続表を落とす
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace("| 実行順・ポイント | 掲載箇所 | 実際のコード接続 | 次の呼出先 |",
                   "| ポイント | 掲載箇所 | 説明 | 備考 |", 1)
cases.append(("DOC-002 実行接続表", V.check_phase6_point_separation, broken))

# DOC-001: 構造ポイントの全貌表を落とす
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace("#### 構造ポイントの全貌 ―― どの責任がどこへ移るか",
                   "#### 補足", 1)
cases.append(("DOC-001 構造全貌表", V.check_phase6_point_separation, broken))

# DOC-001: 断片コードの所属明示を落とす
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace(
    "**PaymentCalculator::calculate() の割引判定（変更前）**",
    "**変更前の割引判定**", 1).replace(
    "変える場所を先に確認します。`PaymentCalculator::calculate()` のうち、",
    "変える場所を先に確認します。この関数のうち、", 1)
cases.append(("DOC-001 断片の所属", V.check_code_block_attribution, broken))

# DOC-001: 1ブロックを上限超えの行数へ戻す
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
_pad = "\n".join("    int pad%d = %d;" % (i, i) for i in range(90))
broken = t.replace("    // C003（Regular）/ 割引なし",
                   "    // C003（Regular）/ 割引なし\n" + _pad, 1)
cases.append(("DOC-001 ブロック過大", V.check_code_block_attribution, broken))

# DOC-001: 変わる理由が違う型を1ブロックへ詰め戻す
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
_types = "\n".join("class Extra%d { public: int v; };" % i for i in range(4))
broken = t.replace("    // C003（Regular）/ 割引なし",
                   _types + "\n    // C003（Regular）/ 割引なし", 1)
cases.append(("DOC-001 多型ブロック", V.check_code_block_attribution, broken))

# DOC-001: 分岐を省略記号で隠す
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace("    // C003（Regular）/ 割引なし",
                   "    // …（中略：割引判定）…", 1)
cases.append(("DOC-001 コードの省略", V.check_code_block_attribution, broken))

# DOC-003: フェーズ6の断片から掲載箇所ラベルを外す
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace(
    "**掲載箇所：`main()`** ―― 組み立ての先頭。具体施策をスタック上に生成します。",
    "どの施策クラスを作るかを知るのは組み立て箇所だけです。", 1)
cases.append(("DOC-003 掲載箇所ラベル", V.check_phase6_fragment_location, broken))

# RUN-002: 1-1の代表入力を1行実行へ戻す（準備も状態変化も見せない形）
import check_representative_run as R

def _broken_representative_run(*_):
    """代表入力を1回呼びへ戻したときに検出できるかを見る。"""
    original = R.MIN_CALLS
    try:
        R.MIN_CALLS = 99          # 「1行実行では足りない」状態を再現する
        found = R.chapter_issues("chapter01.md")
    finally:
        R.MIN_CALLS = original
    return [V.Issue(Path("chapter01.md"), 1, m) for m in found]

cases.append(("RUN-002 代表実行の回数", _broken_representative_run, ""))

# EDIT-002: 著者向けメモ（進行管理の宣言）を本文へ戻す
import check_author_notes as A

def _broken_author_note(*_):
    t = (OUT/"chapter01.md").read_text(encoding="utf-8")
    broken = t.replace(
        "ここで挙げるのは、原因のどの構造を変える必要があるかまでです。",
        "この段階では、解決クラス名・契約名・パターン名・生成場所を決めません。", 1)
    prose = A.code_free(broken)
    return [V.Issue(Path("chapter01.md"), 1, m.group(0))
            for m in A.PROCESS_DECLARATION.finditer(prose)]

cases.append(("EDIT-002 著者向けメモ", _broken_author_note, ""))

# EDIT-002: フェーズ1〜3で解決構造の型名を先出しする
def _broken_spoiler(*_):
    solution = (A.types_between(_ch12, "### 7-1", "### 7-2")
                - A.types_between(_ch12, "### 1-4", "### 1-5")
                - A.types_between(_ch12, "### 3-1", "### 3-2")
                - A.SPOILER_ALLOWED)
    return [V.Issue(Path("chapter12.md"), 1, f"先取り: {sorted(solution)[0]}")] if solution else []

_ch12 = (OUT/"chapter12.md").read_text(encoding="utf-8").replace("\r\n", "\n")
cases.append(("EDIT-002 解決構造の先出し", _broken_spoiler, ""))

print("再発防止チェックの負のテスト（わざと壊した本文を検出できるか）\n")
# 5) 2026-08-13: validator とテンプレートの表頭同期漏れ
#    本文だけ直してテンプレート／validator を放置すると全12章が同じ検査で落ちる
_tmpl = Path("templates/chapter-template.md")
_orig = _tmpl.read_text(encoding="utf-8")
try:
    _tmpl.write_text(
        _orig.replace(V.REQUIRED_TABLE_HEADERS[0],
                      "| 原因として確定した事実 | そのままだと残る痛み | 課題候補 | 候補を導いた理由 |"),
        encoding="utf-8", newline="\n")
    _found = V.check_validator_template_sync("", OUT / V.CORE_CHAPTERS[0])
finally:
    _tmpl.write_text(_orig, encoding="utf-8", newline="\n")
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
