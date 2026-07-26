#!/usr/bin/env python3
"""Validate the semantic completion ledger for the book.

Normal runs validate that the ledger and the task source stay synchronized.
Release runs additionally require every task and chapter review to be complete.
The semantic judgement remains human-reviewed, but a completion claim without
recorded evidence is rejected mechanically.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = BOOK_ROOT / "quality" / "completion-gate.json"
TASK_ID_RE = re.compile(r"^\|\s*(CONS-\d{3})\s*\|", re.MULTILINE)
TASK_STATUSES = {"open", "in_progress", "done"}
CHAPTER_STATUSES = {"pending", "in_review", "pass"}
BOOK_STATUSES = {"in_progress", "ready"}


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"完了条件台帳がありません: {path.relative_to(BOOK_ROOT)}")
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path.relative_to(BOOK_ROOT)}:{exc.lineno}: JSON形式が不正です: "
            f"{exc.msg}"
        )


def expected_chapters() -> set[str]:
    names = {path.name for path in (BOOK_ROOT / "output").glob("chapter*.md")}
    epilogue = BOOK_ROOT / "output" / "epilogue.md"
    if epilogue.exists():
        names.add(epilogue.name)
    return names


def evidence_reference(reference: str) -> tuple[Path, int | None] | None:
    """Return the referenced repository path and optional line number."""
    if not isinstance(reference, str) or not reference.strip():
        return None
    raw_value = reference.strip()
    has_anchor = "#" in raw_value and bool(raw_value.split("#", 1)[1])
    value = raw_value.split("#", 1)[0]
    line_match = re.search(r":(\d+)$", value)
    line_number = int(line_match.group(1)) if line_match else None
    value = re.sub(r":\d+$", "", value)
    if line_number is None and not has_anchor:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return BOOK_ROOT / path, line_number


def validate_evidence(
    owner: str, evidence: object, errors: list[str], *, required: bool
) -> None:
    if not isinstance(evidence, list):
        errors.append(f"{owner}: evidence は配列にしてください")
        return
    if required and not evidence:
        errors.append(f"{owner}: 完了には根拠の行番号または見出しが必要です")
    for reference in evidence:
        parsed = evidence_reference(reference)
        if parsed is None:
            errors.append(f"{owner}: 不正な根拠参照です: {reference!r}")
            continue
        path, line_number = parsed
        if not path.exists():
            errors.append(f"{owner}: 根拠ファイルが存在しません: {reference}")
        elif line_number is not None:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_number < 1 or line_number > line_count:
                errors.append(
                    f"{owner}: 根拠行が範囲外です: {reference} "
                    f"（全{line_count}行）"
                )


def append_github_summary(lines: list[str]) -> None:
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if not destination:
        return
    with Path(destination).open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="未完了タスクまたは未レビュー章があれば失敗する",
    )
    args = parser.parse_args()

    errors: list[str] = []
    try:
        data = load_json(MANIFEST)
    except ValueError as exc:
        print(f"NG: {exc}")
        return 1

    if data.get("schema_version") != 1:
        errors.append("schema_version は 1 にしてください")

    source_value = data.get("task_source")
    if not isinstance(source_value, str):
        errors.append("task_source を文字列で指定してください")
        task_source = BOOK_ROOT / "review-tasks.md"
    else:
        task_source = BOOK_ROOT / source_value

    try:
        task_text = task_source.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        errors.append(f"task_source が読めません: {source_value!r}")
        task_text = ""

    source_ids = TASK_ID_RE.findall(task_text)
    duplicate_ids = sorted(
        task_id for task_id in set(source_ids) if source_ids.count(task_id) > 1
    )
    if duplicate_ids:
        errors.append("タスクIDが重複しています: " + ", ".join(duplicate_ids))

    expected_sequence = [
        f"CONS-{number:03d}" for number in range(1, len(set(source_ids)) + 1)
    ]
    if sorted(set(source_ids)) != expected_sequence:
        errors.append(
            "タスクIDは CONS-001 から欠番なしの連番にしてください"
        )

    tasks = data.get("tasks")
    if not isinstance(tasks, dict):
        errors.append("tasks はオブジェクトにしてください")
        tasks = {}

    source_set = set(source_ids)
    manifest_set = set(tasks)
    missing_tasks = sorted(source_set - manifest_set)
    extra_tasks = sorted(manifest_set - source_set)
    if missing_tasks:
        errors.append("台帳にないタスク: " + ", ".join(missing_tasks))
    if extra_tasks:
        errors.append("タスク一覧に存在しない台帳項目: " + ", ".join(extra_tasks))

    task_counts = {status: 0 for status in sorted(TASK_STATUSES)}
    for task_id, item in sorted(tasks.items()):
        if not isinstance(item, dict):
            errors.append(f"{task_id}: オブジェクトにしてください")
            continue
        status = item.get("status")
        if status not in TASK_STATUSES:
            errors.append(
                f"{task_id}: status は {sorted(TASK_STATUSES)} のいずれかです"
            )
            continue
        task_counts[status] += 1
        validate_evidence(
            task_id, item.get("evidence"), errors, required=status == "done"
        )

    chapters = data.get("chapters")
    if not isinstance(chapters, dict):
        errors.append("chapters はオブジェクトにしてください")
        chapters = {}

    chapter_set = set(chapters)
    expected_chapter_set = expected_chapters()
    missing_chapters = sorted(expected_chapter_set - chapter_set)
    extra_chapters = sorted(chapter_set - expected_chapter_set)
    if missing_chapters:
        errors.append("台帳にない章: " + ", ".join(missing_chapters))
    if extra_chapters:
        errors.append("原稿に存在しない章台帳: " + ", ".join(extra_chapters))

    chapter_counts = {status: 0 for status in sorted(CHAPTER_STATUSES)}
    for chapter, item in sorted(chapters.items()):
        if not isinstance(item, dict):
            errors.append(f"{chapter}: オブジェクトにしてください")
            continue
        status = item.get("status")
        if status not in CHAPTER_STATUSES:
            errors.append(
                f"{chapter}: status は {sorted(CHAPTER_STATUSES)} のいずれかです"
            )
            continue
        chapter_counts[status] += 1
        validate_evidence(
            chapter, item.get("evidence"), errors, required=status == "pass"
        )
        reviewer = item.get("reviewed_by")
        if status == "pass" and (
            not isinstance(reviewer, str) or not reviewer.strip()
        ):
            errors.append(f"{chapter}: pass には reviewed_by が必要です")

    book_status = data.get("book_status")
    if book_status not in BOOK_STATUSES:
        errors.append(f"book_status は {sorted(BOOK_STATUSES)} のいずれかです")

    all_tasks_done = bool(tasks) and task_counts["done"] == len(tasks)
    all_chapters_pass = bool(chapters) and chapter_counts["pass"] == len(chapters)
    completion_required = args.enforce or book_status == "ready"

    if completion_required:
        if not all_tasks_done:
            errors.append(
                f"未完了タスクがあります: "
                f"open={task_counts['open']}, "
                f"in_progress={task_counts['in_progress']}"
            )
        if not all_chapters_pass:
            errors.append(
                f"未レビュー章があります: "
                f"pending={chapter_counts['pending']}, "
                f"in_review={chapter_counts['in_review']}"
            )
        if "**判定：PASS" not in task_text[:6000]:
            errors.append(
                "完成宣言には review-tasks.md の最新監査判定をPASSへ更新してください"
            )

    if book_status == "ready" and not (all_tasks_done and all_chapters_pass):
        errors.append("book_status=ready と台帳の未完了状態が矛盾しています")

    summary = [
        "## Book completion gate",
        "",
        f"- book_status: `{book_status}`",
        f"- tasks: done {task_counts['done']} / {len(tasks)} "
        f"(in progress {task_counts['in_progress']}, open {task_counts['open']})",
        f"- chapters: pass {chapter_counts['pass']} / {len(chapters)} "
        f"(in review {chapter_counts['in_review']}, "
        f"pending {chapter_counts['pending']})",
        f"- mode: `{'release' if completion_required else 'progress'}`",
    ]
    append_github_summary(summary)

    print(
        "完了条件: "
        f"tasks done={task_counts['done']}/{len(tasks)}, "
        f"chapters pass={chapter_counts['pass']}/{len(chapters)}, "
        f"book_status={book_status}"
    )
    if errors:
        for error in errors:
            print(f"NG: {error}")
        return 1

    if completion_required:
        print("OK: 完了条件と全章レビューの証拠がそろっています")
    else:
        print("OK: 進捗台帳はタスク一覧・原稿と同期しています")
    return 0


if __name__ == "__main__":
    sys.exit(main())
