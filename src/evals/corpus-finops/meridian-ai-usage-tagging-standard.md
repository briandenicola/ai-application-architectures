---
title: AI Platform Usage Tagging Standard
doc_id: meridian-ai-usage-tagging-standard
doc_type: reference
effective_date: 2025-10-01
supersedes: null
status: current
contains_pii: false
owner: AI Platform Engineering
---

> **SYNTHETIC — DEMONSTRATION DATA ONLY.** Meridian Wealth Partners is a
> fictional firm and the Meridian AI Platform does not exist. No token count,
> price, cost centre, or person in this document is real.

# Usage Tagging Standard

**Effective 1 October 2025**

Every request to the AI Platform gateway carries the tags below. Tags are
what make attribution possible; a request that cannot be attributed cannot
be charged to the unit that made it.

| Tag | Required | Example | Purpose |
|---|---|---|---|
| `bu` | Yes | `CSV` | Business unit code. Drives chargeback. |
| `cost_center` | Yes | `CC-4315` | Finance posting code. |
| `workload` | Yes | `surveillance-escalation` | Workload identity. |
| `environment` | Yes | `prod` | `prod`, `uat`, or `dev`. |
| `session_id` | Yes | opaque | Per-session cost ceilings. |
| `agent_version` | No | `v3.2.1` | Attributing a cost regression. |

## Enforcement

The gateway rejects a request missing any required tag. Consumption that
reaches the meter without a valid `bu` tag — which can happen only for
platform-internal traffic — is charged to the platform cost centre and is
not reallocated later.

## Non-production

`uat` and `dev` consumption is metered and charged on the same rate card
as `prod`. There is no development discount. Budgets in
`meridian-ai-budget-quota-policy` cover all environments for the unit.
