# Gemini への章執筆指示書（第9〜12章 応用編）

---

## 共通：毎回添付するファイル（7点固定）

| # | ファイル |
|---|---|
| 1 | `shared/skills/author-voice.md` |
| 2 | `CLAUDE.md` |
| 3 | `rules/step5-6-model.md` |
| 4 | `templates/chapter-template.md` |
| 5 | `templates/chapter-template2.md` |
| 6 | `design-philosophy.md` |
| 7 | `agents/chapter-agent.md` |

---

## 章ごとの追加ファイル（pattern yaml）

| 章 | 追加ファイル（計10点以内） |
|---|---|
| 第9章 | `patterns/strategy.yaml` `patterns/state.yaml` |
| 第10章 | `patterns/facade.yaml` `patterns/observer.yaml` `patterns/factory-method.yaml` |
| 第11章 | `patterns/template-method.yaml` `patterns/decorator.yaml` `patterns/command.yaml` |
| 第12章 | `patterns/state.yaml` `patterns/observer.yaml` `patterns/strategy.yaml` |

---

## ステップ別指示文（1セッション内でこの順に送る）

### 最初の指示（セッション開始時に1回だけ送る）

```
添付ファイルをすべて読んでください。
これから第X章を、S0〜S8のステップ別に作成します。
テンプレートは chapter-template2.md（応用編）を chapter-template.md の S0〜S8 構造に差分適用して使ってください。
章タイトル・ドメインは下記のとおりです。

章タイトル：第X章　【〇〇パターン】×【△△パターン】
ドメイン：〇〇〇〇

準備ができたら「了解しました」とだけ返してください。
```

### ステップ別の指示（順番に送る）

```
第X章のS0（クラス構成と責任を読む）を作成してください。
```

```
第X章のS1（実装コードを読む）を作成してください。
```

```
第X章のS2（仮説を立て、関係者に確認する）を作成してください。
```

```
第X章のS3（課題分析）を作成してください。
```

```
第X章のS4（原因分析）を作成してください。
```

```
第X章のS5（課題を定義する）を作成してください。
```

```
第X章のS6（対策案の検討）を作成してください。
```

```
第X章のS7（対策選定）を作成してください。
```

```
第X章のS8（決断と未来）を作成してください。
```

```
整理・振り返り・パターン解説を作成してください。
```

---

## 各章の章タイトルとドメイン

| 章 | 章タイトル | ドメイン |
|---|---|---|
| 第9章 | 【Strategyパターン】×【Stateパターン】 | ECサイト注文処理（複合） |
| 第10章 | 【Facadeパターン】×【Observerパターン】×【Factory Methodパターン】 | 外部連携バッチシステム |
| 第11章 | 【Template Methodパターン】×【Decoratorパターン】×【Commandパターン】 | レポート生成エンジン |
| 第12章 | 【Stateパターン】×【Observerパターン】×【Strategyパターン】 | 承認ワークフローシステム |

---

## 注意

- 出力が途中で切れたら「続きを書いてください」と送る
- 各章は独立したセッションで実施する（前章のファイルは不要）
