import argparse
import json
import os
import random
import re
from pathlib import Path

import numpy as np
import tree_sitter_c_sharp as tscs
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser


JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "true", "false", "null",
    "var"
}

CSHARP_KEYWORDS = {
    "abstract", "as", "base", "bool", "break", "byte", "case", "catch", "char",
    "checked", "class", "const", "continue", "decimal", "default", "delegate",
    "do", "double", "else", "enum", "event", "explicit", "extern", "false",
    "finally", "fixed", "float", "for", "foreach", "goto", "if", "implicit",
    "in", "int", "interface", "internal", "is", "lock", "long", "namespace",
    "new", "null", "object", "operator", "out", "override", "params", "private",
    "protected", "public", "readonly", "ref", "required", "return", "sbyte",
    "sealed", "short", "sizeof", "stackalloc", "static", "string", "struct",
    "switch", "this", "throw", "true", "try", "typeof", "uint", "ulong",
    "unchecked", "unsafe", "ushort", "using", "virtual", "void", "volatile",
    "while", "var", "get", "set", "init", "add", "remove", "value", "nameof",
    "record", "with", "when", "where", "async", "await", "yield"
}

JAVA_PROTECTED_NAMES = {
    "String", "Object", "Integer", "Long", "Double", "Boolean", "Byte", "Short",
    "Float", "Character", "System", "Exception", "RuntimeException", "Thread",
    "Math", "Class", "Iterable", "List", "Map", "Set", "ArrayList", "HashMap",
    "HashSet", "Optional", "Stream"
}

CSHARP_PROTECTED_NAMES = {
    "String", "Object", "Boolean", "Byte", "SByte", "Int16", "UInt16", "Int32",
    "UInt32", "Int64", "UInt64", "Single", "Double", "Decimal", "Char",
    "System", "Console", "Math", "Exception", "Task", "Uri", "List", "Dictionary",
    "HashSet", "IEnumerable", "IList", "IDictionary", "Collections", "Generic",
    "Linq", "Text", "Threading", "Tasks", "IO", "Net"
}

LITERAL_NODE_TO_KIND = {
    "string_literal": "string",
    "character_literal": "char",
    "decimal_integer_literal": "int",
    "hex_integer_literal": "int",
    "binary_integer_literal": "int",
    "octal_integer_literal": "int",
    "integer_literal": "int",
    "decimal_floating_point_literal": "float",
    "hex_floating_point_literal": "float",
    "real_literal": "float",
    "real_literal_token1": "float",
    "real_literal_token2": "float",
}

CATEGORY_PRIORITY = {"type": 4, "method": 3, "field": 2, "var": 1}


def set_seed(seed=42):
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)


def read_file(input_path):
    lines = []
    with open(input_path, "r", encoding="utf-8") as handle:
        for line in handle:
            if input_path.endswith(".jsonl"):
                lines.append(json.loads(line))
            else:
                lines.append(line.rstrip("\n"))
    return lines


def output_to_file(samples, output_path):
    with open(output_path, "w", encoding="utf-8") as handle:
        for sample in samples:
            line = json.dumps(sample, ensure_ascii=False) if output_path.endswith(".jsonl") else sample
            handle.write(line + "\n")


def build_identifier_standardize_name(file_path):
    path = Path(file_path)
    if path.name.endswith(".txt.java"):
        return path.name[:-len(".txt.java")] + "_identifier_standardize.txt.java"
    if path.name.endswith(".txt.cs"):
        return path.name[:-len(".txt.cs")] + "_identifier_standardize.txt.cs"
    return f"{path.stem}_identifier_standardize{path.suffix}"


def remove_comments(code):
    pattern = re.compile(
        r"//.*?$|/\*.*?\*/|'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"",
        re.DOTALL | re.MULTILINE,
    )

    def replacer(match):
        text = match.group(0)
        return " " if text.startswith("/") else text

    cleaned = re.sub(pattern, replacer, code)
    return "\n".join(line for line in cleaned.splitlines() if line.strip())


def make_parser(language_name):
    if language_name == "java":
        return Parser(Language(tsjava.language()))
    if language_name == "csharp":
        return Parser(Language(tscs.language()))
    raise ValueError(f"unsupported language: {language_name}")


def should_wrap_java(code):
    stripped = code.strip()
    return not stripped.startswith(("class ", "interface ", "enum ", "@interface ", "package ", "import "))


def should_wrap_csharp(code):
    stripped = code.strip()
    return not stripped.startswith(("namespace ", "using ", "class ", "interface ", "struct ", "enum ", "record ", "delegate "))


def wrap_code(language_name, code):
    if language_name == "java" and should_wrap_java(code):
        return "class dummy_wrapper {\n", "\n}"
    if language_name == "csharp" and should_wrap_csharp(code):
        return "class dummy_wrapper {\n", "\n}"
    return "", ""


def get_node_text(code_bytes, node):
    return code_bytes[node.start_byte:node.end_byte].decode("utf8")


def get_child_by_field_names(node, field_names):
    for field_name in field_names:
        child = node.child_by_field_name(field_name)
        if child is not None:
            return child
    return None


def is_under(node, target_types):
    current = node.parent
    while current is not None:
        if current.type in target_types:
            return True
        current = current.parent
    return False


def is_local_context(node, stop_types):
    current = node.parent
    while current is not None:
        if current.type in stop_types:
            return True
        if current.type in {"class_declaration", "interface_declaration", "struct_declaration", "enum_declaration", "compilation_unit"}:
            return False
        current = current.parent
    return False


def normalize_literals(tree, code_bytes, language_name):
    literal_map = {}
    counters = {"string": 1, "char": 1, "int": 1, "float": 1}
    replacements = []

    def detect_literal_kind(node):
        node_type = node.type
        if node_type in LITERAL_NODE_TO_KIND:
            return LITERAL_NODE_TO_KIND[node_type]
        if language_name == "csharp":
            if node_type in {"boolean_literal", "null_literal"}:
                return None
            if "string_literal" in node_type:
                return "string"
        if language_name == "java":
            if node_type in {"true", "false", "null_literal"}:
                return None
        return None

    def get_literal_span(node, kind):
        start_byte = node.start_byte
        end_byte = node.end_byte
        if kind in {"string", "char"}:
            if start_byte > 0 and end_byte < len(code_bytes):
                left = chr(code_bytes[start_byte - 1])
                right = chr(code_bytes[end_byte])
                if kind == "string" and left == "\"" and right == "\"":
                    return start_byte - 1, end_byte + 1
                if kind == "char" and left == "'" and right == "'":
                    return start_byte - 1, end_byte + 1
        return start_byte, end_byte

    def has_literal_like_named_child(node):
        for child in node.children:
            if child.is_named and detect_literal_kind(child) is not None:
                return True
        return False

    def visit(node):
        if node.is_named:
            kind = detect_literal_kind(node)
            if kind is not None and not has_literal_like_named_child(node):
                text = get_node_text(code_bytes, node)
                key = (kind, text)
                if key not in literal_map:
                    literal_map[key] = f"{kind}_{counters[kind]}"
                    counters[kind] += 1
                start_byte, end_byte = get_literal_span(node, kind)
                replacements.append((start_byte, end_byte, literal_map[key]))
        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return replacements


def determine_java_category(node, code_bytes):
    name = get_node_text(code_bytes, node)
    if name in JAVA_PROTECTED_NAMES:
        return None

    parent = node.parent
    if parent is None:
        return "var"

    if parent.type in {"class_declaration", "interface_declaration", "enum_declaration", "annotation_type_declaration"}:
        if parent.child_by_field_name("name") == node:
            return "type"

    if parent.type == "constructor_declaration" and parent.child_by_field_name("name") == node:
        return "type"

    if parent.type in {"method_declaration", "method_invocation"} and parent.child_by_field_name("name") == node:
            return "method"

    if parent.type == "method_reference":
        return "method"

    if parent.type == "field_access":
        if parent.child_by_field_name("field") == node:
            grand = parent.parent
            if grand and grand.type == "method_invocation":
                return "method"
            return "field"
        if parent.child_by_field_name("object") == node:
            return "type" if name[:1].isupper() else "var"

    if parent.type in {"formal_parameter", "spread_parameter", "catch_formal_parameter", "inferred_parameters", "lambda_expression"}:
        return "var"

    if parent.type == "variable_declarator":
        local = is_local_context(node, {"method_declaration", "constructor_declaration", "lambda_expression", "initializer"})
        return "var" if local else "field"

    if parent.type == "enum_constant":
        return "field"

    if parent.type in {"package_declaration", "scoped_identifier"}:
        return None

    if parent.type in {"marker_annotation", "annotation", "annotation_argument_list"}:
        return None

    type_contexts = {
        "type_identifier", "type_arguments", "generic_type", "superclass", "super_interfaces",
        "object_creation_expression", "cast_expression", "catch_type", "array_type",
        "class_literal", "extends_interfaces", "type_parameter"
    }
    if node.type == "type_identifier" or parent.type in type_contexts:
        return "type"

    if parent.child_by_field_name("type") == node:
        return "type"

    return "var"


def determine_csharp_category(node, code_bytes):
    name = get_node_text(code_bytes, node)
    if name in CSHARP_PROTECTED_NAMES:
        return None

    parent = node.parent
    if parent is None:
        return "var"

    if parent.type in {"class_declaration", "interface_declaration", "struct_declaration", "enum_declaration", "record_declaration"}:
        if parent.child_by_field_name("name") == node:
            return "type"

    if parent.type == "constructor_declaration" and parent.child_by_field_name("name") == node:
        return "type"

    method_name_node = get_child_by_field_names(parent, ("name", "function"))
    if parent.type in {"method_declaration", "local_function_statement", "invocation_expression"} and method_name_node == node:
        return "method"

    if parent.type == "member_access_expression":
        member_name = get_child_by_field_names(parent, ("name", "member"))
        receiver = get_child_by_field_names(parent, ("expression", "receiver"))
        if member_name == node:
            grand = parent.parent
            if grand and grand.type == "invocation_expression":
                return "method"
            return "field"
        if receiver == node:
            return "type" if name[:1].isupper() else "var"

    if parent.type in {"property_declaration", "event_declaration", "indexer_declaration"}:
        if get_child_by_field_names(parent, ("name", "declarator")) == node:
            return "field"

    if parent.type == "variable_declarator":
        local = is_local_context(
            node,
            {"method_declaration", "constructor_declaration", "local_function_statement", "anonymous_method_expression", "lambda_expression", "accessor_declaration"},
        )
        return "var" if local else "field"

    if parent.type in {"parameter", "declaration_pattern", "catch_declaration", "for_each_statement"}:
        return "var"

    type_contexts = {
        "qualified_name", "generic_name", "type_argument_list", "base_list",
        "object_creation_expression", "cast_expression", "array_type", "nullable_type",
        "pointer_type", "tuple_type", "default_expression", "sizeof_expression",
        "typeof_expression", "ref_type", "implicit_type"
    }
    if parent.type in type_contexts:
        return "type"

    if parent.child_by_field_name("type") == node:
        return "type"

    if is_under(node, {"attribute", "attribute_list"}):
        return None

    return "var"


def collect_identifier_replacements(tree, code_bytes, language_name, excluded_node=None):
    if language_name == "java":
        keywords = JAVA_KEYWORDS
        determine_category = determine_java_category
    else:
        keywords = CSHARP_KEYWORDS
        determine_category = determine_csharp_category

    name_categories = {}
    occurrences = []
    counters = {"type": 1, "method": 1, "field": 1, "var": 1}

    def register(name, category):
        previous = name_categories.get(name)
        if previous is None or CATEGORY_PRIORITY[category] > CATEGORY_PRIORITY[previous]:
            name_categories[name] = category

    def visit(node):
        if excluded_node is not None and node == excluded_node:
            return
        if node.type in {"identifier", "type_identifier"}:
            name = get_node_text(code_bytes, node)
            if name not in keywords:
                category = determine_category(node, code_bytes)
                if category is not None:
                    occurrences.append((node.start_byte, node.end_byte, name))
                    register(name, category)
        for child in node.children:
            visit(child)

    visit(tree.root_node)

    name_map = {}
    replacements = []
    for _, _, name in occurrences:
        if name not in name_map:
            category = name_categories[name]
            name_map[name] = f"{category}_{counters[category]}"
            counters[category] += 1

    for start_byte, end_byte, name in occurrences:
        replacements.append((start_byte, end_byte, name_map[name]))
    return replacements


def apply_replacements(code_bytes, replacements):
    result = bytearray(code_bytes)
    for start_byte, end_byte, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
        result[start_byte:end_byte] = replacement.encode("utf8")
    return result.decode("utf8")


def standardize_code(code, parser, language_name):
    code = remove_comments(code)
    prefix, suffix = wrap_code(language_name, code)
    wrapped_code = prefix + code + suffix
    code_bytes = wrapped_code.encode("utf8")
    tree = parser.parse(code_bytes)
    wrapper_name_node = None
    if prefix:
        for child in tree.root_node.children:
            if child.type in {"class_declaration", "interface_declaration", "struct_declaration", "record_declaration"}:
                wrapper_name_node = child.child_by_field_name("name")
                if wrapper_name_node is not None:
                    break

    replacements = []
    replacements.extend(collect_identifier_replacements(tree, code_bytes, language_name, wrapper_name_node))
    replacements.extend(normalize_literals(tree, code_bytes, language_name))

    standardized = apply_replacements(code_bytes, replacements)
    if prefix:
        standardized = standardized[len(prefix):-len(suffix)]
    return standardized


def standardize_code_pair(java_code, csharp_code, java_parser, csharp_parser):
    return (
        standardize_code(java_code, java_parser, "java"),
        standardize_code(csharp_code, csharp_parser, "csharp"),
    )


def standardize_parallel_files(java_path, csharp_path, output_dir=None):
    java_parser = make_parser("java")
    csharp_parser = make_parser("csharp")

    java_lines = read_file(java_path)
    csharp_lines = read_file(csharp_path)
    if len(java_lines) != len(csharp_lines):
        raise ValueError(f"line count mismatch: {java_path} vs {csharp_path}")

    standardized_java = []
    standardized_csharp = []
    for java_code, csharp_code in zip(java_lines, csharp_lines):
        java_std, csharp_std = standardize_code_pair(java_code, csharp_code, java_parser, csharp_parser)
        standardized_java.append(java_std)
        standardized_csharp.append(csharp_std)

    output_root = Path(output_dir) if output_dir else Path(java_path).parent / "IdentifierStandardized"
    output_root.mkdir(parents=True, exist_ok=True)

    java_output = output_root / build_identifier_standardize_name(java_path)
    csharp_output = output_root / build_identifier_standardize_name(csharp_path)
    output_to_file(standardized_java, str(java_output))
    output_to_file(standardized_csharp, str(csharp_output))
    return str(java_output), str(csharp_output)


def standardize_codetrans_raw(raw_dir, output_dir=None, splits=None):
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir) if output_dir else raw_dir.parent / "IdentifierStandardized"
    output_dir.mkdir(parents=True, exist_ok=True)

    if splits is None:
        splits = ["train", "valid", "test"]

    results = []
    for split in splits:
        java_path = raw_dir / f"{split}.java-cs.txt.java"
        csharp_path = raw_dir / f"{split}.java-cs.txt.cs"
        if java_path.exists() and csharp_path.exists():
            results.append(standardize_parallel_files(str(java_path), str(csharp_path), str(output_dir)))
    return results


def load_yaml_config(config_path):
    import yaml

    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.load(handle, Loader=yaml.FullLoader)


def standardize_from_config(config):
    if "java_path" in config and "csharp_path" in config:
        return standardize_parallel_files(
            config["java_path"],
            config["csharp_path"],
            config.get("output_dir"),
        )

    if "raw_dir" in config:
        return standardize_codetrans_raw(
            config["raw_dir"],
            config.get("output_dir"),
            config.get("splits"),
        )

    raise ValueError("config must provide either (java_path, csharp_path) or raw_dir")


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Standardize paired Java/C# CodeTrans data.")
    parser.add_argument("--config", type=str, help="YAML config path.")
    parser.add_argument("--raw-dir", type=str, help="Directory containing train/valid/test.java-cs.txt.{java,cs}.")
    parser.add_argument("--java-path", type=str, help="Path to the Java file.")
    parser.add_argument("--csharp-path", type=str, help="Path to the C# file.")
    parser.add_argument("--output-dir", type=str, help="Output directory.")
    return parser


def main():
    set_seed(42)
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.config:
        standardize_from_config(load_yaml_config(args.config))
        return

    if args.raw_dir:
        standardize_codetrans_raw(args.raw_dir, args.output_dir)
        return

    if args.java_path and args.csharp_path:
        standardize_parallel_files(args.java_path, args.csharp_path, args.output_dir)
        return

    default_raw_dir = Path(__file__).resolve().parent / "CodeTrans" / "Raw"
    standardize_codetrans_raw(default_raw_dir, args.output_dir)


if __name__ == "__main__":
    main()
