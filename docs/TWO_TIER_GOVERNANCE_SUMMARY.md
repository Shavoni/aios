# Two-Tier Governance: Executive Summary

**Your Question:** "Governance from the Cleveland government website (during onboarding) should be shared across departments, while primary governance stays intact. How do we implement this?"

---

## Short Answer

**Create a two-tier governance system:**

1. **Tier 1: Policy Governance** (human-written rules) - stays unchanged ✅
2. **Tier 2: Knowledge Governance** (Cleveland website content) - shared across all agents 🎯

This ensures agents use same sources, give same answers, and cite sources.

---

## The Problem You Identified

**You're right!** Currently:
- ❌ Each agent has isolated knowledge (can contradict each other)
- ❌ Knowledge from Cleveland website not shared
- ❌ No consistent source citations

**You want:**
- ✅ Cleveland website content shared across all agents
- ✅ Policy governance (governance_policies.json) stays intact
- ✅ Agents use same sources, give same answers, cite sources

---

## The Solution: Two Tiers

### Tier 1: Policy Governance (Unchanged)

**What it is:**
- Human-written rules in `data/governance_policies.json`
- Example: "Escalate PII queries", "Require approval for high-impact"

**What it governs:**
- When to escalate (HITL modes)
- What requires approval
- Risk detection (PII, legal, financial)

**Status:** ✅ **STAYS COMPLETELY INTACT** - No changes needed

### Tier 2: Knowledge Governance (New)

**What it is:**
- Content from Cleveland government website
- Discovered during onboarding
- Stored in shared "city_canon" collection

**What it provides:**
- Organizational facts
- City policies
- Budget information
- Strategic plans
- Service descriptions

**Status:** 🎯 **NEW** - This is what we're adding

---

## How It Works

### During Onboarding

```
1. Onboarding discovers Cleveland website
   └─ Finds: policies, budget, services, org structure

2. Extracts canonical content
   └─ Categorizes: organizational, policies, budget, etc.

3. Populates "city_canon" collection
   └─ Shared knowledge base for all agents

4. Creates agents
   └─ Each agent can query city_canon + own knowledge
```

### During Agent Queries

**Before (Current - Isolated):**
```
HR Agent queries only agent_hr collection
Mayor Agent queries only agent_mayor collection
→ Can have different info = contradictory answers
```

**After (New - Shared Canon):**
```
HR Agent queries city_canon + agent_hr
Mayor Agent queries city_canon + agent_mayor
→ Both see same Cleveland website content = consistent answers
```

---

## Example: Budget Question

**Before:**
```
User: "What is Cleveland's AI initiative budget?"

HR Agent: "I don't have that information"
└─ No budget docs in agent_hr collection

Mayor Agent: "$2.5M according to my files"
└─ Has budget doc in agent_mayor collection

Problem: Inconsistent answers!
```

**After:**
```
User: "What is Cleveland's AI initiative budget?"

Both agents query city_canon first:

HR Agent: "According to [City Canon: Strategic_Plan_2026.pdf], 
the AI initiative budget is $2.5M"
└─ From city_canon (shared)

Mayor Agent: "According to [City Canon: Strategic_Plan_2026.pdf], 
the AI initiative budget is $2.5M"
└─ From city_canon (shared)

Solution: Same answer, clear citation!
```

---

## Implementation Roadmap

### Week 1: Core Infrastructure

**Add to KnowledgeManager:**
```python
# New constant
CITY_CANON_AGENT_ID = "city_canon"

# New methods
def add_to_city_canon(filename, content):
    """Add document to shared city canon."""
    
def query_with_canon(agent_id, query):
    """Query both canon and agent-specific knowledge."""
```

### Week 1: Onboarding Integration

**Extract canonical content:**
- Organizational structure pages
- Policy and procedure pages
- Budget and finance pages
- Strategic plan pages
- Service description pages

**Populate city_canon automatically** during onboarding.

### Week 2: Agent Integration

**Update agent queries:**
```python
# Change from:
results = knowledge_manager.query(agent_id, query)

# To:
results = knowledge_manager.query_with_canon(agent_id, query)
```

**Mark sources:**
- "City Canon Source: ..." (from Cleveland website)
- "Department Source: ..." (agent-specific)

### Week 2: API Endpoints

```
POST   /city-canon/documents    (upload to canon)
POST   /city-canon/urls         (add website to canon)
GET    /city-canon/documents    (list canon docs)
DELETE /city-canon/documents/:id (remove from canon)
```

---

## Benefits

| Benefit | How It Helps |
|---------|--------------|
| **Shared Sources** | All agents see Cleveland website content |
| **Consistent Answers** | Same facts from city_canon = no contradictions |
| **Clear Citations** | "City Canon" vs "Department" sources clearly marked |
| **Policy Intact** | governance_policies.json completely unchanged |
| **Easy Onboarding** | Automatic population from website discovery |
| **Easy Maintenance** | Update canon once, all agents benefit |

---

## Your Three Requirements: ✅ All Solved

### Requirement 1: Agents use same knowledge source

**Solution:** City canon collection
- Cleveland website content stored in city_canon
- All agents query city_canon first
- Ensures common baseline of facts

### Requirement 2: Agents give same factual answers

**Solution:** Shared canon prioritized
- Query returns: 2 from canon + 3 from agent
- Canon results listed first
- Consistent facts across agents

### Requirement 3: Agents cite their sources

**Solution:** Source marking
- Format: "[City Canon Source: filename]"
- vs: "[Department Source: filename]"
- Clear indication of authoritative vs. specific sources

---

## Policy Governance: Completely Unchanged

**Your concern:** "Primary governance (human policies) should stay intact"

**Answer:** ✅ **Guaranteed!**

**Policy governance (governance_policies.json):**
- No changes to file
- No changes to rules
- No changes to evaluation logic
- Still controls HITL, approvals, risk

**Knowledge governance (city_canon):**
- Separate system
- Additive, not replacement
- Only affects knowledge retrieval
- Doesn't touch policy logic

**They work together:**
```
Policy Governance: Controls HOW agents respond
Knowledge Governance: Controls WHAT agents say

Both needed, both independent, both work together.
```

---

## Migration for Existing Deployments

**No breaking changes:**
1. Deploy code update
2. City canon created automatically
3. Re-run onboarding OR manually upload key docs
4. Restart API
5. Verify agents see canon content

**Backward compatible:**
- If no city_canon exists, works as before
- Gradual migration possible
- Can test with one agent first

---

## Next Steps

1. **Review Implementation Plan:**
   - See [TWO_TIER_GOVERNANCE_IMPLEMENTATION.md](./TWO_TIER_GOVERNANCE_IMPLEMENTATION.md)
   - Complete technical design with code

2. **Approve for Implementation:**
   - 3 weeks to complete
   - No breaking changes
   - Can start with Phase 1

3. **Deploy:**
   - Phase by phase rollout
   - Test at each phase
   - Monitor consistency improvements

---

## Summary

You identified a critical need: **governance from Cleveland website should be shared across agents while keeping policy governance intact.**

**Solution:** Two-tier governance system
- **Tier 1:** Policy governance (governance_policies.json) - unchanged ✅
- **Tier 2:** Knowledge governance (city_canon from Cleveland website) - new 🎯

**Result:**
- ✅ Agents use same knowledge sources (city_canon)
- ✅ Agents give same factual answers (shared canon)
- ✅ Agents cite their sources (clear marking)
- ✅ Policy governance stays intact (no changes)

**Timeline:** 3 weeks, no breaking changes, full documentation provided.

---

**Document Version:** 1.0  
**Date:** January 28, 2026  
**Status:** Design Complete, Ready for Implementation
