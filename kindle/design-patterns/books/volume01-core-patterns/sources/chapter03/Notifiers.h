#ifndef NOTIFIERS_H_INCLUDED
#define NOTIFIERS_H_INCLUDED

#include "ProductDatabase.h"
#include "INotification.h"

class EmailNotifier : public INotification {
    vector<string> inbox;

    // 1-4と同じメール基盤の操作
    bool sendMail(const string& subject, const string& body) {
        inbox.push_back(body);
        cout << "Email(" << inbox.size() << "件) [" << subject
             << "] "
             << body << endl;
        return true;
    }
public:
    DeliveryResult send(const StockAlert& a) override {
        string body = a.productName + "(" + a.productId + ") 残"
                    + to_string(a.stock) + " 閾値"
                        + to_string(a.threshold);
        bool ok = sendMail("在庫不足", body);   // 契約→メール基盤へ変換

        return ok ? DeliveryResult{ACCEPTED, "Email", ""}
                  : DeliveryResult{FAILED, "Email", ""};
    }
};

class DashboardUpdater : public INotification {
    int refreshCount;

    // 1-4と同じ画面更新の操作。戻り値が無い
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
        return {ACCEPTED, "Dashboard", ""};
    }
};

class ChatNotifier : public INotification {
    vector<string> posted;

    // 1-4と同じチャット基盤の操作。投稿IDを返す
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
        string text = a.productName + " 残" + to_string(a.stock)
                    + "個。発注を確認してください。";
        string postId = postMessage("inventory-alert", text);

        return postId.empty() ? DeliveryResult{FAILED,
                            "Chat", ""}
               : DeliveryResult{ACCEPTED, "Chat", ""};
    }
};

class SMSNotifier : public INotification {
    bool willFail;  // 受付に失敗する状況を再現するための指定
    vector<string> inbox;  // 受付できた通知だけを蓄積する
    int nextRequestNumber = 1;
public:
    SMSNotifier(bool fail) : willFail(fail) {}
    DeliveryResult send(const StockAlert& a) override {
        if (willFail) {
            cout << "SMS: 受付失敗（後で再送対象）" << endl;

            return {FAILED, "SMS", ""};
        }

        string text = "在庫警告 " + a.productId + " 残"
            + to_string(a.stock);
        inbox.push_back(text);
        string requestId = "SMS-"
            + to_string(nextRequestNumber++);
        cout << "SMS(" << inbox.size() << "件受付): " << text
             << " / 受付ID=" << requestId << endl;
        return {PENDING, "SMS", requestId};
    }
};

#endif  // NOTIFIERS_H_INCLUDED
