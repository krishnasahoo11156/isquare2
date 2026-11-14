"""Compute metrics from a held-out JSONL file; this script does not create labels or inference outputs."""
import argparse
import json
import unicodedata
from pathlib import Path


def distance(left: list, right: list) -> int:
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def iou(a: dict, b: dict) -> float:
    ax1, ay1, ax2, ay2 = a["x"], a["y"], a["x"] + a["width"], a["y"] + a["height"]
    bx1, by1, bx2, by2 = b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"]
    intersection = max(0, min(ax2, bx2) - max(ax1, bx1)) * max(0, min(ay2, by2) - max(ay1, by1))
    union = a["width"] * a["height"] + b["width"] * b["height"] - intersection
    return intersection / union if union else 0.0


def evaluate(rows: list[dict]) -> dict:
    output = {}
    classification = [r for r in rows if r.get("task") == "classification"]
    if classification:
        labels = sorted({str(r["expected"]) for r in classification} | {str(r["predicted"]) for r in classification})
        matrix = {actual: {predicted: 0 for predicted in labels} for actual in labels}
        for row in classification:
            matrix[str(row["expected"])][str(row["predicted"])] += 1
        per_class = {}
        for label in labels:
            tp = matrix[label][label]
            fp = sum(matrix[actual][label] for actual in labels if actual != label)
            fn = sum(matrix[label][predicted] for predicted in labels if predicted != label)
            precision = tp / (tp + fp) if tp + fp else 0
            recall = tp / (tp + fn) if tp + fn else 0
            per_class[label] = {"precision": precision, "recall": recall,
                                "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0}
        output["classification"] = {"count": len(classification), "accuracy": sum(r["expected"] == r["predicted"] for r in classification) / len(classification),
            "uncertain_rate": sum(r["predicted"] == "uncertain" for r in classification) / len(classification),
            "per_class": per_class, "confusion_matrix": matrix}
    ocr = [r for r in rows if r.get("task") == "ocr"]
    if ocr:
        chars = words = char_errors = word_errors = 0
        for row in ocr:
            expected = unicodedata.normalize("NFC", str(row["expected"]))
            predicted = unicodedata.normalize("NFC", str(row["predicted"]))
            expected_words, predicted_words = expected.split(), predicted.split()
            chars += len(expected); words += len(expected_words)
            char_errors += distance(list(expected), list(predicted)); word_errors += distance(expected_words, predicted_words)
        output["ocr"] = {"count": len(ocr), "character_error_rate": char_errors / chars if chars else None,
                          "word_error_rate": word_errors / words if words else None}
    detection = [r for r in rows if r.get("task") == "detection"]
    if detection:
        tp = fp = fn = 0
        for row in detection:
            truths = list(row.get("expected", [])); predictions = sorted(row.get("predicted", []), key=lambda p: p.get("confidence", 0), reverse=True)
            matched = set()
            for prediction in predictions:
                candidates = [(iou(prediction["box"], truth["box"]), idx) for idx, truth in enumerate(truths)
                              if idx not in matched and truth["label"] == prediction["label"]]
                best = max(candidates, default=(0.0, -1))
                if best[0] >= 0.5:
                    tp += 1; matched.add(best[1])
                else: fp += 1
            fn += len(truths) - len(matched)
        output["detection_iou_0_5"] = {"true_positive": tp, "false_positive": fp, "false_negative": fn,
            "precision": tp / (tp + fp) if tp + fp else 0, "recall": tp / (tp + fn) if tp + fn else 0}
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path)
    args = parser.parse_args()
    with args.jsonl.open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    print(json.dumps(evaluate(rows), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
