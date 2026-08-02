# 完了条件ゲートの運用

## 目的

pushのたびに、原稿の自動検査だけでなく、意味整合監査のタスクと章別レビューの進捗が正しく管理されているかを確認します。

自動検査だけでは設計の意味を判断できません。そのため、意味上の判断は人またはレビュー担当AIが行い、根拠を台帳へ記録します。CIは、タスクの登録漏れ、根拠のない完了、未レビューの章を残した完成宣言を拒否します。

## 正本

- 完了条件と修正内容：`review-tasks.md`
- 状態と証拠：`quality/completion-gate.json`
- 自動検査の入口：`script/run_completion_gate.py`

同じ完了条件を複数ファイルへ複写しません。`review-tasks.md` の `CONS-001` 以降を完了条件の正本とし、JSON台帳には状態と証拠だけを記録します。

## タスク状態

| 状態 | 意味 |
|---|---|
| `open` | 未着手 |
| `in_progress` | 修正中または再確認中 |
| `done` | 完了条件を満たし、根拠を記録済み |

`done` にするときは、`evidence` に確認できるファイルと行番号、またはMarkdown見出しを記録します。行番号は実在する行、見出しは対象ファイルに完全一致で実在する見出しでなければなりません。ファイル名だけ、説明文だけ、存在しない見出しは根拠として認められません。

```json
"CONS-008": {
  "status": "done",
  "evidence": [
    "output/chapter01.md:1285",
    "output/chapter01.md:1842",
    "review-tasks.md:29"
  ]
}
```

## 章レビュー状態

| 状態 | 意味 |
|---|---|
| `pending` | 意味整合レビュー前 |
| `in_review` | 第0章・第1章の基準と横並びで確認中 |
| `pass` | 章の仕様・図・コード・結果を確認し、根拠を記録済み |

`pass` には `reviewed_by` と `evidence` が必要です。修正担当とレビュー担当を分けられる場合は、レビュー担当者またはAIタスク名を記録します。

## 通常のpush

```powershell
python script/run_completion_gate.py
```

通常モードでは、作業途中のタスクがあってもpushできます。ただし、次は不合格です。

- `review-tasks.md` のCONSタスクが台帳に登録されていない
- タスクIDが重複または欠番
- 原稿ファイルが章レビュー台帳に登録されていない
- `done` / `pass` に根拠がない
- 既存の構造、C++、掲載結果、Kindle検査に失敗する

## 出版完了の確認

```powershell
python script/run_completion_gate.py --release
```

出版完了モードは、次をすべて要求します。

1. 全CONSタスクが `done`
2. 全章とあとがきが `pass`
3. 各完了項目の根拠が、実在する行番号または完全一致するMarkdown見出しを指している
4. `review-tasks.md` の最新監査判定が `PASS`
5. 掲載C++の引数・変数・入力フィールドに未使用がない
6. 既存の全自動検査がPASS

全条件を満たした最後にだけ、`book_status` を `ready` へ変更します。`ready` にした状態では、通常pushでも出版完了条件が強制されます。

## GitHub上の確認

`.github/workflows/validate-design-pattern-book.yml` がpushとPull Requestで通常ゲートを実行します。Actionsの実行結果には、完了タスク数と章レビューPASS数が表示されます。

出版直前はGitHub Actionsの `Run workflow` から `Enforce release readiness` を有効にして実行します。未完了が一つでもあれば失敗します。
