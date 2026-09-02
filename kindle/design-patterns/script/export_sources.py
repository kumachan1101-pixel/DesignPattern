#!/usr/bin/env python3
"""掲載コードを、本文が示すファイル構成へ切り出す。

本文では「実務ではこう分けます」という表を各章に置いている。読者が実際に
その形を手に入れられるよう、掲載コードから `.h` と `.cpp` を生成する。

掲載コードは1つの流れで書いてあるので、クラス単位で切り出し、宣言を `.h`、
本体を `.cpp` へ分ける……のではなく、**本文の分割表と同じ粒度**でまとめる。
`Discounts.h` に5つの割引クラスが入るのは、本文が「施策が増えたとき、ここ
だけを開けば済む」と書いているからである。ファイルの切り方そのものが設計の
説明なので、機械的な1クラス1ファイルにはしない。

生成したものは Makefile ごとビルドして、掲載コードと同じ出力になることを
確かめる。ここが通らなければ、本文の分割表が絵に描いた餅ということになる。

    python3 script/export_sources.py --config books/<冊>/publishing/book.json
    python3 script/export_sources.py --config <...> --verify   # ビルドまで行う
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]

# 章ごとのファイル構成。本文の「実務でファイルを分けるなら」の表と同じ。
# (出力ファイル, そこへ入れるトップレベル定義の名前) の順で並べる。
LAYOUTS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "03-chapter01": [
        ("Order.h", ("Item", "Order", "CustomerInfo", "CustomerDatabase",
                     "CampaignContext", "PaymentResult", "MemberType", "CampaignCode")),
        ("IDiscountRule.h", ("IDiscountRule",)),
        ("Discounts.h", ("PremiumDiscount", "CampaignDiscount", "SummerSaleDiscount",
                         "SummerSaleAndCampaignDiscount", "NoDiscount")),
        ("RuleSelector.h", ("RuleSelector",)),
        ("DiscountRuleSet.h", ("DiscountRuleSet",)),
        ("PaymentCalculator.h", ("PaymentCalculator", "CheckoutResultRenderer",
                                 "OrderProcessor", "CartPreviewService")),
    ],
    "04-chapter02": [
        ("EventDatabase.h", ("EventInfo", "EventDatabase", "ReservationRecord",
                             "ReservationHistory", "Transition")),
        ("IReservationState.h", ("IReservationState",)),
        # 骨格は状態の共有実体を返す関数を呼ぶため、States.h を先に置く。
        # 本文の「悩みどころ：次の状態を誰が決めるのか」で触れた相互参照が、
        # ファイル順という形でここに現れる。
        ("States.h", ("AvailableState", "ReservedState", "PaidState",
                      "WaitlistedState", "HeldState")),
        ("TicketReservation.h", ("TicketReservation", "ReservationWaitlist",
                                 "ReservationExpiryScheduler", "BatchApplication")),
    ],
    "05-chapter03": [
        ("ProductDatabase.h", ("ProductInfo", "ProductDatabase", "StockAlert",
                               "StockEvent", "StockEventLog", "DeliveryResult",
                               "DeliveryStatus")),
        ("INotification.h", ("INotification",)),
        ("Notifiers.h", ("EmailNotifier", "DashboardUpdater", "ChatNotifier",
                         "SMSNotifier")),
        ("DeliveryStatusLog.h", ("DeliveryStatusLog", "SMSDeliveryCallback")),
        ("InventoryManager.h", ("InventoryManager",)),
    ],
}


# 相互参照するクラスは、最初のヘッダーで前方宣言しておく。
# 第2章は骨格と状態が互いを指すため、これがないとどちらを先に置いても通らない。
# 本文の「悩みどころ：次の状態を誰が決めるのか」で触れている関係そのものである。
FORWARD: dict[str, tuple[str, ...]] = {
    "04-chapter02": ("TicketReservation", "IReservationState"),
}

# クラス本体が相手の実体を必要とする場合、ヘッダーに定義を置けない。
# そのファイルだけ、メンバー関数の本体を .cpp へ落とす。
# 第2章の状態クラスは `reservation->hasCapacity()` を呼ぶため、
# TicketReservation の宣言が済んでいないと書けない。
SPLIT_DEFINITIONS: dict[str, tuple[str, ...]] = {
    "04-chapter02": ("States.h",),
}


def move_bodies_to_source(chunk: str) -> tuple[str, str]:
    """クラス定義から、メンバー関数の本体を切り出す。

    戻り値は (宣言だけのヘッダー用, クラス外定義のソース用)。
    `void f(T* p) override { ... }` を
    `void f(T* p) override;` と `void Cls::f(T* p) { ... }` へ分ける。
    """
    name = re.match(r"\s*class\s+([A-Za-z_]\w*)", chunk)
    if not name:
        # クラスではない塊。自由関数の **定義** はヘッダーへ置くと二重定義に
        # なるので .cpp へ送り、宣言だけを残す。先頭にコメント行が付くことが
        # あるため、行を走査して最初の関数定義を探す。
        lines = chunk.split("\n")
        for index, line in enumerate(lines):
            head = re.match(
                r"\s*((?:[\w:<>&*]+[\s*&]+)+\w+\s*\([^)]*\))\s*\{\s*$", line
            )
            if head:
                keep = lines[:index] + [head.group(1).strip() + ";"]
                return "\n".join(keep), "\n".join(lines[index:])
        return chunk, ""
    cls = name.group(1)
    decls: list[str] = []
    defs: list[str] = []
    lines = chunk.split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        opened = re.match(
            r"(\s*)((?:virtual\s+)?[\w:<>&*\s]+?\s+(\w+)\s*\([^)]*\)"
            r"(?:\s*const)?(?:\s*override)?)\s*\{\s*$",
            line,
        )
        if opened and "class" not in line:
            indent, signature, _ = opened.groups()
            depth = 1
            body = [line]
            index += 1
            while index < len(lines) and depth > 0:
                body.append(lines[index])
                depth += lines[index].count("{") - lines[index].count("}")
                index += 1
            decls.append(f"{indent}{signature.strip()};")
            head = re.sub(r"^\s*(?:virtual\s+)?", "", signature.strip())
            head = re.sub(r"(\w+)\s*\(", rf"{cls}::\1(", head, count=1)
            head = re.sub(r"\s*override\s*$", "", head)
            defs.append(head + " {")
            defs.extend(body[1:])
            defs.append("")
            continue
        decls.append(line)
        index += 1
    return "\n".join(decls), "\n".join(defs)


def gather_program(text: str, heading: str) -> str | None:
    """見出しから main() が閉じるまでの cpp を連結する（check_code_runs と同じ規則）。"""
    found = re.search(rf"^####\s*{heading}\s*$", text, re.M)
    if not found:
        return None
    parts: list[str] = []
    seen_main = False
    for block in re.finditer(r"```cpp\n(.*?)```", text[found.end():], re.S):
        parts.append(block.group(1))
        if re.search(r"\bint\s+main\s*\(", block.group(1)):
            seen_main = True
        if seen_main:
            joined = "\n".join(parts)
            code = re.sub(r'"(\\.|[^"\\])*"', '""', joined)
            code = re.sub(r"'(\\.|[^'\\])*'", "''", code)
            code = re.sub(r"//[^\n]*", "", code)
            if code.count("{") == code.count("}"):
                break
    return "\n".join(parts) if seen_main else None


def split_top_level(program: str) -> list[tuple[str, str]]:
    """(名前, 本文) のトップレベル定義へ切る。名前が取れないものは "" で返す。"""
    lines = program.split("\n")
    chunks: list[tuple[str, str]] = []
    buffer: list[str] = []
    name = ""
    depth = 0
    for line in lines:
        stripped = re.sub(r'"(\\.|[^"\\])*"', '""', line)
        stripped = re.sub(r"//.*", "", stripped)
        if depth == 0:
            match = re.match(r"\s*(?:class|struct|namespace)\s+([A-Za-z_]\w*)", line)
            if match:
                if buffer:
                    chunks.append((name, "\n".join(buffer)))
                    buffer, name = [], ""
                name = match.group(1)
            elif re.match(r"\s*(?:void|int|bool|double|std::string|const)\s+\w+::", line):
                # クラス外定義。直前のクラスへ付ける
                owner = re.search(r"(\w+)::", line)
                if owner and buffer:
                    chunks.append((name, "\n".join(buffer)))
                    buffer, name = [], owner.group(1)
                elif owner:
                    name = owner.group(1)
        buffer.append(line)
        depth += stripped.count("{") - stripped.count("}")
        if depth == 0 and line.strip() in ("};", "}"):
            chunks.append((name, "\n".join(buffer)))
            buffer, name = [], ""
    if buffer:
        chunks.append((name, "\n".join(buffer)))
    return chunks


def export(stem: str, program: str, out_dir: Path) -> list[str]:
    """章のプログラムを LAYOUTS の構成へ書き出し、生成ファイル名を返す。"""
    layout = LAYOUTS[stem]
    chunks = split_top_level(program)

    # `#include` と `using namespace std;` は、最初のヘッダーへまとめて置く。
    # 掲載コードは1ファイル前提で書かれているため、これらを落とすと後続が壊れる。
    preamble = "\n".join(
        line for line in program.split("\n")
        if line.startswith("#include") or line.startswith("using ")
    )
    owner_of: dict[str, str] = {}
    for filename, names in layout:
        for n in names:
            owner_of[n] = filename

    buckets: dict[str, list[str]] = {f: [] for f, _ in layout}
    main_body: list[str] = []
    leftovers: list[str] = []
    for name, body in chunks:
        if re.search(r"\bint\s+main\s*\(", body):
            main_body.append(body)
            continue
        if body.strip().startswith("#include") and not name:
            continue
        target = owner_of.get(name)
        if target:
            buckets[target].append(body.strip("\n"))
            continue
        # 自由関数は、本文へ出てくる型のうち **最も後ろのファイル** へ送る。
        # `IReservationState* availableState() { static AvailableState state; ... }`
        # は戻り値が契約でも、中身は具体を必要とする。先頭の型で決めると、
        # 契約のヘッダーが具体を要求してビルドが通らない。
        order = {f: i for i, (f, _) in enumerate(layout)}
        hits = {
            filename
            for candidate, filename in owner_of.items()
            if re.search(rf"\b{re.escape(candidate)}\b", body)
        }
        if hits:
            buckets[max(hits, key=lambda f: order[f])].append(body.strip("\n"))
            continue
        if name:
            leftovers.append(name)
        elif body.strip() and not body.strip().startswith(("#include", "using ")):
            buckets[layout[0][0]].append(body.strip("\n"))

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    previous: list[str] = []
    sources: dict[str, list[str]] = {}
    for filename in SPLIT_DEFINITIONS.get(stem, ()):
        decls, defs = [], []
        for body in buckets[filename]:
            d, s = move_bodies_to_source(body)
            decls.append(d)
            if s.strip():
                defs.append(s)
        buckets[filename] = decls
        sources[filename] = defs
    for filename, _ in layout:
        guard = re.sub(r"\W", "_", filename).upper() + "_INCLUDED"
        header = [f"#ifndef {guard}", f"#define {guard}", ""]
        if filename == layout[0][0]:
            header.append(preamble)
            forwards = FORWARD.get(stem, ())
            if forwards:
                header.append("")
                header.extend(f"class {n};" for n in forwards)
        else:
            header.extend(f'#include "{p}"' for p in previous)
        header.append("")
        header.append("\n\n".join(buckets[filename]))
        header.extend(["", f"#endif  // {guard}", ""])
        (out_dir / filename).write_text("\n".join(header), encoding="utf-8")
        written.append(filename)
        previous.append(filename)
        if filename in sources:
            source_name = filename[:-2] + ".cpp"
            body = [f'#include "{layout[-1][0]}"', ""] + sources[filename] + [""]
            (out_dir / source_name).write_text("\n".join(body), encoding="utf-8")
            written.append(source_name)

    main_source = ['#include "' + layout[-1][0] + '"', ""] + main_body + [""]
    (out_dir / "main.cpp").write_text("\n".join(main_source), encoding="utf-8")
    written.append("main.cpp")

    # 読者がそのままビルドできるように Makefile を置く。
    (out_dir / "Makefile").write_text(
        "# 本書の掲載コードを、実務のファイル構成へ分けたものです。\n"
        "#   make        ビルド\n"
        "#   make run    ビルドして実行\n"
        "#   make clean  生成物を消す\n"
        "\n"
        "CXX      ?= g++\n"
        "CXXFLAGS ?= -std=c++14 -Wall -I.\n"
        "TARGET   := app\n"
        "SRCS     := $(wildcard *.cpp)\n"
        "\n"
        "$(TARGET): $(SRCS) $(wildcard *.h)\n"
        "\t$(CXX) $(CXXFLAGS) $(SRCS) -o $@\n"
        "\n"
        "run: $(TARGET)\n"
        "\t./$(TARGET)\n"
        "\n"
        "clean:\n"
        "\trm -f $(TARGET)\n"
        "\n"
        ".PHONY: run clean\n",
        encoding="utf-8",
    )
    written.append("Makefile")

    if leftovers:
        print(f"    未割り当て: {', '.join(sorted(set(leftovers)))}")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--verify", action="store_true",
                        help="生成後にビルドし、掲載コードと同じ出力になるか確かめる")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = BOOK_ROOT / config_path
    data = json.loads(config_path.read_text(encoding="utf-8"))
    volume_dir = config_path.parents[1]
    src_root = volume_dir / "sources"

    failures = 0
    for chapter in data.get("chapters", []):
        path = BOOK_ROOT / chapter
        stem = path.stem
        if stem not in LAYOUTS:
            continue
        program = gather_program(path.read_text(encoding="utf-8"), "完成コード")
        if program is None:
            print(f"{stem}: 完成コードを取り出せません")
            failures += 1
            continue
        out_dir = src_root / stem.split("-", 1)[1]
        if out_dir.exists():
            shutil.rmtree(out_dir)
        written = export(stem, program, out_dir)
        print(f"{stem}: {len(written)} ファイル → {out_dir.relative_to(BOOK_ROOT)}")

        if args.verify:
            if not shutil.which("g++"):
                print("    SKIP: g++ が無いため未検証")
                continue
            with tempfile.TemporaryDirectory() as tmp:
                binary = Path(tmp) / "app"
                units = [str(p) for p in sorted(out_dir.glob("*.cpp"))]
                built = subprocess.run(
                    ["g++", "-std=c++14", "-I", str(out_dir)] + units
                    + ["-o", str(binary)],
                    capture_output=True, text=True,
                )
                if built.returncode != 0:
                    first = next((l for l in built.stderr.splitlines()
                                  if "error:" in l), built.stderr[:200])
                    print(f"    ✗ ビルド失敗: {first.strip()[:150]}")
                    failures += 1
                    continue
                run = subprocess.run([str(binary)], stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, timeout=30)
                single = Path(tmp) / "single.cpp"
                single.write_text(program, encoding="utf-8")
                one = Path(tmp) / "one"
                subprocess.run(["g++", "-std=c++14", str(single), "-o", str(one)],
                               capture_output=True, check=True)
                expected = subprocess.run([str(one)], stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, text=True,
                                          timeout=30)
                if run.stdout == expected.stdout:
                    print("    ✓ ビルドでき、掲載コードと同じ出力")
                else:
                    print("    ✗ 出力が掲載コードと違う")
                    failures += 1

    if failures:
        print(f"\nFAILED: {failures} 件")
        return 1
    print("\nOK: すべての章でファイル一式を生成しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
