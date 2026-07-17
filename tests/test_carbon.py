"""Regression: openga.carbon vs WP3 CARBON cached values."""
import pytest

from openga import carbon
from openga.config import DEFAULT

REL = 1e-9


def test_boundaries(baseline):
    r = carbon.run(DEFAULT)
    b = baseline["carbon"]
    assert r.s1_s2_total == pytest.approx(b["s1_s2"], rel=REL)
    assert r.total_with_embodied == pytest.approx(b["with_embodied"], rel=REL)


def test_scope_split_sums(baseline):
    r = carbon.run(DEFAULT)
    assert r.scope1_total + r.scope2_total == pytest.approx(r.s1_s2_total, rel=1e-12)
    assert r.s1_s2_total + r.embodied_total == pytest.approx(r.total_with_embodied, rel=1e-12)


def test_placeholder_flag():
    assert carbon.run(DEFAULT).placeholder is True


def test_luo_gwp_china_grid(baseline):
    lv = carbon.validate_luo(DEFAULT, published_gwp=baseline["carbon"]["luo_gwp_china_grid"])
    assert lv.computed_gwp == pytest.approx(baseline["carbon"]["luo_gwp_china_grid"], rel=REL)
    assert lv.status == "PASS"


def test_grid_override_changes_scope2():
    au = carbon.run(DEFAULT)
    cn = carbon.run(DEFAULT, grid_ef=DEFAULT.ef.grid_elec_cn.value)
    assert cn.scope2_total > au.scope2_total
