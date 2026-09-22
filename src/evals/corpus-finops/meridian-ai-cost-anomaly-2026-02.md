---
title: Cost Anomaly Review — MAP-INC-2026-0214
doc_id: meridian-ai-cost-anomaly-2026-02
doc_type: incident
effective_date: 2026-03-06
supersedes: null
status: current
contains_pii: false
owner: AI Platform Engineering
---

> **SYNTHETIC — DEMONSTRATION DATA ONLY.** Meridian Wealth Partners is a
> fictional firm and the Meridian AI Platform does not exist. No token count,
> price, cost centre, or person in this document is real.

# Cost Anomaly Review — MAP-INC-2026-0214

**Business unit:** CSV — Compliance Surveillance (CC-4315)

**Billing period affected:** February 2026

**Model:** `gpt-5.5`

**Severity:** Sev-2 (cost)

**Status:** Closed

## Summary

A retry loop in the compliance surveillance escalation-drafting agent caused it
to re-plan and re-emit the same escalation summary repeatedly within a
single session. The loop terminated only on the session timeout, so each
affected session issued many more reasoning-tier calls than intended and
each call emitted a substantially longer completion.

Metered cost for CSV in February 2026 was
$67,761.57, against $10,121.99 in January 2026 —
an excess of $57,639.58. Billed cost was $73,182.50 against
a monthly budget of $14,000.

## Consumption detail

| Period | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| January 2026 | 104,053 | 539,412,000 | 126,529,000 | 109,256,000 | $9,890.89 |
| February 2026 | 288,949 | 1,497,914,000 | 351,362,000 | 1,304,606,000 | $67,514.74 |

## Timeline

| Date | Event |
|---|---|
| 2026-02-03 | Escalation-drafting agent release introduces an unbounded re-plan step. |
| 2026-02-09 | Daily spend for CC-4315 exceeds its trailing 30-day mean; alert suppressed as expected month-start variance. |
| 2026-02-14 | Anomaly detector raises `MAP-INC-2026-0214` on sustained reasoning-tier growth. |
| 2026-02-14 | Platform engineering caps re-plan depth at 3 and redeploys. |
| 2026-02-16 | Consumption returns to trend. |
| 2026-03-06 | Review closed; credit applied to the February statement. |

## Contributing factors

1. **No re-plan bound.** The agent's planner had no maximum depth, so a
   failure to satisfy its own stop condition produced unbounded work.
2. **Alerting tuned to monthly spend, not daily rate.** The breach was
   visible on 9 February in the daily rate and was not escalated until the
   monthly projection moved.
3. **No per-session token ceiling.** Nothing in the serving path limited
   the cost of a single session.

## Corrective actions

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Bound planner re-plan depth at 3 | AI Platform Engineering | Complete |
| 2 | Per-session token ceiling of 250,000 on the reasoning tier | AI Platform Engineering | Complete |
| 3 | Daily-rate anomaly alerting at 2.5x trailing mean | AI Platform FinOps | Complete |
| 4 | Loop-detection regression test in the agent release gate | AI Platform Engineering | Complete |

## Financial treatment

The excess of $57,639.58 over the January 2026 baseline
is classified as platform-caused and credited to the business unit under
the incident-credit provision of `meridian-ai-chargeback-policy`. The
February 2026 statement is issued at the full metered
amount; the credit appears as a separate line in the following quarter's
settlement and is not netted against the statement.

March 2026 metered cost for CSV was $11,818.61,
consistent with the pre-incident trend.
