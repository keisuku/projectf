"""The production write gate in flopdid.py (HANDOFF.md §2.5, §5.4).

What is being proven: `--fetch` reaches a non-loopback host only when the
`--production` flag, a matching one-time approval file, and an interactive TTY
confirmation are all present; nothing in the environment can substitute for
any of them; the approval is consumed on send; every attempt lands in
proof.log; and the loopback test lane is unaffected.

The network is never touched: `_send` and `_get` are replaced with recorders.
The key is an RFC 8032 test vector supplied through $FLOP_DID_SEED, so the
permanent identity is never loaded.

Run:  python3 -m pytest flop-agent/technocore/tests -q
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import types
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
RFC_SEED = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
PROD = "https://technocore.chat"
LOCAL = "http://127.0.0.1:8099"


@pytest.fixture()
def flopdid(tmp_path, monkeypatch):
    """A fresh import bound to a throwaway identity home, with the network cut."""
    monkeypatch.setenv("FLOP_AGENT_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("FLOP_DID_SEED", RFC_SEED)
    monkeypatch.setenv("FLOP_FORCE_PURE", "1")  # no compiled backend needed anywhere
    sys.path.insert(0, str(SCRIPTS))
    sys.modules.pop("flopdid", None)
    mod = importlib.import_module("flopdid")
    mod.PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    (mod.PUBLIC_DIR / "did.txt").write_text(
        mod.did_from_pubkey(mod.PUBKEY(bytes.fromhex(RFC_SEED))) + "\n"
    )
    sent: list[str] = []
    monkeypatch.setattr(mod, "_send", lambda url: sent.append(url) or 0)
    monkeypatch.setattr(
        mod, "_get", lambda url, timeout=30: (0, {}, "network cut in tests")
    )
    mod._test_sent = sent
    yield mod
    sys.modules.pop("flopdid", None)


def _args(base, **kw):
    ns = argparse.Namespace(base=base, fetch=True)
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def _say(mod, base, text="a body long enough to pass the length floor"):
    return mod.build_say(bytes.fromhex(RFC_SEED), "d-gate-test", text, base), text


def _approval(mod, tmp_path, result, **override):
    doc = {
        "kind": "say",
        "target": result["room"],
        "did": result["did"],
        "sha256": mod.body_sha256(result["text"]),
        "approved_by": "test commander",
    }
    doc.update(override)
    p = tmp_path / "approval.json"
    p.write_text(json.dumps(doc))
    return str(p)


def _tty(monkeypatch, mod, typed):
    class Tty:
        def isatty(self):
            return True

        def write(self, s):
            return len(s)

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdin", Tty())
    monkeypatch.setattr(sys, "stdout", Tty())
    monkeypatch.setattr("builtins.input", lambda prompt="": typed)


def _proof(mod):
    if not mod.PROOF_LOG.exists():
        return []
    return [json.loads(line) for line in mod.PROOF_LOG.read_text().splitlines()]


def _emit_code(mod, result, args, raw):
    with pytest.raises(SystemExit) as exc:
        mod._emit(result, args, raw_body=raw)
    return exc.value.code


# ----------------------------------------------------------------- loopback lane


def test_loopback_fetch_is_not_gated(flopdid):
    result, raw = _say(flopdid, LOCAL)
    assert _emit_code(flopdid, result, _args(LOCAL), raw) == 0
    assert flopdid._test_sent == [result["url"]]
    assert _proof(flopdid) == []  # the test lane leaves no production proof


@pytest.mark.parametrize(
    "base", ["http://localhost:8080", "http://[::1]:8080", "http://127.0.0.1"]
)
def test_loopback_detection(flopdid, base):
    assert flopdid.is_loopback(base)


@pytest.mark.parametrize(
    "base",
    [
        PROD,
        "http://10.0.0.5:8080",
        "https://127.0.0.1.nip.io",
        "https://localhost.example",
    ],
)
def test_non_loopback_detection(flopdid, base):
    assert not flopdid.is_loopback(base)


# ------------------------------------------------------------- the three factors


def test_refused_without_production_flag(flopdid):
    result, raw = _say(flopdid, PROD)
    assert _emit_code(flopdid, result, _args(PROD), raw) == flopdid.EXIT_GATE_REFUSED
    assert flopdid._test_sent == []
    (entry,) = _proof(flopdid)
    assert entry["outcome"] == "gate-refused" and "--production" in entry["reason"]
    assert entry["canonical_hex"] == result["canonical"].encode().hex()


def test_refused_without_approval_file(flopdid, monkeypatch):
    result, raw = _say(flopdid, PROD)
    _tty(monkeypatch, flopdid, "d-gate-test")
    code = _emit_code(flopdid, result, _args(PROD, production=True), raw)
    assert code == flopdid.EXIT_GATE_REFUSED and flopdid._test_sent == []


def test_refused_when_approval_hash_differs(flopdid, tmp_path, monkeypatch):
    result, raw = _say(flopdid, PROD)
    other = flopdid.body_sha256("a different body that was never approved")
    path = _approval(flopdid, tmp_path, result, sha256=other)
    _tty(monkeypatch, flopdid, "d-gate-test")
    code = _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
    assert code == flopdid.EXIT_GATE_REFUSED and flopdid._test_sent == []
    assert Path(path).exists(), "a refused approval is not consumed"
    assert "sha256" in _proof(flopdid)[-1]["reason"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("target", "d-some-other-room"),
        ("kind", "set"),
        ("did", "did:key:z6MkhCvnKQ9E9eZxK7wcS2FJ1Diir2rgfTkaYbMnczha9QDU"),
        ("approved_by", ""),
        ("expires", "2000-01-01T00:00:00Z"),
        ("expires", "yesterday"),
    ],
)
def test_refused_when_any_approval_field_is_off(
    flopdid, tmp_path, monkeypatch, field, value
):
    result, raw = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result, **{field: value})
    _tty(monkeypatch, flopdid, "d-gate-test")
    code = _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
    assert code == flopdid.EXIT_GATE_REFUSED and flopdid._test_sent == []


def test_refused_without_a_tty(flopdid, tmp_path, monkeypatch):
    result, raw = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result)
    monkeypatch.setattr(
        sys, "stdin", type("NoTty", (), {"isatty": lambda self: False})()
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": "d-gate-test")
    code = _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
    assert code == flopdid.EXIT_GATE_REFUSED and flopdid._test_sent == []
    assert Path(path).exists()
    assert "TTY" in _proof(flopdid)[-1]["reason"]


def test_refused_when_confirmation_does_not_match(flopdid, tmp_path, monkeypatch):
    result, raw = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result)
    _tty(monkeypatch, flopdid, "yes")
    code = _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
    assert code == flopdid.EXIT_GATE_REFUSED and flopdid._test_sent == []
    assert Path(path).exists(), "an aborted confirmation does not consume the approval"


# ------------------------------------------------------------------ the happy path


def test_all_three_factors_send_once_and_consume(flopdid, tmp_path, monkeypatch):
    result, raw = _say(
        flopdid, PROD, "  raw body with​zero-width and trailing spaces   "
    )
    assert result["text"] == "raw body with zero-width and trailing spaces"
    path = _approval(flopdid, tmp_path, result, expires="2099-01-01T00:00:00Z")
    _tty(monkeypatch, flopdid, "d-gate-test")
    code = _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
    assert code == 0
    assert flopdid._test_sent == [result["url"]]
    assert not Path(path).exists()
    used = [p for p in tmp_path.iterdir() if p.name.startswith("approval.json.used-")]
    assert len(used) == 1
    (entry,) = _proof(flopdid)
    assert entry["outcome"] == "accepted"
    assert entry["body_raw"] == raw and entry["body_clean"] == result["text"]
    assert entry["body_sha256"] == flopdid.body_sha256(result["text"])
    assert entry["canonical"] == result["canonical"]
    assert entry["canonical_hex"] == result["canonical"].encode("utf-8").hex()
    assert entry["nonce"] == result["nonce"] and entry["sig"] == result["sig"]
    assert entry["approval"]["consumed_as"] == str(used[0])
    # the snapshot was attempted even though the network is cut, and said so
    assert entry["after"]["export"]["status"] == 0
    assert oct(flopdid.PROOF_LOG.stat().st_mode & 0o777) == "0o600"


def test_a_consumed_approval_cannot_be_reused(flopdid, tmp_path, monkeypatch):
    result, raw = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result)
    _tty(monkeypatch, flopdid, "d-gate-test")
    assert (
        _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
        == 0
    )
    # a second build of the same body draws a new nonce; the old approval file is gone
    result2, raw2 = _say(flopdid, PROD)
    code = _emit_code(
        flopdid, result2, _args(PROD, production=True, approval=path), raw2
    )
    assert code == flopdid.EXIT_GATE_REFUSED
    assert flopdid._test_sent == [result["url"]]


def test_server_refusal_and_transport_failure_are_recorded(
    flopdid, tmp_path, monkeypatch
):
    for code_from_send, outcome in ((1, "server-refused"), (2, "not-sent")):
        result, raw = _say(flopdid, PROD)
        path = _approval(flopdid, tmp_path, result)
        _tty(monkeypatch, flopdid, "d-gate-test")
        monkeypatch.setattr(flopdid, "_send", lambda url, c=code_from_send: c)
        assert (
            _emit_code(
                flopdid, result, _args(PROD, production=True, approval=path), raw
            )
            == code_from_send
        )
        assert _proof(flopdid)[-1]["outcome"] == outcome
        assert "after" not in _proof(flopdid)[-1]
        assert not Path(path).exists(), "consumed on send, whatever the server answered"


# ------------------------------------------------------------ no environment bypass


def test_environment_cannot_relax_the_gate(flopdid, tmp_path, monkeypatch):
    for name in (
        "FLOP_PRODUCTION",
        "FLOP_APPROVED",
        "FLOP_SKIP_GATE",
        "FLOP_FORCE_WRITE",
        "TECHNOCORE_PRODUCTION",
        "CI",
        "FLOP_NO_TTY",
        "FLOP_APPROVAL",
    ):
        monkeypatch.setenv(name, "1")
    monkeypatch.setenv("FLOP_APPROVAL", str(tmp_path / "approval.json"))
    result, raw = _say(flopdid, PROD)
    _approval(flopdid, tmp_path, result)
    _tty(monkeypatch, flopdid, "d-gate-test")
    # flag missing: refused regardless of the environment
    assert _emit_code(flopdid, result, _args(PROD), raw) == flopdid.EXIT_GATE_REFUSED
    # approval path missing from the command line: refused even though $FLOP_APPROVAL points at one
    assert (
        _emit_code(flopdid, result, _args(PROD, production=True), raw)
        == flopdid.EXIT_GATE_REFUSED
    )
    assert flopdid._test_sent == []


def test_gate_reads_no_environment_variables():
    """The gate's own code must not consult os.environ — a structural check, so a
    future 'convenience' override cannot slip in without failing this test."""
    import inspect

    import flopdid

    gate = "".join(
        inspect.getsource(f)
        for f in (
            flopdid.production_fetch,
            flopdid._load_approval,
            flopdid._consume_approval,
            flopdid.is_loopback,
            flopdid._emit,
        )
    )
    assert "environ" not in gate and "getenv" not in gate


# --------------------------------------------------------- ownership namespaces


def test_ownership_note_needs_explicit_ownership_true(flopdid, tmp_path, monkeypatch):
    seed = bytes.fromhex(RFC_SEED)
    result = flopdid.build_set(
        seed, "room-owners", "d-gate-test", result_did(flopdid), PROD, if_absent=True
    )
    doc = {
        "kind": "set",
        "target": "room-owners/d-gate-test",
        "did": result["did"],
        "sha256": flopdid.body_sha256(result["value"]),
        "approved_by": "test commander",
    }
    path = tmp_path / "own.json"
    path.write_text(json.dumps(doc))
    _tty(monkeypatch, flopdid, "room-owners/d-gate-test")
    args = _args(PROD, production=True, approval=str(path))
    assert (
        _emit_code(flopdid, result, args, result["value"]) == flopdid.EXIT_GATE_REFUSED
    )
    assert "ownership" in _proof(flopdid)[-1]["reason"]
    doc["ownership"] = True
    path.write_text(json.dumps(doc))
    result = flopdid.build_set(
        seed, "room-owners", "d-gate-test", result_did(flopdid), PROD, if_absent=True
    )
    assert _emit_code(flopdid, result, args, result["value"]) == 0
    assert flopdid._test_sent == [result["url"]]


def result_did(mod):
    return mod.did_from_pubkey(mod.PUBKEY(bytes.fromhex(RFC_SEED)))


# ------------------------------------------------ self-verification before emit


def _fake_module(monkeypatch, name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


def test_a_broken_verifier_build_is_not_a_bad_signature(flopdid, monkeypatch):
    """cryptography without _cffi_backend dies in a pyo3 panic that is not an
    Exception. That is an absent verifier, not a verdict on our key."""

    class PanicException(BaseException):
        pass

    class Ed25519PublicKey:
        @staticmethod
        def from_public_bytes(raw):
            raise PanicException("Python API call failed")

    monkeypatch.setitem(sys.modules, "nacl", None)  # not installed
    monkeypatch.setitem(sys.modules, "nacl.signing", None)
    monkeypatch.setitem(sys.modules, "nacl.exceptions", None)
    for name in (
        "cryptography",
        "cryptography.hazmat",
        "cryptography.hazmat.primitives",
        "cryptography.hazmat.primitives.asymmetric",
    ):
        _fake_module(monkeypatch, name)
    _fake_module(
        monkeypatch,
        "cryptography.exceptions",
        InvalidSignature=type("InvalidSignature", (Exception,), {}),
    )
    _fake_module(
        monkeypatch,
        "cryptography.hazmat.primitives.asymmetric.ed25519",
        Ed25519PublicKey=Ed25519PublicKey,
    )
    assert flopdid._verifiers() == []
    sig = flopdid.sig_b64(bytes.fromhex(RFC_SEED), "lobby|1|still emits")
    assert len(sig) == 86


def test_a_working_verifier_that_rejects_our_signature_refuses_the_emit(
    flopdid, monkeypatch
):
    class BadSignatureError(Exception):
        pass

    class VerifyKey:
        def __init__(self, pub):
            self.pub = pub

        def verify(self, msg, sig):
            if (self.pub, msg, sig) == (flopdid._RFC_PK, b"", flopdid._RFC_SIG):
                return msg  # passes the probe
            raise BadSignatureError("Signature was forged or corrupt")

    _fake_module(monkeypatch, "nacl")
    _fake_module(monkeypatch, "nacl.signing", VerifyKey=VerifyKey)
    _fake_module(monkeypatch, "nacl.exceptions", BadSignatureError=BadSignatureError)
    assert [v[0] for v in flopdid._verifiers()] == ["pynacl"] or [
        v[0] for v in flopdid._verifiers()
    ][0] == "pynacl"
    with pytest.raises(SystemExit) as exc:
        flopdid.sig_b64(bytes.fromhex(RFC_SEED), "lobby|1|must be refused")
    assert "REFUSING TO EMIT" in str(exc.value) and "pynacl" in str(exc.value)


def test_real_verifier_accepts_our_own_signature(flopdid):
    if not flopdid._verifiers():
        pytest.skip("no working Ed25519 verifier in this interpreter")
    assert len(flopdid.sig_b64(bytes.fromhex(RFC_SEED), "lobby|1|self-check")) == 86


# ------------------------------------------------------------ the approval helper


def test_approval_command_matches_what_the_gate_checks(flopdid, capsys):
    args = argparse.Namespace(
        kind="say", target="d-gate-test", body="  body​with sweepable bits  ", did=None
    )
    flopdid.cmd_approval(args)
    doc = json.loads(capsys.readouterr().out)
    result, _ = _say(flopdid, PROD, "  body​with sweepable bits  ")
    assert doc["sha256"] == flopdid.body_sha256(result["text"])
    assert doc["body_swept"] == result["text"]
    assert doc["did"] == result["did"] and doc["target"] == "d-gate-test"
    assert doc["approved_by"].startswith("<"), (
        "the human fills this in; the tool never does"
    )
