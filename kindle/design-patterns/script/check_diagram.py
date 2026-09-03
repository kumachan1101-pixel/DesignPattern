#!/usr/bin/env python3
"""クラス図の線が、掲載コードの実際の関係と合っているかを確かめる。

読者は図を見て構造を把握し、そのあとコードを読む。**図とコードが食い違うと、
読者は自分の読み方を疑うことになる。** UMLの書き方を間違えていれば、そこも
指摘される。この検査は、図の1本ずつをコードへ突き合わせる。

見る線は5種類。

  `<|--`  継承        コードに `class B : public A` があるか
  `<|..`  契約の実装   同上。ただし A が純粋仮想関数（`= 0`）だけを持つか
  `*--`   合成        A が B を値で持つか（メンバー、または値のコンテナ）
  `o--`   集約        A が B をポインタ・参照のコンテナで持つか
  `-->`   関連        A が B を参照・ポインタのメンバーで持つか

`..>`（一時的な依存）は引数・戻り値・ローカル変数を表し、クラス本体を見ても
確かめられないため対象にしない。

対象は実践章だけである。「はじめに」と第0章の図は、まだ題材を持たない仮の例
（「もしこうだったら」）を描く場所で、掲載コードと対にならない。実践章の中でも、
パターンの一般形（`Strategy <|.. ConcreteStrategyA`）は掲載コードに1つも実体が
無いことで見分け、対象から外す。

    python3 script/check_diagram.py --config books/<冊>/publishing/book.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]

RELATION = re.compile(r"^\s*(\w+)\s*(<\|--|<\|\.\.|\*--|o--|-->|\.\.>)\s*(\w+)")


def class_bodies(code: str) -> dict[str, str]:
    """クラス名 → 本体。波括弧の対応を数えて切り出す。"""
    bodies: dict[str, str] = {}
    for match in re.finditer(r"\b(?:class|struct)\s+(\w+)[^{;]*\{", code):
        name = match.group(1)
        depth, index = 1, match.end()
        while index < len(code) and depth:
            if code[index] == "{":
                depth += 1
            elif code[index] == "}":
                depth -= 1
            index += 1
        # 同名が複数回出るときは、最も長い定義（＝完成形）を採る。
        body = code[match.end(): index - 1]
        if len(body) > len(bodies.get(name, "")):
            bodies[name] = body
    return bodies


def holds_by_value(body: str, other: str) -> bool:
    """値で持っているか。メンバー宣言、または値のコンテナ。"""
    if re.search(rf"^\s*(?:const\s+)?{other}\s+\w+\s*(?:=[^;]*)?;", body, re.M):
        return True
    return bool(re.search(rf"(?:vector|map|deque|list)\s*<[^>]*\b{other}\b[^>*]*>\s*\w+\s*;",
                          body))


def holds_by_reference(body: str, other: str) -> bool:
    """参照・ポインタで持っているか。コンテナ越しも含む。"""
    if re.search(rf"^\s*(?:const\s+)?{other}\s*[*&]\s*\w+\s*;", body, re.M):
        return True
    if re.search(rf"(?:vector|map|deque|list)\s*<[^>]*\b{other}\s*\*", body):
        return True
    return bool(re.search(rf"reference_wrapper\s*<[^>]*\b{other}\b", body))


def is_contract(body: str) -> bool:
    """純粋仮想関数だけを持つか（データメンバーと実装を持たない）。"""
    if "= 0;" not in body:
        return False
    implemented = re.findall(r"\)\s*(?:const\s*)?(?:override\s*)?\{", body)
    return len(implemented) == 0


def check(config_path: Path) -> int:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    checked = 0

    for name in data.get("chapters", []):
        path = BOOK_ROOT / name
        if not path.exists():
            continue
        # 実践章だけを見る。「はじめに」と第0章の図は、まだ題材を持たない
        # 仮の例（「もしこうだったら」）を描く場所で、掲載コードと対にならない。
        if not re.search(r"chapter0[1-9]", path.name):
            continue
        text = path.read_text(encoding="utf-8")

        # 図は、同じフェーズに載っているコードと対で読む。フェーズ1の図は現状
        # コードを、フェーズ7の完成図は完成コードを指す。ここを混ぜると、
        # 同名クラスの別バージョンと突き合わせて誤検出になる。
        marks = [0] + [m.start() for m in re.finditer(r"^## [🔵🟣🟠🟡🔴🟢]", text, re.M)]
        marks.append(len(text))

        def phase_code(position: int) -> str:
            start = max(m for m in marks if m <= position)
            end = min((m for m in marks if m > position), default=len(text))
            return "\n".join(re.findall(r"```cpp\n(.*?)```", text[start:end], re.S))

        for diagram in re.finditer(r"```mermaid\nclassDiagram\n(.*?)```", text, re.S):
            code = phase_code(diagram.start())
            bodies = class_bodies(code)
            inherits = set(
                re.findall(r"\bclass\s+(\w+)\s*:\s*public\s+(\w+)", code)
            )
            lines = diagram.group(1).split("\n")
            names = {m.group(1) for m in (RELATION.match(l) for l in lines) if m}
            names |= {m.group(3) for m in (RELATION.match(l) for l in lines) if m}
            # 掲載コードに1つも実体が無い図は、パターンの一般形とみなす。
            if names and not (names & set(bodies)):
                continue

            for line in lines:
                found = RELATION.match(line)
                if not found:
                    continue
                base, relation, derived = found.groups()
                if relation == "..>":
                    continue
                checked += 1

                if relation in {"<|--", "<|.."}:
                    if (derived, base) not in inherits:
                        failures.append(
                            f"{path.name}: 図は `{base} {relation} {derived}` ですが、"
                            f"コードに `class {derived} : public {base}` がありません"
                        )
                        continue
                    contract = is_contract(bodies.get(base, ""))
                    if relation == "<|.." and not contract:
                        failures.append(
                            f"{path.name}: `{base}` は実装を持つので、点線（`<|..`）ではなく"
                            f"実線（`<|--`）です"
                        )
                    if relation == "<|--" and contract:
                        failures.append(
                            f"{path.name}: `{base}` は純粋仮想関数だけなので、実線（`<|--`）"
                            f"ではなく点線（`<|..`）です"
                        )
                    continue

                body = bodies.get(base)
                if body is None:
                    failures.append(
                        f"{path.name}: 図に出る `{base}` の定義が、掲載コードにありません"
                    )
                    continue
                value = holds_by_value(body, derived)
                reference = holds_by_reference(body, derived)

                if relation == "*--" and not value:
                    failures.append(
                        f"{path.name}: 図は `{base} *-- {derived}`（値で所有）ですが、"
                        f"`{base}` は `{derived}` を値で持っていません"
                    )
                if relation == "o--" and not reference:
                    failures.append(
                        f"{path.name}: 図は `{base} o-- {derived}`（共有集約）ですが、"
                        f"`{base}` は `{derived}` を参照・ポインタで持っていません"
                    )
                if relation == "-->" and not (value or reference):
                    failures.append(
                        f"{path.name}: 図は `{base} --> {derived}`（関連）ですが、"
                        f"`{base}` のメンバーに `{derived}` がありません"
                    )
                if relation == "-->" and value and not reference:
                    failures.append(
                        f"{path.name}: `{base}` は `{derived}` を値で持つので、"
                        f"矢印（`-->`）ではなく黒ひし形（`*--`）です"
                    )

    if failures:
        print("\n".join(sorted(set(failures))))
        print(f"\nFAILED: {len(set(failures))} diagram issue(s) in {config_path.name}")
        return 1
    print(f"OK: クラス図の線 {checked} 本が、掲載コードの関係と一致します")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = BOOK_ROOT / config_path
    return check(config_path)


if __name__ == "__main__":
    sys.exit(main())
