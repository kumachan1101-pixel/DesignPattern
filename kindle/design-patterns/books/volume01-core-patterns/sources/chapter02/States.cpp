#include "States.h"
#include "TicketReservation.h"

void AvailableState::reserve(TicketReservation* reservation) {
        if (!reservation->hasCapacity()) {
            reservation->joinWaitlist();
            std::cout << "満席のためキャンセル待ちに登録しました\n";
            reservation->setState(waitlistedState());
            return;
        }

        reservation->reserveSeat();
        std::cout << "予約完了しました\n";
        reservation->setState(reservedState());
    }

void ReservedState::pay(TicketReservation* reservation) {
        std::cout << "支払い完了しました\n";
        reservation->setState(paidState());
    }

void ReservedState::cancel(TicketReservation* reservation) {
        reservation->cancelSeat();
        std::cout << "予約をキャンセルしました\n";
        reservation->setState(availableState());
        reservation->promoteNextWaitlisted();
    }

void ReservedState::hold(TicketReservation* reservation) {
        std::cout << "保留にしました\n";
        reservation->setState(heldState());
    }

void ReservedState::expire(TicketReservation* reservation) {
        reservation->cancelSeat();
        std::cout << "通常の決済期限が切れました\n";
        reservation->setState(availableState());
        reservation->promoteNextWaitlisted();
    }

void ReservedState::paymentFailed(TicketReservation*) {
        std::cout << "決済に失敗しました。予約済みのまま再試行できます\n";
    }

void WaitlistedState::promoteBySystem(TicketReservation* reservation) {
        reservation->reserveSeat();
        std::cout << "空席発生を検知し、予約へ自動昇格しました\n";
        reservation->setState(reservedState());
    }

void HeldState::pay(TicketReservation* reservation) {
        std::cout << "保留から支払い完了しました\n";
        reservation->setState(paidState());
    }

void HeldState::cancel(TicketReservation* reservation) {
        reservation->cancelSeat();
        std::cout << "保留からキャンセルしました\n";
        reservation->setState(availableState());
        reservation->promoteNextWaitlisted();
    }

void HeldState::expire(TicketReservation* reservation) {
        reservation->cancelSeat();
        std::cout << "保留期限が切れました\n";
        reservation->setState(availableState());
        reservation->promoteNextWaitlisted();
    }

void HeldState::paymentFailed(TicketReservation*) {
        std::cout << "決済に失敗しました。保留中のまま再試行できます\n";
    }

IReservationState* availableState() {
    static AvailableState state;

    return &state;
}
IReservationState* reservedState() {
    static ReservedState state;

    return &state;
}
IReservationState* paidState() {
    static PaidState state;

    return &state;
}
IReservationState* waitlistedState() {
    static WaitlistedState state;

    return &state;
}
IReservationState* heldState() {
    static HeldState state;

    return &state;
}
