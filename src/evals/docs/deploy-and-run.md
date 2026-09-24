# Deploying and Running

Everything operational: provisioning, loading content, running the gate,
reading exit codes, and tearing down.

For what the demo *means* and how to present it, see
[`demo-guide.md`](demo-guide.md).

---

## 1. Deploy and load

### Prerequisites

- An Azure subscription with `Microsoft.CognitiveServices` quota in your target
  region
- `azd`, the Azure CLI, and Python 3.10
- Roughly 20 minutes for the first deployment

See [`prerequisites.md`](prerequisites.md) for exact versions and role
requirements.

### Provision

```bash
cd src/evals
azd auth login
azd up
```

This provisions a Foundry account and project, two model deployments, an Azure
AI Search service and Application Insights. Everything uses Entra ID and
managed identity — there are no keys, connection strings or SAS tokens
anywhere, and none are emitted as outputs. Worth pointing out to a security
audience; show `infra/modules/rbac.bicep` if challenged.

`azd up` provisions **all three tracks**. There is no manual per-track setup.

Then load the content and publish the agents:

```bash
# Index the documents into Azure AI Search
.venv/bin/python scripts/index_corpus.py --corpus finops

# Publish the two agents and smoke-test each one
.venv/bin/python scripts/create_agents.py --corpus finops

# Register the golden dataset and the rubric evaluator in Foundry
.venv/bin/python scripts/seed_dataset.py --corpus finops
.venv/bin/python scripts/seed_evaluator.py --corpus finops
```

Swap `--corpus finops` for `advisor` or `hr` for the other tracks.

### Check it before the room is watching

```bash
python -m pytest        # 334 tests, no Azure needed
```

Then work through [`pre-flight-checklist.md`](pre-flight-checklist.md). It
exists because the failure modes that ruin a demo — an unpublished agent, a
stale index, a dataset version that does not match the config — all look fine
until you run the thing live.

**Run the gate once, for real, before you present.** Live model output varies
between runs. You want to have seen today's numbers before your audience does.

---

## 2. Running the gate

```bash
# The naive agent
.venv/bin/python scripts/run_eval.py --corpus finops --agent meridian-finops-v1

# The hardened agent
.venv/bin/python scripts/run_eval.py --corpus finops --agent meridian-finops-v2
```

Each run takes two to three minutes on the 8-case FinOps set; the 30-case
advisor set takes longer. Both print a scorecard and write a JSON result file
under `results/`.

**Do not run them in parallel.** They share a model deployment and will
throttle each other.

**Do not run a full set live.** Run it before the meeting and open the stored
run in the portal. There is a cheap smoke run for the live terminal moment:

```bash
# 3 cases, labelled partial — can never be mistaken for a gate result
python scripts/run_eval.py --agent meridian-advisor-v1 --dataset-name meridian-smoke --limit 3
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Passed the gate |
| `1` | A quality threshold was breached — the agent is not fit to ship |
| `2` | The harness could not run — config error, auth failure, service problem |

`1` and `2` are deliberately distinct and must stay that way. Collapsing them
means a broken harness reports as a quality failure, and a gate that cannot
tell "this agent is bad" from "I did not actually check" is protecting nothing.
This is enforced by tests.

### If a run fails with exit 2

Most likely causes, in order:

1. **Stale environment** — re-run `eval "$(azd env get-values | sed 's/^/export /')"`
2. **Dataset version mismatch** — the version in `evals.config.yaml` must match
   what is registered in Foundry
3. **Throttling** — if the error says `Response is a required input and cannot
   be None`, that is a 429 that Foundry did not pass through as a rate limit.
   Check the capacity on your model deployment. This cost two full runs before
   it was understood.

---

## 3. Tear down

```bash
azd down --purge
```

`--purge` matters. Without it the Foundry account is soft-deleted and its name
stays reserved, so redeploying into the same environment fails with a name
conflict that does not mention soft deletion.
