#!/usr/bin/env python3
"""
Demo script to show extract_open_orders.py in action with mock data.

This script demonstrates the utility without requiring actual Kraken API credentials.
"""

from extract_open_orders import extract_trailing_stop_orders, output_as_csv


class MockKrakenAPI:
    """Mock Kraken API that returns sample open orders."""
    
    def query_open_orders(self):
        """Return mock open orders data matching Kraken's actual response format."""
        return {
            "open": {
                "OZAFUQ-6FB7W-GR63OS": {
                    "refid": None,
                    "userref": 0,
                    "status": "open",
                    "opentm": 1760578655.936616,
                    "starttm": 0,
                    "expiretm": 0,
                    "descr": {
                        "pair": "XXBTZUSDT",
                        "aclass": "forex",
                        "type": "buy",
                        "ordertype": "trailing-stop",
                        "price": "+15.0000%",
                        "price2": "0",
                        "leverage": "none",
                        "order": "buy 0.00006000 XXBTZUSDT @ trailing stop +15.0000%",
                        "close": ""
                    },
                    "vol": "0.00006000",
                    "vol_exec": "0.00000000",
                    "cost": "0.00000",
                    "fee": "0.00000",
                    "price": "0.00000",
                    "stopprice": "127605.90000",
                    "limitprice": "110961.70000",
                    "misc": "",
                    "oflags": "fciq",
                    "trigger": "index"
                },
                "ORWBHN-LMPRM-TG4RWJ": {
                    "refid": None,
                    "userref": 0,
                    "status": "open",
                    "opentm": 1760578459.280463,
                    "starttm": 0,
                    "expiretm": 0,
                    "descr": {
                        "pair": "XXBTZUSDT",
                        "aclass": "forex",
                        "type": "sell",
                        "ordertype": "trailing-stop",
                        "price": "+10.0000%",
                        "price2": "0",
                        "leverage": "none",
                        "order": "sell 0.00005000 XXBTZUSDT @ trailing stop +10.0000%",
                        "close": ""
                    },
                    "vol": "0.00005000",
                    "vol_exec": "0.00000000",
                    "cost": "0.00000",
                    "fee": "0.00000",
                    "price": "0.00000",
                    "stopprice": "99874.10000",
                    "limitprice": "110971.20000",
                    "misc": "",
                    "oflags": "fcib",
                    "trigger": "index"
                },
                "ORDER-LIMIT-123": {
                    "refid": None,
                    "userref": 0,
                    "status": "open",
                    "opentm": 1760578459.280463,
                    "descr": {
                        "pair": "XETHZUSD",
                        "type": "buy",
                        "ordertype": "limit",
                        "price": "3000.0",
                    },
                    "vol": "0.1",
                }
            }
        }


def main():
    """Run the demo."""
    print("=" * 70)
    print("Demo: Extract Open Trailing-Stop Orders")
    print("=" * 70)
    print()
    print("This demo shows how extract_open_orders.py works with mock data.")
    print("It queries open orders from Kraken API (mocked) and outputs")
    print("trailing-stop orders in config.csv format.\n")
    
    print("Mock API Response:")
    print("-" * 70)
    print("  - 2 trailing-stop orders (XXBTZUSDT)")
    print("  - 1 limit order (will be filtered out)")
    print()
    
    # Create mock API
    api = MockKrakenAPI()
    
    # Extract trailing-stop orders
    print("Extracting trailing-stop orders...")
    orders = extract_trailing_stop_orders(api)
    print(f"Found {len(orders)} trailing-stop orders")
    print()
    
    # Output as CSV
    print("Output in config.csv format:")
    print("-" * 70)
    output_as_csv(orders)
    print()
    
    print("=" * 70)
    print("Notes:")
    print("  - threshold_price and threshold_type are blank (not available)")
    print("  - These trigger the order creation, not tracked in open orders")
    print("  - All other fields are populated from the API response")
    print("  - Order ID is the Kraken transaction ID")
    print("=" * 70)


if __name__ == '__main__':
    main()
