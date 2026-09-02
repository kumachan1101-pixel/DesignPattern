#ifndef INOTIFICATION_H_INCLUDED
#define INOTIFICATION_H_INCLUDED

#include "ProductDatabase.h"

class INotification {
public:
    virtual ~INotification() = default;
    // 在庫警告を受け取り、手段別に表現して受付結果を1つ返す
    virtual DeliveryResult send(const StockAlert& alert) = 0;
};

#endif  // INOTIFICATION_H_INCLUDED
