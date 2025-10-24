"""
Test for dashboard closed orders API with start parameter.
"""
import time
from unittest.mock import Mock, patch
import pytest


def test_get_cached_closed_orders_uses_start_parameter():
    """Test that get_cached_closed_orders passes the start parameter for last 30 days."""
    # Create a mock kraken API
    mock_kraken_api = Mock()
    mock_kraken_api.query_closed_orders = Mock(return_value={'closed': {'order1': {'status': 'closed'}}})
    
    # Patch kraken_api in dashboard module
    with patch('dashboard.kraken_api', mock_kraken_api):
        # Import here so the patch is applied
        from dashboard import get_cached_closed_orders
        
        # Clear any cached results
        if hasattr(get_cached_closed_orders, '__wrapped__'):
            get_cached_closed_orders.__wrapped__.cache = {'result': None, 'timestamp': 0}
        
        # Call the function
        result = get_cached_closed_orders()
        
        # Verify the API was called
        assert mock_kraken_api.query_closed_orders.called, "API should be called"
        
        # Get the call arguments
        call_args, call_kwargs = mock_kraken_api.query_closed_orders.call_args
        
        # Verify that the start parameter was passed
        assert 'start' in call_kwargs, "start parameter should be passed"
        
        # Verify that the start time is approximately 30 days ago
        thirty_days_in_seconds = 30 * 24 * 60 * 60
        expected_start = int(time.time()) - thirty_days_in_seconds
        actual_start = call_kwargs['start']
        
        # Allow 10 seconds tolerance for test execution time
        assert abs(actual_start - expected_start) < 10, \
            f"start parameter should be ~30 days ago. Expected: {expected_start}, Got: {actual_start}"
        
        # Verify the result is correct
        assert result == {'order1': {'status': 'closed'}}

