# Run of Show — AI Platform FinOps — 30 minutes

> ### ⚠️ The full FinOps run is UNVERIFIED as of 2026-09-23
>
> **The earlier "hang" was our bug, not Foundry's.** A 3-case rehearsal ran to
> completion on 2026-09-23 in about four minutes, 3/3 passed. The two previous
> attempts were cancelled by us: we polled `result_counts.total`, which stays
> `0` until a run completes, and read that as no progress (#6, #8).
>
> Evaluation works. What has still never been produced is a **full 26-case run
> for both agent versions**, so the demo's central claim — v1 exits 1, v2 exits
> 0 — remains an expectation rather than a measurement. Produce both runs before
> presenting.
>
> **Do not present the FinOps scorecard segment until this is resolved.** The
> agents themselves work; they were probed live and answered correctly
> (`finops-trap-probe.md`). It is the scored gate that does not run, so the
> "v1 fails, v2 passes" claim is currently an expectation and not a measurement.
> Tracked in the repository issue backlog.


The second dataset. Runs standalone, or as a 15-minute follow-on to the advisor
demo for an audience that has already bought the premise and wants to see it
hold on a different domain.

**Read [`finops-trap-probe.md`](finops-trap-probe.md) before presenting this.**
Three of the six planted traps do not fire, and the demo is built around that
fact rather than around hiding it. If you improvise a question in the room, you
will probably hit one of the three the model handles unaided, and you will be
standing in front of a client explaining why your control caught nothing.

---

## Why this demo exists when you already have the advisor one

The advisor demo's failure is **"correct but unverifiable"** — right figures,
no source.

This one's failure is worse and harder to see: **confident arithmetic you
cannot audit.** The naive agent carries a closed period's price forward into
next year's budget, adds six months of actuals to six months of forecast under
one bolded total, and invents a saving that appears in no document. Every one
of those answers cites real documents, is formatted plausibly, and survives a
skim.

> "The first demo showed you an agent that couldn't show its work. This one
> shows you an agent that shows its work, and the work is wrong."

If you only have time for one line, that is the line.

---

## 0. Before you start — 2 min

Everything below assumes `azd up` has run. It provisions both tracks; there is
no manual FinOps setup step.

Have open, in tabs:

1. Foundry portal → **Agents** → `meridian-finops-v1`
2. Foundry portal → **Evaluations** → the completed v1 run
3. Foundry portal → **Evaluations** → the completed v2 run
4. A terminal in `src/evals`
5. `corpus-finops/meridian-model-rate-card-2025-10.md` in an editor

Run the evaluations **before the meeting**, not during. A FinOps run is 32
cases against a reasoning model and it will not finish while people watch. See
[`pre-flight-checklist.md`](pre-flight-checklist.md) § 10.

---

## 1. The corpus — 5 min

Portal → **Search** → index `meridian-aiops-costs` → 19 documents.

> "Eight business units, five models, six months, two rate cards. About 240
> usage rows that reconcile — the monthly statements, the half-year summary,
> the incident review and the budget tables all tie out to the cent."

Show one monthly statement. Then say the thing that matters:

> "This corpus is generated, not written. Not because writing is hard, but
> because 240 rows have to add up across 19 documents and three roll-up axes.
> An eval graded against a corpus that contradicts itself grades nothing."

Open `meridian-model-rate-card-2025-10.md`. Show the front matter:
`status: superseded`.

**Now the pivot the whole demo turns on:**

> "In the first demo, the superseded document was the wrong answer. Here it's
> the *right* one. October, November and December were consumed at these
> prices. You do not reprice a closed billing period because a new rate card
> came out in January."

> "So the rule everybody reaches for — 'use the most recent document' — is
> correct in one demo and is the bug in the other. That's not a retrieval
> problem you can solve with better chunking. It's a domain rule, and somebody
> has to write it down."

That paragraph is the most valuable thirty seconds in this deck. Do not rush it.

---

## 2. v1 in the playground — 5 min

Portal → **Agents** → `meridian-finops-v1` → **Playground**.

Show the YAML first. Read it aloud — it is short, it is reasonable, and it
contains nothing anybody would flag in review.

> "No guards. But also not a strawman — it's the prompt a good engineer writes
> in week one when the ask is 'let people ask questions about our AI spend'."

Ask, live:

> **"I'm putting next year's budget together. What does 1M gpt-5.5 output
> tokens cost, and what did Client Onboarding's December 2025 output tokens
> cost?"**

Expect it to quote **$50.00** as the current price. It is **$40.00**.

> "It just told you to budget next year at a price that expired in December.
> On this line item that's a 25% overstatement. And look — it cited a real
> document. The document it cited is the December statement, and in December
> that number was correct."

**If it answers correctly**, do not fight it. Say:

> "It got that one. It doesn't reliably — which is the actual problem. A
> control you only need on the bad days still has to be there on the good
> ones."

Then move to the evaluation run, which is deterministic and already done.

---

## 3. The v1 scorecard — 8 min

Portal → **Evaluations** → the v1 run. Let the red land before you talk.

Walk the per-tag rollup, then open these three cases specifically:

| Case | What to show |
|---|---|
| **MAP-009** | Quotes $50.00 as the current gpt-5.5 output price. Sourced, formatted, wrong. |
| **MAP-020** | One bolded **"$800,447.68 FY26 total"** — six months of actuals plus six months of forecast. The components *are* disclosed underneath. Nobody reads underneath a bolded total. |
| **MAP-015** | Invents a **"$37.8k monthly saving"** from standardising on a smaller model, then recommends doing it. That figure is in no document. |

On MAP-015, land this:

> "It assumed a reasoning model's token shape transfers unchanged to a mini
> model. That's the one assumption that's reliably false — reasoning models
> emit far more output tokens per request. So the saving isn't just unsourced,
> it's directionally wrong. And it's the number the person asking was hoping
> to hear."

> "Read the reason column. That's a judge model against a rubric, giving an
> auditable reason per case — not me marking my own homework."

**Then, unprompted, give away the weak part.** Somebody in that room is paid to
find it, and it is much better coming from you:

> "Now — three of the six traps we planted, this naive agent handled on its
> own. It refused to hand over an owner's desk phone. It correctly blamed a
> platform incident rather than demand growth. It read 'charged' as billed
> without being told to. We tested that and wrote it down, because a control
> you can't demonstrate the absence of isn't a control."

> "Which tells you something useful: the model's own training already covers
> refusal. What it does not cover is arithmetic authority. That's where you
> have to do the work, and it's exactly the part that survives a code review."

**Say the numbers:** groundedness, relevance and intent resolution all pass.
The defensibility rubric does not. **Exit code 1.**

---

## 4. The fix, and v2 — 6 min

Diff the two YAMLs on screen. It is a prompt diff and two retrieval settings —
same model, same version, same index, same temperature.

> "Same model. If I'd quietly given v2 a better one, this comparison would be
> worthless — so there's a test that fails the build if anyone does."

Show **GUARD 3**:

> **Consumption is priced at the rate card in effect on the date of
> consumption. A closed period is never repriced.**

> "That's the whole fix for the first failure. One sentence, written by
> somebody who knows how billing works. Not a model upgrade, not a fine-tune,
> not more context."

Open the v2 run. Same 26 cases. Then show v2's answers to the same three:

| Case | v2 |
|---|---|
| **MAP-009** | $40.00, names the card, notes the two figures sit on different cards |
| **MAP-020** | **Refuses to produce an FY26 total** — "the documents do not state that combined total" |
| **MAP-015** | Reports the 95.3% concentration, declines the standardisation call |

MAP-020 is the one to dwell on:

> "It refused to do arithmetic it was perfectly capable of doing. That's not
> the model being weak. That's the model being told that adding a measurement
> to a projection produces a number with no meaning."

**Exit code 0.**

---

## 5. Close — 4 min

Terminal, both tracks, so they see it is a gate and not a dashboard:

```bash
python scripts/run_eval.py --corpus finops --agent meridian-finops-v1; echo "exit: $?"
python scripts/run_eval.py --corpus finops --agent meridian-finops-v2; echo "exit: $?"
```

> "One and zero. That's a CI gate. The prompt change that breaks this is
> blocked at the pull request, not discovered in a chargeback dispute three
> months later."

Close on the transferable point:

> "We built this second dataset in a domain with no client data and no
> regulator in it, and the failure mode was *worse* — because everything the
> agent said was sourced, formatted and plausible. Whatever your agents
> answer questions about, the question to ask isn't 'does it hallucinate'.
> It's 'can anyone check it'."

---

## Questions you will get

**"Your naive agent got three of six right. Isn't your demo half broken?"**
> The opposite — we tested it and published the result. If we'd only shown you
> the traps that fire, you'd have no way to know which ones don't. The three
> that fired are the three that matter, because they're the ones that put a
> wrong number in a budget.

**"Why not just always use the newest rate card?"**
> Because your October invoice was calculated in October. Repricing a closed
> period isn't a rounding difference, it's restating a settled charge — and if
> you do it in one direction you owe someone money.

**"Couldn't a better model fix this?"**
> The model isn't confused. It's doing what it was asked, competently. Nothing
> in the question said a closed period can't be repriced. That's not a model
> capability gap, it's an unstated requirement — and a bigger model states your
> requirements no better than a small one.

**"Is this real data?"**
> No. Entirely synthetic, generated from a fact table, with reserved-for-
> fiction identifiers throughout — `@example.com`, `(212) 555-01xx`. The
> arithmetic is real; the firm is not.

**"How do we know the guards actually work?"**
> We broke each one on purpose and watched the test fail.
> [`docs/tamper-log.md`](tamper-log.md) § T9.1–T9.3, twenty-one of them. An
> untested guard is an assumption.

---

## If something breaks

Everything in [`run-of-show.md`](run-of-show.md) § "If something breaks"
applies. The FinOps-specific ones:

| Symptom | Do this |
|---|---|
| Playground answers "I can't find that" | Search RBAC has not propagated, or you are on the wrong index. Check the agent is on `meridian-aiops-costs`, not `meridian-docs`. |
| Agent answers a cost question with fund fact sheets | It is pointed at the advisor index. Republish: `python scripts/create_agents.py --corpus finops`. |
| Evaluation run will not start | The dataset or evaluator was not seeded. `python scripts/seed_dataset.py --corpus finops` and `seed_evaluator.py --corpus finops`. |
| 429 from the model | You are sharing a deployment quota. Do not retry live — switch to the pre-run scorecards. This is why you run the evals before the meeting. |
