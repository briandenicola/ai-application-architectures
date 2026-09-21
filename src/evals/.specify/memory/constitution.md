# Constitution — Foundry Evals Demo (Wealth Management)

> Governing document for `src/evals`. Every spec, PR, and generated artifact in this
> directory must conform. When a decision conflicts with this file, this file wins.

## Mission

Prove that Microsoft Foundry Evaluations catch ungrounded, non-compliant, and
stale-source answers from a wealth-management advisor agent **before a client ever
sees them** — demonstrated live, in the Foundry portal, in 45 minutes.

## Audience

Mixed room of client architects / AI leads and risk & compliance stakeholders at
financial services firms. Open with the business story; drill into configuration and
code on demand.

## Non-Goals

Explicitly out of scope. Do not add these, even if they would be "nice to have".

1. **Not a production wealth-management product.** No real advice engine, no CRM,
   no portfolio accounting, no trading.
2. **Not a multi-agent orchestration demo.** Prompt agents only — they are legible
   in the portal and that is the point.
3. **Not a fine-tuning or model-training demo.**
4. **Not a network-security demo.** Public endpoints with Entra RBAC. Private
   endpoints are a different conversation with a different deck.
5. **Not a red-team / jailbreak demo.** Safety evaluators are available but the
   staged failures are quality and compliance failures, not adversarial attacks.
6. **No custom UI.** The Foundry portal and the terminal are the UI.

## Non-Negotiables

1. **Zero real data.** Every document, client name, account number, and figure is
   synthetic and clearly labeled as such. Synthetic PII uses reserved-for-fiction
   formats only (`555-01xx` phone, `000-00-xxxx` SSN, `example.com` email).
2. **Keyless.** Managed identity and Entra RBAC for every service-to-service call.
   No API keys, connection strings, or secrets in the repo, in `azure.yaml`, or in
   Bicep outputs. `AZURE_*` endpoints only.
3. **One command.** `azd up` provisions and configures the entire demo from a clean
   subscription with no manual portal steps.
4. **Reproducible.** Seeded dataset, pinned model versions and API versions,
   temperature fixed. Two runs of the same agent against the same dataset must
   produce the same verdicts.
5. **Clean teardown.** `azd down --purge` leaves nothing behind, including
   soft-deleted Foundry/Cognitive Services accounts.
6. **The gate actually blocks.** A failing evaluation exits non-zero. A gate that
   only prints warnings is a lie and must not be demoed.

## Realism Checklist

The demo must survive a skeptical FSI architect asking "would this work at my firm?".

| # | Dimension | Requirement |
|---|-----------|-------------|
| R1 | **Data** | Corpus mirrors real advisory artifacts: fund fact sheets, a versioned fee schedule, an Investment Policy Statement, required-disclosure language, a KYC/suitability policy. Includes at least one **superseded** document still present in the container. |
| R2 | **Data quality** | Corpus contains a document with synthetic client PII, because real document estates always do. The agent must be evaluated on whether it leaks it. |
| R3 | **Identity** | Managed identity + Entra RBAC end to end; least-privilege role assignments, scoped to resource not subscription. |
| R4 | **Integration** | Grounding via Foundry IQ knowledge base over Azure Blob Storage — the same pattern a firm would use over an existing document estate, not an ad-hoc file upload. |
| R5 | **Compliance constraint** | The agent is not licensed to give personalized investment advice and must carry required disclosure language. This is encoded as a graded rubric, not a hope. |
| R6 | **Versioning constraint** | Answers must cite the *current* effective document. Stale-source answers are a gate failure. |
| R7 | **Operational constraint** | Evaluation is runnable both interactively (portal) and non-interactively (`azd ai agent eval run`), so it can move into a release pipeline. |
| R8 | **Cost constraint** | Full demo environment is disposable and cheap enough to stand up per-engagement. Document the estimated run cost. |

## Engineering Guardrails

- **IaC:** Bicep, deployed by `azd`. No portal-authored resources. Existing
  Terraform under `infrastructure/` is reference material, not a dependency.
- **Language:** Python 3.11+ for scripts, hooks, and custom graders.
  `pyproject.toml`, `ruff` for lint+format, `pyright` (basic) for types.
- **Determinism:** Pin the Foundry API version, model versions, and evaluator
  versions explicitly. Never use `latest`.
- **Idempotency:** Every post-provision hook is safe to re-run. Creating an agent,
  knowledge source, or knowledge base that already exists is an update, not an error.
- **Config over constants:** Region, resource names, model deployment names, CIDRs,
  and thresholds come from `azd` environment variables or `evals.config.yaml`.
  Nothing environment-specific is hardcoded in source.
- **Artifacts:** Agent definitions (v1/v2), the golden dataset, and evaluator config
  are version-controlled files, diffable in a PR.

## Security & Privacy Guardrails

- No secrets committed. `gitleaks` runs in the quality gate.
- Storage account: public blob access disabled, shared-key auth disabled, TLS 1.2
  minimum. Access is via RBAC data-plane roles only.
- Role assignments are least-privilege and resource-scoped:
  `Storage Blob Data Reader`, `Search Index Data Reader`, `Search Service Contributor`,
  `Cognitive Services User`, `Azure AI User`.
- Every synthetic document carries a `SYNTHETIC — DEMONSTRATION DATA ONLY` banner in
  its first 200 characters, so a screenshot can never be mistaken for client data.
- The planted-PII document is used to *test for leakage*; the demo narrative must
  explicitly explain why it exists.
- Diagnostic and evaluation output may contain model responses — treat the Log
  Analytics workspace as demo-only and delete it on teardown.

## Quality Gate — Definition of Done

A change to `src/evals` is done when all of the following hold.

**Ship gate (the numbers on screen):**

| Metric | Threshold |
|--------|-----------|
| Groundedness | ≥ 4.0 / 5 |
| Relevance | ≥ 4.0 / 5 |
| Retrieval | ≥ 3.5 / 5 |
| Intent Resolution | ≥ 4.0 / 5 |
| Task Adherence | ≥ 4.0 / 5 |
| Compliance rubric (custom) | 100 % pass |

**Engineering gate:**

1. `ruff check` and `ruff format --check` pass.
2. `pyright` reports no errors.
3. `pytest` unit tests for the custom graders and dataset schema pass.
4. `az bicep build` / `az deployment group validate` succeeds.
5. `gitleaks detect` finds nothing.
6. `azd up` on a clean environment succeeds unattended, and `azd down --purge`
   removes everything.
7. The v1 agent **fails** the ship gate and the v2 agent **passes** it — this
   contrast is a tested invariant, not an anecdote.

**Tamper test (required):** for each staged failure mode, deliberately break the
corresponding guard, confirm the eval flips to fail, then revert. A guard that has
never been observed failing is not a guard.

## Context Discipline

- `specs/001-foundry-evals-demo/` is the single source of truth for what gets built.
- Changes to scope update the spec first, code second.
- Assumptions are labeled `ASSUMPTION:` inline and tracked in `spec.md § Open Questions`.
- ADRs in `docs/adr/` record decisions that were genuinely contested (IaC choice,
  knowledge-source strategy, agent-versioning strategy).
