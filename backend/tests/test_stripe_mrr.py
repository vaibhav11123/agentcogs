from app.services.stripe_mrr import subscription_monthly_usd


def test_normalises_a_yearly_price_to_a_month():
    sub = {
        "items": {
            "data": [
                {
                    "quantity": 1,
                    "price": {
                        "unit_amount": 120000,
                        "recurring": {"interval": "year", "interval_count": 1, "usage_type": "licensed"},
                    },
                }
            ]
        }
    }
    assert subscription_monthly_usd(sub) == 100


def test_skips_metered_prices_and_applies_percent_off():
    sub = {
        "items": {
            "data": [
                {
                    "quantity": 2,
                    "price": {
                        "unit_amount": 5000,
                        "recurring": {"interval": "month", "interval_count": 1, "usage_type": "licensed"},
                    },
                },
                {
                    "quantity": 1,
                    "price": {
                        "unit_amount": 1,
                        "recurring": {"interval": "month", "interval_count": 1, "usage_type": "metered"},
                    },
                },
            ]
        },
        "discount": {"coupon": {"percent_off": 50, "valid": True}},
    }
    assert subscription_monthly_usd(sub) == 50
