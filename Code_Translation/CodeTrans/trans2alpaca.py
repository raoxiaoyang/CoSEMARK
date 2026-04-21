import argparse
import json
from pathlib import Path


def get_common_prefix(java_source_path: Path, cs_source_path: Path) -> str:
    java_suffix = ".java"
    cs_suffix = ".cs"

    if not java_source_path.name.endswith(java_suffix):
        raise ValueError(f"Java source file must end with '{java_suffix}': {java_source_path}")
    if not cs_source_path.name.endswith(cs_suffix):
        raise ValueError(f"C# source file must end with '{cs_suffix}': {cs_source_path}")

    java_prefix = java_source_path.name[: -len(java_suffix)]
    cs_prefix = cs_source_path.name[: -len(cs_suffix)]
    if java_prefix != cs_prefix:
        raise ValueError(
            "Source file prefixes do not match: "
            f"'{java_source_path.name}' vs '{cs_source_path.name}'."
        )

    return java_prefix


def convert_to_alpaca(java_source_path: Path, cs_source_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{get_common_prefix(java_source_path, cs_source_path)}.jsonl"

    instruction = (
        "Translate the following code from Java to C#. "
        "Preserve the original functionality and output only the translated code."
    )

    with (
        java_source_path.open("r", encoding="utf-8") as java_src,
        cs_source_path.open("r", encoding="utf-8") as cs_src,
        output_file.open("w", encoding="utf-8") as dst,
    ):
        for line_number, (java_line, cs_line) in enumerate(
            zip(java_src, cs_src, strict=True),
            start=1,
        ):
            java_code = java_line.rstrip("\n\r")
            cs_code = cs_line.rstrip("\n\r")

            if not java_code and not cs_code:
                continue
            if not java_code or not cs_code:
                raise ValueError(
                    f"Mismatched empty sample on line {line_number}: "
                    f"'{java_source_path}' vs '{cs_source_path}'."
                )

            converted = {
                "instruction": instruction,
                "input": f"//Java\n{java_code}",
                "output": f"//C#\n{cs_code}",
            }
            dst.write(json.dumps(converted, ensure_ascii=False) + "\n")

    return output_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert paired Java and C# source files into Alpaca jsonl format."
    )
    parser.add_argument(
        "java_source_file",
        type=Path,
        help="Path to the source file containing Java code samples.",
    )
    parser.add_argument(
        "cs_source_file",
        type=Path,
        help="Path to the source file containing C# code samples.",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Directory where the converted file will be written.",
    )
    return parser.parse_args()


def validate_source_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{label} path is not a file: {path}")


def main() -> None:
    args = parse_args()
    validate_source_file(args.java_source_file, "Java source")
    validate_source_file(args.cs_source_file, "C# source")

    output_file = convert_to_alpaca(
        args.java_source_file,
        args.cs_source_file,
        args.output_dir,
    )
    print(
        "Converted "
        f"'{args.java_source_file.name}' and '{args.cs_source_file.name}' "
        f"to Alpaca format: '{output_file}'"
    )


if __name__ == "__main__":
    main()
