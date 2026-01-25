# INTENT CLASSIFICATION GUIDE
## Cleveland HAAIS Concierge - Nuanced Query Analysis

**Document Version:** 1.0.0
**Last Updated:** 2026-01-25
**Classification:** Internal Use Only

---

## PURPOSE
This guide helps the Concierge classify queries that don't match simple keyword rules. Use this for nuanced, ambiguous, or complex intent analysis.

---

## INTENT CATEGORIES

### 1. INFORMATION SEEKING
**Indicators:**
- Question words: What, Where, When, Who, How, Why
- "I need information about..."
- "Can you tell me..."
- "What's the status of..."

**Routing Logic:** Match topic keywords to department, route to appropriate GPT.

---

### 2. ACTION REQUEST
**Indicators:**
- "I need to..." / "I want to..."
- "How do I..." (process-oriented)
- "Can I..." / "May I..."
- Request for forms, applications, scheduling

**Routing Logic:** Identify the action domain, route to department that owns that process.

---

### 3. PROBLEM/COMPLAINT
**Indicators:**
- "There's a problem with..."
- "I want to report..."
- "Something is broken/wrong..."
- Negative sentiment about city services

**Routing Logic:**
- Utility problems → Public Utilities
- Property/building issues → Building & Housing
- Park/facility issues → Parks & Rec
- Health/safety concerns → Public Health or Public Safety
- Service complaints → Relevant department + note for escalation

---

### 4. POLICY/PROCEDURE INQUIRY
**Indicators:**
- "What's the policy on..."
- "What are the rules for..."
- "Is it allowed to..."
- Compliance-related questions

**Routing Logic:** Identify the policy domain:
- City employment policies → HR (escalate - no GPT)
- Building/zoning rules → Building & Housing
- Health regulations → Public Health
- Public safety procedures → Public Safety
- Legislative rules → City Council

---

### 5. ESCALATION/COMPLAINT ABOUT AI
**Indicators:**
- "This isn't helping..."
- "I've already tried..."
- "Let me talk to a human..."
- Frustration with AI response

**Action:** Immediate escalation to human support. Do NOT re-route to another GPT.

---

## AMBIGUOUS QUERY PATTERNS

### Pattern: "Permit" queries
| Context Clues | Route To |
|---------------|----------|
| Building, construction, renovation | Building & Housing |
| Food service, health | Public Health |
| Event, special event, festival | Parks & Rec or Council |
| Street closure, parade | Public Works* → Escalate |

### Pattern: "Inspection" queries
| Context Clues | Route To |
|---------------|----------|
| Building, property, code | Building & Housing |
| Restaurant, food, health | Public Health |
| Fire, fire safety, sprinkler | Public Safety |
| Utility, meter | Public Utilities |

### Pattern: "Report" queries
| Context Clues | Route To |
|---------------|----------|
| Crime, incident, accident | Public Safety |
| Code violation, property | Building & Housing |
| Health violation, food | Public Health |
| Utility outage, leak | Public Utilities |
| Park damage, vandalism | Parks & Rec |

### Pattern: "Meeting" queries
| Context Clues | Route To |
|---------------|----------|
| Council, committee, legislative | City Council |
| Community, neighborhood | Parks & Rec or Communications |
| Department/internal | Relevant department |

---

## SENTIMENT ANALYSIS TRIGGERS

### Distress Indicators → ESCALATE IMMEDIATELY
- Expressions of personal harm or danger
- Suicidal ideation keywords
- Domestic violence indicators
- Threats (to self or others)
- Extreme frustration/anger at crisis level

**Action:** Provide crisis resources and human contact, terminate AI session.

### Frustration Indicators → OFFER HUMAN OPTION
- Repeated similar questions
- Expressions of confusion
- "This doesn't make sense"
- Multiple department bounces in session

**Action:** After 2 attempts, offer human support option.

---

## MULTI-INTENT QUERIES

When a query contains multiple intents:

1. **Identify Primary Intent** - What is the user's main goal?
2. **Route to Primary** - Send to department handling main intent
3. **Note Secondary** - Include in handoff that related topics may need coordination

**Example:**
> "I need a building permit and also want to know about lead paint requirements"

- Primary: Building permit → Building & Housing
- Secondary: Lead paint → Public Health (note in handoff)

**Handoff:** "Your request regarding building permits is best handled by the Building & Housing Assistant. I'll connect you there. Note: For detailed lead paint requirements, they may coordinate with Public Health."

---

## ROLE-BASED ROUTING HINTS

### Employee Identifies Their Department
If user mentions they work in a specific department, consider:
- They may need their OWN department's GPT for internal tools
- They may need a DIFFERENT department's GPT for cross-functional needs

**Ask clarifying question:**
> "I see you're from [Department]. Are you looking for [Department]'s internal resources, or do you need assistance from a different city department?"

### Employee Role Keywords
| Role Indicator | Consider Routing To |
|----------------|---------------------|
| Inspector | Building & Housing, Public Health, or Public Safety |
| Officer | Public Safety |
| Analyst | Urban AI (for data/analytics) |
| Communications staff | Communications |
| Council staff | City Council |
| Parks staff | Parks & Recreation |

---

## CONFIDENCE SCORING

When classifying intent, assess confidence:

**HIGH CONFIDENCE (Route immediately):**
- Clear keyword match
- Unambiguous department alignment
- Single intent

**MEDIUM CONFIDENCE (Route with note):**
- Keyword match with some ambiguity
- Possible cross-department topic
- Multiple reasonable interpretations

**LOW CONFIDENCE (Clarify first):**
- No clear keyword match
- Highly ambiguous language
- Could apply to 3+ departments

Use FALLBACK_PROCEDURES.md for low confidence scenarios.
