#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate binary classification metrics from a jsonl file."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default="Defect_Detection/StarCoder2/Model/Clean/Inference/generated_predictions.jsonl",
        help="Path to the jsonl file.",
    )
    parser.add_argument(
        "--label-key",
        default="label",
        help="Field name for the ground-truth label.",
    )
    parser.add_argument(
        "--pred-key",
        default="predict",
        help="Field name for the prediction.",
    )
    parser.add_argument(
        "--positive-label",
        type=int,
        default=1,
        choices=[0, 1],
        help="Which class is treated as the positive class.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail immediately when an invalid label or prediction is found.",
    )
    parser.add_argument(
        "--output",
        help=(
            "Path to save metrics. Defaults to "
            "<input_file_directory>/<input_file_stem>_metrics.json."
        ),
    )
    return parser.parse_args()


def extract_binary_label(value):
    if value is None:
        return None

    text = str(value).strip()
    if text in {"0", "1"}:
        return int(text)

    matches = re.findall(r"[01]", text)
    if len(matches) == 1:
        return int(matches[0])

    return None


def safe_div(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def compute_metrics(tp, tn, fp, fn):
    total = tp + tn + fp + fn
    accuracy = safe_div(tp + tn, total)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)

    neg_precision = safe_div(tn, tn + fn)
    neg_recall = safe_div(tn, tn + fp)
    neg_f1 = safe_div(2 * neg_precision * neg_recall, neg_precision + neg_recall)

    macro_precision = (precision + neg_precision) / 2
    macro_recall = (recall + neg_recall) / 2
    macro_f1 = (f1 + neg_f1) / 2

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "support": total,
    }


def build_result(input_path, args, tp, tn, fp, fn, invalid_rows):
    metrics = compute_metrics(tp, tn, fp, fn)
    return {
        "file": str(input_path),
        "label_key": args.label_key,
        "pred_key": args.pred_key,
        "positive_label": args.positive_label,
        "valid_samples": metrics["support"],
        "invalid_samples": len(invalid_rows),
        "confusion_matrix": {
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
        },
        "metrics": {
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "macro_precision": metrics["macro_precision"],
            "macro_recall": metrics["macro_recall"],
            "macro_f1": metrics["macro_f1"],
        },
        "invalid_examples": invalid_rows,
    }


def print_result(result, output_path):
    confusion_matrix = result["confusion_matrix"]
    metrics = result["metrics"]

    print(f"file: {result['file']}")
    print(f"label_key: {result['label_key']}")
    print(f"pred_key: {result['pred_key']}")
    print(f"positive_label: {result['positive_label']}")
    print(f"valid_samples: {result['valid_samples']}")
    print(f"invalid_samples: {result['invalid_samples']}")
    print(f"tp: {confusion_matrix['tp']}")
    print(f"tn: {confusion_matrix['tn']}")
    print(f"fp: {confusion_matrix['fp']}")
    print(f"fn: {confusion_matrix['fn']}")
    print(f"accuracy: {metrics['accuracy']:.6f}")
    print(f"precision: {metrics['precision']:.6f}")
    print(f"recall: {metrics['recall']:.6f}")
    print(f"f1: {metrics['f1']:.6f}")
    print(f"macro_precision: {metrics['macro_precision']:.6f}")
    print(f"macro_recall: {metrics['macro_recall']:.6f}")
    print(f"macro_f1: {metrics['macro_f1']:.6f}")
    print(f"saved_to: {output_path}")

    invalid_rows = result["invalid_examples"]
    if invalid_rows:
        print("\ninvalid_examples:")
        for item in invalid_rows[:10]:
            print(
                f"  line {item['line']}: label={item['label']!r}, "
                f"predict={item['predict']!r}"
            )
        if len(invalid_rows) > 10:
            print(f"  ... and {len(invalid_rows) - 10} more")


def main():
    args = parse_args()
    input_path = Path(args.input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    tp = tn = fp = fn = 0
    invalid_rows = []

    with input_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            row = json.loads(line)

            label = extract_binary_label(row.get(args.label_key))
            pred = extract_binary_label(row.get(args.pred_key))

            if label is None or pred is None:
                invalid_rows.append(
                    {
                        "line": line_no,
                        "label": row.get(args.label_key),
                        "predict": row.get(args.pred_key),
                    }
                )
                if args.strict:
                    raise ValueError(
                        f"Invalid data at line {line_no}: "
                        f"label={row.get(args.label_key)!r}, "
                        f"predict={row.get(args.pred_key)!r}"
                    )
                continue

            if args.positive_label == 0:
                label = 1 - label
                pred = 1 - pred

            if label == 1 and pred == 1:
                tp += 1
            elif label == 0 and pred == 0:
                tn += 1
            elif label == 0 and pred == 1:
                fp += 1
            else:
                fn += 1

    result = build_result(input_path, args, tp, tn, fp, fn, invalid_rows)
    output_path = (
        Path(args.output)
        if args.output
        else input_path.with_name(f"{input_path.stem}_metrics.json")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print_result(result, output_path)


if __name__ == "__main__":
    main()
