#ifndef RESERVATIONASSEMBLY_H_INCLUDED
#define RESERVATIONASSEMBLY_H_INCLUDED

#include "States.h"
#include "TicketReservation.h"

// ReservationAssembly：共有実体の生成・所有・受け渡しを担う

class ReservationAssembly {
    EventDatabase db;
    ReservationWaitlist waitlist;
    ReservationExpiryScheduler expiryScheduler;
    std::list<TicketReservation> reservations;
public:
    ReservationExpiryScheduler& expiry() {
        return expiryScheduler;
    }

    TicketReservation& startReservation(
            const std::string& eventId) {
        reservations.emplace_back(availableState(), &db,
                                  &waitlist, eventId);
        return reservations.back();
    }

    TicketReservation& existingReserved(
            const std::string& eventId) {
        reservations.emplace_back(reservedState(), &db,
                                  &waitlist, eventId);
        return reservations.back();
    }
};

#endif  // RESERVATIONASSEMBLY_H_INCLUDED
