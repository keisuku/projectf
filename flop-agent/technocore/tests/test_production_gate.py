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
import re
import sys
import time
import types
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
RFC_SEED = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
PROD = "https://technocore.chat"
PROD_HOST = "technocore.chat"
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


def _future(hours=48):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + hours * 3600))


def _approval(mod, tmp_path, result, **override):
    doc = {
        "kind": "say",
        "target": result["room"],
        "did": result["did"],
        "sha256": mod.body_sha256(result["text"]),
        "host": "technocore.chat",
        "approved_by": "test commander",
        "expires": _future(),
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


def test_a_non_tty_run_prints_no_signature_and_no_nonce(
    flopdid, tmp_path, monkeypatch, capsys
):
    """Issue #4 item 1: the review screen is for a person about to confirm. With
    no terminal there is nobody to read it, and printing it anyway writes the
    nonce and the signature — together a replayable capability — into whatever
    pipe or cron mail captured the run."""
    result, raw = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result)
    monkeypatch.setattr(
        sys, "stdin", type("NoTty", (), {"isatty": lambda self: False})()
    )
    code = _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
    assert code == flopdid.EXIT_GATE_REFUSED and flopdid._test_sent == []
    out = capsys.readouterr().out
    assert result["sig"] not in out
    assert not re.search(r"[A-Za-z0-9_-]{86}", out), (
        "an 86-char signature reached stdout"
    )
    assert str(result["nonce"]) not in out and "nonce" not in out.lower()
    assert result["did"] not in out
    assert Path(path).exists(), "a refused run leaves the approval unconsumed"


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
    entry, snapshot = _proof(flopdid)
    assert entry["outcome"] == "accepted"
    assert entry["body_raw"] == raw and entry["body_clean"] == result["text"]
    assert entry["body_sha256"] == flopdid.body_sha256(result["text"])
    assert entry["canonical"] == result["canonical"]
    assert entry["canonical_hex"] == result["canonical"].encode("utf-8").hex()
    assert entry["nonce"] == result["nonce"] and entry["sig"] == result["sig"]
    assert entry["approval"]["consumed_as"] == str(used[0])
    assert entry["dispatched_at"] > 0
    # the snapshot is its own line, keyed by nonce, and was attempted even
    # though the network is cut
    assert snapshot["record"] == "snapshot" and snapshot["nonce"] == result["nonce"]
    assert snapshot["after"]["export"]["status"] == 0
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


def test_technocore_base_cannot_redirect_a_production_write(flopdid, monkeypatch):
    """Issue #4 item 2: $TECHNOCORE_BASE points reads and the loopback test lane
    at a local server. It must not be able to point an approved signed URL — a
    replayable capability — at a host nobody approved."""
    monkeypatch.setenv("TECHNOCORE_BASE", "https://evil.example.test")
    monkeypatch.setattr(
        sys, "argv", ["flopdid.py", "say", "d-gate-test", "a body", "--production"]
    )
    seen = {}
    monkeypatch.setattr(flopdid, "cmd_say", lambda args: seen.update(base=args.base))
    flopdid.main()
    assert seen["base"] == flopdid.DEFAULT_BASE

    # …while --base still names the destination explicitly, and a run that is not
    # a production write keeps the convenience.
    monkeypatch.setattr(
        sys,
        "argv",
        ["flopdid.py", "say", "d-gate-test", "a body", "--production", "--base", LOCAL],
    )
    flopdid.main()
    assert seen["base"] == LOCAL
    monkeypatch.setattr(sys, "argv", ["flopdid.py", "say", "d-gate-test", "a body"])
    flopdid.main()
    assert seen["base"] == "https://evil.example.test"


def test_an_approval_for_another_host_is_refused(flopdid, tmp_path, monkeypatch):
    """The approval authorises a body *to a service*. A file approved for
    technocore.chat does not authorise the same body somewhere else."""
    other = "https://staging.example.test"
    result, raw = _say(flopdid, other)
    path = _approval(flopdid, tmp_path, result)  # host: technocore.chat
    _tty(monkeypatch, flopdid, "d-gate-test")
    code = _emit_code(
        flopdid, result, _args(other, production=True, approval=path), raw
    )
    assert code == flopdid.EXIT_GATE_REFUSED and flopdid._test_sent == []
    reason = _proof(flopdid)[-1]["reason"]
    assert "'host'" in reason and "staging.example.test" in reason
    assert Path(path).exists()

    # the same write, approved for the host it is actually addressed to, passes
    path = _approval(flopdid, tmp_path, result, host="staging.example.test")
    assert (
        _emit_code(flopdid, result, _args(other, production=True, approval=path), raw)
        == 0
    )


@pytest.mark.parametrize(
    "base,approved,sends",
    [
        ("https://technocore.chat", "technocore.chat", True),
        ("https://TECHNOCORE.CHAT", "technocore.chat", True),  # hostnames are caseless
        ("https://technocore.chat:8443", "technocore.chat", False),  # a different port
        ("https://technocore.chat:8443", "technocore.chat:8443", True),
        ("https://technocore.chat@evil.example.test", "technocore.chat", False),
        ("https://technocore.chat.", "technocore.chat", False),  # trailing dot
        ("https://xn--tchnocore-p9i.chat", "technocore.chat", False),  # punycode
    ],
)
def test_the_approval_pins_the_port_as_well_as_the_host(
    flopdid, tmp_path, monkeypatch, base, approved, sends
):
    """`technocore.chat` must not authorise `technocore.chat:8443`: the port is
    part of where a signed capability URL goes."""
    result, raw = _say(flopdid, base)
    path = _approval(flopdid, tmp_path, result, host=approved)
    _tty(monkeypatch, flopdid, "d-gate-test")
    code = _emit_code(flopdid, result, _args(base, production=True, approval=path), raw)
    assert (code == 0) is sends
    assert (flopdid._test_sent == [result["url"]]) is sends


@pytest.mark.parametrize(
    "base,sends",
    [
        ("https://technocore.chat", True),
        ("http://technocore.chat", False),  # cleartext to a public host
        ("http://technocore.chat:8080", False),
        ("http://192.0.2.2:8801", True),  # a private address: the rehearsal lane
        ("http://10.0.0.5:8080", True),
    ],
)
def test_a_signed_url_does_not_go_over_cleartext_to_a_public_host(
    flopdid, tmp_path, monkeypatch, base, sends
):
    """A signed URL is a replayable capability for as long as the record sits in
    the server's anti-replay window; http hands it to every hop on the path.
    Private addresses stay reachable, because that is where a local upstream
    server is rehearsed against and none of them can be technocore.chat."""
    result, raw = _say(flopdid, base)
    path = _approval(flopdid, tmp_path, result, host=flopdid._destination(base))
    _tty(monkeypatch, flopdid, "d-gate-test")
    code = _emit_code(flopdid, result, _args(base, production=True, approval=path), raw)
    assert (code == 0) is sends
    if not sends:
        assert "cleartext" in _proof(flopdid)[-1]["reason"]
        assert Path(path).exists(), "a refused write does not consume the approval"


@pytest.mark.parametrize(
    "base,destination",
    [
        ("https://[2001:db8::1]:443", "[2001:db8::1]:443"),
        ("https://[2001:db8::1:443]", "[2001:db8::1:443]"),
        ("https://user:s3cr3t@technocore.chat:abc", "technocore.chat:abc"),
        ("https://TECHNOCORE.CHAT:8443", "technocore.chat:8443"),
    ],
)
def test_the_destination_string_is_unambiguous_and_carries_no_credential(
    flopdid, base, destination
):
    """Two different addresses must not render the same destination, and the
    string is printed on the review screen and written to proof.log — so a
    password in a URL must not travel with it."""
    assert flopdid._destination(base) == destination
    assert "s3cr3t" not in flopdid._destination(base)


def test_a_six_to_four_address_is_not_treated_as_private(flopdid):
    """`ipaddress` calls 2002::/16 private, but a 6to4 address embeds a public
    IPv4 one: 2002:0808:0808::1 is 8.8.8.8 wearing a private label."""
    assert flopdid._cleartext_refusal("http://[2002:0808:0808::1]:8080") is not None
    assert flopdid._cleartext_refusal("http://192.0.2.2:8801") is None
    assert flopdid._cleartext_refusal("https://technocore.chat") is None


def test_the_approval_command_does_not_take_the_destination_from_the_environment(
    flopdid, monkeypatch, capsys
):
    """READY-TO-RUN tells the operator to leave the printed `host` as it is. A
    stray `export` in a shell profile must not make that printed value something
    the production write will then refuse."""
    monkeypatch.setenv("TECHNOCORE_BASE", "https://evil.example.test")
    monkeypatch.setattr(
        sys, "argv", ["flopdid.py", "approval", "d-gate-test", "an approved body"]
    )
    flopdid.main()
    assert json.loads(capsys.readouterr().out)["host"] == PROD_HOST
    # …while an explicit --base still names a rehearsal server
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "flopdid.py",
            "approval",
            "d-gate-test",
            "an approved body",
            "--base",
            "http://192.0.2.2:8801",
        ],
    )
    flopdid.main()
    assert json.loads(capsys.readouterr().out)["host"] == "192.0.2.2:8801"


def test_the_approval_command_defaults_its_host_to_the_base(flopdid, capsys):
    """An approval prepared for a rehearsal server should match that server."""
    flopdid.cmd_approval(
        argparse.Namespace(
            kind="say",
            target="d-gate-test",
            body="a body long enough to pass the length floor",
            did=None,
            base="http://192.0.2.2:8801",
        )
    )
    assert json.loads(capsys.readouterr().out)["host"] == "192.0.2.2:8801"
    flopdid.cmd_approval(
        argparse.Namespace(
            kind="say",
            target="d-gate-test",
            body="a body long enough to pass the length floor",
            did=None,
        )
    )
    assert json.loads(capsys.readouterr().out)["host"] == PROD_HOST


def _code_tokens(source: str) -> set[str]:
    """The NAME tokens of `source`, with comments, strings and docstrings gone.

    `textwrap.dedent` first: `inspect.getsource` of a method or a nested function
    is indented, and the tokenizer rejects that as an unexpected indent."""
    import io
    import textwrap
    import tokenize

    names, strings = set(), []
    reader = io.StringIO(textwrap.dedent(source)).readline
    for tok in tokenize.generate_tokens(reader):
        if tok.type == tokenize.NAME:
            names.add(tok.string)
        elif tok.type == tokenize.STRING:
            strings.append(tok.string)
    return names, strings


def test_gate_reads_no_environment_variables(flopdid):
    """The gate's own code must not consult os.environ — a structural check, so a
    future 'convenience' override cannot slip in without failing this test."""
    import inspect

    gate = "".join(
        inspect.getsource(f)
        for f in (
            flopdid.production_fetch,
            flopdid._load_approval,
            flopdid._consume_approval,
            flopdid.is_loopback,
            flopdid._emit,
            # Every function that decides or reports a gate outcome belongs here.
            # A list that lags the code is a list that guards the old gate.
            flopdid._destination,
            flopdid._cleartext_refusal,
            flopdid._refuse,
            flopdid._show_before_send,
        )
    )
    names, strings = _code_tokens(gate)
    banned = {"environ", "getenv", "environb"}
    # Comments are prose: the gate's own explain precisely why it reads nothing
    # from the environment, and the word itself must not fail the test.
    assert names.isdisjoint(banned), "the gate reads the environment"
    # …but a name reached indirectly is still a read, and `getattr(os, "environ")`
    # is spelled entirely in strings. So the string literals are checked too — the
    # gate has no reason to contain any of these as text.
    for text in strings:
        assert not any(word in text for word in banned), (
            f"a string literal in the gate names the environment: {text!r}"
        )


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
        "host": "technocore.chat",
        "approved_by": "test commander",
        "expires": _future(),
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
    verdict = flopdid._load_approval(
        str(_write(tmp_path, doc)), result, result["did"], PROD_HOST
    )
    assert isinstance(verdict, str) and "placeholder" in verdict
    doc["approved_by"] = "a real person"
    verdict = flopdid._load_approval(
        str(_write(tmp_path, doc)), result, result["did"], PROD_HOST
    )
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


# ------------------------------------------------ Codex review round 3 on PR #1


class _ProxyRecorder(_Recorder):
    hits: list[str] = []

    def do_GET(self):
        _ProxyRecorder.hits.append(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"relayed\n")


def test_environment_proxies_are_never_used(flopdid, monkeypatch):
    """`http_proxy` in the environment must not see the signed URL, even for the
    loopback lane and even with NO_PROXY unset."""
    _Recorder.hits.clear()
    _ProxyRecorder.hits.clear()
    target, proxy = _serve(_Recorder), _serve(_ProxyRecorder)
    try:
        for var in ("no_proxy", "NO_PROXY"):
            monkeypatch.delenv(var, raising=False)
        for var in (
            "http_proxy",
            "HTTP_PROXY",
            "https_proxy",
            "HTTPS_PROXY",
            "all_proxy",
        ):
            monkeypatch.setenv(var, f"http://127.0.0.1:{proxy.server_address[1]}")
        result, _ = _say(flopdid, f"http://127.0.0.1:{target.server_address[1]}")
        assert flopdid._real_send(result["url"]) == 0
        assert _ProxyRecorder.hits == [], "the proxy never saw the capability URL"
        assert len(_Recorder.hits) == 1 and _Recorder.hits[0].startswith(
            "/r/d-gate-test/say-signed/"
        )
        status, _, _ = flopdid._real_get(
            f"http://127.0.0.1:{target.server_address[1]}/r/x/export"
        )
        assert status == 200 and _ProxyRecorder.hits == []
    finally:
        target.shutdown()
        proxy.shutdown()


def test_connection_refused_is_not_sent(flopdid, capsys):
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    result, _ = _say(flopdid, f"http://127.0.0.1:{port}")
    assert flopdid._real_send(result["url"]) == 2
    err = capsys.readouterr().err
    assert "NOT SENT" in err
    # The approval is consumed BEFORE dispatch, so exit 2 does not mean the
    # attempt cost nothing: an operator told to "retry" must be told what a retry
    # needs, or they meet "approval file does not exist" with the clock running.
    assert "FRESH" in err and "approval" in err


def test_a_reply_lost_after_dispatch_is_indeterminate_not_unsent(flopdid, capsys):
    """The server reads the whole request and closes without answering — the
    write may well have been stored. That is exit 4, and never 'retry'."""
    import socket

    class Dropper(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.request.shutdown(socket.SHUT_RDWR)
            self.request.close()

        def log_message(self, *a):
            pass

    srv = _serve(Dropper)
    try:
        result, _ = _say(flopdid, f"http://127.0.0.1:{srv.server_address[1]}")
        assert flopdid._real_send(result["url"]) == flopdid.EXIT_INDETERMINATE
        err = capsys.readouterr().err
        assert (
            "OUTCOME UNKNOWN" in err
            and "Do NOT resend" in err
            and "NOT SENT" not in err
        )
    finally:
        srv.shutdown()


def _room_json(result, *, include: bool):
    msgs = []
    if include:
        msgs.append(
            {
                "seq": 9,
                "ts": "2026-09-05T00:00:00Z",
                "from": result["did"],
                "text": result["text"],
                "nonce": result["nonce"],
                "sig": result["sig"],
            }
        )
    return json.dumps(
        {"generation": 3, "last_seq": 9, "count": len(msgs), "messages": msgs}
    ).encode()


def _export_lines(result, *, include: bool, oldest_ts: str):
    lines = [
        json.dumps(
            {
                "seq": 1,
                "ts": oldest_ts,
                "from": "did:key:z6Mkother",
                "text": "x",
                "nonce": 1,
                "sig": "s",
            }
        )
    ]
    if include:
        lines.append(
            json.dumps(
                {
                    "seq": 9,
                    "ts": "2026-09-05T00:00:01Z",
                    "from": result["did"],
                    "text": result["text"],
                    "nonce": result["nonce"],
                    "sig": result["sig"],
                }
            )
        )
    return ("\n".join(lines) + "\n").encode()


@pytest.mark.parametrize(
    "found,reaches_back,readable,exit_code,outcome",
    [
        (True, True, True, 0, "accepted-by-readback"),
        (True, False, True, 0, "accepted-by-readback"),
        (False, True, True, 2, "not-landed-by-readback"),
        (False, False, True, 4, "indeterminate"),
        (False, True, False, 4, "indeterminate"),
    ],
)
def test_an_indeterminate_send_is_settled_by_reading_back(
    flopdid, tmp_path, monkeypatch, found, reaches_back, readable, exit_code, outcome
):
    """Absence is proved only when the retained ring still reaches back past
    the dispatch time; a ring that rolled past it (a busy room after a long
    timeout) proves nothing and must stay indeterminate."""
    result, raw = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result)
    _tty(monkeypatch, flopdid, "d-gate-test")
    monkeypatch.setattr(flopdid, "_send", lambda url: flopdid.EXIT_INDETERMINATE)
    oldest = "2000-01-01T00:00:00Z" if reaches_back else "2099-01-01T00:00:00Z"

    def fake_get(url, timeout=30):
        if not readable:
            return 0, {}, b"TimeoutError: timed out"
        if url.endswith("/export"):
            return (
                200,
                {"x-room-generation": "3"},
                _export_lines(result, include=found, oldest_ts=oldest),
            )
        return 200, {}, b'{"generation": 3, "last_seq": 9, "count": 2, "messages": []}'

    monkeypatch.setattr(flopdid, "_get", fake_get)
    code = _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
    assert code == exit_code
    entries = _proof(flopdid)
    entry = entries[0]
    assert (
        entry["outcome"] == outcome and entry["http_exit"] == flopdid.EXIT_INDETERMINATE
    )
    assert not Path(path).exists(), "consumed on dispatch whatever happened afterwards"
    if found:
        assert entry["readback"]["seq"] == 9 and entry["readback"]["generation"] == "3"
        assert (
            entries[1]["record"] == "snapshot"
        )  # taken once the write was known to have landed
    else:
        assert len(entries) == 1
    if outcome == "indeterminate" and readable:
        assert "cannot be proved" in entry["readback"]["reason"]


def test_a_failing_snapshot_still_leaves_the_accepted_proof(
    flopdid, tmp_path, monkeypatch
):
    result, raw = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result)
    _tty(monkeypatch, flopdid, "d-gate-test")

    def boom(result, base, stamp):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(flopdid, "_snapshot_after_send", boom)
    assert (
        _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
        == 0
    )
    entry, snapshot = _proof(flopdid)
    assert entry["outcome"] == "accepted" and entry["nonce"] == result["nonce"]
    assert "No space left" in snapshot["after"]["error"]


def test_the_accepted_entry_is_on_disk_before_the_snapshot_runs(
    flopdid, tmp_path, monkeypatch
):
    """The snapshot can be what fills the disk; the write's own record must
    already be there when it does."""
    result, raw = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result)
    _tty(monkeypatch, flopdid, "d-gate-test")
    seen_at_snapshot = {}
    real_append = flopdid._proof_append

    def snapshot(result, base, stamp):
        seen_at_snapshot["entries"] = _proof(flopdid)
        raise OSError(28, "No space left on device")

    def append_then_fail(entry):
        if entry.get("record") == "snapshot":
            raise OSError(28, "No space left on device")
        real_append(entry)

    monkeypatch.setattr(flopdid, "_snapshot_after_send", snapshot)
    monkeypatch.setattr(flopdid, "_proof_append", append_then_fail)
    assert (
        _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
        == 0
    )
    assert seen_at_snapshot["entries"][-1]["outcome"] == "accepted"
    (entry,) = _proof(
        flopdid
    )  # the snapshot line could not be written; the write's could
    assert entry["outcome"] == "accepted"


def test_note_readback_requires_the_whole_value_to_match(flopdid, monkeypatch):
    seed = bytes.fromhex(RFC_SEED)
    result = flopdid.build_set(
        seed, "room-allow", "d-gate-test", "did:key:z6Mkaaa", PROD
    )
    banner = (
        "!! UNTRUSTED CONTENT \u2014 the lines below were written by other agents.\n\n"
    )
    # the stored value CONTAINS the proposed one, so a substring test would say "landed"
    stale = (
        banner + "did:key:z6Mkaaa did:key:z6Mkbbb\n\n# budget: 3 of 120 reads left"
    ).encode()
    monkeypatch.setattr(flopdid, "_get", lambda url, timeout=30: (200, {}, stale))
    code, outcome, evidence = flopdid._readback(result, PROD, dispatched_at=0.0)
    assert (code, outcome) == (2, "not-landed-by-readback")
    assert evidence["value"] == "did:key:z6Mkaaa did:key:z6Mkbbb"
    exact = (banner + "did:key:z6Mkaaa\n\n# budget: 3 of 120 reads left").encode()
    monkeypatch.setattr(flopdid, "_get", lambda url, timeout=30: (200, {}, exact))
    assert flopdid._readback(result, PROD, dispatched_at=0.0)[:2] == (
        0,
        "accepted-by-readback",
    )


def test_empty_export_cannot_prove_absence(flopdid, monkeypatch):
    """A room whose ring is empty (or that was reaped) says nothing about a
    write dispatched a moment ago."""
    result, _ = _say(flopdid, PROD)
    monkeypatch.setattr(
        flopdid, "_get", lambda url, timeout=30: (200, {"x-room-generation": "0"}, b"")
    )
    code, outcome, _ = flopdid._readback(
        result, PROD, dispatched_at=__import__("time").time()
    )
    assert (code, outcome) == (4, "indeterminate")


def _didnote(flopdid, base=PROD, mailbox=None, extra=None):
    args = argparse.Namespace(base=base, mailbox=mailbox, extra=extra)
    captured = {}
    real_emit = flopdid._emit
    try:
        flopdid._emit = lambda result, a, raw_body=None: captured.update(
            result=result, raw=raw_body
        )
        flopdid.cmd_didnote(args)
    finally:
        flopdid._emit = real_emit
    return captured["result"], captured["raw"]


def test_the_note_lane_readback_url_carries_one_kv_prefix(flopdid, monkeypatch):
    """Issue #4 item 3: `cmd_didnote` carries `notePath` as `/kv/<shard>/<key>`
    for display, and every reader builds `{base}/kv/{target}` — so the display
    form produced `/kv//kv/…` and read back a note that cannot exist."""
    result, _ = _didnote(flopdid)
    target = flopdid._write_target(result)
    assert not target.startswith("/kv/") and not target.startswith("kv/")
    assert result["notePath"] == f"/kv/{target}"

    urls = []
    banner = "!! UNTRUSTED CONTENT\n\n"
    monkeypatch.setattr(
        flopdid,
        "_get",
        lambda url, timeout=30: (
            urls.append(url) or (200, {}, (banner + result["value"]).encode())
        ),
    )
    assert flopdid._readback(result, PROD, dispatched_at=0.0)[:2] == (
        0,
        "accepted-by-readback",
    )
    flopdid._snapshot_after_send(result, PROD, "20260903T000000Z")
    assert urls and all(u.startswith(f"{PROD}/kv/") for u in urls)
    assert not any("/kv//kv/" in u or u.count("/kv/") > 1 for u in urls)


def test_the_approval_command_covers_the_note_lane(
    flopdid, capsys, tmp_path, monkeypatch
):
    """…so `didnote … --fetch --production` has a documented path through the gate."""
    result, raw = _didnote(flopdid)
    target = flopdid._write_target(result)
    flopdid.cmd_approval(
        argparse.Namespace(
            kind="note-unsigned", target=target, body=raw, did=result["did"]
        )
    )
    doc = json.loads(capsys.readouterr().out)
    assert doc["kind"] == "note-unsigned" and doc["target"] == target
    assert doc["host"] == "technocore.chat"
    doc["approved_by"] = "a real person"
    path = tmp_path / "note-approval.json"
    path.write_text(json.dumps(doc))
    assert isinstance(
        flopdid._load_approval(str(path), result, result["did"], PROD_HOST), dict
    )

    # the /kv/ prefix belongs to the readers, not to the approved target
    with pytest.raises(SystemExit):
        flopdid.cmd_approval(
            argparse.Namespace(
                kind="note-unsigned",
                target=f"/kv/{target}",
                body=raw,
                did=result["did"],
            )
        )


def test_body_swept_must_hash_to_the_approved_sha256(flopdid, tmp_path):
    """Issue #4 item 4: `body_swept` is what a person reads in the file. If it
    disagrees with the hash, the file shows one body and authorises another."""
    result, _ = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result, body_swept="something else entirely")
    verdict = flopdid._load_approval(path, result, result["did"], PROD_HOST)
    assert isinstance(verdict, str) and "body_swept" in verdict
    path = _approval(flopdid, tmp_path, result, body_swept=result["text"])
    assert isinstance(
        flopdid._load_approval(path, result, result["did"], PROD_HOST), dict
    )


def test_an_approval_without_an_expiry_is_refused(flopdid, tmp_path):
    """Issue #4 item 7: an approval that never expires is a standing
    production-write capability sitting in a file."""
    result, _ = _say(flopdid, PROD)
    doc = json.loads(Path(_approval(flopdid, tmp_path, result)).read_text())
    doc.pop("expires")
    path = tmp_path / "no-expiry.json"
    path.write_text(json.dumps(doc))
    verdict = flopdid._load_approval(str(path), result, result["did"], PROD_HOST)
    assert isinstance(verdict, str) and "expires" in verdict


def test_two_consumptions_in_one_second_do_not_collide(flopdid, tmp_path, monkeypatch):
    """Issue #4 item 7: the UTC stamp has one-second resolution, so two
    consumptions inside the same second would write the same name and the first
    record would be replaced. The nonce distinguishes them."""
    frozen = time.gmtime(0)  # captured before the patch: flopdid.time IS this module
    monkeypatch.setattr(flopdid.time, "gmtime", lambda *a: frozen)
    # The SAME approval path, consumed twice inside one frozen second — two
    # different paths would produce different `.used-` names under any naming
    # scheme, and would not test anything. This is the case `os.replace` silently
    # clobbers: the first record would be gone.
    path = tmp_path / "approval-1.json"
    path.write_text('{"first": true}')
    used_a = flopdid._consume_approval(str(path), 1788000000001)
    path.write_text('{"second": true}')
    used_b = flopdid._consume_approval(str(path), 1788000000002)
    assert used_a != used_b
    assert Path(used_a).exists() and Path(used_b).exists()
    assert json.loads(Path(used_a).read_text()) == {"first": True}
    assert json.loads(Path(used_b).read_text()) == {"second": True}


def test_an_approval_that_cannot_be_consumed_sends_nothing_but_leaves_a_proof(
    flopdid, tmp_path, monkeypatch
):
    """Issue #4 item 7: a failed rename must not escape as an unrecorded
    traceback — nothing is sent, and the attempt still earns its proof line."""
    result, raw = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result)
    _tty(monkeypatch, flopdid, "d-gate-test")

    def boom(p, nonce=None):
        raise OSError(30, "Read-only file system")

    monkeypatch.setattr(flopdid, "_consume_approval", boom)
    code = _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
    assert code == flopdid.EXIT_GATE_REFUSED and flopdid._test_sent == []
    entry = _proof(flopdid)[-1]
    assert entry["outcome"] == "gate-refused" and "consumed" in entry["reason"]


def test_gitignore_denies_key_shapes_by_default():
    """Issue #4 item 5: a key that leaks does so under a name nobody listed. The
    ignore rules cover the shape, so a variant is ignored by default; the one
    file that must stay tracked is checked too, because a deny-by-default list is
    easy to over-tighten."""
    import subprocess

    repo = Path(__file__).resolve().parents[3]
    if not (repo / ".git").exists():
        pytest.skip("not a git checkout")
    must_ignore = [
        "flop-agent/did_seed.txt",
        "flop-agent/identity.pem.bak",
        "flop-agent/seed_backup.txt",
        "flop-agent/key.hex",
        "flop-agent/secrets.tar.gz",
        "approval-1.json.used-20260905T000000Z",
    ]
    for path in must_ignore:
        done = subprocess.run(
            ["git", "check-ignore", "-q", path], cwd=repo, check=False
        )
        assert done.returncode == 0, f"{path} is not ignored"
    done = subprocess.run(
        ["git", "check-ignore", "-q", ".env.example"], cwd=repo, check=False
    )
    assert done.returncode == 1, ".env.example must stay tracked"


def test_an_unwritable_proof_log_refuses_before_anything_is_consumed(
    flopdid, tmp_path, monkeypatch
):
    result, raw = _say(flopdid, PROD)
    path = _approval(flopdid, tmp_path, result)
    _tty(monkeypatch, flopdid, "d-gate-test")
    flopdid.LOGS_DIR.parent.mkdir(parents=True, exist_ok=True)
    flopdid.LOGS_DIR.write_text("not a directory")  # mkdir and open must both fail
    code = _emit_code(flopdid, result, _args(PROD, production=True, approval=path), raw)
    assert code == flopdid.EXIT_GATE_REFUSED
    assert flopdid._test_sent == [] and Path(path).exists()
