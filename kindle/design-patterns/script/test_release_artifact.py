#!/usr/bin/env python3
"""Regression tests for public PDF freshness checks."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import release_artifact  # noqa: E402


class ReleaseArtifactTests(unittest.TestCase):
    def test_source_change_makes_synced_pdf_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_script = root / "script" / "build_epub.py"
            chapter = root / "books" / "sample" / "output" / "chapter.md"
            cover = root / "books" / "sample" / "cover.png"
            cover_metadata = root / "books" / "sample" / "cover.json"
            dist_pdf = root / "books" / "sample" / "publishing" / "dist" / "book.pdf"
            config = root / "books" / "sample" / "publishing" / "book.json"
            for path in (build_script, chapter, cover, cover_metadata, dist_pdf):
                path.parent.mkdir(parents=True, exist_ok=True)
            build_script.write_text("# build\n", encoding="utf-8")
            chapter.write_text("# 本文\n", encoding="utf-8")
            cover.write_bytes(b"png")
            cover_metadata.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "file": "cover.png",
                        "sha256": hashlib.sha256(b"png").hexdigest(),
                        "title": "テスト書名",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            dist_pdf.write_bytes(b"%PDF-1.4\nexample")
            config.write_text(
                json.dumps(
                    {
                        "paths": {
                            "dist": "books/sample/publishing/dist",
                            "cover": "books/sample/cover.png",
                            "coverMetadata": "books/sample/cover.json",
                            "preview": "books/sample/preview/book.pdf",
                            "previewManifest": "books/sample/preview/book.manifest.json",
                        },
                        "metadata": {"title": "テスト書名"},
                        "chapters": ["books/sample/output/chapter.md"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with (
                patch.object(release_artifact, "BOOK_ROOT", root),
                patch.object(release_artifact, "BUILD_SCRIPT", build_script),
            ):
                release_artifact.sync_release_artifact(config)
                self.assertEqual([], release_artifact.check_release_artifact(config))

                chapter.write_text("# 修正後の本文\n", encoding="utf-8")
                failures = release_artifact.check_release_artifact(config)
                self.assertEqual(1, len(failures))
                self.assertIn("現在の原稿・表紙・組版コードより古い", failures[0])

    def test_cover_title_must_match_book_title(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cover = root / "cover.png"
            metadata_path = root / "cover.json"
            config = root / "book.json"
            cover.write_bytes(b"png")
            metadata_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "file": "cover.png",
                        "sha256": hashlib.sha256(b"png").hexdigest(),
                        "title": "表紙の書名",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            config.write_text(
                json.dumps(
                    {
                        "metadata": {"title": "本文の書名"},
                        "paths": {
                            "preview": "preview.pdf",
                            "cover": "cover.png",
                            "coverMetadata": "cover.json",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(release_artifact, "BOOK_ROOT", root):
                failures = release_artifact.check_cover_metadata(config)
            self.assertEqual(1, len(failures))
            self.assertIn("表紙の書名", failures[0])


if __name__ == "__main__":
    unittest.main()
