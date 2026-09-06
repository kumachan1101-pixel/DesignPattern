#ifndef NOTIFIERS_H_INCLUDED
#define NOTIFIERS_H_INCLUDED

#include "ProductDatabase.h"
#include "INotification.h"
#include "DeliveryStatusLog.h"

class EmailNotifier : public INotification {
    vector<string> inbox;

    // 現状コードと同じメール基盤の操作
    bool sendMail(const string& subject, const string& body) {
        inbox.push_back(body);
        cout << "Email(" << inbox.size() << "件) [" << subject
             << "] "
             << body << endl;
        return true;
    }
public:
    DeliveryResult send(const StockAlert& a) override {
        string body = "商品 " + a.productId + "（" + a.productName
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
    void refreshStockWidget(const string& productCode,
                            int stock) {
        ++refreshCount;
        cout << "Dashboard(" << refreshCount << "件): "
             << productCode
             << " の在庫表示を " << stock << " に更新" << endl;
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
    vector<string> posted;

    // 現状コードと同じチャット基盤。投稿IDを返す
    string postMessage(const string& channel,
                       const string& text) {
        posted.push_back(text);
        string postId = "POST-" + to_string(posted.size());
        cout << "Chat(" << posted.size() << "件) #" << channel
             << "\n"
             << "  " << text << " -> " << postId << endl;
        return postId;
    }
public:
    DeliveryResult send(const StockAlert& a) override {
        string text = "商品 " + a.productId + "（" + a.productName
                    + "） の在庫が閾値以下です。";
        string postId = postMessage("inventory-alert", text);

        if (postId.empty()) {
            return {FAILED, ChannelName::CHAT, ""};
        }
        return {ACCEPTED, ChannelName::CHAT, ""};
    }
};

class SMSNotifier : public INotification {
    DeliveryStatusLog& statusLog;  // 組み立て側が所有する台帳を借りる
    bool willFail;  // 受付に失敗する状況を再現するための指定
    vector<string> inbox;  // 受付できた通知だけを蓄積する
    int nextRequestNumber = 1;
public:
    SMSNotifier(DeliveryStatusLog& log, bool fail)
        : statusLog(log), willFail(fail) {}
    DeliveryResult send(const StockAlert& a) override {
        if (willFail) {
            cout << "SMS: 受付失敗（後で再送対象）" << endl;

            return {FAILED, ChannelName::SMS, ""};
        }

        string text = "在庫警告 " + a.productId + " 残"
            + to_string(a.stock);
        inbox.push_back(text);
        string requestId = "SMS-"
            + to_string(nextRequestNumber++);
        cout << "SMS(" << inbox.size() << "件受付): " << text
             << " / 受付ID=" << requestId << endl;
        DeliveryResult result{
            PENDING, ChannelName::SMS, requestId};
        statusLog.record(result);
        return result;
    }
};

#endif  // NOTIFIERS_H_INCLUDED
