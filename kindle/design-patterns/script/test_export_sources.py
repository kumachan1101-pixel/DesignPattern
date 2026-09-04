#!/usr/bin/env python3
"""Regression tests for exported C++ source files."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import export_sources  # noqa: E402


class EncodingTests(unittest.TestCase):
    def test_write_utf8_keeps_lf_even_on_windows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.cpp"
            export_sources.write_utf8(path, "日本語\nsecond\n")
            self.assertEqual(
                "日本語\nsecond\n".encode("utf-8"),
                path.read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
