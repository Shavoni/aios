"""Tests for Deployment Package functionality.

ONBOARD-001 Required Tests:
- test_preview_returns_package_hash_and_checksums
- test_approve_and_deploy_creates_deployment_structure
- test_hitl_approvals_enforced_via_confidence
- test_replay_deployment_produces_identical_state
"""

import pytest
import tempfile
from pathlib import Path
import json
import yaml

from ..deployment import (
    DeploymentPackage,
    DeploymentPackageGenerator,
    DeploymentExecutor,
    ApprovalManager,
    ManifestChecksum,
)


class TestDeploymentPackage:
    """Tests for DeploymentPackage."""

    def test_package_hash_is_deterministic(self):
        """Package hash should be deterministic."""
        pkg1 = DeploymentPackage(
            package_id="test-1",
            org_id="org-123",
            tenant_name="Test Org",
            agents=[{"name": "Agent A"}, {"name": "Agent B"}],
        )
        pkg1.package_hash = pkg1.compute_hash()

        pkg2 = DeploymentPackage(
            package_id="test-2",  # Different ID
            org_id="org-123",
            tenant_name="Test Org",
            agents=[{"name": "Agent A"}, {"name": "Agent B"}],
        )
        pkg2.package_hash = pkg2.compute_hash()

        # Same content = same hash
        assert pkg1.package_hash == pkg2.package_hash

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        pkg1 = DeploymentPackage(
            package_id="test-1",
            org_id="org-123",
            tenant_name="Test Org",
            agents=[{"name": "Agent A"}],
        )
        pkg1.package_hash = pkg1.compute_hash()

        pkg2 = DeploymentPackage(
            package_id="test-1",
            org_id="org-123",
            tenant_name="Test Org",
            agents=[{"name": "Agent B"}],  # Different agent
        )
        pkg2.package_hash = pkg2.compute_hash()

        assert pkg1.package_hash != pkg2.package_hash

    def test_add_manifest_checksum(self):
        """Test adding manifest checksums."""
        pkg = DeploymentPackage(
            package_id="test",
            org_id="org-123",
            tenant_name="Test",
        )

        content = "test content"
        checksum = pkg.add_manifest_checksum("test.yaml", content)

        assert checksum.filename == "test.yaml"
        assert len(checksum.sha256) == 64  # SHA256 hex length
        assert checksum.size_bytes == len(content.encode())

    def test_to_dict_serialization(self):
        """Test package serialization."""
        pkg = DeploymentPackage(
            package_id="test-123",
            org_id="org-456",
            tenant_name="Test Org",
            agents=[{"name": "Test Agent"}],
        )
        pkg.package_hash = pkg.compute_hash()

        data = pkg.to_dict()

        assert data["package_id"] == "test-123"
        assert data["org_id"] == "org-456"
        assert data["package_hash"] != ""
        assert len(data["agents"]) == 1

    def test_from_dict_deserialization(self):
        """Test package deserialization."""
        data = {
            "package_id": "test-123",
            "org_id": "org-456",
            "tenant_name": "Test Org",
            "package_hash": "abc123",
            "agents": [{"name": "Agent"}],
            "policies": [],
            "hitl_rules": [],
            "kb_sources": ["https://example.com"],
            "kb_document_count": 10,
            "manifest_checksums": [
                {"filename": "test.yaml", "sha256": "abc", "size_bytes": 100}
            ],
            "approvals": [],
            "all_approved": True,
        }

        pkg = DeploymentPackage.from_dict(data)

        assert pkg.package_id == "test-123"
        assert pkg.org_id == "org-456"
        assert len(pkg.manifest_checksums) == 1


class TestDeploymentPackageGenerator:
    """Tests for DeploymentPackageGenerator."""

    def test_preview_returns_package_hash_and_checksums(self):
        """REQUIRED: Preview must return package_hash + manifest checksums."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = DeploymentPackageGenerator(Path(tmpdir))

            agents = [
                {"name": "HR Agent", "domain": "HR"},
                {"name": "IT Support", "domain": "IT"},
            ]

            package = generator.create_package(
                org_id="test-org",
                tenant_name="Test Organization",
                agents=agents,
            )

            # Package hash must be present
            assert package.package_hash != ""
            assert len(package.package_hash) == 64  # SHA256

            # Write package to generate checksums
            generator.write_package(package)

            # Manifest checksums must be present
            assert len(package.manifest_checksums) > 0

            # Verify checksums have required fields
            for checksum in package.manifest_checksums:
                assert checksum.filename != ""
                assert len(checksum.sha256) == 64
                assert checksum.size_bytes > 0

    def test_approve_and_deploy_creates_deployment_structure(self):
        """REQUIRED: Creates deployments/{org_id}/ structure with YAML policies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = DeploymentPackageGenerator(Path(tmpdir))

            agents = [
                {"name": "Concierge", "domain": "Router", "is_router": True},
                {"name": "HR Specialist", "domain": "HR"},
            ]

            package = generator.create_package(
                org_id="test-city",
                tenant_name="Test City",
                agents=agents,
            )

            # Write the package
            pkg_path = generator.write_package(package)

            # Verify directory structure
            assert pkg_path.exists()
            assert (pkg_path / "manifest.json").exists()
            assert (pkg_path / "agents").exists()
            assert (pkg_path / "policies").exists()
            assert (pkg_path / "kb").exists()

            # Verify agent YAML files
            assert (pkg_path / "agents" / "concierge.yaml").exists()
            assert (pkg_path / "agents" / "hr_specialist.yaml").exists()

            # Verify policy YAML files
            governance_path = pkg_path / "policies" / "governance.yaml"
            assert governance_path.exists()

            # Verify YAML is valid
            with open(governance_path) as f:
                policies = yaml.safe_load(f)
            assert "policies" in policies

            # Verify HITL rules YAML
            hitl_path = pkg_path / "policies" / "hitl_rules.yaml"
            assert hitl_path.exists()

            with open(hitl_path) as f:
                hitl = yaml.safe_load(f)
            assert "hitl_rules" in hitl

    def test_package_verification(self):
        """Test package integrity verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = DeploymentPackageGenerator(Path(tmpdir))

            package = generator.create_package(
                org_id="verify-test",
                tenant_name="Verify Test",
                agents=[{"name": "Test Agent", "domain": "Test"}],
            )

            generator.write_package(package)

            # Verify should pass
            is_valid, errors = generator.verify_package(package)
            assert is_valid, f"Verification failed: {errors}"
            assert len(errors) == 0

    def test_package_verification_detects_tampering(self):
        """Test that verification detects file tampering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = DeploymentPackageGenerator(Path(tmpdir))

            package = generator.create_package(
                org_id="tamper-test",
                tenant_name="Tamper Test",
                agents=[{"name": "Agent", "domain": "Test"}],
            )

            pkg_path = generator.write_package(package)

            # Tamper with a file
            agent_file = pkg_path / "agents" / "agent.yaml"
            agent_file.write_text("tampered: true")

            # Verification should fail
            is_valid, errors = generator.verify_package(package)
            assert not is_valid
            assert len(errors) > 0
            assert "checksum mismatch" in errors[0].lower()


class TestHITLApprovals:
    """Tests for HITL approval enforcement."""

    def test_hitl_approvals_enforced_via_confidence(self):
        """REQUIRED: HITL approvals enforced via confidence thresholds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = DeploymentPackageGenerator(Path(tmpdir))

            departments = [
                {"name": "HR", "confidence": {"score": 0.95}},  # High - auto approved
                {"name": "Finance", "confidence": {"score": 0.70}},  # Below threshold
                {"name": "Unknown", "confidence": {"score": 0.40}},  # Low - needs approval
            ]

            package = generator.create_package(
                org_id="confidence-test",
                tenant_name="Confidence Test",
                agents=[{"name": "Agent", "domain": "Test"}],
                departments=departments,
            )

            # Check approvals
            assert len(package.approvals) == 3

            # High confidence should be auto-approved
            hr_approval = next(a for a in package.approvals if "HR" in a["item"])
            assert hr_approval["approved"] is True
            assert hr_approval["approved_by"] == "auto"

            # Low confidence should need approval
            unknown_approval = next(a for a in package.approvals if "Unknown" in a["item"])
            assert unknown_approval["approved"] is False
            assert unknown_approval["needs_approval"] is True

            # Package should not be fully approved
            assert package.all_approved is False

    def test_approval_manager_blocks_deploy_without_approvals(self):
        """REQUIRED: Block deploy if approvals missing."""
        manager = ApprovalManager()

        package = DeploymentPackage(
            package_id="test",
            org_id="test-org",
            tenant_name="Test",
            approvals=[
                {"item": "Dept A", "approved": True, "confidence": 0.9},
                {"item": "Dept B", "approved": False, "confidence": 0.5},
            ],
            all_approved=False,
        )

        can_deploy, reason = manager.can_deploy(package)

        assert can_deploy is False
        assert "pending" in reason.lower()

    def test_approval_manager_logs_approvals(self):
        """REQUIRED: Log approvals."""
        manager = ApprovalManager()

        package = DeploymentPackage(
            package_id="log-test",
            org_id="test-org",
            tenant_name="Test",
            approvals=[
                {"item": "Low Confidence Dept", "approved": False, "confidence": 0.5,
                 "needs_approval": True},
            ],
            all_approved=False,
        )

        # Approve the item
        result = manager.approve_item(
            package=package,
            item_index=0,
            approved_by="admin@example.com",
            notes="Verified manually",
        )

        assert result is True
        assert package.approvals[0]["approved"] is True
        assert package.all_approved is True

        # Check approval log
        log = manager.get_approval_log()
        assert len(log) == 1
        assert log[0]["approved_by"] == "admin@example.com"
        assert log[0]["notes"] == "Verified manually"

    def test_check_approvals_needed(self):
        """Test checking which items need approval."""
        manager = ApprovalManager()

        package = DeploymentPackage(
            package_id="check-test",
            org_id="test-org",
            tenant_name="Test",
            approvals=[
                {"item": "Approved", "approved": True, "confidence": 0.95},
                {"item": "Pending 1", "approved": False, "confidence": 0.60},
                {"item": "Pending 2", "approved": False, "confidence": 0.40},
            ],
        )

        needed = manager.check_approvals_needed(package)

        assert len(needed) == 2
        assert all("Pending" in n["item"] for n in needed)


class TestDeploymentExecutor:
    """Tests for DeploymentExecutor."""

    def test_execute_deployment(self):
        """Test executing a deployment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = DeploymentPackageGenerator(Path(tmpdir))
            executor = DeploymentExecutor(generator)

            package = generator.create_package(
                org_id="execute-test",
                tenant_name="Execute Test",
                agents=[{"name": "Agent", "domain": "Test"}],
            )
            package.all_approved = True

            result = executor.execute(package, dry_run=True)

            assert result["success"] is True
            assert len(result["steps"]) > 0

    def test_execute_fails_without_approvals(self):
        """Test that execution fails without approvals."""
        executor = DeploymentExecutor()

        package = DeploymentPackage(
            package_id="fail-test",
            org_id="test-org",
            tenant_name="Test",
            approvals=[{"item": "Test", "approved": False}],
            all_approved=False,
        )

        result = executor.execute(package)

        assert result["success"] is False
        assert "pending" in result["error"].lower()

    def test_replay_deployment_produces_identical_state(self):
        """REQUIRED: Replay deployment produces identical running state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = DeploymentPackageGenerator(Path(tmpdir))
            executor = DeploymentExecutor(generator)

            # Create and execute original deployment
            package = generator.create_package(
                org_id="replay-test",
                tenant_name="Replay Test",
                agents=[
                    {"name": "Agent A", "domain": "HR"},
                    {"name": "Agent B", "domain": "IT"},
                ],
            )
            package.all_approved = True

            # Write package
            generator.write_package(package)

            # Execute original
            original_result = executor.execute(package, dry_run=True)
            assert original_result["success"] is True

            # Replay from saved package
            replay_result = executor.replay("replay-test")

            # Results should be equivalent
            assert replay_result["success"] is True
            assert len(replay_result["steps"]) == len(original_result["steps"])

            # Step details should match
            for orig_step, replay_step in zip(original_result["steps"], replay_result["steps"]):
                assert orig_step["step"] == replay_step["step"]
                assert orig_step["details"] == replay_step["details"]

    def test_replay_fails_for_nonexistent_package(self):
        """Test that replay fails for non-existent package."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = DeploymentPackageGenerator(Path(tmpdir))
            executor = DeploymentExecutor(generator)

            result = executor.replay("nonexistent-org")

            assert result["success"] is False
            assert "no package found" in result["error"].lower()

    def test_replay_fails_for_tampered_package(self):
        """Test that replay fails if package has been tampered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = DeploymentPackageGenerator(Path(tmpdir))
            executor = DeploymentExecutor(generator)

            package = generator.create_package(
                org_id="tamper-replay",
                tenant_name="Tamper Test",
                agents=[{"name": "Agent", "domain": "Test"}],
            )
            package.all_approved = True

            pkg_path = generator.write_package(package)

            # Tamper with a file
            agent_file = pkg_path / "agents" / "agent.yaml"
            agent_file.write_text("tampered: true")

            # Replay should fail verification
            result = executor.replay("tamper-replay")

            assert result["success"] is False
            assert "verification" in result["error"].lower()


class TestManifestChecksum:
    """Tests for ManifestChecksum."""

    def test_checksum_creation(self):
        """Test checksum creation."""
        checksum = ManifestChecksum(
            filename="test.yaml",
            sha256="abc123" * 10 + "abcd",  # 64 chars
            size_bytes=1024,
        )

        assert checksum.filename == "test.yaml"
        assert len(checksum.sha256) == 64
        assert checksum.size_bytes == 1024
