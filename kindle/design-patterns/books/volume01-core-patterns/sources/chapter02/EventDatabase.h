#ifndef EVENTDATABASE_H_INCLUDED
#define EVENTDATABASE_H_INCLUDED

#include <iostream>
#include <string>
#include <map>
#include <vector>
#include <deque>
#include <stdexcept>

class TicketReservation;
class IReservationState;

struct EventInfo {
    std::string title;   // イベント名
    int capacity;        // 定員
    int reserved;        // 現在の予約数
};

class EventDatabase {
private:
    std::map<std::string, EventInfo> records;
public:
    EventDatabase() {
        records["EVT001"] = {"春の音楽祭",  100,  20};
        records["EVT002"] = {"夏のフェス",  500, 499};
        records["EVT003"] = {"秋の映画会",   50,  50};  // 満席
    }

    bool exists(const std::string& id) const {
        return records.count(id) > 0;
    }

    EventInfo get(const std::string& id) const {
        return records.at(id);
    }

    bool hasCapacity(const std::string& id) const {
        const auto& e = records.at(id);

        return e.reserved < e.capacity;
    }

    void reserveSeat(const std::string& id) {
        auto& event = records.at(id);

        if (event.reserved >= event.capacity) {
            throw std::runtime_error("満席のイベントは予約できません");
        }

        int before = event.reserved;
        ++event.reserved;
        std::cout << "[予約数] " << id << " "
                  << before << "/" << event.capacity
                  << " -> " << event.reserved << "/" << event.capacity;
        if (event.reserved == event.capacity) std::cout << "（満席）";
        std::cout << std::endl;
    }

    void cancelSeat(const std::string& id) {
        auto& event = records.at(id);
        int before = event.reserved;

        if (event.reserved > 0) --event.reserved;
        std::cout << "[予約数] " << id << " "
                  << before << "/" << event.capacity
                  << " -> " << event.reserved << "/" << event.capacity
                  << std::endl;
    }

    void save(const std::string& id, const EventInfo& info) {
        records[id] = info;             // 実行中のイベント表へ追加
    }
};

struct ReservationRecord {
    std::string eventId;
    std::string eventTitle;
    std::string action;   // "予約", "決済", "キャンセル"
};

// 予約履歴を管理するクラス

class ReservationHistory {
    std::vector<ReservationRecord> records;
public:
    void add(const std::string& eventId, const std::string& eventTitle,
             const std::string& action) {
        records.push_back({eventId, eventTitle, action});
    }

    void printAll() const {
        for (const auto& r : records) {
            std::cout << "[" << r.eventId << "] " << r.eventTitle
                      << " -> " << r.action << std::endl;
        }
    }

    int size() const { return (int)records.size(); }
};

// 予約クラス：状態を保持し操作を委譲するだけ

// Reserved（予約済み）：支払い、取消、保留、期限切れを処理する

// Paid（支払い済み）：完了状態のため、すべて既定の拒否を使う

// Held（一時保留）：支払い、取消、期限切れ、決済失敗を処理する

// タイマー基盤から期限切れイベントを予約へ渡す境界。
// 利用者や運用者がexpire()を手動実行する構造にはしない。

#endif  // EVENTDATABASE_H_INCLUDED
