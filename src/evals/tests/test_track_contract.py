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
