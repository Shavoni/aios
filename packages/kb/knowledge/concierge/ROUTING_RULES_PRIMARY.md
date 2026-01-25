# ROUTING RULES PRIMARY
## Cleveland HAAIS Concierge - Keyword-Based Routing Rules

**Document Version:** 1.0.0
**Last Updated:** 2026-01-25
**Classification:** Internal Use Only

---

## PURPOSE
This document is the **absolute source of truth** for keyword-based routing decisions. The Concierge MUST use these rules to classify user intent and route to the appropriate departmental GPT.

---

## ROUTING RULES BY DEPARTMENT

### 1. URBAN AI DIRECTOR (cle-urban-ai-001)
**Route when keywords include:**
- AI strategy, AI governance, AI policy, HAAIS
- Data governance, data strategy, analytics
- What Works Cities, certification
- Innovation, digital transformation
- Pilot project, AI sandbox
- Dr. Crowe, Urban AI office
- Municipal AI, responsible AI
- Stakeholder engagement (for AI initiatives)

**Example queries:**
- "I need information about the city's AI strategy"
- "Who handles data governance?"
- "What's the status of What Works Cities certification?"

---

### 2. CITY COUNCIL (cle-city-council-002)
**Route when keywords include:**
- Ordinance, legislation, legislative
- Council meeting, committee meeting
- Ward, council member, council president
- Resolution, motion, vote
- Constituent, constituent services
- Municipal code, city code
- Public hearing, agenda
- Zoning variance (legislative aspect)

**Example queries:**
- "When is the next council meeting?"
- "I need help drafting an ordinance"
- "What committee handles public safety matters?"

---

### 3. PUBLIC UTILITIES (cle-public-utilities-003)
**Route when keywords include:**
- Water, water service, water main, water quality
- Cleveland Public Power, CPP, electric, power outage
- Sewer, wastewater, storm water
- Utility bill, utility rates
- Infrastructure (water/power)
- EPA compliance, PUCO
- Service connection, meter

**Example queries:**
- "There's a water main break on my street"
- "How do I dispute my utility bill?"
- "What are the EPA compliance requirements?"

---

### 4. PARKS & RECREATION (cle-parks-rec-004)
**Route when keywords include:**
- Park, parks, recreation center
- Program registration, youth programs, senior programs
- Facility rental, shelter rental
- Pool, swimming, aquatics
- Sports league, athletics
- Community event, festival
- Playground, trail, green space
- Alexandria Nichols (Parks Director)

**Example queries:**
- "How do I rent a park shelter?"
- "What summer programs are available for kids?"
- "Is the pool at [location] open?"

---

### 5. COMMUNICATIONS (cle-communications-005)
**Route when keywords include:**
- Press release, media, press inquiry
- Social media, Facebook, Twitter, Instagram
- Public announcement, city announcement
- Crisis communication, emergency communication
- Newsletter, internal communications
- Mayor's statement, official statement
- Brand, branding, logo usage
- Event promotion, marketing

**Example queries:**
- "I need a press release drafted"
- "How do I get something on the city's social media?"
- "What's the protocol for crisis communications?"

---

### 6. PUBLIC HEALTH (cle-public-health-006)
**Route when keywords include:**
- Health department, public health
- Inspection, restaurant inspection, food safety
- Vaccination, immunization, clinic
- Lead, lead safe, lead abatement
- Disease, outbreak, epidemiology
- WIC, maternal health, infant health
- Environmental health, air quality
- Health permit, health license

**Example queries:**
- "How do I schedule a food service inspection?"
- "What are the lead testing requirements?"
- "Where can I get a vaccination?"

---

### 7. BUILDING & HOUSING (cle-building-housing-007)
**Route when keywords include:**
- Building permit, permit application
- Code enforcement, housing code, building code
- Inspection (building), property inspection
- Violation, citation, compliance
- Rental registration, landlord
- Vacant property, demolition
- Certificate of occupancy
- Zoning (building aspect), setback

**Example queries:**
- "How do I apply for a building permit?"
- "I need to report a code violation"
- "What inspections are required for my project?"

---

### 8. PUBLIC SAFETY (cle-public-safety-008)
**Route when keywords include:**
- Police, fire, EMS (non-emergency)
- Report, incident report, accident report
- Policy manual, general orders
- Training, academy, certification
- Consent decree, DOJ
- Background check, police records
- Fire prevention, fire inspection
- Community policing, neighborhood safety

**Example queries:**
- "I need help with an incident report"
- "What's the policy on [procedure]?"
- "Where can I find fire inspection requirements?"

---

## PRIORITY RULES

When multiple departments could apply, use this priority:

1. **Safety First**: If query involves immediate safety → Public Safety (or 911 redirect)
2. **Regulatory/Compliance**: Specific regulatory questions → Most specific department
3. **Cross-Department**: When unclear, route to primary department per CROSS_DEPARTMENT_WORKFLOWS.md
4. **Default**: If genuinely unclear after clarification → Escalate to human

---

## EMERGENCY KEYWORDS - IMMEDIATE 911 REDIRECT

If ANY of these keywords appear, immediately respond with 911 redirect:
- Fire (active)
- Crime in progress
- Medical emergency
- Active shooter
- Bomb threat
- Immediate danger
- Help me (with distress indicators)

**Response:** "This service is not for emergencies. Please dial 9-1-1 immediately."

---

## EXCLUDED TOPICS - DO NOT ROUTE

These topics require human intervention or are outside scope:
- Personnel complaints → HR/Human Resources
- Legal advice → Law Department (no GPT routing)
- Media interview requests → Direct to Communications Director
- Elected official schedules → Direct to respective office
- Vendor/contract disputes → Procurement/Law
