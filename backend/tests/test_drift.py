import numpy as np

from griha import drift


def test_psi_zero_for_same_distribution_and_large_for_shift():
    rng = np.random.default_rng(1)
    ref = rng.normal(0, 1, 5000).tolist()
    assert drift.psi(ref, rng.normal(0, 1, 2000).tolist()) < 0.05
    assert drift.psi(ref, rng.normal(1.5, 1, 2000).tolist()) > 0.25


def test_status_bands():
    assert [drift.status(v) for v in (0.0, 0.1, 0.24, 0.3)] == ["stable", "shifted", "shifted", "drifted"]


def test_report_waits_for_enough_live_cases():
    assert drift.report(None, [])["state"] == "warming"
    assert drift.report({"foir": [0.1, 0.2]}, [])["state"] == "collecting"


def test_engine_reference_and_live_report_on_real_cases():
    from griha.audit import AuditLog
    from griha.engine import Engine
    from griha.synth import make_case
    e = Engine(audit=AuditLog(None))
    ref = drift.build_reference(e, 400)
    assert all(len(v) > 300 for v in ref.values())
    live = [e.underwrite(make_case(70000 + i)[0], record=False) for i in range(300)]
    rep = drift.report(ref, live)
    assert rep["state"] == "ready" and rep["live"] >= drift.MIN_LIVE
    assert {r["feature"] for r in rep["features"]} >= {"foir", "ltv", "bureau_score"}
    assert rep["overall"] == "stable"        # same population family, so it must not alarm
