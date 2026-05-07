"""Verify the lazy-import helper exits cleanly when an extra is missing."""

import pytest

from chimera.monitor import _optional


def test_require_returns_module_when_present():
    mod = _optional.require("json")
    assert hasattr(mod, "loads")


def test_require_exits_with_install_hint_when_missing(capsys):
    with pytest.raises(SystemExit) as exc:
        _optional.require("definitely_not_a_real_module_42x")
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Install monitor extras" in err
    assert "chimera[monitor]" in err
