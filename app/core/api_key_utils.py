"""
ATLAS API Key Utilities
-----------------------

Enterprise-grade API key generation and verification.

Design Goals:
- Secure randomness
- Prefix-based identification
- One-way hashing (SHA-256)
- Environment separation (live/test)
- Rotation-friendly
"""

import hashlib
import secrets
from typing import Tuple


# ============================================================
# CONFIG
# ============================================================

DEFAULT_PREFIX = "atlas"
LIVE_ENV_PREFIX = "live"
TEST_ENV_PREFIX = "test"

KEY_LENGTH_BYTES = 32  # 256-bit entropy


# ============================================================
# API KEY GENERATION
# ============================================================

def generate_api_key(environment: str = "live") -> Tuple[str, str]:
    """
    Generates a secure API key.

    Returns:
        (raw_key, key_prefix)

    Example:
        atlas_live_abcd1234....
    """

    if environment not in {"live", "test"}:
        raise ValueError("Environment must be 'live' or 'test'")

    env_prefix = LIVE_ENV_PREFIX if environment == "live" else TEST_ENV_PREFIX

    # Strong cryptographic randomness
    random_part = secrets.token_urlsafe(KEY_LENGTH_BYTES)

    raw_key = f"{DEFAULT_PREFIX}_{env_prefix}_{random_part}"

    # Prefix stored in DB (for quick identification in UI/logs)
    key_prefix = raw_key[:20]

    return raw_key, key_prefix


# ============================================================
# HASHING
# ============================================================

def hash_api_key(api_key: str) -> str:
    """
    One-way SHA-256 hash of API key.
    Only hashed value should be stored in DB.
    """

    if not api_key:
        raise ValueError("API key cannot be empty")

    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


# ============================================================
# VERIFY FUNCTION
# ============================================================

def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """
    Secure comparison of provided API key against stored hash.
    """

    computed_hash = hash_api_key(raw_key)

    # Prevent timing attacks
    return secrets.compare_digest(computed_hash, stored_hash)


# ============================================================
# SAFE ROTATION HELPER
# ============================================================

def rotate_api_key(environment: str = "live") -> Tuple[str, str, str]:
    """
    Generates a new key and its hash.

    Returns:
        (raw_key, key_prefix, hashed_key)
    """

    raw_key, prefix = generate_api_key(environment)
    hashed = hash_api_key(raw_key)

    return raw_key, prefix, hashed