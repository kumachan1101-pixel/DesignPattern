"""章内の節番号参照へ、その節の名前を初出で併記する（EDIT-006）。

裸の `5-3` だけでは何の話か思い出せず、読者が節を行き来することになる。
各章・各フェーズの中で最初に現れた参照へ `5-3（課題IDと接続点を確定する）`
の形で節名を足す。2回目以降は直前に名前を見ているので番号だけにする。

節名は各章の見出し `### 5-3：…` から取る。同じ章に見出しが無い番号は、
全章で共通する名前を使う。コードブロック・見出し・表の中は書き換えない。
"""
from __future__ import annotations
import re, sys, collections
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
REF = re.compile(r'(?<![0-9A-Za-z])([1-7]-[1-9][a-z]?)(?![0-9])')
HEAD = re.compile(r'(?m)^#{3}\s*([1-7]-[1-9][a-z]?)：(.+?)\s*$')
PHASE = re.compile(r'^## ')


def global_names() -> dict[str, str]:
    """全章の見出しから、最も多い節名を拾う。"""
    tally: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for p in sorted(OUT.glob("chapter*.md")):
        text = p.read_bytes().decode("utf-8")
        for m in HEAD.finditer(text):
            tally[m.group(1)][m.group(2)] += 1
    return {k: _short(c.most_common(1)[0][0]) for k, c in tally.items()}


def _short(name: str) -> str:
    """節名の末尾の補足括弧を落とす。`実装コード（現状）` は入れ子になる。"""
    return re.sub(r"（[^（）]*）\s*$", "", name).strip() or name


def annotate(text: str, names: dict[str, str]) -> tuple[str, int]:
    """フェーズごとに初出の参照へ節名を足す。戻り値は(新本文, 追加数)。"""
    local = {m.group(1): _short(m.group(2)) for m in HEAD.finditer(text)}
    lines = text.split("\n")
    seen: set[str] = set()
    added = 0
    in_code = False
    for i, line in enumerate(lines):
        bare = line.rstrip("\r")
        if bare.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if PHASE.match(bare):        # フェーズが変わったら初出を数え直す
            seen.clear()
            continue
        if bare.startswith("#") or bare.startswith("|") or bare.startswith(">"):
            continue                 # 見出し・表・引用は触らない
        out = []
        last = 0
        for m in REF.finditer(bare):
            num = m.group(1)
            nxt = bare[m.end():m.end() + 1]
            if num in seen or nxt in ("：", "（"):
                continue
            name = local.get(num) or names.get(num)
            if not name:
                continue
            # 直後に節名と同じ語が続くなら重複するので足さない
            tail = bare[m.end():m.end() + 14]
            if name[-4:] in tail or name[:4] in tail:
                seen.add(num)
                continue
            seen.add(num)
            out.append(bare[last:m.end()] + f"（{name}）")
            last = m.end()
            added += 1
        if out:
            eol = "\r" if line.endswith("\r") else ""
            lines[i] = "".join(out) + bare[last:] + eol
    return "\n".join(lines), added


def main() -> int:
    apply = "--apply" in sys.argv
    names = global_names()
    total = 0
    for p in sorted(OUT.glob("chapter*.md")):
        raw = p.read_bytes()
        text = raw.decode("utf-8")
        new, added = annotate(text, names)
        total += added
        if added:
            print(f"{p.name:16} +{added}")
            if apply:
                p.write_bytes(new.encode("utf-8"))
    print(f"\n合計 {total} 箇所{'へ節名を併記した' if apply else '（--apply で反映）'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
