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


if __name__ == "__main__":
    unittest.main()
