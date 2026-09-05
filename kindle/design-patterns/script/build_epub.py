#!/usr/bin/env python3
"""Build the DesignPattern Kindle book with image-based code and diagrams.

The pipeline intentionally leaves the source Markdown untouched:

* optional overview-slide PDF -> one PNG per chapter
* Mermaid fences -> PNG
* every other fenced block -> syntax-highlighted, height-limited PNG chunks
* processed chapters -> one standalone HTML -> EPUB/MOBI/PDF via Calibre
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


BOOK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = BOOK_ROOT / "publishing" / "book.json"
FENCE_RE = re.compile(
    r"^```([^\n`]*)\r?\n(.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+['\"][^)]*['\"])?\)")
HTTP_RE = re.compile(r"^(?:https?:|data:)", re.IGNORECASE)


CODE_CSS = r"""
<style>
html, body {
  margin: 0;
  padding: 0;
  background: #0F172A !important;
  width: __WIDTH__px !important;
  max-width: __WIDTH__px !important;
  box-sizing: border-box;
  overflow: hidden;
}
.highlight {
  background: #0F172A !important;
  color: #FFFFFF !important;
  width: __WIDTH__px !important;
  box-sizing: border-box;
  padding: 0 40px !important;
  font-family: "BIZ UDGothic", "MS Gothic", "Noto Sans Mono CJK JP", "Noto Sans JP", "Yu Gothic", Meiryo, monospace !important;
  font-size: 48px !important;
  line-height: 1.6 !important;
  font-weight: 500 !important;
}
.highlight pre {
  margin: 0 !important;
  padding: 10px 0 !important;
  background: #0F172A !important;
  color: #FFFFFF !important;
  white-space: pre-wrap !important;
  overflow-wrap: break-word !important;
  word-wrap: break-word !important;
  word-break: break-all !important;
  font: inherit !important;
}
.highlight .c1, .highlight .cm, .highlight .c {
  color: #64748B !important;
  font-weight: 600 !important;
  font-style: italic !important;
}
.highlight .cp {
  color: #C4B5FD !important;
  font-weight: bold !important;
  font-style: normal !important;
}
.highlight .cpf, .highlight .s, .highlight .s1, .highlight .s2 {
  color: #A3E635 !important;
  font-weight: 600 !important;
}
.highlight .k, .highlight .kn, .highlight .kr, .highlight .kd {
  color: #38BDF8 !important;
  font-weight: bold !important;
}
.highlight .kt, .highlight .nc {
  color: #818CF8 !important;
  font-weight: 600 !important;
}
.highlight .mi, .highlight .mf, .highlight .mh {
  color: #FBBF24 !important;
  font-weight: 600 !important;
}
.highlight .nf, .highlight .nb {
  color: #A78BFA !important;
  font-weight: bold !important;
}
.highlight .n, .highlight .p, .highlight .o {
  color: #FFFFFF !important;
}
.highlight .go {
  color: #FFFFFF !important;
  opacity: 0.8 !important;
  font-weight: 600 !important;
}
/* 変更前と変更後を見比べる読者が、どこが変わったかを探さずに済むように、
   原稿の「← 追加」「← 変更」で示した行へ帯を敷く。 */
.highlight .chg {
  display: block !important;
  background: #1E3A5F !important;
  padding: 0 40px !important;
  margin: 0 -40px !important;
}
</style>
"""

CODE_TITLE_STYLE = (
    "background:#1E293B;color:#F8FAFC;padding:25px 40px;"
    "border-bottom:2px solid #334155;font-size:48px;font-weight:bold;"
    "font-family:BIZ UDGothic,MS Gothic,Noto Sans Mono CJK JP,Noto Sans JP,"
    "Yu Gothic,Meiryo,monospace;line-height:1.35;overflow-wrap:anywhere;"
    "word-break:break-word;width:{width}px;box-sizing:border-box;"
)


BOOK_CSS = r"""
@page { margin: 0; }
body {
  color: #222;
  font-family: "Hiragino Mincho ProN", "Yu Mincho", serif;
  font-size: 1em;
  line-height: 1.85;
  margin: 0;
  padding: 1em;
  /* 両端そろえにすると、折り返し候補の少ない行で文字間が引き伸ばされ、
     「コ ー ド 上 の 受 け 取 り 口」のような字間の崩れが出る。
     Kindleの端末側は読者の設定で両端そろえにできるので、ここでは行わない。 */
  text-align: left;
}
h1 {
  background: #e0e0e0;
  border-bottom: 4px solid #333;
  font-size: 2em;
  line-height: 1.4;
  margin: 1em 0 0.6em;
  padding: 0.5em 0.8em;
  page-break-before: always;
  page-break-after: avoid;
}
h2 {
  background: #e3f2fd;
  border-left: 5px solid #1976d2;
  font-size: 1.5em;
  margin: 2em 0 1em;
  padding: 0.6em 0.8em;
  page-break-after: avoid;
}
h3 {
  background: #e8f5e9;
  border-left: 4px solid #388e3c;
  font-size: 1.3em;
  margin: 1.5em 0 0.8em;
  padding: 0.5em 0.7em;
  page-break-after: avoid;
}
h4 {
  background: #fff3e0;
  border-left: 3px solid #ff9800;
  font-size: 1.15em;
  margin: 1.2em 0 0.6em;
  padding: 0.4em 0.6em;
  page-break-after: avoid;
}
img { height: auto; max-width: 100%; }
table { border-collapse: collapse; font-size: 0.9em; margin: 1.2em 0; width: 100%; }
th, td { border: 1px solid #999; padding: 0.55em; text-align: left; }
/* 1列目は「要求ID1」のような短い見出しが入る。列幅が詰まって
   1文字ずつ折れるのを防ぐため、最小幅を与える。 */
th:first-child, td:first-child { min-width: 5.5em; }
th { background: #f5f5f5; }
/* 変更前と変更後を並べる表で、変わったところだけを青字にする。
   原稿では **…** で囲み、build 時にこのクラスへ差し替える。
   コード画像の青い帯と同じ「ここが変わった」の合図として使う。 */
blockquote {
  border-left: 4px solid #78909c;
  background: #f7f9fa;
  color: #37474f;
  margin: 1em 0;
  padding: 0.7em 1em;
}
code {
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  font-family: "BIZ UDGothic", "MS Gothic", "Noto Sans Mono CJK JP", "Noto Sans JP", "Yu Gothic", Meiryo, monospace;
  font-size: 0.92em;
  padding: 0.08em 0.28em;
  /* 長い型名・関数名がひとかたまりだと、両端揃えで前後の字間が伸びる。
     入りきらないときだけ折り返し、短い名前は途中で切らない。 */
  overflow-wrap: break-word;
}
.book-cover, .book-toc { page-break-after: always; text-align: center; }
.book-toc { text-align: left; }
.book-toc p { margin: 0.55em 0; }
.book-toc .toc-chapter { margin: 0.9em 0 0.35em 0; font-weight: bold; }
.book-toc .toc-section { margin: 0.2em 0 0.2em 1.4em; font-size: 0.92em; }
.overview-slide, .mermaid-image {
  margin: 0.6em 0 1.2em;
  page-break-inside: avoid;
  break-inside: avoid;
  text-align: center;
}
.overview-slide img, .mermaid-image img { border: 1px solid #ddd; }
.mermaid-image img {
  /* A5で縦長図がページをはみ出し、次ページにも残像のように続くのを防ぐ。 */
  max-height: 5.2in;
  object-fit: contain;
  width: auto;
}
.mermaid-image figcaption {
  color: #455a64;
  font-size: 0.82em;
  line-height: 1.55;
  margin: 0.45em auto 0;
  text-align: left;
}
.figure-intro {
  /* 「次の図では…」だけを前ページへ置き去りにしない。 */
  break-after: avoid;
  page-break-after: avoid;
}
.visual-unit {
  break-inside: avoid;
  page-break-inside: avoid;
}
.code-image-stack {
  background: #0F172A;
  border: 2px solid #334155;
  line-height: 0;
  margin: 1em 0;
  overflow: hidden;
  padding: 0;
  width: 100%;
}
.code-image-stack img {
  border: 0;
  display: block;
  height: auto;
  margin: 0;
  padding: 0;
  width: 100%;
}
"""


class BuildError(RuntimeError):
    """A user-actionable publication build failure."""


@dataclass(frozen=True)
class RenderingConfig:
    code_width: int
    max_height: int
    first_lines: int
    continued_lines: int
    orphan_threshold: int
    mermaid_scale: int
    slide_dpi: int


@dataclass(frozen=True)
class BookConfig:
    path: Path
    root: Path
    title: str
    author: str
    language: str
    dist: Path
    slides: Path
    cover: Path | None
    chapters: tuple[Path, ...]
    slide_page_order: tuple[str, ...]
    rendering: RenderingConfig
    formats: tuple[str, ...]


def _project_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise BuildError(f"設定パスが書籍ルート外です: {value}") from exc
    return candidate


def load_config(path: Path) -> BookConfig:
    path = path.resolve()
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BuildError(f"設定ファイルが見つかりません: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BuildError(f"設定JSONが不正です: {path}: {exc}") from exc

    if raw.get("schemaVersion") != 1:
        raise BuildError("未対応のbook.json schemaVersionです")

    metadata = raw.get("metadata", {})
    paths = raw.get("paths", {})
    rendering = raw.get("rendering", {})
    root = BOOK_ROOT.resolve()
    chapters = tuple(
        path_value
        for item in raw.get("chapters", [])
        if (path_value := _project_path(root, str(item))) is not None
    )
    if not chapters:
        raise BuildError("book.jsonのchaptersが空です")

    config = BookConfig(
        path=path,
        root=root,
        title=str(metadata.get("title", "Book")),
        author=str(metadata.get("author", "")),
        language=str(metadata.get("language", "ja")),
        dist=_required_path(root, paths.get("dist"), "paths.dist"),
        slides=_required_path(root, paths.get("slides"), "paths.slides"),
        cover=_project_path(root, paths.get("cover")),
        chapters=chapters,
        slide_page_order=tuple(str(item) for item in raw.get("slidePageOrder", [])),
        rendering=RenderingConfig(
            code_width=int(rendering.get("codeImageWidth", 2000)),
            max_height=int(rendering.get("maxImageHeight", 1600)),
            first_lines=int(rendering.get("firstCodeLines", 19)),
            continued_lines=int(rendering.get("continuedCodeLines", 22)),
            orphan_threshold=int(rendering.get("orphanThreshold", 4)),
            mermaid_scale=int(rendering.get("mermaidScale", 3)),
            slide_dpi=int(rendering.get("slideDpi", 150)),
        ),
        formats=tuple(str(item).lower() for item in raw.get("formats", ["epub"])),
    )
    validate_config(config)
    return config


def _required_path(root: Path, value: Any, field: str) -> Path:
    result = _project_path(root, str(value) if value else None)
    if result is None:
        raise BuildError(f"book.jsonの{field}が未設定です")
    return result


def validate_config(config: BookConfig) -> None:
    missing = [str(path) for path in config.chapters if not path.is_file()]
    if missing:
        raise BuildError("章ファイルが見つかりません:\n  " + "\n  ".join(missing))
    if config.rendering.first_lines < 1 or config.rendering.continued_lines < 1:
        raise BuildError("コード画像の行数は1以上にしてください")
    if config.rendering.orphan_threshold < 0:
        raise BuildError("orphanThresholdは0以上にしてください")
    unsupported = set(config.formats) - {"epub", "mobi", "pdf"}
    if unsupported:
        raise BuildError(f"未対応の出力形式です: {', '.join(sorted(unsupported))}")


def safe_clean_dist(config: BookConfig) -> None:
    root = config.root.resolve()
    target = config.dist.resolve()
    if target == root or target.parent == root.parent:
        raise BuildError(f"安全でない生成先のため削除しません: {target}")
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise BuildError(f"生成先が書籍ルート外です: {target}") from exc
    if target.exists():
        shutil.rmtree(target)
        print(f"[CLEAN] {target}")


def ensure_output_dirs(config: BookConfig) -> dict[str, Path]:
    dirs = {
        "images": config.dist / "images",
        "code": config.dist / "images" / "code",
        "mermaid": config.dist / "images" / "mermaid",
        "slides": config.dist / "images" / "slides",
        "content": config.dist / "images" / "content",
    }
    for directory in (config.dist, *dirs.values()):
        directory.mkdir(parents=True, exist_ok=True)
    return dirs


def normalized_language(raw: str) -> str:
    language = raw.strip().split(maxsplit=1)[0].lower() if raw.strip() else "text"
    language = language.strip("{}.")
    aliases = {
        "c++": "cpp",
        "cc": "cpp",
        "cxx": "cpp",
        "hpp": "cpp",
        "h++": "cpp",
        "shell": "bash",
        "console": "text",
        "plaintext": "text",
    }
    return aliases.get(language, language or "text")


def split_chunks(
    lines: Sequence[str],
    has_title: bool,
    first_limit: int,
    continued_limit: int,
    orphan_threshold: int,
) -> list[list[str]]:
    """Split display lines while avoiding a tiny final image."""
    if not lines:
        return [[""]]
    chunks: list[list[str]] = []
    start = 0
    while start < len(lines):
        limit = first_limit if not chunks and has_title else continued_limit
        remaining = len(lines) - start
        size = min(remaining, limit)
        tail = remaining - size
        if 0 < tail <= orphan_threshold:
            size = remaining
        chunks.append(list(lines[start : start + size]))
        start += size
    return chunks


def split_code_chunks(
    lines: Sequence[str],
    has_title: bool,
    first_limit: int,
    continued_limit: int,
    orphan_threshold: int,
) -> list[list[str]]:
    """C++を、行数だけでなくメソッドやクラスの境界を優先して分ける。

    固定行で切ると、メソッド宣言だけが画像末尾へ残り、本体が次画像へ送られる。
    目標行数の前後で空行または閉じ波括弧を探し、見つからない場合だけ固定行へ
    戻す。最後の画像が数行だけにならない条件も同時に守る。
    """
    if not lines:
        return [[""]]
    chunks: list[list[str]] = []
    start = 0
    while start < len(lines):
        limit = first_limit if not chunks and has_title else continued_limit
        remaining = len(lines) - start
        if remaining <= limit:
            chunks.append(list(lines[start:]))
            break
        # 目標行数を機械的に守って、閉じ波括弧だけの画像を残さない。
        # 数行の超過なら、直前の意味のまとまりと同じ画像へ収める。
        if remaining - limit <= orphan_threshold:
            chunks.append(list(lines[start:]))
            break

        minimum_tail = orphan_threshold + 1
        lower = max(1, limit - 7)
        upper = min(remaining - minimum_tail, limit + 4)
        candidates: list[tuple[int, int, int]] = []
        for size in range(lower, upper + 1):
            previous = lines[start + size - 1].strip()
            following = lines[start + size].strip()
            if not previous:
                score = 4
            elif previous in ("}", "};"):
                score = 3
            elif previous.endswith(("}", "};")):
                score = 2
            elif not following:
                score = 1
            else:
                continue
            candidates.append((score, -abs(size - limit), size))

        size = max(candidates)[2] if candidates else min(limit, remaining)
        chunks.append(list(lines[start : start + size]))
        start += size
    return chunks


def strip_markdown(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[`*_~]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def chapter_title(markdown_text: str, fallback: str) -> str:
    match = HEADING_RE.search(markdown_text)
    return strip_markdown(match.group(2)) if match else fallback


def remove_first_heading(markdown_text: str) -> str:
    match = HEADING_RE.search(markdown_text)
    if not match:
        return markdown_text
    return markdown_text[: match.start()] + markdown_text[match.end() :]


def shorten_label(label: str) -> str:
    """題名の頭に付く決まり文句を落とす。

    「ここで確認するコード：X」「変更前から抜き出す箇所：X」は、本文では
    役割の合図として要るが、画像の帯では毎回同じ語が並ぶだけで場所を食う。
    帯に要るのは X のほうなので、決まり文句は落とす。
    """
    label = re.sub(r"^(?:ここで確認するコード|変更前から抜き出す箇所)[：:]\s*", "", label)
    # 引数リストは型名が長く、帯を1行で埋めてしまう。名前だけ残す。
    label = re.sub(r"\(([^)]{12,})\)", "()", label)
    return label.strip()


def trim_title(title: str, limit: int = 34) -> str:
    """帯へ収まる長さへ切り詰める。切るのは説明側で、名前は残す。"""
    if len(title) <= limit:
        return title
    if " ―― " in title:
        name, note = title.split(" ―― ", 1)
        room = limit - len(name) - 4
        if room >= 8:
            return f"{name} ―― {note[:room].rstrip()}…"
        return name[:limit]
    return title[:limit].rstrip() + "…"


def preceding_block_title(markdown_text: str, position: int) -> tuple[str | None, str | None]:
    """コード画像へ焼くタイトルと、本文から取り除く行を返す。

    本文の直前行がそのコードの題名になっている場合、画像にも同じ文字列を
    焼くと読者は同じ題名を2回読むことになる。そこで、題名として使った行は
    本文から取り除く。取り除く行が無いときは2つ目が None になる。

    タイトルの取り方は次の順で試す。

      1. 直前の見出し（## 〜 ######）
      2. 直前の太字だけの行（`**Order**`、`**ここで確認するコード：`X`** ―― 説明`）
      3. コード自身が定義している型・関数の名前

    3まで落ちるのは、直前が普通の文になっている場合である。ここで打ち切ると
    「タイトルのある画像とない画像が混ざる」ので、コードから拾って必ず付ける。
    """
    lines = markdown_text[:position].splitlines()
    for line in reversed(lines[-10:]):
        stripped = line.strip()
        if not stripped:
            continue
        heading = re.match(r"^#{2,6}\s+(.+?)\s*$", stripped)
        if heading:
            return strip_markdown(heading.group(1)), None
        bold = re.match(r"^\*\*(.+?)\*\*[：:]?\s*(?:[―—-]{2}\s*(.*))?$", stripped)
        if bold:
            label = shorten_label(strip_markdown(bold.group(1)))
            note = strip_markdown(bold.group(2) or "")
            title = f"{label} ―― {note}" if note else label
            return trim_title(title), line
        if stripped.startswith(("```", "<", "|", ">")):
            continue
        break
    return None, None


def preceding_diagram_title(markdown_text: str, position: int) -> tuple[str, str | None]:
    """図の題名と、キャプションへ移す太字題名の行を返す。

    図の直前に普通の導入文があっても、その少し前に置かれた太字題名を優先する。
    太字題名がなければ、直近の見出しを使い、すべての図を紙面だけで識別できる
    ようにする。
    """
    lines = markdown_text[:position].splitlines()
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        bold = re.match(r"^\*\*(.+?)\*\*$", stripped)
        if bold:
            return trim_title(strip_markdown(bold.group(1)), 48), line
        heading = re.match(r"^#{2,6}\s+(.+?)\s*$", stripped)
        if heading:
            return trim_title(strip_markdown(heading.group(1)), 48), None
    return "構造と処理の関係", None


def diagram_number(chapter_stem: str, index: int) -> str:
    """原稿ファイル名から、読者向けの図番号を作る。"""
    chapter = re.search(r"chapter0*(\d+)", chapter_stem)
    if chapter:
        prefix = str(int(chapter.group(1)))
    elif "preface" in chapter_stem:
        prefix = "序"
    else:
        prefix = safe_stem(chapter_stem)
    return f"図{prefix}-{index}"


def title_from_code(source: str, language: str) -> str:
    """コードや実行結果の中身から題名を作る。

    直前の行が普通の文になっている箇所では、見出しからは題名を取れない。
    そこで中身から拾う。ここで打ち切ると「題名のある画像とない画像が
    混ざる」ため、最後は種類だけでも必ず返す。
    """
    if language != "cpp":
        if re.search(r"^---\s*行\d", source, re.M):
            return "実行結果"
        if re.search(r"[├└│┌]", source):
            return "構成図"
        return "出力"

    kind = re.search(r"\b(class|struct|enum)\s+(\w+)", source)
    if kind:
        return kind.group(2)
    outer = re.search(r"\b(\w+)::(\w+)\s*\(", source)
    if outer:
        return f"{outer.group(1)}::{outer.group(2)}()"
    if re.search(r"\bint\s+main\s*\(", source):
        return "main()"
    free = re.search(r"^[A-Za-z_][\w:<>&*\s]*?\b(\w+)\s*\([^)]*\)\s*\{",
                     source, re.M)
    if free:
        return f"{free.group(1)}()"
    if re.search(r"^\s*#include", source, re.M):
        return "共通ヘッダー"
    return "コード（抜粋）"


def content_hash(*parts: Any) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:12]


def safe_stem(value: str) -> str:
    return re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE).strip("_")


def find_wkhtmltoimage() -> str | None:
    found = shutil.which("wkhtmltoimage") or shutil.which("wkhtmltoimage.exe")
    if found:
        return found
    candidate = Path(r"C:\Program Files\wkhtmltopdf\bin\wkhtmltoimage.exe")
    return str(candidate) if candidate.exists() else None


def find_mmdc() -> str | None:
    found = shutil.which("mmdc.cmd") or shutil.which("mmdc")
    if found:
        return found
    tools = config_tools_dir()
    for name in ("mmdc.cmd", "mmdc"):
        candidate = tools / "node_modules" / ".bin" / name
        if candidate.exists():
            return str(candidate)
    return None


def config_tools_dir() -> Path:
    return BOOK_ROOT / "script" / ".mermaid-tools"


def find_chromium() -> str | None:
    explicit = os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    if explicit and Path(explicit).exists():
        return explicit
    candidates = (
        "/opt/pw-browsers/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return shutil.which("chromium") or shutil.which("google-chrome")


def puppeteer_args(temp_dir: Path) -> list[str]:
    chromium = find_chromium()
    if not chromium:
        return []
    config_path = temp_dir / "puppeteer-config.json"
    config_path.write_text(
        json.dumps(
            {
                "executablePath": chromium,
                "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
            }
        ),
        encoding="utf-8",
    )
    return ["-p", str(config_path)]


def optimize_image(path: Path, max_width: int, max_height: int) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise BuildError("Pillowが未導入です。publishing/requirements.txtを導入してください") from exc

    with Image.open(path) as source:
        image = source.convert("RGB") if source.mode not in ("RGB", "RGBA") else source.copy()
    width, height = image.size
    if width > max_width or height > max_height:
        ratio = min(max_width / width, max_height / height)
        image = image.resize(
            (max(1, int(width * ratio)), max(1, int(height * ratio))),
            Image.Resampling.LANCZOS,
        )
    image.save(path, "PNG", optimize=True)


def pygments_lexer(language: str):
    try:
        from pygments.lexers import CLexer, CppLexer, TextLexer, get_lexer_by_name
        from pygments.util import ClassNotFound
    except ImportError as exc:
        raise BuildError("Pygmentsが未導入です。publishing/requirements.txtを導入してください") from exc
    if language == "cpp":
        return CppLexer()
    if language == "c":
        return CLexer()
    if language == "text":
        return TextLexer()
    try:
        return get_lexer_by_name(language)
    except ClassNotFound:
        return TextLexer()


CHANGE_MARKER = re.compile(r"←\s*.{0,12}?(?:追加|変更|削除|修正)")
# 同じ `←` を、フェーズ4〜6は「どちらの側か」の注釈にも使う。
# 「← 出て行く側（削除）」のような行を変更行と取り違えない。
NOT_A_CHANGE = re.compile(r"残る側|出て行く側|原因ID|問題ID|課題ID|リスクID")


def changed_lines(source_lines: list[str]) -> list[bool]:
    """変更行に印を付ける。原稿の `// ← 追加` のような目印を手がかりにする。

    目印の付き方は3つある。

      1. 目印だけの行（コメント行）――その下の実コード1つを指す
         （`;` `{` `}` で終わるまでを1つと数えるので、複数行にまたがる
         宣言も丸ごと入る。`{` で終わればその括弧の中身も入る）
      2. 「← ここから追加」――空行か「← ここまで」までを一続きで指す
      3. 波括弧で開く行に付いた目印――その括弧が閉じるまでを指す
         （`} else if (...) {  // ← 追加` で、枝の中身まで帯へ入る）

    「← 原因ID1（…）」「← 残る側」のような、変更ではない注釈は対象にしない。

    **画像のほぼ全部が変更行になったときは、帯を1本も引かない。** 帯は
    変わっていない行との対比で意味が出るもので、全面が青いと差が読み取れず、
    地の色が変わっただけになる。まるごと新しいブロックであることは、
    見出しの「（追加）」と本文が伝える。
    """
    flags = [
        bool(CHANGE_MARKER.search(line)) and not NOT_A_CHANGE.search(line)
        for line in source_lines
    ]

    def opens_block(line: str) -> bool:
        """行末のコメントを外したコードが `{` で終わるか。"""
        return line.split("//")[0].rstrip().endswith("{")

    def mark_block(start: int) -> None:
        """`{` で開いた行から、その括弧が閉じる手前までを変更行にする。"""
        depth = 1
        for follower in range(start + 1, len(source_lines)):
            body = source_lines[follower].strip()
            if body.startswith("}") and depth == 1:
                return
            flags[follower] = True
            depth += body.count("{") - body.count("}")
            if depth <= 0:
                return

    for index, matched in enumerate(list(flags)):
        if not matched:
            continue
        if not source_lines[index].strip().startswith("//"):
            if opens_block(source_lines[index]):
                mark_block(index)
            continue
        if "ここから" in source_lines[index]:
            for follower in range(index + 1, len(source_lines)):
                if not source_lines[follower].strip():
                    break
                flags[follower] = True
                if "ここまで" in source_lines[follower]:
                    break
            continue
        seen = 0
        for follower in range(index + 1, len(source_lines)):
            if not source_lines[follower].strip():
                continue
            flags[follower] = True
            code = source_lines[follower].split("//")[0].rstrip()
            seen += 1
            if code.endswith("{"):
                mark_block(follower)
                break
            if code.endswith((";", "}")) or seen >= 6:
                break

    body_lines = [i for i, line in enumerate(source_lines) if line.strip()]
    marked = sum(1 for i in body_lines if flags[i])
    if body_lines and marked / len(body_lines) >= 0.8:
        return [False] * len(source_lines)
    return flags


def render_code_block(
    config: BookConfig,
    output_dir: Path,
    chapter_stem: str,
    index: int,
    language: str,
    code: str,
    title: str | None,
    force: bool,
) -> list[Path]:
    settings = config.rendering
    source_lines = code.splitlines()
    splitter = split_code_chunks if language == "cpp" else split_chunks
    source_chunks = splitter(
        source_lines, bool(title), settings.first_lines,
        settings.continued_lines, settings.orphan_threshold,
    )
    # CSS is part of the cache key so a palette/font change cannot reuse stale PNGs.
    token = content_hash(
        language,
        title or "",
        code,
        settings,
        "semantic-code-boundaries-v2+changed-line-band",
        CODE_CSS,
        CODE_TITLE_STYLE,
    )
    prefix = f"{safe_stem(chapter_stem)}_code{index:03d}_{token}"
    expected = [output_dir / f"{prefix}_part{part:02d}.png" for part in range(len(source_chunks))]
    if not force and expected and all(path.exists() for path in expected):
        return expected

    wkhtmltoimage = find_wkhtmltoimage()
    if not wkhtmltoimage:
        raise BuildError("wkhtmltoimageが見つかりません。wkhtmltopdfを導入してください")
    try:
        import imgkit
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
    except ImportError as exc:
        raise BuildError("imgkit/Pygmentsが未導入です") from exc

    formatter = HtmlFormatter(full=False, linenos=False, noclasses=False)
    highlighted = highlight(code, pygments_lexer(language), formatter)
    pre_match = re.search(r"<pre[^>]*>(.*?)</pre>", highlighted, re.DOTALL)
    if not pre_match:
        raise BuildError(f"コード構文強調に失敗しました: {chapter_stem} code {index}")
    highlighted_lines = pre_match.group(1).split("\n")
    if highlighted_lines and highlighted_lines[-1] == "":
        highlighted_lines.pop()
    # Pygmentsの各行は元コードの各行と一対一。元コードで決めた意味境界を、
    # 構文強調後にもそのまま使う。
    chunks: list[list[str]] = []
    highlighted_start = 0
    for source_chunk in source_chunks:
        highlighted_end = highlighted_start + len(source_chunk)
        chunks.append(highlighted_lines[highlighted_start:highlighted_end])
        highlighted_start = highlighted_end
    expected = [output_dir / f"{prefix}_part{part:02d}.png" for part in range(len(chunks))]

    for stale in output_dir.glob(f"{safe_stem(chapter_stem)}_code{index:03d}_*_part*.png"):
        stale.unlink()
    css = CODE_CSS.replace("__WIDTH__", str(settings.code_width))
    imgkit_config = imgkit.config(wkhtmltoimage=wkhtmltoimage)
    options = {
        "format": "png",
        "encoding": "UTF-8",
        "quiet": "",
        "width": str(settings.code_width),
        "minimum-font-size": "1",
        "quality": "95",
        "disable-smart-width": "",
    }
    for part, (chunk, source_chunk, output_path) in enumerate(
        zip(chunks, source_chunks, expected)
    ):
        marked = changed_lines(source_chunk)
        body_lines: list[str] = []
        for offset, line_html in enumerate(chunk):
            if offset < len(marked) and marked[offset]:
                body_lines.append(f'<span class="chg">{line_html or "&nbsp;"}</span>')
            else:
                body_lines.append(line_html + "\n")
        title_html = ""
        if title and part == 0:
            title_html = (
                f'<div style="{CODE_TITLE_STYLE.format(width=settings.code_width)}">'
                f"{html.escape(title)}</div>"
            )
        document = (
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
            + css
            + f'</head><body style="width:{settings.code_width}px">'
            + title_html
            + f'<div style="background:#0F172A;padding:20px 0;width:{settings.code_width}px;box-sizing:border-box;">'
            + '<div class="highlight"><pre>'
            + "".join(body_lines).rstrip("\n")
            + "</pre></div></div></body></html>"
        )
        imgkit.from_string(
            document,
            str(output_path),
            options=options,
            config=imgkit_config,
        )
        optimize_image(output_path, settings.code_width, settings.max_height)
        print(f"  [CODE] {output_path.name}")
    return expected


def render_mermaid_block(
    config: BookConfig,
    output_dir: Path,
    chapter_stem: str,
    index: int,
    source: str,
    force: bool,
) -> Path:
    token = content_hash(source, config.rendering.mermaid_scale)
    output = output_dir / f"{safe_stem(chapter_stem)}_mermaid{index:03d}_{token}.png"
    if output.exists() and not force:
        return output
    mmdc = find_mmdc()
    if not mmdc:
        raise BuildError("Mermaid CLI (mmdc)が見つかりません")

    for stale in output_dir.glob(f"{safe_stem(chapter_stem)}_mermaid{index:03d}_*.png"):
        stale.unlink()
    with tempfile.TemporaryDirectory(prefix="kindle-mermaid-") as temp_name:
        temp_dir = Path(temp_name)
        input_path = temp_dir / "diagram.mmd"
        with input_path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(source.strip() + "\n")
        command = [
            mmdc,
            "-i",
            str(input_path),
            "-o",
            str(output),
            "--backgroundColor",
            "white",
            "--scale",
            str(config.rendering.mermaid_scale),
        ] + puppeteer_args(temp_dir)
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip()
            raise BuildError(
                f"Mermaid画像化に失敗しました: {chapter_stem} diagram {index}\n{details}"
            )
    optimize_image(output, config.rendering.code_width, config.rendering.max_height)
    print(f"  [MERMAID] {output.name}")
    return output


def target_matches(chapter_stem: str, targets: Sequence[str]) -> bool:
    return not targets or any(target.lower() in chapter_stem.lower() for target in targets)


def relative_to_dist(config: BookConfig, path: Path) -> str:
    return path.relative_to(config.dist).as_posix()


def copy_markdown_images(
    config: BookConfig,
    markdown_path: Path,
    markdown_text: str,
    content_dir: Path,
) -> str:
    def replacement(match: re.Match[str]) -> str:
        alt, raw_path = match.group(1), match.group(2)
        if HTTP_RE.match(raw_path):
            return match.group(0)
        source = (markdown_path.parent / raw_path).resolve()
        if not source.is_file():
            print(f"  [WARN] 本文画像が見つかりません: {markdown_path.name}: {raw_path}")
            return match.group(0)
        name = f"{safe_stem(markdown_path.stem)}_{content_hash(source, source.stat().st_mtime_ns)}{source.suffix.lower()}"
        destination = content_dir / name
        shutil.copy2(source, destination)
        return f"![{alt}]({relative_to_dist(config, destination)})"

    return MARKDOWN_IMAGE_RE.sub(replacement, markdown_text)


def replace_fenced_blocks(
    config: BookConfig,
    markdown_path: Path,
    markdown_text: str,
    dirs: dict[str, Path],
    force: bool,
) -> tuple[str, dict[str, int]]:
    code_index = 0
    mermaid_index = 0
    stats = {"code_blocks": 0, "code_images": 0, "mermaid_blocks": 0}
    # コード画像の帯、または図のキャプションへ移した題名の行。
    # あとで本文から取り除き、同じ題名を2回読ませない。
    consumed_titles: list[str] = []

    def replacement(match: re.Match[str]) -> str:
        nonlocal code_index, mermaid_index
        language = normalized_language(match.group(1))
        source = match.group(2).rstrip("\r\n")
        if language == "mermaid":
            mermaid_index += 1
            stats["mermaid_blocks"] += 1
            title, consumed = preceding_diagram_title(markdown_text, match.start())
            if consumed:
                consumed_titles.append(consumed)
            image_path = render_mermaid_block(
                config,
                dirs["mermaid"],
                markdown_path.stem,
                mermaid_index,
                source,
                force,
            )
            relative = relative_to_dist(config, image_path)
            number = diagram_number(markdown_path.stem, mermaid_index)
            caption = f"{number}　{title}"
            figure_classes = ["mermaid-image"]
            if re.search(r"^\s*%%\s*explanation-set\s*$", source, re.M):
                figure_classes.append("explanation-set")
            return (
                f'\n\n<figure class="{" ".join(figure_classes)}">'
                f'<img src="{relative}" alt="{html.escape(caption)}" />'
                f"<figcaption>{html.escape(caption)}</figcaption>"
                "</figure>\n\n"
            )

        code_index += 1
        stats["code_blocks"] += 1
        title, consumed = preceding_block_title(markdown_text, match.start())
        if not title:
            title = title_from_code(source, language)
        if consumed:
            consumed_titles.append(consumed)
        images = render_code_block(
            config,
            dirs["code"],
            markdown_path.stem,
            code_index,
            language,
            source,
            title,
            force,
        )
        stats["code_images"] += len(images)
        image_html = "".join(
            f'<img src="{relative_to_dist(config, image_path)}" '
            f'alt="{html.escape(title or language)} part {part}" />'
            for part, image_path in enumerate(images, 1)
        )
        return f'\n\n<div class="code-image-stack">{image_html}</div>\n\n'

    rendered = FENCE_RE.sub(replacement, markdown_text)
    # 画像へ焼いた題名は、本文から取り除く。同じ題名を2回読ませないため。
    for line in consumed_titles:
        rendered = rendered.replace(f"\n{line}\n", "\n", 1)
    return rendered, stats


def mark_visual_introductions(body_html: str) -> str:
    """図の導入と図をまとめ、指定した凡例では直後の説明表もまとめる。"""
    pattern = re.compile(
        # `.*?`だけでは前の段落から複数の見出し・段落をまたいでしまう。
        # 直近の1段落だけを選ぶため、途中の閉じpタグを越えない。
        r"<p(?P<attrs>[^>]*)>(?P<content>(?:(?!</p>).)*)</p>"
        r"(?P<gap>\s*)"
        r"(?P<figure><figure class=\"mermaid-image[^\"]*\">.*?</figure>)"
        r"(?P<explanation>\s*<p[^>]*>(?:(?!</p>).)*</p>\s*"
        r"<table>.*?</table>)?",
        re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        attrs = match.group("attrs")
        class_match = re.search(r'class="([^"]*)"', attrs)
        if class_match:
            classes = class_match.group(1).split()
            if "figure-intro" not in classes:
                classes.append("figure-intro")
            attrs = (
                attrs[: class_match.start()]
                + f'class="{" ".join(classes)}"'
                + attrs[class_match.end() :]
            )
        else:
            attrs += ' class="figure-intro"'
        explanation = match.group("explanation") or ""
        keep_explanation = "explanation-set" in match.group("figure")
        grouped_explanation = explanation if keep_explanation else ""
        trailing_explanation = "" if keep_explanation else explanation
        return (
            '<div class="visual-unit">'
            + f'<p{attrs}>{match.group("content")}</p>'
            + match.group("gap")
            + match.group("figure")
            + grouped_explanation
            + "</div>"
            + trailing_explanation
        )

    return pattern.sub(replace, body_html)


def copy_slide(config: BookConfig, chapter_stem: str, slide_dir: Path) -> Path | None:
    source = config.slides / f"{chapter_stem}.png"
    if not source.is_file():
        return None
    destination = slide_dir / source.name
    shutil.copy2(source, destination)
    optimize_image(destination, config.rendering.code_width, config.rendering.max_height)
    return destination


def anchor_sections(body_html: str, chapter_id: str) -> tuple[str, list[dict[str, str]]]:
    """章本文の各h2へidを振り、目次に載せる節の一覧を返す。

    Kindleには節内の進捗表示がないため、章単位の目次しか無いと読者は
    章の途中へ戻れない。h2（各章のフェーズと整理・振り返り）まで
    目次から辿れるようにする。
    """
    sections: list[dict[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        attrs, text = match.group(1), match.group(2)
        if "id=" in attrs:
            return match.group(0)
        section_id = f"{chapter_id}-s{len(sections) + 1}"
        label = re.sub(r"<[^>]+>", "", text).strip()
        # フェーズ見出しの色付きの丸は、字だけの目次には持ち込まない。
        label = label.lstrip("\u25cf").strip()
        sections.append({"id": section_id, "title": label})
        return f'<h2{attrs} id="{section_id}">{text}</h2>'

    body_html = re.sub(r"<h2([^>]*)>(.*?)</h2>", replace, body_html, flags=re.S)
    return body_html, sections


# Obsidian のコールアウト記法。原稿では執筆時の見分けに使うが、
# 読者には種別名を出さず、引用の中の小見出しとして見せる。
CALLOUT_LABELS = {
    "INFO": "補足",
    "NOTE": "補足",
    "TIP": "ヒント",
    "IMPORTANT": "重要",
    "WARNING": "注意",
    "CAUTION": "注意",
}


def unwrap_callouts(markdown_text: str) -> str:
    """`> [!INFO] 見出し` を、読者向けの小見出しへ変える。"""

    def replace(match: re.Match[str]) -> str:
        kind = match.group(1).upper()
        title = match.group(2).strip()
        label = CALLOUT_LABELS.get(kind, "補足")
        if title:
            return f"> **{title}**"
        return f"> **{label}**"

    return re.sub(r"^>\s*\[!(\w+)\]\s*(.*)$", replace, markdown_text, flags=re.M)


def markdown_to_html(markdown_text: str) -> str:
    try:
        import markdown
    except ImportError as exc:
        raise BuildError("Markdownが未導入です。publishing/requirements.txtを導入してください") from exc
    markdown_text = unwrap_callouts(markdown_text)
    markdown_text = colorize_phase_marks(markdown_text)
    markdown_text = re.sub(r"\[\[(?:[^|\]]*)\|([^\]]+)\]\]", r"\1", markdown_text)
    markdown_text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", markdown_text)
    return markdown.markdown(
        markdown_text,
        extensions=["extra", "sane_lists"],
        output_format="xhtml",
    )


# フェーズ見出しの色。読者は「いま何フェーズか」を色で見分ける。
PHASE_COLORS = {
    "1": "#1565c0",  # 現状把握
    "2": "#6a1b9a",  # 仮説立案
    "3": "#00838f",  # 問題特定
    "4": "#ef6c00",  # 原因分析
    "5": "#c9a227",  # 課題定義
    "6": "#c62828",  # 対策検討
    "7": "#2e7d32",  # 対策実施
}

PHASE_HEADING = re.compile(
    r"^(#{1,6}\s+)[\U0001F534-\U0001F7EB]\s*(フェーズ([1-7]))", re.MULTILINE
)


def colorize_phase_marks(markdown_text: str) -> str:
    """フェーズ見出しの絵文字を、色の付いた丸へ置き換える。

    `🟣` `🟠` のような四角・丸の絵文字は Emoji 12.0 で追加されたもので、
    **EPUB／PDFの組版に使うフォントには色付きの字形が無く、白黒の輪郭で出る。**
    フェーズ1（🔵）とフェーズ6（🔴）だけが色で出て、残りの5つは同じ灰色の記号に
    見えていた。「フェーズごとに色が違う」と本文で約束している以上、これでは
    約束を果たせない。

    そこで、どのフォントにもある `●`（U+25CF）へ置き換え、色はCSSで付ける。
    絵文字は原稿のままにしておき、置き換えはフェーズ番号で決める
    （フェーズ2と3は原稿では同じ `🟣` なので、絵文字では見分けられない）。
    """

    def replace(match: re.Match[str]) -> str:
        prefix, label, number = match.groups()
        color = PHASE_COLORS[number]
        return (
            f'{prefix}<span style="color:{color}">\u25cf</span> {label}'
        )

    return PHASE_HEADING.sub(replace, markdown_text)


def copy_cover(config: BookConfig, image_dir: Path) -> Path | None:
    if config.cover is None:
        return None
    if not config.cover.is_file():
        print(f"[WARN] 表紙画像が見つかりません: {config.cover}")
        return None
    destination = image_dir / ("cover" + config.cover.suffix.lower())
    shutil.copy2(config.cover, destination)
    return destination


def build_html(
    config: BookConfig,
    clean: bool,
    targets: Sequence[str],
    force: bool,
) -> Path:
    if clean:
        safe_clean_dist(config)
    dirs = ensure_output_dirs(config)
    cover = copy_cover(config, dirs["images"])
    chapters: list[dict[str, Any]] = []
    totals = {"code_blocks": 0, "code_images": 0, "mermaid_blocks": 0, "slides": 0}

    for index, markdown_path in enumerate(config.chapters, 1):
        print(f"[CHAPTER {index:02d}] {markdown_path.name}")
        source = markdown_path.read_text(encoding="utf-8-sig")
        title = chapter_title(source, markdown_path.stem)
        without_title = remove_first_heading(source)
        without_title = copy_markdown_images(
            config, markdown_path, without_title, dirs["content"]
        )
        chapter_force = force and target_matches(markdown_path.stem, targets)
        processed, stats = replace_fenced_blocks(
            config, markdown_path, without_title, dirs, chapter_force
        )
        for key, value in stats.items():
            totals[key] += value
        slide = copy_slide(config, markdown_path.stem, dirs["slides"])
        slide_html = ""
        if slide:
            totals["slides"] += 1
            slide_html = (
                '<div class="overview-slide">'
                f'<img src="{relative_to_dist(config, slide)}" alt="{html.escape(title)} 概要" />'
                "</div>"
            )
        body = markdown_to_html(processed)
        body = mark_visual_introductions(body)
        chapter_id = f"chapter-{safe_stem(markdown_path.stem)}"
        body, sections = anchor_sections(body, chapter_id)
        chapters.append(
            {
                "id": chapter_id,
                "title": title,
                "sections": sections,
                "html": f'<section><h1 id="{chapter_id}">{html.escape(title)}</h1>{slide_html}{body}</section>',
            }
        )

    cover_html = ""
    if cover:
        cover_html = (
            '<div class="book-cover">'
            f'<img src="{relative_to_dist(config, cover)}" alt="表紙" />'
            "</div>"
        )
    toc_entries: list[str] = []
    for chapter in chapters:
        toc_entries.append(
            f'<p class="toc-chapter"><a href="#{chapter["id"]}">'
            f'{html.escape(chapter["title"])}</a></p>'
        )
        toc_entries.extend(
            f'<p class="toc-section"><a href="#{section["id"]}">'
            f'{html.escape(section["title"])}</a></p>'
            for section in chapter["sections"]
        )
    toc = (
        '<nav class="book-toc"><h1 id="toc">目次</h1>'
        + "".join(toc_entries)
        + "</nav>"
    )
    document = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
        '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" lang="ja">'
        '<head><meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'
        f"<title>{html.escape(config.title)}</title><style>{BOOK_CSS}</style></head><body>"
        + cover_html
        + toc
        + "".join(chapter["html"] for chapter in chapters)
        + "</body></html>"
    )
    output = config.dist / "book.html"
    output.write_text(document, encoding="utf-8")
    manifest = {
        "title": config.title,
        "chapters": [path.name for path in config.chapters],
        **totals,
    }
    (config.dist / "build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"[HTML] {output} (code={totals['code_blocks']} blocks/{totals['code_images']} images, "
        f"mermaid={totals['mermaid_blocks']}, slides={totals['slides']})"
    )
    return output


def run_checked(command: Sequence[str], label: str, cwd: Path) -> None:
    print(f"[{label}] 開始")
    # CalibreのPDF出力はQtWebEngine（Chromium）で組版する。rootで動くコンテナ
    # では、Chromiumのサンドボックスを外さないと起動できない。
    environment = dict(os.environ, QTWEBENGINE_DISABLE_SANDBOX="1")
    result = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, errors="replace",
        env=environment,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise BuildError(f"{label}に失敗しました\n{details}")
    print(f"[{label}] 完了")


def convert_book(config: BookConfig, book_html: Path) -> None:
    converter = shutil.which("ebook-convert") or shutil.which("ebook-convert.exe")
    if not converter:
        raise BuildError("Calibreのebook-convertが見つかりません")
    epub = config.dist / "book.epub"
    command = [
        converter,
        str(book_html),
        str(epub),
        "--title",
        config.title,
        "--language",
        config.language,
        "--epub-version",
        "2",
        "--chapter",
        "//*[name()='h1']",
        "--level1-toc",
        "//h:h1",
        "--level2-toc",
        "//h:h2",
        "--chapter-mark",
        "pagebreak",
        "--disable-font-rescaling",
        "--margin-top",
        "0",
        "--margin-bottom",
        "0",
        "--margin-left",
        "0",
        "--margin-right",
        "0",
        "--pretty-print",
    ]
    if config.author:
        command.extend(["--authors", config.author])
    cover = next((config.dist / "images").glob("cover.*"), None)
    if cover:
        command.extend(["--cover", str(cover)])
    run_checked(command, "EPUB", config.dist)

    if "mobi" in config.formats:
        run_checked(
            [
                converter,
                str(epub),
                str(config.dist / "book.mobi"),
                "--output-profile",
                "kindle",
                "--mobi-file-type",
                "both",
            ],
            "MOBI",
            config.dist,
        )
    if "pdf" in config.formats:
        run_checked(
            [
                converter,
                str(epub),
                str(config.dist / "book.pdf"),
                "--pdf-page-numbers",
                "--paper-size",
                "a5",
                "--pdf-default-font-size",
                "12",
                "--pdf-mono-font-size",
                "12",
            ],
            "PDF",
            config.dist,
        )
    if "epub" not in config.formats:
        epub.unlink(missing_ok=True)


def extract_slides(config: BookConfig, pdf_path: Path, force: bool) -> None:
    try:
        import fitz
    except ImportError as exc:
        raise BuildError("PyMuPDFが未導入です。publishing/requirements.txtを導入してください") from exc
    pdf_path = pdf_path.resolve()
    if not pdf_path.is_file():
        raise BuildError(f"スライドPDFが見つかりません: {pdf_path}")
    if not config.slide_page_order:
        raise BuildError("book.jsonのslidePageOrderが空です")
    config.slides.mkdir(parents=True, exist_ok=True)

    with fitz.open(str(pdf_path)) as document:
        if len(document) != len(config.slide_page_order):
            raise BuildError(
                f"PDFは{len(document)}ページですが、slidePageOrderは"
                f"{len(config.slide_page_order)}件です。対応順を確認してください"
            )
        existing = [
            config.slides / f"{stem}.png"
            for stem in config.slide_page_order
            if (config.slides / f"{stem}.png").exists()
        ]
        if existing and not force:
            raise BuildError(
                "既存スライドがあります。上書きする場合は--forceを指定してください:\n  "
                + "\n  ".join(str(path) for path in existing)
            )
        matrix = fitz.Matrix(config.rendering.slide_dpi / 72, config.rendering.slide_dpi / 72)
        for page_index, stem in enumerate(config.slide_page_order):
            output = config.slides / f"{stem}.png"
            temporary = config.slides / f".{stem}.tmp.png"
            document[page_index].get_pixmap(matrix=matrix, alpha=False).save(str(temporary))
            temporary.replace(output)
            print(f"[SLIDE] page {page_index + 1:02d} -> {output.name}")


def inventory(config: BookConfig) -> None:
    total_code = 0
    total_mermaid = 0
    print("章ファイル / コード / Mermaid / スライド")
    for path in config.chapters:
        text = path.read_text(encoding="utf-8-sig")
        languages = [normalized_language(match.group(1)) for match in FENCE_RE.finditer(text)]
        mermaid_count = sum(language == "mermaid" for language in languages)
        code_count = len(languages) - mermaid_count
        total_code += code_count
        total_mermaid += mermaid_count
        slide = config.slides / f"{path.stem}.png"
        print(
            f"  {path.name}: code={code_count}, mermaid={mermaid_count}, "
            f"slide={'OK' if slide.is_file() else 'MISSING'}"
        )
    print(
        f"合計: chapters={len(config.chapters)}, code={total_code}, "
        f"mermaid={total_mermaid}, slides="
        f"{sum((config.slides / f'{path.stem}.png').is_file() for path in config.chapters)}"
    )


def doctor() -> int:
    modules = {
        "markdown": "Markdown",
        "PIL": "Pillow",
        "pygments": "Pygments",
        "fitz": "PyMuPDF",
        "imgkit": "imgkit",
    }
    executables = {
        "wkhtmltoimage": find_wkhtmltoimage(),
        "mmdc": find_mmdc(),
        "ebook-convert": shutil.which("ebook-convert") or shutil.which("ebook-convert.exe"),
    }
    failed = False
    for module, label in modules.items():
        found = importlib.util.find_spec(module) is not None
        print(f"{'OK' if found else 'MISSING'}: {label}")
        failed |= not found
    for label, path in executables.items():
        print(f"{'OK' if path else 'MISSING'}: {label}{f' -> {path}' if path else ''}")
        failed |= path is None
    return 1 if failed else 0


def add_build_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--clean", action="store_true", help="publishing/distだけを削除して再生成")
    parser.add_argument("--force", action="store_true", help="対象章の既存画像を作り直す")
    parser.add_argument(
        "--target",
        nargs="+",
        default=[],
        metavar="CHAPTER",
        help="--forceの対象章（部分一致）。未生成画像は対象外でも生成する",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="必要なPythonモジュールと外部コマンドを確認")
    commands.add_parser("inventory", help="原稿と未配置スライドを一覧化")
    slides = commands.add_parser("slides", help="概要スライドPDFを章別PNGへ分割")
    slides.add_argument("--pdf", type=Path, required=True)
    slides.add_argument("--force", action="store_true", help="既存の章別PNGを上書き")
    html_parser = commands.add_parser("html", help="画像生成・全章結合を行いHTMLまで作成")
    add_build_arguments(html_parser)
    all_parser = commands.add_parser("all", help="HTML、EPUB、MOBI、PDFを生成")
    add_build_arguments(all_parser)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "doctor":
        return doctor()
    try:
        config = load_config(args.config)
        if args.command == "inventory":
            inventory(config)
            return 0
        if args.command == "slides":
            extract_slides(config, args.pdf, args.force)
            return 0
        book_html = build_html(config, args.clean, args.target, args.force)
        if args.command == "all":
            convert_book(config, book_html)
        return 0
    except BuildError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
