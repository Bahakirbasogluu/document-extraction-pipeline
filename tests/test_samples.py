"""The bundled samples are a regression set: these numbers change only when the code does."""

from pathlib import Path

from docpipe import Pipeline
from docpipe.evaluate import evaluate

SAMPLES = Path(__file__).parent.parent / "samples"


def test_rule_backend_on_bundled_samples():
    summary = evaluate(Pipeline(), SAMPLES / "docs", SAMPLES / "gold").summary()
    assert summary["files_split_correctly"] == summary["files"] == 38
    assert summary["documents"] == 45
    review = summary["review"]
    assert review["faulty_sent_to_review"] == review["faulty_documents"] == 6
    assert review["faulty_with_the_fault_named"] >= 3
    assert summary["field_accuracy"] > 0.85
