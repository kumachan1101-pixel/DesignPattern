#!/usr/bin/env python3
"""
note.com 下書き投稿スクリプト（引数対応版）
使い方:
  python post_article.py --title "タイトル" --body-file path/to/article.md --tags "タグ1,タグ2"
  python post_article.py --title "タイトル" --body "本文テキスト" --tags "タグ1,タグ2"
"""

import argparse
import json
import os
import sys
import requests

# ===== 認証情報（環境変数 or ここに直接設定） =====
NOTE_SESSION_V5 = os.environ.get("NOTE_SESSION_V5", "16ed23d7de9124dbadff1e7a41c9d932")
NOTE_GQL_AUTH_TOKEN = os.environ.get("NOTE_GQL_AUTH_TOKEN", "")


def post_draft(title: str, body: str, tags: list[str]) -> None:
    if not NOTE_SESSION_V5:
        print("❌ エラー: NOTE_SESSION_V5 が未設定です")
        print("  取得方法: Noteにログイン → 開発者ツール → Cookie → _note_session_v5")
        sys.exit(1)

    cookie = f"_note_session_v5={NOTE_SESSION_V5}"
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

    print(f"note.com に下書き保存中: {title[:30]}...")
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
    else:
        print(f"❌ エラー: ステータス {r.status_code}")
        print(r.text[:300])
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="note.com 下書き投稿")
    parser.add_argument("--title", required=True, help="記事タイトル")
    parser.add_argument("--body", help="本文テキスト（--body-file と排他）")
    parser.add_argument("--body-file", help="本文ファイルパス（--body と排他）")
    parser.add_argument(
        "--tags",
        default="ソフトウェア設計,デザインパターン,プログラミング,エンジニア",
        help="タグをカンマ区切りで指定",
    )
    args = parser.parse_args()

    # 本文の取得
    if args.body_file:
        with open(args.body_file, encoding="utf-8") as f:
            raw = f.read()
        # 1行目が # タイトル の場合は除去
        lines = raw.splitlines()
        body = "\n".join(lines[1:]).strip() if lines[0].startswith("# ") else raw
    elif args.body:
        body = args.body
    else:
        print("❌ --body または --body-file のどちらかを指定してください")
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    post_draft(args.title, body, tags)


if __name__ == "__main__":
    main()
