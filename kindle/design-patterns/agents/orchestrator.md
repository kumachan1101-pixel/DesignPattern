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
5. 仕様がコードへ紐づく粒度になっているか、簡略化した入出力の省略範囲が説明されているか確認する。
6. `chapter-agent` で章本文を生成または修正する。
7. `logic-check-agent` で論理の飛躍を確認する。
8. `clarity-agent` で曖昧語を具体化する。
9. `readability-agent` で読者が迷う箇所を直す。
10. `architecture-review-agent` で設計判断を確認する。
11. `review-agent` で総合レビューを行う。
12. `consistency-agent` でテンプレート、第0章、ルール、Agent の整合を確認する。

## 完了条件

- `rules/checklist.md` の該当項目を満たしている。
- `rules/phase-consistency-check.md` の照合ラインを満たしている。
- 仕様がコードに出る値・状態・判定条件・出力名へ紐づく粒度になっている。
- 掲載コードの簡略化範囲が本文または図で説明されている。
- `script/audit_book.py --write-baseline` が0件で通る。
- `git diff --check` が通る。
