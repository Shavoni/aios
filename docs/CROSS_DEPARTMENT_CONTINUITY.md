# Cross-Department Continuity Analysis

**Date:** January 28, 2026  
**Purpose:** Analyze how AIOS ensures agents don't give contradictory answers across departments

---

## Executive Summary

This document analyzes the AIOS knowledge architecture against requirements for cross-department continuity. It addresses four critical questions:

**Status Overview:**
- ❌ **Shared Canon**: NOT implemented (each agent has isolated knowledge)
- ❌ **Knowledge Injection**: NOT implemented (no shared knowledge pack)
- ❌ **Conflict Detection**: NOT implemented (no logging/flagging of divergent answers)
- ❌ **Source Citation**: PARTIAL (sources available but not enforced)

**Critical Finding:** AIOS currently uses an **agent-isolated knowledge model** with **NO shared knowledge layer**. This creates a high risk of contradictory answers across departments for shared topics.

---

## Question 1: Shared Canonical Definitions

### ❌ Status: **NOT IMPLEMENTED**

**Current Reality:**

AIOS does **NOT** ensure different agents use the same canonical definitions. Each agent has a **completely isolated** knowledge base:

```python
# From packages/core/knowledge/__init__.py:127-133

def _get_collection(self, agent_id: str) -> chromadb.Collection:
    """Get or create a Chroma collection for an agent."""
    collection_name = f"agent_{agent_id.replace('-', '_')}"
    return self._client.get_or_create_collection(
        name=collection_name,
        metadata={"agent_id": agent_id},
    )
```

**What This Means:**

1. **HR agent** has collection `agent_hr_assistant`
2. **Mayor agent** has collection `agent_mayors_command_center`
3. **Port Authority agent** has collection `agent_port_authority`

These collections are **completely separate**:
- They can contain different documents
- They can have contradictory information
- They have no awareness of each other
- No synchronization mechanism exists

**Example Scenario (Actual Risk):**

```
Topic: "Cleveland's AI Strategy Budget"

HR Agent Knowledge Base:
- Document uploaded: "AI Budget FY2026 - $2M allocated"

Mayor Agent Knowledge Base:
- Document uploaded: "AI Strategy Budget - $2.5M approved"

Port Authority Agent:
- No documents about AI budget (will hallucinate or refuse)

Result: Three agents give three different answers to the same question!
```

**Architecture Diagram (Current State):**

```
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Manager                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Collection:  │  │ Collection:  │  │ Collection:  │      │
│  │  agent_hr    │  │agent_mayor   │  │ agent_port   │      │
│  │              │  │              │  │              │      │
│  │ Docs: 15     │  │ Docs: 23     │  │ Docs: 8      │      │
│  │ Chunks: 150  │  │ Chunks: 230  │  │ Chunks: 80   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│        ↑                ↑                  ↑                 │
│        │                │                  │                 │
│   NO SHARING      NO SHARING         NO SHARING             │
│   NO SYNC         NO SYNC            NO SYNC                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Impact:**

- **High Risk:** Different departments give contradictory answers
- **Compliance Issue:** No single source of truth for policies
- **User Confusion:** Employees get different answers based on which agent they ask
- **Governance Failure:** Cannot ensure consistent messaging

---

## Question 2: Shared "City Canon / Knowledge Pack"

### ❌ Status: **NOT IMPLEMENTED**

**Current State:**

There is **NO** shared knowledge pack injected into every agent. The knowledge architecture is:

```python
# From packages/api/agents.py:476-494

# Get relevant context from knowledge base
sources: list[dict[str, Any]] = []
context = ""

if request.use_knowledge_base:
    knowledge_manager = get_knowledge_manager()
    # Query ONLY this agent's collection
    results = knowledge_manager.query(agent_id, request.query, n_results=5)
    sources = results
    
    if results:
        context_parts = []
        for r in results:
            context_parts.append(f"[Source: {r['metadata'].get('filename', 'unknown')}]\n{r['text']}")
        context = "\n\n---\n\n".join(context_parts)

# Build system prompt
system_prompt = agent.system_prompt
if context:
    system_prompt += f"\n\n## Relevant Knowledge Base Documents:\n\n{context}"
```

**What's Missing:**

1. **No Shared Collection:**
   - No `agent_city_canon` collection
   - No `agent_shared` collection
   - No organization-wide knowledge base

2. **No Knowledge Profiles:**
   - No concept of "knowledge packs" (e.g., "HR Standard Pack", "City Canon")
   - No ability to assign multiple knowledge sources to an agent
   - No inheritance hierarchy (organization → department → agent)

3. **No Canonical Injection:**
   - Agents only see their own documents
   - No automatic injection of shared knowledge
   - No "always include" document set

**Where Injection SHOULD Happen (But Doesn't):**

```python
# This is what SHOULD exist but doesn't:

def query_with_canon(self, agent_id: str, query_text: str, n_results: int = 5):
    """Query agent knowledge WITH shared city canon."""
    
    # 1. Query agent-specific knowledge
    agent_results = self._query_collection(agent_id, query_text, n_results=3)
    
    # 2. Query shared city canon (DOESN'T EXIST!)
    canon_results = self._query_collection("city_canon", query_text, n_results=2)
    
    # 3. Merge and deduplicate
    all_results = self._merge_results(agent_results, canon_results)
    
    return all_results
```

**Current Implementation:** Query only looks at single collection (line 482 above).

**Impact:**

- **No Baseline Knowledge:** New agents start with zero organizational knowledge
- **Manual Duplication:** Same documents must be uploaded to each agent
- **Drift Risk:** Updates to canonical docs don't propagate
- **Maintenance Nightmare:** Updating a policy requires touching all agents

---

## Question 3: Conflict Detection

### ❌ Status: **NOT IMPLEMENTED**

**Current State:**

There is **NO automatic conflict detection** when two agents answer differently. The system:

1. **Does NOT log answers** in a way that enables comparison
2. **Does NOT flag conflicts** when they occur
3. **Does NOT track answer consistency** across agents
4. **Does NOT have any cross-agent analysis**

**What Exists (Insufficient):**

```python
# From packages/core/audit/__init__.py (audit logging)
# Logs individual queries but doesn't compare across agents

def log_query(agent_id, query, response):
    # Logs to audit trail
    # But NO comparison with other agents
    # NO conflict detection
    pass
```

**What's Missing:**

### Missing Component 1: Answer Storage

```python
# This doesn't exist:
class AgentAnswer(BaseModel):
    """Record of an agent's answer to a question."""
    id: str
    agent_id: str
    query: str
    query_normalized: str  # For matching similar questions
    answer: str
    sources_used: list[str]
    timestamp: datetime
    answer_hash: str  # For detecting changes
```

### Missing Component 2: Conflict Detector

```python
# This doesn't exist:
class ConflictDetector:
    """Detect when agents give contradictory answers."""
    
    def check_for_conflicts(self, query: str) -> list[Conflict]:
        """Check if different agents would answer this question differently.
        
        1. Normalize the query
        2. Query all agents
        3. Compare answers
        4. Flag conflicts
        """
        pass
    
    def find_similar_questions(self, query: str) -> list[AgentAnswer]:
        """Find previous answers to similar questions by all agents."""
        pass
    
    def flag_conflict(self, answers: list[AgentAnswer]) -> Conflict:
        """Create a conflict record when answers diverge."""
        pass
```

### Missing Component 3: Conflict Logging

```python
# This doesn't exist:
class Conflict(BaseModel):
    """A detected conflict between agent answers."""
    id: str
    query: str
    agents_involved: list[str]
    answers: dict[str, str]  # agent_id -> answer
    conflict_type: str  # "factual", "policy", "definition"
    severity: str  # "low", "medium", "high", "critical"
    detected_at: datetime
    resolved: bool = False
    resolution: str | None = None
```

**Where Detection SHOULD Happen:**

1. **Real-time (Query Time):**
   ```python
   # After agent responds, check for conflicts
   async def query_agent_with_conflict_check(agent_id, query):
       answer = await query_agent(agent_id, query)
       
       # Check if other agents have answered similar questions
       conflicts = await detect_conflicts(query, answer, agent_id)
       
       if conflicts:
           # Log conflict
           # Alert governance team
           # Flag in response
           pass
       
       return answer
   ```

2. **Batch (Background):**
   ```python
   # Periodic scan for conflicts
   async def scan_for_conflicts():
       # Get recent answers
       # Group by similar queries
       # Compare answers
       # Flag divergences
       pass
   ```

**Impact:**

- **Silent Failures:** Contradictions go unnoticed until users complain
- **No Metrics:** Cannot measure answer consistency
- **No Alerts:** Governance team not notified of conflicts
- **No Resolution:** No workflow to fix contradictory knowledge

---

## Question 4: Source Citation Enforcement

### ⚠️ Status: **PARTIALLY IMPLEMENTED**

**What EXISTS:**

Sources are tracked and available:

```python
# From packages/api/agents.py:476-489

if request.use_knowledge_base:
    knowledge_manager = get_knowledge_manager()
    results = knowledge_manager.query(agent_id, request.query, n_results=5)
    sources = results  # ← Sources are retrieved
    
    if results:
        context_parts = []
        for r in results:
            # Sources include metadata
            context_parts.append(f"[Source: {r['metadata'].get('filename', 'unknown')}]\n{r['text']}")
        context = "\n\n---\n\n".join(context_parts)
```

Sources are returned in API response:

```python
# From packages/api/agents.py (AgentQueryResponse model)
class AgentQueryResponse(BaseModel):
    response: str
    agent_id: str
    agent_name: str
    sources: list[dict[str, Any]]  # ← Sources included in response
    # ...
```

**What's MISSING:**

### 1. No Citation Enforcement

```python
# Current: LLM can ignore sources
system_prompt = agent.system_prompt
if context:
    system_prompt += f"\n\n## Relevant Knowledge Base Documents:\n\n{context}"

# The LLM is NOT required to cite sources
# The LLM CAN "freestyle" and make up answers
# There's no validation that response uses provided sources
```

**Example of Problem:**

```
Context provided to LLM:
"[Source: HR_Policy_2026.pdf]
Sick leave policy: Employees accrue 1 day per month, max 90 days."

LLM Response:
"You can take unlimited sick days as long as you notify your supervisor."
                                    ↑
                            CONTRADICTION!
                     But no validation catches this
```

### 2. No Unsourced Answer Blocking

```python
# This doesn't exist:
def validate_response_has_citations(response: str, sources: list[dict]) -> bool:
    """Ensure response cites provided sources."""
    # Check if response mentions source filenames
    # Check if facts align with source content
    # Block response if no citations
    pass
```

### 3. No "Grounded-Only" Mode

```python
# This should exist but doesn't:
class AgentConfig(BaseModel):
    # ... existing fields ...
    
    # NEW FIELDS NEEDED:
    require_source_citations: bool = True  # Enforce citations
    allow_unsourced_answers: bool = False  # Block freestyle
    citation_format: str = "inline"  # How to cite
    grounded_only: bool = True  # Only answer if sources exist
```

**Where Blocking SHOULD Happen:**

```python
async def query_agent_with_citation_enforcement(agent_id, query):
    # Get agent config
    agent = get_agent(agent_id)
    
    # Query knowledge base
    sources = knowledge_manager.query(agent_id, query)
    
    # If grounded_only and no sources found
    if agent.grounded_only and not sources:
        return AgentQueryResponse(
            response="I don't have information on that topic in my knowledge base.",
            sources=[],
            refused_reason="no_sources",
        )
    
    # Get LLM response
    response = await llm.generate(query, sources)
    
    # Validate response cites sources
    if agent.require_source_citations:
        if not validate_citations(response, sources):
            return AgentQueryResponse(
                response="I cannot provide an answer without proper source citations.",
                sources=sources,
                refused_reason="citation_validation_failed",
            )
    
    return response
```

**Current vs. Needed:**

| Feature | Current | Needed |
|---------|---------|--------|
| Sources retrieved | ✅ Yes | ✅ Yes |
| Sources passed to LLM | ✅ Yes | ✅ Yes |
| Sources in response | ✅ Yes | ✅ Yes |
| Citation enforcement | ❌ No | ✅ **Required** |
| Unsourced blocking | ❌ No | ✅ **Required** |
| Citation validation | ❌ No | ✅ **Required** |
| Grounded-only mode | ❌ No | ✅ **Required** |

**Impact:**

- **Hallucination Risk:** LLM can make up answers despite having sources
- **No Accountability:** Cannot prove answers came from approved documents
- **Compliance Risk:** Answers not traceable to authoritative sources
- **Quality Issue:** No guarantee of knowledge base usage

---

## Architecture Gaps Summary

### Current Architecture (Isolated)

```
┌─────────────────────────────────────────────────────────────┐
│                         AIOS System                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐            │
│  │ HR Agent │     │Mayor Agent│     │Port Agent│            │
│  │          │     │           │     │          │            │
│  │ KB: 15   │     │ KB: 23    │     │ KB: 8    │            │
│  │ docs     │     │ docs      │     │ docs     │            │
│  └────┬─────┘     └────┬──────┘     └────┬─────┘            │
│       │                │                  │                  │
│       ↓                ↓                  ↓                  │
│  ┌────────┐       ┌─────────┐       ┌────────┐             │
│  │Chroma  │       │Chroma   │       │Chroma  │             │
│  │agent_hr│       │agent_    │       │agent_  │             │
│  │        │       │mayor    │       │port    │             │
│  └────────┘       └─────────┘       └────────┘             │
│                                                               │
│  NO SHARED KNOWLEDGE                                         │
│  NO CONFLICT DETECTION                                       │
│  NO CITATION ENFORCEMENT                                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Needed Architecture (Shared Canon)

```
┌─────────────────────────────────────────────────────────────┐
│                         AIOS System                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐            │
│  │ HR Agent │     │Mayor Agent│     │Port Agent│            │
│  │          │     │           │     │          │            │
│  │Specific: │     │Specific:  │     │Specific: │            │
│  │ 10 docs  │     │ 15 docs   │     │ 5 docs   │            │
│  └────┬─────┘     └────┬──────┘     └────┬─────┘            │
│       │                │                  │                  │
│       ├────────────────┼──────────────────┤                  │
│       │                │                  │                  │
│       ↓                ↓                  ↓                  │
│  ┌────────────────────────────────────────────┐             │
│  │         SHARED CITY CANON (NEW!)           │             │
│  │  ┌──────────────────────────────────────┐  │             │
│  │  │ - City Policies (25 docs)            │  │             │
│  │  │ - HR Standards (10 docs)             │  │             │
│  │  │ - Budget Info (5 docs)               │  │             │
│  │  │ - Department Contacts (1 doc)        │  │             │
│  │  │ - Cleveland Facts (3 docs)           │  │             │
│  │  └──────────────────────────────────────┘  │             │
│  │         Chroma: agent_city_canon           │             │
│  └────────────────────────────────────────────┘             │
│       │                │                  │                  │
│       ↓                ↓                  ↓                  │
│  ┌────────┐       ┌─────────┐       ┌────────┐             │
│  │Agent   │       │Agent    │       │Agent   │             │
│  │Specific│       │Specific │       │Specific│             │
│  └────────┘       └─────────┘       └────────┘             │
│                                                               │
│  ┌──────────────────────────────────────────┐               │
│  │   Conflict Detection Service (NEW!)      │               │
│  │   - Monitors all answers                 │               │
│  │   - Compares across agents               │               │
│  │   - Flags contradictions                 │               │
│  └──────────────────────────────────────────┘               │
│                                                               │
│  ┌──────────────────────────────────────────┐               │
│  │   Citation Enforcement (NEW!)            │               │
│  │   - Validates responses cite sources     │               │
│  │   - Blocks unsourced answers             │               │
│  │   - Enforces grounded-only mode          │               │
│  └──────────────────────────────────────────┘               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Recommendations

### Priority 1: Implement Shared City Canon (CRITICAL)

**Timeline:** Week 1-2

**Changes Needed:**

1. **Create Shared Collection:**
   ```python
   # In KnowledgeManager
   CITY_CANON_COLLECTION = "agent_city_canon"
   
   def add_to_city_canon(self, filename: str, content: bytes):
       """Add document to shared city canon."""
       # Use special agent_id for canon
       return self.add_document(
           agent_id="city_canon",
           filename=filename,
           content=content,
           metadata={"shared": True, "canonical": True}
       )
   ```

2. **Modify Query to Include Canon:**
   ```python
   def query_with_canon(
       self,
       agent_id: str,
       query_text: str,
       n_results: int = 5,
   ) -> list[dict[str, Any]]:
       """Query both agent-specific and shared canon."""
       
       # Get agent-specific results (3)
       agent_results = self.query(agent_id, query_text, n_results=3)
       
       # Get city canon results (2)
       canon_results = self.query("city_canon", query_text, n_results=2)
       
       # Merge, prioritizing canon for conflicts
       all_results = self._merge_and_deduplicate(
           canon_results,  # Canon first (higher priority)
           agent_results,
       )
       
       return all_results[:n_results]
   ```

3. **Update Agent Query Endpoint:**
   ```python
   # In packages/api/agents.py:481
   # Change from:
   results = knowledge_manager.query(agent_id, request.query, n_results=5)
   
   # To:
   results = knowledge_manager.query_with_canon(agent_id, request.query, n_results=5)
   ```

### Priority 2: Implement Conflict Detection (HIGH)

**Timeline:** Week 3-4

**Components to Build:**

1. **Answer Storage:**
   ```python
   # New table/collection
   class AgentAnswerLog:
       def log_answer(self, agent_id, query, answer, sources):
           """Store agent answer for future comparison."""
           pass
       
       def find_similar_answers(self, query) -> list[StoredAnswer]:
           """Find previous answers to similar questions."""
           pass
   ```

2. **Conflict Detector:**
   ```python
   class ConflictDetector:
       def check_for_conflicts(
           self,
           query: str,
           agent_id: str,
           answer: str,
       ) -> list[Conflict]:
           """Check if this answer conflicts with other agents."""
           
           # Find similar questions answered by other agents
           similar = self.answer_log.find_similar_answers(query)
           
           # Compare this answer with previous answers
           conflicts = []
           for prev in similar:
               if prev.agent_id != agent_id:
                   if self._answers_conflict(answer, prev.answer):
                       conflicts.append(Conflict(
                           query=query,
                           agents=[agent_id, prev.agent_id],
                           answers={
                               agent_id: answer,
                               prev.agent_id: prev.answer,
                           },
                       ))
           
           return conflicts
   ```

3. **Alert System:**
   ```python
   def alert_on_conflict(conflict: Conflict):
       """Alert governance team of detected conflict."""
       # Log to database
       # Send email/slack notification
       # Create HITL review item
       pass
   ```

### Priority 3: Enforce Source Citations (HIGH)

**Timeline:** Week 4-5

**Implementation:**

1. **Add Agent Config:**
   ```python
   class AgentConfig(BaseModel):
       # ... existing fields ...
       require_citations: bool = True
       allow_unsourced: bool = False
       grounded_only: bool = True
   ```

2. **Add Citation Validator:**
   ```python
   class CitationValidator:
       def validate_response(
           self,
           response: str,
           sources: list[dict],
       ) -> ValidationResult:
           """Validate that response properly cites sources."""
           
           # Check 1: Does response mention source documents?
           cited_sources = self._extract_citations(response)
           
           # Check 2: Are facts grounded in provided sources?
           grounded = self._verify_grounding(response, sources)
           
           # Check 3: Any hallucinations detected?
           hallucinations = self._detect_hallucinations(response, sources)
           
           return ValidationResult(
               valid=len(cited_sources) > 0 and grounded and not hallucinations,
               cited_sources=cited_sources,
               grounded=grounded,
               hallucinations=hallucinations,
           )
   ```

3. **Update Agent Query:**
   ```python
   async def query_agent(agent_id, request):
       # ... existing code ...
       
       # After LLM generates response
       if agent.require_citations:
           validator = CitationValidator()
           validation = validator.validate_response(response, sources)
           
           if not validation.valid:
               # Block unsourced response
               return AgentQueryResponse(
                   response="I cannot provide an answer without proper citations.",
                   refused=True,
                   validation_failure=validation,
               )
       
       return AgentQueryResponse(response=response, sources=sources)
   ```

### Priority 4: Knowledge Profiles (MEDIUM)

**Timeline:** Week 6-7

**Concept:**

Instead of a single "city canon", allow multiple knowledge profiles:

```python
class KnowledgeProfile(BaseModel):
    """A set of knowledge that can be assigned to agents."""
    id: str
    name: str
    description: str
    document_ids: list[str]
    priority: int  # Higher priority = used first in conflicts

# Examples:
PROFILES = {
    "city_canon": KnowledgeProfile(
        id="city_canon",
        name="Cleveland City Canon",
        description="Official city-wide policies and facts",
        document_ids=["doc1", "doc2", ...],
        priority=100,
    ),
    "hr_standard": KnowledgeProfile(
        id="hr_standard",
        name="HR Standard Operating Procedures",
        description="HR policies applicable to all departments",
        document_ids=["hr1", "hr2", ...],
        priority=90,
    ),
}

# Agents can have multiple profiles:
class AgentConfig(BaseModel):
    # ... existing ...
    knowledge_profiles: list[str] = ["city_canon"]  # IDs of profiles
```

---

## Implementation Phases

### Phase 1: Shared Canon (Weeks 1-2)
- [x] Design shared collection architecture
- [ ] Implement `add_to_city_canon()` method
- [ ] Implement `query_with_canon()` method
- [ ] Update agent query endpoint
- [ ] Add API endpoints for canon management
- [ ] Create admin UI for uploading canon docs
- [ ] Test with sample canonical documents

### Phase 2: Conflict Detection (Weeks 3-4)
- [ ] Design answer storage schema
- [ ] Implement answer logging
- [ ] Build conflict detection algorithm
- [ ] Create conflict dashboard
- [ ] Add alert system
- [ ] Test with historical data

### Phase 3: Citation Enforcement (Weeks 4-5)
- [ ] Add citation config to agents
- [ ] Implement citation validator
- [ ] Add validation to query flow
- [ ] Create "grounded-only" mode
- [ ] Test with various queries
- [ ] Document best practices

### Phase 4: Knowledge Profiles (Weeks 6-7)
- [ ] Design profile system
- [ ] Implement profile management
- [ ] Update query logic
- [ ] Create profile assignment UI
- [ ] Migrate existing knowledge
- [ ] Test profile inheritance

---

## Metrics to Track

Once implemented, track:

1. **Canon Usage:**
   - % of queries that retrieve canon documents
   - Canon hit rate per agent
   - Most-used canon documents

2. **Conflict Detection:**
   - Number of conflicts detected per day
   - Conflicts by agent pair
   - Average time to resolve conflicts
   - Conflict severity distribution

3. **Citation Quality:**
   - % of responses with citations
   - Citation validation success rate
   - Sources cited per response
   - Unsourced block rate

4. **Answer Consistency:**
   - Cross-agent answer similarity for same questions
   - Contradiction rate
   - Knowledge drift over time

---

## Conclusion

AIOS currently has **NO mechanisms** to ensure cross-department continuity:

- ❌ No shared canon
- ❌ No conflict detection
- ❌ No citation enforcement

This creates **high risk** of:
- Contradictory answers across departments
- User confusion
- Compliance failures
- Knowledge drift

**Recommendation:** Implement Phases 1-3 (shared canon, conflict detection, citation enforcement) before production deployment for any multi-department organization.

---

**Document Version:** 1.0  
**Author:** Cross-Department Continuity Analysis  
**Next Review:** After implementing recommendations
