#ifndef IRESERVATIONSTATE_H_INCLUDED
#define IRESERVATIONSTATE_H_INCLUDED

#include "EventDatabase.h"

class IReservationState {
public:
    // 引数は操作対象の予約コンテキスト（TicketReservation*）。
// 既定実装では使わないため仮引数名を省略し、派生側では reservation と名付ける。

    virtual void reserve(TicketReservation*) {
        std::cout << "現在予約できません\n";
    }

    virtual void pay(TicketReservation*) {
        std::cout << "支払いに適した状態ではありません\n";
    }

    virtual void cancel(TicketReservation*) {
        std::cout << "キャンセルできません\n";
    }

    virtual void promoteBySystem(TicketReservation*) {
        std::cout << "システム昇格の対象ではありません\n";
    }

    virtual void hold(TicketReservation*) {
        std::cout << "保留できません\n";
    }

    virtual void expire(TicketReservation*) {
        std::cout << "期限切れ処理は行えません\n";
    }

    virtual void paymentFailed(TicketReservation*) {
        std::cout << "決済失敗を扱える状態ではありません\n";
    }

    virtual ~IReservationState() = default;
};

IReservationState* availableState();
IReservationState* reservedState();
IReservationState* paidState();
IReservationState* waitlistedState();
IReservationState* heldState();

// Available（予約可能）：空席なら予約、満席なら自動待機登録する

#endif  // IRESERVATIONSTATE_H_INCLUDED
