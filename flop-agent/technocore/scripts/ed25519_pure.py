"""Pure-Python Ed25519 (RFC 8032) — the no-dependency fallback.

Why this exists: `flopdid.py` must run on a phone, a fresh laptop, or any box
where `pip install cryptography` is not available or not wanted. The permanent
DID seed should be generatable and usable *anywhere*, with nothing to install.

When `cryptography` IS importable, flopdid.py uses it instead — it is faster and
it is what the upstream `scripts/sign.py` uses. Both paths are cross-checked
against each other and against upstream by `selftest.py`.

This is the well-known RFC 8032 reference construction (SHA-512, curve25519 in
Edwards form). It is written for auditability rather than speed: signing takes
on the order of a second. That is fine for a tool that signs a handful of
messages a day, and the readability is worth more here than the milliseconds,
because this code touches the private key.

Constant-time it is not. It is a signing utility for a key held on the machine
that runs it, not a server-side verifier exposed to attacker-chosen input.
"""

from __future__ import annotations

import hashlib

# Curve constants (RFC 8032 §5.1)
Q = 2**255 - 19
L = 2**252 + 27742317777372353535851937790883648493


def _h(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()


def _inv(x: int) -> int:
    return pow(x, Q - 2, Q)


D = -121665 * _inv(121666) % Q
I = pow(2, (Q - 1) // 4, Q)


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(D * y * y + 1)
    x = pow(xx, (Q + 3) // 8, Q)
    if (x * x - xx) % Q != 0:
        x = (x * I) % Q
    if x % 2 != 0:
        x = Q - x
    return x


_BY = 4 * _inv(5)
_BX = _xrecover(_BY)
B = (_BX % Q, _BY % Q)


def _edwards_add(p: tuple[int, int], q: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = p
    x2, y2 = q
    k = D * x1 * x2 * y1 * y2
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + k)
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - k)
    return (x3 % Q, y3 % Q)


def _scalarmult(p: tuple[int, int], e: int) -> tuple[int, int]:
    """Double-and-add, iterative: recursion would be 256 frames deep."""
    result = (0, 1)  # neutral element
    addend = p
    while e > 0:
        if e & 1:
            result = _edwards_add(result, addend)
        addend = _edwards_add(addend, addend)
        e >>= 1
    return result


def _encode_point(p: tuple[int, int]) -> bytes:
    x, y = p
    return ((y & ~(1 << 255)) | ((x & 1) << 255)).to_bytes(32, "little")


def _clamp(h: bytes) -> int:
    """RFC 8032 §5.1.5: clear the low 3 bits and bit 255, set bit 254."""
    a = int.from_bytes(h[:32], "little")
    return (a & ((1 << 254) - 8)) | (1 << 254)


def public_key_from_seed(seed: bytes) -> bytes:
    """The 32-byte Ed25519 public key for a 32-byte seed."""
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be exactly 32 bytes")
    a = _clamp(_h(seed))
    return _encode_point(_scalarmult(B, a))


def sign(seed: bytes, message: bytes) -> bytes:
    """The 64-byte Ed25519 signature of `message` under `seed`."""
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be exactly 32 bytes")
    h = _h(seed)
    a = _clamp(h)
    pk = _encode_point(_scalarmult(B, a))
    r = int.from_bytes(_h(h[32:] + message), "little") % L
    big_r = _encode_point(_scalarmult(B, r))
    k = int.from_bytes(_h(big_r + pk + message), "little") % L
    s = (r + k * a) % L
    return big_r + s.to_bytes(32, "little")
