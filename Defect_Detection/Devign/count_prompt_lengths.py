from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

from transformers import AutoTokenizer


def build_prompt(example: dict[str, object]) -> str:
    instruction = example.get("instruction", "")
    prompt_input = example.get("input", "")
    if instruction is None:
        instruction = ""
    if prompt_input is None:
        prompt_input = ""

    if instruction and prompt_input:
        return f"{instruction}\n{prompt_input}"
    return instruction or prompt_input


def load_examples(path: Path) -> list[dict[str, object]]:
    examples: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as infile:
        for line_num, line in enumerate(infile, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                example = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_num}: {exc}") from exc
            if not isinstance(example, dict):
                raise ValueError(f"Expected JSON object at {path}:{line_num}, got {type(example).__name__}")
            examples.append(example)
    return examples


def plot_histogram(lengths: Counter[int], output_path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            "matplotlib is required to plot the histogram. Install it with `pip install matplotlib`."
        ) from exc

    sorted_lengths = sorted(lengths.items())
    x, y = zip(*sorted_lengths)
    plt.figure(figsize=(12, 6))
    plt.bar(x, y, width=1.0, edgecolor="black")
    plt.xlabel("Token length")
    plt.ylabel("Count")
    plt.title("StarCoder2 prompt token length distribution")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()


def write_log_file(lines: list[str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count StarCoder2 token lengths for LlamaFactory Alpaca prompts."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).resolve().parent / "Llamafactory" / "train.jsonl",
        help="Path to the Alpaca-format JSONL dataset.",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="/home/raoxiaoyang/llm_models/starcoder2-7b",
        help="StarCoder2 tokenizer model name or path.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional output JSON file for the length histogram.",
    )
    parser.add_argument(
        "--output-log",
        type=Path,
        default=None,
        help="Optional plain text log file to write the distribution output.",
    )
    parser.add_argument(
        "--plot-file",
        type=Path,
        default=None,
        help="Optional image file path for the histogram plot (e.g. png).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))

    try:
        from llamafactory.data.template import TEMPLATES
    except ImportError as exc:
        raise ImportError(
            "Could not import llamafactory. Run this script from the repo root or install the local package."
        ) from exc

    template = TEMPLATES["alpaca"]
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, use_fast=False)
    template.fix_special_tokens(tokenizer)

    if not args.input.exists():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    examples = load_examples(args.input)
    lengths = Counter()
    samples = 0
    bad_samples = 0

    for example in examples:
        if not isinstance(example.get("output"), str):
            bad_samples += 1
            continue

        prompt_text = build_prompt(example)
        messages = [
            {"role": "user", "content": prompt_text},
            {"role": "assistant", "content": example["output"]},
        ]

        prompt_ids, _ = template.encode_oneturn(tokenizer, messages)
        lengths[len(prompt_ids)] += 1
        samples += 1

    if samples == 0:
        raise ValueError("No valid examples found in the input file.")

    sorted_lengths = sorted(lengths.items())
    lines: list[str] = [f"Processed {samples} examples."]
    if bad_samples:
        lines.append(f"Skipped {bad_samples} examples with non-string output.")
    lines.append("Token length distribution (prompt only):")
    lines.append("length\tcount")
    for length, count in sorted_lengths:
        lines.append(f"{length}\t{count}")

    print("\n".join(lines))

    if args.output_log:
        write_log_file(lines, args.output_log)
        print(f"Wrote log to {args.output_log}")

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        result = {"total_examples": samples, "distribution": dict(sorted_lengths)}
        args.output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote histogram to {args.output_json}")

    if args.plot_file:
        plot_histogram(lengths, args.plot_file)
        print(f"Wrote plot to {args.plot_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
