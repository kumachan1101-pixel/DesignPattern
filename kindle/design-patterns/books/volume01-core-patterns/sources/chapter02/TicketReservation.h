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

    // 待機中の予約が先に破棄された場合も、借用ポインタを残さない
    void remove(TicketReservation* reservation) {
        for (auto it = queues.begin(); it != queues.end(); ) {
            auto& queue = it->second;
            auto newEnd = std::remove(
                queue.begin(), queue.end(), reservation);
            queue.erase(newEnd, queue.end());
            if (queue.empty()) {
                it = queues.erase(it);
            } else {
                ++it;
            }
        }
    }
};

class TicketReservation {
private:
    IReservationState* state;
    EventDatabase* db;           // 在庫の保存データ（境界）
    ReservationWaitlist* waitlist;
    std::string eventId;

    // キャンセル待ち昇格は外部公開せず、システム連鎖からだけ呼ぶ
    void promoteBySystem() {
        state->promoteBySystem(this);
    }
public:
    TicketReservation(IReservationState* initialState,
                      EventDatabase* db,
                      ReservationWaitlist* waitlist,
                      const std::string& eventId)
        : state(initialState), db(db), waitlist(waitlist),
          eventId(eventId) {}

    // 待機中に予約オブジェクトが破棄されても参照を残さない
    ~TicketReservation() {
        waitlist->remove(this);
    }

    // キューがthisのアドレスを借用するため、実体の複製・移動を禁止する
    TicketReservation(const TicketReservation&) = delete;
    TicketReservation& operator=(
        const TicketReservation&) = delete;
    TicketReservation(TicketReservation&&) = delete;
    TicketReservation& operator=(TicketReservation&&) = delete;

    // 状態遷移時に、共有状態オブジェクトへの借用ポインタを差し替える。
    // 状態は関数ローカルstaticが所有するため、ここではdeleteしない。
    void setState(IReservationState* nextState) {
        state = nextState;
    }

    // 状態遷移の副作用：在庫の増減
    void reserveSeat() { db->reserveSeat(eventId); }
    void cancelSeat()  { db->cancelSeat(eventId); }
    bool hasCapacity() const {
        return db->hasCapacity(eventId);
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
        int available = info.capacity - info.reserved;
        std::cout << "[席数確認] " << eventId << " "
                  << info.reserved << "/" << info.capacity
                  << "（空席" << available << "）";
        if (available == 0) std::cout << "（満席）";
        std::cout << std::endl;

        return true;
    }

public:
    void run() {
        // ケース1：通常予約フロー (Available → Reserved → Paid)
        std::cout << "--- ケース1: 通常予約 ---\n";

        if (showAvailability("EVT001")) {
            EventInfo i1 = db.get("EVT001");
            std::cout << "予約対象：" << i1.title << "\n";
            TicketReservation seat1(availableState(), &db,
                                    &waitlist, "EVT001");
            seat1.reserve();
            seat1.pay();
        }

        // ケース2：通常キャンセル (Available → Reserved → Available)
        std::cout << "--- ケース2: 通常キャンセル ---\n";

        if (showAvailability("EVT001")) {
            TicketReservation seat2(availableState(), &db,
                                    &waitlist, "EVT001");
            seat2.reserve();
            seat2.cancel();
        }

        // ケース3：保留と支払い (Available → Reserved → Held → Paid)
        std::cout << "--- ケース3: 保留と支払い ---\n";

        if (showAvailability("EVT002")) {
            std::cout << "予約対象："
                      << db.get("EVT002").title << "\n";
            TicketReservation seat3(availableState(), &db,
                                    &waitlist, "EVT002");
            seat3.reserve();
            seat3.hold();
            seat3.pay();
        }

        // ケース4：保留期限切れ
        // (Available → Reserved → Held → Available)
        std::cout << "--- ケース4: 保留期限切れ ---\n";

        if (showAvailability("EVT001")) {
            TicketReservation seat4(availableState(), &db,
                                    &waitlist, "EVT001");
            seat4.reserve();
            seat4.hold();
            // テストハーネスから「24時間経過」を即時注入する。
            // 本番では利用者でなくタイマー基盤が同じ境界を呼ぶ。
            expiryScheduler.onPaymentDeadlineExpired(seat4);
        }

        // ケース4a：通常の15分決済期限切れ (Reserved → Available)
        std::cout << "--- ケース4a: 通常決済期限切れ ---\n";

        if (showAvailability("EVT001")) {
            TicketReservation seat4a(availableState(), &db,
                                     &waitlist, "EVT001");
            seat4a.reserve();
            expiryScheduler.onPaymentDeadlineExpired(seat4a);
        }

        // ケース5：満席確認 → 通常の予約要求で自動待機登録 →
        // 既存予約のキャンセルを起点に自動昇格
        std::cout << "--- ケース5: 満席からの自動昇格 ---\n";
        // 50/50を表示。reserve()が満席を判定する
        showAvailability("EVT003");

        TicketReservation waiting(availableState(), &db,
                                  &waitlist, "EVT003");
        waiting.reserve(); // 利用者は通常の予約操作だけ。満席なので自動待機登録

        // 初期50件のうち1件を表す既存予約。利用側はcancel()だけを呼ぶ。
        TicketReservation occupied(reservedState(), &db,
                                   &waitlist, "EVT003");
        occupied.cancel(); // 50→49、その直後にwaitingを49→50へ自動昇格
        // 昇格後も同じ予約として操作でき、再取消で席を戻せる
        waiting.cancel();

        // ケース5b：待機者がいる状態での期限切れ → 自動昇格
        std::cout << "--- ケース5b: 期限切れからの自動昇格 ---\n";
        // 直前の再取消で49/50。別の予約で満席へ戻してから保留にする
        TicketReservation held(availableState(), &db,
                               &waitlist, "EVT003");
        held.reserve();
        // 席は確保したまま、期限だけ24時間へ延長（席数は動かない）
        held.hold();
        TicketReservation waiting2(availableState(), &db,
                                   &waitlist, "EVT003");
        waiting2.reserve(); // 満席判定により自動待機登録
        // 24時間経過。席が空き、待機者が自動昇格する
        expiryScheduler.onPaymentDeadlineExpired(held);

        // ケース6：無効な操作の拒否 (Available → pay)
        std::cout << "--- ケース6: 無効な操作の拒否 ---\n";

        if (validateExists("EVT001")) {
            TicketReservation seat6(availableState(), &db,
                                    &waitlist, "EVT001");
            seat6.pay();
        }

        // ケース7：存在しないイベントIDのエラー
        std::cout << "--- ケース7: 存在しないイベントID ---\n";
        validateExists("EVT999");

    }
};

#endif  // TICKETRESERVATION_H_INCLUDED
