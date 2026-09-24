"""Model capacity is a correctness setting, not a cost knob.

#17 cost two failed 26-case FinOps runs before anyone questioned the number.
The template default of 50 was never chosen -- and when it was exceeded,
Foundry did not report a quota error. The evaluator received a null response
and the harness exited 2 with "Response is a required input and cannot be
None", which reads like a harness defect rather than a rate limit.

That is the reason this file exists. A capacity too low to finish a run does
not announce itself, so the only cheap place to catch it is here, before
anyone pays for the run.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MAIN_BICEP = ROOT / "infra" / "main.bicep"

# Below this, a full-size dataset run is at risk. Derived from observation, not
# theory: 50 failed a 26-case FinOps run twice, and the advisor's 30 shorter
# cases passed at the same setting. The FinOps answers are long tables, so the
# binding constraint is tokens per case, not case count.
MINIMUM_CAPACITY = 200

# Subscription quota for GlobalStandard in centralus, checked 2026-09-24.
# Asserting a ceiling too keeps a well-meant bump from failing deployment with
# an InsufficientQuota error that looks nothing like its cause.
SUBSCRIPTION_QUOTA = {"agentModelCapacity": 1000, "judgeModelCapacity": 3000}


def _capacity(param: str) -> int:
    text = MAIN_BICEP.read_text(encoding="utf-8")
    match = re.search(rf"^param {param} int = (\d+)$", text, re.MULTILINE)
    assert match, f"{param} not found in main.bicep, or no longer has a literal default"
    return int(match.group(1))


@pytest.mark.parametrize("param", sorted(SUBSCRIPTION_QUOTA))
def test_capacity_is_high_enough_to_finish_a_full_run(param):
    capacity = _capacity(param)
    assert capacity >= MINIMUM_CAPACITY, (
        f"{param} is {capacity}. 50 was the template default and it silently "
        "killed two full FinOps runs -- Foundry hands the evaluator a null "
        "response on a 429 rather than reporting a rate limit, so the run "
        f"fails as exit 2 with no mention of quota. See #17. Minimum "
        f"{MINIMUM_CAPACITY}."
    )


@pytest.mark.parametrize("param", sorted(SUBSCRIPTION_QUOTA))
def test_capacity_stays_inside_subscription_quota(param):
    capacity = _capacity(param)
    quota = SUBSCRIPTION_QUOTA[param]
    assert capacity <= quota, (
        f"{param} is {capacity}, above the centralus quota of {quota}. "
        "Deployment fails with InsufficientQuota, which is a clearer error "
        "than the one above but still not one worth discovering during a demo."
    )
