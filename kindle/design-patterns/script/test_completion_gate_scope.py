#!/usr/bin/env python3
"""分冊の本文検査が通常ゲートと単冊ゲートから外れないことを確認する。"""

from pathlib import Path

import run_completion_gate as gate


def main() -> int:
    config = Path("books/sample/publishing/book.json")
    checks = gate.volume_manuscript_checks("python", config)
    commands = {label: command for label, command in checks}

    required_scripts = {
        "check_volume.py",
        "check_code_runs.py",
        "check_execution_output.py",
        "check_representative_run.py",
        "check_unused_cpp_inputs.py",
        "check_mermaid.py",
        "check_diagram.py",
        "check_layout.py",
        "check_forward.py",
        "check_flow.py",
        "check_anchor.py",
        "export_sources.py",
    }
    actual_scripts = {Path(command[1]).name for command in commands.values()}
    missing = sorted(required_scripts - actual_scripts)
    if missing:
        print("FAILED: 分冊の通常ゲートから検査が欠落: " + ", ".join(missing))
        return 1

    for label, command in checks:
        if "--config" not in command or str(config) not in command:
            print(f"FAILED: {label} が対象book.jsonを受け取っていません")
            return 1
        if "release_artifact.py" in " ".join(command):
            print(f"FAILED: 通常本文ゲートへ出版成果物検査が混入: {label}")
            return 1

    print(f"OK: 分冊本文の必須検査 {len(checks)} 件が通常ゲート対象です")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
