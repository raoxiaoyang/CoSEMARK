#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from bleu import compute_bleu


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate code translation metrics from a jsonl file."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default="Code_Translation/Qwen2.5Coder/Model/Clean/Inference/generated_predictions.jsonl",
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
        "--lang",
        default="c_sharp",
        help=(
            "Target programming language for CodeBLEU, e.g. c_sharp, java, "
            "python, javascript, php, go, ruby."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail immediately when a label or prediction is missing.",
    )
    parser.add_argument(
        "--strict-codebleu",
        action="store_true",
        help="Fail when CodeBLEU cannot be computed.",
    )
    parser.add_argument(
        "--output",
        help=(
            "Path to save metrics. Defaults to "
            "<input_file_directory>/<input_file_stem>_metrics.json."
        ),
    )
    return parser.parse_args()


def normalize_text(value):
    if value is None:
        return None

    text = str(value).strip()
    return text if text else None


def normalize_lang(lang):
    aliases = {
        "cs": "c_sharp",
        "c#": "c_sharp",
        "csharp": "c_sharp",
        "c_sharp": "c_sharp",
        "cpp": "cpp",
        "c++": "cpp",
        "java": "java",
        "javascript": "javascript",
        "js": "javascript",
        "python": "python",
        "py": "python",
        "php": "php",
        "go": "go",
        "golang": "go",
        "ruby": "ruby",
    }
    normalized = aliases.get(lang.strip().lower())
    if normalized is None:
        raise ValueError(f"Unsupported language alias for CodeBLEU: {lang}")
    return normalized


def compute_bleu_score(labels, predictions):
    if not labels:
        return 0.0

    references = [[[token for token in label.split()]] for label in labels]
    translations = [[token for token in prediction.split()] for prediction in predictions]
    bleu_score, _, _, _, _, _ = compute_bleu(
        reference_corpus=references,
        translation_corpus=translations,
        max_order=4,
        smooth=True,
    )
    return round(100 * bleu_score, 2)


def compute_xmatch_score(labels, predictions):
    if not labels:
        return 0.0
    matches = sum(label == prediction for label, prediction in zip(labels, predictions))
    return round(100 * matches / len(labels), 2)


def try_compute_codebleu(labels, predictions, lang):
    if not labels:
        return {
            "score": 0.0,
            "available": True,
            "error": None,
            "details": {"codebleu": 0.0},
            "exception": None,
        }

    try:
        from codebleu import calc_codebleu
    except ImportError as exc:
        return {
            "score": None,
            "available": False,
            "error": (
                "CodeBLEU dependency is not installed. Install the `codebleu` "
                "package to enable this metric."
            ),
            "details": None,
            "exception": repr(exc),
        }

    references = [[label] for label in labels]
    try:
        result = calc_codebleu(references, predictions, lang=lang)
    except TypeError:
        # Older implementations may expect a flat reference list.
        result = calc_codebleu(labels, predictions, lang=lang)

    score = result.get("codebleu")
    if score is None:
        raise ValueError(f"Unexpected CodeBLEU result: {result}")

    details = {}
    for key, value in result.items():
        details[key] = round(100 * value, 2) if isinstance(value, float) else value

    return {
        "score": round(100 * score, 2),
        "available": True,
        "error": None,
        "details": details,
        "exception": None,
    }


def build_result(input_path, args, labels, predictions, invalid_rows, codebleu_result):
    metrics = {
        "bleu": compute_bleu_score(labels, predictions),
        "xmatch": compute_xmatch_score(labels, predictions),
        "codebleu": codebleu_result["score"],
    }

    result = {
        "file": str(input_path),
        "label_key": args.label_key,
        "pred_key": args.pred_key,
        "language": args.lang,
        "valid_samples": len(labels),
        "invalid_samples": len(invalid_rows),
        "metrics": metrics,
        "invalid_examples": invalid_rows,
    }

    if codebleu_result["details"] is not None:
        result["codebleu_details"] = codebleu_result["details"]
    if codebleu_result["error"] is not None:
        result["codebleu_error"] = codebleu_result["error"]

    return result


def print_result(result, output_path):
    metrics = result["metrics"]

    print(f"file: {result['file']}")
    print(f"label_key: {result['label_key']}")
    print(f"pred_key: {result['pred_key']}")
    print(f"language: {result['language']}")
    print(f"valid_samples: {result['valid_samples']}")
    print(f"invalid_samples: {result['invalid_samples']}")
    print(f"bleu: {metrics['bleu']:.2f}")
    if metrics["codebleu"] is None:
        print("codebleu: unavailable")
        print(f"codebleu_error: {result['codebleu_error']}")
    else:
        print(f"codebleu: {metrics['codebleu']:.2f}")
    print(f"xmatch: {metrics['xmatch']:.2f}")
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

    args.lang = normalize_lang(args.lang)

    labels = []
    predictions = []
    invalid_rows = []

    with input_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            row = json.loads(line)

            label = normalize_text(row.get(args.label_key))
            prediction = normalize_text(row.get(args.pred_key))

            if label is None or prediction is None:
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

            labels.append(label)
            predictions.append(prediction)

    codebleu_result = try_compute_codebleu(labels, predictions, args.lang)
    if args.strict_codebleu and not codebleu_result["available"]:
        raise RuntimeError(codebleu_result["error"])

    result = build_result(
        input_path=input_path,
        args=args,
        labels=labels,
        predictions=predictions,
        invalid_rows=invalid_rows,
        codebleu_result=codebleu_result,
    )
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
