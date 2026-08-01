from __future__ import annotations

import base64
import binascii
import secrets
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


class CredentialConfigurationError(RuntimeError):
    pass


class CredentialDecryptionError(RuntimeError):
    pass


@dataclass(frozen=True)
class EncryptedValue:
    key_id: str
    nonce: bytes
    ciphertext: bytes


def _keyring() -> dict[str, bytes]:
    raw = str(getattr(settings, "INTEGRATIONS_MASTER_KEYS", ""))
    keyring: dict[str, bytes] = {}
    for entry in raw.split(","):
        key_id, separator, encoded = entry.strip().partition(":")
        if not separator or not key_id or not encoded:
            continue
        try:
            key = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as error:
            raise CredentialConfigurationError(
                "La clave maestra de integraciones es inválida."
            ) from error
        if len(key) != 32:
            raise CredentialConfigurationError("La clave maestra debe tener 256 bits.")
        keyring[key_id] = key
    if not keyring:
        raise CredentialConfigurationError("INTEGRATIONS_MASTER_KEYS es obligatorio.")
    return keyring


def _active_key() -> tuple[str, bytes]:
    keyring = _keyring()
    key_id = str(getattr(settings, "INTEGRATIONS_ACTIVE_KEY_ID", ""))
    if not key_id or key_id not in keyring:
        raise CredentialConfigurationError(
            "INTEGRATIONS_ACTIVE_KEY_ID no está disponible."
        )
    return key_id, keyring[key_id]


def connection_aad(
    *, organization_id: object, provider: str, connection_id: object
) -> bytes:
    return f"lms-integrations|{organization_id}|{provider}|{connection_id}".encode()


def encrypt(*, plaintext: str, aad: bytes) -> EncryptedValue:
    key_id, key = _active_key()
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), aad)
    return EncryptedValue(key_id=key_id, nonce=nonce, ciphertext=ciphertext)


def decrypt(*, encrypted: EncryptedValue, aad: bytes) -> str:
    key = _keyring().get(encrypted.key_id)
    if key is None:
        raise CredentialDecryptionError(
            "La clave de cifrado indicada no está disponible."
        )
    try:
        return (
            AESGCM(key)
            .decrypt(encrypted.nonce, encrypted.ciphertext, aad)
            .decode("utf-8")
        )
    except (InvalidTag, UnicodeDecodeError) as error:
        raise CredentialDecryptionError(
            "No fue posible descifrar la credencial."
        ) from error
