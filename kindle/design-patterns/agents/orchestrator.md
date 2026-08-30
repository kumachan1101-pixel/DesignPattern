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
5. 現行／変更後の要求ID、変更ID、課題ID、リスクIDの台帳と用途が混同されず、要求と課題が別系統か確認する（まとまった働きを束ねる機能IDは設けない）。
6. フェーズ2が見当→確認質問→ヒアリング回答、フェーズ5が原因→候補→全体評価→課題ID確定、フェーズ6が構想→要点コード→採用判断の順になり、完成クラス図はフェーズ7だけにあるか確認する。
7. 1-1冒頭に入力・主要処理・出力・掲載コードでの代替をまとめた全体要約があり、仕様がコードへ紐づく粒度になっているか、簡略化した入出力の省略範囲が説明されているか確認する。
8. 論点から外す処理について、実際の動き、代替表現、割愛理由、設計論点への影響が補足されているか確認する。
9. `chapter-agent` で章本文を生成または修正する。
10. `logic-check-agent` で論理の飛躍を確認する。
11. `clarity-agent` で曖昧語を具体化する。
12. `readability-agent` で読者が迷う箇所を直す。
13. `architecture-review-agent` で設計判断を確認する。
14. `review-agent` で総合レビューを行う。
15. `consistency-agent` でテンプレート、第0章、ルール、Agent の整合を確認する。
16. 修正があれば原因を分析し、再発しうるなら正本（テンプレート・ルール・Agent・検証スクリプト）を見直し、`rules/recurrence-prevention.md` に記録する。

## 完了条件

- `rules/checklist.md` の該当項目を満たしている。
- `rules/phase-consistency-check.md` の照合ラインを満たしている。
- 仕様がコードに出る値・状態・判定条件・出力名へ紐づく粒度になっている。
- 1-1の最初に、要求表より前にシステム全体の大筋とスタブの位置を説明する要約がある。
- 掲載コードの簡略化範囲が本文または図で説明されている。
- 論点から外す処理の実際の動き、代替表現、割愛理由、設計論点への影響が補足されている。
- 修正の原因を分析し、再発しうる場合は正本を見直して `rules/recurrence-prevention.md` に記録した。
- 全有効要求IDの受入・回帰エビデンス（継続要求の回帰で既存動作の消失を検出）、課題IDの構造結果、変更IDの変更影響が分離して追跡されている。
- 2-1の見当が確認質問と確認先へ変換され、2-3の回答へ接続している。
- `script/check_mermaid.py` で全Mermaidが実レンダリングでき、図内にリテラル`\n`がない。
- `script/validate_book.py` が通る。
- `script/audit_book.py --write-baseline` が0件で通る。
- `git diff --check` が通る。
