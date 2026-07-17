import json
import os

import pytest

_HERE = os.path.dirname(__file__)


@pytest.fixture(scope="session")
def baseline():
    """Cached workbook values (regenerate with tools/build_baseline.py)."""
    with open(os.path.join(_HERE, "baseline.json")) as fh:
        return json.load(fh)


# absolute (kg/kWh) and relative tolerances for reproducing workbook caches
REL = 1e-9
ABS = 1e-6
