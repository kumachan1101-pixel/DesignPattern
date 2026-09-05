#!/usr/bin/env python3
"""Regression tests for volume-level publication checks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_volume  # noqa: E402


class TemplateHoleTests(unittest.TestCase):
    def test_long_author_placeholder_is_detected(self) -> None:
        line = "【著者紹介・これまでの活動・ブログのURLをここへ】"
        self.assertEqual([line], check_volume.unresolved_template_holes(line))

    def test_published_change_annotation_is_allowed(self) -> None:
        self.assertEqual([], check_volume.unresolved_template_holes("【追加】"))


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
                "#### 契約：境界の形と受け渡しを決める",
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

    def test_recap_only_does_not_satisfy_placement(self) -> None:
        text = self.valid_chapter().replace(
            check_volume.THREE_QUESTIONS["問い2"],
            "契約を検討する",
        )
        text += "\n### 振り返り\n" + check_volume.THREE_QUESTIONS["問い2"]
        issues = check_volume.three_question_placement_issues(text)
        self.assertIn("問い2がフェーズ6の契約検討にありません", issues)


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


if __name__ == "__main__":
    unittest.main()
