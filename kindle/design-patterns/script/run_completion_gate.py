#!/usr/bin/env python3
"""本文ゲートと出版パッケージゲートを走らせる（ローカルとGitHub Actions共通）。

判定を2つに分けている（GATE-001）。

  manuscript ready   : 引数なし。旧全章と、books/*/publishing/book.json で
                       宣言した各分冊の原稿を検査する
  one volume         : --config。指定したbook.jsonの本文と同梱ソースだけを
                       検査する（PDF・EPUBは作らない）
  KDP package ready  : --package。その原稿を1冊へ束ねられるか（目次・成果物）

原稿がすべてPASSしていても、目次から章が抜けていれば本は組めない。逆に
出版直前でなければPDFなどのパッケージ検査を毎回回す必要もないので、既定は
本文ゲートだけにしてある。ただし分冊本文と同梱ソースは既定でも検査する。
--release は完了台帳の全項目完了まで要求する最終判定。
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


def volume_manuscript_checks(
    python: str, volume_config: Path
) -> list[tuple[str, list[str]]]:
    """1冊分の本文検査を返す。PDF/EPUBの鮮度検査は含めない。"""
    name = volume_config.parents[1].name
    config_args = ["--config", str(volume_config)]
    return [
        (
            f"Volume: {name}",
            [python, str(SCRIPT_DIR / "check_volume.py"), *config_args],
        ),
        (
            f"Code runs: {name}",
            [python, str(SCRIPT_DIR / "check_code_runs.py"), *config_args],
        ),
        (
            f"Published execution output: {name}",
            [python, str(SCRIPT_DIR / "check_execution_output.py"), *config_args],
        ),
        (
            f"Representative run: {name}",
            [python, str(SCRIPT_DIR / "check_representative_run.py"), *config_args],
        ),
        (
            f"Unused C++ inputs: {name}",
            [python, str(SCRIPT_DIR / "check_unused_cpp_inputs.py"), *config_args],
        ),
        (
            f"Mermaid rendering: {name}",
            [python, str(SCRIPT_DIR / "check_mermaid.py"), *config_args],
        ),
        (
            f"Class diagrams: {name}",
            [python, str(SCRIPT_DIR / "check_diagram.py"), *config_args],
        ),
        (
            f"Kindle layout: {name}",
            [python, str(SCRIPT_DIR / "check_layout.py"), *config_args],
        ),
        (
            f"Forward refs: {name}",
            [python, str(SCRIPT_DIR / "check_forward.py"), *config_args],
        ),
        (
            f"Phase flow: {name}",
            [python, str(SCRIPT_DIR / "check_flow.py"), *config_args],
        ),
        (
            f"Code anchoring: {name}",
            [python, str(SCRIPT_DIR / "check_anchor.py"), *config_args],
        ),
        (
            f"Sources build: {name}",
            [
                python,
                str(SCRIPT_DIR / "export_sources.py"),
                *config_args,
                "--verify",
            ],
        ),
    ]


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
    parser.add_argument(
        "--config",
        help="本文検査をこの冊のbook.jsonだけに限定する",
    )
    args = parser.parse_args()

    python = sys.executable
    ledger_command = [python, str(SCRIPT_DIR / "check_completion_gate.py")]
    if args.release:
        ledger_command.append("--enforce")

    checks: list[tuple[str, list[str]]] = []
    if not args.config:
        # output/ の旧12章にだけ適用する互換ゲート。分冊の合否とは分ける。
        checks.extend([
            ("Legacy completion ledger", ledger_command),
            ("Legacy book structure", [python, str(SCRIPT_DIR / "validate_book.py")]),
            (
                "Legacy review risk baseline and C++ compile",
                [python, str(SCRIPT_DIR / "audit_book.py"), "--check-baseline"],
            ),
            ("Legacy Kindle formatting", [python, str(SCRIPT_DIR / "check_kindle.py")]),
            (
                "Legacy author notes and spoilers",
                [python, str(SCRIPT_DIR / "check_author_notes.py")],
            ),
            (
                "Legacy published execution output",
                [python, str(SCRIPT_DIR / "check_execution_output.py")],
            ),
            (
                "Legacy representative run in 1-1",
                [python, str(SCRIPT_DIR / "check_representative_run.py")],
            ),
            (
                "Legacy unused C++ inputs",
                [python, str(SCRIPT_DIR / "check_unused_cpp_inputs.py")],
            ),
            (
                "Legacy Mermaid rendering",
                [python, str(SCRIPT_DIR / "check_mermaid.py")],
            ),
            (
                "Legacy recurrence checks alive",
                [python, str(SCRIPT_DIR / "test_recurrence_checks.py")],
            ),
        ])
    checks.append((
        "Completion gate scope test",
        [python, str(SCRIPT_DIR / "test_completion_gate_scope.py")],
    ))

    # 分冊は出版物の正本である。PDF/EPUBをまだ作らない本文作業中でも、
    # book.json が指す原稿・図・C++・分割ソースを必ず検査する。
    if args.config:
        requested = Path(args.config)
        if not requested.is_absolute():
            requested = BOOK_ROOT / requested
        volume_configs = [requested.resolve()]
    else:
        volume_configs = sorted(
            (BOOK_ROOT / "books").glob("*/publishing/book.json")
        )
    missing_configs = [path for path in volume_configs if not path.exists()]
    if missing_configs:
        for path in missing_configs:
            print(f"NG: volume config not found: {path}")
        return 1
    for volume_config in volume_configs:
        checks.extend(volume_manuscript_checks(python, volume_config))

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
