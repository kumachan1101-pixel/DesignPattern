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
  text-align: justify;
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
th { background: #f5f5f5; }
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
}
.book-cover, .book-toc { page-break-after: always; text-align: center; }
.book-toc { text-align: left; }
.book-toc p { margin: 0.55em 0; }
.overview-slide, .mermaid-image {
  margin: 0.6em 0 1.2em;
  page-break-inside: avoid;
  text-align: center;
}
.overview-slide img, .mermaid-image img { border: 1px solid #ddd; }
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


def preceding_block_title(markdown_text: str, position: int) -> str | None:
    lines = markdown_text[:position].splitlines()
    for line in reversed(lines[-10:]):
        stripped = line.strip()
        if not stripped:
            continue
        heading = re.match(r"^#{2,6}\s+(.+?)\s*$", stripped)
        if heading:
            return strip_markdown(heading.group(1))
        bold = re.match(r"^\*\*(.+?)\*\*[：:]?\s*$", stripped)
        if bold:
            return strip_markdown(bold.group(1))
        if stripped.startswith(("```", "<", "|", ">")):
            continue
        break
    return None


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
    source_chunks = split_chunks(
        code.splitlines(),
        bool(title),
        settings.first_lines,
        settings.continued_lines,
        settings.orphan_threshold,
    )
    # CSS is part of the cache key so a palette/font change cannot reuse stale PNGs.
    token = content_hash(
        language,
        title or "",
        code,
        settings,
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
    chunks = split_chunks(
        highlighted_lines,
        bool(title),
        settings.first_lines,
        settings.continued_lines,
        settings.orphan_threshold,
    )
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
    for part, (chunk, output_path) in enumerate(zip(chunks, expected)):
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
            + "\n".join(chunk)
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
        input_path.write_text(source.strip() + "\n", encoding="utf-8", newline="\n")
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

    def replacement(match: re.Match[str]) -> str:
        nonlocal code_index, mermaid_index
        language = normalized_language(match.group(1))
        source = match.group(2).rstrip("\r\n")
        if language == "mermaid":
            mermaid_index += 1
            stats["mermaid_blocks"] += 1
            image_path = render_mermaid_block(
                config,
                dirs["mermaid"],
                markdown_path.stem,
                mermaid_index,
                source,
                force,
            )
            relative = relative_to_dist(config, image_path)
            return (
                "\n\n<div class=\"mermaid-image\">"
                f'<img src="{relative}" alt="{html.escape(markdown_path.stem)} diagram {mermaid_index}" />'
                "</div>\n\n"
            )

        code_index += 1
        stats["code_blocks"] += 1
        title = preceding_block_title(markdown_text, match.start())
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

    return FENCE_RE.sub(replacement, markdown_text), stats


def copy_slide(config: BookConfig, chapter_stem: str, slide_dir: Path) -> Path | None:
    source = config.slides / f"{chapter_stem}.png"
    if not source.is_file():
        return None
    destination = slide_dir / source.name
    shutil.copy2(source, destination)
    optimize_image(destination, config.rendering.code_width, config.rendering.max_height)
    return destination


def markdown_to_html(markdown_text: str) -> str:
    try:
        import markdown
    except ImportError as exc:
        raise BuildError("Markdownが未導入です。publishing/requirements.txtを導入してください") from exc
    markdown_text = re.sub(r"\[\[(?:[^|\]]*)\|([^\]]+)\]\]", r"\1", markdown_text)
    markdown_text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", markdown_text)
    return markdown.markdown(
        markdown_text,
        extensions=["extra", "sane_lists"],
        output_format="xhtml",
    )


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
        chapter_id = f"chapter-{safe_stem(markdown_path.stem)}"
        chapters.append(
            {
                "id": chapter_id,
                "title": title,
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
    toc = '<nav class="book-toc"><h1 id="toc">目次</h1>' + "".join(
        f'<p><a href="#{chapter["id"]}">{html.escape(chapter["title"])}</a></p>'
        for chapter in chapters
    ) + "</nav>"
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
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, errors="replace")
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
