#!/usr/bin/env python3
"""Normalize C++ presentation inside the book's Markdown files.

This formatter changes presentation only.  It keeps the C++ token sequence intact,
adds semantic blank lines, and separates multiple top-level type definitions into
individual fenced blocks so each type has a visible reading boundary.
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
FILES = [
    OUTPUT / "chapter00_1.md",
    OUTPUT / "chapter00_2.md",
    OUTPUT / "chapter01.md",
    OUTPUT / "chapter02.md",
    OUTPUT / "chapter03.md",
    OUTPUT / "chapter04.md",
    OUTPUT / "chapter05.md",
    OUTPUT / "chapter06.md",
    OUTPUT / "chapter07.md",
    OUTPUT / "chapter08.md",
    OUTPUT / "chapter09_2.md",
    OUTPUT / "chapter10.md",
    OUTPUT / "chapter11.md",
    OUTPUT / "chapter12.md",
]
CORE_FILES = {path.name for path in FILES if path.name not in {
    "chapter00_1.md", "chapter00_2.md"
}}
FILE_LAYOUT_NOTE = (
    "> **掲載用1ファイルと実務の分割：** この1つの`.cpp`は、手元で動かすための掲載形式です。"
    "実務では、第0章「掲載ブロックと実ファイルの分け方」に従い、公開する契約・宣言を`.h`、"
    "処理本体を`.cpp`、生成・登録・注入を`main.cpp`へ置くことを基本にします。\n"
)

CPP_FENCE = re.compile(r"```cpp\s*\n(.*?)```", re.S)
TOP_LEVEL_TYPE = re.compile(
    r"(?m)^(?:class|struct|enum\s+class)\s+([A-Za-z_]\w*)"
)
ONE_LINE_GUARD = re.compile(r"^if\s*\(.*\)\s*(?:return|continue|break)\b.*;$")
CONTROL_START = re.compile(r"^(?:if|for|while|switch)\s*\(")


def indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def normalize_blank_lines(code: str) -> str:
    """Put a blank line at a change of intent without spacing every statement."""
    source = [line.rstrip() for line in code.strip("\n").split("\n")]
    compact: list[str] = []
    for line in source:
        if not line.strip() and compact and not compact[-1].strip():
            continue
        compact.append(line)

    result: list[str] = []
    for index, line in enumerate(compact):
        result.append(line)
        if not line.strip():
            continue

        next_index = index + 1
        while next_index < len(compact) and not compact[next_index].strip():
            next_index += 1
        if next_index >= len(compact) or next_index != index + 1:
            continue

        current = line.strip()
        following_line = compact[next_index]
        following = following_line.strip()
        same_indent = indentation(line) == indentation(following_line)
        add_blank = False

        # A completed judgment/loop and the following action are separate stages.
        if current == "}" and same_indent:
            if not following.startswith(("else", "catch", "while", "case ", "default:", "}", ");", ";")):
                add_blank = True

        # Keep consecutive guard clauses together, then separate the normal path.
        if ONE_LINE_GUARD.match(current) and same_indent:
            if not ONE_LINE_GUARD.match(following):
                add_blank = True

        # Separate setup/mutation from a new decision or loop at the same depth.
        if current.endswith(";") and same_indent and CONTROL_START.match(following):
            if not current.startswith(("if ", "for ", "while ")):
                add_blank = True

        # A final result is visually distinct from the work used to produce it.
        if following.startswith("return ") and same_indent:
            if current not in {"{", "}"} and not current.startswith(("if ", "else", "return ", "//")):
                add_blank = True

        if add_blank:
            result.append("")

    while result and not result[-1].strip():
        result.pop()
    return "\n".join(result) + "\n"


def type_boundary(code: str, start: int) -> int:
    """Attach contiguous comments immediately above a type to that type."""
    boundary = code.rfind("\n", 0, start) + 1
    cursor = boundary
    while cursor > 0:
        previous_end = cursor - 1
        previous_start = code.rfind("\n", 0, previous_end) + 1
        previous = code[previous_start:previous_end].strip()
        if not previous or previous.startswith("//"):
            cursor = previous_start
            continue
        break
    return cursor


def split_top_level_types(code: str) -> str:
    """Create one fenced block per top-level class/struct/enum definition."""
    matches = list(TOP_LEVEL_TYPE.finditer(code))
    if len(matches) < 2:
        return code

    boundaries = [type_boundary(code, match.start()) for match in matches]
    units: list[tuple[str | None, str]] = []

    prelude = code[:boundaries[0]]
    if prelude.strip():
        units.append((None, prelude))

    for index, match in enumerate(matches):
        start = boundaries[index]
        end = boundaries[index + 1] if index + 1 < len(boundaries) else len(code)
        units.append((match.group(1), code[start:end]))

    rendered: list[str] = []
    for index, (name, unit) in enumerate(units):
        unit = unit.strip("\n") + "\n"
        if index == 0:
            rendered.append(unit)
            continue
        label = name or "共通宣言"
        rendered.append(
            "```\n\n"
            f"**{label}**\n\n"
            f"このブロックでは `{label}` の定義だけを確認します。\n\n"
            "```cpp\n"
            + unit
        )
    return "".join(rendered)


def preserve_unchanged_line_endings(original: str, rendered: str) -> str:
    """Reuse the exact newline bytes for lines whose content did not change."""
    old_lines = original.splitlines(keepends=True)
    new_lines = rendered.splitlines(keepends=True)
    old_content = [line.rstrip("\r\n") for line in old_lines]
    new_content = [line.rstrip("\r\n") for line in new_lines]
    result = [content + "\n" for content in new_content]
    if result and not rendered.endswith(("\n", "\r")):
        result[-1] = new_content[-1]

    matcher = difflib.SequenceMatcher(a=old_content, b=new_content, autojunk=False)
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag != "equal":
            continue
        for offset in range(new_end - new_start):
            result[new_start + offset] = old_lines[old_start + offset]
    return "".join(result)


def rewrite_file(path: Path, from_head: bool = False) -> bool:
    if from_head:
        repository = ROOT.parents[1]
        relative = path.relative_to(repository).as_posix()
        original_bytes = subprocess.check_output(
            ["git", "show", f"HEAD:{relative}"], cwd=repository
        )
    else:
        original_bytes = path.read_bytes()
    original = original_bytes.decode("utf-8")

    def replace(match: re.Match[str]) -> str:
        code = normalize_blank_lines(match.group(1))
        code = split_top_level_types(code)
        rendered = "```cpp\n" + code + "```"
        return preserve_unchanged_line_endings(match.group(0), rendered)

    updated = CPP_FENCE.sub(replace, original)
    if path.name in CORE_FILES and FILE_LAYOUT_NOTE not in updated:
        run_note = re.compile(
            r"(> \*\*手元で動かすには\*\*\r?\n> [^\r\n]+(?:\r?\n))"
        )
        updated, count = run_note.subn(
            lambda match: match.group(1) + ">\n" + FILE_LAYOUT_NOTE,
            updated,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"手元で動かすにはの注記を追加できません: {path.name}")
    rendered = updated.encode("utf-8")
    if rendered == original_bytes:
        return False
    # Prose outside a changed code fence retains its original newline bytes.
    # Newly rendered code uses LF so added lines pass git's whitespace check.
    path.write_bytes(rendered)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-head",
        action="store_true",
        help="rebuild the presentation from the committed manuscript",
    )
    args = parser.parse_args()
    changed = [
        path.name for path in FILES if rewrite_file(path, from_head=args.from_head)
    ]
    print(f"normalized: {len(changed)} files")
    for name in changed:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
