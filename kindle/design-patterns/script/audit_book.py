#!/usr/bin/env python3
"""Produce a repeatable, evidence-based audit of the book.

Unlike validate_book.py, this command does not decide whether the book may be
published. It collects review candidates that require human judgment and
checks whether the self-contained C++ sections actually compile.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


BOOK_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BOOK_ROOT / "output"
DEFAULT_REPORT = BOOK_ROOT / "audit-report.md"
DEFAULT_BASELINE = BOOK_ROOT / "audit-baseline.json"

CORE_CHAPTERS = [
    "chapter01.md",
    "chapter02.md",
    "chapter03.md",
    "chapter04.md",
    "chapter05.md",
    "chapter06.md",
    "chapter07.md",
    "chapter08.md",
    "chapter09_2.md",
    "chapter10.md",
    "chapter11.md",
    "chapter12.md",
]

RISK_PATTERNS = [
    (
        "overclaim",
        "medium",
        re.compile(
            r"だけで完結|だけに閉じ|影響しない構造|互いに影響しない|"
            r"唯一の場所|1行修正|新しいクラスを作らず"
        ),
        "変更範囲を過小評価していないか確認する",
    ),
    (
        "unverified-proof",
        "medium",
        re.compile(
            r"全(?:て|ケース|シナリオ|行).{0,30}(?:一致|確認)|"
            r"動作例.{0,20}一致"
        ),
        "掲載コードの実行結果で本当に全件を確認しているか調べる",
    ),
    (
        "future-leak",
        "high",
        re.compile(
            r"変更要求による追加分|最終実装.{0,20}全シナリオ|"
            r"フェーズ7で追加|変更後の受入条件"
        ),
        "変更要求前の現状把握へ将来仕様が先取りされていないか確認する",
    ),
    (
        "undefined-demo",
        "high",
        re.compile(r"\b(?:EXPECT_EQ|ASSERT_EQ)\s*\("),
        "テストフレームワークや補助クラスを含めて掲載コードが成立するか確認する",
    ),
]


@dataclass(frozen=True)
class Finding:
    finding_id: str
    chapter: str
    line: int
    category: str
    severity: str
    evidence: str
    review_question: str


def normalize_evidence(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())[:180]


def make_id(chapter: str, category: str, line: int, evidence: str) -> str:
    """Create an ID that survives unrelated line insertions.

    Line numbers are useful evidence but are deliberately excluded from the
    identifier. Otherwise adding one paragraph near the beginning of a chapter
    would make every later finding look new to the CI baseline.
    """
    del line
    normalized = normalize_evidence(evidence).lower()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    hint = re.sub(r"\W+", "-", normalized).strip("-")[:28] or "finding"
    return f"{chapter.removesuffix('.md')}:{category}:{hint}:{digest}"


def section(text: str, start_pattern: str, end_pattern: str) -> str:
    start = re.search(start_pattern, text, re.MULTILINE)
    if not start:
        return ""
    end = re.search(end_pattern, text[start.end() :], re.MULTILINE)
    if end:
        return text[start.end() : start.end() + end.start()]
    return text[start.end() :]


def cpp_blocks(text: str) -> list[str]:
    return re.findall(r"```cpp\s*\n(.*?)```", text, re.DOTALL)


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_patterns(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    phase1 = section(text, r"^## 🔵 フェーズ1", r"^## 🟣 フェーズ2")
    phase1_start = text.find(phase1) if phase1 else -1

    for category, severity, pattern, question in RISK_PATTERNS:
        scan_text = phase1 if category == "future-leak" else text
        base = phase1_start if category == "future-leak" else 0
        for match in pattern.finditer(scan_text):
            absolute = base + match.start()
            line = line_of(text, absolute)
            source_line = text.splitlines()[line - 1]
            evidence = normalize_evidence(source_line)
            findings.append(
                Finding(
                    make_id(path.name, category, line, evidence),
                    path.name,
                    line,
                    category,
                    severity,
                    evidence,
                    question,
                )
            )
    return findings


def scan_tables(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    in_fence = False
    in_table = False
    for number, line in enumerate(lines, start=1):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line.strip().startswith("|"):
            in_table = False
            continue
        if in_table:
            continue
        in_table = True
        cells = len([part for part in line.split("|")[1:-1]])
        if cells > 4:
            evidence = normalize_evidence(line)
            findings.append(
                Finding(
                    make_id(path.name, "wide-table", number, evidence),
                    path.name,
                    number,
                    "wide-table",
                    "low",
                    evidence,
                    f"Kindleルール上は最大4列だが、この行は{cells}列ある",
                )
            )
    return findings


def scan_raw_ownership(path: Path, text: str) -> list[Finding]:
    raw_pattern = re.compile(
        r"(?:vector|list|deque)<[^>\n]*\*>|"
        r"\b(?:new|delete)\s+|"
        r"\b(?:I[A-Z]\w*|[A-Z]\w*(?:State|Phase|Rule|Listener|"
        r"Observer|Strategy|Client|Action|Command))\s*\*\s*\w+"
    )
    matches = list(raw_pattern.finditer(text))
    if not matches:
        return []
    explanation_count = len(
        re.findall(
            r"非所有|所有権|生存期間|寿命|関数ローカルの静的|"
            r"より長く生存|破棄前に.*解除",
            text,
        )
    )
    if explanation_count > 0:
        return []
    first = matches[0]
    line = line_of(text, first.start())
    evidence = normalize_evidence(text.splitlines()[line - 1])
    return [
        Finding(
            make_id(path.name, "raw-ownership", line, evidence),
            path.name,
            line,
            "raw-ownership",
            "medium",
            f"生ポインタ等を{len(matches)}箇所使用。例: {evidence}",
            "所有・非所有、生存期間、解除契約を章内で明示する必要があるか",
        )
    ]


def scan_phase1_execution(path: Path, text: str) -> list[Finding]:
    if path.name not in CORE_CHAPTERS:
        return []
    body = section(text, r"^### 1-4：", r"^### 1-5：")
    start = text.find(body)
    findings: list[Finding] = []
    for token, message in [
        ("int main(", "現状コードに実行起点main()がない"),
        ("実行結果", "現状コードに掲載実行結果がない"),
    ]:
        if token not in body:
            line = line_of(text, max(start, 0))
            findings.append(
                Finding(
                    make_id(path.name, "phase1-proof", line, message),
                    path.name,
                    line,
                    "phase1-proof",
                    "high",
                    message,
                    "動作例テーブルの各行を現状コードで再現できるか",
                )
            )
    return findings


def compile_section(
    path: Path, text: str, heading: str, end_heading: str, compiler: str
) -> Finding | None:
    body = section(
        text,
        rf"^### {re.escape(heading)}",
        rf"^### {re.escape(end_heading)}",
    )
    blocks = cpp_blocks(body)
    if not blocks:
        return Finding(
            make_id(path.name, "compile", 1, heading),
            path.name,
            1,
            "compile",
            "high",
            f"{heading}にC++コードがない",
            "実行可能コードを掲載する節として成立しているか",
        )

    source = "\n\n".join(blocks)
    if "int main(" not in source:
        return Finding(
            make_id(path.name, "compile", 1, f"{heading}-main"),
            path.name,
            1,
            "compile",
            "high",
            f"{heading}の結合コードにmain()がない",
            "章内の分割コードを結合して単独実行できるか",
        )

    with tempfile.TemporaryDirectory(prefix="design-pattern-audit-") as temp:
        source_path = Path(temp) / "chapter.cpp"
        exe_path = Path(temp) / "chapter.exe"
        source_path.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [
                compiler,
                "-std=c++14",
                "-Wall",
                "-Wextra",
                "-pedantic",
                str(source_path),
                "-o",
                str(exe_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return None
        evidence = normalize_evidence((result.stderr or result.stdout).splitlines()[0])
        return Finding(
            make_id(path.name, "compile", 1, f"{heading}-{evidence}"),
            path.name,
            1,
            "compile",
            "high",
            f"{heading}のC++14コンパイル失敗: {evidence}",
            "掲載コード内の未定義型・不足include・重複定義を修正する必要がある",
        )


def collect_findings(compile_cpp: bool) -> list[Finding]:
    findings: list[Finding] = []
    compiler = shutil.which("g++") if compile_cpp else None
    if compile_cpp and compiler is None:
        raise RuntimeError(
            "g++ was not found. Install a C++14 compiler or use --no-compile "
            "only when intentionally skipping code verification."
        )
    for path in sorted(OUTPUT_DIR.glob("chapter*.md")):
        text = path.read_text(encoding="utf-8")
        findings.extend(scan_patterns(path, text))
        findings.extend(scan_tables(path, text))
        findings.extend(scan_raw_ownership(path, text))
        findings.extend(scan_phase1_execution(path, text))
        if compiler and path.name in CORE_CHAPTERS:
            for heading, end_heading in [
                ("1-4：実装コード（現状）", "1-5：変更要求"),
                ("7-1：解決後のコード（全体）", "7-2：動作シーケンス図"),
            ]:
                finding = compile_section(
                    path, text, heading, end_heading, compiler
                )
                if finding:
                    findings.append(finding)
    unique = {finding.finding_id: finding for finding in findings}
    return sorted(
        unique.values(),
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2}[item.severity],
            item.chapter,
            item.line,
        ),
    )


def render_report(findings: list[Finding]) -> str:
    counts = {
        severity: sum(item.severity == severity for item in findings)
        for severity in ("high", "medium", "low")
    }
    lines = [
        "# 全章横断監査レポート",
        "",
        "このファイルは`script/audit_book.py`で生成するレビュー候補一覧です。",
        "機械検出は指摘の証拠を集めるものであり、タスク登録前に人が文脈を確認します。",
        "",
        f"- 高: {counts['high']}件",
        f"- 中: {counts['medium']}件",
        f"- 低: {counts['low']}件",
        f"- 合計: {len(findings)}件",
        "",
    ]
    for severity, label in [("high", "高"), ("medium", "中"), ("low", "低")]:
        lines.extend([f"## 優先度：{label}", ""])
        selected = [item for item in findings if item.severity == severity]
        if not selected:
            lines.extend(["該当なし。", ""])
            continue
        for item in selected:
            lines.extend(
                [
                    f"### `{item.finding_id}`",
                    "",
                    f"- 場所: `{item.chapter}:{item.line}`",
                    f"- 分類: `{item.category}`",
                    f"- 証拠: {item.evidence}",
                    f"- 確認事項: {item.review_question}",
                    "",
                ]
            )
    return "\n".join(lines)


def write_text_lf(path: Path, text: str) -> None:
    """Write generated artifacts without Windows newline conversion."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-compile", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--check-baseline", action="store_true")
    args = parser.parse_args()

    findings = collect_findings(not args.no_compile)
    write_text_lf(args.report, render_report(findings))

    serialized = [asdict(item) for item in findings]
    if args.write_baseline:
        write_text_lf(
            DEFAULT_BASELINE,
            json.dumps(serialized, ensure_ascii=False, indent=2) + "\n",
        )

    if args.check_baseline:
        if not DEFAULT_BASELINE.exists():
            print("audit baseline is missing")
            return 2
        baseline = {
            item["finding_id"]
            for item in json.loads(DEFAULT_BASELINE.read_text(encoding="utf-8"))
        }
        current = {item.finding_id for item in findings}
        new_findings = current - baseline
        if new_findings:
            print("New audit findings:")
            for finding_id in sorted(new_findings):
                print(f"- {finding_id}")
            return 1

    print(f"Wrote {len(findings)} findings to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
