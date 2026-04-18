# agents/chapter-agent.md
# 1章分を担当するエージェント（design-patterns 固有版）

---

## 役割

1章分を担当して完成させる。
他の章に依存しない。第0章の構造だけを前提とする。

---

## 受け取る引数

- `chapter_number` : int（例：2）
- `pattern_file` : patterns/{name}.yaml（例：patterns/facade.yaml）

※ 前章ファイルへの参照は不要。各章は完全独立。

---

## 実行手順

### ステップ1：インプットを読む

1. `../../shared/skills/author-voice.md` を読む（最重要・最初に読む）
2. `CLAUDE.md` を読む（特に「執筆品質ルール」「コードルール」「読者視点チェック」を熟読する）
3. 指定された `pattern_file` を読む
4. `templates/chapter-template.md` を読む

---

### ステップ2：章を生成する

`chapter-template.md` を唯一の正とし、その指示通りに各節を生成する。
ステップ0〜7のH2見出しを必ず使う。順序を崩さない。

**各節で何を書くかは `chapter-template.md` に定義されている。このファイルには書かない。**
章の構造フローを変えたい場合は `chapter-template.md` だけを変更すれば良い。

重要な生成ルール（CLAUDE.mdより）：
- 各サービスは宣言だけでなく実体のある実装で示す
- ステップ2（〇.3）に関係者ヒアリングの会話シーンを入れる（変動/不変を確定する前）
- インターフェース名はビジネス責任で命名する（実装手段で付けない）
- 試行は責任チェックが通るまで繰り返す（複数回可）
- コードに `// 💭` は使わない。気づきは散文で説明する
- 使ってよい文法：class / virtual / コンストラクタ / メソッド呼び出し / if / for / 生ポインタ
- 使わない文法：lambda・スマートポインタ・templateメタプログラミング・C++17以降の機能

---

### ステップ3：自己採点

`CLAUDE.md` の品質チェックリストを**全項目**確認する。
未達の項目があれば該当節を再生成する。

**チェック項目の正は `CLAUDE.md` にある。このファイルには複製しない。**

確認すべき主要カテゴリ（詳細は CLAUDE.md を参照）：
- 構造チェック（H2見出し・クラス図・図一式・起点コード・BatchApplication）
- 責任チェック（責任定義・責任チェック表・最終責任テーブル）
- 関係者ヒアリング・契約設計チェック（〇.3のヒアリング会話・インターフェース命名）
- 最終設計チェック（DIP全適用・BatchApplication・main()キックのみ）
- 執筆品質チェック（禁止表現・仕様説明・数字根拠・次章予告なし）
- 著者の人格チェック（口癖3〜5箇所・否定的ラベルなし）

---

### ステップ4：ファイルを書き出す

`output/chapter{nn}.md` に書き出す。
（例：chapter_number=2 なら `output/chapter02.md`）

---

### ステップ5：完了報告

```json
{
  "agent": "chapter-agent",
  "chapter": 2,
  "pattern": "Facade",
  "status": "complete",
  "output": "output/chapter02.md",
  "self_check": {
    "step0_to_7_headings": true,
    "universal_question_used": true,
    "before_class_diagram": true,
    "after_class_diagram": true,
    "dependency_graphs_complete": true,
    "basic_oop_syntax_only": true,
    "no_💭_comments": true,
    "main_with_result_in_step1": true,
    "responsibility_check_table_in_step1": true,
    "stakeholder_interview_in_step2": true,
    "interface_named_by_business_not_implementation": true,
    "trial_with_responsibility_check": true,
    "batch_application_assembles": true,
    "main_kicks_only": true,
    "test_proves_same_behavior_in_step7": true,
    "final_responsibility_table": true,
    "change_scenario_table": true,
    "core_sentence_after_section1": true,
    "no_forbidden_phrases": true,
    "no_next_chapter_preview": true,
    "spec_in_table": true,
    "numbers_have_evidence": true,
    "line_level_annotations": true,
    "di_code_included": true,
    "test_syntax_explained": true,
    "no_other_chapter_ref": true,
    "reader_perspective_ok": true,
    "author_voice_3_to_5": true,
    "no_draft_comments": true
  }
}
```
