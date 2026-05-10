# Gemini への章執筆指示書（第9〜12章 応用編）

## 共通：毎回添付するファイル（この順で渡す）

1. `shared/skills/author-voice.md`
2. `CLAUDE.md`
3. `rules/step5-6-model.md`
4. `templates/chapter-template.md`
5. `templates/chapter-template2.md`
6. `design-philosophy.md`
7. 章ごとの pattern yaml（下記参照）
8. `agents/chapter-agent.md`

---

## 第9章

**添付する pattern yaml：**
- `patterns/strategy.yaml`
- `patterns/state.yaml`

**指示文：**

```
添付ファイルをすべて読んだうえで、第9章を執筆してください。

- 執筆手順は agents/chapter-agent.md の「実行手順」に従う
- テンプレートは chapter-template2.md（応用編）を chapter-template.md の S0〜S8 構造に差分適用して使う
- 章タイトル：第9章　【Strategyパターン】×【Stateパターン】
- ドメイン：ECサイト注文処理（複合）
- 出力ファイル：output/chapter09.md
```

---

## 第10章

**添付する pattern yaml：**
- `patterns/facade.yaml`
- `patterns/observer.yaml`
- `patterns/factory-method.yaml`

**指示文：**

```
添付ファイルをすべて読んだうえで、第10章を執筆してください。

- 執筆手順は agents/chapter-agent.md の「実行手順」に従う
- テンプレートは chapter-template2.md（応用編）を chapter-template.md の S0〜S8 構造に差分適用して使う
- 章タイトル：第10章　【Facadeパターン】×【Observerパターン】×【Factory Methodパターン】
- ドメイン：外部連携バッチシステム
- 出力ファイル：output/chapter10.md
```

---

## 第11章

**添付する pattern yaml：**
- `patterns/template-method.yaml`
- `patterns/decorator.yaml`
- `patterns/command.yaml`

**指示文：**

```
添付ファイルをすべて読んだうえで、第11章を執筆してください。

- 執筆手順は agents/chapter-agent.md の「実行手順」に従う
- テンプレートは chapter-template2.md（応用編）を chapter-template.md の S0〜S8 構造に差分適用して使う
- 章タイトル：第11章　【Template Methodパターン】×【Decoratorパターン】×【Commandパターン】
- ドメイン：レポート生成エンジン
- 出力ファイル：output/chapter11.md
```

---

## 第12章

**添付する pattern yaml：**
- `patterns/state.yaml`
- `patterns/observer.yaml`
- `patterns/strategy.yaml`

**指示文：**

```
添付ファイルをすべて読んだうえで、第12章を執筆してください。

- 執筆手順は agents/chapter-agent.md の「実行手順」に従う
- テンプレートは chapter-template2.md（応用編）を chapter-template.md の S0〜S8 構造に差分適用して使う
- 章タイトル：第12章　【Stateパターン】×【Observerパターン】×【Strategyパターン】
- ドメイン：承認ワークフローシステム
- 出力ファイル：output/chapter12.md
```

---

## 注意事項

- 各章は独立したGeminiセッションで実行する
- 前章のファイルを渡す必要はない（各章は完全独立）
- 出力が途中で切れた場合は「続きを書いてください」と指示する
- 完成後は agents/review-agent.md を使ってレビューを実施する
