from scripts.evaluate_analysis import evaluate


def test_evaluation_reports_uncertainty_ocr_and_detection_errors():
    metrics = evaluate([
        {"task": "classification", "expected": "document", "predicted": "uncertain"},
        {"task": "classification", "expected": "animal", "predicted": "animal"},
        {"task": "ocr", "expected": "Hello world", "predicted": "Hello word"},
        {"task": "detection", "expected": [{"label": "person", "box": {"x": 0, "y": 0, "width": 10, "height": 10}}],
         "predicted": [{"label": "person", "confidence": 0.9, "box": {"x": 0, "y": 0, "width": 10, "height": 10}}]},
    ])
    assert metrics["classification"]["accuracy"] == 0.5
    assert metrics["classification"]["uncertain_rate"] == 0.5
    assert metrics["ocr"]["word_error_rate"] == 0.5
    assert metrics["detection_iou_0_5"]["precision"] == 1.0
