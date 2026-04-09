"""
Auth Service – password hashing and API key encryption/decryption.
"""
from __future__ import annotations

import os
import base64

import bcrypt
from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY environment variable is not set.")
    # Fernet requires a 32-byte url-safe base64-encoded key.
    # Derive one from the secret by padding/truncating and encoding.
    key_bytes = secret.encode()[:32].ljust(32, b"\0")
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


class AuthService:
    """Handles password hashing and symmetric API key encryption."""

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def encrypt_api_key(self, api_key: str) -> bytes:
        return _get_fernet().encrypt(api_key.encode())

    def decrypt_api_key(self, encrypted: bytes) -> str:
        return _get_fernet().decrypt(encrypted).decode()
