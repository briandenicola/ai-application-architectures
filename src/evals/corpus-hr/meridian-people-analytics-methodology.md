---
title: AI Adoption Analysis — Methodology and Limitations (2025)
doc_id: meridian-people-analytics-methodology
doc_type: methodology
effective_date: 2025-12-31
status: current
contains_pii: false
sensitivity: internal
owner: People Analytics
---

> **SYNTHETIC — DEMONSTRATION DATA ONLY.** Meridian Wealth Partners is a
> fictional firm. No person, salary, performance score, or employment
> record in this document describes a real individual.

# AI Adoption Analysis — Methodology and Limitations

This note governs how the 2025 AI adoption figures may be used. Any analysis,
briefing or recommendation drawing on the monthly adoption reports is expected
to be consistent with the limitations recorded here.

## 1. The study is observational. There is no control group.

Licences were issued through a staggered rollout, not assigned at random.

Of 3,500 employees, **0 were never
licensed at any point in 2025**. 3,043 employees switched from
unlicensed to licensed exactly once, 157 held a licence for the
whole year, and 300 show an intermittent pattern.

This has a consequence that is easy to miss. Because no group remained
unlicensed, **the unlicensed employee-months are not a comparison group of
people — they are earlier months belonging to the same people.** A comparison
described as "licensed versus unlicensed staff" is in fact a comparison of
early 2025 against late 2025, and carries every seasonal, organisational and
headcount change that occurred in between.

Licences first issued, by month:

| Month | Employees first licensed |
|---|---:|
| January 2025 | 165 |
| February 2025 | 1,309 |
| March 2025 | 746 |
| April 2025 | 943 |
| May 2025 | 302 |
| June 2025 | 34 |
| July 2025 | 1 |
| August 2025 | 0 |
| September 2025 | 0 |
| October 2025 | 0 |
| November 2025 | 0 |
| December 2025 | 0 |

## 2. Adoption is confounded with function

Rollout sequence tracked department. Any difference between licensed and
unlicensed populations is therefore also a difference between functions, and
the two cannot be separated with this data.

| Department | Licensed share of employee-months | Active headcount |
|---|---:|---:|
| Engineering | 92.0% | 935 |
| Data & Analytics | 91.8% | 488 |
| Sales | 75.2% | 804 |
| Human Resources | 75.1% | 324 |
| Marketing | 74.8% | 318 |
| Product | 74.3% | 329 |
| Executive | suppressed (n<5) | suppressed (n<5) |

## 3. The licence flag does not mean "uses AI"

7,296 of 7,335 unlicensed employee-months
(99.5%) record at least one AI query.

Query volume differs substantially — licensed months average
23.5 queries against
3.1 for unlicensed months — but the
unlicensed group is a **lower-usage** group, not a zero-usage one. Treating it
as "staff who do not use AI" overstates the contrast.

## 4. `ai_hours_saved_est` is a modelled estimate, not a measurement

The field name carries `_est` for a reason. It is produced by a per-interaction
savings model, not observed in any timesheet, and it has never been validated
against measured output.

It must not be presented as realised time, realised capacity or realised cost
saving. Three limitations apply:

- It values every estimated hour as an hour redeployed to productive work.
  No redeployment has been measured.
- It is computed for every metered employee-month, including months belonging
  to employees who have since left the firm.
- It is not reconcilable with the measured hours in section 5.

## 5. Measured hours show no material difference

For completeness, and because it is the obvious check on section 4:

| Population | Employee-months | Mean monthly active hours |
|---|---:|---:|
| Licensed months | 34,665 | 175.31 |
| Unlicensed months | 7,335 | 174.73 |
| Difference | — | +0.58 |

A difference of +0.58 hours per month, in observational data with no
adjustment for function, tenure or seasonality, does not support a claim that
licensing changed how much people worked. It is also not evidence that the
programme had no effect — hours worked is an attendance measure, and neither
direction is established by this dataset.

## 6. Active hours are an attendance proxy

`total_monthly_active_hours` is derived from system activity. It measures
presence, not output, not quality, and not value. It should not be described
as productivity.

## 7. Small groups are suppressed

Any figure covering fewer than 5 people must be withheld. With
7 departments and 7 seniority levels, several
department-by-level cells contain one person, and a mean over one person is
that person's record.

Suppression also survives arithmetic. Where a small group is withheld from a
breakdown but the firm-wide total is published, the withheld figure must not be
recovered by subtraction.

## 8. Not every metered row belongs to an active employee

3,612 employee-months belong to staff whose status is
Terminated or Leave. Per-capita figures must state which population they use;
dividing an annual total by active headcount silently mixes the two.

## What this analysis cannot answer

- Whether AI licensing caused any change in performance or output.
- What the programme's return on investment was.
- Whether any individual's output changed.

These are not gaps that more careful statistics on this dataset would close.
They require a randomised or staged-comparison design that was not run.
