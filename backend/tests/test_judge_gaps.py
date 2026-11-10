"""Tests for the gaps found in the judge's audit: fairness statistics, the Hindi KFS, and the real-data validation record."""
import json

from griha import config
from griha.pricing import build_kfs
from griha.simulate import fair_row


def test_fairness_ratio_below_80_is_not_called_bias_when_the_interval_includes_80():
    # 115 vs 285 applicants at 43.5% vs 54.7%: ratio 0.795, but the 95% interval straddles 0.80
    r = fair_row("gender", {"F": [115, 50], "M": [285, 156]})
    assert r["ratio"] < 0.8 and r["flag"] == "below_80_not_significant" and r["ci95"][0] < 0.8 < r["ci95"][1]


def test_fairness_flags_a_gap_that_is_clear_in_a_large_sample():
    r = fair_row("tier", {"1": [4000, 2400], "2": [4000, 1600]})
    assert r["ratio"] == 0.667 and r["flag"] == "below_80_significant"
    assert fair_row("tier", {"1": [4000, 2400], "2": [4000, 2300]})["flag"] == "ok"
    assert fair_row("tier", {"1": [10, 5], "2": [10, 5]}) is None          # groups under 20 are not compared


def test_hindi_kfs_mirrors_the_english_one_item_for_item_and_keeps_the_numbers():
    for product in ("HL", "LAP"):
        k = build_kfs(3_000_000, 0.0955, 240, product, "P-X")
        en, hi = k["annex_i"], k["hi"]["annex_i"]
        for part in ("part1", "part2"):
            assert [i["no"] for i in en[part]] == [i["no"] for i in hi[part]]
            assert [bool(i.get("lender_to_set")) for i in en[part]] == [bool(i.get("lender_to_set")) for i in hi[part]]
        assert len(en["apr_sheet"]) == len(hi["apr_sheet"]) and en["apr_sheet"][-1][1] == hi["apr_sheet"][-1][1]   # same APR line
        assert en["part1"][8]["value"] == hi["part1"][8]["value"]                       # APR identical
        assert en["part1"][6]["value"]["impact_of_25_bps"] == hi["part1"][6]["value"]["impact_of_25_bps"]
        assert [d["id"] for d in k["other_disclosures"]] == [d["id"] for d in k["hi"]["other_disclosures"]]
        assert [d["lender_to_set"] for d in k["other_disclosures"]] == [d["lender_to_set"] for d in k["hi"]["other_disclosures"]]
        assert k["hi"]["reviewed_by_legal_translator"] is False
        assert any("ऀ" <= ch <= "ॿ" for ch in hi["part1"][1]["item"])           # Devanagari


def test_real_data_validation_record_exists_and_states_its_limits():
    p = config.ARTIFACTS / "real_data_validation.json"
    assert p.exists(), "run: uv run python -m tools.validate_public"
    d = json.loads(p.read_text())
    assert "not Indian mortgages" in d["note"] and len(d["results"]) == 2
    for r in d["results"]:
        assert r["gbm_monotone"]["auc"] > 0.7                                        # ranks real defaults
        assert abs(r["gbm_monotone"]["auc"] - r["gbm_free"]["auc"]) < 0.02            # the monotone constraints cost almost nothing
        assert r["calibration_gap_mean_abs"] < 0.03                                   # isotonic probabilities match observed rates out of sample
