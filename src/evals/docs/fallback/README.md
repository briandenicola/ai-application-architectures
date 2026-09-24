# Fallback Assets

**This directory is intentionally empty of results.** It is populated from your
first successful live run, not fabricated.

That is a deliberate choice. A fallback that was hand-written to look like real
output is worse than no fallback: if you present it and someone asks a question
the numbers cannot answer, you are now improvising over invented evidence in
front of a compliance audience. Capture real output once and reuse it forever.

## What to capture, on your first green run

```bash
cd src/evals

python scripts/run_eval.py --agent meridian-advisor-v1   # exits 1
python scripts/run_eval.py --agent meridian-advisor-v2   # exits 0

# results/ is gitignored; fallback/ is not.
cp results/meridian-advisor-v1-*.json docs/fallback/v1-failing.json
cp results/meridian-advisor-v2-*.json docs/fallback/v2-passing.json
```

Also capture the terminal rendering, since the scorecard is what the room
actually looks at:

```bash
python scripts/run_eval.py --agent meridian-advisor-v1 | tee docs/fallback/v1-terminal.txt
python scripts/run_eval.py --agent meridian-advisor-v2 | tee docs/fallback/v2-terminal.txt
```

## Screenshots to take from the portal

Save alongside the JSON:

| File | What |
|------|------|
| `portal-v1-scorecard.png` | v1 evaluation run, metrics view, failures visible |
| `portal-v2-scorecard.png` | v2 evaluation run, same view |
| `portal-comparison.png` | The side-by-side comparison — the money shot |
| `portal-case-mwp-015.png` | The hallucinated fund, with the judge's reason text |
| `portal-case-mwp-024.png` | The stale fee schedule, showing which document was cited |
| `portal-knowledge-base.png` | The knowledge base with 12 documents indexed |

MWP-015 and MWP-024 are the two cases worth having as stills. They are the ones
people ask to see again.

## Using the fallback

If the live run fails, say so plainly and move to these. Do not debug on stage —
`docs/demo-guide.md` § 7 covers the transition. The argument does not depend on the
run happening live; it depends on the *contrast*, and that is fully present in
the captured output.

## Refresh when

- The dataset, thresholds, or either agent prompt changes
- The model versions change
- More than a quarter has passed — stale screenshots of a preview portal UI get
  noticed
