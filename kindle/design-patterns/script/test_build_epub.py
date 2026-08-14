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
            "PaymentService::pay()",
            build_epub.preceding_block_title(text, match.start()),
        )

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
