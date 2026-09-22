---
title: AI Platform Usage & Cost Statement — February 2026
doc_id: meridian-ai-usage-2026-02
doc_type: usage_statement
effective_date: 2026-02-28
supersedes: null
status: current
contains_pii: false
owner: AI Platform FinOps
---

> **SYNTHETIC — DEMONSTRATION DATA ONLY.** Meridian Wealth Partners is a
> fictional firm and the Meridian AI Platform does not exist. No token count,
> price, cost centre, or person in this document is real.

# AI Platform Usage & Cost Statement — February 2026

**Billing period:** 2026-02-01 to 2026-02-28

**Rate card applied:** `meridian-model-rate-card-2026-01` (effective 2026-01-01)

Platform-wide, Meridian Wealth Partners consumed 11,223,303,000 tokens across
3,410,280 model requests in February 2026. Metered consumption was
$107,174.35; total charged to cost centres after the 8.0% platform
uplift was $115,748.31.

## Summary by business unit

| BU | Business unit | Cost centre | Requests | Tokens | Metered | Billed |
|---|---|---|---:|---:|---:|---:|
| WAS | Wealth Advisory Support | CC-4101 | 485,512 | 1,368,530,000 | $8,171.76 | $8,825.50 |
| COK | Client Onboarding & KYC | CC-4210 | 424,348 | 933,468,000 | $3,197.91 | $3,453.74 |
| CSV | Compliance Surveillance | CC-4315 | 622,352 | 3,791,592,000 | $67,761.57 | $73,182.50 |
| INR | Investment Research | CC-4402 | 336,304 | 1,810,278,000 | $14,368.96 | $15,518.48 |
| CCO | Contact Center Operations | CC-4508 | 968,123 | 1,383,216,000 | $2,112.07 | $2,281.04 |
| MCC | Marketing & Client Communications | CC-4620 | 136,998 | 412,952,000 | $347.11 | $374.88 |
| ITS | Corporate IT Service Desk | CC-4733 | 242,780 | 389,419,000 | $290.63 | $313.88 |
| ITD | Institutional Trading Desk | CC-4850 | 193,863 | 1,133,848,000 | $10,924.34 | $11,798.29 |
| **All** | **Platform total** | — | **3,410,280** | **11,223,303,000** | **$107,174.35** | **$115,748.31** |

## Summary by model

| Model | Requests | Tokens | Metered | Share of metered |
|---|---:|---:|---:|---:|
| `gpt-5.5` | 637,770 | 6,239,558,000 | $104,731.91 | 97.7% |
| `gpt-5.4-mini` | 1,113,290 | 3,224,924,000 | $2,163.12 | 2.0% |
| `gpt-4.1` | 15,748 | 47,401,000 | $124.33 | 0.1% |
| `text-embedding-3-large` | 724,533 | 1,097,860,000 | $142.73 | 0.1% |
| `text-embedding-3-small` | 918,939 | 613,560,000 | $12.26 | 0.0% |

## Detail by business unit and model

### WAS — Wealth Advisory Support (CC-4101)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.5` | 107,324 | 372,628,000 | 228,385,000 | 96,591,000 | $7,818.31 |
| `gpt-5.4-mini` | 148,209 | 277,447,000 | 78,254,000 | 62,248,000 | $320.56 |
| `text-embedding-3-large` | 229,979 | 252,977,000 | 0 | 0 | $32.89 |
| **Total** | **485,512** | **903,052,000** | **306,639,000** | **158,839,000** | **$8,171.76** |

Billed to CC-4101: **$8,825.50** (metered $8,171.76 + 8.0% uplift).

### COK — Client Onboarding & KYC (CC-4210)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.5` | 29,378 | 145,949,000 | 65,572,000 | 33,785,000 | $2,876.46 |
| `gpt-5.4-mini` | 133,833 | 232,334,000 | 182,548,000 | 69,593,000 | $317.38 |
| `text-embedding-3-small` | 261,137 | 203,687,000 | 0 | 0 | $4.07 |
| **Total** | **424,348** | **581,970,000** | **248,120,000** | **103,378,000** | **$3,197.91** |

Billed to CC-4210: **$3,453.74** (metered $3,197.91 + 8.0% uplift).

### CSV — Compliance Surveillance (CC-4315)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.5` | 288,949 | 1,497,914,000 | 351,362,000 | 1,304,606,000 | $67,514.74 |
| `gpt-5.4-mini` | 90,928 | 192,495,000 | 71,197,000 | 34,553,000 | $202.70 |
| `text-embedding-3-large` | 242,475 | 339,465,000 | 0 | 0 | $44.13 |
| **Total** | **622,352** | **2,029,874,000** | **422,559,000** | **1,339,159,000** | **$67,761.57** |

Billed to CC-4315: **$73,182.50** (metered $67,761.57 + 8.0% uplift).

Incident `MAP-INC-2026-0214` affected this period. See
`meridian-ai-cost-anomaly-2026-02` for the review and the credit
treatment.

### INR — Investment Research (CC-4402)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.5` | 100,071 | 745,326,000 | 235,366,000 | 160,113,000 | $14,093.15 |
| `gpt-5.4-mini` | 63,980 | 220,345,000 | 48,369,000 | 39,028,000 | $228.78 |
| `text-embedding-3-large` | 172,253 | 361,731,000 | 0 | 0 | $47.03 |
| **Total** | **336,304** | **1,327,402,000** | **283,735,000** | **199,141,000** | **$14,368.96** |

Billed to CC-4402: **$15,518.48** (metered $14,368.96 + 8.0% uplift).

### CCO — Contact Center Operations (CC-4508)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.4-mini` | 433,350 | 321,112,000 | 502,253,000 | 112,671,000 | $493.21 |
| `gpt-5.5` | 27,661 | 80,520,000 | 32,889,000 | 19,362,000 | $1,612.57 |
| `text-embedding-3-small` | 507,112 | 314,409,000 | 0 | 0 | $6.29 |
| **Total** | **968,123** | **716,041,000** | **535,142,000** | **132,033,000** | **$2,112.07** |

Billed to CC-4508: **$2,281.04** (metered $2,112.07 + 8.0% uplift).

### MCC — Marketing & Client Communications (CC-4620)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.4-mini` | 97,856 | 234,854,000 | 58,714,000 | 84,156,000 | $346.41 |
| `text-embedding-3-small` | 39,142 | 35,228,000 | 0 | 0 | $0.70 |
| **Total** | **136,998** | **270,082,000** | **58,714,000** | **84,156,000** | **$347.11** |

Billed to CC-4620: **$374.88** (metered $347.11 + 8.0% uplift).

### ITS — Corporate IT Service Desk (CC-4733)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.4-mini` | 115,484 | 104,282,000 | 138,235,000 | 39,265,000 | $165.10 |
| `gpt-4.1` | 15,748 | 34,802,000 | 6,142,000 | 6,457,000 | $124.33 |
| `text-embedding-3-small` | 111,548 | 60,236,000 | 0 | 0 | $1.20 |
| **Total** | **242,780** | **199,320,000** | **144,377,000** | **45,722,000** | **$290.63** |

Billed to CC-4733: **$313.88** (metered $290.63 + 8.0% uplift).

### ITD — Institutional Trading Desk (CC-4850)

| Model | Requests | Input tokens | Cached input | Output tokens | Metered |
|---|---:|---:|---:|---:|---:|
| `gpt-5.5` | 84,387 | 593,328,000 | 157,720,000 | 118,142,000 | $10,816.68 |
| `gpt-5.4-mini` | 29,650 | 89,661,000 | 17,078,000 | 14,232,000 | $88.98 |
| `text-embedding-3-large` | 79,826 | 143,687,000 | 0 | 0 | $18.68 |
| **Total** | **193,863** | **826,676,000** | **174,798,000** | **132,374,000** | **$10,924.34** |

Billed to CC-4850: **$11,798.29** (metered $10,924.34 + 8.0% uplift).

## Basis of preparation

Figures are derived from platform inference telemetry aggregated to the
cost centre recorded in `meridian-ai-cost-center-registry`. Token counts
are reported to the nearest thousand; metered cost is computed from the
reported token counts at the rate card named above. Statements are issued
after the reconciliation window described in
`meridian-ai-cost-disclosures` has closed.
