#!/usr/bin/env python3
"""Build済みPDFを公開用プレビューへ同期し、原稿との一致を検査する。

同期:
    python script/release_artifact.py sync --config books/.../publishing/book.json

検査:
    python script/release_artifact.py check --config books/.../publishing/book.json

`book.json` の `paths.preview` と `paths.previewManifest` を公開物の正本とする。
原稿・表紙・book.json・組版コードのどれかが変わったのにPDFを再生成しなければ、
ハッシュが一致せず出版ゲートが失敗する。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Sequence


BOOK_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = BOOK_ROOT / "script" / "build_epub.py"


def project_path(value: str) -> Path:
    target = (BOOK_ROOT / value).resolve()
    try:
        target.relative_to(BOOK_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"設定パスが書籍ルート外です: {value}") from exc
    return target


def load_config(config_path: Path) -> dict[str, Any]:
    return json.loads(config_path.resolve().read_text(encoding="utf-8"))


def release_paths(
    config_path: Path,
) -> tuple[Path, Path, Path, list[Path]] | None:
    raw = load_config(config_path)
    paths = raw.get("paths", {})
    preview_value = paths.get("preview")
    manifest_value = paths.get("previewManifest")
    if not preview_value and not manifest_value:
        return None
    if not preview_value or not manifest_value:
        raise ValueError("paths.preview と paths.previewManifest は両方指定してください")

    dist = project_path(str(paths["dist"]))
    preview = project_path(str(preview_value))
    manifest = project_path(str(manifest_value))
    source_files = [config_path.resolve(), BUILD_SCRIPT.resolve()]
    cover = paths.get("cover")
    if cover:
        source_files.append(project_path(str(cover)))
    cover_metadata = paths.get("coverMetadata")
    if cover_metadata:
        source_files.append(project_path(str(cover_metadata)))
    source_files.extend(project_path(str(item)) for item in raw.get("chapters", []))
    return dist / "book.pdf", preview, manifest, source_files


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_sources(paths: Sequence[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.resolve().relative_to(BOOK_ROOT.resolve()).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def check_cover_metadata(config_path: Path) -> list[str]:
    """表紙画像の正本と、目視転記した書名・ハッシュの一致を検査する。"""
    try:
        raw = load_config(config_path)
        paths = raw.get("paths", {})
        if not paths.get("preview"):
            return []
        cover_value = paths.get("cover")
        metadata_value = paths.get("coverMetadata")
        if not cover_value or not metadata_value:
            return ["公開PDFには paths.cover と paths.coverMetadata が必要です"]
        cover = project_path(str(cover_value))
        metadata_path = project_path(str(metadata_value))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as exc:
        return [f"{config_path}: 表紙メタデータを読めません: {exc}"]

    failures: list[str] = []
    if metadata.get("schemaVersion") != 1:
        failures.append(f"未対応の表紙メタデータです: {metadata_path}")
    if (metadata_path.parent / str(metadata.get("file", ""))).resolve() != cover:
        failures.append("表紙メタデータのfileがbook.jsonのpaths.coverと一致しません")
    if not cover.is_file():
        failures.append(f"表紙画像がありません: {cover}")
    elif metadata.get("sha256") != digest_file(cover):
        failures.append(
            "表紙画像がcover.jsonの記録後に変わっています。画像を目視し、"
            "書名・サブタイトル・帯とsha256を更新してください"
        )
    title = str(raw.get("metadata", {}).get("title", ""))
    if metadata.get("title") != title:
        failures.append(
            f"表紙の書名「{metadata.get('title', '')}」とbook.jsonの書名「{title}」が一致しません"
        )
    return failures


def check_release_artifact(config_path: Path) -> list[str]:
    """不一致理由を返す。公開物を宣言していない設定は検査対象外。"""
    cover_failures = check_cover_metadata(config_path)
    if cover_failures:
        return cover_failures
    try:
        resolved = release_paths(config_path)
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as exc:
        return [f"{config_path}: 公開PDF設定を読めません: {exc}"]
    if resolved is None:
        return []

    _, preview, manifest, source_files = resolved
    missing_sources = [path for path in source_files if not path.is_file()]
    if missing_sources:
        return [f"公開PDFの入力がありません: {path}" for path in missing_sources]
    if not preview.is_file():
        return [f"公開PDFがありません: {preview}"]
    if not preview.read_bytes().startswith(b"%PDF"):
        return [f"公開PDFの形式が不正です: {preview}"]
    if not manifest.is_file():
        return [
            f"公開PDFの鮮度記録がありません: {manifest}。"
            "PDF生成後に release_artifact.py sync を実行してください"
        ]

    try:
        recorded = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"公開PDFの鮮度記録が不正です: {manifest}: {exc}"]

    failures: list[str] = []
    current_source = digest_sources(source_files)
    current_pdf = digest_file(preview)
    if recorded.get("sourceSha256") != current_source:
        failures.append(
            f"公開PDFが現在の原稿・表紙・組版コードより古いです: {preview}。"
            "PDFを再生成して release_artifact.py sync を実行してください"
        )
    if recorded.get("pdfSha256") != current_pdf:
        failures.append(f"公開PDFと鮮度記録のハッシュが一致しません: {preview}")
    return failures


def sync_release_artifact(config_path: Path) -> Path:
    cover_failures = check_cover_metadata(config_path)
    if cover_failures:
        raise ValueError(" / ".join(cover_failures))
    resolved = release_paths(config_path)
    if resolved is None:
        raise ValueError("book.json に paths.preview がありません")
    built_pdf, preview, manifest, source_files = resolved
    if not built_pdf.is_file():
        raise FileNotFoundError(
            f"生成済みPDFがありません: {built_pdf}。先に build_epub.py all を実行してください"
        )
    if not built_pdf.read_bytes().startswith(b"%PDF"):
        raise ValueError(f"生成済みPDFの形式が不正です: {built_pdf}")
    missing_sources = [path for path in source_files if not path.is_file()]
    if missing_sources:
        raise FileNotFoundError(f"公開PDFの入力がありません: {missing_sources[0]}")

    preview.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built_pdf, preview)
    payload = {
        "schemaVersion": 1,
        "sourceSha256": digest_sources(source_files),
        "pdfSha256": digest_file(preview),
        "sourceFiles": [
            path.resolve().relative_to(BOOK_ROOT.resolve()).as_posix()
            for path in source_files
        ],
    }
    manifest.write_bytes(
        (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    return preview


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "sync"))
    parser.add_argument("--config", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "sync":
            preview = sync_release_artifact(args.config)
            print(f"OK: 公開PDFを同期しました: {preview}")
            return 0
        failures = check_release_artifact(args.config)
        if failures:
            print("\n".join(failures))
            return 1
        print("OK: 公開PDFは現在の原稿・表紙・組版コードと一致しています")
        return 0
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
