"""Selecting a subset must not quietly select a different one.

`--cases` exists because `--limit` takes whichever cases happen to be first,
which is rarely the set worth paying for. The risk it introduces is a run that
looks complete and covers less than it claims -- so a case id that is not in
the dataset has to be an error, not a smaller dataset.
"""

from __future__ import annotations

import json

import pytest
from conftest import DATASET

from seed_dataset import to_eval_items


def _ids(payload: str) -> list[str]:
    return [json.loads(line)["case_id"] for line in payload.strip().splitlines()]


def test_cases_selects_exactly_what_was_asked_for():
    payload = to_eval_items(DATASET, None, ["MWP-003", "MWP-001"])
    assert _ids(payload) == ["MWP-001", "MWP-003"], "selection keeps dataset order"


def test_an_unknown_case_id_is_an_error():
    with pytest.raises(SystemExit) as excinfo:
        to_eval_items(DATASET, None, ["MWP-001", "MWP-999"])
    assert excinfo.value.code == 2, "a mis-typed case id is a harness failure, not a gate one"


def test_selecting_nothing_is_an_error():
    with pytest.raises(SystemExit):
        to_eval_items(DATASET, None, [])


def test_limit_still_takes_the_first_n():
    assert len(_ids(to_eval_items(DATASET, 3))) == 3


def test_no_subset_publishes_everything():
    full = _ids(to_eval_items(DATASET))
    assert len(full) == len(DATASET.read_text(encoding="utf-8").strip().splitlines())
