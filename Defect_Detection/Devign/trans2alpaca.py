import argparse
import json
from pathlib import Path


def convert_jsonl_to_alpaca(source_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / source_path.name

    instruction = "Analyze the code for security issues. Output 1 if vulnerable, else 0."

    with source_path.open("r", encoding="utf-8") as src, output_file.open("w", encoding="utf-8") as dst:
        for line_number, line in enumerate(src, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {source_path}: {exc}") from exc

            if "code" not in item or "label" not in item:
                raise KeyError(
                    f"Missing required field on line {line_number} of {source_path}: expected 'code' and 'label'."
                )

            converted = {
                "instruction": instruction,
                "input": item["code"],
                "output": str(item["label"]),
            }
            dst.write(json.dumps(converted, ensure_ascii=False) + "\n")

    return output_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a jsonl file with 'code' and 'label' into Alpaca format."
    )
    parser.add_argument(
        "source_file",
        type=Path,
        help="Path to the source jsonl file containing 'code' and 'label' fields.",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Directory where the converted file will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_file = args.source_file
    if not source_file.exists():
        raise FileNotFoundError(f"Source file does not exist: {source_file}")
    if not source_file.is_file():
        raise ValueError(f"Source path is not a file: {source_file}")

    output_file = convert_jsonl_to_alpaca(source_file, args.output_dir)
    print(f"Converted '{source_file.name}' to Alpaca format: '{output_file}'")


if __name__ == "__main__":
    main()
