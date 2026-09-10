#ifndef INVENTORYAPPLICATION_H_INCLUDED
#define INVENTORYAPPLICATION_H_INCLUDED

#include "Notifiers.h"
#include "DeliveryStatusLog.h"
#include "InventoryManager.h"

class InventoryApplication {
    // 上から生成され、下から破棄される。
    // InventoryManagerより通知先を先に宣言し、借用先の寿命を保証する。
    ProductDatabase productDatabase;
    DeliveryStatusLog deliveryStatusLog;
    EmailNotifier email;
    DashboardUpdater dashboard;
    ChatNotifier chat;
    SMSNotifier sms;
    InventoryManager manager;
    SMSDeliveryCallback smsCallback;

    void registerNotifications() {
        bool registered = manager.attach(&email)
                       && manager.attach(&dashboard)
                       && manager.attach(&chat)
                       && manager.attach(&sms);
        if (!registered) {
            throw std::logic_error("通知先の初期登録に失敗しました");
        }
    }

public:
    explicit InventoryApplication(bool smsWillFail = false)
        : sms(deliveryStatusLog, smsWillFail),
          manager(productDatabase),
          smsCallback(deliveryStatusLog) {
        registerNotifications();
    }

    InventoryManager& inventory() { return manager; }
    SMSDeliveryCallback& smsDelivery() { return smsCallback; }
};

#endif  // INVENTORYAPPLICATION_H_INCLUDED
