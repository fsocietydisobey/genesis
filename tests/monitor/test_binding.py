"""127.0.0.1 binding is the auth layer — refuse anything else."""

import pytest

from chimera.monitor.server import _assert_loopback


def test_loopback_accepted():
    _assert_loopback("127.0.0.1")  # should not raise


def test_zero_zero_zero_zero_rejected():
    with pytest.raises(SystemExit) as exc:
        _assert_loopback("0.0.0.0")
    assert "refusing to bind" in str(exc.value)


def test_arbitrary_host_rejected():
    with pytest.raises(SystemExit):
        _assert_loopback("192.168.1.10")


def test_ipv6_loopback_rejected_for_now():
    # Phase 1 only allows literal "127.0.0.1" — adding "::1" can come
    # later if any Python platform actually defaults to IPv6 loopback.
    with pytest.raises(SystemExit):
        _assert_loopback("::1")
