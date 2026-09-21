---
mode: agent
description: Verify the evals demo is actually in a good state — not just that files exist.
---

Run the checks, then report. Do not fix anything until the report is complete and
I have chosen what to fix.

```bash
cd src/evals
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
az bicep build --file infra/main.bicep --stdout > /dev/null
```

Then verify these by inspection, because a passing test run does not prove them:

- [ ] `tests/test_gate.py` imports `run_eval` directly — **no `importorskip`**
- [ ] No test in the suite is skipped. Report the count explicitly.
- [ ] The dataset still has 30 cases with distribution 10/5/4/4/4/3
- [ ] `corpus/` still has exactly 12 documents
- [ ] v1 and v2 still differ only in `instructions` and `knowledge.retrieval`
- [ ] No key, SAS or connection string appears in any Bicep output
- [ ] Every row of `docs/tamper-log.md` that claims a proven guard has a date

Report as a table: check / result / evidence. Where something fails, quote the
actual output rather than describing it.

Flag loudly if the number of passing tests has *decreased* since the last
checkpoint, even if everything still reports green.
