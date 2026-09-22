---
title: AI Platform Budget & Quota Policy
doc_id: meridian-ai-budget-quota-policy
doc_type: policy
effective_date: 2026-01-01
supersedes: null
status: current
contains_pii: false
owner: AI Governance Council
---

> **SYNTHETIC — DEMONSTRATION DATA ONLY.** Meridian Wealth Partners is a
> fictional firm and the Meridian AI Platform does not exist. No token count,
> price, cost centre, or person in this document is real.

# AI Platform Budget & Quota Policy

**Effective 1 January 2026**

## 1. Budget allocation

Each consuming business unit holds a monthly budget for AI Platform
consumption, expressed as billed cost — that is, metered consumption
inclusive of the 8.0% platform uplift.
Budgets are set annually by the AI Governance Council and are not
transferable between business units or between months.

| BU | Business unit | Cost centre | Monthly budget | Annualised |
|---|---|---|---:|---:|
| WAS | Wealth Advisory Support | CC-4101 | $9,500 | $114,000 |
| COK | Client Onboarding & KYC | CC-4210 | $4,400 | $52,800 |
| CSV | Compliance Surveillance | CC-4315 | $14,000 | $168,000 |
| INR | Investment Research | CC-4402 | $16,000 | $192,000 |
| CCO | Contact Center Operations | CC-4508 | $2,900 | $34,800 |
| MCC | Marketing & Client Communications | CC-4620 | $1,200 | $14,400 |
| ITS | Corporate IT Service Desk | CC-4733 | $400 | $4,800 |
| ITD | Institutional Trading Desk | CC-4850 | $11,500 | $138,000 |
| **All** | **Platform** | — | **$59,900** | **$718,800** |

## 2. Thresholds and actions

| Billed consumption vs monthly budget | Action |
|---|---|
| 80% | Notification to the cost-centre owner. |
| 95% | Notification to the owner and to the AI Governance Council. |
| 100% | Reasoning-tier requests are rate-limited to 60% of the trailing 7-day mean. |
| 120% | Reasoning-tier access suspended for the remainder of the period; volume tier continues. |

Rate limits and suspensions apply to the reasoning tier only. Volume-tier
and embedding workloads are never suspended, because they carry the
regulated operational paths.

## 3. Quotas

| Control | Limit |
|---|---|
| Per-session tokens, reasoning tier | 250,000 |
| Planner re-plan depth | 3 |
| Per-BU concurrent reasoning-tier requests | 40 |
| Daily-rate anomaly alert | 2.5x trailing 30-day mean |

## 4. Breach review

A breach of the monthly budget is reviewed by AI Platform FinOps within
five business days. The review establishes whether the cause is consumer
demand or a platform defect. A breach caused by a platform defect is
credited under the incident-credit provision of
`meridian-ai-chargeback-policy` and does not count toward the suspension
thresholds in section 2.

## 5. Exceptions

A temporary budget increase requires written approval from the AI
Governance Council and the business unit's finance partner. Verbal or
chat-channel approvals are not effective. Exceptions expire at the end of
the quarter in which they are granted.
