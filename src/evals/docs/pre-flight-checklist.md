# Pre-Flight Checklist

Run this **10 minutes before** the meeting, not 10 seconds before. Total time
about 4 minutes.

```bash
cd src/evals
source .venv/bin/activate
```

## 1. Environment is alive — 30s

```bash
azd env get-values | grep -E "AZURE_AI_PROJECT_ENDPOINT|AZURE_SEARCH_ENDPOINT|AZURE_SEARCH_INDEX"
```

☐ All three populated. If empty: `azd env refresh`.

## 2. Model deployments are present — 30s

```bash
az cognitiveservices account deployment list \
  --name "$AZURE_AI_FOUNDRY_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  -o table
```

☐ `gpt-5.5`, `gpt-4.1-mini`, `text-embedding-3-large` all `Succeeded`.

## 3. Corpus is intact — 30s

```bash
curl -s -H "Authorization: Bearer $(az account get-access-token \
    --resource https://search.azure.com --query accessToken -o tsv)" \
  "$AZURE_SEARCH_ENDPOINT/indexes/meridian-docs/docs/\$count?api-version=2026-04-01"
```

☐ Returns `12`.

## 4. Knowledge base is healthy — 60s

```bash
python scripts/setup_knowledge.py
```

Idempotent, so it is safe to re-run. It re-asserts both post-conditions.

☐ Index `meridian-docs` holds 12/12 documents
☐ **Canary passed** — the current fee schedule outranks the superseded one

> If the canary fails, stop. The stale-document segment is the spine of the demo
> and it will not work. Do not present until this is green.

## 5. Both agents exist — 30s

```bash
cat .azure/agents.json
```

☐ `meridian-advisor-v1` and `meridian-advisor-v2` both present with ids.
If missing: `python scripts/create_agents.py`.

## 6. Local suite is green — 15s

```bash
python -m pytest -q
```

☐ 35 passed. This catches a corpus or dataset edit you forgot about.

## 7. Portal is warm — 60s

☐ Foundry portal open and authenticated
☐ Knowledge base page loaded
☐ v1 and v2 evaluation runs open in tabs, **side-by-side comparison already rendered**
☐ Playground open on v2

> Pre-loading the comparison view is worth the minute. Navigating to it live is
> the slowest part of the demo.

## 8. Fallbacks ready — 30s

☐ `docs/fallback/` results open in an editor
☐ Screenshots of the red and green scorecards accessible offline

## 9. Terminal ready — 15s

Staged, not executed:

```bash
python scripts/run_eval.py --agent meridian-advisor-v1 ; echo "exit=$?"
```

☐ Font size legible from the back of the room (16pt+)
☐ Working directory is `src/evals`
☐ Virtualenv active

---

## Abort criteria

Do not present live if any of these are true. Use the fallback assets instead.

- The canary in step 4 fails.
- Fewer than 12 documents are indexed.
- A model deployment is not in `Succeeded`.
- `pytest` is not green.

A demo that fails in front of a risk-and-compliance audience does more damage
than a demo delivered from screenshots. There is no shame in the fallback.
