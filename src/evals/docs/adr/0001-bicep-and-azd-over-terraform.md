# ADR-0001: Bicep and azd for this demo, despite a Terraform repository

- **Status:** Accepted
- **Date:** 2026-09-21
- **Deciders:** @briandenicola

## Context

Everything else in this repository under `infrastructure/` is Terraform, driven
by `Taskfile.yml`. That is the established convention and it works.

Two things pull the other way for this particular artifact:

1. The demo's stated constraint is **one command to stand up, one to tear down**,
   in front of a mixed business-and-technical audience. `azd up` is that command.
   Terraform needs a state backend decision, a `plan`, and an `apply` — a
   reasonable workflow, but three more things to explain to a room that came to
   see evaluations.
2. The evaluation tooling itself (`azd ai agent eval`) is an `azd` extension, and
   `azd` expects `azure.yaml` with hooks. Using Terraform for infrastructure and
   `azd` for the agent lifecycle means two tools and two state models for one
   45-minute demo.

## Decision

Use Bicep with `azd` for this demo only. The Terraform modules under
`infrastructure/` remain the pattern for anything intended to be operated.

## Consequences

### Positive
- `azd up` / `azd down --purge` — literally one command each.
- Post-provision hooks give a natural home for the Foundry IQ REST calls that
  cannot be expressed declaratively (see ADR-0002).
- No state backend to provision, secure, or explain.

### Negative
- Two IaC languages in one repository. A reader may reasonably wonder which is
  the house standard.
- Bicep modules here are not reusable by the Terraform stacks.
- Slightly weaker drift detection than `terraform plan`.

### Neutral
- The Azure resources and the RBAC model are identical either way. The decision
  is about the driver, not the target.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Terraform + Taskfile, matching the repo | The demo becomes a lesson in Terraform workflow. State backend setup in front of a client is time spent on the wrong thing. |
| Terraform for infra, `azd` for agents only | Two state models, two failure modes, one demo. The teardown story fragments. |
| Portal click-through, no IaC | Not reproducible. Fails the "reproducible" non-negotiable, and an architect in the room will notice. |

## Revisit when

Someone wants to run this pattern as a durable environment rather than a
demo — at that point the Terraform modules under `infrastructure/` are the right
starting point, and `docs/day-2.md` describes the production controls to add.
