# Two-Tier Governance Implementation Plan

**Date:** January 28, 2026  
**Purpose:** Implement shared knowledge governance from onboarding while keeping policy governance intact

---

## Problem Statement

User needs:
1. **Governance from Cleveland government website** (discovered during onboarding) should be shared across all agents
2. **Primary governance** (human-written policies in `governance_policies.json`) stays intact
3. This ensures:
   - ✅ All agents use the same knowledge sources
   - ✅ All agents give the same factual answers
   - ✅ All agents cite their sources

---

## Understanding the Two-Tier System

### Tier 1: Policy Governance (Current - Stays Intact)

**What it is:**
- Human-written rules in `data/governance_policies.json`
- Controls workflow, risk, and approval processes
- Examples: "Escalate PII queries", "Draft mode for legal matters"

**What it governs:**
- WHEN to escalate (HITL modes)
- WHAT actions require approval
- WHO can perform operations
- WHICH LLM providers to use

**This stays completely unchanged.** ✅

### Tier 2: Knowledge Governance (NEW - To Implement)

**What it is:**
- Content extracted from Cleveland government website during onboarding
- Shared canonical knowledge base ("city_canon")
- Contains organizational facts, policies, procedures from official sources

**What it governs:**
- WHICH facts are authoritative
- WHAT sources to cite
- WHETHER answers are consistent

**This is what we're adding.** 🎯

---

## Current Architecture vs. Needed

### Current: Isolated Knowledge Per Agent

```
Onboarding discovers Cleveland website
         ↓
    Creates agents
         ↓
Each agent gets own knowledge collection:
├─ HR Agent → agent_hr (isolated)
├─ Mayor Agent → agent_mayor (isolated)
└─ Port Agent → agent_port (isolated)

Problem: No shared knowledge = contradictory answers
```

### Needed: Shared City Canon + Agent-Specific

```
Onboarding discovers Cleveland website
         ↓
    Extracts canonical content
         ↓
    Creates "city_canon" collection ← NEW!
         ↓
    Creates agents
         ↓
All agents query BOTH collections:
├─ HR Agent → city_canon (shared) + agent_hr (specific)
├─ Mayor Agent → city_canon (shared) + agent_mayor (specific)
└─ Port Agent → city_canon (shared) + agent_port (specific)

Solution: Shared knowledge = consistent answers
```

---

## Implementation Design

### Component 1: City Canon Collection

**Purpose:** Shared knowledge base for organizational facts

**Implementation:**

```python
# In packages/core/knowledge/__init__.py

CITY_CANON_AGENT_ID = "city_canon"

class KnowledgeManager:
    
    def add_to_city_canon(
        self,
        filename: str,
        content: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeDocument:
        """Add document to shared city canon.
        
        City canon is queryable by all agents and contains
        organizational facts, policies, and procedures.
        """
        if metadata is None:
            metadata = {}
        
        metadata.update({
            "shared": True,
            "canonical": True,
            "scope": "organization"
        })
        
        return self.add_document(
            agent_id=CITY_CANON_AGENT_ID,
            filename=filename,
            content=content,
            metadata=metadata,
        )
    
    def add_url_to_city_canon(
        self,
        url: str,
        name: str | None = None,
        description: str = "",
    ) -> WebSource:
        """Add web source to shared city canon."""
        return self.add_web_source(
            agent_id=CITY_CANON_AGENT_ID,
            url=url,
            name=name,
            description=description,
        )
    
    def query_with_canon(
        self,
        agent_id: str,
        query_text: str,
        n_results: int = 5,
        canon_priority: int = 2,
    ) -> list[dict[str, Any]]:
        """Query both city canon and agent-specific knowledge.
        
        Args:
            agent_id: The specific agent
            query_text: Query string
            n_results: Total results to return
            canon_priority: Number of canon results to prioritize
        
        Returns:
            Merged results with canon prioritized
        """
        # Query city canon first
        canon_results = self.query(
            CITY_CANON_AGENT_ID,
            query_text,
            n_results=canon_priority
        )
        
        # Query agent-specific knowledge
        agent_results = self.query(
            agent_id,
            query_text,
            n_results=n_results - canon_priority
        )
        
        # Merge with canon first (higher priority)
        merged = canon_results + agent_results
        
        # Deduplicate by text similarity
        deduplicated = self._deduplicate_results(merged)
        
        return deduplicated[:n_results]
    
    def _deduplicate_results(
        self,
        results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Remove duplicate results based on text similarity."""
        if not results:
            return []
        
        unique = [results[0]]
        
        for result in results[1:]:
            # Check if this result is too similar to any existing
            is_duplicate = False
            for existing in unique:
                # Simple similarity check (could be improved)
                if self._text_similarity(
                    result['text'],
                    existing['text']
                ) > 0.9:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(result)
        
        return unique
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (0-1)."""
        # Simple character overlap similarity
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
```

### Component 2: Onboarding Integration

**Purpose:** Populate city canon during onboarding

**Implementation:**

```python
# In packages/onboarding/manifest.py or new file

class OnboardingKnowledgeExtractor:
    """Extract and store canonical knowledge during onboarding."""
    
    def __init__(self, knowledge_manager: KnowledgeManager):
        self.km = knowledge_manager
    
    def process_discovery_results(
        self,
        discovery_result: DiscoveryResult,
        config: OnboardingConfig
    ) -> dict[str, Any]:
        """Process discovered content and populate city canon.
        
        Args:
            discovery_result: Results from website discovery
            config: Onboarding configuration
        
        Returns:
            Summary of what was added to city canon
        """
        summary = {
            "documents_added": 0,
            "urls_added": 0,
            "categories": []
        }
        
        # Extract canonical content categories
        canonical_content = self._identify_canonical_content(discovery_result)
        
        for category, items in canonical_content.items():
            summary["categories"].append(category)
            
            for item in items:
                if item["type"] == "url":
                    # Add web source to city canon
                    self.km.add_url_to_city_canon(
                        url=item["url"],
                        name=item["name"],
                        description=f"Canonical {category} from {config.municipality}"
                    )
                    summary["urls_added"] += 1
                
                elif item["type"] == "document":
                    # Add document to city canon
                    self.km.add_to_city_canon(
                        filename=item["filename"],
                        content=item["content"],
                        metadata={
                            "category": category,
                            "source": item["source"],
                            "municipality": config.municipality
                        }
                    )
                    summary["documents_added"] += 1
        
        return summary
    
    def _identify_canonical_content(
        self,
        discovery_result: DiscoveryResult
    ) -> dict[str, list[dict]]:
        """Identify which discovered content should be canonical.
        
        Returns categorized canonical content:
        - organizational_structure: Org chart, departments, contacts
        - policies_procedures: City policies, ordinances, procedures
        - services_programs: City services, programs, resources
        - budget_finance: Budget documents, financial reports
        - strategic_plans: Strategic plans, initiatives
        """
        canonical = {
            "organizational_structure": [],
            "policies_procedures": [],
            "services_programs": [],
            "budget_finance": [],
            "strategic_plans": []
        }
        
        # Categorize discovered pages
        for page in discovery_result.pages:
            url_lower = page.url.lower()
            title_lower = page.title.lower()
            
            # Organizational structure
            if any(kw in url_lower or kw in title_lower for kw in [
                "about", "organization", "departments", "directory", "leadership"
            ]):
                canonical["organizational_structure"].append({
                    "type": "url",
                    "url": page.url,
                    "name": page.title,
                    "source": "website_discovery"
                })
            
            # Policies and procedures
            if any(kw in url_lower or kw in title_lower for kw in [
                "policy", "policies", "ordinance", "code", "regulation", "procedure"
            ]):
                canonical["policies_procedures"].append({
                    "type": "url",
                    "url": page.url,
                    "name": page.title,
                    "source": "website_discovery"
                })
            
            # Services and programs
            if any(kw in url_lower or kw in title_lower for kw in [
                "service", "program", "resource", "assistance", "help"
            ]):
                canonical["services_programs"].append({
                    "type": "url",
                    "url": page.url,
                    "name": page.title,
                    "source": "website_discovery"
                })
            
            # Budget and finance
            if any(kw in url_lower or kw in title_lower for kw in [
                "budget", "finance", "financial", "fiscal", "spending"
            ]):
                canonical["budget_finance"].append({
                    "type": "url",
                    "url": page.url,
                    "name": page.title,
                    "source": "website_discovery"
                })
            
            # Strategic plans
            if any(kw in url_lower or kw in title_lower for kw in [
                "strategic", "plan", "vision", "initiative", "priority"
            ]):
                canonical["strategic_plans"].append({
                    "type": "url",
                    "url": page.url,
                    "name": page.title,
                    "source": "website_discovery"
                })
        
        return canonical
```

### Component 3: Agent Query Integration

**Purpose:** Make agents use city canon automatically

**Implementation:**

```python
# In packages/api/agents.py, update query_agent function

@router.post("/{agent_id}/query", response_model=AgentQueryResponse)
async def query_agent(agent_id: str, request: AgentQueryRequest) -> AgentQueryResponse:
    """Query an agent with automatic city canon integration."""
    
    # ... existing governance evaluation ...
    
    # Get relevant context from knowledge base
    sources: list[dict[str, Any]] = []
    context = ""
    
    if request.use_knowledge_base:
        knowledge_manager = get_knowledge_manager()
        
        # NEW: Query with city canon (shared knowledge)
        results = knowledge_manager.query_with_canon(
            agent_id=agent_id,
            query_text=request.query,
            n_results=5,
            canon_priority=2  # 2 from canon, 3 from agent-specific
        )
        sources = results
        
        if results:
            context_parts = []
            for r in results:
                # Mark if from city canon
                source_type = "City Canon" if r['metadata'].get('shared') else "Department"
                context_parts.append(
                    f"[{source_type} Source: {r['metadata'].get('filename', 'unknown')}]\n{r['text']}"
                )
            context = "\n\n---\n\n".join(context_parts)
    
    # ... rest of existing code ...
```

### Component 4: API Endpoints

**Purpose:** Allow manual management of city canon

**Implementation:**

```python
# In packages/api/agents.py or new governance.py

@router.post("/city-canon/documents", response_model=KnowledgeDocument)
async def upload_city_canon_document(
    file: UploadFile = File(...),
    category: str = Query(..., description="Category: organizational_structure, policies_procedures, etc."),
) -> KnowledgeDocument:
    """Upload a document to shared city canon.
    
    This makes the document available to all agents.
    """
    content = await file.read()
    
    knowledge_manager = get_knowledge_manager()
    return knowledge_manager.add_to_city_canon(
        filename=file.filename or "unknown.txt",
        content=content,
        metadata={"category": category}
    )


@router.post("/city-canon/urls", response_model=WebSource)
async def add_city_canon_url(
    url: str = Body(...),
    name: str = Body(None),
    description: str = Body(""),
) -> WebSource:
    """Add a web source to shared city canon.
    
    Content from this URL will be scraped and available to all agents.
    """
    knowledge_manager = get_knowledge_manager()
    return knowledge_manager.add_url_to_city_canon(
        url=url,
        name=name,
        description=description,
    )


@router.get("/city-canon/documents", response_model=list[KnowledgeDocument])
async def list_city_canon_documents() -> list[KnowledgeDocument]:
    """List all documents in city canon."""
    knowledge_manager = get_knowledge_manager()
    return knowledge_manager.list_documents(CITY_CANON_AGENT_ID)


@router.delete("/city-canon/documents/{document_id}", status_code=204)
async def delete_city_canon_document(document_id: str) -> None:
    """Delete a document from city canon."""
    knowledge_manager = get_knowledge_manager()
    doc = knowledge_manager.get_document(document_id)
    
    if not doc or doc.agent_id != CITY_CANON_AGENT_ID:
        raise HTTPException(404, "Document not found in city canon")
    
    knowledge_manager.delete_document(document_id)
```

---

## How This Solves the Requirements

### Requirement 1: Shared Knowledge Sources

**Before:**
```
HR Agent: Queries only agent_hr collection
Mayor Agent: Queries only agent_mayor collection
→ Can have different sources, contradictory info
```

**After:**
```
HR Agent: Queries city_canon + agent_hr
Mayor Agent: Queries city_canon + agent_mayor
→ Both see same canonical sources from Cleveland website
```

### Requirement 2: Same Factual Answers

**Before:**
```
User: "What is Cleveland's AI budget?"
HR Agent: "Not sure" (no docs in agent_hr)
Mayor Agent: "$2.5M" (from doc in agent_mayor)
→ Inconsistent answers
```

**After:**
```
User: "What is Cleveland's AI budget?"
Both query city_canon first:
HR Agent: "$2.5M per Strategic Plan" (from city_canon)
Mayor Agent: "$2.5M per Strategic Plan" (from city_canon)
→ Consistent answers from shared source
```

### Requirement 3: Cite Sources

**Before:**
```
Response: "The budget is $2.5M"
→ No indication where this came from
```

**After:**
```
Response: "According to [City Canon Source: Strategic_Plan_2026.pdf], 
the AI initiative budget is $2.5M"
→ Clear citation showing canonical source
```

### Requirement 4: Keep Policy Governance Intact

**Policy governance (governance_policies.json) is completely unchanged:**
- Still controls HITL modes
- Still detects risk signals
- Still requires approvals
- Still restricts tools

**Knowledge governance (city_canon) is additive:**
- Adds shared knowledge layer
- Doesn't modify policy rules
- Works alongside existing governance

---

## Implementation Steps

### Phase 1: Core Infrastructure (Week 1)

1. **Add city canon methods to KnowledgeManager:**
   - ✅ `add_to_city_canon()`
   - ✅ `add_url_to_city_canon()`
   - ✅ `query_with_canon()`
   - ✅ `_deduplicate_results()`

2. **Add constant:**
   - ✅ `CITY_CANON_AGENT_ID = "city_canon"`

3. **Test city canon:**
   - Upload test document
   - Query from multiple "agents"
   - Verify sharing works

### Phase 2: Onboarding Integration (Week 1)

1. **Create OnboardingKnowledgeExtractor:**
   - ✅ `process_discovery_results()`
   - ✅ `_identify_canonical_content()`

2. **Integrate with onboarding flow:**
   - After discovery completes
   - Extract canonical content
   - Populate city_canon
   - Log what was added

3. **Test with Cleveland website:**
   - Run discovery
   - Verify canonical content extracted
   - Check city_canon populated

### Phase 3: Agent Integration (Week 2)

1. **Update agent query endpoint:**
   - Replace `query()` with `query_with_canon()`
   - Update context formatting
   - Add canon source indicators

2. **Test agent queries:**
   - Query same question from different agents
   - Verify both see canon content
   - Check citation format

### Phase 4: API Endpoints (Week 2)

1. **Add city canon management endpoints:**
   - ✅ POST /city-canon/documents
   - ✅ POST /city-canon/urls
   - ✅ GET /city-canon/documents
   - ✅ DELETE /city-canon/documents/{id}

2. **Test API:**
   - Upload document via API
   - Query via agent
   - Verify shared visibility

### Phase 5: UI Integration (Week 3)

1. **Add city canon section to dashboard:**
   - View canonical documents
   - Upload new canonical docs
   - Remove outdated docs

2. **Add indicators in responses:**
   - Show when answer uses canon
   - Display canon source name
   - Link to source document

---

## Configuration

### Environment Variables

```bash
# Optional: Configure canon priority
CITY_CANON_PRIORITY=2  # Number of canon results (default: 2)
CITY_CANON_ENABLED=true  # Enable/disable canon (default: true)
```

### Agent Config

```python
# Optional: Per-agent canon override
class AgentConfig(BaseModel):
    # ... existing fields ...
    
    use_city_canon: bool = True  # Default: use canon
    canon_priority: int = 2  # Override global priority
```

---

## Testing Strategy

### Unit Tests

```python
def test_city_canon_add_document():
    """Test adding document to city canon."""
    km = KnowledgeManager()
    doc = km.add_to_city_canon(
        filename="test.txt",
        content=b"Test content",
    )
    assert doc.agent_id == CITY_CANON_AGENT_ID
    assert doc.metadata.get("shared") == True

def test_query_with_canon():
    """Test querying with canon."""
    km = KnowledgeManager()
    
    # Add to canon
    km.add_to_city_canon("canon.txt", b"Canon content")
    
    # Add to agent
    km.add_document("agent1", "agent.txt", b"Agent content")
    
    # Query should return both
    results = km.query_with_canon("agent1", "content", n_results=5)
    assert len(results) >= 1  # At least canon result
```

### Integration Tests

```python
def test_onboarding_populates_canon():
    """Test that onboarding populates city canon."""
    # Run onboarding
    result = onboard_municipality("Cleveland", "https://clevelandohio.gov")
    
    # Check canon populated
    km = get_knowledge_manager()
    docs = km.list_documents(CITY_CANON_AGENT_ID)
    assert len(docs) > 0

def test_agents_see_same_canon():
    """Test that different agents see same canon."""
    km = get_knowledge_manager()
    
    # Add to canon
    km.add_to_city_canon("shared.txt", b"Shared content")
    
    # Query from different agents
    results1 = km.query_with_canon("agent1", "shared", n_results=5)
    results2 = km.query_with_canon("agent2", "shared", n_results=5)
    
    # Both should see the canonical document
    assert any("shared" in r["metadata"].get("filename", "") for r in results1)
    assert any("shared" in r["metadata"].get("filename", "") for r in results2)
```

---

## Migration Plan

### For Existing Deployments

1. **No breaking changes:**
   - Existing agents work as before
   - City canon is optional
   - Gradual migration possible

2. **Migration steps:**
   ```bash
   # 1. Deploy code update
   git pull
   pip install -r requirements.txt
   
   # 2. Create city canon collection
   # (happens automatically on first use)
   
   # 3. Populate canon (choose one):
   
   # Option A: Re-run onboarding
   python -m packages.onboarding discover --url https://clevelandohio.gov
   
   # Option B: Upload key documents via API
   curl -X POST /city-canon/documents -F file=@strategic_plan.pdf
   
   # Option C: Add key URLs
   curl -X POST /city-canon/urls -d url=https://clevelandohio.gov/budget
   
   # 4. Restart API
   systemctl restart aios-api
   ```

3. **Verify:**
   - Query different agents
   - Check for canonical sources
   - Monitor consistency

---

## Benefits Summary

| Benefit | Before | After |
|---------|--------|-------|
| **Shared Knowledge** | Each agent isolated | All agents share city_canon |
| **Answer Consistency** | Can contradict | Same facts from canon |
| **Source Citation** | Optional, inconsistent | Clear canon vs. dept sources |
| **Maintenance** | Update each agent separately | Update canon once |
| **Onboarding** | Manual doc upload | Automatic canon population |
| **Governance** | Policy-only | Policy + Knowledge |

---

## Summary

This design creates a **two-tier governance system**:

**Tier 1: Policy Governance** (unchanged)
- Controls workflow, risk, approvals
- Lives in `governance_policies.json`
- Evaluated by `GovernanceManager`

**Tier 2: Knowledge Governance** (new)
- Controls factual content
- Lives in `city_canon` knowledge collection
- Shared across all agents
- Populated from Cleveland website during onboarding

**Together they ensure:**
- ✅ Agents use same knowledge sources (city_canon)
- ✅ Agents give same factual answers (shared canon)
- ✅ Agents cite their sources (canon vs. dept)
- ✅ Policy governance stays intact (no changes)

**Implementation:** 3 weeks, no breaking changes, gradual migration possible.

---

**Next Steps:**
1. Review this design
2. Approve for implementation
3. Start Phase 1 (core infrastructure)
4. Test with Cleveland deployment

**Document Version:** 1.0  
**Author:** Two-Tier Governance Design  
**Date:** January 28, 2026
