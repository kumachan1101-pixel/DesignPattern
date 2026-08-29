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
broken = t.replace("### 6-1：決めた流れとコードの照合",
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
end = t.index("### 対策検討のクラス図", start)
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
    "| **今回変える責任** | **ほかの変更から守る責任** |",
    "| **今回変える責任（取込形式）** | **ほかの変更から守る責任（登録処理）** |", 1)
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

# 21) STEP-001: 六段の番号付き見出しを再導入する
t = (OUT/"chapter06.md").read_text(encoding="utf-8")
broken = t.replace(
    "#### 1. 契約と具体をセットで決める（分離）",
    "#### 1. 契約と具体をセットで決める（分離）\n\n"
    "**1. 境界の表し方と、何が渡るかを決める 【契約】**",
    1,
)
cases.append(("STEP-001 六段見出しの再導入", V.check_phase6_numbered_step_titles, broken))

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

# 24) DIAGRAM-001: 第0章の実例図から契約実装の線を欠落させる
t = (OUT/"chapter00_2.md").read_text(encoding="utf-8")
broken = t.replace("    IDiscountRule <|.. MemberDiscountRule : 2 契約の実装\n", "", 1)
cases.append((
    "DIAGRAM-001 クラス図の実例と使い分け",
    lambda txt, _: V.check_class_diagram_glossary(txt, OUT/"chapter00_2.md"),
    broken,
))

# 24a) DIAGRAM-004: インターフェース実現を実装継承の線へ戻す
t = (OUT/"chapter00_2.md").read_text(encoding="utf-8")
broken = t.replace(
    "IDiscountRule <|.. MemberDiscountRule",
    "IDiscountRule <|-- MemberDiscountRule",
    1,
)
cases.append((
    "DIAGRAM-004 契約実装と継承の線種",
    V.check_class_diagram_type_semantics,
    broken,
))

# 24aa) DIAGRAM-005: 既定実装を持つ通常基底をinterfaceと誤記する
t = (OUT/"chapter03.md").read_text(encoding="utf-8")
broken = t.replace(
    "    class IReservationState\n",
    "    class IReservationState { <<interface>> }\n",
    1,
)
cases.append((
    "DIAGRAM-005 ステレオタイプとC++実装",
    V.check_class_diagram_type_semantics,
    broken,
))

# 24b) DIAGRAM-002: main()を架空のクラスとして描く
t = (OUT/"chapter04.md").read_text(encoding="utf-8")
broken = t.replace(
    "classDiagram\n    direction TB\n",
    "classDiagram\n    direction TB\n    class Main {\n        +main()\n    }\n",
    1,
)
cases.append(("DIAGRAM-002 架空のMainクラス", V.check_no_main_class_in_diagrams, broken))

# 24c) DIAGRAM-003: 入力提供側からImporterへの架空依存を描く
t = (OUT/"chapter04.md").read_text(encoding="utf-8")
broken = t.replace(
    "    SchemaRegistry *-- ImportSchema : 形式ID別に保存\n",
    "    SchemaRegistry *-- ImportSchema : 形式ID別に保存\n"
    "    SampleFileStore ..> StoreDataImporter : 組み立て時の入力行\n",
    1,
)
cases.append((
    "DIAGRAM-003 実コードにないクラス依存",
    lambda txt, _: V.check_chapter04_assembly_relation(
        txt, OUT/"chapter04.md"
    ),
    broken,
))

# 24d) EDIT-003: 問題を解く前にパターン名を本文へ出す
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace(
    "問題から導いた「ルール差し替え構造」という名前だけを使います。",
    "問題から導いた「Strategy」という名前を使います。",
    1,
)
cases.append(("EDIT-003 パターン名の先出し", V.check_pattern_name_reveal, broken))

# 25) SCOPE-001: 1-4責任表へ簡略化列を重複させる
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace("| 対象 | 主な責任 | 接続先・結果 |",
                   "| 対象 | 主な責任 | 掲載上の表現 |", 1)
cases.append(("SCOPE-001 責任表の目的", V.check_responsibility_table_scope, broken))

# 26) CHANGE-DIAGRAM-001: 変更後図から差分色を外す
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace("    classDef changed fill:#fff2cc,stroke:#d6b656,stroke-width:2px,color:#111827;\n", "", 1)
cases.append(("CHANGE-DIAGRAM-001 変更図の差分色", V.check_change_diagram_highlight, broken))

# 27) SKELETON-001: 分離の検算で骨格を「なし」へ戻す
t = (OUT/"chapter06.md").read_text(encoding="utf-8")
broken = t.replace(
    "##### 分離の検算：守る処理が契約だけを呼べるか",
    "##### 分離の検算：この課題では骨格は無し", 1)
cases.append(("SKELETON-001 安定骨格の省略", V.check_stable_skeleton_explanation, broken))

# 28) REQUIREMENT-ROOT-001: 変更ID一覧にない要求IDへ変更根拠を付ける
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace(
    "| 要求ID5 | 継続<br/>根拠: — |",
    "| 要求ID5 | 変更<br/>根拠: 変更ID1 |", 1)
cases.append(("REQUIREMENT-ROOT-001 要求と変更IDの対応", V.check_requirement_baseline_contract, broken))

# 29) NUMBER-001: フェーズ7の完成コード番号をフェーズ6の丸数字へ戻す
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace("**共通ヘッダーと ProductInfo", "**① 共通ヘッダーと ProductInfo", 1)
cases.append(("NUMBER-001 番号名前空間", V.check_number_namespace, broken))

# 30) REWRITE-001: 番号置換の副作用でC++三項演算子を壊す
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace('? "あり" : "なし"', '?6? "あり" : "なし"', 1)
cases.append(("REWRITE-001 三項演算子の破損", V.check_number_namespace, broken))

# 30a) REWRITE-002: フェーズ6見出しの置換をフェーズ1〜5の参照へ波及させる
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace('フェーズ4「原因分析」', "フェーズ生成の検討", 1)
cases.append(("REWRITE-002 フェーズ参照の破損", V.check_phase_reference_residue, broken))

# 30b) REWRITE-003: 行番号をフェーズ6の意味名へ誤置換する
t = (OUT/"chapter05.md").read_text(encoding="utf-8")
broken = t.replace("1対1で結びついています", "1対契約の確認で結びついています", 1)
cases.append(("REWRITE-003 行番号の破損", V.check_phase6_reference_scope, broken))

# 30c) REWRITE-004: フェーズ6内の数値を意味名へ誤置換する
t = (OUT/"chapter08.md").read_text(encoding="utf-8")
broken = t.replace("生成が1対1で結びついている", "生成が1対契約の確認で結びついている", 1)
cases.append(("REWRITE-004 構造内番号の破損", V.check_phase_reference_residue, broken))

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

# DOC-002: 旧六段ラベルを再導入する
t = (OUT/"chapter12.md").read_text(encoding="utf-8")
broken = t.replace(
    "#### 2. 全体経路をコードで組み立てる",
    "#### 2. 全体経路をコードで組み立てる\n\n"
    "**【安定骨格】【利用開始】**",
    1,
)
cases.append(("DOC-002 旧六段ラベル", V.check_phase6_point_separation, broken))

# DOC-002: フェーズ6の共通見出しを0章・テンプレートと違う語へ戻す
t = (OUT/"chapter12.md").read_text(encoding="utf-8")
broken = t.replace(
    V.PHASE6_EXACT_HEADING,
    "## 🔴 フェーズ6：対策検討 ―― 接続点を変える",
    1,
)
cases.append(("DOC-002 フェーズ6見出し同期", V.check_phase6_exact_heading, broken))

# CONS-068: 導出時だけ別の日本語構造名へ戻す
t = (OUT/"chapter05.md").read_text(encoding="utf-8")
broken = t.replace("操作記録構造", "操作の部品化構造", 1)
cases.append(("CONS-068 日本語構造名の統一", V.check_structure_name_consistency, broken))

# DOC-002: 実行接続表を落とす
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace("| 実行順・ポイント | 担う場所 | 経路で受け渡すもの・起きること | 次の呼出先 |",
                   "| ポイント | 担う場所 | 説明 | 備考 |", 1)
cases.append(("DOC-002 実行接続表", V.check_phase6_point_separation, broken))

# DOC-008: 前工程の事実から全体経路を導く判断表を落とす
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace(
    "| 前工程で確定した事実 | ここで決めること | 判断 | 全体経路への反映 |",
    "| メモ | 問い | 結論 | 配置 |",
    1,
)
cases.append(("DOC-008 全体経路の導出", V.check_phase6_point_separation, broken))

# DOC-002: 全体経路を詳細コードより後ろへ戻す
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
flow_heading = "### 全体のデータと実体の流れを先に決める"
broken = t.replace(flow_heading, "", 1).replace(
    "#### システム全体の最終構造を決める",
    flow_heading + "\n\n#### システム全体の最終構造を決める",
    1,
)
cases.append(("DOC-002 全体経路の順序", V.check_phase6_point_separation, broken))

# DOC-001: 6-1の二つの判断から一行を落とす
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
assembly_row = next(
    line for line in t.splitlines()
    if line.startswith("| 実体の組み立て |")
)
broken = t.replace(assembly_row + "\n", "", 1)
cases.append(("DOC-001 二判断要約", V.check_phase6_point_separation, broken))

# DOC-007: 第1章で選択を注入と取り違える
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace(
    "`select()`自身は注入ではありません。",
    "`select()`自身が注入です。",
    1,
)
cases.append(("DOC-007 選択と注入の区別",
              lambda txt, _: V.check_chapter01_rule_lifecycle_terms(
                  txt, Path("chapter01.md")), broken))

# DOC-005: 一般的な注入方式の一覧を各章へ戻す
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace(
    "##### 実行：Calculatorから選択済みルールを呼ぶ",
    "| 形 | 実装が決まる決め手 | 入る瞬間 | この本での例 |\n"
    "|---|---|---|---|\n"
    "| 呼び出しごと | 入力 | 引き当て時 | 第1章 |\n\n"
    "##### 実行：Calculatorから選択済みルールを呼ぶ",
    1,
)
cases.append(("DOC-005 注入方式一覧の重複", V.check_phase6_point_separation, broken))

# DOC-006: 第0章へ集約した骨格分類表を各章へ戻す
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
marker = "##### 分離の検算：守る処理が契約だけを呼べるか\n"
legacy_skeleton_table = """

| 型 | 骨格の正体 | 契約の置き場 | 見分け方 |
|---|---|---|---|
| 残った側 | 分岐を外した後の手順 | 別の型 | 実行中に替わる |
"""
broken = t.replace(marker, marker + legacy_skeleton_table, 1)
cases.append(("DOC-006 骨格分類表の重複", V.check_phase6_point_separation, broken))

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
    "**掲載箇所：`main()`** ―― 起動時の生成・登録・注入",
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

# EDIT-003: 第0章へ著者の確認印を戻す。フェーズ見出しのない章も対象にする。
def _broken_chapter0_author_mark(*_):
    return [V.Issue(Path("chapter00_1.md"), 1, issue)
            for issue in A.author_marker_issues(
                "chapter00_1.md", "読者向け本文。★ここを再確認する")]

cases.append(("EDIT-003 第0章の著者確認印", _broken_chapter0_author_mark, ""))

# EDIT-002: フェーズ1〜3で解決構造の型名を先出しする
def _broken_spoiler(*_):
    solution = (A.types_between(_ch12, "### 7-1", "### 7-2")
                - A.types_between(_ch12, "### 1-4", "### 1-5")
                - A.types_between(_ch12, "### 3-1", "### 3-2")
                - A.SPOILER_ALLOWED)
    return [V.Issue(Path("chapter12.md"), 1, f"先取り: {sorted(solution)[0]}")] if solution else []

_ch12 = (OUT/"chapter12.md").read_text(encoding="utf-8").replace("\r\n", "\n")
cases.append(("EDIT-002 解決構造の先出し", _broken_spoiler, ""))

# TRACE-001: 5-3で確定する前に課題IDを参照する
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace(
    "次のフェーズでは両方の原因から別々の課題候補を導き",
    "次のフェーズでは課題ID1と課題ID2を導き", 1)
cases.append((
    "TRACE-001 課題IDの先行参照",
    V.check_phase5_phase6_reasoning_contract,
    broken,
))

# TRACE-002: 問題IDを原因・課題の追跡から落とす
t = (OUT/"chapter10.md").read_text(encoding="utf-8")
broken = t.replace("問題ID1・問題ID3・問題ID4", "問題ID1・問題ID3")
cases.append((
    "TRACE-002 問題IDの追跡切れ",
    V.check_phase5_phase6_reasoning_contract,
    broken,
))

# DOC-004: フェーズ6へ実装結果の達成表を重複して戻す
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace(
    "### 6-3：課題から完成構造までの設計トレース",
    "#### システム全体のコード適用結果\n\n"
    "**システム全体の実装結果：達成。**\n\n"
    "### 6-3：課題から完成構造までの設計トレース",
    1,
)
cases.append((
    "DOC-004 対策検討の重複判定",
    V.check_phase6_point_separation,
    broken,
))

# EDIT-004: 二つの判断で導く前に完成方針を宣言する
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace(
    "**ここで全体経路と対応づけるコード：**",
    "**どう解決するか（方針）：** 規則差し替え構造とします。", 1)
cases.append((
    "EDIT-004 対策結論の先出し",
    V.check_phase6_point_separation,
    broken,
))

# CODE-PRESENT-001: 短い兄弟クラスを同じブロックへ戻す
broken = """```cpp
class FirstRule {
public:
    int apply(int value) const { return value; }
};

class SecondRule {
public:
    int apply(int value) const { return value - 1; }
};
```
"""
cases.append((
    "CODE-PRESENT-001 1型1ブロック",
    V.check_one_top_level_type_per_block,
    broken,
))

# CODE-PRESENT-002: 判定の直後へ正常時の実行を詰める
broken = """```cpp
void run() {
    if (!ready()) {
        return;
    }
    execute();
}
```
"""
cases.append((
    "CODE-PRESENT-002 処理段階の空行",
    V.check_cpp_semantic_spacing,
    broken,
))

# CODE-PRESENT-003: 各章から実ファイル分割の案内を落とす
t = (OUT/"chapter01.md").read_text(encoding="utf-8")
broken = t.replace(
    "> **掲載用1ファイルと実務の分割：**",
    "> **掲載コードの補足：**",
    1,
)
cases.append((
    "CODE-PRESENT-003 実ファイル分割案内",
    V.check_run_locally_section,
    broken,
))

# CODE-PRESENT-004: 第0章から具体的なファイル配置を落とす
t = (OUT/"chapter00_2.md").read_text(encoding="utf-8")
broken = t.replace("PremiumDiscount.cpp", "PremiumDiscount実装")
cases.append((
    "CODE-PRESENT-004 第0章ファイル配置",
    lambda text, _path: V.check_chapter0_file_layout_guidance(
        text, OUT/"chapter00_2.md"
    ),
    broken,
))

print("再発防止チェックの負のテスト（わざと壊した本文を検出できるか）\n")
# 5) 2026-08-13: validator とテンプレートの表頭同期漏れ
#    本文だけ直してテンプレート／validator を放置すると全12章が同じ検査で落ちる
_tmpl = Path("templates/chapter-template.md")
_orig = _tmpl.read_text(encoding="utf-8")
try:
    with _tmpl.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(_orig.replace(
            V.REQUIRED_TABLE_HEADERS[0],
            "| 原因として確定した事実 | そのままだと残る痛み | 課題候補 | 候補を導いた理由 |",
        ))
    _found = V.check_validator_template_sync("", OUT / V.CORE_CHAPTERS[0])
finally:
    with _tmpl.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(_orig)
cases.append(("SYNC-001 テンプレート同期", lambda *_, found=_found: found, ""))

# SYNC-002: フェーズ6の章テンプレートだけを旧見出しへ戻す
_orig = _tmpl.read_text(encoding="utf-8")
try:
    with _tmpl.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(_orig.replace(
            V.PHASE6_EXACT_HEADING,
            "## 🔴 フェーズ6：対策検討 ―― 接続点を変える",
            1,
        ))
    _found = V.check_validator_template_sync("", OUT / V.CORE_CHAPTERS[0])
finally:
    with _tmpl.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(_orig)
cases.append(("SYNC-002 フェーズ6テンプレート同期",
              lambda *_, found=_found: found, ""))

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
