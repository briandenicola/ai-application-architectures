# Copilot Instructions — ai-application-architectures

## What this repository is

Reference architectures and working samples for agentic AI applications on Azure.

| Path | Contents |
|------|----------|
| `infrastructure/` | **Terraform** modules for Foundry, Agent Service, AI Hub, OpenAI — including managed-VNet and private-endpoint variants. Driven by `Taskfile.yaml`. |
| `src/` | Runnable samples: Semantic Kernel, AutoGen, LangChain, Prompt Flow, hosted agents |
| `src/evals/` | **Self-contained** Foundry Evaluations demo. Bicep + azd, not Terraform. See its own README and ADR-0001 for why. |

## General conventions

- Terraform + Taskfile is the house standard for infrastructure. `src/evals/` is a
  documented exception, not a precedent.
- Keyless auth throughout: Entra ID and managed identity. Do not introduce
  connection strings, account keys, or SAS tokens.
- Never emit a key, SAS, or connection string as an IaC output.
- No real customer data in any sample. Synthetic only.

## Working in `src/evals/`

Read these first — they are the contract, not background reading:

1. `src/evals/.specify/memory/constitution.md` — non-negotiables and the ship gate
2. `src/evals/specs/001-foundry-evals-demo/spec.md` — scope and open questions
3. `src/evals/specs/001-foundry-evals-demo/contracts.md` — output, RBAC, exit-code and payload contracts

### Rules that are enforced by tests — do not work around them

- **Agent parity.** `agents/v1-naive.agent.yaml` and `v2-hardened.agent.yaml` may
  differ *only* in `instructions` and `knowledge.retrieval`. Changing the model,
  temperature, seed or knowledge base on one and not the other invalidates the
  demo's central claim. `tests/test_agent_parity.py` will fail.
- **Exit codes are load-bearing.** `0` pass, `1` quality threshold breached,
  `2` harness cannot run. Never collapse 1 and 2 — that is how a gate stops
  protecting anything.
- **Never use `pytest.importorskip` in `tests/test_gate.py`.** A skipped gate test
  is indistinguishable from a passing one.
- **Synthetic identifiers use reserved-for-fiction formats only**: SSN area `000`,
  phone `(212) 555-01xx`, email `@example.com`.
- **Dataset tag distribution is fixed** (10/5/4/4/4/3). Adding a case means
  updating the invariant in `tests/test_dataset.py` deliberately.
- Python target is **3.10**. Do not let a linter rewrite `datetime.timezone.utc`
  to `datetime.UTC` (ruff `UP017`) — it breaks the azd hook on 3.10 runtimes.

### Before claiming a guard works

Break it, watch the check fail, revert, confirm green, and record it in
`docs/tamper-log.md`. An untested guard is an assumption. This is a constitution
requirement, not a style preference.

### Verification commands

```bash
cd src/evals
python -m ruff check . && python -m ruff format --check .
python -m pytest              # 35 tests, no Azure needed
az bicep build --file infra/main.bicep --stdout > /dev/null
```

## Things to ask about rather than assume

- Any command that touches Azure or provisions resources.
- The target region and model availability — `centralus` availability for
  `gpt-5.5` / `gpt-5.4-mini` is an open item.
- Deleting anything.
