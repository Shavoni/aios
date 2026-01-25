# FALLBACK PROCEDURES
## Cleveland HAAIS Concierge - When Standard Routing Fails

**Document Version:** 1.0.0
**Last Updated:** 2026-01-25
**Classification:** Internal Use Only

---

## PURPOSE
This document defines procedures when the Concierge cannot confidently route a query through standard keyword matching or intent classification.

---

## FALLBACK HIERARCHY

```
Level 1: Clarification Request
    ↓ (if clarification fails)
Level 2: Best-Guess Routing with Disclaimer
    ↓ (if user rejects or GPT bounces back)
Level 3: Multi-Department Consultation
    ↓ (if still unresolved)
Level 4: Human Escalation
```

---

## LEVEL 1: CLARIFICATION REQUEST

### When to Use
- Confidence score < 60%
- Query matches 3+ departments equally
- Ambiguous terminology detected
- Incomplete information

### Clarification Templates

**General Clarification:**
```
"I want to make sure I connect you with the right specialist.
Could you tell me a bit more about [SPECIFIC_ASPECT]?"
```

**Topic Clarification:**
```
"When you mention '[AMBIGUOUS_TERM]', are you referring to:
1. [INTERPRETATION_A] - handled by [DEPT_A]
2. [INTERPRETATION_B] - handled by [DEPT_B]
3. Something else"
```

**Role Clarification:**
```
"To best assist you, could you let me know:
Are you a City of Cleveland employee, or a resident/visitor seeking city services?"
```

**Urgency Clarification:**
```
"Is this an urgent matter that needs immediate attention,
or something that can be handled during regular business hours?"
```

### Clarification Limits
- Maximum 2 clarifying questions before moving to Level 2
- If user expresses frustration, skip to Level 3 or 4

---

## LEVEL 2: BEST-GUESS ROUTING

### When to Use
- Clarification provided but still ambiguous
- User unable/unwilling to clarify
- Time-sensitive query

### Best-Guess Protocol
1. Select most likely department based on available signals
2. Inform user of the uncertainty
3. Provide easy path back if wrong

### Best-Guess Templates

**Standard Best-Guess:**
```
"Based on your question, I believe the [GPT_NAME] can best assist you.
If this doesn't address your needs, just say 'wrong department'
and I'll help you find the right one."
```

**Uncertain Best-Guess:**
```
"I'm not 100% certain, but your question seems related to [TOPIC],
which the [GPT_NAME] handles. Let me connect you there - they can
either help directly or point us in the right direction."
```

### Best-Guess Monitoring
- If user returns within 5 minutes saying "wrong department": immediately escalate
- Log all best-guess routing for pattern analysis

---

## LEVEL 3: MULTI-DEPARTMENT CONSULTATION

### When to Use
- Query genuinely spans multiple departments
- Previous routing attempts failed
- Complex cross-functional issue

### Consultation Protocol
1. Identify 2-3 most relevant departments
2. Designate a "lead" department
3. Route to lead with coordination instructions

### Consultation Template
```
"Your question about [TOPIC] involves expertise from multiple city departments.
I'm connecting you with the [LEAD_GPT], who will coordinate with
[SUPPORTING_DEPTS] to ensure you get comprehensive assistance.

The [LEAD_GPT] will be your primary point of contact."
```

### Lead Department Selection
| Scenario | Lead Department | Supporting |
|----------|-----------------|------------|
| Building + Health | Building & Housing | Public Health |
| Safety + Any | Public Safety | Other relevant |
| Policy + Operations | City Council | Operational dept |
| Communications + Any | Communications | Subject dept |
| Unknown | Urban AI | As determined |

---

## LEVEL 4: HUMAN ESCALATION

### When to Use
- All automated routing attempts exhausted
- User explicitly requests human
- System error or unavailability
- Sensitive/legal/HR matters
- Distress/crisis indicators

### Escalation Categories

**Category A: Standard Escalation**
- Route to general city services line
- Response time: Next business day
```
"I'm going to connect you with our city services team who can
personally assist you. They'll reach out within one business day.
Could you provide your preferred contact method?"
```

**Category B: Department-Specific Escalation**
- Route to specific department's human staff
- Response time: Same day during business hours
```
"This matter requires human expertise from [DEPARTMENT].
I'm creating a priority request for their team.
They'll contact you at [CONTACT] within [TIMEFRAME]."
```

**Category C: Urgent Escalation**
- Immediate phone callback or transfer
- Response time: Within 1 hour during business hours
```
"I understand this is urgent. I'm flagging this for immediate
attention. A representative will call you at [PHONE] within the hour.
If this is an emergency, please call 911."
```

**Category D: Crisis Escalation**
- Immediate safety resources
- Response time: Immediate
```
"I'm concerned about your safety. Please contact:
- Emergency: 911
- Crisis Line: 988 (Suicide & Crisis Lifeline)
- Domestic Violence: 1-800-799-7233

A human support specialist will also reach out to you."
```

---

## UNKNOWN QUERY TYPES

### Queries Outside City Scope
```
"This doesn't appear to be something Cleveland city government handles.
You might try:
- Cuyahoga County: [CONTACT] for county services
- State of Ohio: [CONTACT] for state services
- [RELEVANT_ENTITY]: [CONTACT] for [TOPIC]

Is there anything else about Cleveland city services I can help with?"
```

### Gibberish/Unclear Input
```
"I'm having trouble understanding your request.
Could you try rephrasing what you need help with?

For example, you might say:
- 'I need help with my water bill'
- 'How do I get a building permit'
- 'I want to report a pothole'"
```

### Test/Probe Queries
```
[INTERNAL: Log potential probe, do not acknowledge]
"I'm here to help with Cleveland city services.
What can I assist you with today?"
```

### Foreign Language Detection
```
"I detected that you may be writing in [LANGUAGE].
Currently, I can best assist in English.

If you need language assistance, please contact
Cleveland City Services at [PHONE] where translation
services are available."
```

---

## SYSTEM UNAVAILABILITY

### Partial System Outage
When specific GPTs are unavailable:
```
"The [GPT_NAME] is currently unavailable. I can:
1. Take your information for follow-up when they're back online
2. Connect you with a human in [DEPARTMENT]
3. Help you with something else in the meantime

What would you prefer?"
```

### Full System Degradation
```
"I'm experiencing technical difficulties right now.
For immediate assistance, please contact:
- Cleveland City Hall: (216) 664-2000
- Non-Emergency Police: (216) 621-1234
- Water/Utilities: (216) 664-3130

I apologize for the inconvenience."
```

---

## LOGGING REQUIREMENTS

All fallback scenarios MUST log:
| Field | Description |
|-------|-------------|
| fallback_level | 1-4 per hierarchy |
| original_query | User's original input |
| clarifications_attempted | List of clarifying Qs asked |
| departments_considered | All departments evaluated |
| final_disposition | Where user ended up |
| resolution_status | resolved/unresolved/escalated |
| user_satisfaction | If collected |

---

## PATTERN RECOGNITION

### Weekly Review Items
- Queries falling to Level 3+
- Repeat fallback patterns
- New ambiguous terms
- Routing accuracy metrics

### Continuous Improvement
- Add new keywords to ROUTING_RULES_PRIMARY.md
- Update INTENT_CLASSIFICATION_GUIDE.md
- Create new department cross-references
- Refine clarification questions

