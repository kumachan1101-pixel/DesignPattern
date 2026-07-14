# フェーズ間コード整合 監査（2026-07-13）

## 対応結果（2026-07-14）

このファイルの表は、修正前の状態を残す監査証跡です。出版用成果物の生成を除き、ここで挙げた残件は次のように対応しました。

| 監査項目 | 対応結果 |
|---|---|
| A. 中間フェーズで境界が脱落して見える | 第1・2・3・5・6・7・8・9・10・11章のフェーズ3・6へ「中間コードの継続条件」を追加した。差分抜粋の外で維持するDB・Repository・Registry・Gateway・履歴・検証・副作用を明記し、`validate_book.py` で両フェーズの境界名を必須化した |
| B. 中心メソッドのシグネチャ drift | 最新コードと再照合した。第7・9・10章の単なる引数名ブレは修正済み。第2章の要求オブジェクト、第3章のState側 `ctx`、第11章の引数なし骨格は、値や操作を別責任へ移した設計結果であり、その移動先を本文へ明記した。第1・5・10章の意図的な段階差も継続条件として説明した |
| C. 第12章の仕様図先行 | `WorkflowCaseRepository`・`ApproverDatabase`・`NotificationTargetRepository` をフェーズ1〜7へ連鎖させ、操作・状態語彙・金額型を統一済み |
| D. 局所修正 | `Approver` 重複と第3章の存在しない履歴説明は修正済み |
| タスク管理 | `review-tasks.md` を現在の正本、文字化けした `TASK.md` を旧管理ファイルとして統一した |

機械検証が扱える範囲は構造・代表語・コード実行結果です。中間コードは全体コードの再掲ではなく差分抜粋であるため、境界を省略する場合は「何を維持するか」を明記する契約で整合を保ちます。

方針：**コードを仕様に合わせる**。1-1仕様図・7-1解決コードが正、1-4〜フェーズ6の中間コードを
それに合わせて整合させる。本書は「同じ対象を全フェーズで追う」ことを掲げる（CLAUDE.md「フェーズ間整合」）
が、実際には中心クラスのシグネチャと DB/検証/境界クラスが**フェーズ1(1-4)→フェーズ3〜6→フェーズ7(7-1)で
三者三様**になっている。以下はその全件洗い出し。

判定の見方：
- 1-4＝フェーズ1現状コード、P3＝フェーズ3痛みコード、P6＝フェーズ6対策検討、7-1＝フェーズ7解決コード。

---

## A. 境界/DB/検証クラスの脱落（フェーズ3・6で中心クラスが痩せる）

各フェーズのコードに登場する DB/Repository/境界/検証クラス（Database, Repository, Registry,
Catalog, Gateway, Notifier, Renderer, Log, History, RenderingApi など）の有無。
**「1-4にあるが P3/P6 で消える → 7-1で復活」= フェーズ間整合違反。**

| 章 | 1-4（現状） | P3（痛み） | P6（対策検討） | 7-1（解決） | 判定 |
|---|---|---|---|---|---|
| 1 | CustomerDatabase, CheckoutResultRenderer | 同左 | CustomerDatabase | 同左 | ほぼ一致（P6でRenderer欠落・軽微） |
| 2 | AccountDatabase, BankGateway, TransferHistory | BankGatewayのみ | BankGatewayのみ | 全部 | **P3/P6でAccountDatabase・TransferHistory脱落** |
| 3 | EventDatabase | なし | なし | EventDatabase, ReservationHistory | **P3/P6でEventDatabase脱落** |
| 5 | CategoryDatabase | なし | ActionHistoryのみ | CategoryDatabase, LedgerRepository, BalanceViewRenderer, ActionHistory | **P3/P6でCategoryDatabase等脱落** |
| 6 | MenuDatabase | なし | なし | MenuDatabase, ToppingCatalog, OrderLog | **P3/P6でMenuDatabase脱落** |
| 7 | ProductDatabase, Email/Chat Notifier | 通知のみ（ProductDatabase無） | 通知のみ | ProductDatabase, 通知, StockEventLog | **P3/P6でProductDatabase・在庫検証脱落** |
| 8 | ProcessorRegistry, PaymentGatewayClient, PaymentStatusClient, PaymentLog | Registry, Gatewayなど | **なし（全滅）** | 全部 | **P6で境界全滅** |
| 9(09_2) | UserDatabase（SlaTimer/AssignmentEventは境界の概念・散文のみ=許容） | UserDatabase | なし | UserDatabase, TicketEventLog | **P6で脱落** |
| 10 | PartnerDatabase | PartnerDatabase | 脱落（INotifierのみ） | 全部 | **P6でPartnerDatabase脱落** |
| 11 | ReportRenderingApi, TemplateRegistry | RenderingApi, ReportHistory | RenderingApiのみ | RenderingApi, TemplateRegistry, ReportLog | **P3/P6でTemplateRegistry脱落** |
| 12 | ApproverDatabase | **なし** | NotificationTargetRepository＋通知（ApproverDatabaseは無） | ApproverDatabase, WorkflowCaseRepository, NotificationTargetRepository, 通知, ApprovalLog | **P3/P6でApproverDatabase脱落・P6は1-4に無いRepositoryを先取り** |

→ ほぼ全章で、フェーズ3・6の中間コードが 1-4 の検証/境界層を落としている。

## B. 中心メソッドのシグネチャ drift（章内で3〜4通りに揺れる）

| 章 | 中心メソッド | 1-4 | P3/P6（中間） | 7-1 | 問題 |
|---|---|---|---|---|---|
| 1 | `calculate` | `(const Order&)` | `(Order&, memberType, campaign…)` | `(const Order&)` | 中間でmemberType等を引数に外出し→戻る |
| 2 | `transfer` | 要求オブジェクト前提 | 位置引数 `(toAccount, amount, otp)` | `(const TransferRequest&)` | 中間で要求オブジェクトを失う |
| 3 | `reserve` | `()` | `(std::string& status)` | `(TicketReservation* ctx)` | 状態の受け渡し方が3通り |
| 5 | `onAddExpenseClick` | `(int amount, categoryId)` | `()` 引数なし | `(IAction* cmd)` | 中間で引数消失 |
| 7 | `reduceStock` | `(productId, int quantity)`＋DB検証 | 同シグネチャだが**DB検証・在庫0・閾値判定を削除** | `(…)`＋検証復活 | 本体の検証が中間で消える |
| 9 | `execute` | `(string userType)` | `(string userTier)` | — | 引数名 userType↔userTier のブレ |
| 10 | `execute` | `(string partnerId)` | `(string targetId)` | `(IClientCreator*)` | 引数名 partnerId↔targetId のブレ |
| 11 | `generate` | `(format, addGraph, addLogo)` | `(addGraph, addLogo)` / `()` | 骨格メソッド | 中間でformat引数消失 |
| 12 | `process` | `(status, int amount, approverId)` | `(status, double amount, bool)` | `(WorkflowEvent, ApprovalRequest)` | **int↔double、approverId消失、状態指定が4通り** |

## C. 仕様図(1-1)がコード(1-4)より先行している

1-1の「保存データとアクセス関係」図は 7-1相当の Repository 構造を示すが、1-4コードは簡略で不一致。

| 章 | 1-1図/説明が示す構造 | 1-4コードの実態 | 判定 |
|---|---|---|---|
| 12 | `WorkflowCaseRepository` から状態を読む／`NotificationTargetRepository` から通知先を読む（「利用者が毎回指定しない」） | `process(status,…)` で状態を**引数で受け取り**、`notify()` で**inline通知**（Repository無し） | **図と正反対** |
| 3 | 予約履歴を持つ（境界表に記載・除去済） | 1-4に履歴なし | 対応済（境界表から除去） |

## D. この監査で対応済み（局所修正）

- 第12章：未使用の死んだクラス `Approver`（`ApproverInfo`/`ApproverDatabase` と重複）を削除、`ApproverInfo` へ一本化。
- 第3章：1-4境界表からコードに無い `ReservationHistory` 行を除去。

---

## 修正時に用いた順序（対応済み）

1. **第12章（発端・最重症）を見本化**：1-4〜フェーズ6の `WorkflowManager` を、1-1図と7-1に合わせて
   `WorkflowCaseRepository`（状態をIDで読む）・`ApproverDatabase`（int・approverId）・
   `NotificationTargetRepository`＋通知境界に統一。`process` のシグネチャを全フェーズで一致させる。
   実行結果を再検証。
2. 見本OK後、**第7・3・5・10・6・2・11・9・8・1章**へ同じ整合を展開（Aの脱落・Bのシグネチャを1-4/7-1へ統一）。
3. 各章 `check_execution_output.py` で実行結果一致を再確認。

> 各フェーズは前フェーズの出力を入力にする（CLAUDE.md 7フェーズ）。中間フェーズだけ別物のコードを
> 出すと、読者は「同じシステムを追っている」感覚を失う。中間コードは 1-4現状コード＋変更要求を起点に、
> 段階的に7-1へ変形する連続体でなければならない。

上記の順序で第12章を先に修正し、残る各章は差分抜粋の継続条件と責任移動の説明を追加しました。現在の完了判定は本ファイル冒頭と `review-tasks.md` の最新監査を参照してください。
