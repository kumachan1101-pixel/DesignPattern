#ifndef SMSDELIVERYTRACKER_H_INCLUDED
#define SMSDELIVERYTRACKER_H_INCLUDED

#include "ProductDatabase.h"
#include "INotification.h"

class SMSDeliveryTracker {
    std::map<std::string, DeliveryStatus> statuses;
public:
    void record(const DeliveryResult& result) {
        if (result.status != PENDING ||
            result.requestId.empty()) return;

        statuses[result.requestId] = PENDING;
        std::cout << "[SMS状態] " << result.requestId
                  << ": PENDINGを記録" << std::endl;
    }

    bool complete(
        const std::string& requestId,
        bool delivered) {
        auto it = statuses.find(requestId);

        if (it == statuses.end() || it->second != PENDING) {
            std::cout << "[SMS最終結果エラー] 未知または確定済みの受付ID: "
                 << requestId << std::endl;
            return false;
        }

        DeliveryStatus before = it->second;
        it->second = delivered ? DELIVERED : DELIVERY_FAILED;
        std::cout << "[SMS最終結果] " << requestId << ": "
             << DeliveryStatusText::name(before) << " -> "
             << DeliveryStatusText::name(it->second)
             << std::endl;
        return true;
    }
};

class SMSDeliveryCallback {
    SMSDeliveryTracker& tracker;
public:
    explicit SMSDeliveryCallback(SMSDeliveryTracker& tracker)
            : tracker(tracker) {}

    bool receive(const std::string& requestId, bool delivered) {
        return tracker.complete(requestId, delivered);
    }
};

#endif  // SMSDELIVERYTRACKER_H_INCLUDED
