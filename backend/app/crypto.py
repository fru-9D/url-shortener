"""
Email encryption at rest and HMAC search-hash utilities.

Every email address is stored in two columns:
  email_ciphertext  — AES-256-GCM encrypted, DEK sealed by AWS KMS
  email_search_hash — HMAC-SHA256 over lowercased email, used for lookups/uniqueness

In local dev (KMS_KEY_ARN is empty), a local 256-bit key is derived from SECRET_KEY
so the stack runs without real AWS credentials.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

# ── HMAC search hash ──────────────────────────────────────────────────────────

def email_search_hash(email: str) -> str:
    """Return HMAC-SHA256 hex of lowercased email, keyed by HMAC_KEY."""
    key = settings.hmac_key.encode()
    return hmac.new(key, email.lower().encode(), hashlib.sha256).hexdigest()


# ── KMS / local key resolution ────────────────────────────────────────────────

def _get_local_dek() -> bytes:
    """Derive a 32-byte local DEK from SECRET_KEY for dev use."""
    return hashlib.sha256(settings.secret_key.encode()).digest()


def _kms_generate_dek() -> tuple[bytes, bytes]:
    """
    Ask KMS to generate a data-encryption key.
    Returns (plaintext_dek, ciphertext_dek).
    ciphertext_dek is stored alongside the ciphertext in the DB.
    """
    import boto3
    client = boto3.client("kms", region_name=settings.aws_region)
    resp = client.generate_data_key(KeyId=settings.kms_key_arn, KeySpec="AES_256")
    return resp["Plaintext"], resp["CiphertextBlob"]


def _kms_decrypt_dek(ciphertext_dek: bytes) -> bytes:
    import boto3
    client = boto3.client("kms", region_name=settings.aws_region)
    resp = client.decrypt(CiphertextBlob=ciphertext_dek)
    return resp["Plaintext"]  # type: ignore[return-value]


# ── Encryption / decryption ───────────────────────────────────────────────────

def encrypt_email(email: str) -> str:
    """
    Encrypt email with AES-256-GCM.
    Returns a JSON string: {"ct": <b64>, "nonce": <b64>, "kms_ct": <b64>|null}
    kms_ct is null in dev (no KMS).
    """
    plaintext = email.lower().encode()

    if settings.kms_key_arn:
        dek, kms_ct = _kms_generate_dek()
        kms_ct_b64: str | None = base64.b64encode(kms_ct).decode()
    else:
        dek = _get_local_dek()
        kms_ct_b64 = None

    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(dek)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    payload: dict[str, Any] = {
        "ct": base64.b64encode(ciphertext).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "kms_ct": kms_ct_b64,
    }
    return json.dumps(payload)


def decrypt_email(email_ciphertext: str) -> str:
    """Decrypt an email_ciphertext string back to plaintext email."""
    payload = json.loads(email_ciphertext)
    ciphertext = base64.b64decode(payload["ct"])
    nonce = base64.b64decode(payload["nonce"])
    kms_ct_b64 = payload.get("kms_ct")

    if kms_ct_b64 and settings.kms_key_arn:
        dek = _kms_decrypt_dek(base64.b64decode(kms_ct_b64))
    else:
        dek = _get_local_dek()

    aesgcm = AESGCM(dek)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


# ── Token helpers ─────────────────────────────────────────────────────────────

def generate_token() -> tuple[str, str]:
    """
    Generate a cryptographically random URL-safe token and its SHA-256 hash.
    Returns (raw_token, token_hash).
    The raw token is emailed; only the hash is stored.
    """
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()
