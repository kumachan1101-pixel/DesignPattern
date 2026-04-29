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
1. chapter-agent を呼び出して章を生成
2. 以下のエージェントを並列でレビュー実行：
   ├── review-agent              （フォーマット・構造・著者の人格）
   ├── logic-check-agent         （論理の流れ）
   ├── readability-agent         （テキストの読みやすさ）
   ├── clarity-agent             （概念の伝わりやすさ・図表の充足）
   ├── architecture-review-agent （設計の質・DIP・SRP・命名・型安定性）
   └── design-expert-agent       （教えている設計手法の妥当性）
3. 上記全エージェントの結果を統合した後、devils-advocate-agent を実行：
   └── devils-advocate-agent     （反面教師・前提の妥当性・代案の提示）
4. 全結果を統合する：
   - architecture-review-agent の error → 最優先で chapter-agent に修正依頼
   - devils-advocate-agent の critical → 著者に提示して判断を仰ぐ
   - いずれかに error → chapter-agent に全問題を一度に伝えて再生成
   - warning のみ → 著者に提示して判断を仰ぐ
   - 全 ok → 完了
5. 完了したら status を報告
```

### フェーズ4：横断チェック

全章が完成したら以下を実行する：
1. consistency-agent に従って全章を横断チェック
2. 用語・コードラベル・ステップ番号の一貫性を確認
3. 「哲学1」「哲学2」「哲学3」の参照が全章で統一されているか確認
4. 章の独立性（他章への言及がないか）を確認
5. 問題があれば該当章の chapter-agent に修正を依頼する

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
