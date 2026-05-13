import argparse
from pathlib import Path
import re


SDK_PATTERNS = (
    re.compile(r"\bInvokeOptions\b"),
    re.compile(r"\bRequestMarshaller\b"),
    re.compile(r"\bResponseUnmarshaller\b"),
    re.compile(r"\bInvoke\s*<"),
)

JAVA_CTOR_RE = re.compile(r"^\s*public\s+[A-Z][\w$]*\s*\([^)]*\)\s*\{")
JAVA_SUPER_RE = re.compile(r"\{\s*super\s*\(")
CS_BASE_CTOR_RE = re.compile(r"^\s*public\s+[A-Z][\w$]*\s*\([^)]*\)\s*:\s*base\s*\(")
CS_RPC_ASSIGN_RE = re.compile(r"\b(?:Protocol|Method|UriPattern)\s*=")
CS_METHOD_TYPE_RE = re.compile(r"\bMethodType\.")


def is_sdk_wrapper(cs_code: str) -> bool:
    return all(pattern.search(cs_code) for pattern in SDK_PATTERNS)


def is_rpc_request_constructor(java_code: str, cs_code: str) -> bool:
    return (
        JAVA_CTOR_RE.search(java_code) is not None
        and JAVA_SUPER_RE.search(java_code) is not None
        and CS_BASE_CTOR_RE.search(cs_code) is not None
        and (
            CS_RPC_ASSIGN_RE.search(cs_code) is not None
            or CS_METHOD_TYPE_RE.search(cs_code) is not None
        )
    )


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def filter_test(java_path: Path, cs_path: Path, output_dir: Path) -> None:
    java_lines = read_lines(java_path)
    cs_lines = read_lines(cs_path)
    if len(java_lines) != len(cs_lines):
        raise ValueError(
            f"Line count mismatch: {java_path} has {len(java_lines)} lines, "
            f"{cs_path} has {len(cs_lines)} lines."
        )

    filtered_java = []
    filtered_cs = []
    index_records = []
    sdk_count = 0
    rpc_count = 0

    for index, (java_code, cs_code) in enumerate(zip(java_lines, cs_lines)):
        types = []
        if is_sdk_wrapper(cs_code):
            types.append("SDK wrapper")
            sdk_count += 1
        if is_rpc_request_constructor(java_code, cs_code):
            types.append("RPC/request")
            rpc_count += 1

        if types:
            index_records.append(f"{index}\t{','.join(types)}")
            continue

        filtered_java.append(java_code)
        filtered_cs.append(cs_code)

    write_lines(output_dir / "index.txt", index_records)
    write_lines(output_dir / "test_filtered.txt.java", filtered_java)
    write_lines(output_dir / "test_filtered.txt.cs", filtered_cs)

    print(f"total: {len(java_lines)}")
    print(f"SDK wrapper: {sdk_count}")
    print(f"RPC/request: {rpc_count}")
    print(f"removed unique: {len(index_records)}")
    print(f"filtered: {len(filtered_java)}")
    print(f"wrote: {output_dir / 'index.txt'}")
    print(f"wrote: {output_dir / 'test_filtered.txt.java'}")
    print(f"wrote: {output_dir / 'test_filtered.txt.cs'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter CodeTrans test samples that match SDK wrapper or RPC/request constructor templates."
    )
    parser.add_argument(
        "--java",
        type=Path,
        default=Path("Raw/test.java-cs.txt.java"),
        help="Path to the raw Java test file.",
    )
    parser.add_argument(
        "--cs",
        type=Path,
        default=Path("Raw/test.java-cs.txt.cs"),
        help="Path to the raw C# test file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("Raw"),
        help="Directory for index.txt and filtered test files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    filter_test(args.java, args.cs, args.output_dir)


if __name__ == "__main__":
    main()
