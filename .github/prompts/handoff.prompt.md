---
mode: agent
description: Produce a handoff summary for the next person or session working on the evals demo.
---

Write a handoff covering exactly these sections. Be concrete; "mostly working" is
not a status.

## 1. State
What is complete and verified. Include the current test count and lint status.

## 2. In flight
Anything half-finished, with the specific file and line where it stops.

## 3. Unverified assumptions
Every claim in the code that has not been checked against a live environment.
Start from open questions O1–O6 in `specs/001-foundry-evals-demo/spec.md` and the
empty rows in `docs/tamper-log.md`.

Be explicit about the Foundry IQ REST payload shapes and the `azure-ai-projects`
SDK calls — both are best-effort and neither has been run.

## 4. Decisions made and why
Point at the ADRs. If a decision was made that has no ADR, say so — that is a gap.

## 5. Landmines
Things that will bite the next person:

- ruff `UP017` rewriting `timezone.utc` → `datetime.UTC` and breaking Python 3.10
- `pytest.importorskip` silently disabling the gate tests
- Bicep model deployments must be chained with `dependsOn`; concurrent writes are
  rejected by Cognitive Services
- `azd down` without `--purge` leaves a soft-deleted Foundry account that blocks
  redeployment under the same name

## 6. Next three actions
Ordered, specific, each with the command or file to start from.

## 7. What needs the user
Anything touching Azure, spending money, or deleting something.
