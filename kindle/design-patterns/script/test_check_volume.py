#!/usr/bin/env python3
"""Regression tests for volume-level publication checks."""

from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_volume  # noqa: E402
import check_diagram  # noqa: E402


class TemplateHoleTests(unittest.TestCase):
    def test_long_author_placeholder_is_detected(self) -> None:
        line = "【著者紹介・これまでの活動・ブログのURLをここへ】"
        self.assertEqual([line], check_volume.unresolved_template_holes(line))

    def test_published_change_annotation_is_allowed(self) -> None:
        self.assertEqual([], check_volume.unresolved_template_holes("【追加】"))


class PublicationStyleTests(unittest.TestCase):
    def test_explicit_std_without_duplicate_table_is_accepted(self) -> None:
        text = "```cpp\nstd::vector<std::string> values;\n```\n"
        self.assertEqual([], check_volume.publication_style_issues(text))

    def test_using_namespace_std_is_rejected(self) -> None:
        issues = check_volume.publication_style_issues(
            "```cpp\nusing namespace std;\nvector<string> values;\n```\n"
        )
        self.assertTrue(any("using namespace std" in issue for issue in issues))

    def test_repeated_class_member_table_is_rejected(self) -> None:
        issues = check_volume.publication_style_issues(
            "```mermaid\nclassDiagram\n```\n"
            "**クラス図に出てくる主なメンバーと操作**\n"
        )
        self.assertTrue(any("重複掲載" in issue for issue in issues))

    def test_reader_facing_practical_headings_are_accepted(self) -> None:
        text = (
            "# 第1章 題材\n"
            "### この章で解く設計課題\n"
            "自然な文章。\n"
            "## 🔵 フェーズ1\n"
            "#### 実システムと掲載コードの違い\n"
        )
        self.assertEqual([], check_volume.publication_style_issues(text))

    def test_old_practical_headings_are_rejected(self) -> None:
        text = (
            "# 第1章 題材\n"
            "### この章の核心\n"
            "**場面。** 断片。\n"
            "**この章での簡略化**\n"
        )
        issues = check_volume.publication_style_issues(text)
        self.assertTrue(any("この章の核心" in issue for issue in issues))
        self.assertTrue(any("この章での簡略化" in issue for issue in issues))


class EarlyMaterialSpoilerTests(unittest.TestCase):
    def test_cpp_example_is_rejected_even_with_unrelated_names(self) -> None:
        text = "# 第0章\n\n```cpp\nclass NeutralExample {};\n```\n"
        hits = check_volume.early_material_spoilers(text, set())
        self.assertIn((3, "題材を替えても完成形を先に示すC++コード例"), hits)

    def test_later_solution_type_is_rejected(self) -> None:
        text = "第3章では `InventoryNotifier` をmainから渡します。"
        hits = check_volume.early_material_spoilers(
            text,
            {"InventoryNotifier"},
        )
        self.assertTrue(any("InventoryNotifier" in detail for _, detail in hits))

    def test_pattern_names_and_problem_summaries_are_allowed(self) -> None:
        text = "第1章はStrategyを扱い、ルール追加で既存処理が変わる問題を追います。"
        self.assertEqual([], check_volume.early_material_spoilers(text, set()))


class ThreeQuestionPlacementTests(unittest.TestCase):
    def valid_chapter(self) -> str:
        return "\n".join(
            [
                "## フェーズ4：原因分析",
                check_volume.THREE_QUESTIONS["問い1"],
                "## フェーズ5：課題定義",
                "## フェーズ6：対策検討",
                "#### 契約：課題の入出力をC++の型と操作にする",
                check_volume.THREE_QUESTIONS["問い2"],
                "#### 生成・所有・受け渡しを決める",
                check_volume.THREE_QUESTIONS["問い3"],
                "## フェーズ7：対策実施",
            ]
        )

    def test_questions_at_decision_points_are_accepted(self) -> None:
        self.assertEqual(
            [],
            check_volume.three_question_placement_issues(self.valid_chapter()),
        )

    def test_chapter_specific_contract_heading_is_accepted(self) -> None:
        text = self.valid_chapter().replace(
            "#### 契約：課題の入出力をC++の型と操作にする",
            "#### 契約：販促方針の入出力をC++の型と操作にする",
        )
        self.assertEqual([], check_volume.three_question_placement_issues(text))

    def test_recap_only_does_not_satisfy_placement(self) -> None:
        text = self.valid_chapter().replace(
            check_volume.THREE_QUESTIONS["問い2"],
            "契約を検討する",
        )
        text += "\n### 振り返り\n" + check_volume.THREE_QUESTIONS["問い2"]
        issues = check_volume.three_question_placement_issues(text)
        self.assertIn("問い2がフェーズ6の契約検討にありません", issues)


class ContractTranslationTests(unittest.TestCase):
    def contract(self, body: str) -> str:
        return "\n".join(
            [
                "## フェーズ6：対策検討",
                "#### 契約：課題の入出力をC++の型と操作にする",
                body,
                "#### 生成・所有・受け渡しを決める",
                "## フェーズ7：対策実施",
            ]
        )

    def test_phase5_connection_translated_to_cpp_is_accepted(self) -> None:
        text = self.contract(
            "フェーズ5で確定した入力と結果を、C++のメソッド、引数型、"
            "戻り値型へ翻訳します。"
        )
        self.assertEqual([], check_volume.contract_translation_issues(text))

    def test_reselecting_business_inputs_in_contract_is_rejected(self) -> None:
        text = self.contract(
            "フェーズ5の接続を確認します。\n"
            "| 接続候補 | 決めた形 | 理由 |\n"
            "|---|---|---|\n"
            "| 金額 | 引数 | 計算するため |"
        )
        issues = check_volume.contract_translation_issues(text)
        self.assertTrue(any("再選別" in issue for issue in issues))

    def test_contract_without_phase5_input_is_rejected(self) -> None:
        issues = check_volume.contract_translation_issues(
            self.contract("必要な引数をここで考えます。")
        )
        self.assertTrue(any("フェーズ5" in issue for issue in issues))


class PhaseInternalCheckpointTests(unittest.TestCase):
    def valid_chapter(self) -> str:
        return "\n".join(
            [
                "## フェーズ1：現状把握",
                "フェーズ1の確認観点：",
                "## フェーズ2：仮説立案",
                "フェーズ2の確認観点：",
                "### 2-5：次に試す変更と、守る動作を決める",
                "変更IDを試し、動作を維持する。リスクIDはフェーズ6へ渡す。",
                "## フェーズ3：問題特定",
                "フェーズ3の確認観点：",
                "依頼が名指ししたもの以外まで、書き換えるか確認することになっていないか？",
                "## フェーズ4：原因分析",
                "### 4-1：責任の混在を原因として確定する",
                "| 図の番号 | その場所が見ている情報 | 該当実装 | 責任としての読み方 |",
                "|---|---|---|---|",
                "| ① | 会員種別 | `Calculator::calculate()` | 販促方針 |",
                "|---|---|---|",
                "| 販促方針を決める | `calc()` | ○ |",
                "| 責任 | 見ている接続情報 |",
                "|---|---|---|",
                "| 販促方針 | A | 条件と式を決める |",
                "## フェーズ5：課題定義",
                "### 5-1：原因をなくす責任配置を決める",
                "### 5-2：課題と完了条件を確定する",
                "## フェーズ6：対策検討",
                "フェーズ6の確認観点：",
                "## フェーズ7：対策実施",
                "フェーズ7の確認観点：",
            ]
        )

    def test_checkpoints_at_each_phase_are_accepted(self) -> None:
        self.assertEqual(
            [],
            check_volume.phase_internal_checkpoint_issues(self.valid_chapter()),
        )

    def test_checkpoint_in_wrong_phase_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "## フェーズ3：問題特定\nフェーズ3の確認観点：\n"
            "依頼が名指ししたもの以外まで、書き換えるか確認することになっていないか？",
            "## フェーズ3：問題特定\nフェーズ3の確認観点：",
        )
        text += "\n依頼が名指ししたもの以外まで、書き換えるか確認することになっていないか？"
        issues = check_volume.phase_internal_checkpoint_issues(text)
        self.assertTrue(any("直接変更と巻き込み" in issue for issue in issues))


class CppBlockUnitTests(unittest.TestCase):
    def test_one_type_per_heading_and_block_is_accepted(self) -> None:
        text = """**CustomerInfo**

```cpp
struct CustomerInfo {};
```

**CustomerDatabase**

```cpp
class CustomerDatabase {};
```
"""
        self.assertEqual([], check_volume.cpp_block_unit_issues(text))

    def test_group_heading_for_single_type_block_is_rejected(self) -> None:
        text = """**CustomerInfo と CustomerDatabase**

```cpp
struct CustomerInfo {};
```

**CustomerDatabase**

```cpp
class CustomerDatabase {};
```
"""
        issues = check_volume.cpp_block_unit_issues(text)
        self.assertTrue(any("複数の型をまとめています" in issue for issue in issues))

    def test_struct_and_plain_enum_in_one_block_are_rejected(self) -> None:
        text = """**StockAlert**

```cpp
struct StockAlert {};
enum DeliveryStatus { ACCEPTED, FAILED };
```
"""
        issues = check_volume.cpp_block_unit_issues(text)
        self.assertTrue(any("StockAlert, DeliveryStatus" in issue for issue in issues))

    def test_single_type_title_mismatch_is_rejected(self) -> None:
        text = """**CustomerInfo**

```cpp
class CustomerDatabase {};
```

```cpp
struct CustomerInfo {};
```
"""
        issues = check_volume.cpp_block_unit_issues(text)
        self.assertTrue(any("見出し=CustomerInfo、コード=CustomerDatabase" in issue for issue in issues))


class ClassLegendPairingTests(unittest.TestCase):
    def test_each_diagram_followed_by_its_explanation_is_accepted(self) -> None:
        text = """### クラス図の線の意味

```mermaid
classDiagram
%% explanation-set
A <|-- B : ①
```

直前のクラス図の①を説明します。

```mermaid
classDiagram
%% explanation-set
C --> D : ⑤
```

直前のクラス図の⑤を説明します。

## フェーズ1
"""
        self.assertEqual([], check_volume.class_legend_pairing_issues(text))

    def test_diagrams_listed_before_explanations_are_rejected(self) -> None:
        text = """### クラス図の線の意味

```mermaid
classDiagram
%% explanation-set
A <|-- B : ①
```

次の図も見ます。

```mermaid
classDiagram
%% explanation-set
C --> D : ⑤
```

①と⑤をまとめて説明します。

## フェーズ1
"""
        issues = check_volume.class_legend_pairing_issues(text)
        self.assertIn("①の説明が、その番号を載せた図の直後にありません", issues)


class HandRunGuidanceTests(unittest.TestCase):
    def test_single_chapter_zero_guidance_is_accepted(self) -> None:
        text = "### 掲載コードを手元で動かす\n\n説明\n"
        self.assertEqual([], check_volume.hand_run_guidance_issues(text, True))

    def test_practical_chapter_repetition_is_rejected(self) -> None:
        text = "> **手元で動かすには**\n> g++で実行します\n"
        self.assertEqual(
            ["第0章と重複する「手元で動かすには」があります"],
            check_volume.hand_run_guidance_issues(text, False),
        )

    def test_missing_chapter_zero_guidance_is_rejected(self) -> None:
        self.assertEqual(
            ["第0章の実行案内が0件です（1件だけ必要です）"],
            check_volume.hand_run_guidance_issues("# 第0章\n", True),
        )


class EditorialMarkerTests(unittest.TestCase):
    def test_star_instruction_is_rejected(self) -> None:
        self.assertEqual(
            ["2行目に★編集指示があります"],
            check_volume.editorial_marker_issues("本文\n★ここを直す\n"),
        )


class PracticalExplanationConsistencyTests(unittest.TestCase):
    def valid_chapter(self) -> str:
        return "\n".join(
            [
                "### この章を読むと得られること",
                "- **得られること1：変動の特定。** 説明",
                "- **得られること2：原因の特定。** 説明",
                "- **得られること3：再結合の設計。** 説明",
                "- **得られること4：効果の検証。** 説明",
                "## フェーズ1：現状把握",
                "> [!NOTE] この動作例は、第0章で説明した模擬環境で動きます。",
                "**現状：何を組み合わせて支払金額を決めるか**",
                "| 変更ID | 変更内容 | 確認する具体例 |",
                "**変更後：何を組み合わせて支払金額を決めるか**",
                "**実システムの変更を、掲載コードではどう再現するか**",
                "| 実システムの変更対象 | 掲載コードでの表現 | この章で省くもの |",
                "#### 変更後に有効な業務ルール",
                "## フェーズ3：問題特定",
                "### 3-1：変更を試みる",
                "変更ID1を試し、既存動作を維持する。",
                "### 3-2：変更影響グラフ",
                "## フェーズ4：原因分析",
                "### 4-1：責任の混在を原因として確定する",
                "| 図の番号 | その場所が見ている情報 | 該当実装 | 責任としての読み方 |",
                "|---|---|---|---|",
                "| ① | 会員種別 | `Calculator::calculate()` | 販促方針 |",
                "|---|---|---|",
                "| 販促方針を決める | `calc()` | ○ |",
                "| 責任 | 見ている接続情報 |",
                "|---|---|---|",
                "| 販促方針 | A | 条件と式を決める |",
                "**対策前：変更を現状構造へ当てた状態**",
                "```mermaid",
                "classDiagram",
                "%% provisional-role-diagram",
                "class Current {",
                "責任：販促方針",
                "責任：注文計算",
                "}",
                "```",
                "販促方針は直接変わり、注文計算は巻き込まれた。原因ID1の混在が問題ID1を生んだ。",
                "## フェーズ5：課題定義",
                "### 5-1：原因をなくす責任配置を決める",
                "**目標：責任を分けてつなぐ**",
                "```mermaid",
                "classDiagram",
                "%% provisional-role-diagram",
                "class Stable[\"安定側\"] {",
                "責任：注文計算",
                "}",
                "class Change[\"① 変化側\"] {",
                "責任：販促方針",
                "}",
                "Stable --> Change : 依頼と結果",
                "```",
                "### 5-2：課題と完了条件を確定する",
                "#### 課題ID1（境界）の完了条件",
                "**解く原因：** 原因ID1（責任の同居）",
                "**構造の変更：** 目標図の①のとおり責任を分ける。",
                "**接続：** 元の責任から依頼を渡し、分けた責任から結果を返す。",
                "完成コードで次を満たせば完了です。",
                "- 完成コードで確認する",
                "1行が一つの原因です。問題から原因を追います。",
                "| 観測した問題 | 確定した原因 | 課題で目指す状態 |",
                "## フェーズ6：対策検討",
                "### 分離した責任をコードの構造へ変える",
                "```mermaid",
                "classDiagram",
                "class OrderProcessor[\"OrderProcessor\"] {",
                "責任：注文計算",
                "}",
                "class IRule[\"IRule\"] {",
                "責任：販促方針",
                "}",
                "OrderProcessor --> IRule : 依頼と結果",
                "```",
                "### 構想をコードでつなぐ",
                "### 構想を確定する",
                "## フェーズ7：対策実施",
                "#### 完成後のクラス図",
                "フェーズ4で元のクラスに混在していた責任は、完成構造では変更理由ごとのクラスへ分かれた。",
                "#### 完成後の実行シーケンス",
                "#### 設計課題の完了確認",
                "1行が一つの完了条件です。左から条件、証拠、判定を読みます。",
                "| フェーズ5の完了条件 | コード上の証拠 | 判定 |",
                "|---|---|---|",
                "| 完成コードで確認する | `Stable` | 合格 |",
                "#### 変更前→変更後の不変条件照合",
                "### この章のまとめ",
                "- **得られること1：変動の特定。** 根拠",
                "- **得られること2：原因の特定。** 根拠",
                "- **得られること3：再結合の設計。** 根拠",
                "- **得られること4：効果の検証。** 根拠",
            ]
        )

    def test_common_structure_is_accepted(self) -> None:
        self.assertEqual(
            [],
            check_volume.practical_explanation_consistency_issues(
                self.valid_chapter()
            ),
        )

    def test_table_without_reading_guide_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "1行が一つの原因です。問題から原因を追います。\n",
            "",
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("表の直前に1行の単位" in issue for issue in issues))

    def test_old_responsibility_table_is_rejected(self) -> None:
        text = self.valid_chapter() + (
            "\n| 責任 | 問題が起きたコードで担うこと | 今回の変更との関係 |\n"
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("責任表が残っています" in issue for issue in issues))

    def test_old_before_after_responsibility_table_is_rejected(self) -> None:
        text = self.valid_chapter() + "\n| 責任 | 変更前 | 変更後 |\n"
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("旧フェーズ4表" in issue for issue in issues))

    def test_change_preview_table_in_phase31_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "変更ID1を試し、既存動作を維持する。",
            "変更ID1を試し、既存動作を維持する。\n"
            "| 変更ID | 仮に変更するコード | 変更内容 |\n"
            "|---|---|---|\n"
            "| 変更ID1 | Calculator | 条件追加 |",
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("変更内容を予告する表" in issue for issue in issues))

    def test_problem_finding_table_in_phase31_is_accepted(self) -> None:
        text = self.valid_chapter().replace(
            "変更ID1を試し、既存動作を維持する。",
            "変更ID1を試し、既存動作を維持する。\n"
            "| 手段 | 渡すもの | 返ってくる値 |\n"
            "|---|---|---|\n"
            "| Email | 本文 | 成功／失敗 |",
        )
        self.assertEqual(
            [], check_volume.practical_explanation_consistency_issues(text)
        )

    def test_task_card_without_connection_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "**接続：** 元の責任から依頼を渡し、分けた責任から結果を返す。\n",
            "",
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("課題カード" in issue for issue in issues))

    def test_missing_target_responsibility_diagram_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "**目標：責任を分けてつなぐ**\n"
            "```mermaid\n"
            "classDiagram\n"
            "%% provisional-role-diagram\n"
            "class Stable[\"安定側\"] {\n"
            "責任：注文計算\n"
            "}\n"
            "class Change[\"① 変化側\"] {\n"
            "責任：販促方針\n"
            "}\n"
            "Stable --> Change : 依頼と結果\n"
            "```\n",
            "",
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("原因をなくす目標" in issue for issue in issues))

    def test_paraphrased_completion_condition_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "| 完成コードで確認する | `Stable` | 合格 |",
            "| 完成コードで確認できる | `Stable` | 合格 |",
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("同じ文言" in issue for issue in issues))

    def test_old_phase6_headings_are_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "### 分離した責任をコードの構造へ変える",
            "### 構想を決める",
        ).replace("### 構想を確定する", "### 構想を採用する")
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("フェーズ6の共通見出し" in issue for issue in issues))

    def test_completion_evidence_without_reading_guide_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "1行が一つの完了条件です。左から条件、証拠、判定を読みます。\n",
            "",
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("設計課題の完了確認表" in issue for issue in issues))

    def test_missing_final_responsibility_mapping_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "フェーズ4で元のクラスに混在していた責任は、完成構造では変更理由ごとのクラスへ分かれた。\n",
            "",
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("完成後クラス図の直後" in issue for issue in issues))

    def test_negative_process_declaration_is_rejected(self) -> None:
        issues = check_volume.process_declaration_issues(
            "chapter01.md",
            "ここでは対策を決めません。",
        )
        self.assertTrue(any("執筆の段取り" in issue for issue in issues))

    def test_result_first_cause_heading_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "### 4-1：責任の混在を原因として確定する",
            "### 4-1：痛みの根源を探る（観察と原因）",
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("4-1：責任の混在を原因として確定する" in issue for issue in issues))

    def test_problem_ids_on_every_process_are_rejected(self) -> None:
        text = self.valid_chapter()
        text += "\n| 着目箇所 | そこで行っている処理・判断 | 対応する問題ID |\n"
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("旧フェーズ4表" in issue for issue in issues))

    def test_previous_detailed_phase4_tables_are_rejected(self) -> None:
        text = self.valid_chapter()
        text += "\n| 分析対象を選ぶ根拠 | 原因分析で開くコード箇所 |\n"
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("旧フェーズ4表" in issue for issue in issues))

    def test_old_labels_and_redundant_tables_are_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "### 分離した責任をコードの構造へ変える",
            "**構想上のコード経路**\n"
            "### 分離した責任をコードの構造へ変える",
        )
        text += "\n--- 行1: 実行 ---\n**変更前→変更後の要求対照（今回変える要求IDだけ）**\n"
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("旧表現" in issue for issue in issues))
        self.assertTrue(any("重複する要求差分表" in issue for issue in issues))
        self.assertTrue(any("最終コード経路" in issue for issue in issues))

    def test_final_cpp_in_phase5_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "## フェーズ5：課題定義",
            "## フェーズ5：課題定義\n```cpp\nclass IRule {};\n```",
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("フェーズ5に最終コード" in issue for issue in issues))

    def test_summary_without_opening_promises_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "- **得られること4：効果の検証。** 根拠",
            "- **別の結論。** 根拠",
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("章末のまとめ" in issue for issue in issues))

    def test_missing_change_simplification_is_rejected(self) -> None:
        text = self.valid_chapter().replace(
            "**実システムの変更を、掲載コードではどう再現するか**\n"
            "| 実システムの変更対象 | 掲載コードでの表現 | この章で省くもの |\n",
            "",
        )
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("掲載コードではどう再現するか" in issue for issue in issues))

    def test_editorial_rationale_in_body_is_rejected(self) -> None:
        text = self.valid_chapter() + "\nこの図を置きます。\n"
        issues = check_volume.practical_explanation_consistency_issues(text)
        self.assertTrue(any("編集・レビュー向け" in issue for issue in issues))


class DiagramDiffLabelTests(unittest.TestCase):
    def test_text_labels_with_color_marks_are_accepted(self) -> None:
        text = """```mermaid
graph TD
A["［新規］ Rule"]:::added
B["［変更］ Calculator<br>条件2本 → 3本"]:::touched
```
```mermaid
classDiagram
class Rule:::added {
  <<new>>
}
class Calculator:::touched {
  <<changed>>
}
```
"""
        self.assertEqual([], check_volume.diagram_diff_label_issues(text))

    def test_color_only_marks_are_rejected(self) -> None:
        text = """```mermaid
graph TD
A["Rule"]:::added
```
```mermaid
classDiagram
class Calculator:::touched {
  +run()
}
```
"""
        issues = check_volume.diagram_diff_label_issues(text)
        self.assertTrue(any("［新規］" in issue for issue in issues))
        self.assertTrue(any("<<changed>>" in issue for issue in issues))

    def test_changed_marker_without_before_after_is_rejected(self) -> None:
        text = """```mermaid
graph TD
A["［変更］ Calculator"]:::touched
```
"""
        issues = check_volume.diagram_diff_label_issues(text)
        self.assertTrue(any("変更前→変更後" in issue for issue in issues))

    def test_changed_marker_with_added_item_list_is_accepted(self) -> None:
        text = """```mermaid
graph TD
A["［変更］受け取る操作<br>予約／支払／取消<br>一時保留（追加）"]:::touched
```
"""
        issues = check_volume.diagram_diff_label_issues(text)
        self.assertFalse(issues)


class Phase6ClassDiagramTests(unittest.TestCase):
    def test_partial_then_integrated_diagram_is_accepted(self) -> None:
        text = """## フェーズ6：対策検討
これは部分クラス図で、現在の判断対象以外は省略する。
```mermaid
classDiagram
A --> B
```
## フェーズ7：対策実施
### 完成後のクラス図
部分クラス図を全体へ統合する。
"""
        self.assertEqual([], check_volume.phase6_class_diagram_issues(text))


    def test_missing_partial_diagram_is_rejected(self) -> None:
        text = """## フェーズ6：対策検討
構想だけを書く。
## フェーズ7：対策実施
### 完成後のクラス図
"""
        issues = check_volume.phase6_class_diagram_issues(text)
        self.assertTrue(any("部分クラス図がありません" in issue for issue in issues))

    def test_phase6_decision_diagram_does_not_need_provisional_marker(self) -> None:
        text = """## フェーズ6：対策検討
これは部分クラス図で、現在の判断対象以外は省略する。
```mermaid
classDiagram
A --> B
```
## フェーズ7：対策実施
### 完成後のクラス図
部分クラス図を全体へ統合する。
"""
        self.assertEqual([], check_volume.phase6_class_diagram_issues(text))


class Phase6DiagramCodeAlignmentTests(unittest.TestCase):
    def test_phase6_partial_diagram_uses_phase7_complete_code(self) -> None:
        chapter = """## 🔴 フェーズ6：対策検討
```mermaid
classDiagram
Calculator --> IRule : 契約を保持
IRule <|.. ConcreteRule : 実現
```
## 🟢 フェーズ7：対策実施
```cpp
class IRule {
public:
    virtual void run() = 0;
};
```
```cpp
class ConcreteRule : public IRule {
public:
    void run() override {}
};
```
```cpp
class Calculator {
    IRule* rule;
};
```
"""
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "03-chapter01.md").write_text(chapter, encoding="utf-8")
            config = root / "book.json"
            config.write_text(
                json.dumps({"chapters": ["03-chapter01.md"]}),
                encoding="utf-8",
            )
            original_root = check_diagram.BOOK_ROOT
            check_diagram.BOOK_ROOT = root
            try:
                with redirect_stdout(StringIO()):
                    result = check_diagram.check(config)
            finally:
                check_diagram.BOOK_ROOT = original_root
        self.assertEqual(0, result)


class ChangeImpactAlignmentTests(unittest.TestCase):
    def chapter(self, before: str, after: str) -> str:
        return f"""### 3-2：変更影響グラフ
```mermaid
graph TD
{before}
```
### 3-3：痛みの言語化
### 7-3：変更影響グラフ（改善後）
```mermaid
graph TD
{after}
```
## 整理
"""

    def test_same_change_ids_and_composition_scope_are_accepted(self) -> None:
        text = self.chapter(
            'A["変更ID1"] --> B["［変更］ main()<br>入力"]',
            'A["変更ID1"] --> B["［変更］ main()<br>登録"]',
        )
        self.assertEqual([], check_volume.change_impact_alignment_issues(text))

    def test_different_change_ids_are_rejected(self) -> None:
        text = self.chapter(
            'A["変更ID1"] --> B["［変更］ main()<br>入力"]',
            'A["変更ID2"] --> B["［変更］ main()<br>登録"]',
        )
        issues = check_volume.change_impact_alignment_issues(text)
        self.assertTrue(any("変更ID集合" in issue for issue in issues))

    def test_composition_only_counted_after_is_rejected(self) -> None:
        text = self.chapter(
            'A["変更ID1"] --> B["［変更］ Core<br>分岐"]',
            'A["変更ID1"] --> B["［変更］ BatchApplication<br>登録"]',
        )
        issues = check_volume.change_impact_alignment_issues(text)
        self.assertTrue(any("組み立て箇所" in issue for issue in issues))


class RedundantSectionTests(unittest.TestCase):
    def test_compact_phase7_is_accepted(self) -> None:
        text = "### 7-3：変更影響グラフ（改善後）\n\n## 整理\n"
        self.assertEqual([], check_volume.redundant_section_issues(text))

    def test_old_recap_sections_are_rejected(self) -> None:
        text = """### 7-2：動作シーケンス図の検証
### 7-4：変更シナリオ表
### 「はじめに」の三つの問いにどう答えたか
"""
        issues = check_volume.redundant_section_issues(text)
        self.assertEqual(3, len(issues))


class PracticeChapterCharacterTests(unittest.TestCase):
    def test_limit_is_enforced_for_practice_chapters_only(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp:
            root = Path(temp)
            chapter00 = root / "02-chapter00.md"
            chapter01 = root / "03-chapter01.md"
            chapter02 = root / "04-chapter02.md"
            chapter00.write_text("0" * 100, encoding="utf-8")
            chapter01.write_text("1" * 6, encoding="utf-8")
            chapter02.write_text("2" * 5, encoding="utf-8")
            issues = check_volume.practice_chapter_character_issues(
                [chapter00, chapter01, chapter02], 10
            )
        self.assertEqual(1, len(issues))
        self.assertIn("11文字 > 10文字", issues[0])

    def test_missing_limit_is_accepted(self) -> None:
        self.assertEqual(
            [], check_volume.practice_chapter_character_issues([], None)
        )


class AssemblyResponsibilityTests(unittest.TestCase):
    def test_assembly_only_owns_and_registers_components(self) -> None:
        text = """**InventoryApplication**

```cpp
class InventoryApplication {
    InventoryManager manager;
    void registerNotifications() { manager.attach(&email); }
public:
    InventoryManager& inventory() { return manager; }
};
```
---
"""
        self.assertEqual([], check_volume.assembly_responsibility_issues(text))

    def test_scenario_execution_in_assembly_is_rejected(self) -> None:
        text = """**ReservationAssembly**

```cpp
class ReservationAssembly {
public:
    void run() { std::cout << "case"; }
};
```
---
"""
        issues = check_volume.assembly_responsibility_issues(text)
        self.assertTrue(any("動作例の進行" in issue for issue in issues))
        self.assertTrue(any("結果表示" in issue for issue in issues))

    def test_concrete_state_selection_in_runner_is_rejected(self) -> None:
        text = """**BatchApplication**

```cpp
class BatchApplication {
    void run() { TicketReservation r(availableState()); }
};
```
---
"""
        issues = check_volume.assembly_responsibility_issues(text)
        self.assertTrue(any("availableState(" in issue for issue in issues))

    def test_validation_helper_in_runner_is_rejected(self) -> None:
        text = """**BatchApplication**

```cpp
class BatchApplication {
    bool validateExists(const std::string& id) { return true; }
};
```
---
"""
        issues = check_volume.assembly_responsibility_issues(text)
        self.assertTrue(any("入力検証・照会" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
