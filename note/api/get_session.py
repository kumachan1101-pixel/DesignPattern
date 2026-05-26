#!/usr/bin/env python3
"""
note.com セッションCookie 自動取得スクリプト
_note_session_v5 を Chrome から取得して .session_cache に保存する。

取得順:
  1. browser_cookie3 ライブラリ（Chrome < 127 向け）
  2. Chrome DevTools Protocol（--remote-debugging-port=9222 起動時のみ）
  3. Chrome SQLite DB を temp コピー → 復号（Chrome < 127 向け fallback）
  4. 対話入力（すべて失敗した場合）

Chrome 127+ (2024年以降) はアプリ固有暗号化のため 1/3 が失敗することがある。
その場合は 2 (CDP) か 4 (手入力) を使う。

使い方:
  python get_session.py           # 取得してキャッシュ保存
  python get_session.py --show    # 取得した値を表示するだけ（保存しない）
  python get_session.py --manual  # 対話入力を強制
"""

import argparse
import base64
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

# Windows CP932 環境でも UTF-8 出力できるようにする
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp932", "shift_jis", "mbcs"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() in ("cp932", "shift_jis", "mbcs"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CACHE_FILE = Path(__file__).parent / ".session_cache"
COOKIE_NAME = "_note_session_v5"


# ──────────────────────────────────────────
# 方法 1: browser_cookie3
# ──────────────────────────────────────────

def try_browser_cookie3() -> "str | None":
    """browser_cookie3 ライブラリで Chrome Cookie を取得。Chrome < 127 で有効。"""
    try:
        import browser_cookie3  # type: ignore
    except ImportError:
        print("[skip] browser_cookie3 未インストール  → pip install browser-cookie3")
        return None

    try:
        cj = browser_cookie3.chrome(domain_name="note.com")
        for cookie in cj:
            if cookie.name == COOKIE_NAME:
                return cookie.value
        print("[skip] browser_cookie3: note.com に _note_session_v5 が見つかりません")
    except Exception as e:
        print(f"[skip] browser_cookie3: {e}")
    return None


# ──────────────────────────────────────────
# 方法 2: Chrome DevTools Protocol (CDP)
# ──────────────────────────────────────────

def try_chrome_devtools_protocol(port: int = 9222) -> "str | None":
    """
    Chrome を --remote-debugging-port=9222 で起動している場合に Cookie を取得。

    Chrome 起動方法（例）:
      chrome.exe --remote-debugging-port=9222
    または既存のプロファイルで:
      chrome.exe --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\\Google\\Chrome\\User Data"
    """
    import urllib.request
    import urllib.error

    # CDP HTTP エンドポイントで開いているタブ一覧を取得
    try:
        url = f"http://localhost:{port}/json"
        with urllib.request.urlopen(url, timeout=2) as resp:
            tabs = json.loads(resp.read())
    except (urllib.error.URLError, OSError):
        print(f"[skip] CDP: localhost:{port} に接続できません（Chrome がデバッグポート付きで起動していない）")
        return None

    # WebSocket クライアントを試みる
    try:
        import websocket  # type: ignore
    except ImportError:
        print("[skip] CDP: websocket-client 未インストール  → pip install websocket-client")
        return None

    # note.com タブを優先して選択
    target = next(
        (t for t in tabs if "note.com" in t.get("url", "") and "webSocketDebuggerUrl" in t),
        next((t for t in tabs if "webSocketDebuggerUrl" in t), None),
    )
    if not target:
        print("[skip] CDP: デバッグ可能なタブが見つかりません")
        return None

    try:
        ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=5)
        ws.send(json.dumps({
            "id": 1,
            "method": "Network.getCookies",
            "params": {"urls": ["https://note.com"]},
        }))
        result = json.loads(ws.recv())
        ws.close()

        for cookie in result.get("result", {}).get("cookies", []):
            if cookie["name"] == COOKIE_NAME:
                return cookie["value"]

        print("[skip] CDP: note.com の _note_session_v5 が見つかりません（ログイン状態を確認）")
    except Exception as e:
        print(f"[skip] CDP エラー: {e}")
    return None


# ──────────────────────────────────────────
# 方法 3: SQLite 直接読み取り（Chrome < 127）
# ──────────────────────────────────────────

def _get_chrome_aes_key() -> "bytes | None":
    """Chrome Local State から AES-256 キーを取得（Chrome v80+）。"""
    local_state_path = (
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Google/Chrome/User Data/Local State"
    )
    if not local_state_path.exists():
        return None
    try:
        with open(local_state_path, encoding="utf-8") as f:
            local_state = json.load(f)
        b64_key = local_state.get("os_crypt", {}).get("encrypted_key")
        if not b64_key:
            return None
        encrypted_key = base64.b64decode(b64_key)[5:]  # "DPAPI" プレフィックスを除去

        import win32crypt  # type: ignore
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except ImportError:
        pass
    except Exception:
        pass
    return None


def _decrypt_chrome_cookie(encrypted: bytes) -> "str | None":
    """Chrome 暗号化 Cookie 値を復号。"""
    if not encrypted:
        return None

    if encrypted[:3] in (b"v10", b"v11"):
        # AES-256-GCM (Chrome v80+)
        key = _get_chrome_aes_key()
        if key is None:
            return None
        try:
            from Crypto.Cipher import AES  # type: ignore
            nonce = encrypted[3:15]
            ciphertext = encrypted[15:-16]
            tag = encrypted[-16:]
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")
        except ImportError:
            print("  (pycryptodome 未インストール → pip install pycryptodome)")
        except Exception as e:
            print(f"  AES 復号失敗: {e}")
        return None

    # DPAPI (Chrome v80 以前)
    try:
        import win32crypt  # type: ignore
        return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode("utf-8")
    except Exception:
        pass
    return None


def try_sqlite_direct() -> "str | None":
    """Chrome Cookie DB を temp にコピーして直接読み取る（Chrome < 127 fallback）。"""
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Google/Chrome/User Data/Default/Network/Cookies",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Google/Chrome/User Data/Default/Cookies",
    ]
    cookie_db = next((p for p in candidates if p.exists()), None)
    if not cookie_db:
        print("[skip] SQLite: Chrome Cookie DB が見つかりません")
        return None

    print(f"  Cookie DB を一時コピー中: {cookie_db.name}")
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    try:
        shutil.copy2(cookie_db, tmp_path)
        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT value, encrypted_value FROM cookies "
            "WHERE host_key LIKE '%note.com%' AND name = ?",
            (COOKIE_NAME,),
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            print("[skip] SQLite: note.com の _note_session_v5 が見つかりません")
            return None

        value, encrypted_value = row
        if value:
            return value
        return _decrypt_chrome_cookie(bytes(encrypted_value))

    except sqlite3.OperationalError as e:
        print(f"[skip] SQLite エラー: {e}")
    except Exception as e:
        print(f"[skip] SQLite 予期しないエラー: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return None


# ──────────────────────────────────────────
# 方法 4: 対話入力
# ──────────────────────────────────────────

def try_interactive_input() -> "str | None":
    """Chrome DevTools から手動でコピーした値を入力してもらう。"""
    print()
    print("=" * 60)
    print("手動入力モード")
    print("-" * 60)
    print("Chrome で https://note.com を開いてログインした状態で:")
    print("  F12 → Application タブ → Cookies → https://note.com")
    print(f"  「{COOKIE_NAME}」の値をコピーしてください")
    print("=" * 60)
    try:
        value = input("値を貼り付けて Enter: ").strip()
        if value:
            return value
        print("[skip] 入力がありませんでした")
    except (EOFError, KeyboardInterrupt):
        print("\n[skip] 入力がキャンセルされました")
    return None


# ──────────────────────────────────────────
# メイン
# ──────────────────────────────────────────

def fetch_session_cookie(force_manual: bool = False) -> "str | None":
    """_note_session_v5 を取得する（複数手段を順に試す）。"""
    if not force_manual:
        print(f"[1/3] browser_cookie3 を試行...")
        value = try_browser_cookie3()
        if value:
            print("=> 取得成功 (browser_cookie3)")
            return value

        print(f"\n[2/3] Chrome DevTools Protocol を試行...")
        value = try_chrome_devtools_protocol()
        if value:
            print("=> 取得成功 (CDP)")
            return value

        print(f"\n[3/3] SQLite 直接読み取りを試行...")
        value = try_sqlite_direct()
        if value:
            print("=> 取得成功 (SQLite)")
            return value

        print()
        print("注意: Chrome 127+ はアプリ固有暗号化により自動取得が困難です。")
        print("      CDP を使う場合: chrome.exe --remote-debugging-port=9222 で起動してください。")

    # 最終手段: 対話入力
    return try_interactive_input()


def save_cache(value: str) -> None:
    CACHE_FILE.write_text(value.strip(), encoding="utf-8", newline="\n")
    print(f"=> キャッシュ保存: {CACHE_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(description="note.com Cookie 自動取得")
    parser.add_argument("--show", action="store_true", help="値を表示するだけ（保存しない）")
    parser.add_argument("--manual", action="store_true", help="対話入力を強制")
    args = parser.parse_args()

    print(f"=== {COOKIE_NAME} 取得ツール ===\n")

    value = fetch_session_cookie(force_manual=args.manual)
    if not value:
        print("\n取得できませんでした。")
        print(f"手動でキャッシュファイルを作成することもできます:")
        print(f"  {CACHE_FILE}")
        sys.exit(1)

    masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "****"
    print(f"\n取得値（マスク）: {masked}")

    if args.show:
        print(f"\n--- 値（全文） ---\n{value}\n-----------------")
    else:
        save_cache(value)
        print("完了！次回から post_article.py が自動でキャッシュを読みます。")


if __name__ == "__main__":
    main()
