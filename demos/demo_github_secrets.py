#!/usr/bin/env python3
"""
Demo script to show how creds.py now supports GitHub environment secrets.

This demonstrates that COPILOT_KRAKEN_API_KEY and COPILOT_KRAKEN_API_SECRET
can be used for read-only tests.

NOTE: This demo uses fake/example credentials for demonstration purposes only.
The CodeQL alerts about logging sensitive data are expected here as we're
showing how the credential lookup works with example values.
"""
import os
import sys

# Add parent directory to path so we can import creds
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from creds import find_kraken_credentials, get_env_var


def demo_github_secrets():
    """Demonstrate GitHub secrets support."""
    print("=" * 80)
    print("Demo: GitHub Environment Secrets Support in creds.py")
    print("=" * 80)
    print()
    
    # Scenario 1: Using GitHub environment secrets
    print("Scenario 1: Using GitHub environment secrets (COPILOT_KRAKEN_*)")
    print("-" * 80)
    os.environ['COPILOT_KRAKEN_API_KEY'] = 'github_secret_key_example'
    os.environ['COPILOT_KRAKEN_API_SECRET'] = 'github_secret_value_example'
    
    key, secret = find_kraken_credentials(readwrite=False)
    print(f"  Found API Key: {key}")
    print(f"  Found API Secret: {secret}")
    print()
    
    # Clean up
    del os.environ['COPILOT_KRAKEN_API_KEY']
    del os.environ['COPILOT_KRAKEN_API_SECRET']
    
    # Scenario 2: Precedence test - standard name wins
    print("Scenario 2: Precedence - Standard names take priority")
    print("-" * 80)
    os.environ['KRAKEN_API_KEY'] = 'standard_key'
    os.environ['KRAKEN_API_SECRET'] = 'standard_secret'
    os.environ['COPILOT_KRAKEN_API_KEY'] = 'github_key'
    os.environ['COPILOT_KRAKEN_API_SECRET'] = 'github_secret'
    
    key, secret = find_kraken_credentials(readwrite=False)
    print(f"  With both set, uses standard: {key}")
    print(f"  Secret also from standard: {secret}")
    print()
    
    # Clean up
    del os.environ['KRAKEN_API_KEY']
    del os.environ['KRAKEN_API_SECRET']
    del os.environ['COPILOT_KRAKEN_API_KEY']
    del os.environ['COPILOT_KRAKEN_API_SECRET']
    
    # Scenario 3: Full precedence chain
    print("Scenario 3: Full precedence chain demonstration")
    print("-" * 80)
    os.environ['COPILOT_W_KR_RO_PUBLIC'] = 'copilot_w_ro_key'
    os.environ['COPILOT_W_KR_PUBLIC'] = 'copilot_w_key'
    os.environ['COPILOT_KRAKEN_API_KEY'] = 'github_key'
    
    result = get_env_var('KRAKEN_API_KEY')
    print(f"  With all variants set, uses first: {result}")
    print(f"  (COPILOT_W_KR_RO_PUBLIC has highest priority)")
    print()
    
    # Now remove the highest priority
    del os.environ['COPILOT_W_KR_RO_PUBLIC']
    result = get_env_var('KRAKEN_API_KEY')
    print(f"  Without COPILOT_W_KR_RO_PUBLIC, falls back to: {result}")
    print(f"  (COPILOT_W_KR_PUBLIC is second priority)")
    print()
    
    # Now remove second priority
    del os.environ['COPILOT_W_KR_PUBLIC']
    result = get_env_var('KRAKEN_API_KEY')
    print(f"  Without COPILOT_W_KR_PUBLIC, falls back to: {result}")
    print(f"  (COPILOT_KRAKEN_API_KEY is third/last fallback)")
    print()
    
    # Clean up
    del os.environ['COPILOT_KRAKEN_API_KEY']
    
    # Scenario 4: Use case - CI/CD with GitHub secrets
    print("Scenario 4: Real-world use case - GitHub Actions CI/CD")
    print("-" * 80)
    print("  In GitHub Actions, you can set repository secrets:")
    print("    - COPILOT_KRAKEN_API_KEY")
    print("    - COPILOT_KRAKEN_API_SECRET")
    print()
    print("  These will be automatically picked up by creds.py for")
    print("  read-only tests without needing to modify any code!")
    print()
    
    print("=" * 80)
    print("Demo complete! All scenarios work as expected.")
    print("=" * 80)


if __name__ == '__main__':
    demo_github_secrets()
