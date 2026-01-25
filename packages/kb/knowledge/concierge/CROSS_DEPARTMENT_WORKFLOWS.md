# CROSS-DEPARTMENT WORKFLOWS
## Cleveland HAAIS - Multi-Department Coordination Protocols

**Document Version:** 1.0.0
**Last Updated:** 2026-01-25
**Classification:** Internal Use Only

---

## PURPOSE
This document defines standard workflows for queries that require coordination between multiple city departments.

---

## WORKFLOW INDEX

| Workflow ID | Name | Departments Involved |
|-------------|------|---------------------|
| WF-001 | New Business Opening | Building & Housing, Public Health, Public Utilities |
| WF-002 | Special Event Permit | Parks & Rec, Public Safety, Communications |
| WF-003 | Construction Project | Building & Housing, Public Utilities, Public Safety |
| WF-004 | Health Emergency Response | Public Health, Public Safety, Communications |
| WF-005 | Code Violation Resolution | Building & Housing, Public Health, Law* |
| WF-006 | Legislative Initiative | City Council, Urban AI, Relevant Departments |
| WF-007 | Community Program Launch | Parks & Rec, Communications, Public Health |
| WF-008 | Infrastructure Project | Public Utilities, Public Works*, Public Safety |

*Departments without GPTs - escalate to human

---

## WORKFLOW DETAILS

### WF-001: New Business Opening

**Scenario:** User wants to open a new business in Cleveland

**Departments:**
- Primary: Building & Housing (permits, occupancy)
- Secondary: Public Health (if food service)
- Secondary: Public Utilities (service connections)

**Sequence:**
```
1. Concierge → Building & Housing GPT
   "User is opening a new business. Please guide through:
   - Zoning verification
   - Building permit requirements
   - Certificate of occupancy process
   Flag if food service for Public Health coordination."

2. IF food_service THEN Building & Housing → Concierge → Public Health
   "User opening food service business. Building permits in progress.
   Please guide through:
   - Food service license
   - Health inspection scheduling
   - Food handler requirements"

3. Building & Housing notes utility needs → User contacts Public Utilities
   "Contact Public Utilities at [CONTACT] for:
   - Commercial electric service (CPP)
   - Water/sewer connection
   - Utility account setup"
```

**Handoff Message:**
```
"Opening a business involves several city departments. I'll start you with
Building & Housing for permits. They'll coordinate with Public Health
if you're serving food, and guide you on utility setup."
```

---

### WF-002: Special Event Permit

**Scenario:** User wants to hold a public event (festival, parade, gathering)

**Departments:**
- Primary: Parks & Rec (park events) OR City Council (street events)
- Secondary: Public Safety (security, traffic)
- Secondary: Communications (promotion support)

**Sequence:**
```
1. Concierge determines venue type:
   - Park/facility → Parks & Rec GPT
   - Street/public way → Escalate (no Public Works GPT)

2. Parks & Rec OR Escalation handles:
   - Permit application
   - Insurance requirements
   - Fee structure

3. Parks & Rec notes → Concierge → Public Safety
   "Event planned at [LOCATION] on [DATE]. Estimated [#] attendees.
   Please advise on:
   - Security requirements
   - Traffic management needs
   - Fire safety compliance"

4. IF promotion_requested → Concierge → Communications
   "Event approved for [DETAILS]. User requesting promotional support.
   Please advise on:
   - City calendar listing
   - Social media support eligibility
   - Press release assistance"
```

**Handoff Message:**
```
"Special events require coordination between several departments.
For a [park event/street event], I'll connect you with [PRIMARY_GPT]
to start the permit process. They'll coordinate with Public Safety
for security requirements."
```

---

### WF-003: Construction Project

**Scenario:** Major construction or renovation project

**Departments:**
- Primary: Building & Housing (permits, inspections)
- Secondary: Public Utilities (utility coordination)
- Secondary: Public Safety (fire safety)

**Sequence:**
```
1. Concierge → Building & Housing GPT
   "User has construction project. Please guide through:
   - Permit types needed
   - Plan review process
   - Inspection scheduling
   Coordinate with utilities and fire as needed."

2. Building & Housing identifies utility impacts → Note to user
   "Contact Public Utilities for:
   - Temporary service connections
   - Utility locate requests
   - Service upgrades"

3. IF commercial OR multi_family → Building & Housing notes
   → Concierge → Public Safety
   "Commercial/multi-family construction at [ADDRESS].
   Please advise on:
   - Fire suppression requirements
   - Fire inspection scheduling
   - Certificate of occupancy fire clearance"
```

**Handoff Message:**
```
"Construction projects typically start with Building & Housing for permits.
Based on your project scope, they may coordinate with Public Utilities
for service connections and Public Safety for fire inspections."
```

---

### WF-004: Health Emergency Response

**Scenario:** Disease outbreak, contamination, public health emergency

**Departments:**
- Primary: Public Health (lead response)
- Secondary: Public Safety (enforcement support)
- Secondary: Communications (public messaging)

**Sequence:**
```
1. Concierge → Public Health GPT
   "Potential health emergency reported: [BRIEF_DESCRIPTION]
   PRIORITY FLAG: Elevated response protocol
   Please guide through:
   - Initial assessment
   - Reporting requirements
   - Immediate actions"

2. Public Health assesses severity:
   - Level 1: Standard response
   - Level 2: Multi-agency notification
   - Level 3: Emergency operations activation

3. IF level >= 2 → Public Health → Concierge → Communications
   "Health situation at [LOCATION] requires public notification.
   Sensitivity: [LEVEL]
   Please coordinate:
   - Public advisory messaging
   - Media response preparation
   - Social media monitoring"

4. IF enforcement_needed → Public Health → Concierge → Public Safety
   "Health order issued for [LOCATION/ENTITY].
   Compliance support needed for:
   - [SPECIFIC_ENFORCEMENT_NEED]"
```

**Handoff Message:**
```
"Health concerns are handled by our Public Health department.
I'm connecting you immediately. If this is a life-threatening emergency,
please call 911."
```

---

### WF-005: Code Violation Resolution

**Scenario:** Property with multiple code violations

**Departments:**
- Primary: Building & Housing (structural, housing codes)
- Secondary: Public Health (health codes)
- Tertiary: Law Department* (legal enforcement)

**Sequence:**
```
1. Concierge → Building & Housing GPT
   "Code violation inquiry for [ADDRESS/DESCRIPTION].
   Please guide through:
   - Violation identification
   - Compliance requirements
   - Timeline for resolution"

2. IF health_hazard THEN Building & Housing → Concierge → Public Health
   "Property at [ADDRESS] has potential health violations:
   - [HEALTH_ISSUES]
   Please coordinate:
   - Health inspection
   - Abatement requirements"

3. IF legal_action_needed → Escalate to Human
   "Violations at [ADDRESS] may require legal action.
   Please connect with Law Department for:
   - Citation enforcement
   - Court proceedings
   - Lien placement"
```

**Handoff Message:**
```
"Code violations are primarily handled by Building & Housing.
They can coordinate with Public Health for health-related issues.
If legal enforcement is needed, they'll connect you with the appropriate staff."
```

---

### WF-006: Legislative Initiative

**Scenario:** New policy, ordinance, or city initiative

**Departments:**
- Primary: City Council (legislative process)
- Secondary: Urban AI (if AI/technology related)
- Tertiary: Relevant operational departments

**Sequence:**
```
1. Concierge → City Council GPT
   "Legislative inquiry regarding [TOPIC].
   Please guide through:
   - Legislative process overview
   - Committee assignment
   - Timeline expectations"

2. IF ai_technology_related → City Council notes
   → Concierge → Urban AI GPT
   "Legislative initiative involving AI/technology: [TOPIC]
   Please provide:
   - Technical feasibility assessment
   - Governance implications
   - HAAIS alignment review"

3. City Council identifies operational departments
   → Note for coordination
   "Once legislation advances, coordinate implementation with:
   - [OPERATIONAL_DEPARTMENTS]"
```

**Handoff Message:**
```
"Legislative matters go through City Council.
I'll connect you with the Council Assistant who can explain
the process and coordinate with relevant departments."
```

---

### WF-007: Community Program Launch

**Scenario:** New community program or service

**Departments:**
- Primary: Parks & Rec (most community programs)
- Secondary: Communications (promotion)
- Tertiary: Public Health (if health-related)

**Sequence:**
```
1. Concierge → Parks & Rec GPT
   "Inquiry about community program: [DESCRIPTION]
   Please guide through:
   - Program development process
   - Resource requirements
   - Registration/scheduling"

2. Parks & Rec → Concierge → Communications
   "New community program launching: [PROGRAM_NAME]
   Target audience: [AUDIENCE]
   Please coordinate:
   - Promotional materials
   - Event calendar listing
   - Community outreach"

3. IF health_component → Parks & Rec notes
   → Concierge → Public Health
   "Community program with health component: [PROGRAM]
   Please advise on:
   - Health requirements
   - Wellness program alignment
   - Resource partnerships"
```

**Handoff Message:**
```
"Community programs are coordinated through Parks & Recreation.
They work with Communications for promotion and can involve
Public Health for wellness components."
```

---

### WF-008: Infrastructure Project

**Scenario:** Major utility or infrastructure work

**Departments:**
- Primary: Public Utilities (water, electric, sewer)
- Secondary: Public Works* (roads, bridges - no GPT)
- Tertiary: Public Safety (traffic, emergency access)

**Sequence:**
```
1. Concierge → Public Utilities GPT
   "Infrastructure inquiry: [DESCRIPTION]
   Please guide through:
   - Project scope assessment
   - Permitting requirements
   - Timeline coordination"

2. IF road_impact → Escalate portion to human
   "Road/surface work required - coordinate with Public Works:
   - Street opening permits
   - Traffic management plan
   - Surface restoration"

3. Public Utilities → Concierge → Public Safety
   "Infrastructure work affecting [AREA] from [DATES].
   Please coordinate:
   - Traffic control requirements
   - Emergency access routes
   - Public notification"
```

**Handoff Message:**
```
"Infrastructure projects involve Public Utilities for water/electric/sewer work.
They coordinate with other departments for road access and safety.
I'll start you with Public Utilities."
```

---

## COORDINATION PRINCIPLES

### Lead Department Responsibilities
1. Own the user relationship through resolution
2. Initiate handoffs to supporting departments
3. Track overall progress
4. Report completion to Concierge for logging

### Supporting Department Responsibilities
1. Respond to coordination requests promptly
2. Provide specific guidance within scope
3. Return user to lead department when complete
4. Flag if issue grows beyond original scope

### Concierge Responsibilities
1. Initial routing to lead department
2. Facilitate inter-department handoffs
3. Monitor for escalation triggers
4. Log workflow completion

---

## ESCALATION TRIGGERS

Immediately escalate to human when:
- Workflow involves 4+ departments
- Legal action is required
- Media involvement expected
- Elected official involvement
- Timeline exceeds standard expectations
- User expresses significant frustration

