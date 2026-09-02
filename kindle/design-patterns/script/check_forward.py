#!/usr/bin/env python3
"""上から1回だけ読む読者にとっての「前方参照」を洗い出す。

読者は本を上から順に1回だけ読む。そのため、まだ読んでいない先の内容が前提に
なっている説明は、その場では理解できない。この検査は冊全体を1本の文字列として
連結し、次の2つを見る。

  P1 識別子の前方参照
      本文が `Xxx` を挙げているのに、その定義（コード上の `class Xxx` /
      `struct Xxx` / `enum` 値 / メソッド宣言）が、そこより後ろにしか無い。
      直前に「次の節で」「これから」「後で」などの予告があるものは除く。

  P2 節番号の前方参照
      本文が「4-3（…）」のように後ろの節を指し、しかもそれが予告ではなく
      根拠として使われている（「〜で確認したとおり」「〜で見た」）。

冊としてつながっているかを見るため、`book.json` の `chapters` の順に連結する。
第0章が第1章のクラスを説明なしで使えば、それはここで落ちる。

    python3 script/check_forward.py --config books/<冊>/publishing/book.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]

# 「これから出てくる」と断ってあれば前方参照ではない。
PROMISE = re.compile(
    r"(?:次の[節章項]|この[あと後]|後ほど|後で|これから|以降|"
    r"第\d+章で|フェーズ\d で|フェーズ\d で|説明します|扱います|見ます|確認します|"
    r"用意します|決めます|作ります|導入します|定義します)"
)

# 本書がC++の標準・言語機能として使う語。定義は本書に無いので対象外。
STDLIB = {
    "Order", "Design", "Patterns", "Gang", "Four", "Type", "Lightning",
    "Java", "Python", "TypeScript", "Kindle", "Makefile", "README",
    "Strategy", "State", "Observer", "Adapter", "Mediator", "Proxy",
    "Facade", "Command", "Decorator", "Template", "Method", "Factory",
    "Premium", "Regular", "Email", "Chat", "Dashboard", "SMS",
}


def load(config_path: Path) -> list[tuple[str, str]]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    result = []
    for name in data.get("chapters", []):
        path = BOOK_ROOT / name
        if path.exists():
            result.append((path.name, path.read_text(encoding="utf-8")))
    return result


def segments(text: str):
    """(種別, 内容, 行番号) を返す。種別は code / prose。"""
    lines = text.split("\n")
    index = 0
    while index < len(lines):
        if lines[index].startswith("```"):
            start = index
            index += 1
            body = []
            while index < len(lines) and not lines[index].startswith("```"):
                body.append(lines[index])
                index += 1
            index += 1
            yield ("code", "\n".join(body), start + 1)
            continue
        yield ("prose", lines[index], index + 1)
        index += 1


def check(config_path: Path) -> int:
    chapters = load(config_path)
    if not chapters:
        print(f"FAILED: {config_path} に章がありません")
        return 1

    # 冊全体を通した位置。定義位置と初出位置を同じ物差しで比べる。
    position = 0
    defined_at: dict[str, tuple[int, str, int]] = {}
    prose_uses: list[tuple[str, int, str, int, str]] = []

    for name, text in chapters:
        for kind, body, line in segments(text):
            position += 1
            if kind == "code":
                for identifier in re.findall(
                    r"\b(?:class|struct|enum)\s+(\w+)", body
                ):
                    defined_at.setdefault(identifier, (position, name, line))
                # enum 値と、クラス内で宣言されるメソッド名も定義とみなす。
                for enum_body in re.findall(r"enum\s+\w*\s*\{([^}]*)\}", body, re.S):
                    for value in re.findall(r"\b([A-Z][A-Z_0-9]{2,})\b", enum_body):
                        defined_at.setdefault(value, (position, name, line))
                for method in re.findall(r"\b(\w+)\s*\([^)]*\)\s*(?:const\s*)?[{;]", body):
                    defined_at.setdefault(method, (position, name, line))
                # 図に描かれたノード名は、読者がその場で目にしている。
                for node in re.findall(r"[\[(<{]+\s*\"?([A-Za-z_]\w{3,})", body):
                    defined_at.setdefault(node, (position, name, line))
                continue
            for identifier in re.findall(r"`([A-Za-z_][\w:]*)", body):
                identifier = identifier.split("::")[0]
                if len(identifier) < 4 or identifier in STDLIB:
                    continue
                if not re.match(r"^[A-Z][A-Za-z]|^[A-Z_]{3,}$", identifier):
                    continue
                prose_uses.append((identifier, position, name, line, body))

    failures: list[str] = []
    reported: set[str] = set()
    for identifier, position, name, line, body in prose_uses:
        record = defined_at.get(identifier)
        if record is None or record[0] <= position:
            continue
        if identifier in reported:
            continue
        if PROMISE.search(body):
            continue
        # 本書の慣例で「初出がそのまま紹介になる」形は、前方参照として扱わない。
        #   1. クラス一覧表の行（`X` | 役割 | 担当する仕様）
        #   2. 「ここで確認するコード：`X`」の直後にそのコードが続く
        #   3. `X.h` のようにファイル名として挙げる
        introduced = (
            # クラス一覧表・変更一覧表の行
            # 表の行。本書では、表が役割つきで名前を導入する場所になっている。
            (body.lstrip().startswith("|")
             and "`" + identifier in body)
            # 「ここで確認するコード：`X`」の直後にコードが続く
            or "ここで確認するコード" in body
            or "変更前から抜き出す箇所" in body
            # `X.h` のようにファイル名として挙げる
            or re.search(r"`" + re.escape(identifier) + r"\.(?:h|cpp)`", body)
            # 完成コード前のクラス一覧（箇条書きで名前だけを並べる）
            or re.match(r"^\s*[-*]\s*(?:`[\w:()]+`[、,]?\s*)+$", body.strip())
            # 「第N章」と断って先の章のものを指す
            or re.search(r"第\d+章", body)
            # 「◯◯（`X`）」——括弧の前に3文字以上の日本語で役割を書いてある
            or re.search(
                r"[^\s（(]{3,}[（(]\s*`" + re.escape(identifier) + r"`\s*[）)]", body
            )
            # 「〜する `X`」——直前が役割を述べる修飾句になっている
            or re.search(
                r"[ぁ-んァ-ヶ一-龠]{2,}"
                r"(?:する|した|される|を表す|を持つ|を受け持つ|受け持つ|担う|専用の|新しい|積む|返す|扱う|置く)"
                r"\s*`" + re.escape(identifier) + r"`",
                body,
            )
            # 「`X` という〜」
            or re.search(r"`" + re.escape(identifier) + r"`\s*という", body)
            # フェーズ6の構想行。ここで主要クラス名を先に置き、
            # 直後の要点コードで同じ順に確認する、という書き方をしている。
            or "システム全体での設計判断" in body
            or "構想上のコード経路" in body
        )
        if introduced:
            # 紹介された時点で既知とする。以降の言及は前方参照ではない。
            reported.add(identifier)
            continue
        reported.add(identifier)
        failures.append(
            f"{name}:{line}: `{identifier}` を説明なしで使っていますが、"
            f"定義が出るのは {record[1]}:{record[2]} です"
            f"（本文: {body.strip()[:60]}）"
        )

    # P2 後ろの節を根拠として引く
    for name, text in chapters:
        chapter_sections = [
            re.sub(r"^#+\s*", "", l).split("（")[0].strip()
            for l in text.split("\n") if re.match(r"^#{3}\s*\d-\d", l)
        ]
        order = {s: i for i, s in enumerate(chapter_sections)}
        current = None
        for number, line in enumerate(text.split("\n"), 1):
            heading = re.match(r"^#{3}\s*(\d-\d)", line)
            if heading:
                current = order.get(heading.group(1))
                continue
            if current is None or line.startswith(("|", ">", "```")):
                continue
            for cited in re.findall(
                r"(\d-\d)[^\n]{0,30}?(?:で確認したとおり|で見たとおり|で決めたとおり"
                r"|で確定したとおり)", line
            ):
                target = order.get(cited)
                if target is not None and target > current:
                    failures.append(
                        f"{name}:{number}: まだ読んでいない {cited} を根拠として"
                        f"引いています（本文: {line.strip()[:60]}）"
                    )

    if failures:
        print("\n".join(failures))
        print(f"\nFAILED: {len(failures)} forward reference(s) in {config_path.name}")
        return 1
    print(f"OK: {len(chapters)}ファイルを上から読んで、前方参照はありません")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = BOOK_ROOT / config_path
    if not config_path.exists():
        print(f"FAILED: {config_path} がありません")
        return 1
    return check(config_path)


if __name__ == "__main__":
    sys.exit(main())
