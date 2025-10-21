#!/usr/bin/env python3
"""
Tests for CSV editor default path detection.
"""
import os
import sys


def get_default_config_path() -> str:
    """
    Determine the default config file path.
    
    Priority order:
    1. TTSLO_CONFIG_FILE environment variable (same as ttslo.py)
    2. If running as 'ttslo' user, use /var/lib/ttslo/config.csv
    3. Otherwise, use config.csv in current directory
    
    Returns:
        str: Path to the default config file
    """
    # First, check environment variable (same as ttslo.py does)
    env_config = os.getenv('TTSLO_CONFIG_FILE')
    if env_config:
        return env_config
    
    # Check if we're running as the ttslo service user
    try:
        import pwd
        current_user = pwd.getpwuid(os.getuid()).pw_name
        if current_user == 'ttslo':
            # Running as service user, use service directory
            return '/var/lib/ttslo/config.csv'
    except (ImportError, KeyError):
        # pwd module not available (Windows) or user not found
        pass
    
    # Default to config.csv in current directory (backwards compatible)
    return 'config.csv'


def test_default_path_with_env_var():
    """Test that TTSLO_CONFIG_FILE env var takes precedence."""
    # Set environment variable
    os.environ['TTSLO_CONFIG_FILE'] = '/custom/path/config.csv'
    
    try:
        result = get_default_config_path()
        assert result == '/custom/path/config.csv', \
            f"Expected /custom/path/config.csv, got {result}"
        print("✓ Environment variable override test passed")
    finally:
        # Clean up
        del os.environ['TTSLO_CONFIG_FILE']


def test_default_path_without_env_var():
    """Test default behavior without env var."""
    # Ensure env var is not set
    if 'TTSLO_CONFIG_FILE' in os.environ:
        del os.environ['TTSLO_CONFIG_FILE']
    
    result = get_default_config_path()
    
    # Should be either /var/lib/ttslo/config.csv (if running as ttslo user)
    # or config.csv (otherwise)
    assert result in ['/var/lib/ttslo/config.csv', 'config.csv'], \
        f"Expected /var/lib/ttslo/config.csv or config.csv, got {result}"
    
    print(f"✓ Default path test passed (result: {result})")


def test_ttslo_user_detection():
    """Test that we correctly detect when running as ttslo user."""
    # This test will only be meaningful if running as ttslo user
    try:
        import pwd
        current_user = pwd.getpwuid(os.getuid()).pw_name
        
        # Ensure env var is not set
        if 'TTSLO_CONFIG_FILE' in os.environ:
            del os.environ['TTSLO_CONFIG_FILE']
        
        result = get_default_config_path()
        
        if current_user == 'ttslo':
            assert result == '/var/lib/ttslo/config.csv', \
                f"Expected /var/lib/ttslo/config.csv for ttslo user, got {result}"
            print("✓ TTSLO user detection test passed")
        else:
            assert result == 'config.csv', \
                f"Expected config.csv for non-ttslo user, got {result}"
            print(f"✓ Non-TTSLO user test passed (user: {current_user})")
    except ImportError:
        print("⊘ Skipping user detection test (pwd module not available)")


if __name__ == '__main__':
    print("Running CSV editor default path tests...\n")
    test_default_path_with_env_var()
    test_default_path_without_env_var()
    test_ttslo_user_detection()
    print("\nAll tests passed!")
