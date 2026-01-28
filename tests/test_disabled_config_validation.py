"""
Test that disabled configs are validated but not executed.

This test ensures that configs with enabled=false are still validated
and any errors/warnings are reported to the user, addressing the issue
where users had no feedback about why disabled configs weren't working.
"""
from decimal import Decimal
from validator import ConfigValidator


class FakeKrakenAPI:
    def __init__(self, balance, prices):
        self._balance = balance
        self._prices = prices

    def get_balance(self):
        return self._balance

    def get_current_price(self, pair):
        return self._prices.get(pair)


def test_disabled_configs_are_validated():
    """Test that disabled configs are validated for errors."""
    api = FakeKrakenAPI(
        balance={'XXBT': '1.0'},
        prices={'XBTUSDT': Decimal('90000'), 'XBTUSD': Decimal('90000')}
    )

    validator = ConfigValidator(kraken_api=api)
    configs = [
        # Disabled config with valid settings
        {
            'id': 'disabled_valid',
            'pair': 'XBTUSDT',
            'threshold_price': '95000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '2.0',
            'enabled': 'false',
        },
        # Disabled config with INVALID pair
        {
            'id': 'disabled_invalid_pair',
            'pair': 'INVALIDPAIR',
            'threshold_price': '95000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '2.0',
            'enabled': 'false',
        },
        # Enabled config (for comparison)
        {
            'id': 'enabled_valid',
            'pair': 'XBTUSD',
            'threshold_price': '95000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.05',
            'trailing_offset_percent': '2.0',
            'enabled': 'true',
        }
    ]

    result = validator.validate_config_file(configs)
    
    # Validation should FAIL because disabled_invalid_pair has an error
    assert not result.is_valid()
    
    # Should have 1 error (invalid pair in disabled config)
    assert len(result.errors) == 1
    assert result.errors[0]['config_id'] == 'disabled_invalid_pair'
    assert result.errors[0]['field'] == 'pair'
    
    # Total configs validated should be 3
    assert result.total_configs_validated == 3
    
    # Only enabled config should be in result.configs (for execution)
    assert len(result.configs) == 1
    assert result.configs[0]['id'] == 'enabled_valid'
    
    # Should have info messages for disabled configs
    disabled_infos = [i for i in result.infos if 'disabled' in i['message'].lower()]
    assert len(disabled_infos) == 2  # Two disabled configs


def test_disabled_config_info_messages():
    """Test that disabled configs get info messages explaining their status."""
    api = FakeKrakenAPI(
        balance={'XXBT': '1.0'},
        prices={'XBTUSDT': Decimal('90000')}
    )

    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'test_disabled',
            'pair': 'XBTUSDT',
            'threshold_price': '95000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '2.0',
            'enabled': 'false',
        }
    ]

    result = validator.validate_config_file(configs)
    
    # Should be valid (no errors)
    assert result.is_valid()
    
    # Should have 1 info message for disabled config
    assert len(result.infos) >= 1
    
    # Find the "disabled" info message
    disabled_info = None
    for info in result.infos:
        if info['config_id'] == 'test_disabled' and info['field'] == 'enabled':
            disabled_info = info
            break
    
    assert disabled_info is not None
    assert 'disabled' in disabled_info['message'].lower()
    assert 'enabled=false' in disabled_info['message']
    assert 'true' in disabled_info['message']  # Should tell user how to enable


def test_all_enabled_values_except_true_are_disabled():
    """Test that only 'true', 'yes', '1' are considered enabled."""
    api = FakeKrakenAPI(
        balance={'XXBT': '1.0'},
        prices={'XBTUSDT': Decimal('90000')}
    )

    validator = ConfigValidator(kraken_api=api)
    
    # Test various disabled values
    disabled_values = ['false', 'False', 'FALSE', 'no', 'No', '0', 'paused', 'canceled', 'pending', '']
    
    for disabled_value in disabled_values:
        configs = [
            {
                'id': f'test_{disabled_value}',
                'pair': 'XBTUSDT',
                'threshold_price': '95000',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.1',
                'trailing_offset_percent': '2.0',
                'enabled': disabled_value,
            }
        ]
        
        result = validator.validate_config_file(configs)
        
        # Config should not be in execution list
        assert len(result.configs) == 0, f"Config with enabled='{disabled_value}' should not be in execution list"
        
        # Should have info message about being disabled
        disabled_infos = [i for i in result.infos if i['field'] == 'enabled']
        assert len(disabled_infos) >= 1, f"No info message for enabled='{disabled_value}'"


def test_enabled_values_are_active():
    """Test that 'true', 'yes', '1' (case insensitive) are considered enabled."""
    api = FakeKrakenAPI(
        balance={'XXBT': '1.0'},
        prices={'XBTUSDT': Decimal('90000')}
    )

    validator = ConfigValidator(kraken_api=api)
    
    # Test various enabled values
    enabled_values = ['true', 'True', 'TRUE', 'yes', 'Yes', 'YES', '1']
    
    for enabled_value in enabled_values:
        configs = [
            {
                'id': f'test_{enabled_value}',
                'pair': 'XBTUSDT',
                'threshold_price': '95000',
                'threshold_type': 'above',
                'direction': 'sell',
                'volume': '0.1',
                'trailing_offset_percent': '2.0',
                'enabled': enabled_value,
            }
        ]
        
        result = validator.validate_config_file(configs)
        
        # Config should be in execution list
        assert len(result.configs) == 1, f"Config with enabled='{enabled_value}' should be in execution list"
        assert result.configs[0]['id'] == f'test_{enabled_value}'


def test_validation_report_shows_disabled_count():
    """Test that validation report shows enabled/disabled breakdown."""
    api = FakeKrakenAPI(
        balance={'XXBT': '1.0'},
        prices={'XBTUSDT': Decimal('90000')}
    )

    validator = ConfigValidator(kraken_api=api)
    configs = [
        {
            'id': 'enabled_1',
            'pair': 'XBTUSDT',
            'threshold_price': '95000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '2.0',
            'enabled': 'true',
        },
        {
            'id': 'disabled_1',
            'pair': 'XBTUSDT',
            'threshold_price': '95000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '2.0',
            'enabled': 'false',
        },
        {
            'id': 'disabled_2',
            'pair': 'XBTUSDT',
            'threshold_price': '95000',
            'threshold_type': 'above',
            'direction': 'sell',
            'volume': '0.1',
            'trailing_offset_percent': '2.0',
            'enabled': 'paused',
        }
    ]

    result = validator.validate_config_file(configs)
    
    # Total configs validated should be 3
    assert result.total_configs_validated == 3
    
    # Only 1 enabled config
    assert len(result.configs) == 1
    
    # Calculate disabled count
    disabled_count = result.total_configs_validated - len(result.configs)
    assert disabled_count == 2
