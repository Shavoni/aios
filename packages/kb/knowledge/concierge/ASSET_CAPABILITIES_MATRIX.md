# ASSET CAPABILITIES MATRIX
## Cleveland HAAIS - GPT Capabilities Quick Reference

**Document Version:** 1.0.0
**Last Updated:** 2026-01-25
**Classification:** Internal Use Only

---

## PURPOSE
This matrix provides a quick reference for what each HAAIS GPT can and cannot do, helping the Concierge make accurate routing decisions.

---

## CAPABILITIES OVERVIEW

| Agent ID | Can INFORM | Can DRAFT | Can EXECUTE | Escalation Path |
|----------|-----------|-----------|-------------|-----------------|
| cle-urban-ai-001 | ✓ | ✓ | Limited | Dr. Elizabeth Crowe |
| cle-city-council-002 | ✓ | ✓ | ✗ | Council Clerk |
| cle-public-utilities-003 | ✓ | ✓ | ✗ | Director of Utilities |
| cle-parks-rec-004 | ✓ | ✓ | Limited | Director of Parks |
| cle-communications-005 | ✓ | ✓ | ✗ | Communications Director |
| cle-public-health-006 | ✓ | Limited | ✗ | Health Commissioner |
| cle-building-housing-007 | ✓ | ✓ | Limited | Director of B&H |
| cle-public-safety-008 | ✓ | Limited | ✗ | Director of Public Safety |

---

## DETAILED CAPABILITIES BY GPT

### Urban AI Director (cle-urban-ai-001)

**CAN DO:**
- Explain HAAIS framework and governance
- Describe AI initiatives and pilots
- Guide data governance questions
- Draft policy recommendations
- Provide What Works Cities certification info
- Coordinate cross-department AI matters

**CANNOT DO:**
- Approve AI projects (requires human)
- Access specific department systems
- Make budget decisions
- Commit resources

**BEST FOR:**
- AI strategy questions
- Data governance inquiries
- Innovation initiative info
- HAAIS framework guidance

---

### City Council (cle-city-council-002)

**CAN DO:**
- Explain legislative process
- Provide meeting schedules and agendas
- Describe ward boundaries
- Explain ordinance status
- Guide constituent services
- Draft correspondence (for staff review)

**CANNOT DO:**
- State council member positions
- Predict vote outcomes
- Draft legislation
- Make appointments

**BEST FOR:**
- Legislative process questions
- Meeting information
- Constituent services navigation
- Municipal code inquiries

---

### Public Utilities (cle-public-utilities-003)

**CAN DO:**
- Explain billing and rates
- Describe service options (CPP, Water, WPC)
- Guide service applications
- Provide outage information
- Explain EPA compliance requirements
- Draft service requests (for processing)

**CANNOT DO:**
- Modify billing accounts
- Restore service
- Override disconnections
- Access customer account details
- Control infrastructure

**BEST FOR:**
- Billing questions
- Service inquiries
- Outage information
- Utility program info

---

### Parks & Recreation (cle-parks-rec-004)

**CAN DO:**
- List programs and schedules
- Describe park amenities
- Explain facility rental process
- Guide program registration
- Provide event calendars
- Answer accessibility questions

**CANNOT DO:**
- Process registrations
- Reserve facilities
- Modify schedules
- Issue permits

**BEST FOR:**
- Program information
- Park/facility details
- Recreation schedules
- Community events

---

### Communications (cle-communications-005)

**CAN DO:**
- Explain communications protocols
- Guide press release process
- Describe social media policies
- Provide brand guidelines
- Draft content (for approval)
- Explain crisis communication procedures

**CANNOT DO:**
- Publish content
- Speak for the city officially
- Approve messaging
- Access media contacts
- Make media commitments

**BEST FOR:**
- Communications procedures
- Brand/style guidance
- Internal communications help
- Event promotion guidance

---

### Public Health (cle-public-health-006)

**CAN DO:**
- Explain inspection processes
- Describe health programs
- Provide clinic locations/schedules
- Guide permit applications
- Answer general health questions
- Describe disease prevention programs

**CANNOT DO:**
- Provide medical advice
- Access patient records
- Discuss specific inspections
- Share investigation details
- Disclose health violations

**BEST FOR:**
- Health program info
- Inspection process guidance
- Clinic/service locations
- General health resources

---

### Building & Housing (cle-building-housing-007)

**CAN DO:**
- Explain permit requirements
- Describe inspection process
- Guide code compliance
- Provide zoning information
- Draft permit applications (for review)
- Explain housing programs

**CANNOT DO:**
- Issue permits
- Schedule inspections
- Clear violations
- Make zoning determinations
- Access case details

**BEST FOR:**
- Permit questions
- Code requirements
- Inspection guidance
- Housing programs

---

### Public Safety (cle-public-safety-008)

**CAN DO:**
- Explain police/fire policies
- Describe community programs
- Guide report processes
- Provide general safety information
- Explain consent decree requirements
- Answer training/career questions

**CANNOT DO:**
- Discuss active investigations
- Provide tactical information
- Access case records
- Dispatch services
- Confirm officer/equipment locations

**BEST FOR:**
- Policy information
- Community programs
- Career/training info
- Non-emergency guidance

---

## CAPABILITY LIMITATIONS MATRIX

| Limitation Type | Affected GPTs | Alternative |
|----------------|---------------|-------------|
| No medical advice | All, esp. Public Health | Refer to healthcare provider |
| No legal advice | All | Escalate to Law Department |
| No account access | All | Escalate to department staff |
| No transaction processing | All | Provide forms/contact info |
| No personnel matters | All | Escalate to HR |
| No political statements | All | Decline to comment |
| No emergency response | All | Direct to 911 |

---

## CROSS-DEPARTMENT CAPABILITIES

### Who Leads Multi-Department Issues?

| Scenario | Lead GPT | Why |
|----------|----------|-----|
| Building + Health | Building & Housing | Permit is primary |
| Safety + Any other | Public Safety | Safety takes precedence |
| AI + Any department | Urban AI | AI governance coordination |
| Communications + Service | Service dept | Subject matter expertise |
| Council + Department | City Council | Legislative authority |

---

## SYSTEM AVAILABILITY

### Standard Availability
All GPTs: 24/7 for INFORM mode

### Limited Availability (Business Hours Only)
- DRAFT mode requiring approval
- EXECUTE mode actions
- Complex multi-department coordination

### Human Backup
- M-F 8:30 AM - 4:30 PM EST
- Extended for emergencies
- Weekends for critical services only

---

## ROUTING CONFIDENCE GUIDE

### High Confidence - Route Immediately
- Query matches single GPT's core competency
- Clear keywords from ROUTING_RULES_PRIMARY.md
- User explicitly names department

### Medium Confidence - Route with Note
- Query matches GPT but may need coordination
- Cross-department topic with clear primary
- Standard multi-step workflow

### Low Confidence - Clarify First
- Query matches 3+ GPTs equally
- Ambiguous terminology
- Unclear user intent

### No Confidence - Escalate
- No clear GPT match
- Legal/HR/sensitive matter
- User frustration detected

---

## VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-25 | Initial release |

