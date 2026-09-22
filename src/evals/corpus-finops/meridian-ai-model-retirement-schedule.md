---
title: AI Platform Model Retirement Schedule
doc_id: meridian-ai-model-retirement-schedule
doc_type: reference
effective_date: 2026-02-01
supersedes: null
status: current
contains_pii: false
owner: AI Platform Engineering
---

> **SYNTHETIC — DEMONSTRATION DATA ONLY.** Meridian Wealth Partners is a
> fictional firm and the Meridian AI Platform does not exist. No token count,
> price, cost centre, or person in this document is real.

# Model Retirement Schedule

**As of 1 February 2026**

| Model | Status | New deployments | Retirement date |
|---|---|---|---|
| `gpt-5.5` | General availability | Permitted | None announced |
| `gpt-5.4-mini` | General availability | Permitted | None announced |
| `gpt-4.1` | Deprecated | Blocked from 2025-11-01 | 2026-06-30 |
| `text-embedding-3-large` | General availability | Permitted | None announced |
| `text-embedding-3-small` | Deprecated | Blocked from 2026-03-01 | 2026-09-30 |

## Migration obligations

A business unit running a deprecated model must complete migration before
the retirement date. After that date the deployment is removed and calls
fail; there is no grace period and no extension process.

Migration off a deprecated model does not require a budget exception, even
where the replacement carries a different rate.

## Completed migrations

| Business unit | From | To | Completed |
|---|---|---|---|
| MCC — Marketing & Client Communications | `gpt-4.1` | `gpt-5.4-mini` | 2026-01 |

## Outstanding

| Business unit | Model | Retirement date |
|---|---|---|
| ITS — Corporate IT Service Desk | `gpt-4.1` | 2026-06-30 |
| COK — Client Onboarding & KYC | `text-embedding-3-small` | 2026-09-30 |
| CCO — Contact Center Operations | `text-embedding-3-small` | 2026-09-30 |
| MCC — Marketing & Client Communications | `text-embedding-3-small` | 2026-09-30 |
| ITS — Corporate IT Service Desk | `text-embedding-3-small` | 2026-09-30 |
