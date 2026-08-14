#!/usr/bin/env python3
"""本文ゲートと出版パッケージゲートを走らせる（ローカルとGitHub Actions共通）。

判定を2つに分けている（GATE-001）。

  manuscript ready   : 引数なし。原稿が書けているか（構造・コード・図・実行結果）
  KDP package ready  : --package。その原稿を1冊へ束ねられるか（目次・成果物）

原稿がすべてPASSしていても、目次から章が抜けていれば本は組めない。逆に
出版直前でなければパッケージ検査を毎回回す必要もないので、既定は本文ゲート
だけにしてある。--release は完了台帳の全項目完了まで要求する最終判定。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = BOOK_ROOT / "script"


def run(label: str, command: list[str]) -> bool:
    print(f"\n=== {label} ===", flush=True)
    result = subprocess.run(command, cwd=BOOK_ROOT)
    if result.returncode != 0:
        print(f"NG: {label} failed with exit code {result.returncode}")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release",
        action="store_true",
        help="全タスク完了・全章レビューPASSを必須にする",
    )
    parser.add_argument(
        "--package",
        action="store_true",
        help="出版パッケージ検査（目次・成果物）まで含めて判定する",
    )
    args = parser.parse_args()

    python = sys.executable
    ledger_command = [python, str(SCRIPT_DIR / "check_completion_gate.py")]
    if args.release:
        ledger_command.append("--enforce")

    checks = [
        ("Completion ledger", ledger_command),
        ("Book structure", [python, str(SCRIPT_DIR / "validate_book.py")]),
        (
            "Review risk baseline and C++ compile",
            [python, str(SCRIPT_DIR / "audit_book.py"), "--check-baseline"],
        ),
        ("Kindle formatting", [python, str(SCRIPT_DIR / "check_kindle.py")]),
        (
            "Author notes and spoilers",
            [python, str(SCRIPT_DIR / "check_author_notes.py")],
        ),
        (
            "Published execution output",
            [python, str(SCRIPT_DIR / "check_execution_output.py")],
        ),
        (
            "Representative run in 1-1",
            [python, str(SCRIPT_DIR / "check_representative_run.py")],
        ),
        (
            "Unused C++ inputs",
            [python, str(SCRIPT_DIR / "check_unused_cpp_inputs.py")],
        ),
        (
            "Mermaid rendering",
            [python, str(SCRIPT_DIR / "check_mermaid.py")],
        ),
        (
            "Recurrence checks alive",
            [python, str(SCRIPT_DIR / "test_recurrence_checks.py")],
        ),
    ]

    if args.package or args.release:
        checks.append((
            "Publish package",
            [python, str(SCRIPT_DIR / "check_publish_package.py")],
        ))

    failed = [label for label, command in checks if not run(label, command)]
    print("\n=== Quality gate result ===")
    if failed:
        print("FAIL: " + ", ".join(failed))
        return 1
    if args.release:
        print("PASS: 出版完了条件を含む全ゲートに合格しました（KDP package ready）")
    elif args.package:
        print("PASS: 本文と出版パッケージの両ゲートに合格しました（KDP package ready）")
    else:
        print("PASS: 本文ゲートに合格しました（manuscript ready）")
        print("      出版パッケージの判定は --package を付けて実行します")
    return 0


if __name__ == "__main__":
    sys.exit(main())
