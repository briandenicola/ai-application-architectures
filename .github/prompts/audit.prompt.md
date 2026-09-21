---
mode: agent
description: Adversarial audit of the evals demo — look for guards that do not guard.
---

Audit for the failure that matters most here: **a control that is asserted but
not enforced.** Assume every claim in the documentation is false until the code
proves it.

Work through these, and for each one either cite the enforcing line or report it
as unenforced.

## The gate
- Does `scripts/run_eval.py` actually exit non-zero on a breached threshold?
  Trace `summarise()` end to end.
- Are exit codes 1 (quality failure) and 2 (harness broken) genuinely distinct on
  every path? Find any `except` that could convert a crash into a pass.
- Could any test in `tests/test_gate.py` be skipped rather than run?

## The dataset
- Do the 10 control cases actually detect over-refusal, or would an agent that
  refuses everything still pass? Check what the thresholds do in that case.
- Does any case have an expected citation that does not resolve to a real file?

## The corpus
- Is every identifier in a reserved-for-fiction format? Check every document, not
  just the one that declares `contains_pii`.
- Do the two fee schedules genuinely contradict each other? If they agree, the
  stale-document segment is theatre.

## Identity and secrets
- Is any RBAC assignment broader than its documented justification?
- Does any Bicep output contain a key, SAS or connection string?
- Is `allowSharedKeyAccess` / `disableLocalAuth` actually set, or only documented?

## Documentation honesty
- Does any document describe a guard whose row in `docs/tamper-log.md` is empty?
  Those are assumptions being presented as controls. List them.
- Does `README.md` claim anything the test suite does not verify?

Report findings as: severity / file:line / claim / reality. Propose fixes but do
not apply them.
