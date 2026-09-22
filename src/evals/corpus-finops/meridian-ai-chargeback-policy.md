---
title: AI Platform Chargeback Policy
doc_id: meridian-ai-chargeback-policy
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

# AI Platform Chargeback Policy

**Effective 1 January 2026**

## 1. Model

Meridian AI Platform (MAP) operates on **chargeback**, not showback. Metered consumption
is posted to the consuming business unit's cost centre and appears in its
financial results. A business unit cannot decline a charge for
consumption it originated.

## 2. Platform uplift

Metered consumption is charged with an uplift of
**8.0%**. The uplift recovers shared
platform cost — gateway compute, evaluation and monitoring, the
governance function, and on-call — and is reviewed annually.

```
billed = metered x 1.08
```

Budgets, variance reporting, and the thresholds in
`meridian-ai-budget-quota-policy` are all expressed in **billed** terms.
Usage statements report both figures; they are not interchangeable.

## 3. Attribution

Consumption is attributed by the tags described in
`meridian-ai-usage-tagging-standard`. Untagged consumption is charged to
the platform's own cost centre for the period in which it occurs and is
not reallocated retrospectively.

## 4. Incident credits

Where a cost anomaly review concludes that excess consumption was caused
by a platform defect, the excess over the affected unit's prior-month
baseline is credited to that unit. Credits are settled quarterly as a
separate line and are never netted against a monthly statement, so the
statement continues to reflect what was actually consumed.

## 5. Disputes

A business unit may dispute a statement within **15 business days** of
issue. Disputes raised after that window are not considered. A dispute
does not suspend the charge.

## 6. Rate changes

Rate card changes take effect prospectively on the stated effective date.
Consumption is always priced at the card in effect on the date of
consumption. No period is ever repriced.
