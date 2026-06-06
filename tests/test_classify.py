"""ABC-XYZ classification — the approved hand-checked fixture.

Conventions (approved):
  * demand_cv = population std / mean of weekly demand (descriptive, divide by N).
    Undefined (None) when mean == 0.
  * XYZ bands: X if CV <= 0.5 ; Y if 0.5 < CV <= 1.0 ; Z if CV > 1.0.
  * ABC by annual usage value = avg_weekly_demand * 52 * unit_cost, ranked desc:
    A if cumulative share <= 80% ; B if <= 95% ; C otherwise.
  * ABC must REUSE the ingestion-computed avg_weekly_demand, not recompute it.
"""

import math

import pytest

from analytics.metrics import (
    annual_usage_value,
    classify_abc,
    demand_cv,
    xyz_class,
)
from analytics.models import Sku


# ─────────────────────────────────────────────────────────────────────────────
# demand_cv — population coefficient of variation, worked by hand.
# ─────────────────────────────────────────────────────────────────────────────
def test_demand_cv_fixture():
    # FIX-X [8,12,8,12]: mean 10, var 4, std 2 -> CV 0.20
    assert demand_cv([8, 12, 8, 12]) == pytest.approx(0.20)
    # FIX-Y [4,16,4,16]: mean 10, var 36, std 6 -> CV 0.60
    assert demand_cv([4, 16, 4, 16]) == pytest.approx(0.60)
    # FIX-Z [0,0,0,40]: mean 10, var 300, std sqrt(300) -> CV 1.732...
    assert demand_cv([0, 0, 0, 40]) == pytest.approx(math.sqrt(300) / 10)
    assert demand_cv([0, 0, 0, 40]) == pytest.approx(1.7320508, abs=1e-6)


def test_demand_cv_undefined_when_no_demand():
    assert demand_cv([0, 0, 0, 0]) is None   # mean 0 -> undefined
    assert demand_cv([]) is None


# ─────────────────────────────────────────────────────────────────────────────
# xyz_class — bands and the locked boundary rules (0.5 -> X, 1.0 -> Y).
# ─────────────────────────────────────────────────────────────────────────────
def test_xyz_class_bands_and_boundaries():
    assert xyz_class(0.20) == "X"
    assert xyz_class(0.60) == "Y"
    assert xyz_class(1.732) == "Z"
    assert xyz_class(0.5) == "X"    # boundary: upper-inclusive
    assert xyz_class(1.0) == "Y"    # boundary: upper-inclusive
    assert xyz_class(None) is None  # no demand -> no class


# ─────────────────────────────────────────────────────────────────────────────
# annual_usage_value REUSES avg_weekly_demand (does not recompute from sales).
#   A SKU with NO sales rows but a set avg_weekly_demand still values correctly.
# ─────────────────────────────────────────────────────────────────────────────
def test_annual_usage_value_reuses_avg_weekly_demand():
    s = Sku("R", avg_weekly_demand=10, unit_cost=500, recent_weekly_sales=None)
    assert annual_usage_value(s) == pytest.approx(10 * 52 * 500)  # 260,000


# ─────────────────────────────────────────────────────────────────────────────
# classify_abc — the 3-SKU portfolio ranking, worked by hand.
#   Z 260,000 (76.9% -> A) ; Y 52,000 (92.3% -> B) ; X 26,000 (100% -> C)
# ─────────────────────────────────────────────────────────────────────────────
def test_classify_abc_fixture():
    fix_x = Sku("FIX-X", avg_weekly_demand=10, unit_cost=50)
    fix_y = Sku("FIX-Y", avg_weekly_demand=10, unit_cost=100)
    fix_z = Sku("FIX-Z", avg_weekly_demand=10, unit_cost=500)

    classify_abc([fix_x, fix_y, fix_z])  # order-independent

    assert fix_z.abc_class == "A"
    assert fix_y.abc_class == "B"
    assert fix_x.abc_class == "C"


# ─────────────────────────────────────────────────────────────────────────────
# Combined classes: the AZ quadrant (high value + lumpy) is the dangerous one.
# ─────────────────────────────────────────────────────────────────────────────
def test_combined_abc_xyz_quadrants():
    # Full 3-SKU portfolio — ABC is relative, so Y must be present for Z to be A.
    fix_x = Sku("FIX-X", avg_weekly_demand=10, unit_cost=50,
                demand_cv=demand_cv([8, 12, 8, 12]), xyz_class=xyz_class(0.20))
    fix_y = Sku("FIX-Y", avg_weekly_demand=10, unit_cost=100,
                demand_cv=demand_cv([4, 16, 4, 16]), xyz_class=xyz_class(0.60))
    fix_z = Sku("FIX-Z", avg_weekly_demand=10, unit_cost=500,
                demand_cv=demand_cv([0, 0, 0, 40]), xyz_class=xyz_class(1.732))
    classify_abc([fix_x, fix_y, fix_z])

    assert (fix_z.abc_class, fix_z.xyz_class) == ("A", "Z")  # AZ — flag this
    assert (fix_y.abc_class, fix_y.xyz_class) == ("B", "Y")  # BY
    assert (fix_x.abc_class, fix_x.xyz_class) == ("C", "X")  # CX — ignore
