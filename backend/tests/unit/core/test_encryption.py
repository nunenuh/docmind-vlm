"""Tests for docmind.core.encryption module."""

import pytest
from unittest.mock import patch, MagicMock

from cryptography.fernet import Fernet


class TestEncryption:
    """Tests for encrypt/decrypt functions."""

    @patch("docmind.core.encryption.get_settings")
    def test_encrypt_decrypt_roundtrip(self, mock_settings: MagicMock) -> None:
        key = Fernet.generate_key().decode()
        mock_settings.return_value = MagicMock(ENCRYPTION_KEY=key)

        from docmind.core.encryption import encrypt, decrypt

        original = "sk-test-api-key-12345"
        encrypted = encrypt(original)
        assert encrypted != original
        decrypted = decrypt(encrypted)
        assert decrypted == original

    @patch("docmind.core.encryption.get_settings")
    def test_different_plaintexts_different_ciphertexts(
        self, mock_settings: MagicMock
    ) -> None:
        key = Fernet.generate_key().decode()
        mock_settings.return_value = MagicMock(ENCRYPTION_KEY=key)

        from docmind.core.encryption import encrypt

        c1 = encrypt("key1")
        c2 = encrypt("key2")
        assert c1 != c2

    @patch("docmind.core.encryption.get_settings")
    def test_same_plaintext_different_ciphertexts(
        self, mock_settings: MagicMock
    ) -> None:
        """Fernet uses random IV, so same plaintext produces different ciphertext."""
        key = Fernet.generate_key().decode()
        mock_settings.return_value = MagicMock(ENCRYPTION_KEY=key)

        from docmind.core.encryption import encrypt

        c1 = encrypt("same-key")
        c2 = encrypt("same-key")
        assert c1 != c2  # Different IVs

    @patch("docmind.core.encryption.get_settings")
    def test_empty_string_encryption(self, mock_settings: MagicMock) -> None:
        key = Fernet.generate_key().decode()
        mock_settings.return_value = MagicMock(ENCRYPTION_KEY=key)

        from docmind.core.encryption import encrypt, decrypt

        encrypted = encrypt("")
        assert decrypt(encrypted) == ""

    @patch("docmind.core.encryption.get_settings")
    def test_missing_key_raises(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value = MagicMock(ENCRYPTION_KEY="")

        from docmind.core.encryption import encrypt

        with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
            encrypt("test")

    @patch("docmind.core.encryption.get_settings")
    def test_long_api_key(self, mock_settings: MagicMock) -> None:
        key = Fernet.generate_key().decode()
        mock_settings.return_value = MagicMock(ENCRYPTION_KEY=key)

        from docmind.core.encryption import encrypt, decrypt

        long_key = "sk-" + "a" * 200
        encrypted = encrypt(long_key)
        assert decrypt(encrypted) == long_key

    @patch("docmind.core.encryption.get_settings")
    def test_unicode_plaintext(self, mock_settings: MagicMock) -> None:
        key = Fernet.generate_key().decode()
        mock_settings.return_value = MagicMock(ENCRYPTION_KEY=key)

        from docmind.core.encryption import encrypt, decrypt

        original = "key-with-unicode-chars"
        encrypted = encrypt(original)
        assert decrypt(encrypted) == original

    @patch("docmind.core.encryption.get_settings")
    def test_decrypt_with_wrong_key_raises(self, mock_settings: MagicMock) -> None:
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()

        mock_settings.return_value = MagicMock(ENCRYPTION_KEY=key1)
        from docmind.core.encryption import encrypt, decrypt

        encrypted = encrypt("secret")

        mock_settings.return_value = MagicMock(ENCRYPTION_KEY=key2)
        with pytest.raises(Exception):
            decrypt(encrypted)
