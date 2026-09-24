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

☐ All green. This catches a corpus, dataset or agent edit you forgot about.
The count grows as tracks are added — read the summary line, not a memorised
number.

## 6b. FinOps track — 90s

> ### Verified — but re-run it on the morning
>
> Both versions have been graded end to end: 8-case demo set twice, full
> 25-case set once. v1 exits 1 every time, v2 exits 0 every time. That claim
> is a measurement now.
>
> **The count of failures is not stable.** v1 failed 4 of 8 on one run and 5 of
> 8 on the next with nothing changed, and a control case failed on one of them.
> The verdict holds; the number moves. Run the gate on the morning of the demo
> and quote the number you actually got, not the one in the README.

**Skip only if you are certain the FinOps segment is not in this meeting.**
It is provisioned by `azd up` alongside the advisor track, so if it is missing
something went wrong with the deployment and you want to know now.

```bash
curl -s -H "Authorization: ****** account get-access-token \
    --resource https://search.azure.com --query accessToken -o tsv)" \
  "$AZURE_SEARCH_ENDPOINT/indexes/meridian-aiops-costs/docs/\$count?api-version=2026-04-01"

cat .azure/agents-finops.json
```

☐ Index `meridian-aiops-costs` returns `19`
☐ `meridian-finops-v1` and `meridian-finops-v2` both present with ids

> `docs/$count` on Azure AI Search is eventually consistent and lags a push by
> seconds. If it returns 0 immediately after an index run, wait and re-read
> before concluding anything is wrong.

**Both evaluation runs must already be complete.** The FinOps set is 8 cases
and finishes in two to three minutes, which is survivable but still not
something to do while an audience watches — and a live run gives you today's
numbers rather than yesterday's. The advisor set is 30 cases and definitely
will not finish in front of a room.

Do not run the two versions in parallel. They share a model deployment and
throttle each other.

☐ v1 FinOps run complete in the portal, **exit 1**, scorecard open in a tab
☐ v2 FinOps run complete in the portal, **exit 0**, scorecard open in a tab

> Neither box has ever been ticked. See the warning at the top of this section
> — if you cannot tick them, drop the FinOps scorecard segment and present the
> agent comparison from the playground instead.
☐ You have read [`finops-trap-probe.md`](finops-trap-probe.md)

> That last box is not administrative. Three of the six planted traps do not
> fire, and if you improvise a question in the room you will probably hit one
> of them. Know which three before you stand up.

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
- Fewer than 12 documents are indexed in `meridian-docs`.
- Fewer than 19 documents are indexed in `meridian-aiops-costs`, if the FinOps
  segment is in this meeting.
- A model deployment is not in `Succeeded`.
- `pytest` is not green.
- The FinOps evaluation runs are not already complete, if that segment is in
  this meeting. Starting one live is not a recoverable position.

A demo that fails in front of a risk-and-compliance audience does more damage
than a demo delivered from screenshots. There is no shame in the fallback.
