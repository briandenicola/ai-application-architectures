"""What the model actually reads, for every corpus.

#14 was a defect in this seam. v2's GUARD 2 instructs every claim to carry the
document's `doc_id`, and no `doc_id` reached the model: it lives in front
matter, which `parse_document` lifts into metadata. Asked to cite an id and
handed none, agents cited the nearest identifier-shaped thing they could see —
`doc_type` values and `content_hash` strings. No amount of prompting fixes a
field that is absent from the context.

These tests iterate `index_corpus.CONFIG_SECTIONS` rather than naming corpora,
so a fourth track is covered the day its knowledge block exists. That matters
here more than usual: `hr` has a knowledge block but no `dataset_hr`, so the
track-contract tests do not see it yet and these do.

Azure is never contacted; this reads the corpus off disk and calls the same
parser the indexer calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import index_corpus  # noqa: E402

CONFIG = yaml.safe_load((ROOT / "evals.config.yaml").read_text(encoding="utf-8"))

# Words that would hand the model the recency answer if they appeared in the
# provenance header. `status` and `effective_date` are the two fields whose
# whole purpose is to be governed metadata rather than prose.
RECENCY_TELLS = ("status:", "effective_date:", "effective date", "supersed")


def corpus_sections() -> list[tuple[str, Path]]:
    sections = []
    for corpus, block in index_corpus.CONFIG_SECTIONS.items():
        directory = ROOT / CONFIG[block]["directory"]
        sections.append((corpus, directory))
    return sections


SECTIONS = corpus_sections()


def parsed_docs(directory: Path) -> list[dict]:
    return [index_corpus.parse_document(p) for p in sorted(directory.glob("*.md"))]


@pytest.mark.parametrize("corpus,directory", SECTIONS)
def test_corpus_directory_is_populated(corpus, directory):
    """Guards over an empty list pass without proving anything — the failure
    this suite has now hit five separate ways. Establish there is something to
    check before checking it."""
    assert directory.is_dir(), f"'{corpus}' points at missing {directory}"
    docs = parsed_docs(directory)
    expected = CONFIG[index_corpus.CONFIG_SECTIONS[corpus]]["expected_document_count"]
    assert len(docs) == expected, (
        f"'{corpus}' has {len(docs)} documents on disk but config expects {expected}"
    )


@pytest.mark.parametrize("corpus,directory", SECTIONS)
def test_every_indexed_body_states_its_own_doc_id(corpus, directory):
    """The fix for #14. A citation contract the context cannot satisfy is a
    prompt that reliably produces invented identifiers."""
    for doc in parsed_docs(directory):
        first_line = doc["content"].splitlines()[0]
        assert first_line == f"doc_id: {doc['doc_id']}", (
            f"{corpus}/{doc['doc_id']} indexed body starts with {first_line!r}; "
            "the model cannot cite an id it is never shown"
        )


@pytest.mark.parametrize("corpus,directory", SECTIONS)
def test_indexed_body_carries_no_recency_tell(corpus, directory):
    """The line the doc_id fix must not cross.

    Recency belongs in `status` and `effective_date` metadata, where it can be
    governed, not in prose the model can simply read. A superseded document
    that announces itself costs nothing to retrieve, and the stale-document
    trap — the centre of the demo — stops firing. An earlier corpus shipped
    exactly that mistake; see test_fee_schedules_do_not_defeat_their_own_trap.

    If a future change adds `effective_date` to the provenance header to
    satisfy v2's full citation format, this fails. That is the point: it should
    be a decision taken with the trap in view, not a convenience.
    """
    for doc in parsed_docs(directory):
        header = doc["content"].split("\n\n", 1)[0].lower()
        for tell in RECENCY_TELLS:
            assert tell not in header, (
                f"{corpus}/{doc['doc_id']} provenance header contains {tell!r}. "
                "Recency in the body defeats the stale-document trap."
            )


@pytest.mark.parametrize("corpus,directory", SECTIONS)
def test_the_document_body_survives_the_header(corpus, directory):
    """Prepending provenance must not cost any content.

    `content` is both the retrieved text and, via the embedding call, what the
    vector is built from. Truncating it here would degrade retrieval quietly
    and look like a model problem.
    """
    for path in sorted(directory.glob("*.md")):
        doc = index_corpus.parse_document(path)
        _, _, body = path.read_text(encoding="utf-8").split("---", 2)
        assert doc["content"].endswith(body.strip()), (
            f"{corpus}/{doc['doc_id']} indexed body does not end with the source body"
        )
        assert body.strip() in doc["content"]


def test_more_than_one_corpus_is_checked():
    """If this collapses to one, every parametrised test above narrows to a
    single track while still reporting green."""
    assert len(SECTIONS) >= 3, f"only {[c for c, _ in SECTIONS]} checked"
