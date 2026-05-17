#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run metrics_from_jsonl.py for every "
            "Qwen2.5Coder/Model/*/Inference/generated_predictions.jsonl file."
        )
    )
    parser.add_argument(
        "--model-root",
        default="Code_Translation/Qwen2.5Coder/Model",
        help="Root directory containing model subdirectories.",
    )
    parser.add_argument(
        "--metrics-script",
        default="Code_Translation/metrics_from_jsonl.py",
        help="Path to metrics_from_jsonl.py.",
    )
    parser.add_argument(
        "--lang",
        default="c_sharp",
        help="Target language passed to metrics_from_jsonl.py.",
    )
    parser.add_argument(
        "--label-key",
        default="label",
        help="Label field passed to metrics_from_jsonl.py.",
    )
    parser.add_argument(
        "--pred-key",
        default="predict",
        help="Prediction field passed to metrics_from_jsonl.py.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Pass --strict to metrics_from_jsonl.py.",
    )
    parser.add_argument(
        "--strict-codebleu",
        action="store_true",
        help="Pass --strict-codebleu to metrics_from_jsonl.py.",
    )
    return parser.parse_args()


def iter_prediction_files(model_root):
    return sorted(model_root.glob("*/Inference/generated_predictions.jsonl"))


def main():
    args = parse_args()
    model_root = Path(args.model_root)
    metrics_script = Path(args.metrics_script)

    if not model_root.exists():
        raise FileNotFoundError(f"Model root not found: {model_root}")
    if not metrics_script.exists():
        raise FileNotFoundError(f"Metrics script not found: {metrics_script}")

    prediction_files = iter_prediction_files(model_root)
    if not prediction_files:
        raise FileNotFoundError(
            f"No generated_predictions.jsonl files found under {model_root}/*/Inference"
        )

    print(f"Found {len(prediction_files)} prediction files.")
    for input_file in prediction_files:
        print(f"\n=== {input_file} ===")
        command = [
            sys.executable,
            str(metrics_script),
            str(input_file),
            "--lang",
            args.lang,
            "--label-key",
            args.label_key,
            "--pred-key",
            args.pred_key,
        ]
        if args.strict:
            command.append("--strict")
        if args.strict_codebleu:
            command.append("--strict-codebleu")

        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
