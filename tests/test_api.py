"""API endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from packages.api import app


@pytest.fixture
def client() -> TestClient:
    """Test client fixture."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        """Health endpoint returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"

    def test_health_shows_no_policies_initially(self, client: TestClient) -> None:
        """Health endpoint shows no policies loaded initially."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["policies_loaded"] is False


class TestClassifyEndpoint:
    """Tests for the intent classification endpoint."""

    def test_classify_public_statement(self, client: TestClient) -> None:
        """Classifies public statement as Comms domain."""
        response = client.post("/classify", json={"text": "Draft a public statement"})
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "Comms"
        assert data["audience"] == "public"

    def test_classify_contract_review(self, client: TestClient) -> None:
        """Classifies contract review as Legal domain."""
        response = client.post("/classify", json={"text": "Review the NDA contract"})
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "Legal"

    def test_classify_empty_text_rejected(self, client: TestClient) -> None:
        """Empty text is rejected with 422."""
        response = client.post("/classify", json={"text": ""})
        assert response.status_code == 422


class TestRisksEndpoint:
    """Tests for the risk detection endpoint."""

    def test_detect_pii_risk(self, client: TestClient) -> None:
        """Detects PII risk signal."""
        response = client.post(
            "/risks", json={"text": "Send me the employee salary information"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "PII" in data["signals"]

    def test_detect_legal_contract_risk(self, client: TestClient) -> None:
        """Detects legal contract risk signal."""
        response = client.post("/risks", json={"text": "Review this NDA agreement"})
        assert response.status_code == 200
        data = response.json()
        assert "LEGAL_CONTRACT" in data["signals"]

    def test_no_risks_for_safe_text(self, client: TestClient) -> None:
        """No risks detected for safe text."""
        response = client.post("/risks", json={"text": "What is the weather today?"})
        assert response.status_code == 200
        data = response.json()
        assert data["signals"] == []


class TestGovernanceEndpoint:
    """Tests for the governance evaluation endpoint."""

    def test_evaluate_governance_returns_decision(self, client: TestClient) -> None:
        """Governance evaluation returns a decision."""
        response = client.post(
            "/governance/evaluate",
            json={
                "text": "Draft a public statement",
                "tenant_id": "test-tenant",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "hitl_mode" in data
        assert "tools_allowed" in data
        assert "provider_constraints" in data

    def test_evaluate_governance_requires_tenant_id(self, client: TestClient) -> None:
        """Governance evaluation requires tenant_id."""
        response = client.post(
            "/governance/evaluate",
            json={"text": "Draft a public statement"},
        )
        assert response.status_code == 422


class TestPoliciesEndpoint:
    """Tests for the policies endpoints."""

    def test_get_policies_returns_empty_initially(self, client: TestClient) -> None:
        """Get policies returns empty policy set initially."""
        response = client.get("/policies")
        assert response.status_code == 200
        data = response.json()
        assert data["constitutional_rules"] == []

    def test_load_policies_success(self, client: TestClient) -> None:
        """Load policies successfully."""
        policy_config = {
            "constitutional_rules": [
                {
                    "id": "test-rule",
                    "name": "Test Rule",
                    "conditions": [
                        {"field": "intent.audience", "operator": "eq", "value": "public"}
                    ],
                    "action": {"hitl_mode": "DRAFT"},
                }
            ]
        }
        response = client.post("/policies", json=policy_config)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestSimulationEndpoint:
    """Tests for the simulation endpoints."""

    def test_simulate_single_returns_result(self, client: TestClient) -> None:
        """Single simulation returns complete result."""
        response = client.post(
            "/simulate",
            json={
                "text": "Review this contract",
                "tenant_id": "test-tenant",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "intent" in data
        assert "risk" in data
        assert "governance" in data
        assert "agent_id" in data
        assert "audit_event_stub" in data
        assert data["audit_event_stub"]["simulation_mode"] is True

    def test_simulate_batch_returns_results(self, client: TestClient) -> None:
        """Batch simulation returns multiple results."""
        response = client.post(
            "/simulate/batch",
            json={
                "tenant_id": "test-tenant",
                "inputs": [
                    {"text": "Draft a public statement"},
                    {"text": "Review the contract"},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2
        assert data["tools_executed"] == 0
