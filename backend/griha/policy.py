"""Policy-as-code engine. Rules live in YAML, are versioned and hashed, and every evaluation returns a full trace."""
from __future__ import annotations

import copy
import hashlib
import json
import operator
from pathlib import Path
from typing import Any

import yaml

OPS = {"lt": operator.lt, "le": operator.le, "gt": operator.gt, "ge": operator.ge, "eq": operator.eq, "ne": operator.ne}


class Policy:
    def __init__(self, data: dict):
        self.data = data

    @classmethod
    def load(cls, path: str | Path) -> "Policy":
        return cls(yaml.safe_load(Path(path).read_text()))

    @property
    def version(self) -> str:
        return str(self.data["version"])

    @property
    def params(self) -> dict:
        return self.data["params"]

    def hash(self) -> str:
        return hashlib.sha256(json.dumps(self.data, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def ltv_cap(self, product: str, amount: float) -> float:
        for band in self.data["ltv_caps"][product]:
            if band["up_to"] is None or amount <= band["up_to"]:
                return float(band["cap"])
        return 0.0

    def tenure_cap_years(self, product: str) -> float:
        return float(self.data["tenure_cap_years"][product])

    def with_changes(self, changes: dict[str, Any]) -> "Policy":
        """Return a copy with dotted-path changes, e.g. {'params.foir_cap': 0.6}. Used by the policy simulator."""
        d = copy.deepcopy(self.data)
        for path, val in changes.items():
            node = d
            parts = path.split(".")
            for p in parts[:-1]:
                node = node[int(p)] if isinstance(node, list) else node[p]
            last = parts[-1]
            if isinstance(node, list):
                node[int(last)] = val
            else:
                node[last] = val
        return Policy(d)

    def evaluate(self, metrics: dict[str, Any]) -> list[dict]:
        results = []
        for rule in self.data["rules"]:
            actual = metrics.get(rule["metric"])
            res = {"id": rule["id"], "title": rule["title"], "metric": rule["metric"], "actual": actual,
                   "outcome": "pass", "threshold": None, "reason": None}
            if actual is None:
                miss = rule.get("missing", "pass")
                if miss != "pass":
                    res.update(outcome=miss, reason=f"{rule['title']}: data not available")
                results.append(res)
                continue
            for level in ("reject_if", "refer_if"):
                cond = rule.get(level)
                if not cond:
                    continue
                thr = cond.get("value")
                if "value_param" in cond:
                    thr = self.params[cond["value_param"]]
                if "value_metric" in cond:
                    thr = metrics[cond["value_metric"]]
                if OPS[cond["op"]](actual, thr):
                    res.update(outcome=level.split("_")[0], threshold=thr,
                               reason=rule["reason"].format(actual=actual, threshold=thr))
                    break
            else:
                res["threshold"] = next((rule[l].get("value", rule[l].get("value_param")) for l in ("reject_if", "refer_if") if rule.get(l)), None)
            results.append(res)
        return results
