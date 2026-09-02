#ifndef DISCOUNTS_H_INCLUDED
#define DISCOUNTS_H_INCLUDED

#include "Order.h"
#include "IDiscountRule.h"

class NoDiscount : public IDiscountRule {
public:
    bool matches(const std::string&,
                 const CampaignContext&) const override {
        return true;
    }

    int apply(int total) const override { return total; }
    std::string name() const override { return "割引なし"; }
};

class PremiumDiscount : public IDiscountRule {
public:
    bool matches(const std::string& memberType,
                 const CampaignContext&) const override {
        return memberType == MemberType::Premium;
    }

    int apply(int total) const override {
        return total * 80 / 100;
    }

    std::string name() const override { return "プレミアム割引"; }
};

class SummerSaleAndCampaignDiscount : public IDiscountRule {
public:
    bool matches(const std::string& memberType,
                 const CampaignContext& context) const override {
        return memberType == MemberType::Regular
            && context.isActive(CampaignCode::SummerSale)
            && context.isActive(CampaignCode::RegularCampaign);
    }

    int apply(int total) const override {
        return (total * 90 / 100) * 95 / 100;
    }

    std::string name() const override {
        return "サマーセール+キャンペーン";
    }
};

class SummerSaleDiscount : public IDiscountRule {
public:
    bool matches(const std::string& memberType,
                 const CampaignContext& context) const override {
        return memberType == MemberType::Regular
            && context.isActive(CampaignCode::SummerSale);
    }

    int apply(int total) const override {
        return total * 95 / 100;
    }

    std::string name() const override { return "サマーセール割引"; }
};

class CampaignDiscount : public IDiscountRule {
public:
    bool matches(const std::string& memberType,
                 const CampaignContext& context) const override {
        return memberType == MemberType::Regular
            && context.isActive(CampaignCode::RegularCampaign);
    }

    int apply(int total) const override {
        return total * 90 / 100;
    }

    std::string name() const override { return "キャンペーン割引"; }
};

#endif  // DISCOUNTS_H_INCLUDED
