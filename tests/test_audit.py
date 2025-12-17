import pytest
import logging
from unittest.mock import MagicMock

# Import the function we want to test from the main script
from runner import audit_device

# We override the GLOBAL_RULES from the main script to ensure consistency in tests
MOCK_RULES = {
    "static_routes": [{"prefix": "192.168.10.0/24", "next_hop": "10.1.1.2"}],
    "bgp": {"neighbors": [{"ip": "10.2.2.2", "state": "Established"}]},
    "ospf": {"neighbors": [{"neighbor_id": "2.2.2.2", "state": "FULL"}]},
}


@pytest.fixture(autouse=True)
def patch_rules(monkeypatch):
    """Overwrite the GLOBAL_RULES in runner.py with our test rules."""
    monkeypatch.setattr("runner.GLOBAL_RULES", MOCK_RULES)


def test_audit_full_compliance(caplog, mock_route_pass, mock_bgp_pass, mock_ospf_pass):
    """
    Scenario: The router is perfectly compliant.
    Expected: Logs should contain [PASS] and no [FAIL].
    """
    # 1. Create a Mock Task object (simulating Nornir task)
    mock_task = MagicMock()
    mock_task.host.name = "TEST_ROUTER_1"

    # 2. Setup the "Side Effects"
    # When task.run() is called:
    #   1st time (Route) -> returns mock_route_pass
    #   2nd time (BGP)   -> returns mock_bgp_pass
    #   3rd time (OSPF)  -> returns mock_ospf_pass
    mock_task.run.side_effect = [
        MagicMock(result=mock_route_pass),
        MagicMock(result=mock_bgp_pass),
        MagicMock(result=mock_ospf_pass),
    ]

    # 3. Run the actual function
    with caplog.at_level(logging.INFO):
        audit_device(mock_task)

    # 4. Assertions
    assert "TEST_ROUTER_1: [PASS] Route 192.168.10.0/24 correct." in caplog.text
    assert "TEST_ROUTER_1: [PASS] BGP Neighbor 10.2.2.2 Established" in caplog.text
    assert "TEST_ROUTER_1: [PASS] OSPF Neighbor 2.2.2.2 FULL" in caplog.text
    assert "FAIL" not in caplog.text


def test_audit_route_fail(caplog, mock_route_fail, mock_bgp_pass, mock_ospf_pass):
    """
    Scenario: Route exists but has wrong next-hop.
    Expected: Logs should contain [FAIL] for route.
    """
    mock_task = MagicMock()
    mock_task.host.name = "TEST_ROUTER_BAD"

    mock_task.run.side_effect = [
        MagicMock(result=mock_route_fail),  # <--- Failing data
        MagicMock(result=mock_bgp_pass),
        MagicMock(result=mock_ospf_pass),
    ]

    with caplog.at_level(logging.INFO):
        audit_device(mock_task)

    assert "[FAIL] Route 192.168.10.0/24 next-hop mismatch" in caplog.text


def test_audit_bgp_fail(caplog, mock_route_pass, mock_bgp_fail, mock_ospf_pass):
    """
    Scenario: BGP Neighbor is Active (Down).
    Expected: Logs should contain [FAIL] for BGP.
    """
    mock_task = MagicMock()
    mock_task.host.name = "TEST_ROUTER_BGP_DOWN"

    mock_task.run.side_effect = [
        MagicMock(result=mock_route_pass),
        MagicMock(result=mock_bgp_fail),  # <--- Failing data
        MagicMock(result=mock_ospf_pass),
    ]

    with caplog.at_level(logging.INFO):
        audit_device(mock_task)

    assert "[FAIL] BGP Neighbor 10.2.2.2 is Active" in caplog.text


def test_parsing_error_handling(caplog):
    """
    Scenario: The Router returns garbage or connection fails (Empty Dict).
    Expected: Script should not crash, should log error.
    """
    mock_task = MagicMock()
    mock_task.host.name = "TEST_ROUTER_ERROR"

    # Simulate Genie failing to parse and returning an empty dict or None
    mock_task.run.return_value.result = {}

    # We set side_effect to None so it always returns the default empty mock above
    mock_task.run.side_effect = None

    with caplog.at_level(logging.INFO):
        audit_device(mock_task)

    # Should fail safely because the specific keys are missing
    assert "[FAIL]" in caplog.text
