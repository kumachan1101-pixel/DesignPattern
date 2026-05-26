#!/usr/bin/env python3
"""
note.com 下書き投稿スクリプト（引数対応版）
使い方:
  python post_article.py --title "タイトル" --body-file path/to/article.md --tags "タグ1,タグ2"
  python post_article.py --title "タイトル" --body "本文テキスト" --tags "タグ1,タグ2"

Cookie は以下の優先順で解決する:
  1. 環境変数 NOTE_SESSION_V5
  2. .session_cache ファイル（get_session.py が自動生成）
  3. get_session.py を自動実行して取得
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import requests

# ───────────────────────────────────────────
# セッション Cookie の解決
# ───────────────────────────────────────────

_CACHE_FILE = Path(__file__).parent / ".session_cache"
_GET_SESSION_SCRIPT = Path(__file__).parent / "get_session.py"


def _load_cache() -> str | None:
    """キャッシュファイルから Cookie 値を読む。BOM・空白を除去。"""
    if _CACHE_FILE.exists():
        value = _CACHE_FILE.read_text(encoding="utf-8-sig").strip()
        if value:
            return value
    return None


def _run_get_session() -> str | None:
    """get_session.py を実行してキャッシュを生成し、値を返す。"""
    if not _GET_SESSION_SCRIPT.exists():
        print(f"❌ {_GET_SESSION_SCRIPT} が見つかりません")
        return None

    print("🔄 get_session.py を実行してCookieを自動取得します...")
    result = subprocess.run(
        [sys.executable, str(_GET_SESSION_SCRIPT)],
        capture_output=False,   # 出力をそのまま表示
        text=True,
    )
    if result.returncode != 0:
        return None

    # get_session.py がキャッシュを保存したはずなので再読み込み
    return _load_cache()


def resolve_session_cookie() -> str:
    """
    NOTE_SESSION_V5 を優先順で解決して返す。
    取得できない場合は sys.exit(1) する。
    """
    # 1. 環境変数
    env_value = os.environ.get("NOTE_SESSION_V5", "").strip()
    if env_value:
        return env_value

    # 2. キャッシュファイル
    cached = _load_cache()
    if cached:
        print(f"📋 キャッシュから Cookie を読み込みました（{_CACHE_FILE.name}）")
        return cached

    # 3. get_session.py を自動実行
    fetched = _run_get_session()
    if fetched:
        return fetched

    # すべて失敗
    print("\n❌ NOTE_SESSION_V5 を取得できませんでした。")
    print("以下のいずれかの方法で設定してください:")
    print("  A) 環境変数: set NOTE_SESSION_V5=<値>")
    print(f"  B) ファイル: {_CACHE_FILE} に値を貼り付けて保存")
    print(f"  C) スクリプト: python {_GET_SESSION_SCRIPT} を実行")
    sys.exit(1)


# ───────────────────────────────────────────
# 投稿ロジック
# ───────────────────────────────────────────

NOTE_GQL_AUTH_TOKEN = os.environ.get("NOTE_GQL_AUTH_TOKEN", "")


def post_draft(title: str, body: str, tags: list[str]) -> None:
    note_session = resolve_session_cookie()

    cookie = f"_note_session_v5={note_session}"
    if NOTE_GQL_AUTH_TOKEN:
        cookie += f"; note_gql_auth_token={NOTE_GQL_AUTH_TOKEN}"

    headers = {
        "Content-Type": "application/json",
        "Cookie": cookie,
    }
    payload = {
        "draft": {
            "title": title,
            "body": body,
            "hashtag_notes_attributes": [{"name": t} for t in tags],
        }
    }

    print(f"📝 note.com に下書き保存中: {title[:40]}...")
    r = requests.post(
        "https://note.com/api/v3/drafts",
        json=payload,
        headers=headers,
        timeout=30,
    )

    if r.status_code in (200, 201):
        data = r.json()
        key = data.get("data", {}).get("key") or data.get("draft", {}).get("key")
        if key:
            print(f"✅ 成功！下書きURL: https://note.com/edit/n/{key}")
        else:
            print("✅ 保存完了（URLの取得に失敗）")
    elif r.status_code == 401:
        print("❌ 認証エラー（401）: Cookie が期限切れの可能性があります")
        print(f"   キャッシュを削除して再取得: del {_CACHE_FILE}")
        # キャッシュが古い可能性があるので削除を促す
        sys.exit(1)
    else:
        print(f"❌ エラー: ステータス {r.status_code}")
        print(r.text[:300])
        sys.exit(1)


# ───────────────────────────────────────────
# エントリポイント
# ───────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="note.com 下書き投稿")
    parser.add_argument("--title", required=True, help="記事タイトル")
    parser.add_argument("--body", help="本文テキスト（--body-file と排他）")
    parser.add_argument("--body-file", help="本文ファイルパス（--body と排他）")
    parser.add_argument(
        "--tags",
        default="ソフトウェア設計,デザインパターン,プログラミング,エンジニア",
        help="タグをカンマ区切りで指定",
    )
    parser.add_argument(
        "--refresh-cookie",
        action="store_true",
        help="キャッシュを無視してCookieを再取得する",
    )
    args = parser.parse_args()

    # --refresh-cookie: キャッシュを削除して強制再取得
    if args.refresh_cookie and _CACHE_FILE.exists():
        _CACHE_FILE.unlink()
        print("🗑️  キャッシュを削除しました。再取得します...")

    # 本文の取得
    if args.body_file:
        with open(args.body_file, encoding="utf-8") as f:
            raw = f.read()
        lines = raw.splitlines()
        body = "\n".join(lines[1:]).strip() if lines and lines[0].startswith("# ") else raw
    elif args.body:
        body = args.body
    else:
        print("❌ --body または --body-file のどちらかを指定してください")
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    post_draft(args.title, body, tags)


if __name__ == "__main__":
    main()
