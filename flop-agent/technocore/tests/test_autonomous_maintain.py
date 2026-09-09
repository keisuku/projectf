"""Safety and behavior tests for the d-bitflop-only unattended maintainer."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
REAL_SEED_VECTOR = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
DAY = 86400


@pytest.fixture()
def modules(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOP_AGENT_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("FLOP_FORCE_PURE", "1")
    sys.path.insert(0, str(SCRIPTS))
    for name in ("autonomous_maintain", "flopdid"):
        sys.modules.pop(name, None)
    flopdid = importlib.import_module("flopdid")
    auto = importlib.import_module("autonomous_maintain")
    # Use a public test vector while retaining every fixed-target check.
    seed = bytes.fromhex(REAL_SEED_VECTOR)
    test_did = flopdid.did_from_pubkey(flopdid.PUBKEY(seed))
    monkeypatch.setattr(auto, "EXPECTED_DID", test_did)
    monkeypatch.setattr(auto, "DID_NOTE", flopdid.note_path(test_did))
    monkeypatch.setattr(auto, "NOTE_VALUE", f"{test_did} log:{auto.ROOM}")
    monkeypatch.setenv("FLOP_DID_SEED", REAL_SEED_VECTOR)
    yield flopdid, auto, test_did
    for name in ("autonomous_maintain", "flopdid"):
        sys.modules.pop(name, None)


class Server:
    def __init__(self, auto, did, now, *, age_days=2, owner=None, count=4, signed=True):
        self.auto, self.did, self.now = auto, did, now
        self.owner = did if owner is None else owner
        self.note = "old"
        self.writes = []
        self.messages = [{
            "seq": 4,
            "ts": self._ts(now - age_days * DAY),
            "from": did,
            "text": "previous",
            "nonce": 10,
            "sig": "old-signature" if signed else "",
        }]
        self.count = count

    @staticmethod
    def _ts(epoch):
        from datetime import datetime, timezone
        return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")

    def room(self):
        return {
            "generation": 0, "last_seq": self.messages[-1]["seq"],
            "count": self.count, "messages": self.messages,
        }

    def get(self, url, timeout=30):
        if "/kv/room-owners/" in url:
            return 200, {}, self.owner.encode()
        if f"/kv/{self.auto.DID_NOTE}/set/" in url:
            self.note = self.auto.NOTE_VALUE
            self.writes.append("note")
            return 200, {}, b"ok"
        if url.endswith(f"/kv/{self.auto.DID_NOTE}"):
            return 200, {}, self.note.encode()
        if "/say-signed/" in url:
            parts = url.split("/say-signed/", 1)[1].split("/", 3)
            import urllib.parse
            self.messages.append({
                "seq": 5, "ts": self._ts(self.now), "from": parts[0],
                "sig": parts[1], "nonce": int(parts[2]),
                "text": urllib.parse.unquote(parts[3]),
            })
            self.count += 1
            self.writes.append("signed")
            return 200, {}, b"ok"
        if f"/r/{self.auto.ROOM}?" in url:
            return 200, {}, json.dumps(self.room()).encode()
        raise AssertionError(f"unexpected URL: {url}")


def test_not_due_refreshes_note_without_signing(modules):
    _, auto, did = modules
    now = 2_000_000_000
    server = Server(auto, did, now, age_days=2)
    out = auto.maintain(now=now, getter=server.get, sleeper=lambda _: None)
    assert server.writes == ["note"]
    assert out["signed_write"] == "not-due"
    assert server.note == f"{did} log:d-bitflop"


def test_due_signs_once_and_verifies_exact_record(modules):
    _, auto, did = modules
    now = 2_000_000_000
    server = Server(auto, did, now, age_days=5.1)
    out = auto.maintain(now=now, getter=server.get, sleeper=lambda _: None)
    assert server.writes == ["note", "signed"]
    assert out["signed_write"] == "written-and-verified"
    assert server.messages[-1]["from"] == did
    assert "verified the fixed owner DID" in server.messages[-1]["text"]


def test_due_retries_a_stale_success_readback(modules):
    _, auto, did = modules
    now = 2_000_000_000
    server = Server(auto, did, now, age_days=5.1)
    stale_room = json.dumps(server.room()).encode()
    verification_urls = []
    sleeps = []

    def cached_get(url, timeout=30):
        if f"/r/{auto.ROOM}?" in url and "verify=" in url:
            verification_urls.append(url)
            if len(verification_urls) <= 2:
                return 200, {}, stale_room
        return server.get(url, timeout)

    out = auto.maintain(now=now, getter=cached_get, sleeper=sleeps.append)
    assert out["signed_write"] == "written-and-verified"
    assert server.writes == ["note", "signed"]
    assert len(verification_urls) == 3
    assert all("verify=" in url for url in verification_urls)
    assert sleeps == [1, 2]


@pytest.mark.parametrize("failure", ["owner", "count", "signature"])
def test_invariant_failure_refuses_before_any_write(modules, failure):
    _, auto, did = modules
    now = 2_000_000_000
    kwargs = {
        "owner": "did:key:z6MkWrong" if failure == "owner" else None,
        "count": 1 if failure == "count" else 4,
        "signed": failure != "signature",
    }
    server = Server(auto, did, now, age_days=6, **kwargs)
    with pytest.raises(auto.Refusal):
        auto.maintain(now=now, getter=server.get, sleeper=lambda _: None)
    assert server.writes == []


def test_wrong_seed_refuses_before_network(modules, monkeypatch):
    _, auto, _ = modules
    monkeypatch.setenv("FLOP_DID_SEED", "00" * 32)
    calls = []
    with pytest.raises(auto.Refusal):
        auto.maintain(now=2_000_000_000, getter=lambda *a: calls.append(a), sleeper=lambda _: None)
    assert calls == []


def test_targets_are_code_fixed_not_cli_or_environment(modules, monkeypatch):
    _, auto, did = modules
    monkeypatch.setenv("TECHNOCORE_BASE", "https://attacker.invalid")
    server = Server(auto, did, 2_000_000_000, age_days=2)
    auto.maintain(now=server.now, getter=server.get, sleeper=lambda _: None)
    assert auto.BASE == "https://technocore.chat"
    assert auto.ROOM == "d-bitflop"
