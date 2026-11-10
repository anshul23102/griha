from griha import config
from griha.audit import AuditLog
from griha.engine import Engine
from griha.synth import make_case


def _decide():
    e = Engine(audit=AuditLog(None))
    app, _ = make_case(61000)
    d = e.underwrite(app, record=True)
    return e, d


def test_kfs_and_grievance_controls_cite_the_verified_digital_lending_paragraphs():
    e, d = _decide()
    stage = next(x for x in d.evidence if x.stage == "compliance")
    ctl = {c["id"]: c for c in stage.data["controls"]} if "controls" in stage.data else {c["id"]: c for c in stage.data}
    assert "paras 142 to 144" in ctl["GRIEVANCE"]["clause"] and "para 11" in ctl["GRIEVANCE"]["clause"] and ctl["GRIEVANCE"]["basis"] == "verified"
    assert "paras 131, 132, 137, 175" in ctl["KFS"]["clause"] and "8(i), 10" in ctl["KFS"]["clause"]
    if d.kfs:
        assert f"{config.COOLING_OFF_DAYS}-day cooling-off" in ctl["KFS"]["evidence"]
    assert config.COOLING_OFF_DAYS >= 1                     # the Directions: not less than one day


def test_replay_reports_the_engine_version_and_flags_an_older_record():
    e, d = _decide()
    entry = e.audit.for_case_event(d.case_id, "DECISION")[0]
    assert entry["payload"]["engine_version"] == config.ENGINE_VERSION
    r = e.replay(entry)
    assert r["match"] is True and r["engine_match"] is True and r["engine_current"] == config.ENGINE_VERSION
    old = {**entry, "payload": {k: v for k, v in entry["payload"].items() if k != "engine_version"}}      # written before versioning
    r2 = e.replay(old)
    assert r2["engine_recorded"] == "1.0.0" and r2["engine_match"] is False


def _big_case(minimum: float):
    for seed in range(61000, 62500):
        app, _ = make_case(seed)
        if app.loan.amount >= minimum and app.loan.product == "HL":
            return app
    raise AssertionError("no synthetic case that large")


def _rule(d, rid):
    stage = next(x for x in d.evidence if x.stage == "policy")
    return next((r for r in stage.data["rules"] if r["id"] == rid), None)


def test_two_valuations_required_from_50_lakh_and_two_independent_from_75_lakh():
    e = Engine(audit=AuditLog(None))
    app = _big_case(7_500_000)
    assert len(app.property.independent_valuations) == 2                       # the synthetic generator supplies what the Directions require
    ok = e.underwrite(app, record=False)
    r = _rule(ok, "VALUATION_REPORTS")
    assert r is None or r["outcome"] == "pass"
    short = app.model_copy(deep=True)
    short.property.independent_valuations = short.property.independent_valuations[:1]
    r1 = _rule(e.underwrite(short, record=False), "VALUATION_REPORTS")
    assert r1["outcome"] == "refer" and "Annex V" in r1["reason"]
    none = app.model_copy(deep=True)
    none.property.independent_valuations = []
    d = e.underwrite(none, record=False)
    assert d.outcome in ("REFER", "REJECT")


def test_lower_of_the_valuation_reports_is_used():
    e = Engine(audit=AuditLog(None))
    app = _big_case(7_500_000)
    low = app.model_copy(deep=True)
    low.property.independent_valuations = [round(app.property.declared_value * 0.5), round(app.property.declared_value * 0.52)]
    d = e.underwrite(low, record=False)
    prop = next(x for x in d.evidence if x.stage == "property").data
    assert prop["assessed_value"] == min(prop["valuation_reports"]["independent"]) and "lower of 3" in next(x for x in d.evidence if x.stage == "property").summary


def test_kfs_discloses_what_para_131_requires():
    e = Engine(audit=AuditLog(None))
    for seed in range(61000, 61200):
        app, _ = make_case(seed)
        d = e.underwrite(app, record=False)
        if d.kfs and app.loan.product == "HL":
            ids = {x["id"] for x in d.kfs["other_disclosures"]}
            assert {"all_in_cost", "fee_refund", "penal", "conversion", "reset", "terms_change"} <= ids
            assert "para 163" in d.kfs["foreclosure_charges"]
            assert all(x["basis"].startswith(("HFC Directions 2025 para", "RBC Directions 2025 para")) for x in d.kfs["other_disclosures"])
            return
    raise AssertionError("no approved housing loan found")
