# HANDOFF PROTOCOLS
## Cleveland HAAIS Concierge - GPT-to-GPT Transfer Standards

**Document Version:** 1.0.0
**Last Updated:** 2026-01-25
**Classification:** Internal Use Only

---

## PURPOSE
This document defines the standard protocols for transferring user sessions between the Concierge and departmental GPTs, and between departmental GPTs when cross-functional needs arise.

---

## HANDOFF TYPES

### Type 1: Concierge → Departmental GPT
**Trigger:** User intent classified, department identified
**Protocol:**
1. Confirm understanding of user request
2. Announce target GPT by name
3. Provide brief context to receiving GPT
4. Transfer session with full context

**Template:**
```
[TO USER]
I understand you need assistance with [TOPIC]. The [GPT_NAME] specializes in this area.
Connecting you now...

[TO RECEIVING GPT - CONTEXT PACKET]
{
  "handoff_type": "concierge_to_department",
  "user_intent": "[CLASSIFIED_INTENT]",
  "topic_summary": "[BRIEF_SUMMARY]",
  "keywords_detected": ["keyword1", "keyword2"],
  "user_role": "[employee/citizen/unknown]",
  "sensitivity_level": "[public/internal/confidential/restricted]",
  "prior_attempts": 0,
  "session_id": "[SESSION_UUID]"
}
```

---

### Type 2: Departmental GPT → Different Department
**Trigger:** Query falls outside current GPT's scope
**Protocol:**
1. Acknowledge the cross-functional need
2. Request Concierge mediation (do NOT direct-transfer)
3. Concierge validates and routes

**Template:**
```
[FROM DEPARTMENTAL GPT TO CONCIERGE]
{
  "handoff_type": "department_to_concierge",
  "originating_gpt": "[CURRENT_GPT_ID]",
  "reason": "out_of_scope",
  "suggested_destination": "[SUGGESTED_GPT_ID]",
  "user_query": "[ORIGINAL_QUERY]",
  "context_summary": "[WHAT_WAS_DISCUSSED]",
  "session_id": "[SESSION_UUID]"
}

[TO USER]
This question about [NEW_TOPIC] is better handled by a different specialist.
Let me route you through our Concierge to ensure you reach the right department.
```

---

### Type 3: GPT → Human Escalation
**Trigger:** User requests human, system limitation, or policy requirement
**Protocol:**
1. Acknowledge escalation need
2. Gather contact preference
3. Create escalation ticket
4. Provide confirmation and timeline

**Template:**
```
[TO USER]
I understand you'd prefer to speak with a human representative about [TOPIC].

To connect you with the right person, I'll need:
- Your preferred contact method (phone/email)
- Best time to reach you
- Brief description of your concern

[ESCALATION TICKET]
{
  "escalation_type": "human_request",
  "department": "[RELEVANT_DEPARTMENT]",
  "urgency": "[low/medium/high/critical]",
  "user_contact": "[CONTACT_INFO]",
  "summary": "[ISSUE_SUMMARY]",
  "ai_attempts": "[WHAT_AI_TRIED]",
  "session_transcript_id": "[SESSION_UUID]"
}
```

---

## CONTEXT PRESERVATION

### Required Context Fields
Every handoff MUST include:
| Field | Description | Required |
|-------|-------------|----------|
| session_id | Unique session identifier | Yes |
| user_intent | Classified intent category | Yes |
| topic_summary | Brief description of need | Yes |
| sensitivity_level | Data classification | Yes |
| prior_attempts | Number of routing attempts | Yes |
| user_role | Employee/citizen/unknown | Yes |

### Optional Context Fields
| Field | Description | When to Include |
|-------|-------------|-----------------|
| department_affiliation | User's department (if employee) | When identified |
| referenced_documents | Documents discussed | When relevant |
| prior_gpts_visited | GPTs already consulted | Multi-bounce scenarios |
| frustration_indicators | Signs of user frustration | When detected |
| special_accommodations | Accessibility needs | When disclosed |

---

## HANDOFF SCRIPTS BY SCENARIO

### Scenario: Clear Single-Department Match
```
"Your question about [TOPIC] is exactly what the [GPT_NAME] handles.
I'm connecting you now. They'll have full context of our conversation."
```

### Scenario: Possible Multi-Department Need
```
"Your request involves [TOPIC], which primarily falls under [PRIMARY_DEPT].
I'm connecting you to the [PRIMARY_GPT]. They can coordinate with
[SECONDARY_DEPT] if needed for the [SECONDARY_ASPECT]."
```

### Scenario: No Clear Match - Clarification Needed
```
"I want to make sure I connect you with the right specialist.
Could you help me understand: [CLARIFYING_QUESTION]?"
```

### Scenario: User Frustration Detected
```
"I can see this hasn't been straightforward. Let me make sure you get
the help you need. Would you prefer:
1. A direct connection to a human representative
2. One more try with a specialist GPT in [SUGGESTED_AREA]"
```

### Scenario: Emergency Detection
```
"STOP - This sounds like an emergency situation.
Please dial 9-1-1 immediately for [fire/police/medical] assistance.
This AI service cannot handle emergencies."
```

---

## BOUNCE PREVENTION

### Definition
A "bounce" occurs when a user is transferred between GPTs without resolution.

### Maximum Bounces
- **Hard Limit:** 3 transfers per session
- **Soft Limit:** 2 transfers triggers human option

### Bounce Counter Logic
```
IF bounce_count >= 2:
    OFFER human escalation option

IF bounce_count >= 3:
    FORCE human escalation
    LOG incident for review
```

### Bounce Recovery Script
```
"I apologize - it seems we've had some difficulty finding the right
specialist for your needs. Rather than transfer you again, let me
connect you directly with a human representative who can ensure
you get the help you need. Is that okay?"
```

---

## SPECIAL HANDOFF RULES

### Confidential/Restricted Topics
When sensitivity_level is "confidential" or higher:
1. Do NOT include detailed query in handoff logs
2. Use generic topic descriptors
3. Ensure receiving GPT has appropriate clearance
4. Log handoff in secure audit trail

### Employee vs. Citizen
| User Type | Context Shared | Sensitivity Default |
|-----------|----------------|---------------------|
| Employee | Full context + role | internal |
| Citizen | Limited context | public |
| Unknown | Minimal context | public |

### After-Hours Handoffs
If query arrives outside business hours (M-F 8:30-4:30 EST):
1. Acknowledge limited availability
2. Offer to create ticket for next business day
3. Provide emergency contacts if urgent
4. Log for morning queue

---

## ERROR HANDLING

### Receiving GPT Unavailable
```
"The [GPT_NAME] is temporarily unavailable. I can:
1. Take your information and have them follow up
2. Connect you with a human in that department
3. Try again in a few minutes

What would you prefer?"
```

### Context Transfer Failed
```
"I apologize - there was a technical issue with the transfer.
Let me gather your information again to ensure nothing is lost.
Could you briefly restate your question?"
```

### Invalid Handoff Request
```
[INTERNAL LOG]
Invalid handoff attempted from [SOURCE] to [DESTINATION]
Reason: [VALIDATION_ERROR]
Action: Return to Concierge for re-routing
```

---

## AUDIT REQUIREMENTS

Every handoff MUST log:
- Timestamp (UTC)
- Source GPT ID
- Destination GPT ID
- Handoff type
- User consent (implicit/explicit)
- Context packet hash
- Session ID

Logs retained for: 90 days (operational), 7 years (compliance)

