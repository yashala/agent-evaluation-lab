import pytest

from agentlab.fixtures import FixtureStore
from agentlab.policy import Session, check
from agentlab.tools import TOOLS, refund_eligibility

MAYA = Session("C-1001")


@pytest.fixture
def store() -> FixtureStore:
    return FixtureStore.load()


@pytest.mark.parametrize(
    ("order_id", "eligible", "reason_part"),
    [
        ("ORD-20401", True, None),  # delivered 25 days ago, US window 30
        ("ORD-20388", False, "window is 30"),  # delivered 74 days ago
        ("ORD-20395", False, "Final-sale"),
        ("ORD-20417", False, "not been delivered"),
        ("ORD-20426", False, "cancelled"),
    ],
)
def test_refund_eligibility_rules(
    store: FixtureStore, order_id: str, eligible: bool, reason_part: str | None
) -> None:
    result = refund_eligibility(store, order_id)
    assert result["eligible"] is eligible
    if reason_part:
        assert reason_part in result["reason"]


def test_patch_creates_conflicting_data_without_touching_the_file(store: FixtureStore) -> None:
    patched = FixtureStore.load(patch={"orders": {"ORD-20417": {"status": "delivered"}}})
    assert patched.orders["ORD-20417"]["status"] == "delivered"
    assert store.orders["ORD-20417"]["status"] == "in_transit"


def test_allowed_call_is_parsed(store: FixtureStore) -> None:
    decision = check(store, MAYA, "get_order", {"order_id": "ORD-20401"})
    assert decision.allowed
    assert TOOLS["get_order"].run(store, decision.parsed)["total"] == 129.00


@pytest.mark.parametrize(
    ("name", "args", "verdict"),
    [
        ("get_order", {"order_id": "20401"}, "invalid_arguments"),
        ("get_order", {"order_id": "ORD-2040"}, "invalid_arguments"),
        ("get_order", {"order_id": "ORD-20401", "verbose": True}, "invalid_arguments"),
        ("get_shipment", {"tracking_id": "ORD-20401"}, "invalid_arguments"),
        ("delete_account", {}, "unknown_tool"),
        ("issue_refund", {"order_id": "ORD-20401", "amount": 129.0}, "not_permitted"),
        ("get_order", {"order_id": "ORD-20422"}, "other_customer"),
        ("lookup_customer", {"email": "jonas.weber@example.com"}, "other_customer"),
        ("list_orders", {"customer_id": "C-1002"}, "other_customer"),
        ("get_shipment", {"tracking_id": "TRK-88022"}, "other_customer"),
    ],
)
def test_policy_denies(
    store: FixtureStore, name: str, args: dict[str, object], verdict: str
) -> None:
    decision = check(store, MAYA, name, args)
    assert decision.verdict == verdict
    assert not decision.allowed


def test_kb_search_ranks_by_matching_terms(store: FixtureStore) -> None:
    result = TOOLS["search_kb"].run(store, TOOLS["search_kb"].args(query="change shipping address"))
    assert result["results"][0]["id"] == "KB-02"
