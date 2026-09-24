# Run of Show — AI Platform FinOps — 30 minutes

> ### Verified 2026-09-24
>
> Both versions have now been run end to end, twice on the 8-case demo set and
> once on the full 25-case set. The central claim is a measurement, not an
> expectation:
>
> | | Naive (v1) | Hardened (v2) |
> |---|---|---|
> | 8-case set, run twice | 0.88-0.92, 4-5 fail, **exit 1** | 1.00, 0 fail, **exit 0** |
> | Full 25-case set | 0.92, 7 fail, **exit 1** | 1.00, 0 fail, **exit 0** |
>
> The earlier "hang" was two separate bugs, both ours. First we polled
> `result_counts.total`, which stays `0` until a run completes, and read that
> as no progress (#6, #8). Then full runs died on exit 2 with "Response is a
> required input and cannot be None" — a 429 that Foundry does not pass through
> as a rate limit. The agent deployment was at capacity 50 against a
> subscription quota of 1000 (#17).
>
> **The dataset was cut from 25 cases to 8 on 2026-09-24.** Two whole failure
> modes never fired on either agent. If you are reading an older version of
> this document, MAP-015 and MAP-020 no longer exist.

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
| **MAP-009** | Budget question. Quotes **$50.00** as "the current rate card" for gpt-5.5 output. |
| **MAP-010** | Repricing question. Quotes **$40.00 / 1M output, $10 / 1M input** as "current gpt-5.5 prices". |
| **MAP-011** | Repricing question. Quotes **$50.00 / 1M output, $12.50 / 1M input** as "current gpt-5.5 rates". |

**This is the moment. Put all three on screen together.**

> "Same agent. Same corpus. Same afternoon. Three people asked what our current
> gpt-5.5 price is and got three different answers — fifty dollars, forty
> dollars, fifty dollars again with a different input rate. Every one of them
> is sourced. Every one cites a document. Two of them are the superseded
> card."

> "Nobody in this room would catch that, because you would never ask the same
> question three times. You would ask once, get a confident sourced answer,
> and put it in a budget."

Then MAP-016, which is the other failure mode:

| Case | What v1 does |
|---|---|
| **MAP-016** | Asked for gpt-5.5's billed cost *alone* for one business unit. Produces **$8,230.05** from "$7,620.42 metered × 1.08". The statements publish billed cost per cost centre, not per model — so the input to that multiplication is not in any document. |

> "The arithmetic is right. The uplift is right. The starting number does not
> exist. That is the hardest class of error to catch by reading, because
> everything around it checks out."

Point at the groundedness column: **2.0** on MAP-009, MAP-010 and MAP-016.
That is a built-in Foundry evaluator, not our rubric, independently reaching
the same conclusion.

**Then, unprompted, give away the weak part.** Somebody in that room is paid to
find it, and it is much better coming from you:

> "We planted six failure modes. This naive agent handled three of them on its
> own — it refused to hand over an owner's desk phone, it blamed a platform
> incident rather than demand growth, and it read 'charged' as billed without
> being told to. So we graded a full twenty-five cases, watched two of those
> modes never fire once, and cut the set to eight."

> "We deleted our own test cases because they weren't proving anything. That's
> in the commit history if you want it."

> "Which tells you something useful: the model's own training already covers
> refusal. What it does not cover is arithmetic authority. That's where you
> have to do the work, and it's exactly the part that survives a code review."

**Say the numbers:** relevance and intent resolution pass. Groundedness and the
defensibility rubric do not. **Exit code 1.**

Expect four or five of the eight to fail. It moved between our two runs, and
one control failed on one of them — v1's answer was right but uncited, and the
attribution dimensions scored it down. If that happens live, say so: a correct
answer you cannot trace is a weaker answer, and the rubric is entitled to say
so.

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

Open the v2 run. Same 8 cases. Then show v2's answers to the same questions:

| Case | v2 |
|---|---|
| **MAP-009** | **$40.00**, and names the card — `meridian-model-rate-card-2026-01, effective 2026-01-01`. Then refuses to give a generic billed figure, because billed cost is uplift applied per cost centre and the rate card does not carry one. |
| **MAP-010 / MAP-011** | Prices each period at **the card that applied to that billing period**, named with its effective date — not "current prices". |
| **MAP-016** | **"I can't find Wealth Advisory Support's billed cost for gpt-5.5 alone."** Then shows what *is* published: $7,620.42 metered for that model, and billed only at cost-centre level, $8,595.19 for all WAS models combined. |

MAP-016 is the one to dwell on. Put v1 and v2 side by side:

> "v1 gave you $8,230.05. v2 says the number doesn't exist, and then shows you
> the two real numbers either side of the gap — the metered figure for that
> model, and the billed figure for the whole cost centre."

> "That second answer is more work to read and it is the only one you could
> defend in an audit. The first one would have gone into a chargeback report
> and nobody would have queried it."

And on MAP-010 and MAP-011, the recency point:

> "Notice what changed. v1 said 'current prices'. v2 says 'the rate card that
> applied to that billing period', and names it. You do not reprice a closed
> month because a new card came out in January — and the difference between
> those two habits is about four thousand dollars on one business unit."

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
