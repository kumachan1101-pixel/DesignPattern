#!/usr/bin/env python3
"""再発防止チェックが、実際に起きた違反を検出できるか確認する。

2026-08-12のロジック監査（logic-audit-20260812.md）で見つかった152件のうち、
機械判定へ落とせた4系統について「わざと壊した本文を検出できるか」を見る。
validate_book.py 本体は「現在の本文が通るか」しか見ないため、チェックが
空振りしていても気づけない。この負のテストで、検査が生きていることを担保する。

    python3 script/test_recurrence_checks.py

対応する監査ID：
  LOGIC-001  受入エビデンスが実行していないシナリオを参照する
  LOGIC-003  フェーズ6の契約が7-1完成コードと食い違う
  LOGIC-007  変更ID一覧の列名が「現行」なのに追加要求IDが並ぶ
  LOGIC-008  参照先のない「フェーズ6のステップN」
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path("script").resolve()))
import validate_book as V

OUT = Path("output")
cases = []

# 1) LOGIC-001: エビデンスが実行結果にないシナリオを参照する
t = (OUT/"chapter11.md").read_text(encoding="utf-8")
broken = t.replace("A5で未登録IDを拒否し成果物なし", "A9で未登録IDを拒否し成果物なし")
cases.append(("LOGIC-001 エビデンス参照", V.check_evidence_scenario_reference, broken))

# 2) LOGIC-003: フェーズ6契約に7-1へ無いメソッドがある
t = (OUT/"chapter09_2.md").read_text(encoding="utf-8")
broken = t.replace(
    '    virtual ITicketPhase* sendBack() { return reject("差し戻し"); }\nprotected:',
    '    virtual ITicketPhase* sendBack() { return reject("差し戻し"); }\n'
    '    virtual ITicketPhase* archive()  { return reject("封棚"); }\nprotected:', 1)
cases.append(("LOGIC-003 契約不一致", V.check_phase6_phase7_contract_match, broken))

# 3) LOGIC-007: 列名が「現行」なのに追加要求IDが入る
t = (OUT/"chapter10.md").read_text(encoding="utf-8")
broken = t.replace("| 変更ID | 変更依頼の要点 | 関係する要求ID（追加は変更後ID） |",
                   "| 変更ID | 変更依頼の要点 | 対象の現行要求ID |", 1)
cases.append(("LOGIC-007 要求ID列", V.check_change_id_requirement_scope, broken))

# 4) LOGIC-008: 参照先のないステップN
t = (OUT/"chapter07.md").read_text(encoding="utf-8")
broken = t.replace("フェーズ6で確定した通知分離構造を実装し",
                   "フェーズ6のステップ3を実装し", 1)
cases.append(("LOGIC-008 ステップ参照", V.check_step_reference_target, broken))

print("再発防止チェックの負のテスト（わざと壊した本文を検出できるか）\n")
ng = 0
for name, fn, txt in cases:
    found = fn(txt, Path("dummy.md"))
    mark = "検出OK" if found else "見逃し"
    if not found:
        ng += 1
    print(f"[{mark}] {name}: {len(found)}件")
    for i in found[:1]:
        print(f"         → {i.message[:90]}")
print()
if ng:
    print(f"FAILED: {ng} 件のチェックが違反を見逃しました")
else:
    print(f"OK: {len(cases)} 件のチェックがすべて違反を検出しました")
sys.exit(1 if ng else 0)
