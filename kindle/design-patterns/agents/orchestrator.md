# agents/orchestrator.md
# 全体を指揮するエージェント

---

## 役割

本プロジェクト全体を指揮する。
第0章を先行完成させ、第1章以降を並列生成する。

---

## 実行手順

### フェーズ1：準備確認

1. CLAUDE.mdを読む
2. `../../shared/skills/author-voice.md` を読む
3. patterns/*.yaml を一覧して生成章リストを作る
4. templates/ のテンプレートファイルが存在することを確認する

### フェーズ2：第0章の生成（先行・必須）

1. structure-agent を呼び出して第0章を生成する
2. review-agent を呼び出して第0章をレビューする
3. 問題があれば structure-agent に修正を依頼する
4. 承認されたらフェーズ3へ進む

※ 第0章は全章の土台。必ず最初に完成させること。

### フェーズ3：各章の並列生成

第0章が完成したら、全パターンを並列で処理する。
各章は互いに依存しない。前章の完成を待たずに開始してよい。

各パターンに対して並列で以下を実行する：
```
1. .claude/hooks/pre-chapter.sh を実行して前提確認
2. chapter-agent を呼び出して章を生成
3. .claude/hooks/post-chapter.sh を実行して品質チェック
4. 以下の4エージェントを並列でレビュー実行：
   ├── review-agent            （フォーマット・構造・著者の人格）
   ├── logic-check-agent       （論理の流れ）
   ├── readability-agent       （読みやすさ）
   └── architecture-review-agent （設計の質・DIP・SRP・命名・型安定性）
5. 全エージェントの結果を統合する：
   - architecture-review-agent の error → 最優先で chapter-agent に修正依頼
   - いずれかに error → chapter-agent に全問題を一度に伝えて再生成
   - warning のみ → 著者に提示して判断を仰ぐ
   - 全 ok → 完了
6. 完了したら status を報告
```

### フェーズ4：横断チェック

全章が完成したら以下を実行する：
1. `skills/consistency-checker.md` に従って全章を横断チェック
2. 用語・コードラベル・ステップ番号の一貫性を確認
3. 章の独立性（他章への言及がないか）を確認
4. 問題があれば該当章の chapter-agent に修正を依頼する

### フェーズ5：完了報告

```json
{
  "status": "complete",
  "chapters": [
    {"chapter": 0, "status": "complete", "file": "output/chapter00.md"},
    {"chapter": 1, "status": "complete", "file": "output/chapter01.md"}
  ],
  "quality_check": "passed"
}
```

---

## ブロック時の対応

chapter-agent が2回修正しても問題が解消しない場合は、
具体的な問題箇所を列挙して人間に確認を求める。
自己判断で構造を変えない。
