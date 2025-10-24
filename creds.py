"""
Credential helpers for ttslo.

Provides a single place to load a .env file and find Kraken API
credentials from multiple locations with a clear precedence:

1. Explicit environment variables (e.g., KRAKEN_API_KEY)
2. Variables loaded from a .env file
3. Copilot-style or CI secrets (copilot_ prefix, COPILOT_W_*, or COPILOT_KRAKEN_*)

Functions:
- load_env(env_file='.env') -> loads .env into os.environ if not present
 - get_env_var(name) -> checks name, copilot_ prefixed, COPILOT_W_*, and COPILOT_KRAKEN_* variants
- get_env_var(name) -> checks name, copilot_ prefixed, COPILOT_W_*, and COPILOT_KRAKEN_* variants
- find_kraken_credentials(readwrite=False) -> returns (key, secret) tuple
"""
from __future__ import annotations

import os
import sys
from typing import Tuple, Optional


def load_env(env_file: str = '.env') -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ when missing.

    This is intentionally conservative: existing environment variables are
    not overridden.
    """
    if not os.path.exists(env_file):
        return

    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                if key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        print(f"Warning: failed to load env file {env_file}: {e}", file=sys.stderr)


def _check_variants(name: str) -> Tuple[str, ...]:
    """Return possible environment variable variants to check in order.

    For example for 'KRAKEN_API_KEY' returns:
      ('KRAKEN_API_KEY', 'copilot_KRAKEN_API_KEY')
    and also consider COPILOT_W_ prefixed forms externally where applicable.
    """
    variants = [name, f"copilot_{name}"]
    # Support older agent/CI names used in this repo (COPILOT_W_KR_RW_PUBLIC etc.)
    # Map common keys to the COPILOT_W_* equivalents when asked for read/write keys
    if name.endswith('_RW') or name.endswith('_SECRET') or name.endswith('_KEY'):
        # also include upper-case COPILOT_W_* fallback patterns
        variants.append(name.replace('KRAKEN_API_', 'COPILOT_W_KR_'))
    return tuple(variants)
def get_env_var(name: str) -> Optional[str]:
    """Get environment variable checking multiple variants.

    Order of precedence:
      1. Exact name in os.environ
      2. 'COPILOT_' prefixed name in os.environ (uppercase)
      3. 'copilot_' prefixed name in os.environ (lowercase)
    4. COPILOT_W_ prefixed variants (best-effort mapping)
    5. COPILOT_KRAKEN_* fallbacks (legacy/alternate secrets)
      2. 'copilot_' prefixed name in os.environ
      3. COPILOT_W_ prefixed variants (best-effort mapping)
      4. COPILOT_KRAKEN_API_KEY and COPILOT_KRAKEN_API_SECRET (for GitHub secrets)
    """
    # Exact match
    val = os.environ.get(name)
    if val:
        return val

    # Try uppercase COPILOT_ prefix (GitHub Copilot agent style)
    copilot_upper_name = f"COPILOT_{name}"
    val = os.environ.get(copilot_upper_name)
    if val:
        return val

    # Try lowercase copilot_ prefix (legacy style)
    copilot_lower_name = f"copilot_{name}"
    val = os.environ.get(copilot_lower_name)
    if val:
        return val

    # Try some well-known COPILOT_W_* mappings used in this repo
    # e.g., KRAKEN_API_KEY_RW -> COPILOT_W_KR_RW_PUBLIC
    if name == 'KRAKEN_API_KEY_RW':
        return os.environ.get('COPILOT_W_KR_RW_PUBLIC') or os.environ.get('COPILOT_W_KR_RW_KEY')
    if name == 'KRAKEN_API_SECRET_RW':
        return os.environ.get('COPILOT_W_KR_RW_SECRET') or os.environ.get('COPILOT_W_KR_RW_SECRET_KEY')
    if name == 'KRAKEN_API_KEY':
        return (
            os.environ.get('COPILOT_W_KR_RO_PUBLIC')
            or os.environ.get('COPILOT_W_KR_PUBLIC')
            or os.environ.get('COPILOT_KRAKEN_API_KEY')
        )
    if name == 'KRAKEN_API_SECRET':
        return (
            os.environ.get('COPILOT_W_KR_RO_SECRET')
            or os.environ.get('COPILOT_W_KR_SECRET')
            or os.environ.get('COPILOT_KRAKEN_API_SECRET')
        )
        return (os.environ.get('COPILOT_W_KR_RO_PUBLIC') or 
                os.environ.get('COPILOT_W_KR_PUBLIC') or 
                os.environ.get('COPILOT_KRAKEN_API_KEY'))
    if name == 'KRAKEN_API_SECRET':
        return (os.environ.get('COPILOT_W_KR_RO_SECRET') or 
                os.environ.get('COPILOT_W_KR_SECRET') or 
                os.environ.get('COPILOT_KRAKEN_API_SECRET'))

    return None

def find_kraken_credentials(readwrite: bool = False, env_file: str = '.env') -> Tuple[Optional[str], Optional[str]]:
    """Find Kraken credentials.

    If `readwrite` is True, look for read-write keys (KRAKEN_API_KEY_RW / KRAKEN_API_SECRET_RW).
    Otherwise look for read-only keys (KRAKEN_API_KEY / KRAKEN_API_SECRET).

    Returns: (key, secret) or (None, None) if not found.
    """
    # Ensure .env is loaded (but do not override existing env vars)
    load_env(env_file)

    if readwrite:
        key = get_env_var('KRAKEN_API_KEY_RW')
        secret = get_env_var('KRAKEN_API_SECRET_RW')
    else:
        key = get_env_var('KRAKEN_API_KEY')
        secret = get_env_var('KRAKEN_API_SECRET')

    return key, secret
