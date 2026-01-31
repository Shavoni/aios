"""
Tests for GPT Factory

Tests the agent generation pipeline including:
- Archetype loading and matching
- Template-based blueprint generation
- Validation rules
- Export adapters
"""

import pytest
from pathlib import Path

from packages.gpt_factory import (
    GPTFactory,
    ArchetypeRegistry,
    TemplateEngine,
    AgentValidator,
    ExportManager,
    Organization,
    OrganizationType,
    AgentCandidate,
    CandidateType,
    AgentBlueprint,
    ExportTarget,
)
from packages.gpt_factory.models import (
    GovernanceConfig,
    HITLMode,
    ValidationStatus,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def archetype_registry():
    """Create and load archetype registry."""
    registry = ArchetypeRegistry()
    registry.load_archetypes()
    return registry


@pytest.fixture
def template_engine(archetype_registry):
    """Create template engine with registry."""
    return TemplateEngine(archetype_registry)


@pytest.fixture
def validator():
    """Create agent validator."""
    return AgentValidator()


@pytest.fixture
def export_manager():
    """Create export manager."""
    return ExportManager()


@pytest.fixture
def sample_organization():
    """Create a sample organization."""
    return Organization(
        id="test-org",
        name="City of Test",
        type=OrganizationType.MUNICIPAL,
        url="https://www.testcity.gov",
        description="A test municipal organization",
    )


@pytest.fixture
def sample_candidate(sample_organization):
    """Create a sample candidate."""
    return AgentCandidate(
        id="test-public-health",
        organization_id=sample_organization.id,
        name="Department of Public Health",
        suggested_agent_name="Dr. Jane Smith",
        type=CandidateType.PUBLIC_HEALTH,
        confidence=0.9,
        source_urls=["https://www.testcity.gov/health"],
    )


# =============================================================================
# ARCHETYPE TESTS
# =============================================================================

class TestArchetypeRegistry:
    """Tests for archetype registry."""

    def test_load_archetypes(self, archetype_registry):
        """Test archetypes are loaded correctly."""
        archetypes = archetype_registry.list_all()
        assert len(archetypes) > 0

    def test_get_archetype_by_id(self, archetype_registry):
        """Test getting archetype by ID."""
        archetype = archetype_registry.get("municipal-public-health")
        assert archetype is not None
        assert archetype.domain == "PublicHealth"

    def test_find_matching_archetypes(self, archetype_registry):
        """Test finding matching archetypes."""
        matches = archetype_registry.find_matching(
            OrganizationType.MUNICIPAL,
            CandidateType.PUBLIC_HEALTH,
        )
        assert len(matches) > 0
        assert any(a.id == "municipal-public-health" for a in matches)

    def test_best_match(self, archetype_registry):
        """Test getting best matching archetype."""
        best = archetype_registry.best_match(
            OrganizationType.MUNICIPAL,
            CandidateType.HUMAN_RESOURCES,
        )
        assert best is not None
        assert "hr" in best.id.lower() or "human" in best.id.lower()

    def test_for_organization_type(self, archetype_registry):
        """Test getting archetypes for org type."""
        municipal_archetypes = archetype_registry.for_organization_type(
            OrganizationType.MUNICIPAL
        )
        assert len(municipal_archetypes) > 0


# =============================================================================
# TEMPLATE ENGINE TESTS
# =============================================================================

class TestTemplateEngine:
    """Tests for template engine."""

    def test_generate_blueprint(
        self,
        template_engine,
        sample_candidate,
        sample_organization,
    ):
        """Test blueprint generation."""
        blueprint = template_engine.generate_blueprint(
            candidate=sample_candidate,
            organization=sample_organization,
        )

        assert blueprint is not None
        assert blueprint.name == "Dr. Jane Smith"
        assert blueprint.domain == "PublicHealth"
        assert len(blueprint.instructions) > 0
        assert len(blueprint.capabilities) > 0
        assert len(blueprint.guardrails) > 0

    def test_generate_with_overrides(
        self,
        template_engine,
        sample_candidate,
        sample_organization,
    ):
        """Test blueprint generation with overrides."""
        blueprint = template_engine.generate_blueprint(
            candidate=sample_candidate,
            organization=sample_organization,
            overrides={"name": "Custom Name", "domain": "CustomDomain"},
        )

        assert blueprint.name == "Custom Name"
        assert blueprint.domain == "CustomDomain"

    def test_short_description_within_limit(
        self,
        template_engine,
        sample_candidate,
        sample_organization,
    ):
        """Test short description stays within 300 char limit."""
        blueprint = template_engine.generate_blueprint(
            candidate=sample_candidate,
            organization=sample_organization,
        )

        assert len(blueprint.description_short) <= 300

    def test_instructions_include_governance(
        self,
        template_engine,
        sample_candidate,
        sample_organization,
    ):
        """Test instructions include HAAIS governance framework."""
        blueprint = template_engine.generate_blueprint(
            candidate=sample_candidate,
            organization=sample_organization,
        )

        assert "HAAIS Governance Framework" in blueprint.instructions


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestAgentValidator:
    """Tests for agent validation."""

    def test_validate_good_blueprint(
        self,
        validator,
        template_engine,
        sample_candidate,
        sample_organization,
    ):
        """Test validation of well-formed blueprint."""
        blueprint = template_engine.generate_blueprint(
            candidate=sample_candidate,
            organization=sample_organization,
        )

        report = validator.validate(blueprint)

        assert report is not None
        assert report.status != ValidationStatus.FAILED
        assert report.overall_score > 0.5

    def test_validate_missing_escalation(self, validator):
        """Test validation catches missing escalation."""
        blueprint = AgentBlueprint(
            id="test",
            organization_id="org",
            name="Test Agent",
            title="Test",
            domain="Test",
            description_short="Test description",
            description_full="Full description",
            instructions="Basic instructions without escalation",
            escalates_to=None,  # Missing escalation
        )

        report = validator.validate(blueprint)

        escalation_issues = [
            i for i in report.issues if i.category == "escalation"
        ]
        assert len(escalation_issues) > 0

    def test_validate_short_description_too_long(self, validator):
        """Test validation catches description over 300 chars."""
        blueprint = AgentBlueprint(
            id="test",
            organization_id="org",
            name="Test Agent",
            title="Test",
            domain="Test",
            description_short="x" * 350,  # Over limit
            description_full="Full description",
            instructions="Instructions",
        )

        report = validator.validate(blueprint)

        description_errors = [
            i for i in report.issues
            if i.category == "description" and i.severity == "error"
        ]
        assert len(description_errors) > 0

    def test_validation_scores(
        self,
        validator,
        template_engine,
        sample_candidate,
        sample_organization,
    ):
        """Test validation produces proper scores."""
        blueprint = template_engine.generate_blueprint(
            candidate=sample_candidate,
            organization=sample_organization,
        )

        report = validator.validate(blueprint)

        assert 0 <= report.overall_score <= 1
        assert 0 <= report.instruction_score <= 1
        assert 0 <= report.knowledge_score <= 1
        assert 0 <= report.governance_score <= 1


# =============================================================================
# EXPORT TESTS
# =============================================================================

class TestExportManager:
    """Tests for export manager."""

    def test_export_aios_native(
        self,
        export_manager,
        template_engine,
        sample_candidate,
        sample_organization,
        tmp_path,
    ):
        """Test AIOS native export."""
        blueprint = template_engine.generate_blueprint(
            candidate=sample_candidate,
            organization=sample_organization,
        )

        result = export_manager.export(
            blueprint,
            ExportTarget.AIOS_NATIVE,
            tmp_path,
        )

        assert result.success
        assert result.output_path is not None
        assert Path(result.output_path).exists()

    def test_export_openai_gpt(
        self,
        export_manager,
        template_engine,
        sample_candidate,
        sample_organization,
        tmp_path,
    ):
        """Test OpenAI GPT export."""
        blueprint = template_engine.generate_blueprint(
            candidate=sample_candidate,
            organization=sample_organization,
        )

        result = export_manager.export(
            blueprint,
            ExportTarget.OPENAI_GPT,
            tmp_path,
        )

        assert result.success
        assert result.output_data is not None
        # Check OpenAI constraints applied
        assert len(result.output_data["description"]) <= 300
        assert len(result.output_data["conversation_starters"]) <= 4

    def test_export_all_targets(
        self,
        export_manager,
        template_engine,
        sample_candidate,
        sample_organization,
        tmp_path,
    ):
        """Test exporting to all targets."""
        blueprint = template_engine.generate_blueprint(
            candidate=sample_candidate,
            organization=sample_organization,
        )

        results = export_manager.export_all(blueprint, tmp_path)

        assert ExportTarget.AIOS_NATIVE in results
        assert ExportTarget.OPENAI_GPT in results
        assert all(r.success for r in results.values())


# =============================================================================
# FACTORY INTEGRATION TESTS
# =============================================================================

class TestGPTFactory:
    """Integration tests for GPT Factory."""

    @pytest.mark.asyncio
    async def test_factory_discover(self, archetype_registry):
        """Test factory discovery creates job with candidates."""
        factory = GPTFactory(archetype_registry=archetype_registry)

        job = await factory.discover(
            url="https://www.testcity.gov",
            organization_type=OrganizationType.MUNICIPAL,
        )

        assert job is not None
        assert job.job_id is not None
        assert len(job.candidates) > 0
        assert job.organization.name == "Testcity"

    @pytest.mark.asyncio
    async def test_factory_select_candidates(self, archetype_registry):
        """Test selecting candidates moves job to research stage."""
        factory = GPTFactory(archetype_registry=archetype_registry)

        job = await factory.discover(
            url="https://www.testcity.gov",
            organization_type=OrganizationType.MUNICIPAL,
        )

        # Select first two candidates
        selected_ids = [c.id for c in job.candidates[:2]]
        job = factory.select_candidates(job.job_id, selected_ids)

        assert len(job.selected_candidates) == 2
        assert job.current_stage.value == "research"

    @pytest.mark.asyncio
    async def test_factory_full_pipeline(self, archetype_registry, tmp_path):
        """Test full factory pipeline."""
        factory = GPTFactory(archetype_registry=archetype_registry)

        # Stage 1: Discover
        job = await factory.discover(
            url="https://www.testcity.gov",
            organization_type=OrganizationType.MUNICIPAL,
        )

        # Stage 2: Select candidates
        selected_ids = [job.candidates[0].id]
        job = factory.select_candidates(job.job_id, selected_ids)

        # Stage 3: Research
        job = await factory.research(job.job_id)

        # Stage 4: Generate
        job = factory.generate(job.job_id)
        assert len(job.blueprints) == 1

        # Stage 5: Approve blueprints
        job = factory.approve_blueprints(job.job_id)

        # Stage 6: Validate
        job = factory.validate(job.job_id)
        assert len(job.validation_reports) == 1

        # Stage 7: Package
        job = factory.package(
            job.job_id,
            targets=[ExportTarget.AIOS_NATIVE],
            output_dir=tmp_path,
        )
        assert len(job.export_results) == 1

        # Stage 8: Finalize
        job = factory.finalize(job.job_id)
        assert job.get_pending_checkpoint() is None


# =============================================================================
# MODEL TESTS
# =============================================================================

class TestModels:
    """Tests for data models."""

    def test_governance_config_defaults(self):
        """Test governance config has sensible defaults."""
        config = GovernanceConfig()

        assert config.default_hitl_mode == HITLMode.INFORM
        assert config.require_grounding is True
        assert config.min_grounding_score == 0.5
        assert "PII" in config.risk_escalations

    def test_agent_blueprint_serialization(
        self,
        template_engine,
        sample_candidate,
        sample_organization,
    ):
        """Test blueprint serializes to JSON correctly."""
        blueprint = template_engine.generate_blueprint(
            candidate=sample_candidate,
            organization=sample_organization,
        )

        # Should not raise
        json_data = blueprint.model_dump(mode="json")

        assert "id" in json_data
        assert "instructions" in json_data
        assert "governance" in json_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
