import os
import base64
import mimetypes
from pathlib import Path
from bs4 import BeautifulSoup

def convert_to_standalone(html_path: str = "dist/book.html", output_path: str = "dist/book_standalone.html"):
    html_file = Path(html_path)
    if not html_file.exists():
        print(f"エラー: {html_file} が見つかりません。先に build_epub.py を実行してください。")
        return

    print(f"[{html_file.name}] を読み込み中...")
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    images = soup.find_all('img')
    
    encoded_count = 0
    missing_count = 0

    print(f"画像データの埋め込みを開始します (全 {len(images)} 件)")

    for img in images:
        src = img.get('src')
        if not src:
            continue
            
        # "images/" から始まるパス、もしくは相対パスのみ処理
        # Epubビルド時、HTMLからは src="images/xxx.png" や src="images/pdf/xxx.png" となっている
        if src.startswith('http://') or src.startswith('https://') or src.startswith('data:'):
            continue

        # HTMLファイルからの相対パスを解決
        img_path = html_file.parent / src
        
        if img_path.exists() and img_path.is_file():
            # mimetypeの判定
            mime_type, _ = mimetypes.guess_type(img_path)
            if not mime_type:
                mime_type = 'image/png' # デフォルト
                
            with open(img_path, 'rb') as img_f:
                b64_data = base64.b64encode(img_f.read()).decode('utf-8')
                
            # src属性をBase64データURIに置換
            img['src'] = f"data:{mime_type};base64,{b64_data}"
            encoded_count += 1
            if encoded_count % 10 == 0:
                print(f"  ... {encoded_count}/{len(images)} 枚変換完了")
        else:
            print(f"警告: 画像ファイルが見つかりません -> {img_path}")
            missing_count += 1

    print("HTMLファイルを保存中...")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))

    print("=" * 40)
    print("変換完了！")
    print(f"成功: {encoded_count} 枚")
    if missing_count > 0:
        print(f"失敗(スキップ): {missing_count} 枚")
    print(f"出力ファイル: {output_path}")

if __name__ == "__main__":
    # 実行前に beautifulsoup4 のインストールが必要です
    # pip install beautifulsoup4
    
    # 04_work ディレクトリで実行された場合を想定
    html_input = "../05_生成/dist/book.html"
    html_output = "../05_生成/dist/book_standalone.html"
    
    # パスが存在しない場合は、カレントの dist/book.html を探す
    if not Path(html_input).exists() and Path("dist/book.html").exists():
        html_input = "dist/book.html"
        html_output = "dist/book_standalone.html"
        
    convert_to_standalone(html_input, html_output)
