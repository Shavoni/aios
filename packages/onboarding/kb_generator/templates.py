"""Regulatory and domain templates for knowledge base generation.

Pre-built content templates for common municipal domains with:
- Federal/state regulatory frameworks
- Standard operational procedures
- Domain-specific guardrails
"""

from __future__ import annotations

from typing import Any

# =============================================================================
# REGULATORY TEMPLATES - Federal & State Frameworks
# =============================================================================

REGULATORY_TEMPLATES: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # HIPAA - Health Insurance Portability and Accountability Act
    # -------------------------------------------------------------------------
    "hipaa": {
        "title": "HIPAA Compliance and Health Data Privacy",
        "domain": "Public Health",
        "source": "U.S. Department of Health and Human Services",
        "tier": "Tier 1",
        "content": """### Overview

The Health Insurance Portability and Accountability Act (HIPAA) establishes national standards for protecting sensitive patient health information. All public health operations must comply with HIPAA regulations.

### Protected Health Information (PHI)

PHI includes any individually identifiable health information:
- Names, addresses, dates (birth, death, admission, discharge)
- Phone numbers, fax numbers, email addresses
- Social Security numbers, medical record numbers
- Health plan beneficiary numbers
- Account numbers, certificate/license numbers
- Vehicle identifiers, device identifiers
- Web URLs, IP addresses
- Biometric identifiers, photographs
- Any unique identifying number or code

### The Privacy Rule

**Permitted Uses and Disclosures:**
1. To the individual
2. Treatment, Payment, Healthcare Operations (TPO)
3. With valid authorization
4. Incidental disclosures (if reasonable safeguards in place)
5. Public interest and benefit activities
6. Limited data sets for research

**Minimum Necessary Standard:**
Only the minimum amount of PHI necessary should be used or disclosed for any purpose.

### The Security Rule

**Administrative Safeguards:**
- Security management process
- Assigned security responsibility
- Workforce security
- Information access management
- Security awareness training
- Security incident procedures
- Contingency planning
- Evaluation

**Physical Safeguards:**
- Facility access controls
- Workstation use policies
- Workstation security
- Device and media controls

**Technical Safeguards:**
- Access controls
- Audit controls
- Integrity controls
- Transmission security

### Breach Notification Requirements

A breach must be reported:
- To affected individuals without unreasonable delay (within 60 days)
- To HHS (annually if <500 individuals; within 60 days if ≥500)
- To media if breach affects ≥500 residents of a state

### AI-Specific Guidance

**For AI Systems Handling Health Data:**
1. Never process raw PHI - only de-identified or aggregated data
2. Implement access logging for all data queries
3. Apply data minimization principles
4. Ensure encryption at rest and in transit
5. Maintain audit trails for compliance verification
6. Immediately escalate any potential breach""",
        "escalation_contacts": [
            {"role": "HIPAA Privacy Officer", "name": "[Department HIPAA Officer]"},
            {"role": "HHS Office for Civil Rights", "name": "Federal oversight"},
        ],
        "related_templates": ["public_health_governance", "data_privacy"],
    },

    # -------------------------------------------------------------------------
    # EPA - Environmental Protection Agency Regulations
    # -------------------------------------------------------------------------
    "epa_clean_water": {
        "title": "Clean Water Act and NPDES Compliance",
        "domain": "Public Utilities",
        "source": "U.S. Environmental Protection Agency",
        "tier": "Tier 1",
        "content": """### Overview

The Clean Water Act (CWA) establishes the basic structure for regulating discharges of pollutants into waters of the United States. The National Pollutant Discharge Elimination System (NPDES) permit program controls these discharges.

### NPDES Permit Requirements

**Point Source Discharges:**
All point source discharges to waters of the United States require an NPDES permit. This includes:
- Municipal wastewater treatment plants
- Industrial facilities
- Concentrated animal feeding operations
- Municipal separate storm sewer systems (MS4s)

**Permit Components:**
1. Effluent limitations (technology-based and water quality-based)
2. Monitoring and reporting requirements
3. Standard conditions
4. Special conditions (as applicable)

### Municipal Wastewater Requirements

**Secondary Treatment Standards:**
- BOD5: 30 mg/L (monthly average), 45 mg/L (weekly average)
- TSS: 30 mg/L (monthly average), 45 mg/L (weekly average)
- pH: 6.0 - 9.0
- Removal rates: 85% minimum for BOD5 and TSS

**Combined Sewer Overflow (CSO) Requirements:**
- Nine Minimum Controls
- Long-Term Control Plan (LTCP)
- Public notification requirements

### Stormwater Management

**MS4 Requirements:**
1. Public education and outreach
2. Public participation/involvement
3. Illicit discharge detection and elimination
4. Construction site runoff control
5. Post-construction stormwater management
6. Pollution prevention/good housekeeping

### Reporting Requirements

**Discharge Monitoring Reports (DMRs):**
- Submit monthly/quarterly as specified in permit
- Report all exceedances within 24 hours
- Maintain records for minimum 3 years

### AI-Specific Guidance

**For AI Systems in Water Management:**
1. Track permit compliance status in real-time
2. Flag potential violations before they occur
3. Generate DMR data summaries for human review
4. Never authorize discharge parameter changes
5. Escalate all potential violations immediately""",
        "escalation_contacts": [
            {"role": "Utility Director", "name": "[Utility Director Name]"},
            {"role": "Ohio EPA District Office", "name": "State regulatory authority"},
            {"role": "US EPA Region 5", "name": "Federal oversight"},
        ],
        "related_templates": ["safe_drinking_water", "ohio_epa"],
    },

    # -------------------------------------------------------------------------
    # Safe Drinking Water Act
    # -------------------------------------------------------------------------
    "safe_drinking_water": {
        "title": "Safe Drinking Water Act Compliance",
        "domain": "Public Utilities",
        "source": "U.S. Environmental Protection Agency",
        "tier": "Tier 1",
        "content": """### Overview

The Safe Drinking Water Act (SDWA) is the principal federal law ensuring the quality of drinking water in the United States. It authorizes EPA to set national health-based standards for drinking water.

### National Primary Drinking Water Regulations (NPDWRs)

**Microbiological Contaminants:**
- Total Coliform Rule (revised)
- Surface Water Treatment Rules
- Ground Water Rule
- Lead and Copper Rule (revised 2021)

**Chemical Contaminants:**
- Inorganic chemicals (IOCs)
- Volatile organic chemicals (VOCs)
- Synthetic organic chemicals (SOCs)
- Radionuclides
- Disinfectants and disinfection byproducts

### Lead and Copper Rule (LCR) Requirements

**Action Levels:**
- Lead: 15 μg/L (90th percentile)
- Copper: 1.3 mg/L (90th percentile)

**If Action Level Exceeded:**
1. Public education within 60 days
2. Water quality parameter monitoring
3. Source water monitoring/treatment
4. Lead service line replacement program
5. Corrosion control treatment optimization

**Lead Service Line Inventory:**
- Complete inventory required
- Annual reporting to state
- Public access to inventory
- Replacement program if AL exceeded

### Consumer Confidence Reports

Annual reports must include:
- Source water information
- Detected contaminants
- Compliance status
- Educational information
- Vulnerability assessment results

### AI-Specific Guidance

**For AI Systems in Water Quality:**
1. Monitor all regulated contaminant levels
2. Generate alerts before action levels are approached
3. Track lead service line inventory and replacements
4. Draft consumer notifications for human review
5. Never certify compliance - human review required
6. Escalate any detected exceedances immediately""",
        "escalation_contacts": [
            {"role": "Water Quality Manager", "name": "[Water Quality Manager]"},
            {"role": "Ohio EPA Drinking Water", "name": "State primacy agency"},
        ],
        "related_templates": ["epa_clean_water", "lead_copper_rule"],
    },

    # -------------------------------------------------------------------------
    # Fair Housing Act
    # -------------------------------------------------------------------------
    "fair_housing": {
        "title": "Fair Housing Act Compliance",
        "domain": "Building & Housing",
        "source": "U.S. Department of Housing and Urban Development",
        "tier": "Tier 1",
        "content": """### Overview

The Fair Housing Act prohibits discrimination in housing based on race, color, national origin, religion, sex (including gender identity and sexual orientation), familial status, and disability.

### Protected Classes

**Federal Protected Classes:**
1. Race
2. Color
3. National Origin
4. Religion
5. Sex (including gender identity, sexual orientation)
6. Familial Status (families with children under 18)
7. Disability (physical or mental)

**Ohio Additional Protections:**
- Military status
- Ancestry

### Prohibited Practices

**In Sale or Rental:**
- Refusing to sell or rent
- Discriminatory terms or conditions
- Discriminatory advertising
- Falsely denying availability
- Blockbusting
- Discriminatory lending practices

**Disability-Specific:**
- Refusing reasonable modifications
- Refusing reasonable accommodations
- Failing to design accessible units (new construction)

### Affirmatively Furthering Fair Housing (AFFH)

HUD-funded programs must:
1. Analyze fair housing data
2. Assess fair housing issues
3. Set goals to overcome barriers
4. Take meaningful actions

### AI-Specific Guidance

**For AI Systems in Housing:**
1. Never use protected class information in decisions
2. Ensure algorithms are tested for disparate impact
3. Provide equal information to all inquiries
4. Document all interactions for fair housing compliance
5. Escalate any discrimination complaints immediately
6. Never draft communications that could be discriminatory""",
        "escalation_contacts": [
            {"role": "Fair Housing Officer", "name": "[City Fair Housing Officer]"},
            {"role": "HUD Regional Office", "name": "Federal oversight"},
            {"role": "Ohio Civil Rights Commission", "name": "State enforcement"},
        ],
        "related_templates": ["housing_code", "ada_compliance"],
    },

    # -------------------------------------------------------------------------
    # Ohio Building Code
    # -------------------------------------------------------------------------
    "ohio_building_code": {
        "title": "Ohio Building Code Summary",
        "domain": "Building & Housing",
        "source": "Ohio Board of Building Standards",
        "tier": "Tier 2",
        "content": """### Overview

The Ohio Building Code (OBC) is based on the International Building Code (IBC) with Ohio-specific amendments. It governs the construction, alteration, and maintenance of buildings and structures.

### Code Applicability

**Covered Buildings:**
- Commercial buildings
- Industrial buildings
- Residential buildings (3+ units)
- Mixed-use buildings
- Assembly occupancies
- Educational facilities
- Healthcare facilities

**Exempt (Residential Code applies):**
- One and two-family dwellings
- Townhouses (3 stories or less)

### Key Requirements

**Structural:**
- Design loads (dead, live, snow, wind, seismic)
- Foundation requirements
- Structural materials (concrete, masonry, steel, wood)
- Fire-resistance ratings

**Fire Protection:**
- Occupancy classifications
- Construction types (I-V)
- Fire barriers and partitions
- Means of egress requirements
- Fire suppression systems
- Fire alarm systems

**Accessibility:**
- ICC A117.1 standards
- Accessible routes
- Accessible parking
- Accessible facilities

**Energy:**
- Ohio Energy Code (based on IECC)
- Insulation requirements
- HVAC efficiency
- Lighting efficiency

### Permit Requirements

**Permits Required For:**
- New construction
- Additions
- Alterations
- Change of occupancy
- Demolition

**Plan Review:**
- Certified plans examiner review
- Fire department review (if applicable)
- Health department review (if applicable)

### AI-Specific Guidance

**For AI Systems in Building:**
1. Provide code reference information only
2. Never approve or deny permits
3. Direct complex interpretations to certified officials
4. Track permit status but don't modify records
5. Draft inspection checklists for human use
6. Escalate safety hazards immediately""",
        "escalation_contacts": [
            {"role": "Chief Building Official", "name": "[Chief Building Official]"},
            {"role": "Ohio BBS", "name": "State building authority"},
        ],
        "related_templates": ["fair_housing", "fire_safety", "ada_compliance"],
    },

    # -------------------------------------------------------------------------
    # CDC Guidelines Framework
    # -------------------------------------------------------------------------
    "cdc_guidelines": {
        "title": "CDC Guidelines Quick Reference",
        "domain": "Public Health",
        "source": "U.S. Centers for Disease Control and Prevention",
        "tier": "Tier 1",
        "content": """### Overview

This document provides a framework for referencing CDC guidelines in public health operations. CDC guidelines represent evidence-based recommendations for disease prevention and health promotion.

### Immunization Guidelines

**Advisory Committee on Immunization Practices (ACIP):**
- Childhood immunization schedule
- Adult immunization schedule
- Catch-up immunization guidance
- Special populations guidance

**Key Vaccine-Preventable Diseases:**
- Influenza (annual recommendations)
- COVID-19 (updated as needed)
- Measles, Mumps, Rubella (MMR)
- Hepatitis A and B
- HPV
- Pneumococcal disease
- Meningococcal disease

### Disease Surveillance

**Nationally Notifiable Conditions:**
- Immediate notification (within 24 hours)
- Weekly notification
- Annual notification

**Outbreak Investigation Steps:**
1. Verify diagnosis
2. Define and identify cases
3. Describe data (time, place, person)
4. Develop hypotheses
5. Evaluate hypotheses
6. Implement control measures
7. Communicate findings

### Food Safety

**Foodborne Illness Investigation:**
- PulseNet (molecular surveillance)
- SEDRIC (outbreak reporting)
- Investigation coordination with FDA/USDA

### Environmental Health

**Lead Poisoning Prevention:**
- Blood lead reference value: 3.5 μg/dL (children)
- Primary prevention strategies
- Environmental investigation triggers
- Case management protocols

### AI-Specific Guidance

**For AI Systems in Public Health:**
1. Reference CDC guidance but note update dates
2. Never provide clinical recommendations
3. Direct clinical questions to healthcare providers
4. Track guideline updates and flag changes
5. Draft public health communications for review
6. Escalate outbreak indicators immediately""",
        "escalation_contacts": [
            {"role": "City Epidemiologist", "name": "[City Epidemiologist]"},
            {"role": "Ohio Department of Health", "name": "State health authority"},
            {"role": "CDC Emergency Operations", "name": "Federal response"},
        ],
        "related_templates": ["hipaa", "disease_surveillance", "outbreak_response"],
    },
}

# =============================================================================
# DOMAIN TEMPLATES - Department-Specific Content Structures
# =============================================================================

DOMAIN_TEMPLATES: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Public Health Domain
    # -------------------------------------------------------------------------
    "public_health": {
        "domain": "Public Health",
        "file_structure": [
            {"num": 1, "id": "disease_surveillance", "title": "Disease Surveillance and Outbreak Response", "type": "procedure"},
            {"num": 2, "id": "immunization_programs", "title": "Immunization Programs and Vaccine Distribution", "type": "procedure"},
            {"num": 3, "id": "environmental_health", "title": "Environmental Health and Food Safety", "type": "procedure"},
            {"num": 4, "id": "vital_statistics", "title": "Vital Statistics and Health Data", "type": "data_reference"},
            {"num": 5, "id": "health_equity", "title": "Health Equity and Social Determinants", "type": "policy"},
            {"num": 6, "id": "maternal_child_health", "title": "Maternal and Child Health Programs", "type": "procedure"},
            {"num": 7, "id": "chronic_disease", "title": "Chronic Disease Prevention", "type": "procedure"},
            {"num": 8, "id": "mental_health", "title": "Mental Health and Substance Abuse Services", "type": "procedure"},
            {"num": 9, "id": "hipaa_compliance", "title": "HIPAA Compliance and Health Data Privacy", "type": "regulatory"},
            {"num": 10, "id": "state_health_code", "title": "Ohio Revised Code - Public Health", "type": "regulatory"},
            {"num": 11, "id": "emergency_preparedness", "title": "Emergency Preparedness and Response", "type": "procedure"},
            {"num": 12, "id": "accreditation", "title": "PHAB Accreditation Standards", "type": "policy"},
            {"num": 13, "id": "health_disparities", "title": "Local Health Disparities Data", "type": "data_reference"},
            {"num": 14, "id": "community_health_assessment", "title": "Community Health Assessment Data", "type": "data_reference"},
            {"num": 15, "id": "partnerships", "title": "Local Health Partnerships", "type": "department_structure"},
            {"num": 16, "id": "department_structure", "title": "Department Structure and Contacts", "type": "department_structure"},
            {"num": 17, "id": "communications", "title": "Public Health Communications", "type": "procedure"},
            {"num": 18, "id": "grant_management", "title": "Grant Management and Funding", "type": "procedure"},
        ],
        "regulatory_templates": ["hipaa", "cdc_guidelines"],
        "prohibited_actions": [
            "Provide medical advice or clinical diagnoses",
            "Issue public health advisories or quarantine orders",
            "Access or handle unprotected PHI",
            "Communicate directly with the public or media",
            "Make decisions on medical resource allocation",
            "Mandate public health interventions",
        ],
        "special_protocols": {
            "data_privacy": "HIPAA compliance required for all health data handling",
            "health_equity": "All analyses must consider impact on vulnerable populations",
        },
    },

    # -------------------------------------------------------------------------
    # Building & Housing Domain
    # -------------------------------------------------------------------------
    "building_housing": {
        "domain": "Building & Housing",
        "file_structure": [
            {"num": 1, "id": "permits_inspections", "title": "Building Permits and Inspections", "type": "procedure"},
            {"num": 2, "id": "housing_code", "title": "Housing Code Enforcement", "type": "procedure"},
            {"num": 3, "id": "lead_safe", "title": "Lead-Safe Housing Requirements", "type": "regulatory"},
            {"num": 4, "id": "vacant_property", "title": "Vacant Property Management", "type": "procedure"},
            {"num": 5, "id": "fair_housing", "title": "Fair Housing Compliance", "type": "regulatory"},
            {"num": 6, "id": "zoning", "title": "Zoning and Land Use", "type": "regulatory"},
            {"num": 7, "id": "historic_preservation", "title": "Historic Preservation", "type": "policy"},
            {"num": 8, "id": "demolition", "title": "Demolition Protocols", "type": "procedure"},
            {"num": 9, "id": "rental_registration", "title": "Rental Registration Program", "type": "procedure"},
            {"num": 10, "id": "housing_data", "title": "Local Housing Data", "type": "data_reference"},
            {"num": 11, "id": "affordable_housing", "title": "Affordable Housing Programs", "type": "policy"},
            {"num": 12, "id": "contractor_licensing", "title": "Contractor Licensing", "type": "procedure"},
            {"num": 13, "id": "residential_rehab", "title": "Residential Rehabilitation Programs", "type": "procedure"},
            {"num": 14, "id": "commercial_development", "title": "Commercial Development", "type": "procedure"},
            {"num": 15, "id": "housing_court", "title": "Housing Court Procedures", "type": "procedure"},
            {"num": 16, "id": "ada_compliance", "title": "Accessibility and ADA Compliance", "type": "regulatory"},
            {"num": 17, "id": "fire_safety", "title": "Fire Safety Codes", "type": "regulatory"},
            {"num": 18, "id": "department_structure", "title": "Department Structure and Contacts", "type": "department_structure"},
        ],
        "regulatory_templates": ["ohio_building_code", "fair_housing"],
        "prohibited_actions": [
            "Issue building permits or certificates of occupancy",
            "Condemn properties or issue stop-work orders",
            "Assess fines or fees",
            "Communicate directly with property owners or contractors",
            "Provide engineering, architectural, or legal advice",
            "Alter official inspection records",
        ],
        "special_protocols": {
            "life_safety": "Immediate escalation for imminent danger or collapse",
            "property_rights": "All enforcement actions must be based strictly on code",
        },
    },

    # -------------------------------------------------------------------------
    # Public Utilities Domain
    # -------------------------------------------------------------------------
    "public_utilities": {
        "domain": "Public Utilities",
        "file_structure": [
            {"num": 1, "id": "water_treatment", "title": "Water Treatment and Distribution", "type": "procedure"},
            {"num": 2, "id": "wastewater", "title": "Wastewater and Sewer Infrastructure", "type": "procedure"},
            {"num": 3, "id": "stormwater", "title": "Stormwater Management", "type": "procedure"},
            {"num": 4, "id": "public_power", "title": "Public Power Operations", "type": "procedure"},
            {"num": 5, "id": "asset_management", "title": "Asset Management and Capital Planning", "type": "procedure"},
            {"num": 6, "id": "emergency_response", "title": "Emergency Response Protocols", "type": "procedure"},
            {"num": 7, "id": "maintenance", "title": "Maintenance Best Practices", "type": "procedure"},
            {"num": 8, "id": "billing", "title": "Utility Billing and Customer Service", "type": "procedure"},
            {"num": 9, "id": "clean_water_act", "title": "Clean Water Act and NPDES", "type": "regulatory"},
            {"num": 10, "id": "ohio_epa", "title": "Ohio EPA Regulations", "type": "regulatory"},
            {"num": 11, "id": "lead_copper", "title": "Lead and Copper Rule", "type": "regulatory"},
            {"num": 12, "id": "rate_structures", "title": "Rate Structures and Affordability", "type": "policy"},
            {"num": 13, "id": "bond_financing", "title": "Bond Financing and Capital Funding", "type": "procedure"},
            {"num": 14, "id": "regional_partnerships", "title": "Regional Partnerships", "type": "department_structure"},
            {"num": 15, "id": "infrastructure_planning", "title": "Long-Term Infrastructure Planning", "type": "policy"},
            {"num": 16, "id": "affordability", "title": "Water Affordability and Shutoff Prevention", "type": "policy"},
            {"num": 17, "id": "community_engagement", "title": "Community Engagement on Infrastructure", "type": "procedure"},
            {"num": 18, "id": "environmental_justice", "title": "Environmental Justice and Utility Access", "type": "policy"},
            {"num": 19, "id": "workforce", "title": "Workforce Development and Local Hiring", "type": "policy"},
        ],
        "regulatory_templates": ["epa_clean_water", "safe_drinking_water"],
        "prohibited_actions": [
            "Authorize changes to water treatment processes",
            "Modify utility rates or billing",
            "Issue service disconnection orders",
            "Approve capital expenditures",
            "Certify regulatory compliance reports",
            "Communicate with regulatory agencies on behalf of the utility",
        ],
        "special_protocols": {
            "water_quality": "Immediate escalation for any water quality exceedance",
            "service_continuity": "24/7 monitoring requirements for critical infrastructure",
        },
    },

    # -------------------------------------------------------------------------
    # Public Safety Domain
    # -------------------------------------------------------------------------
    "public_safety": {
        "domain": "Public Safety",
        "file_structure": [
            {"num": 1, "id": "crime_data", "title": "Crime Statistics and Analysis", "type": "data_reference"},
            {"num": 2, "id": "community_policing", "title": "Community Policing Programs", "type": "policy"},
            {"num": 3, "id": "emergency_management", "title": "Emergency Management", "type": "procedure"},
            {"num": 4, "id": "use_of_force", "title": "Use of Force Policies", "type": "policy"},
            {"num": 5, "id": "consent_decree", "title": "Consent Decree Compliance", "type": "regulatory"},
            {"num": 6, "id": "training", "title": "Training Requirements", "type": "procedure"},
            {"num": 7, "id": "evidence_management", "title": "Evidence Management", "type": "procedure"},
            {"num": 8, "id": "victim_services", "title": "Victim Services", "type": "procedure"},
            {"num": 9, "id": "fire_prevention", "title": "Fire Prevention Programs", "type": "procedure"},
            {"num": 10, "id": "ems_protocols", "title": "EMS Protocols", "type": "procedure"},
            {"num": 11, "id": "internal_affairs", "title": "Internal Affairs Procedures", "type": "procedure"},
            {"num": 12, "id": "community_commission", "title": "Community Police Commission", "type": "department_structure"},
            {"num": 13, "id": "grants_funding", "title": "Public Safety Grants", "type": "procedure"},
            {"num": 14, "id": "crisis_intervention", "title": "Crisis Intervention", "type": "procedure"},
            {"num": 15, "id": "technology", "title": "Public Safety Technology", "type": "procedure"},
            {"num": 16, "id": "recruitment", "title": "Recruitment and Retention", "type": "policy"},
            {"num": 17, "id": "juvenile_justice", "title": "Juvenile Justice Programs", "type": "procedure"},
            {"num": 18, "id": "reentry", "title": "Reentry Programs", "type": "procedure"},
            {"num": 19, "id": "department_structure", "title": "Department Structure and Contacts", "type": "department_structure"},
        ],
        "regulatory_templates": [],
        "prohibited_actions": [
            "Access criminal justice records or ongoing investigations",
            "Provide information about specific cases or individuals",
            "Make statements about officer conduct or discipline",
            "Advise on legal matters or rights",
            "Communicate with media about public safety incidents",
            "Access or process personally identifiable information",
        ],
        "special_protocols": {
            "victim_privacy": "Strict protection of victim information",
            "ongoing_investigations": "No discussion of active investigations",
        },
    },

    # -------------------------------------------------------------------------
    # Finance Domain
    # -------------------------------------------------------------------------
    "finance": {
        "domain": "Finance",
        "file_structure": [
            {"num": 1, "id": "budget_process", "title": "Budget Development Process", "type": "procedure"},
            {"num": 2, "id": "procurement", "title": "Procurement Policies", "type": "policy"},
            {"num": 3, "id": "accounts_payable", "title": "Accounts Payable Procedures", "type": "procedure"},
            {"num": 4, "id": "accounts_receivable", "title": "Accounts Receivable and Collections", "type": "procedure"},
            {"num": 5, "id": "grants_management", "title": "Grants Management", "type": "procedure"},
            {"num": 6, "id": "payroll", "title": "Payroll Administration", "type": "procedure"},
            {"num": 7, "id": "financial_reporting", "title": "Financial Reporting Requirements", "type": "regulatory"},
            {"num": 8, "id": "audit_requirements", "title": "Audit Requirements", "type": "regulatory"},
            {"num": 9, "id": "debt_management", "title": "Debt Management", "type": "policy"},
            {"num": 10, "id": "investment_policy", "title": "Investment Policy", "type": "policy"},
            {"num": 11, "id": "tax_collection", "title": "Tax Collection", "type": "procedure"},
            {"num": 12, "id": "asset_management", "title": "Fixed Asset Management", "type": "procedure"},
            {"num": 13, "id": "internal_controls", "title": "Internal Controls", "type": "policy"},
            {"num": 14, "id": "contracts", "title": "Contract Management", "type": "procedure"},
            {"num": 15, "id": "risk_management", "title": "Risk Management", "type": "policy"},
            {"num": 16, "id": "department_structure", "title": "Department Structure and Contacts", "type": "department_structure"},
        ],
        "regulatory_templates": [],
        "prohibited_actions": [
            "Approve expenditures or authorize payments",
            "Modify budget allocations",
            "Execute contracts or agreements",
            "Access individual taxpayer information",
            "Change procurement vendor selections",
            "Certify financial reports",
        ],
        "special_protocols": {
            "fiscal_responsibility": "All financial recommendations require CFO review",
            "procurement_integrity": "Strict separation from vendor selection",
        },
    },

    # -------------------------------------------------------------------------
    # Human Resources Domain
    # -------------------------------------------------------------------------
    "hr": {
        "domain": "Human Resources",
        "file_structure": [
            {"num": 1, "id": "recruitment", "title": "Recruitment and Hiring", "type": "procedure"},
            {"num": 2, "id": "civil_service", "title": "Civil Service Rules", "type": "regulatory"},
            {"num": 3, "id": "compensation", "title": "Compensation and Classification", "type": "policy"},
            {"num": 4, "id": "benefits", "title": "Benefits Administration", "type": "procedure"},
            {"num": 5, "id": "leave_policies", "title": "Leave Policies", "type": "policy"},
            {"num": 6, "id": "performance", "title": "Performance Management", "type": "procedure"},
            {"num": 7, "id": "discipline", "title": "Discipline and Grievance", "type": "procedure"},
            {"num": 8, "id": "labor_relations", "title": "Labor Relations and Collective Bargaining", "type": "policy"},
            {"num": 9, "id": "training", "title": "Training and Development", "type": "procedure"},
            {"num": 10, "id": "workplace_safety", "title": "Workplace Safety", "type": "regulatory"},
            {"num": 11, "id": "eeo", "title": "Equal Employment Opportunity", "type": "regulatory"},
            {"num": 12, "id": "ada_accommodations", "title": "ADA Accommodations", "type": "regulatory"},
            {"num": 13, "id": "fmla", "title": "FMLA Administration", "type": "regulatory"},
            {"num": 14, "id": "retirement", "title": "Retirement Systems", "type": "procedure"},
            {"num": 15, "id": "records_management", "title": "Personnel Records Management", "type": "procedure"},
            {"num": 16, "id": "department_structure", "title": "Department Structure and Contacts", "type": "department_structure"},
        ],
        "regulatory_templates": [],
        "prohibited_actions": [
            "Make hiring or termination decisions",
            "Access individual personnel files",
            "Provide legal advice on employment matters",
            "Negotiate labor agreements",
            "Approve leave requests or accommodations",
            "Discuss specific employee situations",
        ],
        "special_protocols": {
            "confidentiality": "Strict protection of personnel information",
            "union_matters": "No involvement in collective bargaining",
        },
    },
}


def get_domain_templates(domain: str) -> dict[str, Any] | None:
    """Get template configuration for a domain.

    Args:
        domain: Domain name (e.g., "Public Health", "Building & Housing")

    Returns:
        Domain template configuration or None if not found
    """
    # Normalize domain name
    domain_key = domain.lower().replace(" ", "_").replace("&", "").replace("__", "_")

    # Try direct match
    if domain_key in DOMAIN_TEMPLATES:
        return DOMAIN_TEMPLATES[domain_key]

    # Try partial match
    for key, template in DOMAIN_TEMPLATES.items():
        if domain.lower() in template["domain"].lower():
            return template

    return None


def get_regulatory_template(template_id: str) -> dict[str, Any] | None:
    """Get a specific regulatory template.

    Args:
        template_id: Template identifier (e.g., "hipaa", "fair_housing")

    Returns:
        Regulatory template or None if not found
    """
    return REGULATORY_TEMPLATES.get(template_id)


def get_all_regulatory_templates_for_domain(domain: str) -> list[dict[str, Any]]:
    """Get all regulatory templates applicable to a domain.

    Args:
        domain: Domain name

    Returns:
        List of applicable regulatory templates
    """
    domain_config = get_domain_templates(domain)
    if not domain_config:
        return []

    templates = []
    for template_id in domain_config.get("regulatory_templates", []):
        template = get_regulatory_template(template_id)
        if template:
            templates.append(template)

    return templates
