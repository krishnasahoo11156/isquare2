"""
Unit and integration tests for real image classification inference in iSquare.
"""
import time
from pathlib import Path
from PIL import Image
import pytest

from app.services.analysis.engines import (
    run_classifier,
    ClassificationOutput,
    ISQUARE_CATEGORIES,
    _load_classifier,
)
from app.services.analysis.preprocessing import PreparedImage


class TestClassificationInference:
    def _create_prepared(self, width: int = 224, height: int = 224, color: str = "white") -> PreparedImage:
        img = Image.new("RGB", (width, height), color)
        return PreparedImage(img, width, height, width, height, [])

    def test_classifier_loads(self):
        (torch, nn, backbone, head, transform), (categories, version) = _load_classifier()
        assert backbone is not None
        assert head is not None
        assert len(categories) == 10
        assert version == "1.0.0"

    def test_classifier_returns_contract(self):
        prepared = self._create_prepared()
        out = run_classifier(prepared)
        prepared.close()

        assert isinstance(out, ClassificationOutput)
        assert isinstance(out.category, str)
        assert out.category in ISQUARE_CATEGORIES or out.category == "Uncertain"
        assert out.confidence is None or (0.0 <= out.confidence <= 1.0)
        assert isinstance(out.alternatives, list)
        assert len(out.alternatives) == 10
        assert out.model == "isquare-mobilenet_v3_large-classifier"
        assert out.version == "1.0.0"

    def test_alternatives_ranked_descending(self):
        prepared = self._create_prepared(300, 300, "lightblue")
        out = run_classifier(prepared)
        prepared.close()

        confs = [item["confidence"] for item in out.alternatives]
        assert confs == sorted(confs, reverse=True)
        assert sum(confs) <= 1.01  # softmax sum rounded

    def test_classification_on_synthetic_fixtures(self):
        dataset_dir = Path(__file__).resolve().parent.parent / "storage" / "dataset" / "test"
        if not dataset_dir.is_dir():
            pytest.skip("Dataset fixtures not found")

        doc_files = list(dataset_dir.glob("test_document_*.png"))
        if doc_files:
            with Image.open(doc_files[0]) as img:
                w, h = img.size
                prepared = PreparedImage(img.convert("RGB"), w, h, w, h, [])
                out = run_classifier(prepared)
                prepared.close()
                assert out.category in ISQUARE_CATEGORIES or out.category == "Uncertain"
                assert out.confidence is not None

