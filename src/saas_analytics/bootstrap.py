from __future__ import annotations

from saas_analytics.generate_data import generate_all
from saas_analytics.health import assert_outputs, missing_exports
from saas_analytics.run import run_pipeline


def ensure_demo_outputs() -> bool:
    if not missing_exports():
        assert_outputs()
        return False
    generate_all()
    run_pipeline(mode="full")
    assert_outputs()
    return True
