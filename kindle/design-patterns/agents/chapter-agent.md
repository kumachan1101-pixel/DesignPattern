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
2. `CLAUDE.md` を読む（執筆品質ルール・コードルール・読者視点チェックを熟読する）
3. **`rules/step5-6-model.md` を読む**（S5〜S8の執筆ルール。接続点の特定・2×2マトリクス接続図・コスト天秤・対策実施。ここを理解してから章を生成する）
4. **`design-philosophy.md` を読む**（設計思想カタログ。全テーマ・全問いを把握する）
5. 指定された `pattern_file` を読む
6. `templates/chapter-template.md` を読む（各節の生成指示の唯一の正）

---

### ステップ2：章を生成する

`chapter-template.md` を唯一の正とし、その指示通りに各節を生成する。
ステップ0〜8（S0〜S8）のH2見出しを必ず使う（9ステップ）。順序を崩さない。

**各節で何を書くかは `chapter-template.md` に定義されている。このファイルには書かない。**
章の構造フローを変えたい場合は `chapter-template.md` だけを変更すれば良い。

**生成前に `design-philosophy.md` の全問い（Q1-1〜Q8-2）を確認し、章がそれぞれに答えていることを確かめてから書き始める。**
新しい設計の問いが見つかったときは `design-philosophy.md` に追加するだけでよい。

重要な生成ルール（CLAUDE.mdより）：
- 章の冒頭（この章の核心の直後・S0の前）に `## この章を読むと得られること` を必ず書く
  - 「〜できるようになる」形式で3〜4項目。パターン名を前面に出さない
  - **【重要】構造分析の眼で書く。以下の3視点を基本とする：**
    1. どんな観点でコードの変動箇所を識別するか（変わる理由の見極め方）
    2. 接続点がどの形（2×2マトリクスのどのセル）になっているかをどう読み取るか
    3. 接続点の形を変えることで変更がどのように局所化されるか
  - パターン名は登場させない。「〇〇パターンを使える」ではなく「〇〇という構造の変化を見極められる」と書く
- この章のドメインが CLAUDE.md のドメイン割り当て表と一致しているか確認してから書き始める
- 各サービスは宣言だけでなく実体のある実装で示す
- S0（X.0）はコードの事実のみ（仕様表・クラス図・責任一覧）。この段階では仮説を立てない
- S2（X.3）で初めて仮説を立てる：S0・S1の観察から仮説テーブルを作り、そのあと関係者ヒアリングで確定する
- インターフェース名はビジネス責任で命名する（実装手段で付けない）
- 試行は責任チェックが通るまで繰り返す（複数回可）
- コードに `// 💭` は使わない。気づきは散文で説明する
- 使ってよい文法：class / virtual / コンストラクタ / メソッド呼び出し / if / for / 生ポインタ
- 使わない文法：lambda・スマートポインタ・templateメタプログラミング・C++17以降の機能

**責任チェックのルール：**

- 「具体型を呼んでいる＝責務外」ではない。判断基準は「その知識は誰の判断で変わるか」
- 変わる理由が別の担当者・別のタイミングであれば責務外（❌）
- 今後も変わらない・変わっても影響が軽微なら責務内（✅）
- 責任チェック表の各行に「なぜそう判断したか」を1文で必ず書く

**禁止事項：**

- 略語を使わない。初出時は必ず正式名称で書く。誰でも知っている略語（CPU、APIなど）以外は略さない
- ケーブル比喩で「ハンダ付け」「基板に固定」「溶接」など、実際には起こらない表現を使わない。起こりうる繋ぎ方（ケーブルを直差し、アダプターを挟む、ハブ経由など）のみで説明する
- 「最初からデザインパターンの正解を当てはめようとしない」「パターンを先に決めない」系の一文を書かない。この本の読者はパターンを知らない前提であり、言及すること自体が矛盾する
- パターン名（Strategy、State、Decoratorなど）はS6より前に登場させない

**S6の案構成ルール（必須）：**

S6では必ず案0〜案4の5案を連番で示す。「案N」という表現は使わない。
- 案0：現状維持（何もしない）
- 案1：具体×直接
- 案2：抽象×直接
- 案3：具体×間接
- 案4：抽象×間接
各案には「この形にするための考え方と準備」（どう考えてどう実装するか）を必ず書く。

**S6では結論を出さない（最重要）。**
「この章では〇〇が目的のため〇〇を選びます」という一文はS6に書いてはいけない。
S6の役割は全案を並べることのみ。どの案を採用するかはS7（コスト天秤）で初めて決める。
コスト天秤（S7）では全5案を比較してから採用案を選ぶ。

**接続点のコネクタ比喩（S4の原因分析末尾で使う）：**

比喩は章冒頭ではなく、S4で「なぜこの構造が痛みを生むか」が見えた後に登場させる。
読者が問題を理解した瞬間に「それはケーブルで言うとこういう状態だ」と示すことで、比喩が思考の道具として機能する。

- **具体×直接**：Lightningケーブルで直差し（iPhone専用端子・直接つなぐ）
- **抽象×直接**：USB-Cケーブルで直差し（どのメーカーでも使える規格・直接つなぐ）
- **具体×間接**：Lightning→USB-C変換アダプター経由（特定機種用アダプターを挟む）
- **抽象×間接**：MacBook→USB-Cハブ→モニター（ハブがどの機器を繋ぐか知らない）
- 軸の対応を比喩の近くに必ず明記すること：
  - 直接 ＝ ケーブルを直差し（間に別のモノを挟まない）
  - 間接 ＝ アダプターを挟む（間に別のモノが入る）
  - 具体 ＝ その機種専用（特定の相手を知っている）
  - 抽象 ＝ どれでも使える規格（型・インターフェースだけ知っている）
- S4で「現在の接続形態（例：具体×直接）」を示し、S6で「対策案がどの接続形態に変えるか」を示すことで、接続形態の変化が設計の変化として見えるようにする
- **「分ける」という判断はS4末尾で下す。** S4の末尾で「○○と△△は変わる理由が異なるため分けるべき」と結論づけてからS5に進む。S5冒頭はその判断の続きとして書く

---

# 接続点マトリクス図のImagePromptルール

各章のS4（原因分析）末尾の「ケーブルで考える」部分に、以下の形式でImagePromptを必ず出力してください。

## 出力形式

```
[ImagePrompt: A clean flat 2x2 matrix diagram showing cable/connector metaphors for software design patterns.
The matrix has two axes: vertical axis labeled "具体（専用規格）" (top) to "抽象（汎用規格）" (bottom), horizontal axis labeled "直接（直差し）" (left) to "間接（アダプター経由）" (right).
Four cells:
- Top-left (具体×直接): Lightning cable plugged directly into iPhone. Label: "Lightning直差し"
- Top-right (具体×間接): Lightning-to-USB-C adapter between iPhone and charger. Label: "専用アダプター経由"
- Bottom-left (抽象×直接): USB-C cable plugged directly. Label: "USB-C直差し"
- Bottom-right (抽象×間接): MacBook connected via USB-C hub to monitor, USB drive, and SD card. Label: "USB-Cハブ経由"
HIGHLIGHT the [該当セル名] cell with a bright colored border and slightly larger size. All other cells are muted gray.
Minimalist flat illustration style, white background, no gradients, Japanese labels on axes.]
```

## 該当セル名の対応表（章ごとに差し替え）

| パターン | 該当セル名（ハイライト対象） |
|---|---|
| Strategy | bottom-left (抽象×直接) |
| Template Method | top-left (具体×直接) |
| Facade | top-right (具体×間接) |
| Factory Method | bottom-left (抽象×直接) |
| Observer | bottom-right (抽象×間接) |
| Decorator | bottom-right (抽象×間接)、かつ「複数のアダプターを直列に重ねる」旨を追記 |
| Composite | bottom-left (抽象×直接)、かつ「ハブ自身もUSB-C機器としてネスト可能」旨を追記 |
| Command | CommandはImagePromptを出力しない（代わりに録画予約リモコンの比喩をテキストで説明する） |

## chapter00_2 専用ルール

chapter00_2では、接続点を1象限ずつ紹介するため、各象限を紹介するタイミングで単独のImagePromptを出力する（4回出力）。
その際は該当セルのみをハイライトし、残り3セルはグレーアウトする。

## 禁止事項
- ImagePromptに "Note" という文字を含めないこと（既存ルールと同じ）
- 1章につきImagePromptは原則1回のみ（Decoratorは積み重ねの図を追記してよい）

---

**S5の出力ルール（課題定義）：**
- 接続点の特定（どこに何個の接続点があるか）を必ず出力すること
- 非機能制約（変更頻度・パフォーマンス・メモリ）を確認し表で示すこと
- クライアント影響範囲（どのクラスが影響を受けるか）を明記すること
- 課題まとめ表（接続点・分けた理由・非機能制約・クライアント影響の4列）を必ず出力すること

**S6の出力ルール（対策案検討）：**
- 冒頭に必ず2×2マトリクス接続図（mermaid）を入れること
- 案0（分けない）から案N（完全対応）の順で展開すること

- S7に「使わない方が良い状況」「過剰コード例」「最小コスト代替案との比較」を必ず含める
- S8の変更シナリオ表で「変わるクラス・変わらないクラス」を明示する（影響範囲の可視化）

---

### ステップ3：自己採点

生成した章を**読者として上から一度通読**し、以下を確認する。問題があれば該当節を再生成してから次に進む。

**意味・品質チェック（構造の有無ではなく、内容の質を確認する）：**

| チェック項目 | 確認する問い | よくある失敗パターン |
|:---|:---|:---|
| S1_responsibility_each_row_has_justification | 責任チェック表の全行に「判断理由」列があり、1文以上書いてあるか | 行がある＝OKとして理由が空のまま |
| S1_no_absolute_claim_concrete_equals_bad | 「具体型を使っている＝責務外」という根拠なし断言がないか | 変更可能性を示さずに❌をつけている |
| S4_split_decision_stated_at_end | S4末尾に「○○と△△は変わる理由が異なるため分けるべき」という結論文があるか | S4末尾が「ケーブルで考える」比喩だけで終わり、判断が明示されていない |
| S4_cable_metaphor_no_soldering_or_welding | ケーブル比喩にハンダ付け・溶接・基板固定などの表現がないか | 日常では起こらない行為を比喩に使っている |
| S6_all_5_cases_present | 案0〜案4（5案）が全て見出しとして存在するか | 案0と案4だけ、または案0と案2だけなど一部省略 |
| S6_no_conclusion_sentence | S6に「この章では〇〇が目的のため〇〇を選びます」という一文がないか | S6で案を並べる前・並べた後に結論を出してしまっている |
| S6_each_case_has_howto_explanation | 案1〜案4それぞれに「この形にするための考え方と準備」の説明があるか | コード例だけあって「どう考えてこの形に変えるか」が書かれていない |
| S7_conclusion_only_in_S7 | 「採用する対策案：案X」という採用決定がS7にのみ現れるか | S6にも採用決定の文が混入している |
| S7_all_5_cases_compared | S7のコスト天秤表に案0〜案4が全行あるか | 案0と採用案の2行しかない |
| pattern_name_not_before_S6 | S0〜S5のどこにもパターン名（Strategy, Facade等）が出ていないか | S1の「要するに〜パターン」などで早出しされている |
| no_unexplained_abbreviations | MES・ERP・ORM等の業界略語が初出時に正式名称＋括弧説明つきか | 略語をそのまま使い「分かるだろう」と前提している |
| no_pattern_application_sermon | 「最初からパターンを当てはめようとしない」系の説教文がないか | 読者がパターンを知っている前提の文が混入している |
| review_section_has_promises_fulfillment_table | 整理セクションに「得られること1〜4がどのステップで示されたか」の対応表があるか | 振り返りが設計原則の確認だけで章冒頭の約束に戻っていない |

**構造・品質チェック（CLAUDE.md を参照）：**

**設計思想チェック（design-philosophy.md の全問いを確認）：**
- テーマ1（責任）：Q1-1〜Q1-4 全て回答済みか
- テーマ2（依存）：Q2-1〜Q2-3 全て回答済みか
- テーマ3（組み立て）：Q3-1〜Q3-3 全て回答済みか
- テーマ4（命名）：Q4-1〜Q4-2 全て回答済みか
- テーマ5（契約合意）：Q5-1〜Q5-2 全て回答済みか（ヒアリングリスク→〇.10伏線回収の対応確認）
- テーマ6（型と隠蔽）：Q6-1〜Q6-3 全て回答済みか
- テーマ7（変更耐性）：Q7-1〜Q7-2 全て回答済みか
- テーマ8（判断）：Q8-1〜Q8-2 全て回答済みか

**構造・品質チェック（CLAUDE.md を参照）：**
- 構造チェック（H2見出し・クラス図・図一式・起点コード・BatchApplication）
- 責任チェック（責任定義・責任チェック表・最終責任テーブル）
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
    "reader_benefit_section_exists": true,
    "reader_benefit_no_pattern_name_upfront": true,
    "reader_benefit_3_to_4_items": true,
    "domain_matches_assignment_table": true,
    "step0_to_8_headings": true,
    "system_overview_before_universal_question": true,
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
    "step5_connection_points_identified": true,
    "step5_nonfunctional_constraints_checked": true,
    "step5_summary_table_exists": true,
    "step6_2x2_matrix_diagram_exists": true,

    "S1_responsibility_each_row_has_justification": true,
    "S1_no_absolute_claim_concrete_equals_bad": true,

    "S4_split_decision_stated_at_end": true,
    "S4_cable_metaphor_no_soldering_or_welding": true,

    "S6_all_5_cases_present": true,
    "S6_no_conclusion_sentence": true,
    "S6_each_case_has_howto_explanation": true,

    "S7_conclusion_only_in_S7": true,
    "S7_all_5_cases_compared": true,

    "pattern_name_not_before_S6": true,

    "no_unexplained_abbreviations": true,
    "no_pattern_application_sermon": true,

    "review_section_has_promises_fulfillment_table": true,

    "batch_application_assembles": true,
    "main_kicks_only": true,
    "test_proves_same_behavior_in_step8": true,
    "final_responsibility_table": true,
    "change_scenario_table": true,
    "impact_analysis_graph_in_step3": true,
    "min_cost_alternative_in_step7": true,
    "overdesign_example_in_step7": true,
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
