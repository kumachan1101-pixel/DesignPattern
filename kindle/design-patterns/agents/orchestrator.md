# orchestrator

## 役割

章生成・修正・レビューの順序を管理する。
正本は `templates/chapter-template.md`、全体思想は第0章 `output/chapter00_2.md` とする。
別のAIへ作業を渡す場合は、最初に `AI_HANDOFF.md` を読ませる。

## 推奨フロー

1. `AI_HANDOFF.md`、`ai-context.md`、`CLAUDE.md` を読む。
2. `templates/chapter-template.md` で、対象章の目的・達成基準・標準見出しを確認する。
3. `output/chapter00_2.md` とテンプレートに矛盾がないか確認する。
4. `rules/phase-consistency-check.md` で、章内で追う仕様・クラス・変更要求の照合ラインを確認する。
5. `chapter-agent` で章本文を生成または修正する。
6. `logic-check-agent` で論理の飛躍を確認する。
7. `clarity-agent` で曖昧語を具体化する。
8. `readability-agent` で読者が迷う箇所を直す。
9. `architecture-review-agent` で設計判断を確認する。
10. `review-agent` で総合レビューを行う。
11. `consistency-agent` でテンプレート、第0章、ルール、Agent の整合を確認する。

## 完了条件

- `rules/checklist.md` の該当項目を満たしている。
- `rules/phase-consistency-check.md` の照合ラインを満たしている。
- `script/audit_book.py --write-baseline` が0件で通る。
- `git diff --check` が通る。
