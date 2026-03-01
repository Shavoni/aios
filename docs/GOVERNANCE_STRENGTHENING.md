# Strengthening Governance for Cross-Agent Consistency

**Date:** January 28, 2026  
**Question:** "Doesn't my governance layer govern across the agents to give guardrails so different agents aren't saying something different? Do I need to strengthen that functionality?"

---

## TL;DR Answer

**Current State:** Governance controls **workflow and risk**, but NOT **content consistency**.

**Short Answer:** Yes, you need to strengthen governance to include cross-agent consistency guardrails.

**What Governance DOES Do:**
- ✅ Escalates sensitive topics (PII, legal, financial)
- ✅ Requires approval for high-impact actions
- ✅ Applies uniformly across all agents
- ✅ Prevents unauthorized operations

**What Governance DOES NOT Do:**
- ❌ Ensure agents use the same knowledge sources
- ❌ Prevent contradictory factual answers
- ❌ Enforce source citation
- ❌ Detect when agents give different answers

---

## Current Governance Scope

### What Governance Currently Governs

The governance system in AIOS controls **process and risk**, not **content**:

```python
# From packages/core/schemas/models.py
class GovernanceDecision(BaseModel):
    """Result of governance policy evaluation."""
    
    hitl_mode: HITLMode              # ← Controls WHEN human review needed
    tools_allowed: bool              # ← Controls WHAT actions allowed
    approval_required: bool          # ← Controls IF approval needed
    escalation_reason: str | None    # ← Explains WHY escalated
    policy_trigger_ids: list[str]    # ← Tracks WHICH policies triggered
    provider_constraints: ProviderConstraints  # ← Controls WHICH LLM
```

**These fields control:**

1. **Workflow Control (HITL Mode):**
   - `INFORM` = Agent responds directly
   - `DRAFT` = Response needs review
   - `ESCALATE` = Route to human

2. **Risk Mitigation:**
   - Detects PII, legal, financial signals
   - Escalates based on risk level
   - Restricts sensitive operations

3. **Approval Gates:**
   - Requires human approval for high-impact
   - Blocks unauthorized actions
   - Enforces review for public communications

**Example Governance Rules:**

```json
{
  "constitutional_rules": [
    {
      "id": "const-001",
      "name": "PII Protection",
      "conditions": [
        {"field": "risk.contains", "value": "PII"}
      ],
      "action": {
        "hitl_mode": "ESCALATE",
        "escalation_reason": "PII detected"
      }
    },
    {
      "id": "const-002",
      "name": "Legal Matters",
      "conditions": [
        {"field": "risk.contains", "value": "LEGAL"}
      ],
      "action": {
        "hitl_mode": "DRAFT"
      }
    }
  ]
}
```

**These rules govern:**
- **When** to escalate
- **What** requires review
- **Who** must approve

**These rules DO NOT govern:**
- **Which sources** to cite
- **What facts** to state
- **Whether answers** are consistent

---

## What Governance Does NOT Govern

### Gap 1: Shared Knowledge Requirements

**Problem:** Governance doesn't require agents to use shared canonical sources.

```python
# Current: Each agent queries its own isolated knowledge
knowledge_manager.query(agent_id, query)  # No shared canon enforced

# HR Agent can have: "Budget: $2M"
# Mayor Agent can have: "Budget: $2.5M"
# Both pass governance checks! ✅ (But are contradictory ❌)
```

**Impact:**
- HR agent says budget is $2M
- Mayor agent says budget is $2.5M
- Both responses pass governance validation
- Users get contradictory information

**Missing Governance Rule:**
```json
{
  "id": "org-shared-canon",
  "name": "Require Shared Canon for Organizational Facts",
  "conditions": [
    {"field": "intent.domain", "operator": "contains", "value": "budget"},
    {"field": "intent.domain", "operator": "contains", "value": "policy"}
  ],
  "action": {
    "require_shared_canon": true,
    "escalation_reason": "Must use shared organizational knowledge"
  }
}
```

### Gap 2: Source Citation Requirements

**Problem:** Governance doesn't enforce citation of sources.

```python
# Current governance decision:
GovernanceDecision(
    hitl_mode="INFORM",     # ← Allowed to respond
    tools_allowed=True,     # ← Allowed to use tools
    approval_required=False # ← No approval needed
)

# But no check for:
# - Did agent cite sources?
# - Are facts grounded in documents?
# - Is this hallucination?
```

**Impact:**
- Agent can make up facts
- Agent can ignore provided sources
- No validation of factual accuracy
- Hallucinations pass governance checks

**Missing Governance Rule:**
```json
{
  "id": "org-citation-required",
  "name": "Require Source Citations",
  "conditions": [
    {"field": "intent.task", "operator": "eq", "value": "inquiry"}
  ],
  "action": {
    "require_citations": true,
    "grounded_only": true,
    "escalation_reason": "Response must cite authoritative sources"
  }
}
```

### Gap 3: Cross-Agent Consistency

**Problem:** Governance doesn't check if different agents would give contradictory answers.

```python
# Current: Each agent evaluated independently
def evaluate_governance(intent, risk, ctx, policy_set):
    # Evaluates THIS agent's request
    # No comparison with other agents
    # No check for contradictions
    pass

# Missing:
def evaluate_cross_agent_consistency(query, agent_id, answer):
    # Check if other agents have answered similar questions
    # Compare this answer with previous answers
    # Flag if contradictory
    pass
```

**Impact:**
- No detection of contradictions
- No alerts when agents diverge
- Silent inconsistency across departments

**Missing Governance Rule:**
```json
{
  "id": "const-consistency-check",
  "name": "Cross-Agent Consistency Required",
  "conditions": [
    {"field": "intent.impact", "operator": "eq", "value": "high"}
  ],
  "action": {
    "require_consistency_check": true,
    "escalation_reason": "Answer must be consistent with other agents"
  }
}
```

### Gap 4: Knowledge Source Validation

**Problem:** Governance doesn't validate which knowledge sources are used.

```python
# Current: Agent can use ANY document in its collection
sources = knowledge_manager.query(agent_id, query)
# No check: Are these approved sources?
# No check: Are these current/outdated?
# No check: Are these shared across agents?

# Missing validation:
# - Is this an approved source?
# - Is this the canonical version?
# - Should all agents use this source?
```

**Impact:**
- Agents use inconsistent sources
- Outdated documents not flagged
- Non-canonical sources allowed

---

## Architecture Gap: Governance vs. Content

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Query Processing                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Receive Query                                            │
│     ↓                                                         │
│  2. Governance Evaluation ✅                                 │
│     - Check risk signals (PII, LEGAL, etc.)                  │
│     - Determine HITL mode                                    │
│     - Check if approval required                             │
│     ↓                                                         │
│  3. Knowledge Retrieval (NO GOVERNANCE) ❌                   │
│     - Query agent-specific collection                        │
│     - No shared canon requirement                            │
│     - No source validation                                   │
│     ↓                                                         │
│  4. LLM Response Generation (NO GOVERNANCE) ❌               │
│     - LLM can ignore sources                                 │
│     - No citation enforcement                                │
│     - No consistency check                                   │
│     ↓                                                         │
│  5. Return Response                                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Problem:** Governance only controls step 2, not steps 3-4 where content consistency matters.

### Needed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Query Processing                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Receive Query                                            │
│     ↓                                                         │
│  2. Governance Evaluation ✅                                 │
│     - Check risk signals                                     │
│     - Determine HITL mode                                    │
│     - CHECK: Shared canon required? (NEW)                    │
│     - CHECK: Citation required? (NEW)                        │
│     ↓                                                         │
│  3. Knowledge Retrieval (GOVERNED) ✅                        │
│     - Query shared canon (if required)                       │
│     - Query agent-specific collection                        │
│     - VALIDATE: Approved sources only                        │
│     - LOG: Sources used for audit                            │
│     ↓                                                         │
│  4. LLM Response Generation (GOVERNED) ✅                    │
│     - VALIDATE: Citations present                            │
│     - VALIDATE: Grounded in sources                          │
│     - CHECK: Consistent with other agents (NEW)              │
│     - BLOCK: Unsourced answers (if required)                 │
│     ↓                                                         │
│  5. Return Response (with governance metadata)               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Strengthening Governance: Proposed Extensions

### Extension 1: Shared Canon Requirement

**New Governance Action Field:**

```python
class RuleAction(BaseModel):
    # Existing fields
    hitl_mode: HITLMode | None
    tools_allowed: bool
    approval_required: bool
    escalation_reason: str | None
    
    # NEW: Content consistency fields
    require_shared_canon: bool = Field(
        default=False,
        description="Require querying shared organizational knowledge"
    )
    canon_priority: int = Field(
        default=0,
        description="How many shared canon results to prioritize"
    )
```

**Usage:**

```json
{
  "id": "org-001",
  "name": "Organizational Facts Require Shared Canon",
  "conditions": [
    {"field": "intent.domain", "operator": "contains", "value": "organization"}
  ],
  "action": {
    "require_shared_canon": true,
    "canon_priority": 3,
    "escalation_reason": "Must use shared organizational knowledge"
  }
}
```

**Implementation:**

```python
def query_with_governance(agent_id, query, governance_decision):
    """Query knowledge base with governance enforcement."""
    
    if governance_decision.require_shared_canon:
        # Query shared canon first
        canon_results = knowledge_manager.query("city_canon", query, n=3)
        agent_results = knowledge_manager.query(agent_id, query, n=2)
        
        # Merge with canon prioritized
        results = canon_results + agent_results
    else:
        # Standard query
        results = knowledge_manager.query(agent_id, query, n=5)
    
    return results
```

### Extension 2: Citation Enforcement

**New Governance Action Field:**

```python
class RuleAction(BaseModel):
    # ... existing fields ...
    
    # NEW: Citation fields
    require_citations: bool = Field(
        default=False,
        description="Require response to cite sources"
    )
    grounded_only: bool = Field(
        default=False,
        description="Block responses without source grounding"
    )
    min_citations: int = Field(
        default=1,
        description="Minimum number of sources to cite"
    )
```

**Usage:**

```json
{
  "id": "const-003",
  "name": "Factual Queries Must Cite Sources",
  "conditions": [
    {"field": "intent.task", "operator": "eq", "value": "inquiry"}
  ],
  "action": {
    "require_citations": true,
    "grounded_only": true,
    "min_citations": 2
  }
}
```

**Implementation:**

```python
def validate_response_governance(response, sources, governance_decision):
    """Validate response meets governance requirements."""
    
    if governance_decision.require_citations:
        citations = extract_citations(response)
        
        if len(citations) < governance_decision.min_citations:
            return ValidationFailure(
                reason=f"Response must cite at least {governance_decision.min_citations} sources",
                blocked=governance_decision.grounded_only
            )
    
    if governance_decision.grounded_only:
        if not verify_grounding(response, sources):
            return ValidationFailure(
                reason="Response contains unsourced claims",
                blocked=True
            )
    
    return ValidationSuccess()
```

### Extension 3: Consistency Check Requirement

**New Governance Action Field:**

```python
class RuleAction(BaseModel):
    # ... existing fields ...
    
    # NEW: Consistency fields
    require_consistency_check: bool = Field(
        default=False,
        description="Check answer consistency with other agents"
    )
    consistency_threshold: float = Field(
        default=0.8,
        description="Similarity threshold (0-1) for consistency"
    )
```

**Usage:**

```json
{
  "id": "const-004",
  "name": "High-Impact Answers Require Consistency",
  "conditions": [
    {"field": "intent.impact", "operator": "eq", "value": "high"}
  ],
  "action": {
    "require_consistency_check": true,
    "consistency_threshold": 0.9,
    "hitl_mode": "DRAFT"
  }
}
```

**Implementation:**

```python
def check_consistency_governance(query, agent_id, answer, governance_decision):
    """Check answer consistency with other agents per governance."""
    
    if not governance_decision.require_consistency_check:
        return ConsistencyCheckResult(required=False)
    
    # Find similar questions answered by other agents
    similar_answers = find_similar_answers(query, exclude_agent=agent_id)
    
    if not similar_answers:
        return ConsistencyCheckResult(
            required=True,
            passed=True,
            reason="No prior answers to compare"
        )
    
    # Compare this answer with previous answers
    conflicts = []
    for prev in similar_answers:
        similarity = compute_similarity(answer, prev.answer)
        
        if similarity < governance_decision.consistency_threshold:
            conflicts.append(Conflict(
                agent_pair=(agent_id, prev.agent_id),
                similarity=similarity,
                threshold=governance_decision.consistency_threshold
            ))
    
    if conflicts:
        return ConsistencyCheckResult(
            required=True,
            passed=False,
            conflicts=conflicts,
            reason=f"Answer inconsistent with {len(conflicts)} other agents"
        )
    
    return ConsistencyCheckResult(required=True, passed=True)
```

---

## Implementation Plan

### Phase 1: Extend Governance Model (Week 1)

**Changes:**

1. **Update `RuleAction` model:**
   ```python
   # In packages/core/governance/__init__.py
   class RuleAction(BaseModel):
       # Existing fields
       hitl_mode: HITLMode | None = None
       local_only: bool = False
       tools_allowed: bool = True
       approval_required: bool = False
       escalation_reason: str | None = None
       
       # NEW: Content consistency fields
       require_shared_canon: bool = False
       canon_priority: int = 0
       require_citations: bool = False
       grounded_only: bool = False
       min_citations: int = 1
       require_consistency_check: bool = False
       consistency_threshold: float = 0.8
   ```

2. **Update `GovernanceDecision` model:**
   ```python
   # In packages/core/schemas/models.py
   class GovernanceDecision(BaseModel):
       # Existing fields
       hitl_mode: HITLMode
       tools_allowed: bool
       approval_required: bool
       escalation_reason: str | None
       policy_trigger_ids: list[str]
       provider_constraints: ProviderConstraints
       
       # NEW: Content governance fields
       require_shared_canon: bool = False
       canon_priority: int = 0
       require_citations: bool = False
       grounded_only: bool = False
       min_citations: int = 1
       require_consistency_check: bool = False
       consistency_threshold: float = 0.8
   ```

3. **Update merge logic:**
   ```python
   # In packages/core/governance/__init__.py:_merge_action
   def _merge_action(decision: GovernanceDecision, action: RuleAction, rule_id: str):
       # Existing merges...
       
       # NEW: Merge content governance
       if action.require_shared_canon:
           decision.require_shared_canon = True
           decision.canon_priority = max(decision.canon_priority, action.canon_priority)
       
       if action.require_citations:
           decision.require_citations = True
           decision.min_citations = max(decision.min_citations, action.min_citations)
       
       if action.grounded_only:
           decision.grounded_only = True
       
       if action.require_consistency_check:
           decision.require_consistency_check = True
           decision.consistency_threshold = max(
               decision.consistency_threshold,
               action.consistency_threshold
           )
   ```

### Phase 2: Add Default Consistency Rules (Week 1)

**Add to `data/governance_policies.json`:**

```json
{
  "constitutional_rules": [
    {
      "id": "const-shared-canon",
      "name": "Organizational Facts Require Shared Canon",
      "description": "Queries about organizational information must use shared canon",
      "conditions": [
        {"field": "intent.audience", "operator": "eq", "value": "external"}
      ],
      "action": {
        "require_shared_canon": true,
        "canon_priority": 3
      },
      "priority": 95
    },
    {
      "id": "const-citation-required",
      "name": "Factual Claims Must Cite Sources",
      "description": "Responses with factual claims must cite knowledge base sources",
      "conditions": [
        {"field": "intent.task", "operator": "eq", "value": "inquiry"}
      ],
      "action": {
        "require_citations": true,
        "grounded_only": true,
        "min_citations": 1
      },
      "priority": 90
    },
    {
      "id": "const-consistency-high-impact",
      "name": "High-Impact Answers Require Consistency",
      "description": "High-impact answers checked for consistency with other agents",
      "conditions": [
        {"field": "intent.impact", "operator": "eq", "value": "high"}
      ],
      "action": {
        "require_consistency_check": true,
        "consistency_threshold": 0.85,
        "hitl_mode": "DRAFT"
      },
      "priority": 85
    }
  ]
}
```

### Phase 3: Implement Enforcement (Weeks 2-3)

**Update agent query endpoint:**

```python
# In packages/api/agents.py:query_agent

# After governance evaluation
governance_decision = governance_mgr.evaluate_for_agent(...)

# NEW: Apply content governance to knowledge retrieval
if governance_decision.require_shared_canon:
    # Query shared canon + agent-specific
    canon_results = knowledge_manager.query("city_canon", query, n=governance_decision.canon_priority)
    agent_results = knowledge_manager.query(agent_id, query, n=5-governance_decision.canon_priority)
    sources = canon_results + agent_results
else:
    # Standard query
    sources = knowledge_manager.query(agent_id, query, n=5)

# Generate response
response = await llm.generate(...)

# NEW: Validate response against governance
if governance_decision.require_citations:
    validation = validate_citations(response, sources, governance_decision)
    if not validation.passed and governance_decision.grounded_only:
        return AgentQueryResponse(
            response="I cannot provide an answer without citing authoritative sources.",
            governance_triggered=True,
            validation_failure=validation
        )

# NEW: Check consistency if required
if governance_decision.require_consistency_check:
    consistency = check_consistency(query, agent_id, response, governance_decision)
    if not consistency.passed:
        # Log conflict for review
        log_consistency_conflict(consistency)
        
        # If DRAFT mode, require human review
        if governance_decision.hitl_mode == HITLMode.DRAFT:
            return AgentQueryResponse(
                response=response,
                hitl_mode="DRAFT",
                governance_triggered=True,
                consistency_warning=consistency
            )
```

---

## Summary

### Question: Does governance govern across agents?

**Answer:**

**Partially:**
- ✅ Governance policies apply uniformly to all agents
- ✅ Risk signals (PII, legal, etc.) trigger consistently
- ✅ HITL modes work the same for all agents

**But NOT for content consistency:**
- ❌ Agents can use different knowledge sources
- ❌ Agents can give contradictory factual answers
- ❌ No enforcement of source citation
- ❌ No detection of cross-agent contradictions

### Do you need to strengthen it?

**YES.** To ensure cross-agent consistency, governance needs:

1. **Shared Canon Requirement** - Force agents to query shared organizational knowledge
2. **Citation Enforcement** - Require agents to cite sources, block unsourced claims
3. **Consistency Checks** - Compare answers across agents, flag contradictions

### Current vs. Strengthened

| Aspect | Current | Strengthened |
|--------|---------|--------------|
| **Workflow** | ✅ Governed | ✅ Governed |
| **Risk Signals** | ✅ Governed | ✅ Governed |
| **Knowledge Sources** | ❌ Not Governed | ✅ **Governed** |
| **Citation** | ❌ Not Governed | ✅ **Governed** |
| **Consistency** | ❌ Not Governed | ✅ **Governed** |

**Bottom Line:** Your governance needs extension from "workflow governance" to "content governance" to ensure agents don't contradict each other.

---

**Next Steps:**
1. Review proposed extensions
2. Implement Phase 1 (governance model updates)
3. Add default consistency rules
4. Implement enforcement in query pipeline
5. Test with multi-agent scenarios

**Document Version:** 1.0  
**Author:** Governance Strengthening Analysis  
**Date:** January 28, 2026
