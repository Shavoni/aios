# Does Governance Prevent Agents from Contradicting Each Other?

**Your Question:** "Doesn't my governance layer govern across the agents in a sense give it guardrails so the different agents aren't saying something different? Do I need to strengthen that functionality?"

---

## Short Answer

**Partially, but YES you need to strengthen it.**

Your governance layer ensures:
- ✅ All agents follow same **workflow** rules (when to escalate, when to require approval)
- ✅ All agents detect same **risk signals** (PII, legal, financial)
- ✅ All agents respect same **policy restrictions**

But governance does NOT ensure:
- ❌ Agents use the same **knowledge sources**
- ❌ Agents give the same **factual answers**
- ❌ Agents **cite their sources**
- ❌ System detects when agents **contradict each other**

---

## What Your Governance Currently Does

### Example: PII Protection Rule

```json
{
  "id": "const-001",
  "name": "PII Protection",
  "conditions": [{"field": "risk.contains", "value": "PII"}],
  "action": {"hitl_mode": "ESCALATE"}
}
```

**This governs WORKFLOW:**
- HR Agent asking about SSN → Escalates ✅
- Mayor Agent asking about SSN → Escalates ✅
- Port Agent asking about SSN → Escalates ✅

**All agents follow the SAME governance rule.** ✅

---

## What Your Governance Does NOT Do

### Example: Budget Question

```
User asks all agents: "What is Cleveland's AI initiative budget?"

HR Agent response:
"The AI initiative budget is $2 million for FY2026."
└─ Sources: HR_Budget_Doc.pdf (uploaded to HR agent only)

Mayor Agent response:
"The AI strategy budget is $2.5 million for FY2026."
└─ Sources: Mayor_Strategic_Plan.pdf (uploaded to Mayor agent only)

Port Authority Agent response:
"I don't have information about the AI budget."
└─ Sources: None (no documents uploaded)
```

**Problem:** Three different answers! But all pass governance ✅

**Why?** Governance checks:
- Risk signals (PII? LEGAL?) → None detected ✅
- HITL mode → INFORM (respond directly) ✅
- Approval required? → No ✅

Governance does NOT check:
- Are agents using the same knowledge? ❌
- Are the answers consistent? ❌
- Did agents cite sources? ❌

---

## The Gap: Workflow vs. Content

```
┌─────────────────────────────────────────────────┐
│         Current Governance Scope                │
├─────────────────────────────────────────────────┤
│                                                  │
│  ✅ WHEN to escalate                            │
│  ✅ WHAT actions are allowed                    │
│  ✅ WHO must approve                            │
│  ✅ WHICH LLM provider to use                   │
│                                                  │
│  ❌ WHICH knowledge sources to use              │
│  ❌ WHETHER facts are consistent                │
│  ❌ IF sources are cited                        │
│  ❌ WHEN answers contradict                     │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Current governance = "Process governance"**  
**Needed = "Process governance" + "Content governance"**

---

## How to Strengthen Governance

### Add 3 New Governance Capabilities

#### 1. Require Shared Canon

**New Governance Rule:**
```json
{
  "id": "org-shared-canon",
  "name": "Require Shared Organizational Knowledge",
  "conditions": [
    {"field": "intent.domain", "value": "organization"}
  ],
  "action": {
    "require_shared_canon": true,
    "canon_priority": 3
  }
}
```

**Effect:** All agents MUST query shared "city_canon" collection first, then their own.

**Result:**
- HR Agent → Queries city_canon + HR collection
- Mayor Agent → Queries city_canon + Mayor collection
- Port Agent → Queries city_canon + Port collection

All agents see the SAME organizational facts! ✅

#### 2. Enforce Citations

**New Governance Rule:**
```json
{
  "id": "const-citations",
  "name": "Factual Claims Must Cite Sources",
  "conditions": [
    {"field": "intent.task", "value": "inquiry"}
  ],
  "action": {
    "require_citations": true,
    "grounded_only": true
  }
}
```

**Effect:** Responses MUST cite knowledge base sources. Block responses without citations.

**Result:**
- Agent must say: "According to [Budget_FY2026.pdf], the budget is $2M"
- Agent cannot say: "The budget is $2M" (no citation → blocked)

#### 3. Check Consistency

**New Governance Rule:**
```json
{
  "id": "const-consistency",
  "name": "High-Impact Answers Must Be Consistent",
  "conditions": [
    {"field": "intent.impact", "value": "high"}
  ],
  "action": {
    "require_consistency_check": true,
    "consistency_threshold": 0.85
  }
}
```

**Effect:** System compares this answer with other agents' previous answers. Flags if different.

**Result:**
- If HR says "$2M" and Mayor says "$2.5M" → Conflict detected
- Alert governance team to resolve contradiction
- Flag for human review

---

## Implementation Plan

### Week 1: Extend Governance Models

**Add to `RuleAction`:**
```python
class RuleAction(BaseModel):
    # Existing
    hitl_mode: HITLMode | None
    approval_required: bool
    
    # NEW: Content governance
    require_shared_canon: bool = False
    require_citations: bool = False
    require_consistency_check: bool = False
```

### Week 1: Add Default Rules

**Add to `data/governance_policies.json`:**
- Shared canon rule (for organizational facts)
- Citation rule (for factual claims)
- Consistency rule (for high-impact answers)

### Weeks 2-3: Implement Enforcement

**Update agent query pipeline:**
```python
# 1. Evaluate governance (existing)
decision = governance.evaluate(query, agent_id)

# 2. NEW: Apply content governance
if decision.require_shared_canon:
    sources = query_with_canon(agent_id, query)

# 3. Generate response
response = llm.generate(query, sources)

# 4. NEW: Validate response
if decision.require_citations:
    if not has_citations(response):
        return "Cannot answer without citing sources"

# 5. NEW: Check consistency
if decision.require_consistency_check:
    if conflicts_detected(query, response, agent_id):
        log_conflict_for_review()
```

---

## Summary

### Your Question: Does governance prevent contradictions?

**Answer:** Not currently, but it can with extensions.

**Current State:**
- Governance ensures agents follow same **workflow rules** ✅
- But agents can give **contradictory facts** ❌

**Why?**
- Each agent has **isolated knowledge** (no shared canon)
- No requirement to **cite sources**
- No detection of **cross-agent contradictions**

**Solution:**
Strengthen governance to include:
1. **Shared canon requirement** - Force common knowledge
2. **Citation enforcement** - Require sourcing facts
3. **Consistency checks** - Detect contradictions

**Timeline:** 3 weeks to implement

**Next Step:** Review [GOVERNANCE_STRENGTHENING.md](./GOVERNANCE_STRENGTHENING.md) for detailed plan

---

**Bottom Line:** Your governance controls "when" and "how" agents respond, but not "what" they say. Extending governance to cover content consistency will ensure agents don't contradict each other.
