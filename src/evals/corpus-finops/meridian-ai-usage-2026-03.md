---
title: AI Platform Usage & Cost Statement — March 2026
doc_id: meridian-ai-usage-2026-03
doc_type: usage_statement
effective_date: 2026-03-31
supersedes: null
status: current
contains_pii: false
owner: AI Platform FinOps
---

> **SYNTHETIC — DEMONSTRATION DATA ONLY.** Meridian Wealth Partners is a
> fictional firm and the Meridian AI Platform does not exist. No token count,
> price, cost centre, or person in this document is real.

# AI Platform Usage & Cost Statement — March 2026

**Billing period:** 2026-03-01 to 2026-03-31

**Rate card applied:** `meridian-model-rate-card-2026-01` (effective 2026-01-01)

Platform-wide, Meridian Wealth Partners consumed 9,336,558,000 tokens across
3,344,103 model requests in March 2026. Metered consumption was
$53,361.76; total charged to cost centres after the 8.0% platform
uplift was $57,630.68.

## Summary by business unit

| BU | Business unit | Cost centre | Requests | Tokens | Metered | Billed |
|---|---|---|---:|---:|---:|---:|
| WAS | Wealth Advisory Support | CC-4101 | 478,460 | 1,348,653,000 | $8,053.06 | $8,697.30 |
| COK | Client Onboarding & KYC | CC-4210 | 441,338 | 970,841,000 | $3,325.93 | $3,592.00 |
| CSV | Compliance Surveillance | CC-4315 | 485,979 | 1,602,293,000 | $11,818.61 | $12,764.10 |
| INR | Investment Research | CC-4402 | 379,414 | 2,042,344,000 | $16,210.93 | $17,507.80 |
| CCO | Contact Center Operations | CC-4508 | 957,250 | 1,367,683,000 | $2,088.38 | $2,255.45 |
| MCC | Marketing & Client Communications | CC-4620 | 139,186 | 419,547,000 | $352.66 | $380.87 |
| ITS | Corporate IT Service Desk | CC-4733 | 263,785 | 423,112,000 | $315.77 | $341.03 |
| ITD | Institutional Trading Desk | CC-4850 | 198,691 | 1,162,085,000 | $11,196.42 | $12,092.13 |
| **All** | **Platform total** | — | **3,344,103** | **9,336,558,000** | **$53,361.76** | **$57,630.68** |

## Summary by model

| Model | Requests | Tokens | Metered | Share of metered |
|---|---:|---:|---:|---:|
| `gpt-5.5` | 484,552 | 4,156,898,000 | $50,825.49 | 95.2% |
| `gpt-5.4-mini` | 1,140,599 | 3,328,419,000 | $2,235.86 | 4.2% |
| `gpt-4.1` | 17,110 | 51,502,000 | $135.08 | 0.3% |
| `text-embedding-3-large` | 767,866 | 1,175,781,000 | $152.84 | 0.3% |
| `text-embedding-3-small` | 933,976 | 623,958,000 | $12.49 | 0.0% |

## Detail by business unit and model

### WAS — Wealth Advisory Support (CC-4101)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.5` | 105,765 | 367,216,000 | 225,067,000 | 95,188,000 | $7,704.75 |
| `gpt-5.4-mini` | 146,056 | 273,417,000 | 77,118,000 | 61,344,000 | $315.90 |
| `text-embedding-3-large` | 226,639 | 249,303,000 | 0 | 0 | $32.41 |
| **Total** | **478,460** | **889,936,000** | **302,185,000** | **156,532,000** | **$8,053.06** |

Billed to CC-4101: **$8,697.30** (metered $8,053.06 + 8.0% uplift).

### COK — Client Onboarding & KYC (CC-4210)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.5` | 30,554 | 151,793,000 | 68,197,000 | 35,137,000 | $2,991.61 |
| `gpt-5.4-mini` | 139,191 | 241,636,000 | 189,857,000 | 72,379,000 | $330.08 |
| `text-embedding-3-small` | 271,593 | 211,842,000 | 0 | 0 | $4.24 |
| **Total** | **441,338** | **605,271,000** | **258,054,000** | **107,516,000** | **$3,325.93** |

Billed to CC-4210: **$3,592.00** (metered $3,325.93 + 8.0% uplift).

### CSV — Compliance Surveillance (CC-4315)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.5` | 121,495 | 629,828,000 | 147,737,000 | 127,569,000 | $11,548.78 |
| `gpt-5.4-mini` | 99,405 | 210,440,000 | 77,834,000 | 37,774,000 | $221.59 |
| `text-embedding-3-large` | 265,079 | 371,111,000 | 0 | 0 | $48.24 |
| **Total** | **485,979** | **1,211,379,000** | **225,571,000** | **165,343,000** | **$11,818.61** |

Billed to CC-4315: **$12,764.10** (metered $11,818.61 + 8.0% uplift).

### INR — Investment Research (CC-4402)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.5` | 112,899 | 840,872,000 | 265,539,000 | 180,638,000 | $15,899.78 |
| `gpt-5.4-mini` | 72,181 | 248,593,000 | 54,569,000 | 44,031,000 | $258.10 |
| `text-embedding-3-large` | 194,334 | 408,102,000 | 0 | 0 | $53.05 |
| **Total** | **379,414** | **1,497,567,000** | **320,108,000** | **224,669,000** | **$16,210.93** |

Billed to CC-4402: **$17,507.80** (metered $16,210.93 + 8.0% uplift).

### CCO — Contact Center Operations (CC-4508)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.4-mini` | 428,483 | 317,507,000 | 496,612,000 | 111,406,000 | $487.68 |
| `gpt-5.5` | 27,350 | 79,616,000 | 32,519,000 | 19,145,000 | $1,594.48 |
| `text-embedding-3-small` | 501,417 | 310,878,000 | 0 | 0 | $6.22 |
| **Total** | **957,250** | **708,001,000** | **529,131,000** | **130,551,000** | **$2,088.38** |

Billed to CC-4508: **$2,255.45** (metered $2,088.38 + 8.0% uplift).

### MCC — Marketing & Client Communications (CC-4620)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.4-mini` | 99,419 | 238,605,000 | 59,651,000 | 85,500,000 | $351.94 |
| `text-embedding-3-small` | 39,767 | 35,791,000 | 0 | 0 | $0.72 |
| **Total** | **139,186** | **274,396,000** | **59,651,000** | **85,500,000** | **$352.66** |

Billed to CC-4620: **$380.87** (metered $352.66 + 8.0% uplift).

### ITS — Corporate IT Service Desk (CC-4733)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.4-mini` | 125,476 | 113,306,000 | 150,195,000 | 42,662,000 | $179.38 |
| `gpt-4.1` | 17,110 | 37,814,000 | 6,673,000 | 7,015,000 | $135.08 |
| `text-embedding-3-small` | 121,199 | 65,447,000 | 0 | 0 | $1.31 |
| **Total** | **263,785** | **216,567,000** | **156,868,000** | **49,677,000** | **$315.77** |

Billed to CC-4733: **$341.03** (metered $315.77 + 8.0% uplift).

### ITD — Institutional Trading Desk (CC-4850)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.5` | 86,489 | 608,104,000 | 161,648,000 | 121,085,000 | $11,086.09 |
| `gpt-5.4-mini` | 30,388 | 91,893,000 | 17,504,000 | 14,586,000 | $91.19 |
| `text-embedding-3-large` | 81,814 | 147,265,000 | 0 | 0 | $19.14 |
| **Total** | **198,691** | **847,262,000** | **179,152,000** | **135,671,000** | **$11,196.42** |

Billed to CC-4850: **$12,092.13** (metered $11,196.42 + 8.0% uplift).

## Basis of preparation

Figures are derived from platform inference telemetry aggregated to the
cost centre recorded in `meridian-ai-cost-center-registry`. Token counts
are reported to the nearest thousand; metered cost is computed from the
reported token counts at the rate card named above. Statements are issued
after the reconciliation window described in
`meridian-ai-cost-disclosures` has closed.
