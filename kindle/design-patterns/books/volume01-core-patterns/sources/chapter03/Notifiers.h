#ifndef NOTIFIERS_H_INCLUDED
#define NOTIFIERS_H_INCLUDED

#include "ProductDatabase.h"
#include "INotification.h"
#include "DeliveryStatusLog.h"

class EmailNotifier : public INotification {
    std::vector<std::string> inbox;

    // 現状コードと同じメール基盤の操作
    bool sendMail(
        const std::string& subject,
        const std::string& body) {
        inbox.push_back(body);
        std::cout << "Email(" << inbox.size()
                  << "件) [" << subject << "] "
                  << body << std::endl;
        return true;
    }
public:
    DeliveryResult send(const StockAlert& a) override {
        std::string body =
            "商品 " + a.productId + "（" + a.productName
            + "） の在庫が閾値以下です。";
        bool ok = sendMail("在庫アラート", body);

        if (ok) {
            return {ACCEPTED, ChannelName::EMAIL, ""};
        }
        return {FAILED, ChannelName::EMAIL, ""};
    }
};

class DashboardUpdater : public INotification {
    int refreshCount;

    // 現状コードと同じ画面更新。戻り値が無い
    void refreshStockWidget(const std::string& productCode,
                            int stock) {
        ++refreshCount;
        std::cout << "Dashboard(" << refreshCount << "件): "
             << productCode
             << " の在庫表示を " << stock << " に更新" << std::endl;
    }
public:
    DashboardUpdater() : refreshCount(0) {}
    DeliveryResult send(const StockAlert& a) override {
        refreshStockWidget(a.productId, a.stock);
        // 呼べたことをもって受付成功とする。この割り切りはここに閉じる
        return {ACCEPTED, ChannelName::DASHBOARD, ""};
    }
};

class ChatNotifier : public INotification {
    std::vector<std::string> posted;

    // 現状コードと同じチャット基盤。投稿IDを返す
    std::string postMessage(
        const std::string& channel,
        const std::string& text) {
        posted.push_back(text);
        std::string postId =
            "POST-" + std::to_string(posted.size());
        std::cout << "Chat(" << posted.size()
                  << "件) #" << channel << "\n"
                  << "  " << text << " -> " << postId
                  << std::endl;
        return postId;
    }
public:
    DeliveryResult send(const StockAlert& a) override {
        std::string text =
            "商品 " + a.productId + "（" + a.productName
            + "） の在庫が閾値以下です。";
        std::string postId =
            postMessage("inventory-alert", text);

        if (postId.empty()) {
            return {FAILED, ChannelName::CHAT, ""};
        }
        return {ACCEPTED, ChannelName::CHAT, ""};
    }
};

class SMSNotifier : public INotification {
    DeliveryStatusLog& statusLog;  // 組み立て側が所有する台帳を借りる
    bool willFail;  // 受付に失敗する状況を再現するための指定
    std::vector<std::string> inbox;  // 受付できた通知だけを蓄積する
    int nextRequestNumber = 1;
public:
    SMSNotifier(DeliveryStatusLog& log, bool fail)
        : statusLog(log), willFail(fail) {}
    DeliveryResult send(const StockAlert& a) override {
        if (willFail) {
            std::cout << "SMS: 受付失敗（後で再送対象）" << std::endl;

            return {FAILED, ChannelName::SMS, ""};
        }

        std::string text = "在庫警告 " + a.productId + " 残"
            + std::to_string(a.stock);
        inbox.push_back(text);
        std::string requestId = "SMS-"
            + std::to_string(nextRequestNumber++);
        std::cout << "SMS(" << inbox.size() << "件受付): " << text
             << " / 受付ID=" << requestId << std::endl;
        DeliveryResult result{
            PENDING, ChannelName::SMS, requestId};
        statusLog.record(result);
        return result;
    }
};

#endif  // NOTIFIERS_H_INCLUDED
