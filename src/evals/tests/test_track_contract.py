"""Every registered track must survive the whole harness path.

Both bugs fixed in 913d432 were found by *running* the harness against a second
corpus. 135 tests were green and caught neither, because the suite proved the
`--corpus` swap worked for the blocks it knew about and nothing proved there
was nothing else that needed swapping. A module constant still pinned to the
advisor track stayed invisible until a second track ran.

So these tests iterate the corpora rather than naming them. A third track is
covered the day it appears in `evals.config.yaml`, which is the only way this
kind of test keeps paying for itself.

Azure is stubbed throughout; nothing here makes a network call.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_eval  # noqa: E402
from _common import CORPUS_KEYS, ConfigError, select_corpus  # noqa: E402

CONFIG_PATH = ROOT / "evals.config.yaml"


def _config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def registered_corpora() -> list[str]:
    """Derive the track list from config instead of hard-coding it.

    `dataset` with no suffix is the default track; every `dataset_<x>` is
    another. Deriving it is the point — a hard-coded list would pass forever
    while a new track went untested.
    """
    config = _config()
    extra = sorted(k.split("_", 1)[1] for k in config if k.startswith("dataset_"))
    return ["meridian", *extra]


CORPORA = registered_corpora()


def test_more_than_one_track_is_registered():
    """If this ever drops to one, these tests stop proving anything and the
    generic-harness claim is untested rather than true."""
    assert len(CORPORA) >= 2, f"only {CORPORA} registered"


@pytest.mark.parametrize("corpus", CORPORA)
def test_every_track_resolves_a_complete_config(corpus):
    config = select_corpus(_config(), corpus)
    for key in CORPUS_KEYS:
        assert key in config, f"'{corpus}' has no {key} block after the swap"
    assert config["dataset"]["name"]
    assert config["dataset"]["path"]
    assert config["evaluators"]["custom_metric"]
    assert config["thresholds"]


@pytest.mark.parametrize("corpus", CORPORA)
def test_every_track_walks_the_full_harness_path(corpus):
    """Criteria → metric → thresholds → parse → verdict, for each track."""
    config = select_corpus(_config(), corpus)

    criteria = run_eval.build_testing_criteria(config, judge_model="judge-deployment")
    assert criteria, f"'{corpus}' produced no testing criteria"

    metric = run_eval.custom_metric(config)
    assert metric

    assert run_eval.check_thresholds(config) == [], (
        f"'{corpus}' has thresholds that do not correspond to any evaluator"
    )

    builtins = list(config["evaluators"]["builtin"])
    results = [{"name": name, "passed": True, "score": 5.0} for name in builtins]
    results.append({"name": metric, "passed": True, "score": 5.0})
    item = {
        "datasource_item": {"case_id": "T-001", "failure_tag": "grounded_happy"},
        "results": results,
        "sample": {"output_text": "A grounded answer."},
    }

    case = run_eval.parse_case(item, metric)
    assert case["case_id"] == "T-001"
    assert case["verdict"] == "pass"
    assert case.get("evaluator_errors") in (None, {}), case.get("evaluator_errors")


@pytest.mark.parametrize("corpus", CORPORA)
def test_a_failing_case_fails_the_gate_on_every_track(corpus):
    """A track whose gate cannot say 'fail' is decoration.

    This is the check that would have caught the metric-name bug had the two
    rubrics happened to share a metric name: the FinOps gate would have been
    judged against the advisor's threshold and printed a clean scorecard.
    """
    config = select_corpus(_config(), corpus)
    metric = run_eval.custom_metric(config)

    results = [
        {"name": name, "passed": True, "score": 5.0} for name in config["evaluators"]["builtin"]
    ]
    results.append({"name": metric, "passed": False, "score": 1.0})
    item = {
        "datasource_item": {"case_id": "T-001", "failure_tag": "fabricated_number"},
        "results": results,
        "sample": {"output_text": "A confident fabrication."},
    }

    case = run_eval.parse_case(item, metric)
    assert case["verdict"] == "fail", (
        f"'{corpus}' reported pass on a case Foundry failed — this track's gate does not gate"
    )


@pytest.mark.parametrize("corpus", CORPORA)
def test_each_track_has_its_own_dataset_and_metric(corpus):
    """Two tracks sharing a dataset path or metric name means one of them is
    silently grading the other's work."""
    others = [c for c in CORPORA if c != corpus]
    mine = select_corpus(_config(), corpus)
    my_path = mine["dataset"]["path"]
    my_metric = mine["evaluators"]["custom_metric"]

    for other in others:
        theirs = select_corpus(_config(), other)
        assert theirs["dataset"]["path"] != my_path, (
            f"'{corpus}' and '{other}' both evaluate {my_path}"
        )
        assert theirs["evaluators"]["custom_metric"] != my_metric, (
            f"'{corpus}' and '{other}' both report under '{my_metric}', so one "
            "track's threshold is being applied to the other's rubric"
        )


@pytest.mark.parametrize("corpus", CORPORA)
def test_every_track_dataset_file_exists_and_is_populated(corpus):
    config = select_corpus(_config(), corpus)
    path = ROOT / config["dataset"]["path"]
    assert path.exists(), f"'{corpus}' points at a dataset that does not exist: {path}"
    assert run_eval.load_dataset(path), f"'{corpus}' dataset is empty"


def test_an_unknown_corpus_fails_loudly():
    """Silently returning the advisor config for a typo would produce a full,
    plausible, green scorecard for the wrong dataset."""
    with pytest.raises(ConfigError):
        select_corpus(_config(), "nosuchtrack")


# ─────────────────────────────────────────────────────────────────────────────
# The registries have to agree with each other
# ─────────────────────────────────────────────────────────────────────────────


def test_every_script_that_knows_about_corpora_knows_about_all_of_them():
    """`--corpus` is not one switch, it is several.

    `select_corpus` swaps dataset/evaluators/thresholds; `index_corpus` maps to
    a knowledge block; `create_agents` maps to an agents block. Adding a track
    means editing three registries, and nothing until now checked they agreed.
    A track registered in config but missing from `create_agents` fails at
    demo time, not at test time.

    The assertion is containment, not equality, and the direction matters. A
    corpus that is indexed before its golden set exists is a legitimate
    in-progress state — the HR track sat there for a day. A corpus that has a
    golden set but is missing from a script is not: it is an evaluable track
    whose corpus nobody can index or whose agents nobody can publish.

    `test_every_referenced_config_block_exists` covers the other direction by
    checking that whatever a script does know about resolves to real config.
    """
    import create_agents
    import index_corpus

    registries = {
        "index_corpus.CONFIG_SECTIONS": set(index_corpus.CONFIG_SECTIONS),
        "create_agents.CORPORA": set(create_agents.CORPORA),
    }
    expected = set(CORPORA)
    for label, known in registries.items():
        missing = expected - known
        assert not missing, (
            f"{label} does not know about {sorted(missing)}, but the config "
            f"registers a dataset for each. A track missing here fails at demo time."
        )


def test_every_referenced_config_block_exists():
    """The registries can agree with each other and still point at nothing."""
    import create_agents
    import index_corpus

    config = _config()
    for corpus, section in index_corpus.CONFIG_SECTIONS.items():
        assert section in config, f"index_corpus maps '{corpus}' to missing '{section}'"
    for corpus, sections in create_agents.CORPORA.items():
        for section in sections[:2]:
            assert section in config, f"create_agents maps '{corpus}' to missing '{section}'"


# The complete set of inputs a `type: rubric` evaluator accepts. This is
# generated by the SERVICE from the evaluator type — it is not authored in our
# YAML and cannot be extended. Read back from both published rubrics
# (meridian-finops-defensible-answer v2, meridian-compliance-safe-answer v4)
# on 2026-09-24. Anything mapped to a name outside this set is silently
# discarded: no error, no warning, the value simply never arrives.
RUBRIC_ACCEPTED_INPUTS = frozenset({"query", "response", "messages", "tool_definitions"})


@pytest.mark.parametrize("corpus", CORPORA)
def test_citation_mapping_is_wired_and_proven_inert(corpus):
    """The successor to the T20 guard, recording what it actually proved.

    T20 pinned the original defect: no evaluator received a citation column, so
    `forbidden_citations` passed for every agent forever. `3705444` mapped both
    columns into the custom rubric and shipped it marked UNVERIFIED, on the
    strength of the service accepting the keys and echoing them back.

    It was wrong. A three-arm controlled experiment
    (probes/citation_delivery_probe.py, 2026-09-24) sent the SAME canned
    response three times against a pinned rubric version confirmed to contain
    `citation_discipline`, varying only the citation metadata. All three arms
    scored 1.0 — and in every arm the judge praised the response for citing the
    very document one arm forbade.

    So this is T20 in better cover, exactly as the UNVERIFIED note feared: the
    columns are published, mapped, accepted and read by nothing.

    The mapping is deliberately LEFT IN PLACE so that this guard and
    `test_inert_rubric_inputs_are_documented_as_such` keep the finding visible.
    Deleting the mapping would make the repository look correct while the
    published rubrics still carry a dead weight-9 dimension.
    """
    config = select_corpus(_config(), corpus)
    criteria = run_eval.build_testing_criteria(config, judge_model="judge-deployment")

    metric = run_eval.custom_metric(config)
    rubric = next((c for c in criteria if c["name"] == metric), None)
    assert rubric is not None, f"'{corpus}' emits no custom rubric criterion"

    for field in ("expected_citations", "forbidden_citations"):
        assert rubric["data_mapping"].get(field) == f"{{{{item.{field}}}}}", (
            f"'{corpus}' does not map {field} into the rubric. If that was "
            "removed deliberately, restore the T20 guard rather than leaving "
            "the columns published and unread."
        )
        assert field not in RUBRIC_ACCEPTED_INPUTS, (
            f"{field} is now in the accepted-input set. If the service began "
            "accepting it, re-run probes/citation_delivery_probe.py and "
            "promote citation_discipline to a real control."
        )


@pytest.mark.parametrize("corpus", CORPORA)
def test_inert_rubric_inputs_are_documented_as_such(corpus):
    """An inert dimension must be labelled inert, in the code and in the docs.

    This is the guard the demo actually needs. The failure mode it protects
    against is not a broken mapping — it is a broken mapping that LOOKS fine,
    which is what shipped in `3705444` and what T20 caught before it.

    If a rubric input cannot be delivered, saying so next to the code is the
    only thing standing between that fact and a presenter claiming the
    dimension works.
    """
    config = select_corpus(_config(), corpus)
    criteria = run_eval.build_testing_criteria(config, judge_model="judge-deployment")
    metric = run_eval.custom_metric(config)
    rubric = next(c for c in criteria if c["name"] == metric)

    undeliverable = sorted(set(rubric["data_mapping"]) - RUBRIC_ACCEPTED_INPUTS)
    if not undeliverable:
        return

    source = (ROOT / "scripts" / "run_eval.py").read_text(encoding="utf-8")
    assert "PROVEN INERT" in source, (
        f"'{corpus}' maps {undeliverable}, which a rubric evaluator cannot "
        "receive, and run_eval.py no longer says so. Either the finding was "
        "disproved — re-run probes/citation_delivery_probe.py and say so — or "
        "the warning was deleted while the defect remained."
    )

    finding = ROOT / "docs" / "citation-delivery-finding.md"
    assert finding.exists(), (
        "The evidence that these inputs are discarded has been deleted. "
        "Without it the mapping reads as working."
    )


@pytest.mark.parametrize("corpus", CORPORA)
def test_the_rubric_that_receives_citations_knows_what_to_do_with_them(corpus):
    """Mapping a field to a rubric that never mentions it scores nothing.

    The mapping and the dimension are two halves of one change. Shipping the
    first without the second is indistinguishable, from the outside, from
    shipping neither.

    NOTE: this guard passing does NOT mean the dimension works. Both halves are
    in place and the dimension is still inert, because the input never arrives —
    see test_citation_mapping_is_wired_and_proven_inert.
    """
    config = select_corpus(_config(), corpus)
    spec_path = ROOT / config["evaluators"]["custom"][0]
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    dimensions = {d["id"]: d for d in spec["definition"]["dimensions"]}

    assert "citation_discipline" in dimensions, (
        f"'{corpus}' maps the citation columns but its rubric "
        f"({spec_path.name}) has no dimension that reads them"
    )
    body = dimensions["citation_discipline"]["description"]
    for field in ("expected_citations", "forbidden_citations"):
        assert field in body, (
            f"'{corpus}' citation_discipline never names {field}, so the judge "
            "is not told the field exists"
        )
    assert dimensions["citation_discipline"]["always_applicable"] is False, (
        "citation_discipline must not be always_applicable: cases with no "
        "citations would be scored against empty lists"
    )
