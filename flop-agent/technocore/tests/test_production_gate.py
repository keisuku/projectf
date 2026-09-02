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
    mod._real_send, mod._real_get = (
        mod._send,
        mod._get,
    )  # for the tests that need the wire
    monkeypatch.setattr(mod, "_send", lambda url: sent.append(url) or 0)
    monkeypatch.setattr(
        mod, "_get", lambda url, timeout=30: (0, {}, b"network cut in tests")
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


# ------------------------------------------------- the wire: redirects and files
#
# Codex review on PR #1: a loopback test server answering `302 Location:
# https://technocore.chat/<the signed path>` would have been followed by
# urllib, turning an ungated test-lane write into a production one. Two real
# local servers prove the redirect is refused and the target never sees it.

import http.server  # noqa: E402
import threading  # noqa: E402


class _Recorder(http.server.BaseHTTPRequestHandler):
    hits: list[str] = []

    def do_GET(self):
        _Recorder.hits.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"landed\n")

    def log_message(self, *a):  # keep pytest output clean
        pass


def _serve(handler):
    srv = http.server.HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture()
def redirecting_pair():
    """(redirector, target): the redirector answers every GET with a 302 to
    the same path on the target; the target records what reaches it."""
    _Recorder.hits.clear()
    target = _serve(_Recorder)
    t_port = target.server_address[1]

    class Redirector(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(getattr(Redirector, "code", 302))
            self.send_header("Location", f"http://127.0.0.1:{t_port}{self.path}")
            self.end_headers()
            self.wfile.write(b"moved\n")

        def log_message(self, *a):
            pass

    redirector = _serve(Redirector)
    yield redirector, target
    redirector.shutdown()
    target.shutdown()


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_send_never_follows_a_redirect(flopdid, redirecting_pair, capsys, code):
    redirector, target = redirecting_pair
    redirector.RequestHandlerClass.code = code
    port = redirector.server_address[1]
    result, _ = _say(flopdid, f"http://127.0.0.1:{port}")
    rc = flopdid._real_send(result["url"])
    assert rc == 1, "a redirect is a refusal, not a success"
    assert _Recorder.hits == [], "the signed path never reached the redirect target"
    err = capsys.readouterr().err
    assert f"HTTP {code}" in err and "redirect" in err.lower()


def test_get_never_follows_a_redirect(flopdid, redirecting_pair):
    redirector, target = redirecting_pair
    port = redirector.server_address[1]
    status, headers, body = flopdid._real_get(f"http://127.0.0.1:{port}/r/x/export")
    assert status == 302 and "location" in headers
    assert _Recorder.hits == []


def test_proof_log_is_forced_to_0600_even_if_it_already_exists(flopdid):
    flopdid.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    flopdid.PROOF_LOG.write_text('{"restored": true}\n')
    flopdid.PROOF_LOG.chmod(0o644)
    flopdid._proof_append({"ts": "t", "outcome": "test"})
    assert oct(flopdid.PROOF_LOG.stat().st_mode & 0o777) == "0o600"
    lines = flopdid.PROOF_LOG.read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[1])["outcome"] == "test"


def test_export_snapshot_is_the_exact_bytes_received(flopdid, monkeypatch):
    # Bytes that text mode or a decode-with-replace would alter: a bare LF the
    # platform might translate, and an invalid UTF-8 byte in the middle.
    raw = b'{"seq":1,"text":"a\\u00e9"}\n{"seq":2,"bad":"\xff"}\n'
    calls = []

    def fake_get(url, timeout=30):
        calls.append(url)
        if url.endswith("/export"):
            return 200, {"x-room-generation": "7"}, raw
        return 200, {}, b'{"generation": 7, "last_seq": 2, "count": 2, "messages": []}'

    monkeypatch.setattr(flopdid, "_get", fake_get)
    result, _ = _say(flopdid, PROD)
    out = flopdid._snapshot_after_send(result, PROD, "20990101T000000Z")
    path = Path(out["export"]["file"])
    assert path.read_bytes() == raw
    assert out["export"]["sha256"] == __import__("hashlib").sha256(raw).hexdigest()
    assert out["export"]["generation"] == "7" and out["export"]["lines"] == 2
    assert out["export"]["bytes"] == len(raw)
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert out["room"] == {"generation": 7, "last_seq": 2, "count": 2}


# ------------------------------------------------ Codex review round 2 on PR #1


@pytest.mark.parametrize(
    "placeholder", ["<name of the approver>", " <name of the approver> ", "<someone>"]
)
def test_the_printed_placeholder_approver_is_refused(
    flopdid, tmp_path, monkeypatch, placeholder
):
    """The `approval` command prints a template on purpose; an unedited one
    must not satisfy the approval factor."""
    result, raw = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result, approved_by=placeholder)
    _tty(monkeypatch, flopdid, "d-gate-test")
    code = _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
    assert code == flopdid.EXIT_GATE_REFUSED and flopdid._test_sent == []
    assert "placeholder" in _proof(flopdid)[-1]["reason"]
    assert Path(path).exists()


def test_the_approval_command_output_is_refused_until_edited(flopdid, tmp_path, capsys):
    args = argparse.Namespace(
        kind="say", target="d-gate-test", body="an unedited template", did=None
    )
    flopdid.cmd_approval(args)
    doc = json.loads(capsys.readouterr().out)
    assert doc["approved_by"] == flopdid.APPROVER_PLACEHOLDER
    result = flopdid.build_say(
        bytes.fromhex(RFC_SEED), "d-gate-test", "an unedited template", PROD
    )
    verdict = flopdid._load_approval(str(_write(tmp_path, doc)), result, result["did"])
    assert isinstance(verdict, str) and "placeholder" in verdict
    doc["approved_by"] = "a real person"
    verdict = flopdid._load_approval(str(_write(tmp_path, doc)), result, result["did"])
    assert isinstance(verdict, dict)


def _write(tmp_path, doc):
    p = tmp_path / "template.json"
    p.write_text(json.dumps(doc))
    return p


def test_two_snapshots_in_the_same_second_do_not_collide(flopdid, monkeypatch):
    raw1, raw2 = b'{"seq":1}\n', b'{"seq":1}\n{"seq":2}\n'
    bodies = iter([raw1, raw2])

    def fake_get(url, timeout=30):
        if url.endswith("/export"):
            return 200, {"x-room-generation": "1"}, next(bodies)
        return 200, {}, b'{"generation": 1, "last_seq": 2, "count": 2, "messages": []}'

    monkeypatch.setattr(flopdid, "_get", fake_get)
    first, _ = _say(flopdid, PROD)
    second, _ = _say(flopdid, PROD)
    assert first["nonce"] != second["nonce"]
    out1 = flopdid._snapshot_after_send(first, PROD, "20990101T000000Z")
    out2 = flopdid._snapshot_after_send(second, PROD, "20990101T000000Z")
    f1, f2 = Path(out1["export"]["file"]), Path(out2["export"]["file"])
    assert (
        f1 != f2 and str(first["nonce"]) in f1.name and str(second["nonce"]) in f2.name
    )
    assert f1.read_bytes() == raw1 and f2.read_bytes() == raw2, (
        "the first snapshot survives"
    )


def test_an_existing_snapshot_is_never_overwritten(flopdid, monkeypatch):
    monkeypatch.setattr(
        flopdid,
        "_get",
        lambda url, timeout=30: (200, {"x-room-generation": "1"}, b"x\n"),
    )
    result, _ = _say(flopdid, PROD)
    out = flopdid._snapshot_after_send(result, PROD, "20990101T000000Z")
    with pytest.raises(FileExistsError):
        flopdid._snapshot_after_send(result, PROD, "20990101T000000Z")
    assert Path(out["export"]["file"]).read_bytes() == b"x\n"


@pytest.mark.parametrize("cmd", ["checkin", "say"])
def test_the_raw_body_reaches_the_gate_from_every_room_command(
    flopdid, monkeypatch, cmd
):
    """The confirmation screen and proof log show the body as typed AND as
    swept; a command that forwarded only the swept form would hide exactly the
    transformation the review exists to expose."""
    seen = {}

    def fake_emit(result, args, raw_body=None):
        seen["raw"], seen["clean"] = raw_body, result["text"]

    monkeypatch.setattr(flopdid, "_emit", fake_emit)
    typed = "  a body with​zero-width and trailing spaces   "
    if cmd == "checkin":
        flopdid.cmd_checkin(
            argparse.Namespace(text=typed, room="d-gate-test", base=PROD)
        )
    else:
        flopdid.cmd_say(argparse.Namespace(room="d-gate-test", text=typed, base=PROD))
    assert seen["raw"] == typed
    assert seen["clean"] == "a body with zero-width and trailing spaces"
    assert seen["raw"] != seen["clean"]
