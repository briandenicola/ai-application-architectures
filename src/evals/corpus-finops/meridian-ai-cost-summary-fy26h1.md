---
title: AI Platform Cost Summary — FY26 H1
doc_id: meridian-ai-cost-summary-fy26h1
doc_type: summary
effective_date: 2026-03-31
supersedes: null
status: current
contains_pii: false
owner: AI Platform FinOps
---

> **SYNTHETIC — DEMONSTRATION DATA ONLY.** Meridian Wealth Partners is a
> fictional firm and the Meridian AI Platform does not exist. No token count,
> price, cost centre, or person in this document is real.

# AI Platform Cost Summary — FY26 H1

**Period:** 2025-10-01 to 2026-03-31 (six months)

Across FY26 H1, Meridian Wealth Partners consumed 51,581,881,000 tokens across
18,385,699 model requests. Metered consumption was
$360,045.09 and total charged to cost centres was
$388,848.70.

Two rate cards apply to this period: `meridian-model-rate-card-2025-10`
for October through December 2025, and `meridian-model-rate-card-2026-01`
from January 2026. Month-over-month movements are therefore not
like-for-like across the December/January boundary.

## Billed cost by business unit and month

| BU | Oct 2025 | Nov 2025 | Dec 2025 | Jan 2026 | Feb 2026 | Mar 2026 | H1 total |
|---|---:|---:|---:|---:|---:|---:|---:|
| WAS | $8,809.25 | $8,595.19 | $9,072.57 | $7,848.11 | $8,825.50 | $8,697.30 | **$51,847.92** |
| COK | $3,987.67 | $4,131.66 | $4,077.21 | $3,540.55 | $3,453.74 | $3,592.00 | **$22,782.83** |
| CSV | $12,393.09 | $12,350.77 | $13,555.93 | $10,931.75 | $73,182.50 | $12,764.10 | **$135,178.14** |
| INR | $13,532.49 | $14,839.83 | $15,871.95 | $14,394.46 | $15,518.48 | $17,507.80 | **$91,665.01** |
| CCO | $2,602.71 | $2,646.60 | $2,566.36 | $2,362.62 | $2,281.04 | $2,255.45 | **$14,714.78** |
| MCC | $1,089.16 | $1,011.65 | $1,082.04 | $371.41 | $374.88 | $380.87 | **$4,310.01** |
| ITS | $346.12 | $359.89 | $347.47 | $342.28 | $313.88 | $341.03 | **$2,050.67** |
| ITD | $9,362.50 | $10,671.07 | $11,268.15 | $11,107.20 | $11,798.29 | $12,092.13 | **$66,299.34** |
| **All** | **$52,122.99** | **$54,606.66** | **$57,841.68** | **$50,898.38** | **$115,748.31** | **$57,630.68** | **$388,848.70** |

## Metered cost by model

| Model | Requests | Tokens | Metered | Share of metered |
|---|---:|---:|---:|---:|
| `gpt-5.5` | 2,668,965 | 23,414,111,000 | $343,034.21 | 95.3% |
| `gpt-5.4-mini` | 6,156,179 | 17,568,057,000 | $12,815.20 | 3.6% |
| `gpt-4.1` | 281,259 | 1,099,969,000 | $3,354.82 | 0.9% |
| `text-embedding-3-large` | 3,910,725 | 5,917,122,000 | $769.22 | 0.2% |
| `text-embedding-3-small` | 5,368,571 | 3,582,622,000 | $71.64 | 0.0% |
| **All** | **18,385,699** | **51,581,881,000** | **$360,045.09** | **100.0%** |

## Unit economics

| BU | Requests (H1) | Metered cost per request | Blended cost per 1M tokens |
|---|---:|---:|---:|
| WAS | 2,561,906 | $0.0187 | $6.65 |
| COK | 2,499,843 | $0.0084 | $3.84 |
| CSV | 2,692,072 | $0.0465 | $11.79 |
| INR | 1,795,223 | $0.0473 | $8.78 |
| CCO | 5,583,370 | $0.0024 | $1.71 |
| MCC | 781,806 | $0.0051 | $1.63 |
| ITS | 1,484,812 | $0.0013 | $0.80 |
| ITD | 986,667 | $0.0622 | $10.64 |

## Budget variance

| BU | H1 budget | H1 billed | Variance | Variance % |
|---|---:|---:|---:|---:|
| WAS | $57,000.00 | $51,847.92 | -$5,152.08 | -9.0% |
| COK | $26,400.00 | $22,782.83 | -$3,617.17 | -13.7% |
| CSV | $84,000.00 | $135,178.14 | +$51,178.14 | 60.9% |
| INR | $96,000.00 | $91,665.01 | -$4,334.99 | -4.5% |
| CCO | $17,400.00 | $14,714.78 | -$2,685.22 | -15.4% |
| MCC | $7,200.00 | $4,310.01 | -$2,889.99 | -40.1% |
| ITS | $2,400.00 | $2,050.67 | -$349.33 | -14.6% |
| ITD | $69,000.00 | $66,299.34 | -$2,700.66 | -3.9% |

## Monthly budget breaches

| Month | BU | Billed | Monthly budget | Overage |
|---|---|---:|---:|---:|
| February 2026 | CSV | $73,182.50 | $14,000 | $59,182.50 |
| February 2026 | ITD | $11,798.29 | $11,500 | $298.29 |
| March 2026 | INR | $17,507.80 | $16,000 | $1,507.80 |
| March 2026 | ITD | $12,092.13 | $11,500 | $592.13 |

Each breach triggers the review path in
`meridian-ai-budget-quota-policy`. Breaches attributable to a platform
incident are handled under the credit provisions of that policy rather
than as a consumer overage.

## Concentration

`gpt-5.5` accounts for 95.3% of metered
spend while representing a minority of requests. Spend concentration in
the reasoning tier is the dominant driver of platform cost and the primary
target of the measures in `meridian-ai-optimization-playbook`.

## Basis of preparation

This summary aggregates the six monthly statements
`meridian-ai-usage-2025-10` through `meridian-ai-usage-2026-03`.
Where this summary and a monthly statement disagree, the monthly statement
governs.
