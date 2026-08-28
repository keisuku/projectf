"""Run: uv run --group dev python -m pytest tests

`scripts/sign.py` now has two signing backends: `cryptography` when it imports, and
the stdlib RFC 8032 implementation beside it when it does not. That is the same shape
`tests/unit/test_didkey_backends.py` guards on the verification side, and for the same
reason: the two are not obliged to agree, and a fallback that quietly produced a
different signature would be a correctness change wearing a portability change's
clothes. The signer is the half a caller cannot re-check — a wrong signature is a 403
from a server that will not say which byte was wrong.

Two hand-written RFC vectors pin the backend to the standard but not to *this repo's
other backend*, which is the comparison that catches a divergence. So `cryptography`
is used here exactly as it is used there: as an oracle, asked the same question rather
than consulted through a table of expectations written by hand.

Deterministic seed so a failure is reproducible.
"""

from __future__ import annotations

import importlib.util
import random
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]


def _stdlib_backend():
    """The fallback module, loaded by path: `scripts/` is not an importable package."""
    spec = importlib.util.spec_from_file_location(
        "stdlib_ed25519_under_test", ROOT / "scripts" / "stdlib_ed25519.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_both_signing_backends_produce_identical_signatures() -> None:
    """200 keypairs and messages, signed both ways. Ed25519 signing is deterministic
    (RFC 8032 derives the nonce from the key and message), so agreement here is exact
    equality, not merely 'both verify' — a weaker assertion that would pass against two
    backends drifting in opposite directions."""
    rnd = random.Random(1234)
    stdlib = _stdlib_backend()

    for _ in range(200):
        seed = bytes(rnd.randrange(256) for _ in range(32))
        message = bytes(rnd.randrange(256) for _ in range(rnd.randrange(0, 80)))

        native = Ed25519PrivateKey.from_private_bytes(seed)
        fallback = stdlib.Ed25519PrivateKey.from_private_bytes(seed)

        assert fallback.public_key().public_bytes_raw() == native.public_key().public_bytes_raw(), (
            "the two backends disagree on the public key, so they disagree on the did:key"
        )
        assert fallback.sign(message) == native.sign(message), (
            "the two backends produced different signatures for the same key and message"
        )


def test_the_fallback_rejects_seeds_the_native_backend_rejects() -> None:
    """A seed the native backend refuses must not be silently accepted by the fallback:
    the two lanes have to fail in the same places as well as succeed in the same places."""
    stdlib = _stdlib_backend()
    for bad in (b"", b"\x00" * 31, b"\x00" * 33):
        with pytest.raises(ValueError):
            Ed25519PrivateKey.from_private_bytes(bad)
        with pytest.raises(ValueError):
            stdlib.Ed25519PrivateKey.from_private_bytes(bad)


def test_the_fallback_signs_the_edges_of_the_seed_space() -> None:
    """All-zero and all-0xff seeds are the values a scalar-clamping bug survives on
    random input and dies on here. Compared against the oracle, not asserted by hand."""
    stdlib = _stdlib_backend()
    for seed in (b"\x00" * 32, b"\xff" * 32):
        native = Ed25519PrivateKey.from_private_bytes(seed)
        fallback = stdlib.Ed25519PrivateKey.from_private_bytes(seed)
        assert fallback.public_key().public_bytes_raw() == native.public_key().public_bytes_raw()
        for message in (b"", b"\x00", b"technocore"):
            assert fallback.sign(message) == native.sign(message)
