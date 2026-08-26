"""Regression coverage for Discord IPC cleanup on failed GUI/service probes."""

from __future__ import annotations


class FakeRPC:
    def __init__(self, *, connect_error: Exception | None = None, update_error: Exception | None = None):
        self.connect_error = connect_error
        self.update_error = update_error
        self.closed = 0
        self.connected = False

    def connect(self):
        if self.connect_error:
            raise self.connect_error
        self.connected = True

    def update(self, **_payload):
        if self.update_error:
            raise self.update_error

    def clear(self):
        return None

    def close(self):
        self.closed += 1
        self.connected = False


def test_resource_safe_presence_closes_failed_connect(monkeypatch):
    import pypresence
    import resource_hardening

    original = pypresence.Presence

    class Base(FakeRPC):
        pass

    monkeypatch.setattr(pypresence, "Presence", Base)
    # Reset only the local patch marker for this isolated regression test.
    resource_hardening._patch_pypresence_cleanup()
    Safe = pypresence.Presence
    rpc = Safe(connect_error=RuntimeError("offline"))
    try:
        rpc.connect()
    except RuntimeError:
        pass
    assert rpc.closed == 1
    monkeypatch.setattr(pypresence, "Presence", original)


def test_resource_safe_presence_closes_failed_update(monkeypatch):
    import pypresence
    import resource_hardening

    original = pypresence.Presence

    class Base(FakeRPC):
        pass

    monkeypatch.setattr(pypresence, "Presence", Base)
    resource_hardening._patch_pypresence_cleanup()
    Safe = pypresence.Presence
    rpc = Safe(update_error=RuntimeError("pipe gone"))
    rpc.connect()
    try:
        rpc.update(details="x")
    except RuntimeError:
        pass
    assert rpc.closed == 1
    monkeypatch.setattr(pypresence, "Presence", original)
