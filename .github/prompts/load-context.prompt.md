---
mode: agent
description: Load the full working context for the Foundry evals demo before making changes.
---

Read, in this order, and summarise what you learned from each in one line:

1. `src/evals/.specify/memory/constitution.md` — the non-negotiables and the ship gate
2. `src/evals/specs/001-foundry-evals-demo/spec.md` — scope, user stories, open questions O1–O6
3. `src/evals/specs/001-foundry-evals-demo/contracts.md` — Bicep outputs, RBAC, agent parity, exit codes
4. `src/evals/specs/001-foundry-evals-demo/tasks.md` — what is done and what remains
5. `src/evals/docs/tamper-log.md` — which guards are proven and which are still assumptions

Then report:

- **Current state:** what exists and is green
- **Open questions:** which of O1–O6 are still unresolved
- **Unproven guards:** every empty row in the tamper log
- **Blocked on the user:** anything requiring Azure access or an explicit decision

Do not change any file during this prompt. Report only.
