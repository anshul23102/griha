"""KFS against the NBFC Responsible Business Conduct Directions 2025 (RBI/DOR/2025-26/362): para 29, Annex I, paras 30, 34."""
from datetime import datetime, timezone

from griha import pricing
from griha.api import _validity, app
from tests.keyed import KeyedClient


def test_apr_matches_the_rbi_worked_example():                       # para 29(3)(i): 20,000, 15%, 24 EPIs, fees 400 -> APR 17.07%
    assert round(pricing.apr(20000, 0.15, 24, 400) * 100, 2) == 17.07
    assert round(pricing.emi(20000, 0.15, 24) * 24 - 20000) == 3274   # total interest in the same illustration


def test_schedule_amortises_to_zero_and_sums_to_the_principal():
    rows = pricing.schedule(2_000_000, 0.0975, 120)
    assert len(rows) == 120 and rows[0]["outstanding"] == 2_000_000 and abs(sum(r["principal"] for r in rows) - 2_000_000) <= 120
    assert rows[-1]["principal"] == rows[-1]["outstanding"]


def test_rate_shock_is_directionally_right():
    s = pricing.rate_shock(5_000_000, 0.0975, 240)
    assert s["emi_change"] > 0 and s["epi_count_change"] > 0


def test_kfs_follows_annex_i_and_para_29_and_30():
    k = pricing.build_kfs(3_000_000, 0.0975, 240, "HL", "P-T1")
    a = k["annex_i"]
    assert k["proposal_no"] == "P-T1" and k["validity_working_days"] >= 3
    assert [i["no"] for i in a["part1"]] == list(range(1, 11)) and [i["no"] for i in a["part2"]] == list(range(1, 7))
    assert a["part1"][6]["value"]["benchmark_pct"] == 5.5 and a["part1"][8]["value"].endswith("%")
    ids = {d["id"] for d in k["other_disclosures"]}
    assert {"no_other_fees", "validity", "rate_basis", "reset_options", "penal"} <= ids
    penal = next(d for d in k["other_disclosures"] if d["id"] == "penal")
    assert "not added to the interest rate" in penal["value"] and "para 30" in penal["basis"]
    assert "para 34(1)" in k["foreclosure_charges"]
    assert any(r[0].startswith("APR") for r in a["apr_sheet"])


def test_validity_skips_weekends():
    fri = datetime(2026, 11, 6, 10, tzinfo=timezone.utc).timestamp()          # a Friday
    assert _validity(fri) == "2026-11-11"                                       # Mon, Tue, Wed


def test_schedule_endpoint_and_acknowledgement_are_kept_on_record():
    with KeyedClient(app) as c:
        cid = c.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()["case_id"]
        rows = c.get(f"/api/cases/{cid}/schedule").json()["rows"]
        assert len(rows) > 12
        v0 = c.get(f"/api/cases/{cid}").json()
        assert v0["kfs_valid_until"] and v0["kfs_ack"] is None
        r = c.post(f"/api/cases/{cid}/kfs-ack").json()
        assert r["ok"] and c.get(f"/api/cases/{cid}").json()["kfs_ack"]["reference"] == r["reference"]
        assert c.post(f"/api/cases/{cid}/kfs-ack").json()["reference"] == r["reference"]          # idempotent
        refer = c.post("/api/applications", json={"scenario_id": "refer_gap"}).json()["case_id"]
        assert c.get(f"/api/cases/{refer}/schedule").status_code == 409
