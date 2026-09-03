#!/usr/bin/env python3
"""掲載コードの長い行を、狙った位置で折り返す。

コード画像は幅2000px・48pxの等幅フォントで組まれ、**64桁を超えると勝手に
折り返される。** 折り返しの位置は選べないので、`= 0;` だけが次の行へ落ちる
ような読みにくい割れ方をする。

そこで、あらかじめ意味の切れ目で改行しておく。切れ目は次の順で探す。

  1. 引数・パラメータの区切り（`,` の直後）――次の行は開き括弧へ揃える
  2. 出力の連結（` << ` の直前）――次の行は最初の `<<` へ揃える
  3. 論理演算子（` && ` / ` || ` の直後）――条件の頭へ揃える
  4. 1行に収めた関数本体（`{ return ...; }`）――中身を次の行へ出す
  5. 文字列の連結（` + ` の直前）――最初の被演算子へ揃える
  6. 末尾の行コメント（` // `）――コメントを前の行へ出す
  7. 代入（` = ` の直後）――右辺を次の行へ落とす
  8. 初期化子リスト（` : ` の直前）――コンストラクタ本体の前で折る

どれも見つからない行は触らない。**無理に割ると、かえって読みにくくなる。**

    python3 script/wrap_code.py <ファイル...> [--limit 64] [--apply]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def split_at_commas(line: str, limit: int) -> list[str] | None:
    """引数の区切りで折る。次の行は開き括弧の直後へ揃える。"""
    open_at = line.find("(")
    if open_at < 0 or open_at >= limit:
        return None
    align = " " * (open_at + 1)
    # 括弧の深さが1のカンマだけを切れ目にする。
    breaks, depth = [], 0
    for index, char in enumerate(line):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 1:
            breaks.append(index + 1)
    if not breaks:
        return None
    out, start = [], 0
    for position in breaks:
        head = line[start:position]
        candidate = (out and align + head.lstrip()) or head
        if len(candidate) > limit and out:
            return None
        if len(line[start:]) + (0 if not out else len(align)) <= limit:
            break
        out.append(candidate.rstrip())
        start = position
    tail = line[start:].lstrip()
    if not out or not tail:
        return None
    out.append(align + tail)
    return out if all(len(l) <= limit for l in out) else None


def split_at_streams(line: str, limit: int) -> list[str] | None:
    """`<<` の前で折る。次の行は最初の `<<` の位置へ揃える。"""
    first = line.find("<<")
    if first < 0:
        return None
    align = " " * first
    parts = [p for p in re.split(r"(?=<<)", line) if p]
    out, current = [], ""
    for part in parts:
        candidate = current + part
        head = candidate if not out else align + candidate.lstrip()
        if len(head.rstrip()) > limit and current.strip():
            out.append((current if not out else align + current.lstrip()).rstrip())
            current = part
        else:
            current = candidate
    if not out:
        return None
    out.append((align + current.lstrip()).rstrip())
    return out if all(len(l) <= limit for l in out) else None


def split_at_logic(line: str, limit: int) -> list[str] | None:
    """`&&` / `||` の直後で折る。条件の頭へ揃える。"""
    open_at = line.find("(")
    if open_at < 0:
        return None
    align = " " * (open_at + 1)
    parts = re.split(r"(?<=&&)\s|(?<=\|\|)\s", line)
    if len(parts) < 2:
        return None
    out = [parts[0].rstrip()] + [align + p.strip() for p in parts[1:]]
    return out if all(len(l) <= limit for l in out) else None


def split_inline_body(line: str, limit: int) -> list[str] | None:
    """`... { return x; }` のように1行へ詰めた本体を、3行へ開く。"""
    found = re.match(r"^(\s*)(.*?)\s*\{\s*(.+?)\s*\}\s*$", line)
    if not found:
        return None
    indent, head, inner = found.groups()
    if "{" in inner or "}" in inner:
        return None
    out = [f"{indent}{head} {{", f"{indent}    {inner}", f"{indent}}}"]
    return out if all(len(l) <= limit for l in out) else None


def split_at_plus(line: str, limit: int) -> list[str] | None:
    """文字列の連結を ` + ` の前で折る。"""
    first = line.find(" + ")
    if first < 0:
        return None
    align = " " * (len(line) - len(line.lstrip()) + 4)
    parts = [p for p in re.split(r"(?= \+ )", line) if p]
    out, current = [], ""
    for part in parts:
        candidate = current + part
        head = candidate if not out else align + candidate.lstrip()
        if len(head.rstrip()) > limit and current.strip():
            out.append((current if not out else align + current.lstrip()).rstrip())
            current = part
        else:
            current = candidate
    if not out:
        return None
    out.append((align + current.lstrip()).rstrip())
    return out if all(len(l) <= limit for l in out) else None


def split_trailing_comment(line: str, limit: int) -> list[str] | None:
    """末尾の行コメントを、コードの上の行へ出す。"""
    found = re.match(r"^(\s*)(.+?)\s{2,}(//.*)$", line)
    if not found:
        return None
    indent, body, comment = found.groups()
    out = [f"{indent}{comment}", f"{indent}{body}"]
    return out if all(len(l) <= limit for l in out) else None


def split_at_assign(line: str, limit: int) -> list[str] | None:
    """代入の右辺を次の行へ落とす。"""
    found = re.match(r"^(\s*)(.+?=)\s+(.+)$", line)
    if not found or "==" in line:
        return None
    indent, head, tail = found.groups()
    out = [f"{indent}{head}", f"{indent}    {tail}"]
    return out if all(len(l) <= limit for l in out) else None


def split_at_init_list(line: str, limit: int) -> list[str] | None:
    """コンストラクタの初期化子リストの前で折る。"""
    found = re.match(r"^(\s*)(.+?\))\s*(:\s*.+)$", line)
    if not found:
        return None
    indent, head, tail = found.groups()
    out = [f"{indent}{head}", f"{indent}        {tail}"]
    return out if all(len(l) <= limit for l in out) else None


def wrap(line: str, limit: int) -> list[str]:
    if len(line) <= limit or line.strip().startswith("//"):
        return [line]
    for splitter in (split_trailing_comment, split_at_commas, split_at_streams,
                     split_at_logic, split_inline_body, split_at_plus,
                     split_at_init_list, split_at_assign):
        result = splitter(line, limit)
        if result:
            return result
    return [line]


def process(path: Path, limit: int, apply: bool) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    changed = skipped = 0

    def replacement(match: re.Match[str]) -> str:
        nonlocal changed, skipped
        out = []
        for line in match.group(1).split("\n"):
            wrapped = wrap(line, limit)
            if len(wrapped) > 1:
                changed += 1
            elif len(line) > limit and not line.strip().startswith("//"):
                skipped += 1
            out.extend(wrapped)
        return "```cpp\n" + "\n".join(out) + "```"

    updated = re.sub(r"```cpp\n(.*?)```", replacement, text, flags=re.S)
    if apply and updated != text:
        path.write_text(updated, encoding="utf-8")
    return changed, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--limit", type=int, default=64)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    total_changed = total_skipped = 0
    for name in args.files:
        changed, skipped = process(Path(name), args.limit, args.apply)
        total_changed += changed
        total_skipped += skipped
        print(f"{Path(name).name}: 折り返し {changed}行 / 切れ目が無く据え置き {skipped}行")
    print(f"\n合計 折り返し {total_changed}行 / 据え置き {total_skipped}行"
          f"{'（--apply で反映）' if not args.apply else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
