#ifndef BATCHAPPLICATION_H_INCLUDED
#define BATCHAPPLICATION_H_INCLUDED

#include "ReservationAssembly.h"

// BatchApplication：入力例の実行と結果表示を担う

class BatchApplication {
    ReservationAssembly assembly;

public:
    void run() {
        // ケース1：通常予約フロー (Available → Reserved → Paid)
        std::cout << "--- ケース1: 通常予約 ---\n";

        TicketReservation& seat1 =
            assembly.startReservation("EVT001");
        if (seat1.showAvailability()) {
            std::cout << "予約対象：" << seat1.eventTitle() << "\n";
            seat1.reserve();
            seat1.pay();
        }

        // ケース2：通常キャンセル (Available → Reserved → Available)
        std::cout << "--- ケース2: 通常キャンセル ---\n";

        TicketReservation& seat2 =
            assembly.startReservation("EVT001");
        if (seat2.showAvailability()) {
            seat2.reserve();
            seat2.cancel();
        }

        // ケース3：保留と支払い (Available → Reserved → Held → Paid)
        std::cout << "--- ケース3: 保留と支払い ---\n";

        TicketReservation& seat3 =
            assembly.startReservation("EVT002");
        if (seat3.showAvailability()) {
            std::cout << "予約対象：" << seat3.eventTitle() << "\n";
            seat3.reserve();
            seat3.hold();
            seat3.pay();
        }

        // ケース4：保留期限切れ
        // (Available → Reserved → Held → Available)
        std::cout << "--- ケース4: 保留期限切れ ---\n";

        TicketReservation& seat4 =
            assembly.startReservation("EVT001");
        if (seat4.showAvailability()) {
            seat4.reserve();
            seat4.hold();
            // テストハーネスから「24時間経過」を即時注入する。
            // 本番では利用者でなくタイマー基盤が同じ境界を呼ぶ。
            assembly.expiry().onPaymentDeadlineExpired(seat4);
        }

        // ケース4a：通常の15分決済期限切れ (Reserved → Available)
        std::cout << "--- ケース4a: 通常決済期限切れ ---\n";

        TicketReservation& seat4a =
            assembly.startReservation("EVT001");
        if (seat4a.showAvailability()) {
            seat4a.reserve();
            assembly.expiry().onPaymentDeadlineExpired(seat4a);
        }

        // ケース5：満席確認 → 通常の予約要求で自動待機登録 →
        // 既存予約のキャンセルを起点に自動昇格
        std::cout << "--- ケース5: 満席からの自動昇格 ---\n";

        TicketReservation& waiting =
            assembly.startReservation("EVT003");
        // 50/50を表示。reserve()が満席を判定する
        waiting.showAvailability();
        waiting.reserve(); // 利用者は通常の予約操作だけ。満席なので自動待機登録
        TicketReservation& waitingSecond =
            assembly.startReservation("EVT003");
        waitingSecond.reserve(); // 2番目として同じ待ち行列へ入る

        // 初期50件のうち1件を表す既存予約。利用側はcancel()だけを呼ぶ。
        TicketReservation& occupied =
            assembly.existingReserved("EVT003");
        occupied.cancel(); // 50→49、その直後にwaitingを49→50へ自動昇格
        // 1番目の再取消で、2番目が続けて自動昇格する
        waiting.cancel();
        // 昇格後も同じ予約として操作できることを確認し、席を49へ戻す
        waitingSecond.cancel();

        // ケース5b：待機者がいる状態での期限切れ → 自動昇格
        std::cout << "--- ケース5b: 期限切れからの自動昇格 ---\n";
        // 直前の再取消で49/50。別の予約で満席へ戻してから保留にする
        TicketReservation& held =
            assembly.startReservation("EVT003");
        held.reserve();
        // 席は確保したまま、期限だけ24時間へ延長（席数は動かない）
        held.hold();
        TicketReservation& waiting2 =
            assembly.startReservation("EVT003");
        waiting2.reserve(); // 満席判定により自動待機登録
        // 24時間経過。席が空き、待機者が自動昇格する
        assembly.expiry().onPaymentDeadlineExpired(held);

        // ケース6：無効な操作の拒否 (Available → pay)
        std::cout << "--- ケース6: 無効な操作の拒否 ---\n";

        TicketReservation& seat6 =
            assembly.startReservation("EVT001");
        seat6.pay();

        // ケース7：存在しないイベントIDのエラー
        std::cout << "--- ケース7: 存在しないイベントID ---\n";
        TicketReservation& missing =
            assembly.startReservation("EVT999");
        missing.showAvailability();

    }
};

#endif  // BATCHAPPLICATION_H_INCLUDED
