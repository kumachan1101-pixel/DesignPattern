#!/usr/bin/env python3
"""
note.com 下書き投稿スクリプト
pip install requests  してから実行してください
"""

import requests
import json

# ===== 認証情報（ここを設定） =====
NOTE_SESSION_V5 = "16ed23d7de9124dbadff1e7a41c9d932"
NOTE_GQL_AUTH_TOKEN = ""  # 見つかった場合は入力。空でもOK

# ===== 記事内容 =====
TITLE = "「中を見る前提」で設計していた時期がありました"

BODY = """設計の話をするとき、「この関数の中がこうなっているから」という説明をよくしていました。

内部実装を把握していることが、設計力だと思っていたんです。

---

### 黒い箱として扱う、という発想

ある時期から、少し見方が変わりました。

コンポーネントを「何をするか」ではなく「何を受け取って、何を返すか」で考えるようになりました。

入力と出力だけを見る。中身は見ない。

これがいわゆる「ブラックボックス」思考です。

---

### 中を見ていると何が起きるか

内部実装を前提に設計すると、依存が生まれます。

「あのクラスはこういう順番で処理するから、こっちもそれに合わせて呼ぶ」

この前提が壊れたとき、連鎖的に修正が必要になります。

変更がひとつで済まない設計は、内部に依存しすぎているサインです。

---

### 責任の境界を引く

ブラックボックス思考の本質は、「知らなくていいことを決める」ことです。

このコンポーネントは、あのコンポーネントの中身を知らなくていい。

その境界を引くことが、責任を分けることと同じ意味を持ちます。

---

### インターフェースという言語

入力と出力だけで会話できる設計をすると、インターフェースが自然に浮かび上がります。

「このメソッドはこういう値を受け取って、こういう値を返す」という約束。

その約束を守れば、中身はいつでも変えられます。

---

### 今でも「中を見たい」気持ちはある

正直に言うと、内部実装が気になる瞬間はまだあります。

特にバグを追うときや、パフォーマンスを調べるときは、中を開けたくなります。

でも、設計の段階では、「中を見なくて済む構造にする」ことを先に考えるようになりました。

見るタイミングを選ぶ、という習慣です。

---

### まとめ

「中を見る前提」で設計していた頃は、変更のたびに連鎖修正が起きていました。

「中を見ない前提」で設計するようになってから、変更の影響がひとつのクラスに収まることが増えました。

黒い箱として扱う。それだけで、設計の見通しがずいぶん変わります。"""

TAGS = ["ソフトウェア設計", "プログラミング", "エンジニア", "デザインパターン"]

# ===== 実行 =====
cookie = f"_note_session_v5={NOTE_SESSION_V5}"
if NOTE_GQL_AUTH_TOKEN:
    cookie += f"; note_gql_auth_token={NOTE_GQL_AUTH_TOKEN}"

headers = {
    "Content-Type": "application/json",
    "Cookie": cookie,
}

payload = {
    "draft": {
        "title": TITLE,
        "body": BODY,
        "hashtag_notes_attributes": [{"name": t} for t in TAGS],
    }
}

print("note.com に下書き保存中...")
r = requests.post("https://note.com/api/v3/drafts", json=payload, headers=headers, timeout=30)

if r.status_code in (200, 201):
    data = r.json()
    key = data.get("data", {}).get("key") or data.get("draft", {}).get("key")
    if key:
        print(f"✅ 成功！下書きURL: https://note.com/edit/n/{key}")
    else:
        print("✅ 保存完了（URLの取得に失敗）")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:300])
else:
    print(f"❌ エラー: ステータス {r.status_code}")
    print(r.text[:500])
