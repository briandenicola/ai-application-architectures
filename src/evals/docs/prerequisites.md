# Prerequisites

## Tooling

Pin these. The `azd ai agent eval` surface is in preview and has moved before.

| Tool | Version | Check |
|------|---------|-------|
| Azure Developer CLI (`azd`) | ≥ 1.20.0 | `azd version` |
| Azure CLI (`az`) | ≥ 2.77.0 | `az version` |
| Bicep CLI | ≥ 0.40.0 | `az bicep version` |
| `azd` AI extension | latest | `azd extension list` |
| Python | ≥ 3.10 | `python3 -V` |

Install the AI extension (provides `azd ai agent eval`):

```bash
azd extension install microsoft.azd.ai
```

> **T0.2 — record the exact versions you validated against here before the first
> client engagement.** "Latest" is not a pin.

## Azure

| Requirement | Notes |
|-------------|-------|
| Subscription with Contributor + User Access Administrator | The RBAC module creates role assignments; Contributor alone is not enough |
| Region | `centralus` by default — **verify model availability first (T0.1)** |
| Model quota | `gpt-5.5` 50k TPM, `gpt-4.1-mini` 100k TPM, `text-embedding-3-large` 50k TPM |

### Verified in `centralus` (2026-09-21)

All three models deploy on **`GlobalStandard`**. `Standard` is *not* offered for
`text-embedding-3-large` there — a deployment specifying it fails preflight.

| Model | Version | SKU |
|---|---|---|
| `gpt-5.5` | `2026-04-24` | GlobalStandard |
| `gpt-4.1-mini` | `2025-04-14` | GlobalStandard |
| `text-embedding-3-large` | `1` | GlobalStandard |

Model versions and SKUs are region-specific. Re-run the checks below when you
change region — a version that exists in one region often does not in another.

| Resource providers | `Microsoft.CognitiveServices`, `Microsoft.Search`, `Microsoft.OperationalInsights`, `Microsoft.Insights` |

### Verify region and quota before you commit (T0.1)

```bash
# Are the models available in the target region?
az cognitiveservices model list \
  --location centralus \
  --query "[?contains(model.name,'gpt-5.5') || contains(model.name,'gpt-4.1-mini')].{name:model.name,version:model.version,sku:model.skus[0].name}" \
  -o table

# Is there quota for them?
az cognitiveservices usage list --location centralus -o table
```

If `centralus` does not carry the models or the quota, set a different region and
record the change:

```bash
azd env set AZURE_LOCATION eastus2
```

Model names and versions are parameters on `infra/main.bicep`; override them the
same way rather than editing Bicep.

## Local setup

```bash
cd src/evals
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

### Windows note

On machines with a restrictive PowerShell execution policy, the `.ps1` shims that
pip installs are blocked. Invoke interpreters directly:

```powershell
& .\.venv\Scripts\python.exe -m pytest
& .\.venv\Scripts\python.exe scripts\run_eval.py --agent meridian-advisor-v2
```

`scripts/postprovision.ps1` already does this.

## Verify before deploying

```bash
az bicep build --file infra/main.bicep      # template compiles
python -m ruff check .                       # lint
python -m pytest                             # full suite, no Azure required
python scripts/generate_finops_corpus.py --check   # committed corpus is current
python scripts/build_finops_golden.py --check      # committed dataset is current
```

These run without a subscription. Everything they can catch, they catch before
you spend money.

## Known constraints

| Item | Status |
|------|--------|
| `azd ai agent eval` | Preview. CLI surface may change; re-verify before each engagement. |
| Foundry IQ knowledge sources / bases | Created via REST in a post-provision hook, not Bicep. See `docs/adr/0002-knowledge-base-via-rest.md`. |
| RBAC propagation | The post-provision hook waits 60s. Role assignments are not always immediately effective; without the wait the first data-plane call intermittently 403s. |
| Soft-delete | Foundry accounts soft-delete on `azd down`. Use `--purge`; `scripts/verify_teardown.py` checks. |
| `AZURE_SEARCH_FINOPS_INDEX` | Set by `infra/main.bicep` (default `meridian-aiops-costs`) and consumed by both FinOps agent YAMLs. An environment provisioned before this output existed must set it manually: `azd env set AZURE_SEARCH_FINOPS_INDEX meridian-aiops-costs`. |
| `AZURE_SEARCH_HR_INDEX` | Set by `infra/main.bicep` (default `meridian-people-analytics`) and consumed by both HR agent YAMLs. An environment provisioned before this output existed must set it manually: `azd env set AZURE_SEARCH_HR_INDEX meridian-people-analytics`. |
| Shared model quota | All three demo tracks share one `gpt-5.5` deployment. Six evaluation runs plus playground use will trip a 429 on default quota. Run evaluations ahead of a demo, not during. |
| `docs/$count` consistency | Azure AI Search document counts are eventually consistent and lag a push by seconds. `index_corpus.py` polls rather than reading once; do not replace it with a single read. |
