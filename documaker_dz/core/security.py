"""Encrypted local storage for API keys using Windows DPAPI or Fernet/PBKDF2."""

from __future__ import annotations

import base64
import ctypes
import ctypes.wintypes
import getpass
import hashlib
import hmac
import json
import os
import platform
import secrets
import sys
from pathlib import Path


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _dpapi_encrypt(raw: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    blob_in = _DATA_BLOB(len(raw), ctypes.create_string_buffer(raw, len(raw)))
    blob_out = _DATA_BLOB()
    if not crypt32.CryptProtectData(ctypes.byref(blob_in), "DocuMakerDZ", None, None, None, 0, ctypes.byref(blob_out)):
        raise OSError("DPAPI CryptProtectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _dpapi_decrypt(enc: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    blob_in = _DATA_BLOB(len(enc), ctypes.create_string_buffer(enc, len(enc)))
    blob_out = _DATA_BLOB()
    if not crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise OSError("DPAPI CryptUnprotectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _machine_secret(salt: bytes) -> bytes:
    identity = f"{getpass.getuser()}::{platform.node()}::DocuMakerDZ-LocalVault".encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", identity, salt, 120_000, dklen=32)


def _xor_stream(data: bytes, key: bytes, nonce: bytes) -> bytes:
    out = bytearray(len(data))
    counter = 0
    pos = 0
    while pos < len(data):
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        chunk = data[pos : pos + len(block)]
        for i, b in enumerate(chunk):
            out[pos + i] = b ^ block[i]
        pos += len(chunk)
        counter += 1
    return bytes(out)


class SecretVault:
    """Stores API keys encrypted at rest in api_keys.enc (DPAPI on Windows, authenticated encryption fallback)."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path

    def load_keys(self) -> dict[str, str]:
        if not self.vault_path.exists():
            return {}
        try:
            wrapper = json.loads(self.vault_path.read_text(encoding="utf-8"))
            mode = wrapper.get("mode")
            payload = base64.b64decode(wrapper["payload"])
            if mode == "dpapi" and sys.platform == "win32":
                plaintext = _dpapi_decrypt(payload)
                return dict(json.loads(plaintext.decode("utf-8")))
            if mode == "fernet":
                from cryptography.fernet import Fernet  # type: ignore

                salt = base64.b64decode(wrapper["salt"])
                fkey = base64.urlsafe_b64encode(_machine_secret(salt))
                plaintext = Fernet(fkey).decrypt(payload)
                return dict(json.loads(plaintext.decode("utf-8")))
            if mode == "hmac_ctr":
                salt = base64.b64decode(wrapper["salt"])
                nonce = base64.b64decode(wrapper["nonce"])
                tag = base64.b64decode(wrapper["tag"])
                key = _machine_secret(salt)
                expected = hmac.new(key, nonce + payload, hashlib.sha256).digest()
                if not hmac.compare_digest(tag, expected):
                    return {}
                plaintext = _xor_stream(payload, key, nonce)
                return dict(json.loads(plaintext.decode("utf-8")))
        except Exception:
            return {}
        return {}

    def save_keys(self, keys: dict[str, str]) -> None:
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        clean = {k: v.strip() for k, v in keys.items() if v and v.strip()}
        raw = json.dumps(clean, ensure_ascii=False).encode("utf-8")

        if sys.platform == "win32":
            try:
                enc = _dpapi_encrypt(raw)
                wrapper = {"mode": "dpapi", "payload": base64.b64encode(enc).decode("ascii")}
                self.vault_path.write_text(json.dumps(wrapper), encoding="utf-8")
                return
            except Exception:
                pass

        salt = secrets.token_bytes(16)
        try:
            from cryptography.fernet import Fernet  # type: ignore

            fkey = base64.urlsafe_b64encode(_machine_secret(salt))
            enc = Fernet(fkey).encrypt(raw)
            wrapper = {
                "mode": "fernet",
                "salt": base64.b64encode(salt).decode("ascii"),
                "payload": base64.b64encode(enc).decode("ascii"),
            }
        except ImportError:
            nonce = secrets.token_bytes(16)
            key = _machine_secret(salt)
            enc = _xor_stream(raw, key, nonce)
            tag = hmac.new(key, nonce + enc, hashlib.sha256).digest()
            wrapper = {
                "mode": "hmac_ctr",
                "salt": base64.b64encode(salt).decode("ascii"),
                "nonce": base64.b64encode(nonce).decode("ascii"),
                "tag": base64.b64encode(tag).decode("ascii"),
                "payload": base64.b64encode(enc).decode("ascii"),
            }

        self.vault_path.write_text(json.dumps(wrapper), encoding="utf-8")
        try:
            os.chmod(self.vault_path, 0o600)
        except Exception:
            pass
