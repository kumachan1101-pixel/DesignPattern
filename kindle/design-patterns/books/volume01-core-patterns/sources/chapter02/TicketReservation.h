#ifndef TICKETRESERVATION_H_INCLUDED
#define TICKETRESERVATION_H_INCLUDED

#include "EventDatabase.h"
#include "IReservationState.h"

class TicketReservation;

class ReservationWaitlist {
    std::map<std::string,
             std::deque<TicketReservation*>> queues;
public:
    void enqueue(const std::string& eventId,
                 TicketReservation* reservation) {
        queues[eventId].push_back(reservation);
        std::cout << "[待ち行列] " << eventId
                  << " 待機数=" << queues[eventId].size()
                  << std::endl;
    }

    TicketReservation* popNext(const std::string& eventId) {
        auto& queue = queues[eventId];

        if (queue.empty()) return nullptr;

        TicketReservation* next = queue.front();
        queue.pop_front();
        std::cout << "[待ち行列] " << eventId
                  << " 待機数=" << queue.size()
                  << std::endl;
        return next;
    }
};

class TicketReservation;

// 状態ごとの共通操作と、許可されない操作の既定処理を持つ基底クラス

class TicketReservation {
private:
    IReservationState* state;
    EventDatabase* db;           // 在庫の保存データ（境界）
    ReservationHistory* history; // 予約履歴
    ReservationWaitlist* waitlist;
    std::string eventId;
    std::string title;

    // キャンセル待ち昇格は外部公開せず、システム連鎖からだけ呼ぶ
    void promoteBySystem() {
        state->promoteBySystem(this);
    }
public:
    TicketReservation(IReservationState* initialState,
                      EventDatabase* db,
                      ReservationHistory* history,
                      ReservationWaitlist* waitlist,
                      const std::string& eventId,
                      const std::string& title)
        : state(initialState), db(db), history(history),
          waitlist(waitlist),
          eventId(eventId), title(title) {}

    // 状態遷移時に、共有状態オブジェクトへの借用ポインタを差し替える。
    // 状態は関数ローカルstaticが所有するため、ここではdeleteしない。
    void setState(IReservationState* nextState) {
        state = nextState;
    }

    // 状態遷移の副作用：在庫の増減と履歴の記録
    void reserveSeat() { db->reserveSeat(eventId); }
    void cancelSeat()  { db->cancelSeat(eventId); }
    bool hasCapacity() const {
        return db->hasCapacity(eventId);
    }
    void record(const std::string& action) {
        history->add(eventId, title, action);
    }

    void joinWaitlist() {
        waitlist->enqueue(eventId, this);
    }

    void promoteNextWaitlisted() {
        TicketReservation* next = waitlist->popNext(eventId);

        if (next != nullptr) next->promoteBySystem();
    }

    // 操作を現在の状態に委譲するだけ
    void reserve()         { state->reserve(this); }
    void pay()             { state->pay(this); }
    void cancel()          { state->cancel(this); }
    void hold()            { state->hold(this); }
    void expire()          { state->expire(this); }
    void paymentFailed()   { state->paymentFailed(this); }
};

class ReservationExpiryScheduler {
public:
    void onPaymentDeadlineExpired(
            TicketReservation& reservation) {
        reservation.expire();
    }
};

// BatchApplication：依存の組み立てを担う入口

class BatchApplication {
    EventDatabase db;
    ReservationHistory history;
    ReservationWaitlist waitlist;
    ReservationExpiryScheduler expiryScheduler;

    bool validateExists(const std::string& eventId) {
        if (!db.exists(eventId)) {
            std::cout << "エラー：イベントID " << eventId
                      << " は存在しません\n";
            return false;
        }

        return true;
    }

    // 予約前に現在の席数を表示する。満席判定と待機登録はreserve()側が行う。
    bool showAvailability(const std::string& eventId) {
        if (!validateExists(eventId)) return false;

        EventInfo info = db.get(eventId);
        std::cout << "[席数確認] " << eventId << " "
                  << info.reserved << "/" << info.capacity;
        if (info.reserved == info.capacity) std::cout << "（満席）";
        std::cout << std::endl;

        return true;
    }

public:
    void run() {
        // シナリオ1：通常予約フロー (Available → Reserved → Paid)
        std::cout << "--- 行1: 通常予約 ---\n";

        if (showAvailability("EVT001")) {
            EventInfo i1 = db.get("EVT001");
            std::cout << "予約対象：" << i1.title << "\n";
            TicketReservation seat1(availableState(), &db,
                                    &history, &waitlist,
                                    "EVT001", i1.title);
            seat1.reserve();
            seat1.pay();
        }

        // シナリオ2：通常キャンセル (Available → Reserved → Available)
        std::cout << "--- 行2: 通常キャンセル ---\n";

        if (showAvailability("EVT001")) {
            EventInfo i2 = db.get("EVT001");
            TicketReservation seat2(availableState(), &db,
                                    &history, &waitlist,
                                    "EVT001", i2.title);
            seat2.reserve();
            seat2.cancel();
        }

        // シナリオ3：保留と支払い (Available → Reserved → Held → Paid)
        std::cout << "--- 行3: 保留と支払い ---\n";

        if (showAvailability("EVT002")) {
            EventInfo i3 = db.get("EVT002");
            std::cout << "予約対象：" << i3.title << "\n";
            TicketReservation seat3(availableState(), &db,
                                    &history, &waitlist,
                                    "EVT002", i3.title);
            seat3.reserve();
            seat3.hold();
            seat3.pay();
        }

        // シナリオ4：保留期限切れ
        // (Available → Reserved → Held → Available)
        std::cout << "--- 行4: 保留期限切れ ---\n";

        if (showAvailability("EVT001")) {
            EventInfo i4 = db.get("EVT001");
            TicketReservation seat4(availableState(), &db,
                                    &history, &waitlist,
                                    "EVT001", i4.title);
            seat4.reserve();
            seat4.hold();
            // テストハーネスから「24時間経過」を即時注入する。
            // 本番では利用者でなくタイマー基盤が同じ境界を呼ぶ。
            expiryScheduler.onPaymentDeadlineExpired(seat4);
        }

        // シナリオ4a：通常の15分決済期限切れ (Reserved → Available)
        std::cout << "--- 行4a: 通常決済期限切れ ---\n";

        if (showAvailability("EVT001")) {
            EventInfo i4a = db.get("EVT001");
            TicketReservation seat4a(availableState(), &db,
                                     &history, &waitlist,
                                     "EVT001", i4a.title);
            seat4a.reserve();
            expiryScheduler.onPaymentDeadlineExpired(seat4a);
        }

        // シナリオ5：満席確認 → 通常の予約要求で自動待機登録 →
        // 既存予約のキャンセルを起点に自動昇格
        std::cout << "--- 行5: 満席からの自動昇格 ---\n";
        EventInfo full = db.get("EVT003");
        // 50/50を表示。reserve()が満席を判定する
        showAvailability("EVT003");

        TicketReservation waiting(availableState(), &db,
                                  &history, &waitlist,
                                  "EVT003", full.title);
        waiting.reserve(); // 利用者は通常の予約操作だけ。満席なので自動待機登録

        // 初期50件のうち1件を表す既存予約。利用側はcancel()だけを呼ぶ。
        TicketReservation occupied(reservedState(), &db,
                                   &history, &waitlist,
                                   "EVT003", full.title);
        occupied.cancel(); // 50→49、その直後にwaitingを49→50へ自動昇格
        waiting.pay();

        // シナリオ5b：待機者がいる状態での期限切れ → 自動昇格
        std::cout << "--- 行5b: 期限切れからの自動昇格 ---\n";
        EventInfo f2 = db.get("EVT003");
        // 50/50の満席状態。1件を保留にしてから待機者を登録する
        TicketReservation held(reservedState(), &db,
                               &history, &waitlist,
                               "EVT003", f2.title);
        // 席は確保したまま、期限だけ24時間へ延長（席数は動かない）
        held.hold();
        TicketReservation waiting2(availableState(), &db,
                                   &history, &waitlist,
                                   "EVT003", f2.title);
        waiting2.reserve(); // 満席判定により自動待機登録
        // 24時間経過。席が空き、待機者が自動昇格する
        expiryScheduler.onPaymentDeadlineExpired(held);

        // シナリオ6：無効な操作の拒否 (Available → pay)
        std::cout << "--- 行6: 無効な操作の拒否 ---\n";

        if (validateExists("EVT001")) {
            EventInfo i6 = db.get("EVT001");
            TicketReservation seat6(availableState(), &db,
                                    &history, &waitlist,
                                    "EVT001", i6.title);
            seat6.pay();
        }

        // シナリオ7：存在しないイベントIDのエラー
        std::cout << "--- 行7: 存在しないイベントID ---\n";
        validateExists("EVT999");

// シナリオ8：決済失敗 (Available → Reserved → 決済失敗、Reservedのまま)

        std::cout << "--- 行8: 決済失敗（再試行可能） ---\n";

        if (showAvailability("EVT001")) {
            EventInfo i8 = db.get("EVT001");
            TicketReservation seat8(availableState(), &db,
                                    &history, &waitlist,
                                    "EVT001", i8.title);
            seat8.reserve();
            seat8.paymentFailed();
        }

        std::cout << "\n--- 行9: 予約履歴 ---\n";
        history.printAll();
    }
};

#endif  // TICKETRESERVATION_H_INCLUDED
