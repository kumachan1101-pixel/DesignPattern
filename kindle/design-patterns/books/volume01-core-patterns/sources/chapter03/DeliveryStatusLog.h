#ifndef DELIVERYSTATUSLOG_H_INCLUDED
#define DELIVERYSTATUSLOG_H_INCLUDED

#include "ProductDatabase.h"
#include "INotification.h"

class DeliveryStatusLog {
    std::map<std::string, DeliveryStatus> statuses;

    static std::string statusName(DeliveryStatus status) {
        if (status == PENDING) return "PENDING";
        if (status == DELIVERED) return "DELIVERED";
        if (status == DELIVERY_FAILED) return "DELIVERY_FAILED";

        return "対象外";
    }
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
             << statusName(before) << " -> "
             << statusName(it->second)
             << std::endl;
        return true;
    }
};

class SMSDeliveryCallback {
    DeliveryStatusLog& statusLog;
public:
    explicit SMSDeliveryCallback(DeliveryStatusLog& log)
            : statusLog(log) {}

    bool receive(const std::string& requestId, bool delivered) {
        return statusLog.complete(requestId, delivered);
    }
};

#endif  // DELIVERYSTATUSLOG_H_INCLUDED
