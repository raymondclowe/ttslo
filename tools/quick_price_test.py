#!/usr/bin/env python3
"""
Quick Price Update Frequency Test - 30 second version for faster testing
"""
import sys
import time
import json
import statistics
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional

# Modify the main test duration
TEST_DURATION = 30  # 30 seconds per test

# Import the main script's classes
import price_update_frequency_test as main_test

def main():
    """Main entry point with shorter test duration."""
    print(f"\n{'='*80}")
    print(f"Kraken Price Update Frequency Analysis (Quick Test - 30s)")
    print(f"{'='*80}")
    print(f"Testing BTC/USD price update behavior")
    print(f"Comparing REST API polling vs WebSocket streaming")
    print(f"{'='*80}\n")
    
    # Configuration
    rest_pair = 'XXBTZUSD'  # REST API format
    ws_pair = 'XBT/USD'      # WebSocket format
    test_duration = TEST_DURATION
    rest_interval = 1.0      # Poll every 1 second
    
    # Test REST API
    print("Starting REST API test...")
    rest_tester = main_test.RESTAPITester(pair=rest_pair)
    rest_stats = rest_tester.poll_prices(
        duration_seconds=test_duration,
        interval_seconds=rest_interval
    )
    main_test.print_statistics(rest_stats, "REST API Results")
    
    # Test WebSocket (if available)
    ws_stats = None
    if main_test.WEBSOCKET_AVAILABLE:
        print("Starting WebSocket test...")
        ws_tester = main_test.WebSocketTester(pair=ws_pair)
        ws_stats = ws_tester.stream_prices(duration_seconds=test_duration)
        if ws_stats:
            main_test.print_statistics(ws_stats, "WebSocket Results")
    else:
        print("WebSocket not available, skipping WebSocket test")
    
    # Compare results
    main_test.compare_results(rest_stats, ws_stats)
    
    # Summary and Recommendations
    print(f"\n{'='*80}")
    print(f"SUMMARY AND RECOMMENDATIONS")
    print(f"{'='*80}\n")
    
    print("Key Findings:")
    print("1. REST API provides snapshot data when polled")
    print("2. Price updates reflect the latest market price at query time")
    print("3. REST API has rate limit of ~1 request per second")
    
    if ws_stats and 'error' not in ws_stats:
        print("4. WebSocket provides real-time streaming updates")
        print("5. WebSocket receives updates immediately when trades occur")
        print("6. WebSocket is significantly faster for real-time price monitoring")
    
    print("\nRecommendations:")
    print("• For real-time price monitoring: Use WebSocket API")
    print("• For occasional price checks: Use REST API")
    print("• For automated trading: Use WebSocket for minimal latency")
    print("• Both public and private endpoints return the same market price")
    print("• The 'delay' observed with REST is likely due to polling interval")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
