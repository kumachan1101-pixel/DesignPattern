#!/usr/bin/env python3
"""分冊が1冊として成立しているかを検査する（SHRINK-001）。

`validate_book.py` は `output/` の章ファイル名（chapter01.md 〜 chapter12.md）へ
規則を紐づけているため、章を選び直して番号を振り直した分冊には当てられない。
こちらは冊の構成を `book.json` から読み、**冊をまたいだときに壊れるもの**だけを見る。

検査するもの:
  1. 収録していない章番号を本文が参照していない
  2. 「〜章で説明した」「〜の3つの原則」の参照先が、その冊の中に実在する
  3. 存在しない節への前方参照がない（「〜の項で示します」）
  4. 掲載コードで例示するクラス名が、その冊の中に実在する
  5. 見出しの最上位レベルが全ファイルでそろっている（EPUB目次の階層）
  6. 「N つ目です」に受け皿がある（2つ目・3つ目、または分類の定義）
  7. 「N つの辛い状況」「変更した定義はN つ」が直後の表の行数と一致する
  8. 実行結果のシナリオラベルの形が、冊の中でそろっている
  9. 完成後のクラス図と完成コードのクラス集合が一致する（省略には理由を書く）
 10. 各章で繰り返し使う語が、用語集に定義されている
 11. 各章で使うC++記法が、はじめに・第0章で説明されている
 12. Mermaid図の前に目的が1文あり、後に読み取り結論がある
 13. クラス図の関係線が、第0章の規約6種（と、その矢先つき表記）に収まる
 14. 同じクラスの組が、章の中で違う線で描かれていない
 15. 掲載コードが値で持つ関係は、白ひし形ではなく黒ひし形で描かれている
 16. 実践章の全部に同じ読み方の指示が繰り返されていない
 17. 表のセルに文が入っていない（6インチ端末で列が潰れる）
 18. コード行が表示幅80桁に収まる
 19. 図が横に広がりすぎていない（頁幅へ縮むと文字が読めなくなる）
 20. 変更影響グラフの箱が、第0章の規約4種のどれかになっている
 21. 第0章が挙げる章内の節名が、実践章の見出しと一致する
 22. 執筆用テンプレートの穴埋め記号が本文に残っていない
 23. 「第N章／はじめに で触れた○○」の話題が、その参照先に実在する
 24. 種類の違うID（問題・原因・課題）を等号で結んでいない
 25. 実践章のIDに、思い出すための短い名前が併記されている

    python3 script/check_volume.py --config books/<冊>/publishing/book.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


def display_width(text: str) -> int:
    """全角を2、半角を1として表示幅を数える。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WFA" else 1 for c in text)


BOOK_ROOT = Path(__file__).resolve().parents[1]

# 本文が参照しうる「まとまり」と、その所在を決める手がかり。
# 章番号以外の参照先（はじめに・おわりに）は、見出しの文字列で照合する。
UNIT_HEADINGS = {
    "はじめに": re.compile(r"^#\s*はじめに"),
    "おわりに": re.compile(r"^#\s*おわりに"),
}

# コードブロックと Mermaid を落としてから散文を見るための正規表現。
FENCE = re.compile(r"^```")


def load_config(path: Path) -> tuple[list[Path], str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    chapters = [BOOK_ROOT / c for c in data.get("chapters", [])]
    return chapters, data.get("metadata", {}).get("title", "")


def prose_lines(text: str) -> list[tuple[int, str]]:
    """コードブロックの外にある行だけを (行番号, 本文) で返す。"""
    out: list[tuple[int, str]] = []
    in_fence = False
    for number, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append((number, line))
    return out


def chapter_numbers(paths: list[Path]) -> set[int]:
    """収録章が名乗っている章番号を、本文の見出しから読む。"""
    numbers: set[int] = set()
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^#{1,2}\s*第(\d+)章", line)
            if match:
                numbers.add(int(match.group(1)))
                break
    return numbers


def declared_class_names(paths: list[Path]) -> set[str]:
    """掲載コードが定義しているクラス・構造体・名前空間の名前。"""
    names: set[str] = set()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        names.update(re.findall(r"\b(?:class|struct|namespace)\s+([A-Za-z_]\w*)", text))
    return names


def table_rows_after(lines: list[str], start: int) -> int:
    """start 行以降で最初に現れる表の、見出し行を除いたデータ行数。"""
    index = start
    while index < len(lines) and not lines[index].lstrip().startswith("|"):
        if index - start > 12:
            return -1
        index += 1
    if index >= len(lines):
        return -1
    index += 2  # 見出し行と区切り行
    rows = 0
    while index < len(lines) and lines[index].lstrip().startswith("|"):
        rows += 1
        index += 1
    return rows


def check(config_path: Path) -> int:
    chapters, title = load_config(config_path)
    failures: list[str] = []

    missing = [p for p in chapters if not p.exists()]
    for path in missing:
        failures.append(f"book.json が指す {path} がありません")
    chapters = [p for p in chapters if p.exists()]
    if not chapters:
        print("FAILED: 収録原稿が1件もありません")
        return 1

    included = chapter_numbers(chapters)
    class_names = declared_class_names(chapters)
    units_present = set()
    for path in chapters:
        head = path.read_text(encoding="utf-8").splitlines()[:5]
        for unit, pattern in UNIT_HEADINGS.items():
            if any(pattern.match(line) for line in head):
                units_present.add(unit)

    for path in chapters:
        name = path.name
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        prose = prose_lines(text)

        # 1. 収録していない章番号への参照
        for number, line in prose:
            for referenced in re.findall(r"第(\d+)章", line):
                if int(referenced) not in included:
                    failures.append(
                        f"{name}:{number}: 収録していない第{referenced}章を参照しています"
                    )

        # 2. 参照先のまとまりが、この冊に実在するか
        for number, line in prose:
            for unit in re.findall(r"「(はじめに|おわりに)」で(?:説明|紹介)した", line):
                if unit not in units_present:
                    failures.append(
                        f"{name}:{number}: 「{unit}」を参照していますが、この冊にありません"
                    )

        # 3. 存在しない節への前方参照
        for number, line in prose:
            for section in re.findall(r"「([^」]{4,40})」の項で示します", line):
                if not re.search(rf"^#{{2,5}}\s*.*{re.escape(section)}", text, re.M):
                    failures.append(
                        f"{name}:{number}: 「{section}」の項を予告していますが、"
                        f"その見出しがありません"
                    )

        # 4. 例示クラス名の実在
        for number, line in prose:
            for cited in re.findall(r"代表具体`([A-Za-z_]\w*)`", line.replace(" ", "")):
                if cited not in class_names:
                    failures.append(
                        f"{name}:{number}: 例示クラス {cited} がこの冊に存在しません"
                    )

        # 6. 序数に受け皿があるか
        for number, line in prose:
            if re.search(r"この章は\d+つ目です", line):
                others = sum(
                    1
                    for other in chapters
                    for other_line in other.read_text(encoding="utf-8").splitlines()
                    if re.search(r"この章は\d+つ目です", other_line)
                )
                if others < 2:
                    failures.append(
                        f"{name}:{number}: 「N つ目です」が1件しかなく、"
                        f"読者が何と比べるか判断できません"
                    )

        # 7. 宣言した件数と表の行数
        for number, line in prose:
            match = re.search(r"変更した定義は(\d+)つです", line)
            if match:
                rows = table_rows_after(lines, number)
                if rows >= 0 and rows != int(match.group(1)):
                    failures.append(
                        f"{name}:{number}: 「変更した定義は{match.group(1)}つ」ですが、"
                        f"直後の表は {rows} 行です"
                    )
            match = re.search(r"(\d+)つの辛い状況", line)
            if match:
                stated = int(match.group(1))
                found = len(
                    re.findall(
                        r"^(\d+)つ目は",
                        "\n".join(lines[number : number + 40]),
                        re.M,
                    )
                )
                if found and found != stated:
                    failures.append(
                        f"{name}:{number}: 「{stated}つの辛い状況」ですが、"
                        f"「N つ目は」が {found} 件です"
                    )

    # 5. 見出しの最上位レベル
    top_levels = {}
    for path in chapters:
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^(#{1,3})\s+\S", line)
            if match:
                top_levels[path.name] = len(match.group(1))
                break
    if len(set(top_levels.values())) > 1:
        detail = ", ".join(f"{k}=h{v}" for k, v in sorted(top_levels.items()))
        failures.append(
            f"最上位の見出しレベルがそろっていません（{detail}）。"
            f"EPUBの目次が同じ階層に並びません"
        )

    # 8. 実行結果ラベルの形
    label_forms: dict[str, set[str]] = {}
    for path in chapters:
        text = path.read_text(encoding="utf-8")
        forms = set()
        for label in re.findall(r"^---[ \t]*(\S[^-\n]*?)[ \t]*---[ \t]*$", text, re.M):
            if re.match(r"行\d+[a-z]?[:：]", label):
                forms.add("行N: 説明")
            elif re.match(r"シナリオ\d+[:：]", label):
                forms.add("シナリオN: 説明")
            elif re.match(r"\d+回目", label):
                forms.add("N回目")
            else:
                forms.add("説明のみ")
        if forms:
            label_forms[path.name] = forms
    all_forms = set().union(*label_forms.values()) if label_forms else set()
    if len(all_forms) > 1:
        detail = "; ".join(f"{k}={sorted(v)}" for k, v in sorted(label_forms.items()))
        failures.append(
            f"実行結果のシナリオラベルが{len(all_forms)}通りに割れています（{detail}）。"
            f"読者は章ごとに読み方を切り替えることになります"
        )

    # 9. 完成後のクラス図と完成コード
    arrow = r"(?:<\|--|<\|\.\.|\*-->|o-->|\*--|o--|-->|\.\.>)"
    for path in chapters:
        text = path.read_text(encoding="utf-8")
        head = re.search(r"^####\s*完成後のクラス図\s*$", text, re.M)
        code = re.search(r"####\s*完成コード(.*?)(?=\n###\s|\n##\s)", text, re.S)
        if not head or not code:
            continue
        # 図は読みやすさのために複数枚へ分けることがある。節の中の全図を合わせて見る。
        section = text[head.end(): code.start()]
        drawn: set[str] = set()
        for diagram_source in re.findall(r"```mermaid\n(.*?)```", section, re.S):
            if "classDiagram" not in diagram_source:
                continue
            drawn |= set(re.findall(r"^\s*class\s+([A-Z]\w*)", diagram_source, re.M))
            drawn |= set(re.findall(rf"^\s*([A-Z]\w*)\s*{arrow}", diagram_source, re.M))
            drawn |= set(re.findall(rf"{arrow}\s*([A-Z]\w*)", diagram_source))
        diagram = type("S", (), {"group": lambda self, n: section})()
        written = set(re.findall(r"\b(?:class|struct)\s+([A-Z]\w*)", code.group(1)))
        undrawn = sorted(written - drawn)
        if undrawn and not re.search(r"省略|描いていません|載せていません|割愛", diagram.group(1)):
            failures.append(
                f"{path.name}: 完成コードの {', '.join(undrawn)} が完成後のクラス図に無く、"
                f"省略の理由も書かれていません"
            )

    # 10. 用語集の網羅
    guide = "\n".join(p.read_text(encoding="utf-8") for p in chapters[:2])
    glossary = re.search(r"本書で使う主要な言葉(.*?)\n\n", guide, re.S)
    if glossary:
        defined = set(re.findall(r"\*\*「([^」]+)」\*\*", glossary.group(1)))
        body = "\n".join(p.read_text(encoding="utf-8") for p in chapters[2:])
        for term in (
            "接続点", "契約", "具体", "骨格", "注入", "混在",
            "変わる側", "守る側", "変化軸",
        ):
            used = len(re.findall(term, body))
            if used >= 10 and term not in defined:
                failures.append(
                    f"実践章で {used} 回使う『{term}』が、用語集に定義されていません"
                )

    # 11. 未説明のC++記法
    guide_text = "\n".join(p.read_text(encoding="utf-8") for p in chapters[:2])
    body_text = "\n".join(p.read_text(encoding="utf-8") for p in chapters[2:])
    for label, pattern in (
        ("override", r"\boverride\b"),
        ("= default", r"=\s*default"),
        ("auto", r"\bauto\b"),
        ("std::reference_wrapper", r"reference_wrapper"),
        ("std::cref", r"std::cref"),
        ("namespace", r"\bnamespace\s+\w+"),
    ):
        if re.search(pattern, body_text) and not re.search(pattern, guide_text):
            count = len(re.findall(pattern, body_text))
            failures.append(
                f"実践章で {count} 回使う C++記法『{label}』が、"
                f"はじめに・第0章のどこにも説明されていません"
            )

    # 12. 図の前後の散文
    for path in chapters:
        lines = path.read_text(encoding="utf-8").split("\n")
        for index, line in enumerate(lines):
            if line.strip() != "```mermaid":
                continue
            before = index - 1
            while before >= 0 and lines[before].strip() == "":
                before -= 1
            if before < 0 or lines[before].lstrip().startswith(("#", "|", "```")):
                failures.append(
                    f"{path.name}:{index + 1}: 図の前に目的の1文がありません"
                    f"（直前が見出し・表・別のブロックです）"
                )
            after = index + 1
            while after < len(lines) and lines[after].strip() != "```":
                after += 1
            after += 1
            while after < len(lines) and lines[after].strip() == "":
                after += 1
            if after >= len(lines) or lines[after].lstrip().startswith(("#", "```")):
                failures.append(
                    f"{path.name}:{index + 1}: 図の後に読み取り結論がありません"
                )

    # 13〜15. クラス図の関係線
    allowed = {"<|--", "<|..", "*--", "o--", "-->", "..>", "*-->", "o-->"}
    edge_re = re.compile(
        r'^\s*(\w+)\s*("[\d.*]+"\s*)?'
        r'(<\|--|<\|\.\.|\*-->|o-->|\*--|o--|-->|\.\.>|\.\.\|>|--\|>)'
        r'\s*("[\d.*]+"\s*)?(\w+)'
    )
    for path in chapters:
        text = path.read_text(encoding="utf-8")
        seen: dict[tuple[str, str], set[str]] = {}
        for diagram in re.findall(r"```mermaid\n(.*?)```", text, re.S):
            if "classDiagram" not in diagram:
                continue
            for line in diagram.split("\n"):
                match = edge_re.match(line)
                if not match:
                    continue
                arrow, left, right = match.group(3), match.group(1), match.group(5)
                if arrow not in allowed:
                    failures.append(
                        f"{path.name}: 第0章の規約に無い関係線 {arrow} "
                        f"（{left} {arrow} {right}）。規約は "
                        f"<|-- / <|.. / *-- / o-- / --> / ..> と、その矢先つきです"
                    )
                    continue
                seen.setdefault((left, right), set()).add(arrow)
        for (left, right), arrows in seen.items():
            kinds = {a.replace("-->", "--").replace("..>", "..") for a in arrows}
            if len(kinds) > 1:
                failures.append(
                    f"{path.name}: {left} と {right} の関係が、章の中で "
                    f"{sorted(arrows)} と違う線で描かれています"
                )

    # 15. 値で持つ関係は黒ひし形
    for path in chapters:
        text = path.read_text(encoding="utf-8")
        owned: set[tuple[str, str]] = set()
        for holder in re.finditer(
            r"\b(?:class|struct)\s+([A-Z]\w*)\s*\{(.*?)\n\};", text, re.S
        ):
            body = holder.group(2)
            for member in re.finditer(
                r"(?:std::)?(?:vector|map|deque|set)<[^>]*?\b([A-Z]\w*)\s*>\s+\w+\s*;", body
            ):
                owned.add((holder.group(1), member.group(1)))
        for diagram in re.findall(r"```mermaid\n(.*?)```", text, re.S):
            if "classDiagram" not in diagram:
                continue
            for line in diagram.split("\n"):
                match = edge_re.match(line)
                if not match:
                    continue
                arrow, left, right = match.group(3), match.group(1), match.group(5)
                if arrow in ("o--", "o-->") and (left, right) in owned:
                    failures.append(
                        f"{path.name}: {left} は {right} を値で持っているのに、"
                        f"図では共有集約（{arrow}）です。第0章の規約では黒ひし形です"
                    )

    # 16. 実践章に繰り返される読み方の指示
    practice = [p for p in chapters if re.match(r"chapter\d", p.name)]
    if len(practice) >= 3:
        counter: dict[str, int] = {}
        for path in practice:
            body = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
            for sentence in {s.strip() for s in re.split(r"(?<=。)", body)}:
                if 15 < len(sentence) < 160 and not sentence.startswith(("|", "#", ">", "-", "*")):
                    counter[sentence] = counter.get(sentence, 0) + 1
        guides = ("上から順に", "コードを読むときは", "1つずつ、上から順に", "連結すれば")
        for sentence, times in counter.items():
            if times >= len(practice) and any(g in sentence for g in guides):
                failures.append(
                    f"読み方の指示「{sentence[:34]}」が実践章 {times} 本すべてにあります。"
                    f"第0章へ一度だけ置いてください"
                )

    # 17〜19. Kindleでの見え方
    for path in chapters:
        text = path.read_text(encoding="utf-8")
        if re.search(r"^>\s*\[!\w+\]", text, re.M) and False:
            pass  # コールアウトは build_epub 側で見出しへ変換する
        in_fence = False
        fence_lang = ""
        for number, line in enumerate(text.split("\n"), 1):
            if line.startswith("```"):
                fence_lang = line[3:].strip() if not in_fence else ""
                in_fence = not in_fence
                continue
            if in_fence:
                # Mermaidの原文は画像へ描き換わるので読者には見えない。
                # 読者が読むのはコードと実行結果だけ。
                if fence_lang not in ("cpp", ""):
                    continue
                if display_width(line) > 80:
                    failures.append(
                        f"{path.name}:{number}: コード行の表示幅が "
                        f"{display_width(line)} 桁です（80桁に収めてください）"
                    )
                continue
            if not line.strip().startswith("|") or re.match(r"^\|[\s:-]+\|", line):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            longest = max((display_width(c) for c in cells), default=0)
            if longest > 80:
                failures.append(
                    f"{path.name}:{number}: 表のセルが {longest} 桁あります。"
                    f"6インチ端末では列が潰れるので、表から外して書いてください"
                )

    # 19. 図の横幅
    for path in chapters:
        text = path.read_text(encoding="utf-8")
        for number, diagram in enumerate(
            re.findall(r"```mermaid\n(.*?)```", text, re.S), 1
        ):
            # 横に並ぶ要素が多いほど、頁幅へ縮めたときに文字が小さくなる。
            # クラス図は葉の数、シーケンス図は参加者の数で見る。
            if "classDiagram" in diagram:
                boxes = len(re.findall(r"^\s*class\s+\w+", diagram, re.M))
                limit, kind = 10, "クラス"
            elif "sequenceDiagram" in diagram:
                boxes = len(re.findall(r"^\s*participant\s", diagram, re.M))
                limit, kind = 6, "参加者"
            else:
                continue
            if boxes > limit:
                failures.append(
                    f"{path.name}: {number}枚目の図に{kind}が {boxes} あります"
                    f"（{limit} を超えると頁幅へ縮んだとき文字が読めません）。"
                    f"責任のまとまりで分けてください"
                )

    # 20. 変更影響グラフの箱の書き方
    for path in chapters:
        text = path.read_text(encoding="utf-8")
        for graph in re.findall(r"```mermaid\ngraph (?:TD|LR)\n(.*?)```", text, re.S):
            for label in re.findall(r'\w+\["([^"]+)"\]', graph):
                if label.startswith("変更要求") or "✅" in label or "<br>" in label:
                    continue
                failures.append(
                    f"{path.name}: 変更影響グラフの箱「{label[:30]}」が規約の4種"
                    f"（起点・届いた先・届かなかった先・再テスト）のどれでもありません"
                )

    # 21. 第0章が挙げる節名の実在
    practice_headings: set[str] = set()
    for path in chapters:
        if not re.match(r"chapter\d", path.name):
            continue
        for line in path.read_text(encoding="utf-8").split("\n"):
            if re.match(r"^#{3,4}\s", line):
                practice_headings.add(re.sub(r"^#+\s*", "", line).strip())
    if practice_headings:
        for path in chapters:
            text = path.read_text(encoding="utf-8")
            for cited in re.findall(r"\*\*章内の項目\*\*：([^\n]+)", text):
                for part in cited.split("／"):
                    part = part.strip()
                    if not part:
                        continue
                    if not any(
                        part == h or part in h or h in part for h in practice_headings
                    ):
                        failures.append(
                            f"{path.name}: 「{part}」を章内の項目として挙げていますが、"
                            f"実践章にその見出しがありません"
                        )

    # 22. 執筆用テンプレートの穴埋め
    # 図のラベル【追加】【変更】や、掲載箇所を示す【ここで確認するコード】は本文の一部。
    # 埋めないまま残った「【○○を書く】」だけを落とす。
    allowed = re.compile(
        r"【(?:追加|変更|削除|接続|ここで確認するコード|変更前から抜き出す箇所"
        r"|今回の変更から守る部分（守りたい骨格）|過剰コード：[^】]*|痛みのコード[^】]*"
        r"|現状コード[^】]*|完成コード[^】]*)】"
    )
    for path in chapters:
        for number, line in prose_lines(path.read_text(encoding="utf-8")):
            for hole in re.findall(r"【[^】]{2,30}】", line):
                if allowed.fullmatch(hole):
                    continue
                if re.search(r"(?:と同じ|を書く|方法|条件|クラス|場所|文|値|範囲|結果)】$", hole):
                    failures.append(
                        f"{path.name}:{number}: 執筆用の穴埋め {hole} が本文に残っています"
                    )

    # 23. 他ファイルの話題を名指しする参照
    # 「第0章で触れたUSB充電の例え」のように、章をまたいで話題を指す文が、
    # 移動・削除の後も古い参照先を指したままになるのを防ぐ。
    where = {}
    for path in chapters:
        body = path.read_text(encoding="utf-8")
        heading = re.search(r"^#\s*(.+)$", body, re.M)
        if heading:
            where[heading.group(1).strip()] = body
    for path in chapters:
        text = path.read_text(encoding="utf-8")
        for target, topic in re.findall(
            r"(第\d+章|「はじめに」|「おわりに」)(?:で|の)(?:触れた|挙げた|見た|示した)"
            r"([^\n]{2,12}?)(?:の例え|の例|の話|を)", text
        ):
            name = target.strip("「」")
            source = next(
                (b for h, b in where.items() if h.startswith(name) or name in h), None
            )
            if source is None or path.read_text(encoding="utf-8") is source:
                continue
            core = re.sub(r"[「」『』]", "", topic)
            if core and core not in source:
                failures.append(
                    f"{path.name}: 「{name}で触れた{topic}」と書いていますが、"
                    f"{name}にその話題がありません"
                )

    # 24. 種類の違うIDを等号で結ばない
    # 「問題ID1＝原因ID1」は、痛みと原因が同じものだと読ませる。
    # 導出の向き（原因から課題、痛みから原因）が消えるため、矢印か文で書く。
    kinds = "(?:問題|原因|課題|要求|変更|リスク)ID\\d"
    for path in chapters:
        for number, line in prose_lines(path.read_text(encoding="utf-8")):
            for left, right in re.findall(
                rf"({kinds})[^。\n]{{0,60}}?＝\s*({kinds})", line
            ):
                if left[:2] != right[:2]:
                    failures.append(
                        f"{path.name}:{number}: {left}と{right}を「＝」で結んでいます。"
                        f"種類の違うIDは導出の向きが分かる書き方にしてください"
                    )

    # 25. IDへ短い名前を併記する
    # 番号だけだと、10ページ先で出てきたときに何の話か分からない。
    # 定義見出し（**要求ID1** だけの行）と、直後に説明が続く形は対象外。
    for path in chapters:
        if not re.search(r"chapter0[1-9]", path.name):
            continue
        for number, line in prose_lines(path.read_text(encoding="utf-8")):
            if line.lstrip().startswith("|"):
                continue
            for match in re.finditer(
                r"(?:要求|変更|リスク|問題|原因|課題)ID\d+", line
            ):
                after = line[match.end(): match.end() + 2]
                before = line[max(0, match.start() - 2): match.start()]
                if after.startswith(("（", "(", "**")) or before.endswith("**"):
                    continue
                failures.append(
                    f"{path.name}:{number}: {match.group(0)} に短い名前が"
                    f"併記されていません（{line.strip()[:44]}）"
                )
                break

    if failures:
        print("\n".join(failures))
        print(f"\nFAILED: {len(failures)} volume issue(s) in {config_path.name}")
        return 1

    print(f"OK: 『{title}』の{len(chapters)}ファイルが1冊として成立しています")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        required=True,
        help="検査する冊の book.json（例 books/volume01-core-patterns/publishing/book.json）",
    )
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
