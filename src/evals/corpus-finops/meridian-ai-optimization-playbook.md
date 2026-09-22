---
title: AI Platform Cost Optimization Playbook
doc_id: meridian-ai-optimization-playbook
doc_type: reference
effective_date: 2026-02-15
supersedes: null
status: current
contains_pii: false
owner: AI Platform Engineering
---

> **SYNTHETIC — DEMONSTRATION DATA ONLY.** Meridian Wealth Partners is a
> fictional firm and the Meridian AI Platform does not exist. No token count,
> price, cost centre, or person in this document is real.

# Cost Optimization Playbook

**As of 15 February 2026**

Measures available to a business unit that needs to reduce AI Platform
spend, ordered by observed effect at Meridian. Figures are the ranges
measured on Meridian workloads and are not guarantees.

| # | Measure | Typical metered reduction | Effort |
|---:|---|---:|---|
| 1 | Route non-reasoning work to the volume tier | 30–60% | Medium |
| 2 | Stabilise prompt prefixes to raise cache hit rate | 8–18% | Low |
| 3 | Bound planner depth and tool-call count | 5–25% | Low |
| 4 | Trim retrieved context to the top 5 chunks | 6–12% | Low |
| 5 | Cap per-session tokens | 3–10% | Low |
| 6 | Batch embedding refresh rather than on-write | 2–5% | Medium |
| 7 | Shorten system prompts | 1–4% | Low |

## Routing

Routing is the dominant lever because the reasoning tier costs roughly
sixteen times the volume tier per output token under the January 2026
card. Classification, extraction, summarisation, and formatting do not
need the reasoning tier. Multi-step analysis and planning do.

## What is not a lever

Reducing output quality to save tokens is not an approved measure.
Neither is disabling evaluation or monitoring: both are recovered through
the platform uplift and are not optional for regulated workloads.

## Measuring

Effect is measured on billed cost per unit of business volume — cost per
onboarding case, per surveillance alert, per advisor session — not on
absolute monthly spend, which moves with demand.
