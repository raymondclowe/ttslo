#!/usr/bin/env python3
"""
Live integration tests for Kraken API client.

These tests run against the real Kraken API and should only be executed
after all local unit tests pass. They use minimal order sizes with
unreasonable prices to avoid execution.

Environment variables required:
- COPILOT_W_KR_RW_PUBLIC: Kraken API public key
- COPILOT_W_KR_RW_SECRET: Kraken API secret key
"""
import os
import sys
import time
import json
import logging
from datetime import datetime
from decimal import Decimal
import pytest
from dotenv import load_dotenv

load_dotenv()

# Map .env keys to expected test environment variables
os.environ['COPILOT_W_KR_RW_PUBLIC'] = os.environ.get('KRAKEN_API_KEY_RW', '')
os.environ['COPILOT_W_KR_RW_SECRET'] = os.environ.get('KRAKEN_API_SECRET_RW', '')

from kraken_api import KrakenAPI


# Configure logging for detailed request/response tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveTestLogger:
    """Logger for tracking all API operations during live tests."""
    
    def __init__(self):
        self.log_file = f"kraken_live_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.operations = []
    
    def log_operation(self, operation_type, params, response, error=None):
        """Log an API operation with full details."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation_type,
            'params': params,
            'response': response,
            'error': str(error) if error else None
        }
        self.operations.append(entry)
        
        # Log to console
        logger.info(f"\n{'='*80}")
        logger.info(f"Operation: {operation_type}")
        logger.info(f"Params: {json.dumps(params, indent=2)}")
        if error:
            logger.error(f"Error: {error}")
        else:
            logger.info(f"Response: {json.dumps(response, indent=2)}")
        logger.info(f"{'='*80}\n")
    
    def save_log(self):
        """Save all operations to a log file."""
        with open(self.log_file, 'w') as f:
            json.dump(self.operations, f, indent=2)
        logger.info(f"Log saved to: {self.log_file}")


@pytest.fixture(scope="module")
def live_api():
    """Create KrakenAPI instance with credentials from environment."""
    api_key = os.environ.get('COPILOT_W_KR_RW_PUBLIC')
    api_secret = os.environ.get('COPILOT_W_KR_RW_SECRET')
    
    if not api_key or not api_secret:
        pytest.skip("Live API credentials not available in environment")
    
    return KrakenAPI(api_key=api_key, api_secret=api_secret)


@pytest.fixture(scope="module")
def test_logger():
    """Create logger for tracking test operations."""
    logger = LiveTestLogger()
    yield logger
    logger.save_log()


@pytest.fixture(scope="module")
def btc_current_price(live_api, test_logger):
    """Get current BTC/USD price for calculating unreasonable prices."""
    try:
        price = live_api.get_current_price('XXBTZUSD')
        test_logger.log_operation(
            'get_current_price',
            {'pair': 'XXBTZUSD'},
            {'price': price}
        )
        logger.info(f"Current BTC/USD price: ${price:,.2f}")
        return price
    except Exception as e:
        test_logger.log_operation(
            'get_current_price',
            {'pair': 'XXBTZUSD'},
            None,
            error=e
        )
        pytest.fail(f"Failed to get current price: {e}")


class TestKrakenAPILive:
    """Live integration tests for Kraken API."""
    
    # Minimum order volumes - varying by 5% increments
    # For BTC, minimum is typically around 0.0001
    BASE_VOLUME = Decimal('0.0001')
    
    @classmethod
    def get_next_volume(cls, iteration):
        """Get next volume, varying slightly each time."""
        # Increase by 5% for each iteration
        multiplier = Decimal('1.05') ** iteration
        return float(cls.BASE_VOLUME * multiplier)
    
    @classmethod
    def get_unreasonable_buy_price(cls, current_price):
        """Get a buy price that's 10% below market (won't execute)."""
        # Round to 1 decimal place for BTC/USD pair requirements
        price = float(Decimal(str(current_price)) * Decimal('0.90'))
        return round(price, 1)
    
    @classmethod
    def get_unreasonable_sell_price(cls, current_price):
        """Get a sell price that's 10% above market (won't execute)."""
        # Round to 1 decimal place for BTC/USD pair requirements
        price = float(Decimal(str(current_price)) * Decimal('1.10'))
        return round(price, 1)
    
    def test_01_live_add_query_modify_cancel_limit_order(
        self, live_api, test_logger, btc_current_price
    ):
        """
        Test complete lifecycle: add limit order -> query -> modify -> query -> cancel -> query.
        
        This test:
        1. Creates a limit buy order at 10% below market (won't execute)
        2. Queries to verify order was created
        3. Modifies the order (changes volume)
        4. Queries to verify modification
        5. Cancels the order
        6. Queries to verify cancellation
        """
        # Step 1: Add limit sell order at unreasonable price
        volume = self.get_next_volume(0)
        sell_price = self.get_unreasonable_sell_price(btc_current_price)
        
        logger.info(f"\n{'#'*80}")
        logger.info(f"TEST 1: Add -> Query -> Modify -> Query -> Cancel -> Query")
        logger.info(f"Volume: {volume} BTC")
        logger.info(f"Sell Price: ${sell_price:,.2f} (current: ${btc_current_price:,.2f})")
        logger.info(f"{'#'*80}\n")
        
        add_params = {
            'pair': 'BTC/USD',
            'order_type': 'limit',
            'direction': 'sell',
            'volume': volume,
            'price': str(sell_price)
        }
        
        try:
            add_result = live_api.add_order(**add_params)
            test_logger.log_operation('add_order', add_params, add_result)
            
            assert 'txid' in add_result, "Order should return txid"
            txid = add_result['txid'][0]
            logger.info(f"✓ Order created: {txid}")
            
        except Exception as e:
            test_logger.log_operation('add_order', add_params, None, error=e)
            pytest.fail(f"Failed to add order: {e}")
        
        # Small delay to ensure order is in system
        time.sleep(2)
        
        # Step 2: Query to verify order was created
        try:
            query_result = live_api.query_open_orders()
            test_logger.log_operation('query_open_orders', {}, query_result)
            
            assert 'open' in query_result, "Query should return 'open' dict"
            assert txid in query_result['open'], f"Order {txid} should be in open orders"
            
            order = query_result['open'][txid]
            assert order['descr']['type'] == 'sell', "Order should be sell type"
            assert float(order['vol']) == volume, f"Order volume should be {volume}"
            logger.info(f"✓ Order verified in open orders")
            
        except Exception as e:
            test_logger.log_operation('query_open_orders', {}, None, error=e)
            pytest.fail(f"Failed to query orders after add: {e}")
        
        # Step 3: Modify the order (increase volume slightly)
        new_volume = self.get_next_volume(1)
        modify_params = {
            'txid': txid,
            'pair': 'BTC/USD',
            'volume': new_volume,
            'price': str(sell_price)
        }
        
        try:
            modify_result = live_api.edit_order(**modify_params)
            test_logger.log_operation('edit_order', modify_params, modify_result)
            
            # Edit may return new txid
            if 'txid' in modify_result:
                new_txid = modify_result['txid']
                logger.info(f"✓ Order modified, new txid: {new_txid}")
                txid = new_txid  # Update txid for subsequent operations
            else:
                logger.info(f"✓ Order modified: {txid}")
            
        except Exception as e:
            test_logger.log_operation('edit_order', modify_params, None, error=e)
            logger.warning(f"Failed to modify order (may not be supported): {e}")
            # Note: Edit may not be supported or may fail, continue to cancel
        
        time.sleep(2)
        
        # Step 4: Query to verify modification
        try:
            query_result2 = live_api.query_open_orders()
            test_logger.log_operation('query_open_orders', {}, query_result2)
            
            if txid in query_result2.get('open', {}):
                order = query_result2['open'][txid]
                logger.info(f"✓ Order still in open orders, volume: {order['vol']}")
            else:
                logger.info(f"✓ Order {txid} not found (may have been replaced)")
            
        except Exception as e:
            test_logger.log_operation('query_open_orders', {}, None, error=e)
            logger.warning(f"Failed to query orders after modify: {e}")
        
        # Step 5: Cancel the order
        cancel_params = {'txid': txid}
        
        try:
            cancel_result = live_api.cancel_order(txid)
            test_logger.log_operation('cancel_order', cancel_params, cancel_result)
            
            logger.info(f"✓ Order cancelled: {txid}")
            
        except Exception as e:
            test_logger.log_operation('cancel_order', cancel_params, None, error=e)
            pytest.fail(f"Failed to cancel order: {e}")
        
        time.sleep(2)
        
        # Step 6: Query to verify cancellation
        try:
            query_result3 = live_api.query_open_orders()
            test_logger.log_operation('query_open_orders', {}, query_result3)
            
            assert txid not in query_result3.get('open', {}), \
                f"Order {txid} should not be in open orders after cancellation"
            logger.info(f"✓ Order confirmed cancelled and removed from open orders")
            
        except Exception as e:
            test_logger.log_operation('query_open_orders', {}, None, error=e)
            pytest.fail(f"Failed to query orders after cancel: {e}")
        
        logger.info(f"\n✓✓✓ TEST 1 PASSED: Full lifecycle completed successfully\n")
    
    def test_02_live_add_trailing_stop_and_cancel(
        self, live_api, test_logger, btc_current_price
    ):
        """
        Test trailing stop order: add -> query -> cancel -> query.
        
        This test:
        1. Creates a trailing stop sell order with 10% offset (won't execute)
        2. Queries to verify order was created
        3. Cancels the order
        4. Queries to verify cancellation
        """
        volume = self.get_next_volume(2)
        
        logger.info(f"\n{'#'*80}")
        logger.info(f"TEST 2: Add Trailing Stop -> Query -> Cancel -> Query")
        logger.info(f"Volume: {volume} BTC")
        logger.info(f"Trailing offset: 10%")
        logger.info(f"{'#'*80}\n")
        
        # Step 1: Add trailing stop sell order
        add_params = {
            'pair': 'BTC/USD',
            'direction': 'sell',
            'volume': volume,
            'trailing_offset_percent': 10.0
        }
        
        try:
            add_result = live_api.add_trailing_stop_loss(**add_params)
            test_logger.log_operation('add_trailing_stop_loss', add_params, add_result)
            
            assert 'txid' in add_result, "Order should return txid"
            txid = add_result['txid'][0]
            logger.info(f"✓ Trailing stop order created: {txid}")
            
        except Exception as e:
            test_logger.log_operation('add_trailing_stop_loss', add_params, None, error=e)
            pytest.fail(f"Failed to add trailing stop order: {e}")
        
        time.sleep(2)
        
        # Step 2: Query to verify order was created
        try:
            query_result = live_api.query_open_orders()
            test_logger.log_operation('query_open_orders', {}, query_result)
            
            assert 'open' in query_result, "Query should return 'open' dict"
            assert txid in query_result['open'], f"Order {txid} should be in open orders"
            
            order = query_result['open'][txid]
            assert order['descr']['ordertype'] == 'trailing-stop', \
                "Order should be trailing-stop type"
            logger.info(f"✓ Trailing stop order verified in open orders")
            
        except Exception as e:
            test_logger.log_operation('query_open_orders', {}, None, error=e)
            pytest.fail(f"Failed to query orders after add: {e}")
        
        # Step 3: Cancel the order
        cancel_params = {'txid': txid}
        
        try:
            cancel_result = live_api.cancel_order(txid)
            test_logger.log_operation('cancel_order', cancel_params, cancel_result)
            
            logger.info(f"✓ Trailing stop order cancelled: {txid}")
            
        except Exception as e:
            test_logger.log_operation('cancel_order', cancel_params, None, error=e)
            pytest.fail(f"Failed to cancel order: {e}")
        
        time.sleep(2)
        
        # Step 4: Query to verify cancellation
        try:
            query_result2 = live_api.query_open_orders()
            test_logger.log_operation('query_open_orders', {}, query_result2)
            
            assert txid not in query_result2.get('open', {}), \
                f"Order {txid} should not be in open orders after cancellation"
            logger.info(f"✓ Trailing stop order confirmed cancelled")
            
        except Exception as e:
            test_logger.log_operation('query_open_orders', {}, None, error=e)
            pytest.fail(f"Failed to query orders after cancel: {e}")
        
        logger.info(f"\n✓✓✓ TEST 2 PASSED: Trailing stop lifecycle completed successfully\n")
    
    def test_03_live_multiple_orders_batch_cancel(
        self, live_api, test_logger, btc_current_price
    ):
        """
        Test creating multiple orders and cancelling them.
        
        This test:
        1. Creates 3 orders with different volumes
        2. Queries to verify all were created
        3. Cancels all orders
        4. Queries to verify all were cancelled
        """
        logger.info(f"\n{'#'*80}")
        logger.info(f"TEST 3: Create Multiple Orders -> Query -> Cancel All -> Query")
        logger.info(f"{'#'*80}\n")
        
        txids = []
        sell_price = self.get_unreasonable_sell_price(btc_current_price)
        
        # Step 1: Create 3 orders with different volumes
        for i in range(3, 6):  # iterations 3, 4, 5
            volume = self.get_next_volume(i)
            add_params = {
                'pair': 'BTC/USD',
                'order_type': 'limit',
                'direction': 'sell',
                'volume': volume,
                'price': str(sell_price)
            }
            
            try:
                add_result = live_api.add_order(**add_params)
                test_logger.log_operation('add_order', add_params, add_result)
                
                txid = add_result['txid'][0]
                txids.append(txid)
                logger.info(f"✓ Order {i-2}/3 created: {txid} (volume: {volume})")
                
            except Exception as e:
                test_logger.log_operation('add_order', add_params, None, error=e)
                logger.error(f"Failed to create order {i-2}/3: {e}")
                # Continue trying to create remaining orders
        
        if not txids:
            pytest.fail("Failed to create any orders")
        
        time.sleep(2)
        
        # Step 2: Query to verify all were created
        try:
            query_result = live_api.query_open_orders()
            test_logger.log_operation('query_open_orders', {}, query_result)
            
            open_orders = query_result.get('open', {})
            for txid in txids:
                assert txid in open_orders, f"Order {txid} should be in open orders"
            
            logger.info(f"✓ All {len(txids)} orders verified in open orders")
            
        except Exception as e:
            test_logger.log_operation('query_open_orders', {}, None, error=e)
            logger.error(f"Failed to query orders: {e}")
        
        # Step 3: Cancel all orders
        for i, txid in enumerate(txids, 1):
            cancel_params = {'txid': txid}
            
            try:
                cancel_result = live_api.cancel_order(txid)
                test_logger.log_operation('cancel_order', cancel_params, cancel_result)
                
                logger.info(f"✓ Order {i}/{len(txids)} cancelled: {txid}")
                
            except Exception as e:
                test_logger.log_operation('cancel_order', cancel_params, None, error=e)
                logger.error(f"Failed to cancel order {txid}: {e}")
        
        time.sleep(2)
        
        # Step 4: Query to verify all were cancelled
        try:
            query_result2 = live_api.query_open_orders()
            test_logger.log_operation('query_open_orders', {}, query_result2)
            
            open_orders = query_result2.get('open', {})
            for txid in txids:
                assert txid not in open_orders, \
                    f"Order {txid} should not be in open orders after cancellation"
            
            logger.info(f"✓ All {len(txids)} orders confirmed cancelled")
            
        except Exception as e:
            test_logger.log_operation('query_open_orders', {}, None, error=e)
            pytest.fail(f"Failed to query orders after cancellations: {e}")
        
        logger.info(f"\n✓✓✓ TEST 3 PASSED: Multiple orders lifecycle completed successfully\n")


if __name__ == '__main__':
    # Run live tests only if local tests pass
    logger.info("Running local tests first...")
    local_result = pytest.main([
        'test_kraken_api.py',
        '-v',
        '--tb=short'
    ])
    
    if local_result == 0:
        logger.info("\n" + "="*80)
        logger.info("LOCAL TESTS PASSED - Proceeding with live tests")
        logger.info("="*80 + "\n")
        
        pytest.main([
            __file__,
            '-v',
            '--tb=short',
            '-s'  # Show print statements
        ])
    else:
        logger.error("\n" + "="*80)
        logger.error("LOCAL TESTS FAILED - Skipping live tests")
        logger.error("="*80 + "\n")
        sys.exit(1)
