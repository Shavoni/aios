# Grounded AI: Source Attribution & Authority Tracking

## HAAIS AIOS Enterprise Trust Infrastructure

> "What authoritative source justifies this output?"
>
> Every AIOS response can now answer this question.

---

## Overview

AIOS now implements **Grounded AI** - a system where every AI response is traced back to authoritative sources with explicit authority levels. This transforms AIOS from a chatbot into **institutional decision infrastructure**.

### The Problem Grounded AI Solves

| Weak AI Pattern | AIOS Grounded Pattern |
|----------------|----------------------|
| "The model said…" | "The system cited HR Policy §4.2 + City Ordinance 12.4" |
| Free-text outputs | Structured claims with source anchors |
| Probabilistic guesses | Policy-bound determinations |
| No accountability | Full audit trail with authority chain |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER QUERY                                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      GROUNDING ENGINE                                │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │ Source Citation │  │ Authority       │  │ Governance          │ │
│  │ Extraction      │  │ Classification  │  │ Reasoning           │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │ Grounding Score │  │ Verification    │  │ Response Lineage    │ │
│  │ Calculation     │  │ Status          │  │ Tracking            │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      GROUNDED RESPONSE                               │
│                                                                      │
│  response: "You receive 20 days PTO per year."                      │
│  grounding_score: 0.92                                              │
│  authority_basis: "HR Policy Manual §4.2"                           │
│  source_citations: [{source_id, quote, authority_level}]            │
│  verification_status: "verified"                                    │
│  governance_reasoning: "No policy concerns - INFORM mode"           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Concepts

### 1. Source Citations

Every substantive claim in a response is linked to its source:

```json
{
  "source_id": "doc_hr_policy_4.2",
  "source_type": "policy",
  "source_name": "HR Policy Manual",
  "authority_level": "organizational",
  "section_reference": "§4.2",
  "quote": "Employees with 5+ years of service receive 20 days PTO...",
  "relevance_score": 0.92,
  "verification_status": "verified"
}
```

### 2. Authority Levels

Sources are classified by authority level:

| Level | Description | Examples |
|-------|-------------|----------|
| **Constitutional** | Immutable core rules | City Charter, Federal Law |
| **Statutory** | Legal/regulatory requirements | Ordinances, HIPAA, GDPR |
| **Organizational** | Organization-wide policies | HR Policies, Finance Rules |
| **Departmental** | Department-specific rules | IT Procedures, Safety Protocols |
| **Operational** | Day-to-day procedures | FAQs, How-To Guides |

### 3. Grounding Score

A 0.0-1.0 score indicating how well-grounded a response is:

| Score | Meaning | Action |
|-------|---------|--------|
| 0.8-1.0 | Well-grounded | Auto-deliver |
| 0.5-0.8 | Moderately grounded | Consider review |
| 0.0-0.5 | Weakly grounded | Requires human review |

**Factors affecting score:**
- Source relevance
- Number of verified sources
- Authority level of sources
- Verification status

### 4. Verification Status

| Status | Meaning |
|--------|---------|
| `verified` | Human-verified as accurate |
| `unverified` | Not yet verified |
| `ai_generated` | Generated by AI without source backing |
| `requires_review` | Flagged for human verification |
| `deprecated` | Source is outdated |

### 5. Governance Reasoning

Human-readable explanation of why a governance decision was made:

```
"Response delivered immediately - no policy concerns detected.
 Domain: HR, Impact: low"
```

Or for more complex decisions:

```
"Response requires human review (DRAFT mode).
 Triggered policies: PII_PROTECTION, SALARY_DISCLOSURE.
 Detected: personal identifiable information.
 Domain: HR, Impact: high"
```

---

## API Response Format

### Enhanced AgentQueryResponse

```json
{
  "response": "Based on HR Policy §4.2, employees with 5+ years receive 20 days PTO.",
  "agent_id": "hr-assistant",
  "agent_name": "HR Assistant",
  "sources": [...],

  "source_citations": [
    {
      "source_id": "hr_policy_manual",
      "source_type": "policy",
      "source_name": "HR Policy Manual",
      "authority_level": "organizational",
      "section_reference": "§4.2",
      "quote": "Employees with 5+ years of continuous service...",
      "relevance_score": 0.92,
      "verification_status": "verified"
    }
  ],

  "grounding_score": 0.92,
  "authority_basis": "HR Policy Manual §4.2",
  "attribution": "ai_generated",
  "verification_status": "unverified",
  "requires_human_verification": false,
  "governance_reasoning": "Response delivered immediately - no policy concerns detected.",
  "confidence": 0.96,

  "hitl_mode": "INFORM",
  "governance_triggered": false,
  "policy_ids": [],
  "approval_required": false
}
```

---

## Response Lineage

Full traceability of how a response was generated:

```json
{
  "lineage_id": "lineage-a1b2c3d4e5f6",
  "request_id": "req-123",
  "timestamp": "2026-01-29T12:00:00Z",

  "original_query": "How much PTO do I get after 5 years?",
  "user_id": "emp-456",
  "user_role": "employee",
  "user_department": "Engineering",

  "agent_id": "hr-assistant",
  "agent_version": "1.0",

  "sources_retrieved": [...],
  "sources_used_in_response": ["hr_policy_manual"],

  "governance_decision": {
    "hitl_mode": "INFORM",
    "policy_trigger_ids": [],
    "reasoning": "No policy concerns detected"
  },

  "approval_required": false,
  "approved_by": null,

  "response_text": "Based on HR Policy §4.2...",
  "response_modified": false,

  "attribution": "ai_generated",
  "human_verified": false,
  "response_hash": "a1b2c3d4..."
}
```

---

## Implementation Details

### Files Added/Modified

| File | Purpose |
|------|---------|
| `packages/core/grounding.py` | **NEW** - Grounding engine with citation extraction |
| `packages/core/schemas/models.py` | Enhanced with grounding schemas |
| `packages/api/agents.py` | Updated response with grounding fields |

### Key Functions

```python
# Extract citations from sources
citations = extract_source_citations(response_text, sources)

# Calculate grounding score
metrics = calculate_grounding_score(response_text, citations)

# Generate governance reasoning
reasoning = generate_governance_reasoning(governance_decision, intent, risk_signals)

# Create full grounding summary
grounding = create_grounding_summary(response_text, sources, governance_decision)

# Create response lineage for audit
lineage = create_response_lineage(request_id, query, user_id, agent_id, ...)
```

---

## Use Cases

### 1. Government Compliance

```
Query: "Can I approve this $50,000 contract?"

Response: "According to City Ordinance 12.4 §3, contracts over $25,000
require City Council approval."

Grounding:
- authority_basis: "City Ordinance 12.4 §3"
- grounding_score: 0.95
- verification_status: "verified"
```

### 2. Healthcare (HIPAA)

```
Query: "Can I share patient records with the insurance company?"

Response: "Per HIPAA §164.502, patient authorization is required
for disclosure to insurance companies except for treatment,
payment, or healthcare operations."

Grounding:
- authority_basis: "HIPAA §164.502"
- grounding_score: 0.98
- governance_reasoning: "DRAFT mode triggered - PHI detected"
```

### 3. Financial Decisions

```
Query: "What's our budget for Q2 marketing?"

Response: "According to the 2026 Budget Allocation (Finance Policy B-4),
Marketing has $150,000 allocated for Q2."

Grounding:
- authority_basis: "Finance Policy B-4"
- grounding_score: 0.88
- verification_status: "requires_review" (budget data)
```

---

## Benefits

### For Compliance Officers
- **Audit Trail**: Every response traceable to source
- **Authority Chain**: Know what backs each decision
- **Verification**: Flag ungrounded claims automatically

### For End Users
- **Trust**: Know responses are based on real policies
- **Transparency**: See the sources behind answers
- **Confidence**: Grounding score indicates reliability

### For Administrators
- **Quality Control**: Monitor grounding scores across agents
- **Gap Identification**: Find topics lacking authoritative sources
- **Continuous Improvement**: Track verification rates over time

---

## Configuration

### Minimum Grounding Threshold

Set minimum grounding score for auto-delivery:

```python
# In governance policies
{
  "grounding_requirements": {
    "min_score_for_inform": 0.5,  # Below this = DRAFT mode
    "min_score_for_auto_approve": 0.8,
    "require_verified_sources": true
  }
}
```

### Authority Requirements by Domain

```python
{
  "domain_authority_requirements": {
    "Legal": "statutory",      # Must cite laws/regulations
    "HR": "organizational",    # Must cite HR policies
    "IT": "departmental",      # Can cite procedures
    "General": "operational"   # Any source acceptable
  }
}
```

---

## Future Enhancements

### Planned Features

1. **Per-Claim Grounding**: Map each sentence to its specific source
2. **Grounding Dashboard**: Visualize grounding metrics across agents
3. **Source Freshness**: Auto-flag responses using outdated sources
4. **Cross-Reference Validation**: Verify claims against multiple sources
5. **Grounding Alerts**: Notify when grounding drops below threshold

### Roadmap

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Basic source citations | ✅ Complete |
| 1 | Authority level classification | ✅ Complete |
| 1 | Grounding score calculation | ✅ Complete |
| 1 | Governance reasoning | ✅ Complete |
| 2 | Response lineage tracking | ✅ Complete |
| 2 | Per-claim mapping | 🔄 Planned |
| 3 | Grounding dashboard | 🔄 Planned |
| 3 | Source freshness alerts | 🔄 Planned |

---

## Summary

**Grounded AI** transforms AIOS from a chatbot into **institutional decision infrastructure**. Every response now carries:

1. **Source Citations** - What documents support this?
2. **Authority Basis** - What legal/policy authority backs this?
3. **Grounding Score** - How well-supported is this response?
4. **Verification Status** - Has a human verified this?
5. **Governance Reasoning** - Why was this decision made?
6. **Response Lineage** - Full audit trail for compliance

This is how AIOS becomes the **trust infrastructure** for enterprise AI.

---

*HAAIS AIOS Grounded AI v1.0*
*© 2026 DEF1LIVE LLC*
