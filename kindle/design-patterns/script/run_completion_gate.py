#!/usr/bin/env python3
"""Run the same book quality gate locally and in GitHub Actions."""

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
            "Published execution output",
            [python, str(SCRIPT_DIR / "check_execution_output.py")],
        ),
    ]

    failed = [label for label, command in checks if not run(label, command)]
    print("\n=== Quality gate result ===")
    if failed:
        print("FAIL: " + ", ".join(failed))
        return 1
    if args.release:
        print("PASS: 出版完了条件を含む全ゲートに合格しました")
    else:
        print("PASS: 通常push用ゲートに合格しました（出版完了判定ではありません）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
