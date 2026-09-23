---
title: People Analytics — Data Dictionary
doc_id: meridian-people-analytics-data-dictionary
doc_type: reference
effective_date: 2025-01-01
status: current
contains_pii: false
sensitivity: internal
owner: People Analytics
---

> **SYNTHETIC — DEMONSTRATION DATA ONLY.** Meridian Wealth Partners is a
> fictional firm. No person, salary, performance score, or employment
> record in this document describes a real individual.

# People Analytics — Data Dictionary

## Grain

| Table | Grain | Rows |
|---|---|---:|
| Employee register | one row per employee | 3,500 |
| Monthly metrics | one row per employee per month | 42,000 |
| Compensation | one row per employee | 3,500 |
| Performance reviews | one row per employee per cycle | 7,000 |

Reporting period: January 2025 to December 2025
(12 months).

## Fields that are routinely misread

| Field | What it is | What it is not |
|---|---|---|
| `ai_license_active` | whether a licence was active that month | whether the employee used AI |
| `ai_queries_made` | metered queries that month | a measure of value or effort |
| `ai_hours_saved_est` | **modelled** estimate of time saved | measured or realised time |
| `total_monthly_active_hours` | system-derived attendance | productivity or output |
| `expected_monthly_hours` | contractual baseline, constant at 168 | a target or a quota |
| `status` | current employment status | status during the metered month |


## Status

`status` reflects the employee's position **today**, not during any given
reporting month. 3,612 employee-months belong to staff now
recorded as Terminated or Leave. Filter explicitly; state which population a
figure covers.

## Joins

All tables join on `employee_id`. Department, job title and location resolve
through the employee register. Every monthly row resolves to a known employee
and every employee carries exactly one compensation row.

## Date formats

The source extracts are not internally consistent: monthly and employee tables
use `M/D/YYYY`, daily activity uses ISO `YYYY-MM-DD`. Normalise on read.
