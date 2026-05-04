# Human-in-the-Loop (HITL) Execution: Complete Analysis

**Date:** January 28, 2026  
**Purpose:** Answer all questions about AIOS HITL system - the key differentiator

---

## Executive Summary

AIOS implements a **sophisticated 4-tier HITL system** with:
- ✅ Configurable approval requirements based on risk/impact
- ✅ 4-level escalation chain (L1→L2→L3→L4)
- ✅ SLA monitoring with automatic escalation
- ✅ Multi-channel notifications (extensible)
- ✅ Batch operations for efficiency
- ⚠️ **Dual approval partially supported** (need enhancement for full two-person integrity)

---

## Question 1: Which Actions Require Human Approval?

### Answer: Defined in `HITLManager.determine_hitl_mode()`

**Location:** `packages/core/hitl/__init__.py` lines 139-166

### The 4 HITL Modes

```python
class HITLMode(str, Enum):
    """HITL operational modes."""
    
    INFORM = "INFORM"      # Auto-respond, inform user (no approval)
    DRAFT = "DRAFT"        # Queue for human review before sending
    EXECUTE = "EXECUTE"    # Requires manager approval before action
    ESCALATE = "ESCALATE"  # Route to human immediately, agent cannot respond
```

### Approval Decision Logic

**Code:** `packages/core/hitl/__init__.py:139-166`

```python
def determine_hitl_mode(
    self,
    intent_domain: str,
    intent_impact: str,
    risk_signals: list[str],
    user_role: str = "employee",
) -> HITLMode:
    """Determine the appropriate HITL mode based on context."""
    
    # 1. HIGH-RISK SIGNALS → Always ESCALATE
    high_risk_signals = {"PII", "PHI", "LEGAL_CONTRACT", "FINANCIAL_LARGE"}
    if any(s in high_risk_signals for s in risk_signals):
        return HITLMode.ESCALATE
    
    # 2. HIGH IMPACT → EXECUTE (manager approval)
    if intent_impact == "high":
        return HITLMode.EXECUTE
    
    # 3. MEDIUM IMPACT → DRAFT (review before sending)
    if intent_impact == "medium":
        return HITLMode.DRAFT
    
    # 4. EXTERNAL-FACING → DRAFT (review before sending)
    if intent_domain in {"Communications", "PublicRelations", "Legal"}:
        return HITLMode.DRAFT
    
    # 5. DEFAULT → INFORM (no approval needed)
    return HITLMode.INFORM
```

### What Requires Approval: The List

| Action Type | HITL Mode | Approval Required | Example |
|-------------|-----------|-------------------|---------|
| **PII/PHI handling** | ESCALATE | Yes (immediate) | "Show me John's SSN" |
| **Legal contracts** | ESCALATE | Yes (immediate) | "Sign this contract" |
| **Large financial** | ESCALATE | Yes (immediate) | "Transfer $50K" |
| **High-impact actions** | EXECUTE | Yes (manager) | "Delete production database" |
| **Medium-impact actions** | DRAFT | Yes (review) | "Update customer record" |
| **External communications** | DRAFT | Yes (review) | "Post to social media" |
| **Public relations** | DRAFT | Yes (review) | "Issue press release" |
| **Legal domain queries** | DRAFT | Yes (review) | "Interpret city ordinance" |
| **Low-impact internal** | INFORM | No | "What's the HR policy?" |
| **Read-only queries** | INFORM | No | "Show me my timesheet" |

### How to Customize Approval Requirements

**Method 1: Governance Policies**

Governance rules can override HITL mode:

```json
// In data/governance_policies.json
{
  "id": "finance-approval",
  "name": "Financial Actions Require Approval",
  "conditions": [
    {"field": "intent.domain", "operator": "eq", "value": "Finance"},
    {"field": "intent.task", "operator": "eq", "value": "transaction"}
  ],
  "action": {
    "hitl_mode": "EXECUTE",
    "approval_required": true,
    "escalation_reason": "Financial transaction requires approval"
  }
}
```

**Method 2: Agent-Specific Guardrails**

Agents can have custom guardrails:

```python
// In agent configuration
agent = AgentConfig(
    id="finance-agent",
    guardrails=[
        "All payments > $1000 require manager approval",
        "Budget changes require CFO approval",
    ]
)
```

**Method 3: Code Extension**

Extend `determine_hitl_mode()` with custom logic:

```python
# Custom HITL determination
def custom_hitl_mode(query, context):
    # Custom business logic
    if "payment" in query.lower() and extract_amount(query) > 1000:
        return HITLMode.EXECUTE
    
    if is_personnel_action(query):
        return HITLMode.ESCALATE
    
    # Fall back to default logic
    return manager.determine_hitl_mode(...)
```

---

## Question 2: Approval Step State Machine / Code Path

### The Approval State Machine

```
┌─────────────────────────────────────────────────────────────┐
│                   APPROVAL STATE MACHINE                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Query Received                                           │
│     ↓                                                         │
│  2. Governance Evaluation                                    │
│     - Classify intent (domain, impact)                       │
│     - Detect risk signals (PII, PHI, etc.)                   │
│     - Determine HITL mode                                    │
│     ↓                                                         │
│  3. Decision Point                                           │
│     ├─ INFORM → Auto-respond (no approval)                   │
│     ├─ DRAFT → Create approval, queue for review             │
│     ├─ EXECUTE → Create approval, require manager            │
│     └─ ESCALATE → Create approval, immediate escalation      │
│                                                               │
│  4. Approval Creation (if not INFORM)                        │
│     - Create ApprovalRequest                                 │
│     - Set expiration (24h DRAFT, 48h EXECUTE, 4h ESCALATE)   │
│     - Auto-assign to reviewer (workload balancing)           │
│     - Send notification                                      │
│     ↓                                                         │
│  5. Approval Status: PENDING                                 │
│     ├─ Reviewer approves → APPROVED → Execute action         │
│     ├─ Reviewer rejects → REJECTED → Notify user             │
│     ├─ SLA breach → Auto-escalate to next level              │
│     ├─ Expires → EXPIRED → Notify user                       │
│     └─ User cancels → CANCELLED → Remove from queue          │
│                                                               │
│  6. Post-Resolution                                          │
│     - Update reviewer workload                               │
│     - Send notifications                                     │
│     - Log to history                                         │
│     - Track metrics (SLA compliance, avg time, etc.)         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Code Path

#### Step 1: Agent Query Entry Point

**File:** `packages/api/agents.py:426-534`

```python
@router.post("/{agent_id}/query")
async def query_agent(agent_id: str, request: AgentQueryRequest):
    """Query an agent with HITL governance."""
    
    # Get agent
    agent = agent_manager.get_agent(agent_id)
    
    # STEP 2: GOVERNANCE EVALUATION
    governance_mgr = get_governance_manager()
    decision = governance_mgr.evaluate_for_agent(
        query=request.query,
        agent_id=agent_id,
        domain=agent.domain,
    )
    
    # STEP 3: DECISION POINT - ESCALATE MODE
    if decision.hitl_mode == HITLMode.ESCALATE:
        # Create approval request (code below)
        hitl_mgr = get_hitl_manager()
        approval = hitl_mgr.create_approval_request(
            hitl_mode=HITLMode.ESCALATE,
            user_id=request.user_id,
            agent_id=agent_id,
            original_query=request.query,
            proposed_response="[Escalated - Awaiting Human Response]",
            risk_signals=decision.risk_signals,
            escalation_reason=decision.escalation_reason,
        )
        
        # Return escalation response
        return AgentQueryResponse(
            response=f"Escalated to supervisor: {decision.escalation_reason}",
            hitl_mode="ESCALATE",
            approval_id=approval.id,
        )
    
    # Generate LLM response
    response_text = router.llm.generate(prompt=request.query, ...)
    
    # STEP 3: DECISION POINT - DRAFT MODE
    if decision.hitl_mode == HITLMode.DRAFT:
        # Create approval for review
        approval = hitl_mgr.create_approval_request(
            hitl_mode=HITLMode.DRAFT,
            user_id=request.user_id,
            agent_id=agent_id,
            original_query=request.query,
            proposed_response=response_text,
        )
        
        # Prefix with DRAFT indicator
        response_text = f"[DRAFT - Pending Human Review]\n\n{response_text}"
        
        return AgentQueryResponse(
            response=response_text,
            hitl_mode="DRAFT",
            approval_id=approval.id,
        )
    
    # INFORM mode - return response directly
    return AgentQueryResponse(response=response_text, hitl_mode="INFORM")
```

#### Step 2: Governance Evaluation

**File:** `packages/core/governance/manager.py:50-120`

```python
def evaluate_for_agent(self, query: str, agent_id: str, domain: str):
    """Evaluate governance for an agent query."""
    
    # 1. Classify intent
    intent = self._classify_intent(query, domain)
    # Returns: Intent(domain, task, audience, impact, confidence)
    
    # 2. Detect risk signals
    risk = self._detect_risk_signals(query)
    # Returns: RiskSignals(["PII", "FINANCIAL", ...])
    
    # 3. Evaluate governance policies
    decision = evaluate_governance(intent, risk, context, policy_set)
    # Returns: GovernanceDecision with hitl_mode
    
    # 4. Determine HITL mode (if not set by policy)
    if decision.hitl_mode is None:
        hitl_mgr = get_hitl_manager()
        decision.hitl_mode = hitl_mgr.determine_hitl_mode(
            intent_domain=intent.domain,
            intent_impact=intent.impact,
            risk_signals=risk.signals,
        )
    
    return decision
```

#### Step 3: Create Approval Request

**File:** `packages/core/hitl/__init__.py:172-211`

```python
def create_approval_request(
    self,
    hitl_mode: HITLMode,
    user_id: str,
    agent_id: str,
    agent_name: str,
    original_query: str,
    proposed_response: str,
    ...
) -> ApprovalRequest:
    """Create a new approval request."""
    
    # Calculate expiration based on mode
    exp_hours = {
        HITLMode.DRAFT: 24,      # 24 hours for drafts
        HITLMode.EXECUTE: 48,    # 48 hours for actions
        HITLMode.ESCALATE: 4,    # 4 hours for escalations
    }
    expires_at = (datetime.utcnow() + timedelta(hours=exp_hours[hitl_mode])).isoformat()
    
    # Create request
    request = ApprovalRequest(
        id=str(uuid.uuid4()),
        hitl_mode=hitl_mode,
        status=ApprovalStatus.PENDING,
        user_id=user_id,
        agent_id=agent_id,
        original_query=original_query,
        proposed_response=proposed_response,
        expires_at=expires_at,
        priority=self._determine_priority(risk_signals),
        ...
    )
    
    # Save to storage
    self._approvals[request.id] = request
    self._save_approvals()  # → data/hitl/approvals.json
    
    # Auto-assign reviewer
    workflow = get_hitl_workflow_manager()
    workflow.auto_assign(request.id)
    
    return request
```

#### Step 4: Reviewer Actions

**File:** `packages/core/hitl/__init__.py:218-270`

```python
def approve_request(self, request_id: str, reviewer_id: str, notes: str = None):
    """Approve a pending request."""
    request = self._approvals.get(request_id)
    
    if not request or request.status != ApprovalStatus.PENDING:
        return None
    
    # Update status
    request.status = ApprovalStatus.APPROVED
    request.resolved_at = datetime.utcnow().isoformat()
    request.resolved_by = reviewer_id
    request.reviewer_notes = notes
    
    # Save
    self._save_approvals()
    
    # Send notification to user
    notify_user(request.user_id, "Your request was approved")
    
    # Execute the approved action (if EXECUTE mode)
    if request.hitl_mode == HITLMode.EXECUTE:
        execute_approved_action(request)
    
    return request

def reject_request(self, request_id: str, reviewer_id: str, reason: str):
    """Reject a pending request."""
    request = self._approvals.get(request_id)
    
    if not request or request.status != ApprovalStatus.PENDING:
        return None
    
    # Update status
    request.status = ApprovalStatus.REJECTED
    request.resolved_at = datetime.utcnow().isoformat()
    request.resolved_by = reviewer_id
    request.reviewer_notes = reason
    
    # Save
    self._save_approvals()
    
    # Notify user of rejection
    notify_user(request.user_id, f"Your request was rejected: {reason}")
    
    return request
```

#### Step 5: Escalation (if SLA breach)

**File:** `packages/core/hitl/workflow.py:426-510`

```python
def escalate(self, approval_id: str, reason: str) -> bool:
    """Escalate an approval to the next level."""
    approval = self._hitl.get_approval_request(approval_id)
    
    # Determine current level
    current_reviewer = self._reviewers.get(approval.assigned_to)
    current_level = current_reviewer.level  # L1, L2, L3, or L4
    
    # Find next level
    level_order = [L1_SUPERVISOR, L2_MANAGER, L3_DIRECTOR, L4_EXECUTIVE]
    next_level = level_order[level_order.index(current_level) + 1]
    
    # Find reviewer at next level
    new_reviewer = self.find_available_reviewer(level=next_level)
    
    # Reassign
    self._hitl.assign_request(approval_id, new_reviewer.reviewer_id)
    
    # Log escalation
    approval.context["escalation_history"].append({
        "from_level": current_level,
        "to_level": next_level,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    # Notify new reviewer
    notify_reviewer(new_reviewer, "Escalated approval assigned")
    
    return True
```

### State Transition Diagram

```
                    ┌──────────────┐
                    │   PENDING    │
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ↓                 ↓                 ↓
    ┌─────────┐     ┌──────────┐     ┌──────────┐
    │APPROVED │     │ REJECTED │     │ EXPIRED  │
    └─────────┘     └──────────┘     └──────────┘
         │                 │                 │
         ↓                 ↓                 ↓
    Execute           Notify            Notify
    Action            User              User
    
    
    Escalation Path (SLA breach):
    
    PENDING → Check SLA → Breach? → Escalate to L2
                    ↓
              Still pending?
                    ↓
           Escalate to L3 → L4
```

---

## Question 3: Which Tools Can Run Without Approval?

### Answer: Depends on Tool Risk Classification

**Current Implementation:** Tools require approval based on:
1. Governance policy evaluation
2. Tool's inherent risk level
3. Action context (user, domain, impact)

### Tool Approval Matrix

| Tool Type | Risk Level | HITL Mode | Example | Requires Approval? |
|-----------|------------|-----------|---------|-------------------|
| **Read-only queries** | Low | INFORM | "Show database records" | ❌ No |
| **Search operations** | Low | INFORM | "Find customer by name" | ❌ No |
| **Report generation** | Low | INFORM | "Generate sales report" | ❌ No |
| **Data visualization** | Low | INFORM | "Create chart" | ❌ No |
| **Draft creation** | Medium | DRAFT | "Draft email to customer" | ✅ Yes (review) |
| **Record updates** | Medium | DRAFT | "Update contact info" | ✅ Yes (review) |
| **Notifications** | Medium | DRAFT | "Send notification" | ✅ Yes (review) |
| **Approvals** | High | EXECUTE | "Approve purchase order" | ✅ Yes (manager) |
| **Payments** | High | EXECUTE | "Process payment" | ✅ Yes (manager) |
| **Deletions** | High | EXECUTE | "Delete record" | ✅ Yes (manager) |
| **External API calls** | High | EXECUTE | "Call vendor API" | ✅ Yes (manager) |
| **PII operations** | Critical | ESCALATE | "Access SSN" | ✅ Yes (immediate) |
| **Financial transactions** | Critical | ESCALATE | "Transfer funds" | ✅ Yes (immediate) |
| **Legal actions** | Critical | ESCALATE | "Sign contract" | ✅ Yes (immediate) |
| **System admin** | Critical | ESCALATE | "Delete production DB" | ✅ Yes (immediate) |

### How Tool Approval is Determined

**Code Location:** Tool calls go through same governance evaluation

```python
def execute_tool(tool_name: str, params: dict, context: dict):
    """Execute a tool with governance check."""
    
    # 1. Get tool metadata
    tool = get_tool(tool_name)
    
    # 2. Classify tool action
    intent = classify_tool_action(tool, params)
    # Returns: Intent(domain="Finance", task="payment", impact="high")
    
    # 3. Detect risk from params
    risk = detect_tool_risks(tool, params)
    # Returns: RiskSignals(["FINANCIAL_LARGE"])
    
    # 4. Evaluate governance
    decision = evaluate_governance(intent, risk, context, policy_set)
    
    # 5. Check if tool execution allowed
    if not decision.tools_allowed:
        raise ToolExecutionBlocked("Governance policy blocks this tool")
    
    # 6. Check approval requirement
    if decision.approval_required:
        # Create approval request
        approval = create_approval_request(
            hitl_mode=decision.hitl_mode,
            action="execute_tool",
            tool_name=tool_name,
            params=params,
        )
        
        # Wait for approval or return pending
        if approval.status == ApprovalStatus.APPROVED:
            # Execute tool
            return tool.execute(params)
        else:
            return {"status": "pending_approval", "approval_id": approval.id}
    
    # 7. No approval needed - execute directly
    return tool.execute(params)
```

### Configuring Tool Approval Requirements

**Method 1: Tool Metadata**

```python
class Tool(BaseModel):
    name: str
    description: str
    risk_level: str  # "low", "medium", "high", "critical"
    requires_approval: bool = False
    min_approval_level: EscalationLevel = L1_SUPERVISOR
    
# Example
send_email_tool = Tool(
    name="send_email",
    risk_level="medium",
    requires_approval=True,
    min_approval_level=L1_SUPERVISOR,
)

delete_record_tool = Tool(
    name="delete_record",
    risk_level="high",
    requires_approval=True,
    min_approval_level=L2_MANAGER,
)

financial_transfer_tool = Tool(
    name="transfer_funds",
    risk_level="critical",
    requires_approval=True,
    min_approval_level=L3_DIRECTOR,
)
```

**Method 2: Governance Policies**

```json
{
  "id": "tool-payment-approval",
  "name": "Payment Tools Require Approval",
  "conditions": [
    {"field": "tool.name", "operator": "eq", "value": "process_payment"},
    {"field": "tool.params.amount", "operator": "gt", "value": 1000}
  ],
  "action": {
    "tools_allowed": true,
    "approval_required": true,
    "hitl_mode": "EXECUTE",
    "escalation_reason": "Payment > $1000 requires manager approval"
  }
}
```

---

## Question 4: Where Do Escalations Go?

### Answer: Multi-Channel Notification System

**Current Implementation:** Escalations use a **pluggable notification system** with multiple channels.

### Escalation Destinations

#### 1. Internal Approval Queue

**Primary destination:** `data/hitl/approvals.json`

```json
{
  "approval_id_123": {
    "status": "PENDING",
    "hitl_mode": "ESCALATE",
    "assigned_to": "reviewer_456",
    "priority": "urgent",
    "escalation_reason": "PII detected",
    "created_at": "2026-01-28T10:00:00Z",
    "expires_at": "2026-01-28T14:00:00Z"
  }
}
```

**Access via:**
- API: `GET /hitl/queue?hitl_mode=ESCALATE`
- Dashboard: `web/src/app/(dashboard)/approvals`

#### 2. Reviewer Notifications

**File:** `packages/core/hitl/workflow.py:577-617`

```python
def _send_notification(
    self,
    type: NotificationType,
    recipient_id: str,
    title: str,
    message: str,
    approval_id: str = None,
):
    """Send notification via registered handlers."""
    
    notification = Notification(
        type=type,
        recipient_id=recipient_id,
        title=title,
        message=message,
        approval_id=approval_id,
    )
    
    # Call all registered handlers
    for handler in self._notification_handlers:
        handler(notification)
```

**Supported notification handlers:**
- In-app notifications (stored in memory)
- Email (requires handler registration)
- Slack (requires handler registration)
- Microsoft Teams (requires handler registration)
- SMS (requires handler registration)
- Webhook (requires handler registration)

#### 3. Email Notifications (Extensible)

**Example email handler:**

```python
def email_notification_handler(notification: Notification):
    """Send email for HITL notifications."""
    import smtplib
    from email.message import EmailMessage
    
    # Get reviewer email
    reviewer = get_reviewer(notification.recipient_id)
    
    if notification.type == NotificationType.ESCALATION_TRIGGERED:
        msg = EmailMessage()
        msg['Subject'] = f"URGENT: {notification.title}"
        msg['From'] = "aios@city.gov"
        msg['To'] = reviewer.email
        msg.set_content(f"""
        {notification.message}
        
        Approval ID: {notification.approval_id}
        Review at: https://aios.city.gov/approvals/{notification.approval_id}
        """)
        
        # Send email
        smtp = smtplib.SMTP('localhost')
        smtp.send_message(msg)
        smtp.quit()

# Register handler
workflow = get_hitl_workflow_manager()
workflow.register_notification_handler(email_notification_handler)
```

#### 4. Slack Integration (Extensible)

**Example Slack handler:**

```python
def slack_notification_handler(notification: Notification):
    """Send Slack message for escalations."""
    import requests
    
    if notification.type == NotificationType.ESCALATION_TRIGGERED:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        
        payload = {
            "text": f"🚨 *ESCALATION*: {notification.title}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": notification.message
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Review"},
                            "url": f"https://aios.city.gov/approvals/{notification.approval_id}"
                        }
                    ]
                }
            ]
        }
        
        requests.post(webhook_url, json=payload)

# Register
workflow.register_notification_handler(slack_notification_handler)
```

#### 5. Microsoft Teams (Extensible)

**Example Teams handler:**

```python
def teams_notification_handler(notification: Notification):
    """Send Teams message for escalations."""
    import requests
    
    if notification.type == NotificationType.ESCALATION_TRIGGERED:
        webhook_url = os.getenv("TEAMS_WEBHOOK_URL")
        
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": notification.title,
            "themeColor": "FF0000",
            "title": "🚨 ESCALATION",
            "sections": [
                {
                    "activityTitle": notification.title,
                    "activitySubtitle": notification.message,
                    "facts": [
                        {"name": "Approval ID", "value": notification.approval_id},
                        {"name": "Priority", "value": "URGENT"}
                    ]
                }
            ],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "Review Approval",
                    "targets": [
                        {"os": "default", "uri": f"https://aios.city.gov/approvals/{notification.approval_id}"}
                    ]
                }
            ]
        }
        
        requests.post(webhook_url, json=payload)

# Register
workflow.register_notification_handler(teams_notification_handler)
```

### What Triggers Escalation?

#### Trigger 1: High-Risk Detection (Immediate)

**Code:** `packages/core/hitl/__init__.py:148-150`

```python
# High-risk signals always escalate
high_risk_signals = {"PII", "PHI", "LEGAL_CONTRACT", "FINANCIAL_LARGE"}
if any(s in high_risk_signals for s in risk_signals):
    return HITLMode.ESCALATE
```

**Examples:**
- Query contains Social Security Number
- Request involves Protected Health Information
- Legal contract signature requested
- Large financial transaction ($10K+)

#### Trigger 2: SLA Breach (Automatic)

**Code:** `packages/core/hitl/workflow.py:383-420`

```python
def process_sla_violations(self):
    """Process SLA violations and trigger escalations."""
    issues = self.check_sla_status()
    
    for issue in issues:
        if issue["status"] == "breach":
            # Escalate to next level
            self.escalate(
                approval_id=issue["approval_id"],
                reason=f"SLA breach: {issue['age_minutes']} minutes"
            )
```

**SLA Thresholds:**

```python
_sla_configs = {
    HITLMode.DRAFT: SLAConfig(
        warning_minutes=60,   # 1 hour warning
        breach_minutes=240,   # 4 hour breach
    ),
    HITLMode.EXECUTE: SLAConfig(
        warning_minutes=120,  # 2 hour warning
        breach_minutes=480,   # 8 hour breach
    ),
    HITLMode.ESCALATE: SLAConfig(
        warning_minutes=15,   # 15 min warning
        breach_minutes=60,    # 1 hour breach
    ),
}
```

**Escalation on breach:**
1. Check age of pending approval
2. If age > breach_minutes:
   - Escalate to next level (L1→L2→L3→L4)
   - Notify new reviewer
   - Update priority to "urgent"
   - Log escalation history

#### Trigger 3: Manual Escalation

**API:** `POST /hitl/approvals/{id}/escalate`

```python
@router.post("/approvals/{request_id}/escalate")
async def escalate_approval(request_id: str, request: EscalateRequest):
    """Manually escalate an approval."""
    workflow = get_hitl_workflow_manager()
    
    if workflow.escalate(request_id, request.reason):
        return {"status": "ok", "message": "Approval escalated"}
    
    raise HTTPException(400, "Cannot escalate")
```

**Use cases:**
- Reviewer doesn't have authority
- Complex case needs senior review
- Policy uncertainty requires legal/executive input

#### Trigger 4: Governance Policy

**Example policy that triggers escalation:**

```json
{
  "id": "personnel-escalation",
  "name": "Personnel Actions Escalate to HR Director",
  "conditions": [
    {"field": "intent.domain", "operator": "eq", "value": "HR"},
    {"field": "intent.task", "operator": "contains", "value": "personnel"}
  ],
  "action": {
    "hitl_mode": "ESCALATE",
    "escalation_reason": "Personnel action requires HR Director review"
  }
}
```

### Escalation Chain

```
L1_SUPERVISOR (Frontline Manager)
      ↓
      ↓ (if SLA breach or manual escalation)
      ↓
L2_MANAGER (Department Manager)
      ↓
      ↓ (if SLA breach or manual escalation)
      ↓
L3_DIRECTOR (Department Director)
      ↓
      ↓ (if SLA breach or manual escalation)
      ↓
L4_EXECUTIVE (C-Level Executive)
```

**Workload balancing:** When escalating, system finds available reviewer at next level with lowest current workload.

---

## Question 5: Two-Person Integrity / Dual Approval

### Current Status: ⚠️ **PARTIALLY SUPPORTED**

The system has foundations for dual approval but needs enhancement for full two-person integrity.

### What Exists (Partial Support)

#### 1. Sequential Approval Chain

**Current:** Escalation chain provides sequential review

```python
# L1 reviews first
approval.assigned_to = "reviewer_L1"
reviewer_L1.approve(approval_id)

# If escalated, L2 reviews
approval.assigned_to = "reviewer_L2"  # Second person
reviewer_L2.approve(approval_id)  # Second approval
```

**Limitation:** This is sequential, not parallel dual approval

#### 2. Reviewer History Tracking

**Current:** All reviewers are tracked

```python
approval.context["escalation_history"] = [
    {"from_reviewer": "reviewer_L1", "to_reviewer": "reviewer_L2"},
    {"from_reviewer": "reviewer_L2", "to_reviewer": "reviewer_L3"},
]
```

**Limitation:** Tracks history but doesn't enforce dual requirement

#### 3. Batch Operations

**Current:** Multiple reviewers can approve in batch

```python
# Reviewer 1 approves subset
workflow.batch_approve(approval_ids=[...], reviewer_id="reviewer_1")

# Reviewer 2 approves subset
workflow.batch_approve(approval_ids=[...], reviewer_id="reviewer_2")
```

**Limitation:** Not true parallel dual approval

### What's Missing for Full Two-Person Integrity

#### Missing Feature 1: Parallel Dual Approval

**Need:**

```python
class DualApprovalRequest(ApprovalRequest):
    """Approval requiring two independent reviewers."""
    
    required_approvals: int = 2
    approvals_received: list[dict] = []  # [{reviewer_id, timestamp, notes}]
    
    def is_approved(self) -> bool:
        """Check if required approvals met."""
        return len(self.approvals_received) >= self.required_approvals
    
    def can_reviewer_approve(self, reviewer_id: str) -> bool:
        """Check if reviewer can approve (not already approved)."""
        return reviewer_id not in [a["reviewer_id"] for a in self.approvals_received]
```

#### Missing Feature 2: Role Separation Enforcement

**Need:**

```python
class TwoPersonIntegrityRule:
    """Rule for two-person integrity."""
    
    requires_dual_approval: bool = True
    approvers_must_differ: bool = True  # Can't be same person
    roles_must_differ: bool = True      # Can't be from same role
    departments_must_differ: bool = False  # Optional: different departments
    min_level_difference: int = 1       # L1 + L2, not L1 + L1
```

#### Missing Feature 3: Conflict of Interest Detection

**Need:**

```python
def check_conflict_of_interest(
    approval: ApprovalRequest,
    reviewer: ReviewerProfile,
) -> bool:
    """Check if reviewer has conflict of interest."""
    
    # Check if reviewer is requestor
    if reviewer.reviewer_id == approval.user_id:
        return True
    
    # Check if reviewer already approved
    if reviewer.reviewer_id in approval.approvals_received:
        return True
    
    # Check reporting relationship
    if reviewer.reviewer_id in get_direct_reports(approval.user_id):
        return True
    
    # Check same department (if required)
    if approval.context.get("require_cross_department"):
        if reviewer.departments[0] == approval.user_department:
            return True
    
    return False
```

### Implementation Plan for Full Two-Person Integrity

#### Enhancement 1: Add Dual Approval Support

**File:** `packages/core/hitl/__init__.py`

```python
class ApprovalRequest(BaseModel):
    # ... existing fields ...
    
    # NEW: Dual approval fields
    required_approvals: int = 1  # Default: single approval
    approvals_received: list[dict[str, Any]] = Field(default_factory=list)
    dual_approval_rules: dict[str, bool] = Field(default_factory=dict)
    
    def add_approval(
        self,
        reviewer_id: str,
        notes: str | None = None,
    ) -> bool:
        """Add an approval from a reviewer."""
        
        # Check if reviewer already approved
        if any(a["reviewer_id"] == reviewer_id for a in self.approvals_received):
            return False
        
        # Add approval
        self.approvals_received.append({
            "reviewer_id": reviewer_id,
            "timestamp": datetime.utcnow().isoformat(),
            "notes": notes,
        })
        
        # Check if all required approvals received
        if len(self.approvals_received) >= self.required_approvals:
            self.status = ApprovalStatus.APPROVED
            self.resolved_at = datetime.utcnow().isoformat()
        
        return True
    
    def is_fully_approved(self) -> bool:
        """Check if all required approvals received."""
        return len(self.approvals_received) >= self.required_approvals
```

#### Enhancement 2: Add Two-Person Integrity Rules

**File:** `packages/core/hitl/__init__.py`

```python
class TwoPersonIntegrityConfig(BaseModel):
    """Configuration for two-person integrity."""
    
    enabled: bool = True
    required_approvals: int = 2
    approvers_must_differ: bool = True
    min_level_difference: int = 0  # 0 = same level OK, 1 = must be different
    require_cross_department: bool = False
    require_cross_domain: bool = False
    conflict_checks_enabled: bool = True

def create_dual_approval_request(
    self,
    hitl_mode: HITLMode,
    user_id: str,
    agent_id: str,
    original_query: str,
    proposed_response: str,
    two_person_config: TwoPersonIntegrityConfig,
    ...
) -> ApprovalRequest:
    """Create approval request with two-person integrity."""
    
    request = ApprovalRequest(
        hitl_mode=hitl_mode,
        user_id=user_id,
        agent_id=agent_id,
        original_query=original_query,
        proposed_response=proposed_response,
        required_approvals=two_person_config.required_approvals,
        dual_approval_rules={
            "approvers_must_differ": two_person_config.approvers_must_differ,
            "min_level_difference": two_person_config.min_level_difference,
            "require_cross_department": two_person_config.require_cross_department,
        },
        ...
    )
    
    # Auto-assign first reviewer
    reviewer1 = workflow.find_available_reviewer(...)
    request.assigned_to = reviewer1.reviewer_id
    
    # Find second reviewer (different from first)
    reviewer2 = workflow.find_available_reviewer(
        exclude=[reviewer1.reviewer_id],
        min_level=reviewer1.level + config.min_level_difference,
    )
    
    # Track both reviewers
    request.context["required_reviewers"] = [
        reviewer1.reviewer_id,
        reviewer2.reviewer_id,
    ]
    
    return request
```

#### Enhancement 3: Governance Rule for Dual Approval

**File:** `data/governance_policies.json`

```json
{
  "id": "financial-dual-approval",
  "name": "Large Financial Transactions Require Dual Approval",
  "conditions": [
    {"field": "intent.domain", "operator": "eq", "value": "Finance"},
    {"field": "risk.contains", "operator": "eq", "value": "FINANCIAL_LARGE"}
  ],
  "action": {
    "hitl_mode": "EXECUTE",
    "approval_required": true,
    "two_person_integrity": {
      "enabled": true,
      "required_approvals": 2,
      "approvers_must_differ": true,
      "min_level_difference": 1,
      "require_cross_department": false
    },
    "escalation_reason": "Large financial transaction requires dual approval from different managers"
  },
  "priority": 95
}
```

### Use Cases for Two-Person Integrity

| Use Case | Dual Approval? | Configuration |
|----------|----------------|---------------|
| **Financial > $10K** | ✅ Yes | 2 approvers, L2+ minimum, must differ |
| **Wire transfers** | ✅ Yes | 2 approvers, L3+ minimum, cross-dept |
| **Legal contracts** | ✅ Yes | 2 approvers, Legal + Business owner |
| **Personnel termination** | ✅ Yes | 2 approvers, HR + Department head |
| **System admin actions** | ✅ Yes | 2 approvers, IT + Security |
| **Database deletions** | ✅ Yes | 2 approvers, DBA + Application owner |
| **Policy changes** | ✅ Yes | 2 approvers, Policy owner + Legal |
| **Standard approvals** | ❌ No | 1 approver |

---

## Summary

### Your HITL System is a Differentiator ✅

**Strengths:**
1. ✅ **4-tier HITL modes** (INFORM, DRAFT, EXECUTE, ESCALATE)
2. ✅ **Risk-based determination** (automatic based on PII, impact, domain)
3. ✅ **4-level escalation chain** (L1→L2→L3→L4)
4. ✅ **SLA monitoring** with auto-escalation
5. ✅ **Workload balancing** for reviewer assignment
6. ✅ **Batch operations** for efficiency
7. ✅ **Extensible notifications** (email, Slack, Teams)
8. ✅ **Comprehensive metrics** and reporting

**Enhancement Needed:**
- ⚠️ **Two-person integrity** needs full implementation (currently partial)

### Quick Reference

| Question | Answer Location |
|----------|-----------------|
| **Which actions require approval?** | Defined in `determine_hitl_mode()` - see approval matrix |
| **Approval code path?** | See state machine diagram and code path section |
| **Tools without approval?** | Read-only/low-risk tools - see tool matrix |
| **Escalation destinations?** | Approval queue + multi-channel notifications (email/Slack/Teams) |
| **Dual approval?** | Partially supported - needs enhancement for full two-person integrity |

---

**Document Version:** 1.0  
**Author:** HITL System Analysis  
**Date:** January 28, 2026
