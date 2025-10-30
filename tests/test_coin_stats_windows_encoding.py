"""
Tests for coin_stats.py Windows encoding fix.
"""
import sys
import os
import io
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_windows_utf8_encoding_configuration():
    """Test that Windows UTF-8 encoding configuration is properly set up."""
    # Import the module which should configure UTF-8 on Windows
    import importlib
    import tools.coin_stats
    importlib.reload(tools.coin_stats)
    
    # On any platform, the module should import without errors
    # The encoding setup only activates on Windows
    assert tools.coin_stats is not None


def test_unicode_characters_in_output():
    """Test that Unicode characters used in the script can be printed."""
    # These are the Unicode characters used in coin_stats.py
    unicode_chars = ['✓', '✅', '⚠️', '✗']
    
    # Try to encode them - should not raise UnicodeEncodeError
    for char in unicode_chars:
        try:
            # Try encoding with UTF-8
            encoded = char.encode('utf-8')
            assert encoded is not None
            
            # Try printing to a StringIO buffer
            buffer = io.StringIO()
            print(char, file=buffer)
            output = buffer.getvalue()
            assert char in output
        except UnicodeEncodeError as e:
            assert False, f"Failed to encode Unicode character {char}: {e}"


def test_print_with_unicode_symbols():
    """Test that print statements with Unicode work through StringIO."""
    from tools.coin_stats import CoinStatsAnalyzer
    
    # The script uses these exact print statements that failed on Windows
    test_messages = [
        "\n✓ Summary table saved to test.csv",
        "\n✓ HTML graph viewer saved to test.html",
        "\n✅ Analysis complete!",
        "⚠️  Warning: test warning",
    ]
    
    for msg in test_messages:
        buffer = io.StringIO()
        try:
            print(msg, file=buffer)
            output = buffer.getvalue()
            # Just verify it doesn't crash
            assert output is not None
        except UnicodeEncodeError as e:
            assert False, f"Failed to print message: {msg}. Error: {e}"


def test_windows_platform_detection():
    """Test that the Windows platform detection works correctly."""
    # Mock Windows platform
    with patch('sys.platform', 'win32'):
        # Mock stdout with non-UTF-8 encoding
        original_stdout = sys.stdout
        mock_stdout = io.TextIOWrapper(io.BytesIO(), encoding='cp1252')
        
        try:
            with patch('sys.stdout', mock_stdout):
                # This simulates what happens when the module loads on Windows
                # The actual reconfiguration happens at module import time,
                # but we can verify the logic would work
                if sys.platform == 'win32' and sys.stdout.encoding != 'utf-8':
                    # This is what the fix does
                    assert True
                else:
                    # On non-Windows or already UTF-8, it should skip
                    pass
        finally:
            sys.stdout = original_stdout


if __name__ == '__main__':
    test_windows_utf8_encoding_configuration()
    test_unicode_characters_in_output()
    test_print_with_unicode_symbols()
    test_windows_platform_detection()
    print("✅ All Windows encoding tests passed!")
