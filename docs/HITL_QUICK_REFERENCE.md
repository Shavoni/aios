# HITL System: Quick Reference

**Your Key Differentiator** - Human-in-the-Loop approval workflows

---

## Quick Answers

### Q1: Which actions require approval?

**Automatic determination based on risk:**

```
HIGH RISK (PII/PHI/Legal/Financial) → ESCALATE (immediate supervisor)
HIGH IMPACT actions                 → EXECUTE (manager approval)
MEDIUM IMPACT / External comms      → DRAFT (review before sending)
LOW RISK / Read-only               → INFORM (no approval)
```

**Defined:** `packages/core/hitl/__init__.py:139-166`

---

### Q2: Approval state machine?

```
Query → Governance → Decision Point
                          ↓
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                 ↓
    ESCALATE          EXECUTE           DRAFT         INFORM
        ↓                 ↓                 ↓            ↓
  Create approval   Create approval   Create approval  Auto-respond
        ↓                 ↓                 ↓
     PENDING          PENDING           PENDING
        ↓                 ↓                 ↓
   ┌────┼────┐       ┌────┼────┐      ┌────┼────┐
   ↓    ↓    ↓       ↓    ↓    ↓      ↓    ↓    ↓
APPROVE REJECT EXPIRE...
```

**Code path:** `packages/api/agents.py:452-534`

---

### Q3: Tools without approval?

**No approval:**
- Read-only queries
- Database searches
- Report generation
- Data visualization

**Approval required:**
- Drafts (review)
- Record updates (review)
- Payments (manager)
- Deletions (manager)
- PII operations (immediate)

**See:** Tool approval matrix in full doc

---

### Q4: Where do escalations go?

**Destinations:**
1. **Approval queue** - `data/hitl/approvals.json`
2. **Dashboard** - `web/src/app/(dashboard)/approvals`
3. **API** - `GET /hitl/queue?hitl_mode=ESCALATE`
4. **Notifications:**
   - In-app
   - Email (extensible)
   - Slack (extensible)
   - Teams (extensible)

**Escalation chain:**
```
L1_SUPERVISOR → L2_MANAGER → L3_DIRECTOR → L4_EXECUTIVE
```

**Triggers:**
- High-risk detection (PII, PHI, etc.)
- SLA breach (automatic)
- Manual escalation (reviewer request)
- Governance policy

---

### Q5: Two-person integrity?

**Status:** ⚠️ Partially supported

**What exists:**
- Sequential approval via escalation chain
- Multiple reviewers tracked
- Escalation history logged

**What's missing:**
- Parallel dual approval
- Conflict of interest detection
- Role separation enforcement

**Enhancement plan provided** in full doc with code examples.

---

## Key Files

| Component | File |
|-----------|------|
| Core HITL | `packages/core/hitl/__init__.py` |
| Advanced workflow | `packages/core/hitl/workflow.py` |
| API | `packages/api/hitl.py` |
| Storage | `data/hitl/approvals.json` |
| UI | `web/src/app/(dashboard)/approvals` |

---

## API Endpoints

```bash
# Queue management
GET  /hitl/queue/summary
GET  /hitl/queue?hitl_mode=ESCALATE&priority=urgent

# Approvals
POST /hitl/approvals                    # Create
GET  /hitl/approvals/{id}               # Get
POST /hitl/approvals/{id}/approve       # Approve
POST /hitl/approvals/{id}/reject        # Reject
POST /hitl/approvals/{id}/escalate      # Escalate

# Reviewers
POST /hitl/reviewers                    # Register
GET  /hitl/reviewers?level=L2_MANAGER   # List

# Auto-assignment
POST /hitl/approvals/{id}/auto-assign
POST /hitl/queue/auto-assign-all

# SLA monitoring
GET  /hitl/sla/status
POST /hitl/sla/process-violations

# Stats
GET  /hitl/stats/workflow?days=30
GET  /hitl/stats/dashboard
```

---

## SLA Thresholds

| Mode | Warning | Breach | Action |
|------|---------|--------|--------|
| DRAFT | 1 hour | 4 hours | Auto-escalate |
| EXECUTE | 2 hours | 8 hours | Auto-escalate |
| ESCALATE | 15 min | 1 hour | Auto-escalate |

---

## System Strengths

✅ 4-tier approval modes  
✅ Risk-based automatic routing  
✅ 4-level escalation chain  
✅ SLA monitoring & enforcement  
✅ Workload-balanced assignment  
✅ Batch operations  
✅ Extensible notifications  
✅ Comprehensive metrics  

**This is production-ready and a key differentiator.**

---

## Complete Documentation

See **[HITL_EXECUTION_ANALYSIS.md](./HITL_EXECUTION_ANALYSIS.md)** for:
- Detailed approval requirements
- Complete state machine diagrams
- Tool approval matrix
- Escalation configuration
- Two-person integrity implementation plan
- Code examples for all features

---

**Quick Reference Version:** 1.0  
**Date:** January 28, 2026
