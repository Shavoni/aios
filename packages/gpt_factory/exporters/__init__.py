"""
Export Adapters

Transform AIOS-native agent blueprints for different target platforms.
Each exporter handles platform-specific constraints and formats.
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from abc import ABC, abstractmethod

from ..models import (
    AgentBlueprint,
    ExportTarget,
    ExportResult,
    KnowledgeSource,
)
from ..templates import TemplateEngine


class Exporter(ABC):
    """Base class for platform-specific exporters."""

    target: ExportTarget

    @abstractmethod
    def export(
        self,
        blueprint: AgentBlueprint,
        output_dir: Optional[Path] = None,
    ) -> ExportResult:
        """Export the blueprint to the target platform format."""
        pass


class AIOSExporter(Exporter):
    """
    Export to AIOS native format.

    Full fidelity - no constraints applied.
    """

    target = ExportTarget.AIOS_NATIVE

    def export(
        self,
        blueprint: AgentBlueprint,
        output_dir: Optional[Path] = None,
    ) -> ExportResult:
        """Export blueprint as AIOS-native JSON."""
        # AIOS native format is just the blueprint as-is
        output_data = blueprint.model_dump(mode="json")

        # Write to file if output_dir provided
        output_path = None
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{blueprint.id}.agent.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, default=str)

        return ExportResult(
            agent_id=blueprint.id,
            target=self.target,
            success=True,
            output_path=str(output_path) if output_path else None,
            output_data=output_data,
            transformations=["none - full fidelity"],
            warnings=[],
            exported_at=datetime.utcnow(),
        )


class OpenAIGPTExporter(Exporter):
    """
    Export to OpenAI Custom GPT format.

    Applies platform constraints:
    - Description: 300 characters max
    - Instructions: 8,000 characters max
    - Conversation starters: 4 max
    - Knowledge: 20 files, 512MB total
    """

    target = ExportTarget.OPENAI_GPT

    # Platform limits
    DESCRIPTION_LIMIT = 300
    INSTRUCTIONS_LIMIT = 8000
    STARTERS_LIMIT = 4
    KNOWLEDGE_FILES_LIMIT = 20
    KNOWLEDGE_SIZE_LIMIT = 512 * 1024 * 1024  # 512MB

    def __init__(self):
        self.template_engine = TemplateEngine()

    def export(
        self,
        blueprint: AgentBlueprint,
        output_dir: Optional[Path] = None,
    ) -> ExportResult:
        """Export blueprint in OpenAI Custom GPT format."""
        warnings = []
        transformations = []

        # Transform description
        description = blueprint.description_short
        if len(description) > self.DESCRIPTION_LIMIT:
            description = description[:self.DESCRIPTION_LIMIT - 3] + "..."
            transformations.append(f"description truncated to {self.DESCRIPTION_LIMIT} chars")
            warnings.append(f"Description truncated from {len(blueprint.description_short)} chars")

        # Transform instructions
        instructions = blueprint.instructions
        if len(instructions) > self.INSTRUCTIONS_LIMIT:
            instructions = self.template_engine.generate_instructions_summary(
                blueprint,
                max_length=self.INSTRUCTIONS_LIMIT
            )
            transformations.append(f"instructions summarized to {self.INSTRUCTIONS_LIMIT} chars")
            warnings.append(f"Instructions condensed from {len(blueprint.instructions)} chars")

        # Transform conversation starters
        starters = blueprint.conversation_starters[:self.STARTERS_LIMIT]
        if len(blueprint.conversation_starters) > self.STARTERS_LIMIT:
            transformations.append(f"conversation starters limited to {self.STARTERS_LIMIT}")
            warnings.append(f"Reduced conversation starters from {len(blueprint.conversation_starters)}")

        # Build output structure
        output_data = {
            "name": blueprint.name,
            "description": description,
            "instructions": instructions,
            "conversation_starters": starters,
            "capabilities": {
                "web_browsing": False,
                "code_interpreter": False,
                "dalle": False,
            },
            "knowledge_files": self._prepare_knowledge_files(blueprint, warnings, transformations),
            # Metadata for reference
            "_metadata": {
                "source": "HAAIS GPT Factory",
                "aios_agent_id": blueprint.id,
                "exported_at": datetime.utcnow().isoformat(),
                "full_instructions_available": len(blueprint.instructions) > self.INSTRUCTIONS_LIMIT,
            }
        }

        # Write to file if output_dir provided
        output_path = None
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{blueprint.id}.openai-gpt.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, default=str)

            # Also write a deployment guide
            guide_path = output_dir / f"{blueprint.id}.deployment-guide.md"
            self._write_deployment_guide(blueprint, output_data, guide_path)
            transformations.append("deployment guide generated")

        return ExportResult(
            agent_id=blueprint.id,
            target=self.target,
            success=True,
            output_path=str(output_path) if output_path else None,
            output_data=output_data,
            transformations=transformations,
            warnings=warnings,
            exported_at=datetime.utcnow(),
        )

    def _prepare_knowledge_files(
        self,
        blueprint: AgentBlueprint,
        warnings: list[str],
        transformations: list[str],
    ) -> list[dict[str, Any]]:
        """Prepare knowledge files for OpenAI GPT format."""
        knowledge_files = []
        total_size = 0
        file_count = 0

        for source in blueprint.knowledge_sources:
            if file_count >= self.KNOWLEDGE_FILES_LIMIT:
                warnings.append(f"Knowledge files limited to {self.KNOWLEDGE_FILES_LIMIT} (had more)")
                transformations.append(f"knowledge files capped at {self.KNOWLEDGE_FILES_LIMIT}")
                break

            # Estimate size (actual would need file system access)
            estimated_size = len(source.content or "") if source.content else 0

            if total_size + estimated_size > self.KNOWLEDGE_SIZE_LIMIT:
                warnings.append("Total knowledge size exceeds 512MB limit")
                break

            knowledge_files.append({
                "name": source.name,
                "source_type": source.source_type.value,
                "file_path": source.file_path,
                "url": source.url,
            })

            total_size += estimated_size
            file_count += 1

        return knowledge_files

    def _write_deployment_guide(
        self,
        blueprint: AgentBlueprint,
        export_data: dict[str, Any],
        guide_path: Path,
    ) -> None:
        """Write a deployment guide for manual GPT creation."""
        guide = f"""# OpenAI Custom GPT Deployment Guide

## Agent: {blueprint.name}

This guide helps you deploy the **{blueprint.name}** agent as an OpenAI Custom GPT.

---

## Step 1: Create New GPT

1. Go to [ChatGPT](https://chat.openai.com)
2. Click your profile → "My GPTs" → "Create a GPT"
3. Select "Configure" tab

---

## Step 2: Configure Basic Info

**Name:**
```
{blueprint.name}
```

**Description:** (copy exactly - {len(export_data['description'])} chars)
```
{export_data['description']}
```

---

## Step 3: Instructions

Copy the following into the "Instructions" field:

```
{export_data['instructions'][:2000]}...

[Full instructions in the exported JSON file]
```

---

## Step 4: Conversation Starters

Add these conversation starters:

{chr(10).join(f'- {s}' for s in export_data['conversation_starters'])}

---

## Step 5: Knowledge Files

Upload the following knowledge files:

{chr(10).join(f"- {k['name']}" for k in export_data['knowledge_files']) if export_data['knowledge_files'] else '(No knowledge files)'}

---

## Step 6: Capabilities

Configure capabilities:
- Web Browsing: Off
- Code Interpreter: Off
- DALL-E: Off

---

## Step 7: Save and Test

1. Click "Save" → Choose visibility (Private/Link/Public)
2. Test with conversation starters
3. Verify guardrails are respected

---

## Notes

- Full AIOS deployment provides richer functionality (unlimited instructions, full knowledge base, governance)
- This export is a simplified version for ChatGPT platform
- For enterprise deployment, use AIOS native format

---

*Generated by HAAIS GPT Factory*
*Agent ID: {blueprint.id}*
*Exported: {datetime.utcnow().isoformat()}*
"""
        with open(guide_path, "w", encoding="utf-8") as f:
            f.write(guide)


class ExportManager:
    """
    Manages exports to multiple platforms.

    Provides a unified interface for exporting agent blueprints.
    """

    def __init__(self):
        self.exporters: dict[ExportTarget, Exporter] = {
            ExportTarget.AIOS_NATIVE: AIOSExporter(),
            ExportTarget.OPENAI_GPT: OpenAIGPTExporter(),
        }

    def export(
        self,
        blueprint: AgentBlueprint,
        target: ExportTarget,
        output_dir: Optional[Path] = None,
    ) -> ExportResult:
        """Export a blueprint to the specified target platform."""
        exporter = self.exporters.get(target)
        if not exporter:
            return ExportResult(
                agent_id=blueprint.id,
                target=target,
                success=False,
                warnings=[f"No exporter available for target: {target}"],
                exported_at=datetime.utcnow(),
            )

        return exporter.export(blueprint, output_dir)

    def export_all(
        self,
        blueprint: AgentBlueprint,
        output_dir: Path,
    ) -> dict[ExportTarget, ExportResult]:
        """Export a blueprint to all available platforms."""
        results = {}
        for target, exporter in self.exporters.items():
            target_dir = output_dir / target.value
            results[target] = exporter.export(blueprint, target_dir)
        return results

    def register_exporter(self, exporter: Exporter) -> None:
        """Register a custom exporter."""
        self.exporters[exporter.target] = exporter
