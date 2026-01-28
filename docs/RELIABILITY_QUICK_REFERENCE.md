# Reliability + Enterprise: Quick Reference

**Production-Ready Reliability with Critical Environment Gap** ⚠️

---

## Quick Answers

### H1: What happens when model/tool fails?

✅ **Multi-layer failure handling:**

1. **Retry (3x):** Exponential backoff (0.5s, 1s, 1.5s)
2. **Fallback:** Secondary model or tier downgrade
3. **Escalate:** HITL system if all fail

**Code:** `packages/core/llm/router.py` (IntelligentModelRouter.execute)

---

### H2: Rate limiting and quotas?

✅ **Comprehensive multi-level system:**

**Per-User:**
- 60 requests/minute
- 1000 requests/hour
- 10K requests/day
- 1M tokens/day
- $100 cost/day

**Per-Department:**
- 50K requests/day
- 5M tokens/day
- $500 cost/day

**Code:** `packages/core/ratelimit/__init__.py` (RateLimitManager)

---

### H3: Environment separation?

⚠️ **CRITICAL GAP - Not implemented:**

- ❌ No dev/stage/prod profiles
- ❌ Same API keys everywhere
- ❌ No audit boundaries
- ❌ No environment tagging

**Blocker:** Needs environment profile system (2 days)

---

### H4: Dashboards and KPIs?

✅ **Production-ready analytics:**

**Primary KPIs (4):**
1. Total Requests (30d)
2. Escalation Rate (target <5%)
3. Guardrails Enforced
4. Cost Savings

**Extended KPIs (4):**
5. Unique Users
6. Avg Response Time
7. Success Rate
8. Total Tokens

**Code:** `packages/api/analytics.py` + `web/src/components/dashboard/kpi-cards.tsx`

---

## Code Locations

| Component | File |
|-----------|------|
| **Retry/Fallback** | `packages/core/llm/router.py` |
| **Health Checks** | `IntelligentModelRouter._check_model_health()` |
| **Rate Limiting** | `packages/core/ratelimit/__init__.py` |
| **Analytics** | `packages/core/analytics/__init__.py` |
| **Dashboard UI** | `web/src/components/dashboard/kpi-cards.tsx` |
| **Analytics API** | `packages/api/analytics.py` |
| **Environment Config** | `packages/api/config.py` |

---

## Example Usage

### Check Rate Limit

```python
from packages.core.ratelimit import get_rate_limit_manager

rate_limiter = get_rate_limit_manager()

# Check if request allowed
result = rate_limiter.check_rate_limit(
    user_id="user-123",
    department="HR"
)

if not result.allowed:
    # Rate limit exceeded
    print(f"Denied: {result.reason}")
    print(f"Retry after: {result.retry_after_seconds}s")
else:
    # Process request
    # ... do work ...
    
    # Record usage
    rate_limiter.record_usage(
        user_id="user-123",
        department="HR",
        tokens=150,
        cost=0.015
    )
```

### Execute with Retry/Fallback

```python
from packages.core.llm import get_model_router, Task

router = get_model_router()

# Create task with retry config
task = Task(
    task_type="conversation",
    context_length=1000,
    max_retries=3,           # ← 3 retry attempts
    allow_fallback=True,     # ← Enable fallback
    escalate_on_failure=True # ← Escalate if all fail
)

# Execute (automatic retry + fallback)
result = await router.execute(
    task=task,
    prompt="What is the leave policy?",
)

if result.success:
    print(f"Response: {result.response.content}")
    print(f"Retries: {result.retries}")
    print(f"Fallback used: {result.fallback_used}")
else:
    print(f"Failed: {result.error}")
    # Escalate to human via HITL
```

### Get Analytics

```python
from packages.core.analytics import get_analytics_manager

analytics = get_analytics_manager()

# Get 30-day summary
summary = analytics.get_summary(days=30)

print(f"Total queries: {summary.total_queries_30d}")
print(f"Escalation rate: {summary.escalation_rate}%")
print(f"Avg latency: {summary.avg_latency_ms}ms")
print(f"Success rate: {summary.success_rate}%")
```

### API Endpoints

```http
# Get dashboard summary
GET /api/analytics/summary?days=30

# Get agent analytics
GET /api/analytics/agents/{agent_id}?days=30

# List events with filtering
GET /api/analytics/events?agent_id=hr-agent&limit=100

# Export analytics
GET /api/analytics/export?format=csv&days=30

# Check rate limit usage
GET /api/ratelimit/usage?user_id=user-123
```

---

## Status Summary

### Reliability: ✅ 85%
- Retry logic ✅
- Fallback models ✅
- Health checks ✅
- HITL escalation ✅
- Circuit breaker ❌ (recommended)

### Rate Limiting: ✅ 95%
- Per-user quotas ✅
- Per-department quotas ✅
- Token limits ✅
- Cost limits ✅
- Sliding windows ✅
- Custom limits ✅

### Environment: ⚠️ 40%
- Basic .env ✅
- Dev/stage/prod ❌ **CRITICAL**
- Separate keys ❌ **CRITICAL**
- Audit boundaries ❌ **HIGH**
- Environment tags ❌ **HIGH**

### Analytics: ✅ 90%
- KPI dashboard ✅
- Real-time data ✅
- Agent breakdown ✅
- Export ✅
- Time-series charts ⚠️ (could add)

---

## Production Checklist

**Before Production:**
- [ ] Implement environment separation system
- [ ] Configure separate API keys (dev/stage/prod)
- [ ] Set up separate audit storage per environment
- [ ] Add environment tagging to traces
- [ ] Implement circuit breaker pattern
- [ ] Configure production rate limits
- [ ] Set up health monitoring dashboard
- [ ] Enable cost alerts
- [ ] Test failover scenarios
- [ ] Document escalation procedures

**Production Monitoring:**
- [ ] Monitor escalation rate (target <5%)
- [ ] Monitor success rate (target >99%)
- [ ] Monitor P95 latency (target <5s)
- [ ] Monitor cost per query
- [ ] Monitor quota usage
- [ ] Review failed requests daily
- [ ] Review HITL escalations weekly

---

## Failure Type Matrix

| Failure | Retry? | Fallback? | Escalate? |
|---------|--------|-----------|-----------|
| Network timeout | ✅ 3x | ✅ After | ⚠️ If all fail |
| Rate limit (429) | ✅ With backoff | ❌ No | ❌ No |
| Model unavailable (503) | ✅ 3x | ✅ Immediate | ⚠️ If all fail |
| Auth error (401) | ❌ No | ❌ No | ✅ Immediate |
| Invalid input (400) | ❌ No | ❌ No | ✅ Immediate |
| Quality failure | ✅ With feedback | ✅ Different model | ⚠️ If all fail |

---

## Rate Limit Response

```json
// 429 Rate Limit Exceeded
{
  "error": "Rate limit exceeded",
  "reason": "Daily request limit exceeded",
  "retry_after_seconds": 3600,
  "current_usage": {
    "requests_this_day": 10000
  },
  "limits": {
    "requests_per_day": 10000
  }
}
```

---

## Recommendations Priority

**Priority 1 (1 week):**
1. Environment separation (2 days) - **CRITICAL**
2. Circuit breaker (1 day)
3. Environment-specific configs (1 day)

**Priority 2 (1 week):**
1. Advanced health monitoring
2. Explicit tenant quotas
3. Predictive alerts

**Priority 3 (1 week):**
1. Retry policy config UI
2. Alert system (Email/Slack)
3. Time-series charting

---

## Timeline to Production

**Current:** 75% ready  
**Blocker:** Environment separation  
**Timeline:** 3 weeks to 100%

- Week 1: Environment separation + circuit breaker
- Week 2: Enhanced monitoring + quotas
- Week 3: Advanced analytics + alerts

---

**Complete documentation:** See `RELIABILITY_AND_ENTERPRISE_READINESS.md` (46KB)

**Quick Reference Version:** 1.0  
**Date:** January 28, 2026
