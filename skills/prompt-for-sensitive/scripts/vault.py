"""Encrypted secret vaults for prompt-for-sensitive.

A vault is a JSON file holding AES-256-GCM ciphertext of ONE opaque text value
(an API key, a block of env lines, a PEM, a paragraph of PII - the vault does not
care and never parses it).
The key is split in two halves, and both are needed to decrypt:

  * the TOKEN    - 32 random bytes, given to the caller (printed once as PFS_TOKEN).
  * the MACHINE  - 32 random bytes, protected with Windows DPAPI (bound to this
                   Windows user) and kept in the local key store, not next to the vault.

  key = HKDF-SHA256(token || machine, salt=vault_id, info="pfs-v1")

So a leaked transcript (token) is useless off this user account, a leaked vault
file is useless without the token, and deleting the machine half (revoke / expiry
sweep) destroys the vault for good even if copies of the .enc file exist.

The expiry time is part of the authenticated header (AES-GCM AAD), so it cannot be
edited without the decrypt failing.
"""
import base64
import ctypes
import json
import os
import re
import secrets
import sys
import time
from ctypes import wintypes

VERSION = 1


class VaultError(Exception):
    """Raised for every vault failure. Messages never contain secret values."""


# --------------------------------------------------------------------------- crypto

def _crypto():
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    except ImportError as e:  # pragma: no cover
        raise VaultError(
            f"the 'cryptography' package is missing for {sys.executable} "
            f"(pip install cryptography): {e}")
    return hashes, AESGCM, HKDF


def _derive_key(token: bytes, machine: bytes, vault_id: str) -> bytes:
    hashes, _, HKDF = _crypto()
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=vault_id.encode(),
                info=b"pfs-v1").derive(token + machine)


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# --------------------------------------------------------------------------- DPAPI

class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data: bytes):
    buf = ctypes.create_string_buffer(data, len(data))
    return _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def _dpapi(data: bytes, protect: bool) -> bytes:
    if os.name != "nt":
        # No DPAPI: the key store file is chmod 600 instead (see _write_private).
        return data
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    src, _keep = _blob(data)
    out = _Blob()
    entropy, _keep2 = _blob(b"prompt-for-sensitive")
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    ok = fn(ctypes.byref(src), None, ctypes.byref(entropy), None, None, 0x1,  # UI_FORBIDDEN
            ctypes.byref(out))
    if not ok:
        raise VaultError(f"DPAPI {'protect' if protect else 'unprotect'} failed "
                         f"(error {ctypes.GetLastError()})")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(out.pbData)


# --------------------------------------------------------------------------- key store

def store_dir() -> str:
    base = os.environ.get("PFS_STORE_DIR")
    if not base:
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
        base = os.path.join(root, "pfs", "keys")
    os.makedirs(base, exist_ok=True)
    return base


def _key_path(vault_id: str) -> str:
    return os.path.join(store_dir(), f"{vault_id}.key")


def _meta_path(vault_id: str) -> str:
    return os.path.join(store_dir(), f"{vault_id}.json")


def _write_private(path: str, data: bytes):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)


def _shred(path: str):
    """Overwrite then delete. Best effort: SSDs and sync tools may keep copies."""
    try:
        size = os.path.getsize(path)
        with open(path, "r+b") as f:
            f.write(secrets.token_bytes(size))
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


# --------------------------------------------------------------------------- parsing

def parse_ttl(text: str) -> int:
    m = re.fullmatch(r"\s*(\d+)\s*([smhd]?)\s*", text or "")
    if not m:
        raise VaultError(f"bad ttl {text!r}: use e.g. 900, 30m, 12h, 2d")
    return int(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


# --------------------------------------------------------------------------- vaults

def _header(vault_id, created, expires_at, label):
    return {"v": VERSION, "id": vault_id, "created": created,
            "expires_at": expires_at, "label": label}


def _aad(header) -> bytes:
    return json.dumps(header, sort_keys=True, separators=(",", ":")).encode()


def create_vault(value: str, out_path: str, ttl_seconds: int, label: str = "", now=None):
    """Encrypt `value` into `out_path`. Returns (vault_id, token_str, expires_at).

    `label` is a NON-secret description (shown by `pfs list`), never the value.
    """
    if not isinstance(value, str):
        raise VaultError("value must be text")
    if ttl_seconds <= 0:
        raise VaultError("ttl must be positive")
    _, AESGCM, _ = _crypto()
    now = int(now if now is not None else time.time())
    vault_id = secrets.token_hex(8)
    token = secrets.token_bytes(32)
    machine = secrets.token_bytes(32)
    header = _header(vault_id, now, now + ttl_seconds, label or "")
    nonce = secrets.token_bytes(12)
    ct = AESGCM(_derive_key(token, machine, vault_id)).encrypt(
        nonce, value.encode("utf-8"), _aad(header))

    out_path = os.path.abspath(out_path)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    _write_private(_key_path(vault_id), _dpapi(machine, protect=True))
    _write_private(_meta_path(vault_id), json.dumps(
        {"id": vault_id, "path": out_path, "created": now,
         "expires_at": header["expires_at"], "label": header["label"]}).encode())
    _write_private(out_path, json.dumps(
        {**header, "nonce": _b64e(nonce), "ct": _b64e(ct)}, indent=1).encode())
    return vault_id, "pfs1." + vault_id + "." + _b64e(token), header["expires_at"]


def _parse_token(token: str):
    parts = (token or "").strip().split(".")
    if len(parts) != 3 or parts[0] != "pfs1":
        raise VaultError("bad token format (expected pfs1.<id>.<key>)")
    try:
        raw = _b64d(parts[2])
    except Exception:
        raise VaultError("bad token format (key part is not base64)")
    if len(raw) != 32:
        raise VaultError("bad token format (key part has the wrong length)")
    return parts[1], raw


def open_vault(path: str, token: str, now=None) -> str:
    """Decrypt and return the value. Raises VaultError on any failure."""
    _, AESGCM, _ = _crypto()
    token_id, token_raw = _parse_token(token)
    try:
        with open(path, "rb") as f:
            doc = json.loads(f.read())
    except FileNotFoundError:
        raise VaultError(f"vault file not found: {path} (revoked or swept?)")
    except ValueError:
        raise VaultError(f"vault file is not valid JSON: {path}")
    if doc.get("v") != VERSION:
        raise VaultError(f"unsupported vault version {doc.get('v')!r}")
    vault_id = doc["id"]
    if vault_id != token_id:
        raise VaultError(f"token is for vault {token_id}, file is vault {vault_id}")
    now = int(now if now is not None else time.time())
    if now >= doc["expires_at"]:
        revoke(vault_id)
        raise VaultError(f"vault {vault_id} expired at {_iso(doc['expires_at'])}; it is now shredded")
    try:
        with open(_key_path(vault_id), "rb") as f:
            machine = _dpapi(f.read(), protect=False)
    except FileNotFoundError:
        raise VaultError(f"machine key for vault {vault_id} not found (revoked, swept, "
                         f"or another user/machine)")
    header = _header(vault_id, doc["created"], doc["expires_at"], doc.get("label", ""))
    try:
        plain = AESGCM(_derive_key(token_raw, machine, vault_id)).decrypt(
            _b64d(doc["nonce"]), _b64d(doc["ct"]), _aad(header))
    except Exception:
        raise VaultError("decrypt failed: wrong token, or the vault file was changed")
    return plain.decode("utf-8")


def read_id(target: str) -> str:
    """Accept a vault id or a path to a .enc file."""
    if os.path.isfile(target):
        with open(target, "rb") as f:
            return json.loads(f.read())["id"]
    if re.fullmatch(r"[0-9a-f]{16}", target):
        return target
    raise VaultError(f"{target!r} is not a vault id or an existing vault file")


def revoke(vault_id: str) -> bool:
    """Shred the machine half, the metadata and the vault file. True if anything existed."""
    found = False
    meta = _meta_path(vault_id)
    if os.path.exists(meta):
        found = True
        try:
            with open(meta, "rb") as f:
                enc = json.loads(f.read()).get("path")
            if enc and os.path.exists(enc):
                _shred(enc)
        except (OSError, ValueError):
            pass
    for p in (_key_path(vault_id), meta):
        if os.path.exists(p):
            found = True
            _shred(p)
    return found


def list_vaults():
    out = []
    for name in sorted(os.listdir(store_dir())):
        if name.endswith(".json"):
            try:
                with open(os.path.join(store_dir(), name), "rb") as f:
                    out.append(json.loads(f.read()))
            except (OSError, ValueError):
                pass
    return out


def sweep(now=None):
    """Revoke every expired vault. Also removes orphan key files. Returns revoked ids."""
    now = int(now if now is not None else time.time())
    done = []
    for meta in list_vaults():
        if now >= meta.get("expires_at", 0):
            revoke(meta["id"])
            done.append(meta["id"])
    for name in os.listdir(store_dir()):
        if name.endswith(".key") and not os.path.exists(_meta_path(name[:-4])):
            _shred(os.path.join(store_dir(), name))
            done.append(name[:-4])
    return done


def _iso(ts: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(ts))
