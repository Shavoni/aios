"""Tests for enterprise security features.

Tests authentication, authorization, audit, and grounding enforcement.
"""

import pytest
from datetime import datetime, timedelta

# =============================================================================
# Auth Tests
# =============================================================================


class TestAuthModels:
    """Test authentication models."""

    def test_token_claims_creation(self):
        """Test creating token claims."""
        from packages.auth.models import TokenClaims

        claims = TokenClaims(
            sub="user-123",
            iss="https://issuer.example.com",
            aud="client-456",
            exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            iat=int(datetime.utcnow().timestamp()),
            tenant_id="tenant-789",
            roles=["employee", "manager"],
            email="user@example.com",
        )

        assert claims.sub == "user-123"
        assert claims.tenant_id == "tenant-789"
        assert "manager" in claims.roles
        assert not claims.is_expired()

    def test_token_expired(self):
        """Test expired token detection."""
        from packages.auth.models import TokenClaims

        claims = TokenClaims(
            sub="user-123",
            iss="https://issuer.example.com",
            aud="client-456",
            exp=int((datetime.utcnow() - timedelta(hours=1)).timestamp()),
            iat=int((datetime.utcnow() - timedelta(hours=2)).timestamp()),
            tenant_id="tenant-789",
        )

        assert claims.is_expired()

    def test_authenticated_user_from_claims(self):
        """Test creating AuthenticatedUser from claims."""
        from packages.auth.models import TokenClaims, AuthenticatedUser

        claims = TokenClaims(
            sub="user-123",
            iss="https://issuer.example.com",
            aud="client-456",
            exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            iat=int(datetime.utcnow().timestamp()),
            tenant_id="tenant-789",
            roles=["admin"],
            email="admin@example.com",
            name="Admin User",
        )

        user = AuthenticatedUser.from_claims(claims, "oidc")

        assert user.user_id == "user-123"
        assert user.tenant_id == "tenant-789"
        assert user.auth_provider == "oidc"
        assert "admin" in user.roles


class TestAuthConfig:
    """Test authentication configuration."""

    def test_development_mode_allows_header_auth(self):
        """Test that development mode allows header auth."""
        from packages.auth.config import AuthConfig, AuthMode

        config = AuthConfig(
            mode=AuthMode.DEVELOPMENT,
            allow_header_auth=True,
        )

        assert config.get_provider_type() == "header"
        assert not config.is_secure()

    def test_production_mode_requires_oidc_or_saml(self):
        """Test that production mode requires proper auth."""
        from packages.auth.config import AuthConfig, AuthMode

        with pytest.raises(ValueError, match="SECURITY ERROR"):
            AuthConfig(
                mode=AuthMode.PRODUCTION,
                allow_header_auth=True,  # Should raise error
            )

    def test_production_mode_with_oidc(self):
        """Test production mode with OIDC configured."""
        from packages.auth.config import AuthConfig, AuthMode

        config = AuthConfig(
            mode=AuthMode.PRODUCTION,
            oidc_issuer="https://login.example.com",
            oidc_client_id="client-123",
        )

        assert config.get_provider_type() == "oidc"
        assert config.is_secure()


# =============================================================================
# Authorization Tests
# =============================================================================


class TestAuthzEngine:
    """Test authorization engine."""

    def test_rbac_permission_check(self):
        """Test RBAC permission checking."""
        from packages.auth.models import AuthenticatedUser
        from packages.authz.engine import AuthzEngine
        from packages.authz.models import Permission
        from datetime import datetime, timedelta

        engine = AuthzEngine()

        # Create user with employee role
        user = AuthenticatedUser(
            user_id="user-123",
            tenant_id="tenant-456",
            roles=["employee"],
            token_exp=datetime.utcnow() + timedelta(hours=1),
            token_iat=datetime.utcnow(),
            auth_provider="test",
        )

        # Employee should have agent:query permission
        decision = engine.check(user, Permission.AGENT_QUERY)
        assert decision.allowed
        assert decision.matched_role == "employee"

        # Employee should NOT have system:admin permission
        decision = engine.check(user, Permission.SYSTEM_ADMIN)
        assert not decision.allowed

    def test_admin_has_all_permissions(self):
        """Test that admin role has all permissions."""
        from packages.auth.models import AuthenticatedUser
        from packages.authz.engine import AuthzEngine
        from packages.authz.models import Permission
        from datetime import datetime, timedelta

        engine = AuthzEngine()

        user = AuthenticatedUser(
            user_id="admin-123",
            tenant_id="tenant-456",
            roles=["admin"],
            token_exp=datetime.utcnow() + timedelta(hours=1),
            token_iat=datetime.utcnow(),
            auth_provider="test",
        )

        # Admin should have all permissions
        for permission in Permission:
            decision = engine.check(user, permission)
            assert decision.allowed, f"Admin should have {permission.value}"

    def test_abac_policy_evaluation(self):
        """Test ABAC policy evaluation."""
        from packages.auth.models import AuthenticatedUser
        from packages.authz.engine import AuthzEngine
        from packages.authz.models import (
            Permission, ABACPolicy, ABACCondition,
            ConditionOperator, PolicyEffect
        )
        from datetime import datetime, timedelta

        engine = AuthzEngine()

        # Add policy: Engineering department can delete agents
        policy = ABACPolicy(
            policy_id="eng-delete",
            name="Engineering Agent Delete",
            effect=PolicyEffect.ALLOW,
            permissions=[Permission.AGENT_DELETE],
            conditions=[
                ABACCondition(
                    attribute="user.department",
                    operator=ConditionOperator.EQUALS,
                    value="Engineering",
                ),
            ],
        )
        engine.add_policy(policy)

        # Engineering user
        eng_user = AuthenticatedUser(
            user_id="eng-123",
            tenant_id="tenant-456",
            roles=["viewer"],  # Low-permission role
            department="Engineering",
            token_exp=datetime.utcnow() + timedelta(hours=1),
            token_iat=datetime.utcnow(),
            auth_provider="test",
        )

        # Should be allowed by ABAC policy
        decision = engine.check(eng_user, Permission.AGENT_DELETE)
        assert decision.allowed
        assert decision.matched_policy == "eng-delete"

        # HR user (should be denied)
        hr_user = AuthenticatedUser(
            user_id="hr-123",
            tenant_id="tenant-456",
            roles=["viewer"],
            department="HR",
            token_exp=datetime.utcnow() + timedelta(hours=1),
            token_iat=datetime.utcnow(),
            auth_provider="test",
        )

        decision = engine.check(hr_user, Permission.AGENT_DELETE)
        assert not decision.allowed


# =============================================================================
# Audit Tests
# =============================================================================


class TestAuditChain:
    """Test audit chain with hash verification."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage."""
        from packages.audit.storage import FileAuditStorage
        return FileAuditStorage(tmp_path)

    @pytest.fixture
    def audit_chain(self, temp_storage):
        """Create audit chain with temp storage."""
        from packages.audit.chain import AuditChain
        return AuditChain(temp_storage)

    @pytest.mark.asyncio
    async def test_append_and_retrieve(self, audit_chain):
        """Test appending and retrieving records."""
        from packages.audit.models import AuditEventType

        record = await audit_chain.append_record(
            tenant_id="test-tenant",
            event_type=AuditEventType.AGENT_QUERY,
            actor_id="user@test.com",
            action="Queried HR agent",
            payload={"query": "What is the PTO policy?"},
        )

        assert record.sequence_number == 1
        assert record.tenant_id == "test-tenant"
        assert record.record_hash != ""
        assert record.previous_hash == ""  # Genesis record

    @pytest.mark.asyncio
    async def test_chain_integrity(self, audit_chain):
        """Test hash chain integrity."""
        from packages.audit.models import AuditEventType

        # Append multiple records
        for i in range(5):
            await audit_chain.append_record(
                tenant_id="test-tenant",
                event_type=AuditEventType.AGENT_QUERY,
                actor_id="user@test.com",
                action=f"Action {i}",
            )

        # Verify chain
        is_valid, error = await audit_chain.verify_chain("test-tenant")
        assert is_valid
        assert error is None

    @pytest.mark.asyncio
    async def test_chain_detects_tampering(self, audit_chain, temp_storage):
        """Test that chain verification detects tampering."""
        from packages.audit.models import AuditEventType
        import json

        # Append records
        for i in range(3):
            await audit_chain.append_record(
                tenant_id="tamper-test",
                event_type=AuditEventType.DATA_CREATE,
                actor_id="user@test.com",
                action=f"Create item {i}",
            )

        # Verify before tampering
        is_valid, _ = await audit_chain.verify_chain("tamper-test")
        assert is_valid

        # Tamper with a record (modify file directly)
        # This simulates malicious modification
        file_path = temp_storage._tenant_file("tamper-test")
        with open(file_path, "r") as f:
            lines = f.readlines()

        # Modify the action in the middle record
        if len(lines) >= 2:
            record = json.loads(lines[1])
            record["action"] = "TAMPERED ACTION"
            lines[1] = json.dumps(record) + "\n"

            with open(file_path, "w") as f:
                f.writelines(lines)

            # Verify after tampering - should fail
            is_valid, error = await audit_chain.verify_chain("tamper-test")
            assert not is_valid
            assert error is not None


# =============================================================================
# Grounding Tests
# =============================================================================


class TestGroundingEnforcement:
    """Test grounding enforcement."""

    def test_well_grounded_response_allowed(self):
        """Test that well-grounded responses pass."""
        from packages.core.grounding import (
            enforce_grounding,
            GroundingEnforcementConfig,
        )

        grounding = {
            "grounding_score": 0.85,
            "verified_sources": 2,
            "sources_used": 3,
        }

        response, blocked, warning = enforce_grounding(
            "Based on HR Policy 4.2, you receive 20 days PTO.",
            grounding,
        )

        assert not blocked
        assert "HR Policy" in response

    def test_ungrounded_response_blocked(self):
        """Test that ungrounded responses are blocked."""
        from packages.core.grounding import (
            enforce_grounding,
            GroundingEnforcementConfig,
        )

        config = GroundingEnforcementConfig(
            enabled=True,
            min_grounding_score=0.5,
        )

        grounding = {
            "grounding_score": 0.2,
            "verified_sources": 0,
            "sources_used": 1,
        }

        response, blocked, warning = enforce_grounding(
            "I think you probably get some PTO.",
            grounding,
            config,
        )

        assert blocked
        assert "sufficient verified information" in response

    def test_enforcement_disabled(self):
        """Test that enforcement can be disabled."""
        from packages.core.grounding import (
            enforce_grounding,
            GroundingEnforcementConfig,
        )

        config = GroundingEnforcementConfig(enabled=False)

        grounding = {
            "grounding_score": 0.1,  # Very low
            "verified_sources": 0,
            "sources_used": 0,
        }

        response, blocked, _ = enforce_grounding(
            "Unverified response",
            grounding,
            config,
        )

        assert not blocked
        assert response == "Unverified response"

    def test_warning_for_borderline_score(self):
        """Test warning for borderline grounding scores."""
        from packages.core.grounding import (
            enforce_grounding,
            GroundingEnforcementConfig,
        )

        config = GroundingEnforcementConfig(
            enabled=True,
            min_grounding_score=0.5,
            warn_threshold=0.7,
        )

        grounding = {
            "grounding_score": 0.55,  # Above min but below warn
            "verified_sources": 1,
            "sources_used": 2,
        }

        response, blocked, warning = enforce_grounding(
            "Partially grounded response.",
            grounding,
            config,
        )

        assert not blocked
        assert warning is not None
        assert "Low grounding score" in warning


# =============================================================================
# Integration Tests
# =============================================================================


class TestSecurityIntegration:
    """Test security components working together."""

    def test_full_auth_flow(self):
        """Test authentication to authorization flow."""
        from packages.auth.models import TokenClaims, AuthenticatedUser
        from packages.authz.engine import AuthzEngine
        from packages.authz.models import Permission
        from datetime import datetime, timedelta

        # Simulate token validation -> user creation -> permission check

        # 1. Token claims (would come from JWT validation)
        claims = TokenClaims(
            sub="jane.doe",
            iss="https://corp.example.com",
            aud="aios",
            exp=int((datetime.utcnow() + timedelta(hours=8)).timestamp()),
            iat=int(datetime.utcnow().timestamp()),
            tenant_id="acme-corp",
            roles=["manager"],
            department="Engineering",
            email="jane.doe@acme.com",
        )

        # 2. Create authenticated user
        user = AuthenticatedUser.from_claims(claims, "oidc")

        # 3. Check permissions
        engine = AuthzEngine()

        # Manager can query agents
        assert engine.check(user, Permission.AGENT_QUERY).allowed

        # Manager can review approvals
        assert engine.check(user, Permission.APPROVAL_REVIEW).allowed

        # Manager cannot do system admin
        assert not engine.check(user, Permission.SYSTEM_ADMIN).allowed
