from griha import config, sources
from tests.keyed import KeyedClient
from griha.api import app


def test_rates_derive_from_the_repo_rate_and_numbers_are_unchanged():
    assert abs(config.BASE_RATE - (config.REPO_RATE + config.LENDER_SPREAD)) < 1e-9
    assert abs(config.UW_RATE - (config.BASE_RATE + config.STRESS_BUFFER)) < 1e-9
    assert config.REPO_RATE == 0.055 and config.BASE_RATE == 0.095 and config.UW_RATE == 0.115     # RBI 5.50% (21 Oct 2026 minutes)


def test_every_real_source_has_a_link_a_date_and_a_status():
    reg = sources.registry()
    assert len({r["id"] for r in reg}) == len(reg)
    for r in reg:
        assert r["status"] in {"verified", "pending", "synthetic", "internal", "rejected"} and r["name"] and r["used_for"]
        if r["group"] == "real":
            assert r["url"].startswith("https://") and r["retrieved"] and r["status"] == "verified"
        if r["status"] in {"synthetic", "internal"}:
            assert r["url"] == ""                      # nothing is dressed up as an external source


def test_residex_figures_are_the_published_ones():
    r = sources.RESIDEX
    assert r["composite_yoy_pct"] == 5.0 and r["city_yoy_pct"]["Mumbai"] == 3.7 and r["city_yoy_pct"]["Bengaluru"] == 12.7
    assert sources.market_context("Pune")["city_yoy_pct"] == 3.5 and sources.market_context("Jaipur")["city_yoy_pct"] is None


def test_sources_endpoint_and_case_market_context():
    with KeyedClient(app) as c:
        d = c.get("/api/sources").json()
        assert d["rates"]["repo_pct"] == 5.5 and d["rates"]["base_pct"] == 9.5 and any(i["id"] == "nhb-residex" for i in d["items"])
        case = c.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
        mc = case["market_context"]
        assert mc["source"] == "NHB RESIDEX" and mc["composite_yoy_pct"] == 5.0 and mc["city"] == case["property"]["city"] if "property" in case else True


def test_impact_separates_measured_from_assumed_and_the_arithmetic_holds():
    with KeyedClient(app) as c:
        d = c.get("/api/impact", params={"manual_minutes": 60, "review_minutes": 30, "cost_per_hour": 600, "files_per_month": 2000}).json()
        m, a, k = d["measured"], d["assumed"], d["computed"]
        assert m["n"] == 1000 and abs(m["approve_rate"] + m["refer_rate"] + m["reject_rate"] - 1) < 1e-3
        assert abs(m["straight_through_rate"] - (m["approve_rate"] + m["reject_rate"])) < 1e-3
        assert a["manual_minutes_per_file"] == 60 and "not measured" in a["note"]
        assert abs(k["officer_minutes_per_file_with_engine"] - m["refer_rate"] * 30) < 0.02
        assert abs(k["cost_per_file_manual_inr"] - 600.0) < 0.01
        assert abs(k["cost_saved_per_month_inr"] - 2000 * (k["cost_per_file_manual_inr"] - k["cost_per_file_with_engine_inr"])) < 2
        assert m["engine_ms_median"] > 0 and m["source"].startswith("1000 synthetic")
        wild = c.get("/api/impact", params={"manual_minutes": 99999, "cost_per_hour": -5}).json()["assumed"]       # inputs are clamped, never trusted
        assert wild["manual_minutes_per_file"] == 600 and wild["officer_cost_per_hour_inr"] == 50
