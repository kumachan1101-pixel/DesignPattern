# orchestrator

## 役割

章生成・修正・レビューの順序を管理する。
正本は `templates/chapter-template.md`、全体思想は第0章 `output/chapter00_2.md` とする。

## 推奨フロー

1. `ai-context.md` と `CLAUDE.md` を読む。
2. `templates/chapter-template.md` で、対象章の目的・達成基準・標準見出しを確認する。
3. `chapter-agent` で章本文を生成または修正する。
4. `logic-check-agent` で論理の飛躍を確認する。
5. `clarity-agent` で曖昧語を具体化する。
6. `readability-agent` で読者が迷う箇所を直す。
7. `architecture-review-agent` で設計判断を確認する。
8. `review-agent` で総合レビューを行う。
9. `consistency-agent` でテンプレート、第0章、ルール、Agent の整合を確認する。

## 完了条件

- `rules/checklist.md` の該当項目を満たしている。
- `script/audit_book.py --write-baseline` が0件で通る。
- `git diff --check` が通る。
