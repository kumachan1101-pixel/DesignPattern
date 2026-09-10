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
    bool showAvailability() const {
        if (!db->exists(eventId)) {
            std::cout << "エラー：イベントID " << eventId
                      << " は存在しません\n";
            return false;
        }

        EventInfo info = db->get(eventId);
        int available = info.capacity - info.reserved;
        std::cout << "[席数確認] " << eventId << " "
                  << info.reserved << "/" << info.capacity
                  << "（空席" << available << "）";
        if (available == 0) std::cout << "（満席）";
        std::cout << std::endl;

        return true;
    }
    std::string eventTitle() const {
        return db->get(eventId).title;
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

#endif  // TICKETRESERVATION_H_INCLUDED
