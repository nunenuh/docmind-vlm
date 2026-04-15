"""
docmind/core/encryption.py

Fernet-based encrypt/decrypt helpers for user API keys.
Uses ENCRYPTION_KEY from application settings.
"""

from cryptography.fernet import Fernet

from docmind.core.config import get_settings


def _get_fernet() -> Fernet:
    """Return a Fernet instance using the ENCRYPTION_KEY from settings."""
    key = get_settings().ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY is not set. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext string. Returns the original plaintext."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
