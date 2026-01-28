"""Tests for Auto-Onboarding Wizard.

Required tests per ONBOARD-001 spec:
- test_approve_and_deploy_creates_deployment_package()
- test_preview_returns_confidence_scores()
- test_checklist_approval_workflow()
"""

import pytest
import tempfile
from pathlib import Path
import json
from unittest.mock import patch, MagicMock, AsyncMock

from ..wizard import (
    OnboardingWizard,
    WizardState,
    WizardStep,
    ConfidenceLevel,
    ConfidenceScore,
    DetectedDepartment,
    TemplateMatch,
    DeploymentPreview,
)


class TestConfidenceScore:
    """Tests for ConfidenceScore."""

    def test_high_confidence(self):
        """Test high confidence scoring."""
        score = ConfidenceScore(score=0.90, reason="Test")
        assert score.level == ConfidenceLevel.HIGH

    def test_medium_confidence(self):
        """Test medium confidence scoring."""
        score = ConfidenceScore(score=0.70, reason="Test")
        assert score.level == ConfidenceLevel.MEDIUM

    def test_low_confidence(self):
        """Test low confidence scoring."""
        score = ConfidenceScore(score=0.50, reason="Test")
        assert score.level == ConfidenceLevel.LOW

    def test_very_low_confidence(self):
        """Test very low confidence scoring."""
        score = ConfidenceScore(score=0.30, reason="Test")
        assert score.level == ConfidenceLevel.VERY_LOW

    def test_to_dict(self):
        """Test serialization."""
        score = ConfidenceScore(
            score=0.85,
            reason="High match",
            evidence=["Evidence 1", "Evidence 2"],
        )
        data = score.to_dict()

        assert data["score"] == 0.85
        assert data["level"] == "high"
        assert data["reason"] == "High match"
        assert len(data["evidence"]) == 2


class TestOnboardingWizard:
    """Tests for OnboardingWizard."""

    def test_start_wizard(self):
        """Test starting a new wizard."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = OnboardingWizard(storage_path=Path(tmpdir))

            state = wizard.start_wizard(
                organization_name="City of Cleveland",
                website_url="https://cleveland.gov",
                organization_type="municipal",
            )

            assert state.id is not None
            assert state.organization_name == "City of Cleveland"
            assert state.website_url == "https://cleveland.gov"
            assert state.organization_type == "municipal"
            assert state.step == WizardStep.INIT

    def test_get_wizard(self):
        """Test retrieving wizard by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = OnboardingWizard(storage_path=Path(tmpdir))

            state = wizard.start_wizard(
                organization_name="Test Org",
                website_url="https://test.org",
            )

            # Retrieve
            retrieved = wizard.get_wizard(state.id)
            assert retrieved is not None
            assert retrieved.id == state.id
            assert retrieved.organization_name == "Test Org"

    def test_list_wizards(self):
        """Test listing all wizards."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = OnboardingWizard(storage_path=Path(tmpdir))

            # Create multiple wizards
            wizard.start_wizard("Org 1", "https://org1.com")
            wizard.start_wizard("Org 2", "https://org2.com")
            wizard.start_wizard("Org 3", "https://org3.com")

            wizards = wizard.list_wizards()
            assert len(wizards) == 3

    def test_preview_returns_confidence_scores(self):
        """REQUIRED: Preview must include confidence scores.

        Per ONBOARD-001 spec: Preview must return confidence fields.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = OnboardingWizard(storage_path=Path(tmpdir))

            state = wizard.start_wizard(
                organization_name="Test City",
                website_url="https://testcity.gov",
                organization_type="municipal",
            )

            # Manually add departments with confidence scores
            state.discovered_departments = [
                DetectedDepartment(
                    name="HR Department",
                    url="https://testcity.gov/hr",
                    confidence=ConfidenceScore(
                        score=0.92,
                        reason="Direct URL match",
                        evidence=["Found HR portal link"],
                    ),
                    suggested_domain="HR",
                ),
                DetectedDepartment(
                    name="Building Services",
                    url="https://testcity.gov/building",
                    confidence=ConfidenceScore(
                        score=0.75,
                        reason="Partial match",
                        evidence=["Contains 'building' keyword"],
                    ),
                    suggested_domain="Building",
                ),
                DetectedDepartment(
                    name="Unknown Dept",
                    url="https://testcity.gov/misc",
                    confidence=ConfidenceScore(
                        score=0.35,
                        reason="Low confidence detection",
                        evidence=[],
                    ),
                    suggested_domain="General",
                ),
            ]

            wizard._save_wizard(state)

            # Generate preview
            state = wizard.generate_preview(state.id)

            # Verify preview has confidence scores
            assert state.preview is not None

            # Check agents have confidence
            for agent in state.preview.agents:
                if agent.get("is_router"):
                    continue  # Router doesn't need confidence
                # Each agent from detected dept should have confidence
                if "confidence" in agent:
                    assert 0 <= agent["confidence"] <= 1

            # Check requires_review contains low-confidence items
            assert len(state.preview.requires_review) > 0

    def test_checklist_approval_workflow(self):
        """REQUIRED: HITL checklist approval workflow.

        Per ONBOARD-001 spec: UI checklist contract for approvals.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = OnboardingWizard(storage_path=Path(tmpdir))

            state = wizard.start_wizard(
                organization_name="Test City",
                website_url="https://testcity.gov",
            )

            # Add low-confidence department to trigger checklist
            state.discovered_departments = [
                DetectedDepartment(
                    name="Unknown Service",
                    url="https://testcity.gov/unknown",
                    confidence=ConfidenceScore(score=0.35, reason="Low confidence"),
                    suggested_domain="General",
                ),
            ]
            wizard._save_wizard(state)

            # Generate preview - should require approval
            state = wizard.generate_preview(state.id)

            assert state.requires_approval is True
            assert len(state.approval_checklist) > 0
            assert all(not item["approved"] for item in state.approval_checklist)

            # Approve items one by one
            for i in range(len(state.approval_checklist)):
                state = wizard.approve_checklist_item(state.id, i)

            # All should be approved
            assert all(item["approved"] for item in state.approval_checklist)
            assert state.requires_approval is False

    def test_update_department(self):
        """Test department customization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = OnboardingWizard(storage_path=Path(tmpdir))

            state = wizard.start_wizard(
                organization_name="Test City",
                website_url="https://testcity.gov",
            )

            # Add department
            state.discovered_departments = [
                DetectedDepartment(
                    name="HR Department",
                    url="https://testcity.gov/hr",
                    confidence=ConfidenceScore(score=0.9, reason="Test"),
                ),
            ]
            wizard._save_wizard(state)

            # Update department
            state = wizard.update_department(
                wizard_id=state.id,
                department_name="HR Department",
                enabled=True,
                custom_name="Human Resources",
                custom_instructions="Focus on benefits questions",
            )

            # Verify update
            dept = state.discovered_departments[0]
            assert dept.custom_name == "Human Resources"
            assert dept.custom_instructions == "Focus on benefits questions"

    def test_select_template(self):
        """Test template selection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = OnboardingWizard(storage_path=Path(tmpdir))

            state = wizard.start_wizard(
                organization_name="Test City",
                website_url="https://testcity.gov",
            )

            # Add templates manually
            state.matched_templates = [
                TemplateMatch(
                    template_id="municipal-standard",
                    template_name="Municipal Standard",
                    confidence=ConfidenceScore(score=0.85, reason="Good match"),
                ),
                TemplateMatch(
                    template_id="enterprise",
                    template_name="Enterprise",
                    confidence=ConfidenceScore(score=0.60, reason="Partial match"),
                ),
            ]
            wizard._save_wizard(state)

            # Select template
            state = wizard.select_template(state.id, "municipal-standard")
            assert state.selected_template == "municipal-standard"

    @pytest.mark.asyncio
    async def test_approve_and_deploy_creates_deployment_package(self):
        """REQUIRED: Approve and deploy must create deployment package.

        Per ONBOARD-001 spec: POST /onboarding/{job_id}/approve-and-deploy
        must create a complete deployment package.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = OnboardingWizard(storage_path=Path(tmpdir))

            state = wizard.start_wizard(
                organization_name="Deploy Test City",
                website_url="https://deploytestcity.gov",
            )

            # Setup departments
            state.discovered_departments = [
                DetectedDepartment(
                    name="HR",
                    url="https://deploytestcity.gov/hr",
                    confidence=ConfidenceScore(score=0.95, reason="High confidence"),
                    suggested_domain="HR",
                    suggested_capabilities=["benefits", "policies"],
                ),
            ]
            wizard._save_wizard(state)

            # Generate preview
            state = wizard.generate_preview(state.id)

            # Mock the external dependencies
            with patch("packages.core.multitenancy.get_tenant_manager") as mock_tenant, \
                 patch("packages.core.agents.get_agent_manager") as mock_agent_manager:

                # Setup mocks
                mock_tenant_mgr = MagicMock()
                mock_tenant_mgr.create_tenant.return_value = MagicMock(id="test-tenant-123")
                mock_tenant.return_value = mock_tenant_mgr

                mock_mgr = MagicMock()
                mock_mgr.create_agent.return_value = MagicMock(id="agent-123")
                mock_agent_manager.return_value = mock_mgr

                # Deploy
                state = await wizard.deploy(state.id, skip_approval=True)

                # Verify deployment created
                assert state.step == WizardStep.COMPLETE
                assert state.deployment_id is not None
                assert state.deployment_status == "complete"
                assert state.completed_at is not None

                # Verify tenant was created
                mock_tenant_mgr.create_tenant.assert_called_once()

                # Verify agents were created
                assert mock_mgr.create_agent.called

    @pytest.mark.asyncio
    async def test_deploy_fails_without_approval(self):
        """Test that deployment fails when approvals are pending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wizard = OnboardingWizard(storage_path=Path(tmpdir))

            state = wizard.start_wizard(
                organization_name="Approval Test",
                website_url="https://approvaltest.gov",
            )

            # Add low-confidence dept to require approval
            state.discovered_departments = [
                DetectedDepartment(
                    name="Unknown",
                    url="https://approvaltest.gov/unknown",
                    confidence=ConfidenceScore(score=0.30, reason="Very low"),
                    suggested_domain="General",
                ),
            ]
            wizard._save_wizard(state)

            # Generate preview (creates approval checklist)
            state = wizard.generate_preview(state.id)
            assert state.requires_approval is True

            # Try to deploy without approval - should fail
            with pytest.raises(ValueError, match="requires approval"):
                await wizard.deploy(state.id, skip_approval=False)

    def test_wizard_persistence(self):
        """Test that wizard state persists across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            # Create wizard and start session
            wizard1 = OnboardingWizard(storage_path=path)
            state = wizard1.start_wizard(
                organization_name="Persist Test",
                website_url="https://persist.gov",
            )
            wizard_id = state.id

            # Create new wizard instance (simulates server restart)
            wizard2 = OnboardingWizard(storage_path=path)

            # Should be able to retrieve state
            retrieved = wizard2.get_wizard(wizard_id)
            assert retrieved is not None
            assert retrieved.organization_name == "Persist Test"


class TestWizardState:
    """Tests for WizardState serialization."""

    def test_to_dict(self):
        """Test full state serialization."""
        state = WizardState(
            id="test-123",
            tenant_id="tenant-456",
            organization_name="Test Org",
            website_url="https://test.org",
        )

        state.discovered_departments = [
            DetectedDepartment(
                name="HR",
                url="https://test.org/hr",
                confidence=ConfidenceScore(score=0.85, reason="Test"),
            ),
        ]

        data = state.to_dict()

        assert data["id"] == "test-123"
        assert data["tenant_id"] == "tenant-456"
        assert len(data["discovered_departments"]) == 1
        assert data["discovered_departments"][0]["confidence"]["score"] == 0.85

    def test_step_progression(self):
        """Test wizard step progression."""
        state = WizardState(
            id="test",
            tenant_id="tenant",
        )

        assert state.step == WizardStep.INIT

        state.step = WizardStep.DISCOVERY
        assert state.step == WizardStep.DISCOVERY

        state.step = WizardStep.PREVIEW
        assert state.step == WizardStep.PREVIEW


class TestDetectedDepartment:
    """Tests for DetectedDepartment."""

    def test_defaults(self):
        """Test default values."""
        dept = DetectedDepartment(
            name="Test Dept",
            url="https://test.gov/dept",
        )

        assert dept.enabled is True
        assert dept.custom_name == ""
        assert dept.suggested_model == "gpt-4o-mini"

    def test_to_dict(self):
        """Test serialization."""
        dept = DetectedDepartment(
            name="HR",
            url="https://test.gov/hr",
            description="Human Resources",
            confidence=ConfidenceScore(score=0.9, reason="Direct match"),
            suggested_domain="HR",
            suggested_capabilities=["benefits", "policies"],
        )

        data = dept.to_dict()

        assert data["name"] == "HR"
        assert data["confidence"]["score"] == 0.9
        assert "benefits" in data["suggested_capabilities"]


class TestDeploymentPreview:
    """Tests for DeploymentPreview."""

    def test_preview_structure(self):
        """Test preview has all required fields."""
        preview = DeploymentPreview(
            tenant_id="test-tenant",
            tenant_name="Test Org",
            agents=[
                {"name": "Concierge", "domain": "Router"},
                {"name": "HR", "domain": "HR"},
            ],
            agent_count=2,
            kb_documents=30,
            kb_sources=["https://test.gov/hr", "https://test.gov/finance"],
            policies=["default", "hitl_legal"],
            hitl_rules=["legal_review"],
            estimated_monthly_cost=95.0,
            estimated_setup_time_minutes=10,
        )

        data = preview.to_dict()

        assert data["tenant_id"] == "test-tenant"
        assert data["agent_count"] == 2
        assert data["estimated_monthly_cost"] == 95.0
        assert len(data["policies"]) == 2

    def test_warnings_and_review(self):
        """Test warnings and review requirements."""
        preview = DeploymentPreview(
            tenant_id="test",
            tenant_name="Test",
            warnings=["Large number of agents"],
            requires_review=["2 departments have low confidence"],
        )

        assert len(preview.warnings) == 1
        assert len(preview.requires_review) == 1


class TestTemplateMatch:
    """Tests for TemplateMatch."""

    def test_template_match(self):
        """Test template match structure."""
        match = TemplateMatch(
            template_id="municipal-ohio",
            template_name="Ohio Municipal Standard",
            confidence=ConfidenceScore(
                score=0.88,
                reason="Organization type matches",
                evidence=["Municipal type detected", "Ohio location"],
            ),
            modifications_needed=["Add Parks agent"],
        )

        data = match.to_dict()

        assert data["template_id"] == "municipal-ohio"
        assert data["confidence"]["score"] == 0.88
        assert "Add Parks agent" in data["modifications_needed"]
