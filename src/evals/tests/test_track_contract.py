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
# YAML and cannot be extended. Read back from both published rubrics on
# 2026-09-24. Anything mapped to a name outside this set is silently discarded:
# no error, no warning, the value simply never arrives.
# See docs/citation-delivery-finding.md.
RUBRIC_ACCEPTED_INPUTS = frozenset({"query", "response", "messages", "tool_definitions"})


def _corpus_dir(corpus: str) -> Path:
    """The directory holding a track's corpus documents.

    Resolved through index_corpus.CONFIG_SECTIONS rather than hardcoded, so a
    track that is renamed or re-pointed cannot leave this test silently reading
    an empty directory and passing. Imported lazily, as elsewhere in this file,
    so the pure-logic tests do not require the Azure SDK.
    """
    import index_corpus

    section = index_corpus.CONFIG_SECTIONS[corpus]
    return ROOT / _config()[section]["directory"]


# Inputs a rubric dimension must never be written to depend on, because they
# cannot be delivered to it. Prose that tells the judge to consult one of these
# is asking for a check that will not happen — and the judge will not say so,
# it will simply score something else. That is how `attributed_figures` gave
# full marks to a figure traceable to nothing (docs/citation-delivery-finding.md).
UNDELIVERABLE_TO_A_RUBRIC = ("expected_citations", "forbidden_citations", "ground_truth")


@pytest.mark.parametrize("corpus", CORPORA)
def test_no_undeliverable_inputs_are_mapped(corpus):
    """The successor to T20 and T23, and the lesson from both.

    T20 pinned the original defect: the citation columns were published into
    the dataset and handed to no evaluator, so `forbidden_citations` passed for
    every agent forever. 3705444 "fixed" it by mapping them into the custom
    rubric — and T23 proved the service accepts those keys and throws them
    away, which is the same defect wearing a mapping.

    So the rule is not "map the citation columns". It is that a rubric
    criterion must map ONLY inputs the service will actually deliver. Mapping
    anything else produces a dimension that looks wired, scores nothing, and
    cannot be distinguished from a working one by reading the code.

    If this fails because a new key was added, re-run
    probes/citation_delivery_probe.py against the live service before assuming
    the key arrives.
    """
    config = select_corpus(_config(), corpus)
    criteria = run_eval.build_testing_criteria(config, judge_model="judge-deployment")
    rubric = next(
        (c for c in criteria if c["name"] == run_eval.custom_metric(config)),
        None,
    )
    assert rubric is not None, f"'{corpus}' emits no custom rubric criterion"

    undeliverable = sorted(set(rubric["data_mapping"]) - RUBRIC_ACCEPTED_INPUTS)
    assert not undeliverable, (
        f"'{corpus}' maps {undeliverable} into a rubric evaluator, which "
        f"accepts only {sorted(RUBRIC_ACCEPTED_INPUTS)}. The service will "
        "accept this mapping and discard those values, leaving a dimension "
        "that appears wired and scores nothing. See "
        "docs/citation-delivery-finding.md."
    )


@pytest.mark.parametrize("corpus", CORPORA)
def test_rubric_dimensions_do_not_ask_for_what_they_cannot_see(corpus):
    """A dimension may only depend on its own prose, the query, or the response.

    This is the guard the demo actually needed and did not have. Four
    dimensions across the two rubrics — `citation_discipline` twice, `recency`,
    `attributed_figures` and `no_fabricated_figures` — were written to check
    the answer against "the retrieved context" or against a per-case citation
    list. None of that is ever delivered to a rubric evaluator.

    The failure is silent and it is worse than a no-op. Asked to consult
    evidence it does not have, the judge does not abstain: it scores on
    plausibility and writes a confident justification. An untraceable figure
    came back with full marks and a paragraph explaining why it was sound.

    A dimension that names the documents in its own text — as
    `rate_card_in_effect` always did — needs nothing delivered and works.
    """
    config = select_corpus(_config(), corpus)
    spec_path = ROOT / config["evaluators"]["custom"][0]
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    for dimension in spec["definition"]["dimensions"]:
        body = dimension["description"]
        for field in UNDELIVERABLE_TO_A_RUBRIC:
            assert field not in body, (
                f"{spec_path.name}: dimension '{dimension['id']}' tells the "
                f"judge to consult `{field}`, which a rubric evaluator never "
                "receives. Rewrite it to carry the fact in its own prose, the "
                "way rate_card_in_effect does."
            )

    # Any dimension that does mention retrieval must also tell the judge it
    # cannot see it, or the judge will invent an answer rather than abstain.
    for dimension in spec["definition"]["dimensions"]:
        body = dimension["description"]
        if "retrieved" not in body.lower():
            continue
        assert "NOT" in body and "alone" in body, (
            f"{spec_path.name}: dimension '{dimension['id']}' refers to "
            "retrieved documents without telling the judge they are NOT "
            "available and that it must judge from the response alone. That "
            "omission is what produced a full-marks score for an untraceable "
            "figure."
        )


@pytest.mark.parametrize("corpus", CORPORA)
def test_citation_discipline_names_the_superseded_document_it_guards(corpus):
    """Self-contained means the trap is spelled out, not referred to.

    `citation_discipline` exists to catch reliance on a superseded document.
    Since no citation list reaches the judge, the only way it can do that is by
    naming the document in its own prose. Each corpus has exactly one
    superseded document; the dimension must name it, or it is guarding nothing.
    """
    config = select_corpus(_config(), corpus)
    spec_path = ROOT / config["evaluators"]["custom"][0]
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    dimensions = {d["id"]: d for d in spec["definition"]["dimensions"]}

    assert "citation_discipline" in dimensions, (
        f"'{corpus}' rubric ({spec_path.name}) has no citation_discipline dimension"
    )
    dimension = dimensions["citation_discipline"]

    corpus_dir = _corpus_dir(corpus)
    superseded = [
        path.stem
        for path in sorted(corpus_dir.glob("*.md"))
        if "status: superseded" in path.read_text(encoding="utf-8")
    ]
    assert superseded, f"'{corpus}' corpus has no superseded document to guard"

    for doc_id in superseded:
        assert doc_id in dimension["description"], (
            f"{spec_path.name}: citation_discipline never names '{doc_id}', "
            "the superseded document it exists to catch reliance on. With no "
            "citation list reaching the judge, a document the prose does not "
            "name is a document the dimension cannot guard against."
        )

    assert dimension["always_applicable"] is False, (
        "citation_discipline must not be always_applicable: a refusal cites "
        "nothing and would be scored down for it"
    )
