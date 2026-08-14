from pathlib import Path
import re
import subprocess
import shutil
import os
import sys
from pygments import highlight
from pygments.lexers import CLexer
from pygments.formatters import HtmlFormatter
import imgkit

# ========= 設定 =========
CHAPTER_DIR = Path("../02_章別")  # 修正: 02_章別を対象にする
DIST_DIR = Path("../05_生成/dist")
IMG_DIR = DIST_DIR / "images"
MERMAID_DIR = IMG_DIR / "mermaid"
CODE_IMG_DIR = IMG_DIR / "code"
SLIDES_IMG_DIR = IMG_DIR / "slides"

# PDF資料のパス（04_workから見た相対パス）
# 旧: RESOURCE_PDF_PATH = Path("../03_資料/SOLID_C_Architecture.pdf")
SLIDES_DIR = Path("../03_資料/png")

# ファイルの先頭prefix "01_" などの章番号文字列から、MDファイルインデックスへのマッピング
# (sorted(02_章別/*.md)した結果の chapter_index に合致させる)
CHAPTER_NUM_TO_MD_INDEX = {
    "01": 0,   # 01_section_1 (序論)
    "02": 1,   # 02_第1部
    "03": 2,   # 03_第1部 第1章
    "04": 3,   # 04_第1部 第2章
    "05": 5,   # 05_第1部 第3章
    "06": 7,   # 06_第1部 第4章
    "07": 8,   # 07_第1部 第5章
    "08": 10,  # 08_第1部 第6章
    "09": 12,  # 09_第1部 第7章
    "10": 14,  # 10_第1部 まとめ
    "11": 15,  # 11_第2部
    "12": 16,  # 12_第2部 第8章
    "13": 18,  # 13_第2部 第9章
    "14": 20,  # 14_第2部 第10章
    "15": 22,  # 15_第2部 第11章
    "16": 24,  # 16_第2部 第12章
    "17": 27,  # 17_第2部 第13章
    "18": 29,  # 18_第2部 第14章
    "19": 31,  # 19_第2部 第15章
    "20": 32,  # 20_おわりに
}

# ユーザー指定の目次タイトルマッピング
CUSTOM_TOC_TITLES = {
    "01_section_1": "はじめに",
    "02_第1部 導入：基礎道具編の目的と学習ロードマップ": "第1部 導入：基礎道具編の目的と学習ロードマップ",
    "03_第1部 第1章 `static`キーワード - 情報隠蔽による依存の切断と実装の自由": "第1部 第1章 `static`キーワード - 情報隠蔽による依存の切断と実装の自由",
    "04_第1部 第2章 関数ポインタと間接呼び出し - 動的結合の実現_01": "第1部 第2章 関数ポインタと間接呼び出し - 動的結合の実現",
    "04_第1部 第2章 関数ポインタと間接呼び出し - 動的結合の実現": "第1部 第2章 関数ポインタと間接呼び出し - 動的結合の実現",
    "05_第1部 第3章 構造体設計とコンポジション - データと責任の統合_01": "第1部 第3章 構造体設計とコンポジション - データと責任の統合",
    "05_第1部 第3章 構造体設計とコンポジション - データと責任の統合": "第1部 第3章 構造体設計とコンポジション - データと責任の統合",
    "06_第1部 第4章 不完全型と不透明ポインタ - 型情報の隠蔽による契約のカプセル化": "第1部 第4章 不完全型と不透明ポインタ - 型情報の隠蔽による契約のカプセル化",
    "07_第1部 第5章 モジュール構成とヘッダ設計 - 最小限の契約公開と依存の最小化_01": "第1部 第5章 モジュール構成とヘッダ設計 - 最小限の契約公開と依存の最小化",
    "07_第1部 第5章 モジュール構成とヘッダ設計 - 最小限の契約公開と依存の最小化": "第1部 第5章 モジュール構成とヘッダ設計 - 最小限の契約公開と依存の最小化",
    "08_第1部 第6章 エラーハンドリングパターン - 堅牢な契約_01": "第1部 第6章 エラーハンドリングパターン - 堅牢な契約",
    "08_第1部 第6章 エラーハンドリングパターン - 堅牢な契約": "第1部 第6章 エラーハンドリングパターン - 堅牢な契約",
    "09_第1部 第7章 メモリ管理パターン - 責任の明確化_01": "第1部 第7章 メモリ管理パターン - 責任の明確化",
    "09_第1部 第7章 メモリ管理パターン - 責任の明確化": "第1部 第7章 メモリ管理パターン - 責任の明確化",
    "10_第1部 総括 堅牢なコードの「基礎」は固まった": "第1部 総括 堅牢なコードの「基礎」は固まった",
    "11_第2部 導入：原則編の目的と学習ロードマップ": "第2部 導入：原則編の目的と学習ロードマップ",
    "12_第2部 第8章 単一責任原則 (SRP) 変更の軸を明確にする設計指針_01": "第2部 第8章 単一責任原則 (SRP): 変更の軸を明確にする設計指針",
    "12_第2部 第8章 単一責任原則 (SRP) 変更の軸を明確にする設計指針": "第2部 第8章 単一責任原則 (SRP): 変更の軸を明確にする設計指針",
    "13_第2部 第9章 開放閉鎖原則（OCP）：拡張のために開き、修正に対して閉じる_01": "第2部 第9章 開放閉鎖原則（OCP）：拡張のために開き、修正に対して閉じる",
    "13_第2部 第9章 開放閉鎖原則（OCP）：拡張のために開き、修正に対して閉じる": "第2部 第9章 開放閉鎖原則（OCP）：拡張のために開き、修正に対して閉じる",
    "14_第2部 第10章 リスコフ置換原則 (LSP) 多態性の安全性と契約の保証_01": "第2部 第10章 リスコフ置換原則 (LSP): 多態性の安全性と契約の保証",
    "14_第2部 第10章 リスコフ置換原則 (LSP) 多態性の安全性と契約の保証": "第2部 第10章 リスコフ置換原則 (LSP): 多態性の安全性と契約の保証",
    "15_第2部 第11章 インターフェース分離原則 (ISP) 不要な依存の排除とモジュール結合度の最小化_01": "第2部 第11章 インターフェース分離原則 (ISP): 不要な依存の排除とモジュール結合度の最小化",
    "15_第2部 第11章 インターフェース分離原則 (ISP) 不要な依存の排除とモジュール結合度の最小化": "第2部 第11章 インターフェース分離原則 (ISP): 不要な依存の排除とモジュール結合度の最小化",
    "16_第2部 第12章 依存性逆転原則（DIP）：抽象への依存とテスト容易性_01": "第2部 第12章 依存性逆転原則（DIP）：抽象への依存とテスト容易性",
    "16_第2部 第12章 依存性逆転原則（DIP）：抽象への依存とテスト容易性": "第2部 第12章 依存性逆転原則（DIP）：抽象への依存とテスト容易性",
    "17_第2部 第13章 統合実践（基本）_01": "第2部 第13章 統合実践（基本）",
    "17_第2部 第13章 統合実践（基本）": "第2部 第13章 統合実践（基本）",
    "18_第2部 第14章 統合実践（応用）_01": "第2部 第14章 統合実践（応用）",
    "18_第2部 第14章 統合実践（応用）": "第2部 第14章 統合実践（応用）",
    "19_第2部 第15章：SOLID原則を「使える思考」にする": "第2部 第15章 SOLID原則を「使える思考」にする",
    "20_おわりに": "おわりに"
}

BOOK_HTML = DIST_DIR / "book.html"
BOOK_EPUB = DIST_DIR / "book.epub"
BOOK_MOBI = DIST_DIR / "book.mobi"

COVER_IMAGE = Path("../05_生成/cover.jpg")

# Kindle互換性設定
MAX_IMAGE_WIDTH = 2000
MAX_IMAGE_HEIGHT = 1600

# 【重要】ご自身の環境に合わせてパスを変更してください
MMDC = r"C:\Users\kumac\AppData\Roaming\npm\mmdc.cmd"

TARGET_CODE_IMAGE_HEIGHT = 1400  # コード画像の目標高さ
LINE_HEIGHT_PX = 55              # 1行あたりの推定高さ (line-height 1.45 * font-size 38px)

IMGKIT_OPTIONS = {
    "format": "png",
    "encoding": "UTF-8",
    "quiet": "",
    "width": str(MAX_IMAGE_WIDTH),
    "minimum-font-size": "1",    # フォントサイズ縮小を防止
    "quality": "95",
    "disable-smart-width": "",   # 指定幅を厳守
}


# 視認性を最大化したCSS設定（ファイル名見出し・色分け強化版）
CODE_CSS = """
<style>
/* 全体の背景 */
html, body {
  margin: 0; padding: 0; 
  background: #0F172A !important; 
  width: 2000px !important;
  max-width: 2000px !important;
  box-sizing: border-box; 
  overflow: hidden;
}

/* Pygmentsハイライトコンテナ */
.highlight {
  background: #0F172A !important;
  font-size: 48px !important;
  line-height: 1.6 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-weight: 500 !important;
  box-sizing: border-box;
  width: 2000px !important;
  padding: 0 40px !important; /* 両端の余白 */
  display: block !important;
}

/* コード表示領域 */
.highlight pre {
  background: #0F172A !important;
  color: #FFFFFF !important;
  padding: 10px 0 !important;
  margin: 0 !important;
  font-size: 48px !important;
  line-height: 1.6 !important;
  font-weight: 500 !important;
  white-space: pre-wrap !important;
  word-wrap: break-word !important;
  word-break: break-all !important;
  display: block !important;
  box-sizing: border-box;
}

/* 1. コメント */
.highlight .c1, .highlight .cm, .highlight .c, .highlight .cp {
  color: #64748B !important;
  font-weight: 600 !important;
  font-style: italic !important;
}
/* 2. prefix (#include, $) */
.highlight .cp {
  color: #C4B5FD !important;
  font-weight: bold !important;
  font-style: normal !important;
}
/* 3. string ("文字列", <ヘッダ>) */
.highlight .cpf, .highlight .s, .highlight .s1, .highlight .s2 {
  color: #A3E635 !important;
  font-weight: 600 !important;
}
/* 4. keyword (if, return など) */
.highlight .k, .highlight .kn, .highlight .kr, .highlight .kd {
  color: #38BDF8 !important;
  font-weight: bold !important;
}
/* 5. type (int, struct など) */
.highlight .kt, .highlight .nc {
  color: #818CF8 !important;
  font-weight: 600 !important;
}
/* 6. number (数値リテラル) */
.highlight .mi, .highlight .mf, .highlight .mh {
  color: #FBBF24 !important;
  font-weight: 600 !important;
}
/* 関数名 */
.highlight .nf, .highlight .nb { color: #A78BFA !important; font-weight: bold !important; }
/* 変数名・括弧・演算子 */
.highlight .n, .highlight .p, .highlight .o { color: #FFFFFF !important; }
/* 標準出力 */
.highlight .go { color: #FFFFFF !important; opacity: 0.8 !important; font-weight: 600 !important; }
</style>
"""


# MAX_LINES_PER_IMAGE は動的計算に置き換え（TARGET_CODE_IMAGE_HEIGHT / LINE_HEIGHT_PX ベース）


# ========= 初期化 =========
def force_remove_dist():
    """distフォルダを確実に削除して再作成する"""
    if DIST_DIR.exists():
        print(f"[INIT] {DIST_DIR} をクリーンアップ中...")
        def handle_remove_readonly(func, path, excinfo):
            import stat
            os.chmod(path, stat.S_IWRITE)
            func(path)
        try:
            shutil.rmtree(DIST_DIR, onerror=handle_remove_readonly)
        except Exception as e:
            print(f"[WARN] distの削除失敗: {e}")

    MERMAID_DIR.mkdir(parents=True, exist_ok=True)
    CODE_IMG_DIR.mkdir(parents=True, exist_ok=True)
    SLIDES_IMG_DIR.mkdir(parents=True, exist_ok=True)

    src_jpg = CHAPTER_DIR / "solid_design.jpg"
    if src_jpg.exists():
        shutil.copy(src_jpg, DIST_DIR / src_jpg.name)
        print(f"[INIT] {src_jpg.name} を dist へコピーしました")
    else:
        print(f"[WARN] {src_jpg} が見つかりません")

    print(f"[INIT] ディレクトリ準備完了")

force_remove_dist()


def optimize_image(img_path: Path):
    """画像をKindle互換サイズに最適化"""
    try:
        from PIL import Image
        img = Image.open(img_path)
        width, height = img.size
        if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
            ratio = min(MAX_IMAGE_WIDTH / width, MAX_IMAGE_HEIGHT / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            img.save(img_path, "PNG", optimize=True)
            print(f"    画像最適化: {width}x{height} -> {new_size[0]}x{new_size[1]}")
        else:
            img.save(img_path, "PNG", optimize=True)
    except ImportError:
        pass
    except Exception as e:
        print(f"    [WARN] 画像最適化失敗: {e}")

# 表紙画像をコピー
cover_dest = None
if COVER_IMAGE.exists():
    cover_dest = IMG_DIR / COVER_IMAGE.name
    shutil.copy(COVER_IMAGE, cover_dest)
    print(f"[COVER] 表紙画像をコピー: {COVER_IMAGE.name}")
    optimize_image(cover_dest)
elif Path("cover.jpg").exists():
    COVER_IMAGE = Path("cover.jpg")
    cover_dest = IMG_DIR / COVER_IMAGE.name
    shutil.copy(COVER_IMAGE, cover_dest)
    print(f"[COVER] 表紙画像をコピー: {COVER_IMAGE.name}")
    optimize_image(cover_dest)
else:
    print("[INFO] 表紙画像が見つかりません")


# ========= スライド画像処理 =========
def gather_slide_images() -> dict:
    """用意されたスライド画像(PNG)を収集し、MDファイルインデックスに対応付ける"""
    if not SLIDES_DIR.exists():
        print(f"[WARN] スライドフォルダが見つかりません: {SLIDES_DIR}")
        return {}

    print(f"[スライド画像] {SLIDES_DIR.name} 内の画像を各章に配分中...")
    chapter_images = {}  # {md_index: [image_rel_paths]}

    for chapter_num_str, chapter_index in CHAPTER_NUM_TO_MD_INDEX.items():
        img_path = SLIDES_DIR / f"chapter_{chapter_num_str}.png"
        if not img_path.exists():
            print(f"[INFO] {img_path.name} は存在しません。スキップします。")
            continue
            
        # EPUBパッケージングのため、dist/images/slides へコピーする
        out_path = SLIDES_IMG_DIR / img_path.name
        import shutil
        shutil.copy(img_path, out_path)
        optimize_image(out_path)

        rel_path = f"images/slides/{img_path.name}"
        
        if chapter_index not in chapter_images:
            chapter_images[chapter_index] = []
        chapter_images[chapter_index].append(rel_path)
        
        print(f"  -> 章{chapter_index} ({img_path.name}) を配分")

    print(f"[スライド画像] {len(chapter_images)}章に配分完了")
    return chapter_images



# 事前生成されたスライド画像(PNG)を各章に配分
chapter_pdf_images = gather_slide_images()


# ========= Mermaid =========
def sanitize_mermaid(code: str) -> str:
    lines = code.splitlines()
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    code = "\n".join(cleaned_lines)
    code = code.replace('　', '  ')
    code = re.sub(r'graph\s+LR\b', 'graph TB', code, flags=re.I)
    code = re.sub(r'flowchart\s+LR\b', 'flowchart TB', code, flags=re.I)
    code = re.sub(r'^(graph|flowchart|classDiagram|mindmap|sequenceDiagram)(.*)$', r'\1\2', code, flags=re.M)
    return code.strip()

def mermaid_to_image(code: str, out_png: Path, img_index:int) -> bool:
    cleaned_code = sanitize_mermaid(code)
    tmp_mmd = out_png.parent / f"temp_diag_{img_index}.mmd"
    with open(tmp_mmd, "w", encoding="utf-8", newline="\n") as f:
        f.write(cleaned_code)
    
    try:
        cmd = [
            MMDC, "-i", str(tmp_mmd), "-o", str(out_png),
            "--backgroundColor", "white", "--scale", "3",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if res.returncode != 0:
            print(f"[ERROR] mmdc stderr: {res.stderr}")
            return False
        print(f"  -> Mermaid画像 {img_index} 作成成功")
        optimize_image(out_png)
        return True
    except Exception as e:
        print(f"[ERROR] Mermaid例外: {e}")
        return False
    finally:
        if tmp_mmd.exists(): tmp_mmd.unlink()

# ========= ソースコード画像化（ファイル名ヘッダー改善版） =========
def code_to_images_with_title(code: str, md_stem: str, code_index: int, title: str = None) -> list:
    lines = code.splitlines()
    images = []
    
    print(f"  コード全体: {len(lines)}行")
    
    formatter = HtmlFormatter(full=False, linenos=False, noclasses=False)
    full_highlighted = highlight(code, CLexer(), formatter)
    
    pre_match = re.search(r'<pre[^>]*>(.*?)</pre>', full_highlighted, re.DOTALL)
    if not pre_match: return []
    
    highlighted_lines = pre_match.group(1).split('\n')
    start_line = 0
    part_num = 0
    
    # 固定行数で統一（サイズの安定化）
    MAX_LINES = 22
    # タイトル付き最初の画像は少し減らす
    MAX_LINES_WITH_TITLE = 19
    # オーファン防止：残りがこの行数以下なら前のチャンクに含める
    ORPHAN_THRESHOLD = 4
    
    while start_line < len(highlighted_lines):
        is_first = (part_num == 0 and title)
        max_lines_for_chunk = MAX_LINES_WITH_TITLE if is_first else MAX_LINES
        remaining = len(highlighted_lines) - start_line
        chunk_size = min(remaining, max_lines_for_chunk)
        
        # オーファン防止：次のチャンクが少なすぎる場合、今のチャンクに含める
        next_remaining = remaining - chunk_size
        if 0 < next_remaining <= ORPHAN_THRESHOLD:
            chunk_size = remaining  # 全部含める
        
        end_line = start_line + chunk_size
        chunk_html = '\n'.join(highlighted_lines[start_line:end_line])
        
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{CODE_CSS}
</head>
<body style="margin: 0; padding: 0; background-color: #0F172A; width: 2000px;">
"""
        # ファイル名（タイトル）の見やすさを改善
        if title and part_num == 0:
            html += f"""<div style="background: #1E293B; color: #F8FAFC; padding: 25px 40px; 
    border-bottom: 2px solid #334155;
    font-size: 48px; font-weight: bold; font-family: 'JetBrains Mono', monospace;
    display: flex; align-items: center; gap: 15px; width: 2000px; box-sizing: border-box;">
    {title}
</div>
"""
        # 横幅の背景色拡張のため、さらにwrapperを追加
        html += f"""<div style="background: #0F172A; padding-top: 20px; padding-bottom: 20px; width: 2000px; box-sizing: border-box;">
<div class="highlight"><pre>{chunk_html}</pre></div>
</div>
</body>
</html>"""
        img_name = f"{md_stem}_code{code_index}_part{part_num}.png"
        out_path = CODE_IMG_DIR / img_name
        
        try:
            imgkit.from_string(html, str(out_path), options=IMGKIT_OPTIONS)
            print(f"  -> 画像作成: {img_name}")
            optimize_image(out_path)
            images.append(img_name)
        except Exception as e:
            print(f"[ERROR] 画像生成失敗 {img_name}: {e}")
        
        start_line = end_line
        part_num += 1
    
    return images


# ========= Markdown要素処理 =========
def md_links_to_html(text: str) -> str:
    return re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', r'<a href="\2">\1</a>', text)

def inline_code_to_html(text: str) -> str:
    return re.sub(r'`([^`\n]+)`', r"<code style='font-family: monospace; font-size: 0.95em; background-color: #f5f5f5; padding: 0.15em 0.4em; border: 1px solid #e0e0e0; font-weight: 600;'>\1</code>", text)

def emphasize_code_symbols(text: str) -> str:
    def safe_sub(pattern, repl, text):
        parts = re.split(r'(<a\s+[^>]+>.*?</a>)', text, flags=re.S)
        for i in range(len(parts)):
            if not parts[i].startswith('<a '):
                parts[i] = re.sub(pattern, repl, parts[i])
        return ''.join(parts)

    protected = []
    def protect_include(m):
        protected.append(m.group(0))
        return f"@@INCLUDE_{len(protected)-1}@@"
    
    text = re.sub(r'#include\s*<[^>]+>', protect_include, text)

    text = safe_sub(
        r'\b([a-zA-Z_][a-zA-Z0-9_]*\.(?:c|h))\b',
        r"<code style='font-family: monospace; font-weight: 600; background-color: #f5f5f5; padding: 0.1em 0.3em; border: 1px solid #e0e0e0;'>\1</code>",
        text
    )
    text = safe_sub(
        r'\b([a-zA-Z_][a-zA-Z0-9_]*)\(\)',
        r"<code style='font-family: monospace; font-weight: 600; background-color: #e3f2fd; padding: 0.1em 0.3em; border: 1px solid #bbdefb;'>\1()</code>",
        text
    )

    for i, inc in enumerate(protected):
        text = text.replace(f"@@INCLUDE_{i}@@", inc)
    return text

def md_images_to_html(md_text: str) -> str:
    code_blocks = []
    def _cb(m):
        code_blocks.append(m.group(0))
        return f"@@CODEBLOCK_{len(code_blocks)-1}@@"
    md_text = re.sub(r"```[\s\S]*?```", _cb, md_text)

    inline_codes = []
    def _ic(m):
        inline_codes.append(m.group(0))
        return f"@@INLINECODE_{len(inline_codes)-1}@@"
    md_text = re.sub(r"`[^`]*`", _ic, md_text)

    def _img(m):
        alt = m.group(1); path = m.group(2).strip()
        if not path.startswith("images/"): path = f"images/{Path(path).name}"
        return f'<img src="{path}" alt="{alt}" style="max-width:100%; height:auto;" />'
    md_text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _img, md_text)

    for i, c in enumerate(inline_codes): md_text = md_text.replace(f"@@INLINECODE_{i}@@", c)
    for i, c in enumerate(code_blocks): md_text = md_text.replace(f"@@CODEBLOCK_{i}@@", c)
    return md_text


# ========= Markdown処理 =========
def process_md(md_path: Path, chapter_index: int = -1):
    print(f"\n[MD] {md_path.name}")
    
    try:
        text = md_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = md_path.read_text(encoding="shift_jis")

    # 目次用タイトルの決定（マッピングから取得、なければファイル名）
    # ファイルが分割されている場合(_01, _02など)、ベース名でマッチングを試みる
    base_stem = re.sub(r'_\d+$', '', md_path.stem)
    chapter_title = CUSTOM_TOC_TITLES.get(md_path.stem) or CUSTOM_TOC_TITLES.get(base_stem) or md_path.stem

    # 元のファイル内のH1は削除する（後でカスタムタイトルを強制挿入するため）
    text = re.sub(r"^# .+$", "", text, flags=re.M)

    code_counter = 0
    code_placeholders = {}

    def extract_code_common(code, heading=None):
        nonlocal code_counter
        code_counter += 1
        title = heading.split('\n')[0].strip() if heading else None
        if title: 
            title = re.sub(r'<[^>]+>', '', title)
            title = re.sub(r'\*\*', '', title)
        
        imgs = code_to_images_with_title(code, md_path.stem, code_counter, title)
        
        placeholder = f"@@CODEBLOCK_PLACEHOLDER_{code_counter}@@"
        # 枠線とパディングを1つのコンテナに集約（内部画像の隙間を排除）
        code_placeholders[placeholder] = f'<div style="margin: 1em 0; background-color: #1a1a1a; border: 2px solid #44475a; padding: 25px 0; page-break-inside: avoid; width: 100%; box-sizing: border-box; overflow: hidden; line-height: 0;">' + "".join([f'<img src="images/code/{img}" alt="Code {code_counter} Part {i+1}" style="display: block; width: 100%; height: auto; margin: 0; padding: 0; border: none;"/>' for i, img in enumerate(imgs)]) + '</div>'
        return placeholder
        
    text = re.sub(r'####\s+([^\n]+)\n+```c\s*(.*?)```', lambda m: extract_code_common(m.group(2), m.group(1)), text, flags=re.S)
    text = re.sub(r'\*\*([^\*]+)\*\*\s*[：:]*\s*\n+```c\s*(.*?)```', lambda m: extract_code_common(m.group(2), m.group(1)), text, flags=re.S)
    for keyword in ["実行結果", "出力例", "実行例"]:
        text = re.sub(rf'^({keyword}[^\n]*)$\s*\n+```c\s*(.*?)```', lambda m: extract_code_common(m.group(2), m.group(1)), text, flags=re.S | re.M)
    text = re.sub(r"```c\s*(.*?)```", lambda m: extract_code_common(m.group(1)), text, flags=re.S)

    # Mermaidもプレースホルダ化してinline_code変換から保護
    img_counter = 0
    mermaid_placeholders = {}
    def mermaid_repl(match):
        nonlocal img_counter; img_counter += 1
        img_name = f"{md_path.stem}_mermaid{img_counter}.png"
        if mermaid_to_image(match.group(1), MERMAID_DIR / img_name, img_counter):
            html_result = f'<div style="margin: 1.5em 0; page-break-inside: avoid; text-align: center; background-color: #fafafa; padding: 1em; border: 1px solid #ddd;"><img src="images/mermaid/{img_name}" alt="Diagram" style="max-width: 100%; height: auto;"/></div>'
        else:
            html_result = "<p>[図生成失敗]</p>"
        placeholder = f"@@MERMAID_BLOCK_{img_counter}@@"
        mermaid_placeholders[placeholder] = html_result
        return placeholder
    text = re.sub(r"```mermaid\s*(.*?)```", mermaid_repl, text, flags=re.S)

    # ![PDF](chapterXX.pdf) を除去
    text = re.sub(r'!\[PDF\]\([^)]+\.pdf\)', '', text)

    text = md_images_to_html(text)
    text = md_links_to_html(text)
    text = inline_code_to_html(text)
    text = emphasize_code_symbols(text)
    # プレースホルダを復元（コード画像、Mermaid画像）
    for k, v in code_placeholders.items(): text = text.replace(k, v)
    for k, v in mermaid_placeholders.items(): text = text.replace(k, v)

    # WikiLinksの変換： 
    # 2. Convert WikiLinks with alias: [[Link|Text]] -> Text
    text = re.sub(r'\[\[(?:[^|\]]*)\|([^\]]*)\]\]', r'\1', text)
    # 3. Convert simple WikiLinks: [[Link]] -> Link
    text = re.sub(r'\[\[([^\]]*)\]\]', r'\1', text)

    # テーブル処理（簡潔かつ堅牢に）
    def table_repl(match):
        lines = match.group(0).strip().split('\n')
        if len(lines) < 3: return match.group(0)
        headers = [c.strip() for c in lines[0].split('|') if c.strip()]
        rows = []
        for line in lines[2:]:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells: rows.append(cells)
        html = '<table style="width: 100%; border-collapse: collapse; margin: 1.2em 0; font-size: 0.9em; page-break-inside: avoid;">\n<thead>\n<tr>\n'
        for h in headers: html += f'<th style="border: 1px solid #666; padding: 0.7em; text-align: left; background: #f5f5f5;">{h}</th>\n'
        html += '</tr>\n</thead>\n<tbody>\n'
        for i, row in enumerate(rows):
            bg = '#fafafa' if i % 2 == 1 else '#fff'
            html += '<tr>\n'
            for c in row: html += f'<td style="border: 1px solid #999; padding: 0.6em; background: {bg};">{c}</td>\n'
            html += '</tr>\n'
        html += '</tbody>\n</table>\n'
        return html
    text = re.sub(r'(?:^\|.+\|$\n?){3,}', table_repl, text, flags=re.M)

    # ---- Obsidian Callout 変換 ----
    # > [!NOTE] タイトル
    # > 本文行1
    # > 本文行2
    # → 種別ごとに別色の装飾ボックスに変換
    #
    # [INFO] 読者の疑問：…  → 水色  (#e1f5fe / #0288d1)
    # [INFO] コラム：…      → 紫色  (#f3e5f5 / #7b1fa2)
    # [INFO] 補足：… / その他  → 緑色  (#e8f5e9 / #2e7d32)
    # [NOTE]              → オレンジ (#fff3e0 / #e65100)
    # [IMPORTANT]         → 赤色  (#ffebee / #b71c1c)
    # [WARNING]           → 琼琶色 (#fff8e1 / #f57c00)
    # [TIP]               → ティール (#e0f2f1 / #00695c)
    # [CAUTION]           → 深赤  (#ffcdd2 / #c62828)

    callout_styles = {
        'NOTE':      ('✏', '#fff3e0', '#e65100', '#ffe0b2'),  # オレンジ：備考・注記
        'INFO':      ('ℹ', '#e8f5e9', '#2e7d32', '#c8e6c9'),  # 緑：補足（デフォルト）
        'TIP':       ('✨', '#e0f2f1', '#00695c', '#b2dfdb'),       # ティール：実践ハント
        'IMPORTANT': ('⚠', '#ffebee', '#b71c1c', '#ffcdd2'),  # 赤：重要事項
        'WARNING':   ('⚠', '#fff8e1', '#f57c00', '#ffe082'),  # 琥珀：注意喚起
        'CAUTION':   ('❗', '#ffcdd2', '#c62828', '#ef9a9a'),       # 深赤：危険・禁止
        'SUCCESS':   ('✓', '#e8f5e9', '#2e7d32', '#c8e6c9'),       # 緑：成功・推奨
    }

    def convert_callout(text):
        lines = text.split('\n')
        result = []
        i = 0
        while i < len(lines):
            # コールアウト開始行を探す: > [!TYPE] タイトル
            m = re.match(r'^>\s*\[!(NOTE|INFO|TIP|IMPORTANT|WARNING|CAUTION|SUCCESS)\]\s*(.*)', lines[i], re.I)
            if m:
                ctype = m.group(1).upper()
                ctitle = m.group(2).strip()
                icon, bg, border_color, header_bg = callout_styles.get(ctype, ('ℹ', '#e3f2fd', '#1565c0', '#bbdefb'))
                
                # タイトルによる動的スタイリング (INFO 専用：読者の疑問/コラム/補足 で色を分ける)
                if ctype == 'INFO':
                    if '読者の疑問' in ctitle:
                        # 水色：読者の疑問
                        icon, bg, border_color = ('❓', '#e1f5fe', '#0288d1')
                    elif 'コラム' in ctitle:
                        # 紫色：コラム
                        icon, bg, border_color = ('📖', '#f3e5f5', '#7b1fa2')
                    else:
                        # 緑色：補足（デフォルト）
                        if not ctitle or ctitle.upper() == 'INFO':
                            ctitle = '補足'
                        icon, bg, border_color = ('ℹ', '#e8f5e9', '#2e7d32')
                
                # 本文行を収集（> で始まる連続行）
                body_lines = []
                i += 1
                while i < len(lines) and re.match(r'^>\s?', lines[i]):
                    body_line = re.sub(r'^>\s?', '', lines[i]).strip()
                    if body_line:
                        body_lines.append(body_line)
                    i += 1
                # タイトルがない場合はctype自体をタイトルにする
                display_title = ctitle if ctitle else ctype.capitalize()
                body_html = ' '.join(body_lines)
                # HTMLを生成
                html = (
                    f'<div style="background-color:{bg}; border-left:4px solid {border_color}; '
                    f'border-radius:4px; margin:1.2em 0; padding:0.8em 1em; page-break-inside:avoid;">'
                    f'<div style="color:{border_color}; font-weight:bold; margin-bottom:0.4em;">'
                    f'{icon} {display_title}</div>'
                    f'<div style="color:#000; line-height:1.8;">{body_html}</div>'
                    f'</div>'
                )
                result.append(html)
            elif re.match(r'^>\s?', lines[i]):
                # コールアウト以外の > 行（通常blockquoteや孤立した >）
                # 連続する > 行をまとめてHTMLのblockquoteに変換
                bq_lines = []
                while i < len(lines) and re.match(r'^>\s?', lines[i]):
                    bq_line = re.sub(r'^>\s?', '', lines[i]).strip()
                    if bq_line:
                        bq_lines.append(bq_line)
                    i += 1
                if bq_lines:
                    bq_html = (
                        '<blockquote style="border-left:3px solid #ccc; '
                        'margin:0.8em 0 0.8em 1em; padding:0.4em 1em; '
                        'color:#555; font-style:italic;">'
                        + ' '.join(bq_lines)
                        + '</blockquote>'
                    )
                    result.append(bq_html)
            else:
                result.append(lines[i])
                i += 1
        return '\n'.join(result)

    text = convert_callout(text)

    # 装飾

    text = re.sub(r'【重要】', r'<b style="background-color: #fff9c4; padding: 0.2em 0.5em; border-left: 3px solid #ffa726;">【重要】</b>', text)
    text = re.sub(r'【注意】', r'<b style="background-color: #ffcdd2; padding: 0.2em 0.5em; border-left: 3px solid #ef5350;">【注意】</b>', text)
    text = re.sub(r'【ポイント】', r'<b style="background-color: #e1f5fe; padding: 0.2em 0.5em; border-left: 3px solid #42a5f5;">【ポイント】</b>', text)
    text = re.sub(r'❌', r'<span style="color: #ef5350; font-weight: bold;">✕</span>', text)
    text = re.sub(r'✅', r'<span style="color: #66bb6a; font-weight: bold;">✓</span>', text)
    text = re.sub(r'[⚠⚠️]', r'<span style="color: #ffa726; font-weight: bold;">⚠</span>', text)
    # チェックリスト（段落・リストとして機能させる）
    # CSSでの図形描画はフォントによるベースラインの崩れが起きやすいため、確かな文字「□」「☑」を使用する
    # 浮き・沈みを防ぐため vertical-align: baseline に統一
    text = re.sub(r'^(\s*)[\-\*]?\s*\[[xX]\]\s+(.+)$', r'<div style="margin: 0.8em 0; line-height: 1.6; padding-left: 2em; text-indent: -2em;">\1<span style="color: #66bb6a; font-size: 1.25em; margin-right: 0.4em; vertical-align: baseline;">☑</span>\2</div>', text, flags=re.M)
    text = re.sub(r'^(\s*)[\-\*]?\s*\[ \]\s+(.+)$', r'<div style="margin: 0.8em 0; line-height: 1.6; padding-left: 2em; text-indent: -2em;">\1<span style="color: #999; font-size: 1.25em; margin-right: 0.4em; vertical-align: baseline;">□</span>\2</div>', text, flags=re.M)
    
    # 以前の単純な置換は残しておく（文中のインライン用）
    text = re.sub(r'\[[xX]\]', r'<span style="color: #66bb6a; font-size: 1.1em; vertical-align: baseline;">☑</span>', text)
    text = re.sub(r'\[ \]', r'<span style="color: #999; font-size: 1.1em; vertical-align: baseline;">□</span>', text)
    
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)

    # 見出し（Kindle用にスタイル強化）
    # カスタムタイトルを明示的にH1として各章の先頭に付与する
    # ※ただし _02 などの分割ファイルの場合はH1を付けない（1つの章としてまとめるため）
    if not re.search(r'_\d{2}$', md_path.stem) or md_path.stem.endswith("_01"):
        h1_html = f'<h1 id="chap{chapter_index}" style="font-size: 2em; margin: 1em 0 0.5em 0; font-weight: bold; line-height: 1.4; background-color: #e0e0e0; padding: 0.5em 0.8em; border-bottom: 4px solid #333; page-break-before: always; page-break-after: avoid;">{chapter_title}</h1>\n\n'
        text = h1_html + text

    text = re.sub(r"^## (.+)$", r'<h2 style="font-size: 1.5em; margin: 2em 0 1em 0; font-weight: bold; background-color: #e3f2fd; padding: 0.6em 0.8em; border-left: 5px solid #1976d2;">\1</h2>', text, flags=re.M)
    text = re.sub(r"^### (.+)$", r'<h3 style="font-size: 1.3em; margin: 1.5em 0 0.8em 0; font-weight: bold; background-color: #e8f5e9; padding: 0.5em 0.7em; border-left: 4px solid #388e3c;">\1</h3>', text, flags=re.M)
    text = re.sub(r"^#### (.+)$", r'<h4 style="font-size: 1.15em; margin: 1.2em 0 0.6em 0; font-weight: bold; background-color: #fff3e0; padding: 0.4em 0.6em; border-left: 3px solid #ff9800;">\1</h4>', text, flags=re.M)
    text = re.sub(r"^##### (.+)$", r'<h5 style="font-size: 1.05em; margin: 1em 0 0.5em 0; font-weight: bold;">\1</h5>', text, flags=re.M)
    text = re.sub(r"^###### (.+)$", r'<h6 style="font-size: 1em; margin: 0.8em 0 0.4em 0; font-weight: bold;">\1</h6>', text, flags=re.M)

    # リストと段落
    # 番号付きリストと箇条書きリスト（ネスト対応）を包括的に <li> に変換
    text = re.sub(r"^(\s*)[\-\*]\s+(.+)$", r"\1<li>\2</li>", text, flags=re.M)
    text = re.sub(r"^(\s*)\d+\.\s+(.+)$", r"\1<li>\2</li>", text, flags=re.M)
    
    # <li> の連続を <ul> で囲む（簡易的）
    text = re.sub(r"((?:\s*<li>.*?</li>\n?)+)", lambda m: f"<ul style='margin: 1.2em 0; padding-left: 2em; line-height: 1.9;'>\n{m.group(1)}</ul>\n", text, flags=re.S)

    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # ブロック要素（h1-h6, div, ul, li, table等）以外から始まる行は<p>タグで囲む
        # これにより、<b>や<i>から始まる行も正しく段落として認識される
        if stripped and not re.match(r'^</?(h[1-6]|div|ul|li|table|thead|tbody|tr|th|td|blockquote|p)\b', stripped, re.I):
            lines.append(f"<p>{line}</p>")
        else:
            lines.append(line)
    html_content = "\n".join(lines)

    # 章ごとのPDF画像をH1タグの直後に挿入
    if chapter_index in chapter_pdf_images:
        pdf_html = '<div style="margin: 0.5em 0; page-break-inside: avoid;">\n'
        for pdf_img_path in chapter_pdf_images[chapter_index]:
            pdf_html += f'<div style="margin: 0.5em 0; text-align: center;"><img src="{pdf_img_path}" alt="Slide" style="max-width: 100%; height: auto; border: 1px solid #ddd;"/></div>\n'
        pdf_html += '</div>\n'
        h1_pattern = r'(<h1[^>]*>.*?</h1>)'
        html_content = re.sub(h1_pattern, r'\1\n' + pdf_html, html_content, count=1)

    return html_content, chapter_title

# ========= メイン =========
def main():
    print("EPUB生成開始...")
    CHAPTER_DIR.mkdir(exist_ok=True)
    md_files = sorted(CHAPTER_DIR.glob("*.md"))
    if not md_files:
        (CHAPTER_DIR / "01_test.md").write_text("# テスト\n```c\n#include <stdio.h>\n// コメント\nint main(){}\n```", encoding="utf-8")
        md_files = sorted(CHAPTER_DIR.glob("*.md"))

    body = []
    chapters = []
    for chapter_index, md in enumerate(md_files):
        try:
            html, title = process_md(md, chapter_index)
            body.append(html)
            # ページ分割された後半のファイル（_02等）はHTMLの目次（TOC）に含めない
            if not re.search(r'_\d{2}$', md.stem) or md.stem.endswith("_01"):
                chapters.append({'id': f"chap{chapter_index}", 'title': title})
        except Exception as e:
            print(f"[ERROR] {md.name} 処理中にエラー: {e}")
            import traceback
            traceback.print_exc()

    toc = ""
    if cover_dest: toc += f'<div style="text-align:center; page-break-after:always;"><img src="images/{cover_dest.name}" /></div>'
    toc += '<div style="page-break-before:always; page-break-after:always;"><h2>目次</h2>'
    for i, c in enumerate(chapters, 1): toc += f'<p><a href="#{c["id"]}">{i}. {c["title"]}</a></p>'
    toc += '</div>'

    css_content = "body{font-family:'Hiragino Mincho ProN',serif; line-height:1.8; margin:0; padding:1em; text-align:justify; color:#222;}\nimg{max-width:100%; height:auto;}"

    html_content = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n'
        '<html xmlns="http://www.w3.org/1999/xhtml">\n'
        '<head><title>Book</title>\n'
        '<style>\n' + css_content + '\n</style>\n'
        '</head><body>\n' + toc + ''.join(body) + '\n</body></html>'
    )

    BOOK_HTML.write_text(html_content, encoding="utf-8")

    print(f"[HTML] {BOOK_HTML} 生成完了")

    # EPUB生成オプション（Kindle向け最適化設定 - h1のみを章として認識）
    epub_options = [
        "ebook-convert", str(BOOK_HTML), str(BOOK_EPUB),
        "--language", "ja", 
        "--epub-version", "2",
        "--chapter", "//*[name()='h1']",  # h1のみを章として認識
        "--level1-toc", "//h:h1",
        "--chapter-mark", "pagebreak",
        "--disable-font-rescaling",
        "--margin-top", "0", "--margin-bottom", "0",
        "--margin-left", "0", "--margin-right", "0",
        "--pretty-print"
    ]
    if cover_dest:
        epub_options.extend(["--cover", str(cover_dest)])

    try:
        print("[EPUB変換開始...]")
        result = subprocess.run(epub_options, capture_output=True)
        if result.returncode == 0:
            print("[OK] EPUB完了:", BOOK_EPUB)
        else:
            stderr = result.stderr.decode('utf-8', errors='replace')
            print(f"[ERROR] EPUB変換失敗: {stderr}")
            return
        
        # Kindle(MOBI)変換
        if Path(BOOK_EPUB).exists():
            print("[MOBI変換開始...]")
            result2 = subprocess.run([
                "ebook-convert", str(BOOK_EPUB), str(BOOK_MOBI),
                "--output-profile", "kindle",
                "--mobi-file-type", "both"
            ], capture_output=True)
            if result2.returncode == 0:
                print("[OK] MOBI完了:", BOOK_MOBI)
            else:
                stderr2 = result2.stderr.decode('utf-8', errors='replace')
                print(f"[ERROR] MOBI変換失敗: {stderr2}")

        # PDF変換
        if Path(BOOK_EPUB).exists():
            print("[PDF変換開始...]")
            book_pdf = DIST_DIR / "book.pdf"
            result3 = subprocess.run([
                "ebook-convert", str(BOOK_EPUB), str(book_pdf),
                "--pdf-page-numbers",
                "--paper-size", "a5",
                "--pdf-default-font-size", "12",
                "--pdf-mono-font-size", "12"
            ], capture_output=True)
            if result3.returncode == 0:
                print("[OK] PDF完了:", book_pdf)
            else:
                stderr3 = result3.stderr.decode('utf-8', errors='replace')
                print(f"[ERROR] PDF変換失敗: {stderr3}")
    except Exception as e:
        print(f"[ERROR] 変換失敗: {e}")
        print("Calibreがインストールされているか確認してください。")

    # --- 6. スタンドアロンHTMLの自動生成 ---
    print("\n[スタンドアロンHTML (Google Drive閲覧用) を生成しています...]")
    standalone_script = Path.cwd() / "convert_to_standalone.py"
    if standalone_script.exists():
        try:
            subprocess.run(["python", str(standalone_script)], cwd=str(Path.cwd()), check=True)
            print("[OK] スタンドアロンHTMLの生成完了")
        except Exception as e:
            print(f"[ERROR] スタンドアロンHTMLの生成失敗: {e}")
    else:
        print(f"[WARN] {standalone_script} が見つからないため実行スキップ")

if __name__ == "__main__":
    main()