#ifndef STATES_H_INCLUDED
#define STATES_H_INCLUDED

#include "EventDatabase.h"
#include "IReservationState.h"

class AvailableState : public IReservationState {
public:
    void reserve(TicketReservation* reservation) override;
};

class ReservedState : public IReservationState {
public:
    void pay(TicketReservation* reservation) override;

    void cancel(TicketReservation* reservation) override;

    void hold(TicketReservation* reservation) override;

    void expire(TicketReservation* reservation) override;

    void paymentFailed(TicketReservation* reservation) override;
};

class PaidState : public IReservationState {};

// Waitlisted（キャンセル待ち）：システムからの昇格だけを受ける

class WaitlistedState : public IReservationState {
public:
    void promoteBySystem(TicketReservation* reservation) override;
};

class HeldState : public IReservationState {
public:
    void pay(TicketReservation* reservation) override;

    void cancel(TicketReservation* reservation) override;

    void expire(TicketReservation* reservation) override;

    void paymentFailed(TicketReservation* reservation) override;
};

// 状態オブジェクト取得関数。関数ローカルstaticが所有する。
IReservationState* availableState();

IReservationState* reservedState();

IReservationState* paidState();

IReservationState* waitlistedState();

IReservationState* heldState();

#endif  // STATES_H_INCLUDED
