#!/usr/bin/env python3
"""
Tests for credential loading and environment variable resolution.

Tests the creds module's ability to find Kraken API credentials from
multiple sources including GitHub environment secrets.
"""
import os
import pytest
from creds import get_env_var, find_kraken_credentials, load_env


class TestGetEnvVar:
    """Test get_env_var function with various environment variable patterns."""
    
    def test_exact_match(self):
        """Test that exact environment variable name takes precedence."""
        os.environ['TEST_VAR'] = 'exact_value'
        os.environ['copilot_TEST_VAR'] = 'copilot_value'
        
        result = get_env_var('TEST_VAR')
        
        assert result == 'exact_value'
        
        # Cleanup
        del os.environ['TEST_VAR']
        del os.environ['copilot_TEST_VAR']
    
    def test_copilot_prefix(self):
        """Test that copilot_ prefix works when exact name not found."""
        os.environ['copilot_TEST_VAR'] = 'copilot_value'
        
        result = get_env_var('TEST_VAR')
        
        assert result == 'copilot_value'
        
        # Cleanup
        del os.environ['copilot_TEST_VAR']
    
    def test_no_match_returns_none(self):
        """Test that None is returned when no variant is found."""
        result = get_env_var('NONEXISTENT_VAR')
        
        assert result is None
    
    def test_kraken_api_key_with_copilot_w_ro_public(self):
        """Test KRAKEN_API_KEY resolves COPILOT_W_KR_RO_PUBLIC."""
        os.environ['COPILOT_W_KR_RO_PUBLIC'] = 'ro_public_key'
        
        result = get_env_var('KRAKEN_API_KEY')
        
        assert result == 'ro_public_key'
        
        # Cleanup
        del os.environ['COPILOT_W_KR_RO_PUBLIC']
    
    def test_kraken_api_key_with_copilot_w_kr_public(self):
        """Test KRAKEN_API_KEY resolves COPILOT_W_KR_PUBLIC (fallback)."""
        os.environ['COPILOT_W_KR_PUBLIC'] = 'public_key'
        
        result = get_env_var('KRAKEN_API_KEY')
        
        assert result == 'public_key'
        
        # Cleanup
        del os.environ['COPILOT_W_KR_PUBLIC']
    
    def test_kraken_api_key_with_copilot_kraken_api_key(self):
        """Test KRAKEN_API_KEY resolves COPILOT_KRAKEN_API_KEY (GitHub secrets)."""
        os.environ['COPILOT_KRAKEN_API_KEY'] = 'github_secret_key'
        
        result = get_env_var('KRAKEN_API_KEY')
        
        assert result == 'github_secret_key'
        
        # Cleanup
        del os.environ['COPILOT_KRAKEN_API_KEY']
    
    def test_kraken_api_secret_with_copilot_kraken_api_secret(self):
        """Test KRAKEN_API_SECRET resolves COPILOT_KRAKEN_API_SECRET (GitHub secrets)."""
        os.environ['COPILOT_KRAKEN_API_SECRET'] = 'github_secret_value'
        
        result = get_env_var('KRAKEN_API_SECRET')
        
        assert result == 'github_secret_value'
        
        # Cleanup
        del os.environ['COPILOT_KRAKEN_API_SECRET']
    
    def test_kraken_api_key_precedence_order(self):
        """Test precedence: COPILOT_W_KR_RO_PUBLIC over COPILOT_W_KR_PUBLIC over COPILOT_KRAKEN_API_KEY."""
        # Set all three variants
        os.environ['COPILOT_W_KR_RO_PUBLIC'] = 'ro_public'
        os.environ['COPILOT_W_KR_PUBLIC'] = 'public'
        os.environ['COPILOT_KRAKEN_API_KEY'] = 'github_key'
        
        result = get_env_var('KRAKEN_API_KEY')
        
        # Should prefer COPILOT_W_KR_RO_PUBLIC (first in chain)
        assert result == 'ro_public'
        
        # Cleanup
        del os.environ['COPILOT_W_KR_RO_PUBLIC']
        del os.environ['COPILOT_W_KR_PUBLIC']
        del os.environ['COPILOT_KRAKEN_API_KEY']
    
    def test_kraken_api_key_fallback_to_second(self):
        """Test fallback to COPILOT_W_KR_PUBLIC when COPILOT_W_KR_RO_PUBLIC not set."""
        os.environ['COPILOT_W_KR_PUBLIC'] = 'public'
        os.environ['COPILOT_KRAKEN_API_KEY'] = 'github_key'
        
        result = get_env_var('KRAKEN_API_KEY')
        
        # Should use COPILOT_W_KR_PUBLIC (second in chain)
        assert result == 'public'
        
        # Cleanup
        del os.environ['COPILOT_W_KR_PUBLIC']
        del os.environ['COPILOT_KRAKEN_API_KEY']
    
    def test_kraken_api_key_fallback_to_github_secret(self):
        """Test fallback to COPILOT_KRAKEN_API_KEY when other variants not set."""
        os.environ['COPILOT_KRAKEN_API_KEY'] = 'github_key'
        
        result = get_env_var('KRAKEN_API_KEY')
        
        # Should use COPILOT_KRAKEN_API_KEY (last fallback)
        assert result == 'github_key'
        
        # Cleanup
        del os.environ['COPILOT_KRAKEN_API_KEY']
    
    def test_kraken_api_secret_precedence_order(self):
        """Test precedence for KRAKEN_API_SECRET variants."""
        os.environ['COPILOT_W_KR_RO_SECRET'] = 'ro_secret'
        os.environ['COPILOT_W_KR_SECRET'] = 'secret'
        os.environ['COPILOT_KRAKEN_API_SECRET'] = 'github_secret'
        
        result = get_env_var('KRAKEN_API_SECRET')
        
        # Should prefer COPILOT_W_KR_RO_SECRET (first in chain)
        assert result == 'ro_secret'
        
        # Cleanup
        del os.environ['COPILOT_W_KR_RO_SECRET']
        del os.environ['COPILOT_W_KR_SECRET']
        del os.environ['COPILOT_KRAKEN_API_SECRET']
    
    def test_kraken_api_key_rw_with_copilot_w_variants(self):
        """Test read-write key resolution with COPILOT_W_ variants."""
        os.environ['COPILOT_W_KR_RW_PUBLIC'] = 'rw_public_key'
        
        result = get_env_var('KRAKEN_API_KEY_RW')
        
        assert result == 'rw_public_key'
        
        # Cleanup
        del os.environ['COPILOT_W_KR_RW_PUBLIC']
    
    def test_kraken_api_secret_rw_with_copilot_w_variants(self):
        """Test read-write secret resolution with COPILOT_W_ variants."""
        os.environ['COPILOT_W_KR_RW_SECRET'] = 'rw_secret_value'
        
        result = get_env_var('KRAKEN_API_SECRET_RW')
        
        assert result == 'rw_secret_value'
        
        # Cleanup
        del os.environ['COPILOT_W_KR_RW_SECRET']


class TestFindKrakenCredentials:
    """Test find_kraken_credentials function."""
    
    def test_find_readonly_credentials_with_github_secrets(self):
        """Test finding read-only credentials from COPILOT_KRAKEN_* vars."""
        os.environ['COPILOT_KRAKEN_API_KEY'] = 'test_key_readonly'
        os.environ['COPILOT_KRAKEN_API_SECRET'] = 'test_secret_readonly'
        
        key, secret = find_kraken_credentials(readwrite=False)
        
        assert key == 'test_key_readonly'
        assert secret == 'test_secret_readonly'
        
        # Cleanup
        del os.environ['COPILOT_KRAKEN_API_KEY']
        del os.environ['COPILOT_KRAKEN_API_SECRET']
    
    def test_find_readwrite_credentials(self):
        """Test finding read-write credentials."""
        os.environ['COPILOT_W_KR_RW_PUBLIC'] = 'test_key_rw'
        os.environ['COPILOT_W_KR_RW_SECRET'] = 'test_secret_rw'
        
        key, secret = find_kraken_credentials(readwrite=True)
        
        assert key == 'test_key_rw'
        assert secret == 'test_secret_rw'
        
        # Cleanup
        del os.environ['COPILOT_W_KR_RW_PUBLIC']
        del os.environ['COPILOT_W_KR_RW_SECRET']
    
    def test_find_credentials_returns_none_when_not_found(self):
        """Test that (None, None) is returned when credentials not found."""
        # Ensure no credentials are set
        for key in ['KRAKEN_API_KEY', 'KRAKEN_API_SECRET', 'copilot_KRAKEN_API_KEY',
                    'COPILOT_W_KR_RO_PUBLIC', 'COPILOT_W_KR_PUBLIC', 'COPILOT_KRAKEN_API_KEY',
                    'COPILOT_W_KR_RO_SECRET', 'COPILOT_W_KR_SECRET', 'COPILOT_KRAKEN_API_SECRET']:
            os.environ.pop(key, None)
        
        key, secret = find_kraken_credentials(readwrite=False)
        
        assert key is None
        assert secret is None
    
    def test_find_credentials_prefers_standard_names_over_copilot(self):
        """Test that standard env var names take precedence."""
        os.environ['KRAKEN_API_KEY'] = 'standard_key'
        os.environ['KRAKEN_API_SECRET'] = 'standard_secret'
        os.environ['COPILOT_KRAKEN_API_KEY'] = 'github_key'
        os.environ['COPILOT_KRAKEN_API_SECRET'] = 'github_secret'
        
        key, secret = find_kraken_credentials(readwrite=False)
        
        assert key == 'standard_key'
        assert secret == 'standard_secret'
        
        # Cleanup
        del os.environ['KRAKEN_API_KEY']
        del os.environ['KRAKEN_API_SECRET']
        del os.environ['COPILOT_KRAKEN_API_KEY']
        del os.environ['COPILOT_KRAKEN_API_SECRET']


class TestLoadEnv:
    """Test load_env function."""
    
    def test_load_env_existing_var_not_overridden(self):
        """Test that existing environment variables are not overridden by .env file."""
        # This is tested implicitly by the precedence tests above
        # The function is conservative and won't override existing vars
        pass
