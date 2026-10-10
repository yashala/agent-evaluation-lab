"""In-memory store of the synthetic support data, copied per case so cases can patch it."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "fixtures.json"


@dataclass
class FixtureStore:
    today: date
    customers: dict[str, dict[str, Any]]
    orders: dict[str, dict[str, Any]]
    shipments: dict[str, dict[str, Any]]
    policies: dict[str, dict[str, Any]]
    articles: list[dict[str, Any]]

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH, patch: dict[str, Any] | None = None) -> FixtureStore:
        raw = json.loads(path.read_text())
        if patch:
            raw = apply_patch(raw, patch)
        return cls(
            today=date.fromisoformat(raw["today"]),
            customers={c["id"]: c for c in raw["customers"]},
            orders={o["id"]: o for o in raw["orders"]},
            shipments={s["tracking_id"]: s for s in raw["shipments"]},
            policies={p["region"]: p for p in raw["refund_policies"]},
            articles=raw["kb_articles"],
        )

    def customer_by_email(self, email: str) -> dict[str, Any] | None:
        return next((c for c in self.customers.values() if c["email"] == email.lower()), None)


def apply_patch(raw: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Patch list entries by id: {"orders": {"ORD-20417": {"status": "delivered"}}}.

    Used by cases that need contradictory data (an order and its shipment disagreeing) without
    changing the shared fixture file.
    """
    out = copy.deepcopy(raw)
    keys = {
        "customers": "id",
        "orders": "id",
        "shipments": "tracking_id",
        "refund_policies": "region",
        "kb_articles": "id",
    }
    for collection, changes in patch.items():
        if collection == "today":
            out["today"] = changes
            continue
        key = keys[collection]
        for item_id, fields in changes.items():
            target = next((x for x in out[collection] if x[key] == item_id), None)
            if target is None:
                out[collection].append({key: item_id, **fields})
            else:
                target.update(fields)
    return out
