#!/usr/bin/env python3
"""Regression tests for the publication pipeline's non-rendering logic."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_epub  # noqa: E402


class ChunkingTests(unittest.TestCase):
    def test_title_reduces_only_the_first_chunk(self) -> None:
        lines = [str(index) for index in range(45)]
        chunks = build_epub.split_chunks(lines, True, 19, 22, 4)
        self.assertEqual([19, 26], [len(chunk) for chunk in chunks])

    def test_small_tail_is_joined_to_previous_chunk(self) -> None:
        lines = [str(index) for index in range(24)]
        chunks = build_epub.split_chunks(lines, False, 19, 22, 4)
        self.assertEqual([24], [len(chunk) for chunk in chunks])

    def test_empty_block_still_produces_one_chunk(self) -> None:
        self.assertEqual(
            [[""]],
            build_epub.split_chunks([], False, 19, 22, 4),
        )

    def test_cpp_chunk_prefers_complete_method_over_small_tail_merge(self) -> None:
        lines = [f"line {index}" for index in range(24)]
        lines[17] = "}"
        lines[18] = ""
        chunks = build_epub.split_code_chunks(lines, True, 19, 22, 4)
        self.assertEqual([19, 5], [len(chunk) for chunk in chunks])
        self.assertEqual("", chunks[0][-1])

    def test_cpp_chunk_does_not_leave_method_signature_at_image_end(self) -> None:
        lines = [f"line {index}" for index in range(24)]
        lines[16] = "}"
        lines[17] = ""
        lines[18] = "bool hasCapacity() {"
        chunks = build_epub.split_code_chunks(lines, True, 19, 22, 4)
        self.assertEqual("", chunks[0][-1])
        self.assertEqual("bool hasCapacity() {", chunks[1][0])

    def test_cpp_chunk_does_not_create_closing_brace_only_image(self) -> None:
        lines = [f"line {index}" for index in range(23)]
        lines[-1] = "};"
        chunks = build_epub.split_code_chunks(lines, False, 19, 22, 4)
        self.assertEqual([23], [len(chunk) for chunk in chunks])
        self.assertEqual("};", chunks[0][-1])


class MarkdownTests(unittest.TestCase):
    def test_cpp_aliases_select_cpp(self) -> None:
        for alias in ("cpp", "c++", "cc", "cxx", "hpp"):
            with self.subTest(alias=alias):
                self.assertEqual("cpp", build_epub.normalized_language(alias))

    def test_code_title_uses_nearest_heading(self) -> None:
        text = "本文\n\n#### PaymentService::pay()\n\n```cpp\nreturn;\n```\n"
        match = build_epub.FENCE_RE.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(
            ("PaymentService::pay()", None),
            build_epub.preceding_block_title(text, match.start()),
        )

    def test_diagram_title_moves_standalone_bold_label_to_caption(self) -> None:
        text = "### 現状構造\n\n**システム全体図**\n\n次の図で境界を見ます。\n\n" + chr(96) * 3 + "mermaid\ngraph LR\nA --> B\n" + chr(96) * 3 + "\n"
        match = build_epub.FENCE_RE.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(
            ("システム全体図", "**システム全体図**"),
            build_epub.preceding_diagram_title(text, match.start()),
        )

    def test_diagram_number_uses_reader_facing_chapter_number(self) -> None:
        self.assertEqual("図0-2", build_epub.diagram_number("02-chapter00", 2))
        self.assertEqual("図序-1", build_epub.diagram_number("01-preface", 1))

    def test_visual_intro_is_marked_for_page_break_control(self) -> None:
        body = '<p>前の説明です。</p><h3>図の節</h3>'
        body += '<p>次の図で確認します。</p>\n<figure class="mermaid-image">'
        body += '<img src="a.png" /></figure>'
        marked = build_epub.mark_visual_introductions(body)
        self.assertIn('<p class="figure-intro">', marked)
        self.assertIn('<div class="visual-unit">', marked)
        self.assertIn('<p>前の説明です。</p><h3>図の節</h3><div', marked)

    def test_content_hash_changes_with_title(self) -> None:
        first = build_epub.content_hash("cpp", "A", "int main() {}")
        second = build_epub.content_hash("cpp", "B", "int main() {}")
        self.assertNotEqual(first, second)


class ConfigTests(unittest.TestCase):
    def test_default_config_lists_existing_chapters(self) -> None:
        config = build_epub.load_config(build_epub.DEFAULT_CONFIG)
        self.assertEqual(16, len(config.chapters))
        self.assertTrue(all(path.is_file() for path in config.chapters))
        self.assertEqual(len(config.chapters), len(config.slide_page_order))


if __name__ == "__main__":
    unittest.main()
