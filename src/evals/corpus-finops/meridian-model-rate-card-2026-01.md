---
title: Meridian AI Platform — Model Rate Card (January 2026)
doc_id: meridian-model-rate-card-2026-01
doc_type: rate_card
effective_date: 2026-01-01
supersedes: meridian-model-rate-card-2025-10
status: current
contains_pii: false
owner: AI Platform FinOps
---

> **SYNTHETIC — DEMONSTRATION DATA ONLY.** Meridian Wealth Partners is a
> fictional firm and the Meridian AI Platform does not exist. No token count,
> price, cost centre, or person in this document is real.

# Model Rate Card — January 2026

**Effective 2026-01-01**

Internal transfer prices charged by Meridian AI Platform (MAP) to consuming business
units. All figures are US dollars per 1,000,000 tokens.

| Model | Tier | Input / 1M | Cached input / 1M | Output / 1M |
|---|---|---:|---:|---:|
| `gpt-5.5` | chat | $10 | $1 | $40.00 |
| `gpt-5.4-mini` | chat | $0.6 | $0.06 | $2.40 |
| `gpt-4.1` | chat | $2 | $0.5 | $8.00 |
| `text-embedding-3-large` | embedding | $0.13 | $0.13 | n/a |
| `text-embedding-3-small` | embedding | $0.02 | $0.02 | n/a |

## How consumption is priced

Metered cost for a model in a billing period is:

```
cost = (uncached_input_tokens x input_rate
        + cached_input_tokens x cached_input_rate
        + output_tokens       x output_rate) / 1,000,000
```

The rate card **in effect on the date of consumption** applies. A billing
period is never repriced against a later card.

Embedding models produce no output tokens; the output column does not
apply to them.

## Cached input

Cached input is prompt content served from the provider's prompt cache. It
is metered separately and priced at a tenth of the uncached input rate for
the reasoning and volume tiers. Cache hit rates are a property of the
workload, not of the platform, and are not guaranteed.

## Scope

This card covers model inference only. Search, storage, orchestration
compute, network egress, and human review are billed under separate
schedules and do not appear in AI Platform usage statements.
