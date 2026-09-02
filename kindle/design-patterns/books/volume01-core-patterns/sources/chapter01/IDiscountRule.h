#ifndef IDISCOUNTRULE_H_INCLUDED
#define IDISCOUNTRULE_H_INCLUDED

#include "Order.h"

class IDiscountRule {
public:
    virtual bool matches(const std::string& memberType,
                         const CampaignContext& context) const = 0;
    virtual int apply(int total) const = 0;
    virtual std::string name() const = 0;
    virtual ~IDiscountRule() = default;
};

#endif  // IDISCOUNTRULE_H_INCLUDED
