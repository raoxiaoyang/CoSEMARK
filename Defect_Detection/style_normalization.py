import argparse
import json
import os
import random
import re
from pathlib import Path

import numpy as np
import tree_sitter_cpp as tscpp
import yaml
from tree_sitter import Language, Parser


DEFAULT_OUTPUT_DIR = "Defect_Detection/Devign/StyleNormalization"


CPP_KEYWORDS = {
    "alignas", "alignof", "and", "and_eq", "asm", "auto", "bitand", "bitor",
    "bool", "break", "case", "catch", "char", "char8_t", "char16_t", "char32_t",
    "class", "compl", "concept", "const", "consteval", "constexpr", "constinit",
    "const_cast", "continue", "co_await", "co_return", "co_yield", "decltype",
    "default", "delete", "do", "double", "dynamic_cast", "else", "enum",
    "explicit", "export", "extern", "false", "float", "for", "friend", "goto",
    "if", "inline", "int", "long", "mutable", "namespace", "new", "noexcept",
    "not", "not_eq", "nullptr", "operator", "or", "or_eq", "private", "protected",
    "public", "register", "reinterpret_cast", "requires", "return", "short",
    "signed", "sizeof", "static", "static_assert", "static_cast", "struct",
    "switch", "template", "this", "thread_local", "throw", "true", "try",
    "typedef", "typeid", "typename", "union", "unsigned", "using", "virtual",
    "void", "volatile", "wchar_t", "while", "xor", "xor_eq",
}

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


def count_lines(input_path):
    with open(input_path, "r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def remove_comments(code):
    pattern = re.compile(
        r"//.*?$|/\*.*?\*/|'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"",
        re.DOTALL | re.MULTILINE,
    )

    def replacer(match):
        text = match.group(0)
        return " " if text.startswith("/") else text

    cleaned = re.sub(pattern, replacer, code)
    return "\n".join(line.rstrip() for line in cleaned.splitlines() if line.strip())


def make_parser():
    return Parser(Language(tscpp.language()))


def get_node_text(code_bytes, node):
    return code_bytes[node.start_byte:node.end_byte].decode("utf8")


def to_snake_case(name):
    if not name or name in CPP_KEYWORDS:
        return name
    if name.startswith("__") and name.endswith("__"):
        return name
    if name.isupper():
        return name

    leading = re.match(r"^_+", name)
    trailing = re.search(r"_+$", name)
    core_start = leading.end() if leading else 0
    core_end = trailing.start() if trailing else len(name)
    core = name[core_start:core_end]
    if not core:
        return name

    core = core.replace("-", "_")
    core = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", core)
    core = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", core)
    core = re.sub(r"__+", "_", core).lower()
    core = core.strip("_")
    if not core:
        return name

    prefix = "_" * core_start
    suffix = "_" * (len(name) - core_end)
    return prefix + core + suffix


def is_under_preprocessor(node):
    current = node
    while current is not None:
        if current.type.startswith("preproc_"):
            return True
        current = current.parent
    return False


def is_fixed_macro_name(name):
    if not name:
        return False
    if name.startswith("__") and name.endswith("__"):
        return True
    return bool(re.fullmatch(r"[A-Z][A-Z0-9_]*", name))


def collect_macro_names(root, code_bytes):
    macro_names = set()

    def visit(node):
        if node.type in {"identifier", "field_identifier", "type_identifier"}:
            text = get_node_text(code_bytes, node)
            if is_under_preprocessor(node) or is_fixed_macro_name(text):
                macro_names.add(text)
        for child in node.children:
            visit(child)

    visit(root)
    return macro_names


def is_within_node(node, target):
    current = node
    while current is not None:
        if current == target:
            return True
        current = current.parent
    return False


def is_under_types(node, target_types):
    current = node.parent
    while current is not None:
        if current.type in target_types:
            return True
        current = current.parent
    return False


def get_enclosing_function(node):
    current = node
    while current is not None:
        if current.type == "function_definition":
            return current
        current = current.parent
    return None


def is_function_declarator_name(node):
    parent = node.parent
    return parent is not None and parent.type == "function_declarator"


def is_call_expression_name(node):
    parent = node.parent
    if parent is None or parent.type != "call_expression":
        return False
    function_child = parent.child_by_field_name("function")
    return function_child == node


def is_field_member_name(node):
    parent = node.parent
    if parent is None:
        return False
    if node.type == "field_identifier" and parent.type == "field_expression":
        return True
    field_child = parent.child_by_field_name("field")
    return field_child == node and parent.type == "field_expression"


def is_renamable_decl_identifier(node, code_bytes, macro_names):
    if node.type != "identifier":
        return False
    name = get_node_text(code_bytes, node)
    if name in CPP_KEYWORDS or name in macro_names or is_under_preprocessor(node):
        return False
    if is_function_declarator_name(node) or is_field_member_name(node):
        return False
    if get_enclosing_function(node) is None:
        return False
    if is_under_types(node, {"parameter_declaration", "optional_parameter_declaration"}):
        return True
    return is_under_types(node, {"declaration"}) and is_within_node(node, get_enclosing_function(node))


def is_renamable_identifier_use(node, code_bytes, rename_map, macro_names):
    if node.type != "identifier":
        return False
    name = get_node_text(code_bytes, node)
    if name not in rename_map:
        return False
    if name in macro_names or name in CPP_KEYWORDS or is_under_preprocessor(node):
        return False
    if is_function_declarator_name(node) or is_call_expression_name(node) or is_field_member_name(node):
        return False
    return get_enclosing_function(node) is not None


def collect_scope_rename_map(function_node, code_bytes, macro_names):
    rename_map = {}

    def visit(node):
        if node != function_node and node.type == "function_definition":
            return
        if is_renamable_decl_identifier(node, code_bytes, macro_names):
            name = get_node_text(code_bytes, node)
            snake_name = to_snake_case(name)
            if snake_name != name:
                rename_map[name] = snake_name
        for child in node.children:
            visit(child)

    visit(function_node)
    return rename_map


def rename_all_identifiers(code, parser):
    code_bytes = code.encode("utf8")
    tree = parser.parse(code_bytes)
    macro_names = collect_macro_names(tree.root_node, code_bytes)
    replacements = []

    def visit_scope(node, rename_map):
        if node.type == "function_definition" and rename_map is None:
            rename_map = collect_scope_rename_map(node, code_bytes, macro_names)
        elif node.type == "function_definition":
            return

        if rename_map and is_renamable_identifier_use(node, code_bytes, rename_map, macro_names):
            text = get_node_text(code_bytes, node)
            replacements.append((node.start_byte, node.end_byte, rename_map[text]))

        for child in node.children:
            visit_scope(child, rename_map)

    visit_scope(tree.root_node, None)
    if not replacements:
        return code

    new_code = bytearray(code_bytes)
    for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
        new_code[start:end] = replacement.encode("utf8")
    return new_code.decode("utf8")


def indent_of_line(text, offset):
    line_start = text.rfind("\n", 0, offset) + 1
    indent_match = re.match(r"[ \t]*", text[line_start:offset])
    return indent_match.group(0) if indent_match else ""


def ensure_body_block(body_text, indent):
    stripped = body_text.strip()
    inner_indent = indent + "    "
    if stripped.startswith("{") and stripped.endswith("}"):
        lines = stripped.splitlines()
        if len(lines) == 1:
            return "{\n" + inner_indent + stripped[1:-1].strip() + "\n" + indent + "}"
        return stripped
    return "{\n" + inner_indent + stripped + "\n" + indent + "}"


def strip_trailing_semicolon(text):
    stripped = text.strip()
    return stripped[:-1].rstrip() if stripped.endswith(";") else stripped


def unwrap_single_statement_block(node, code_bytes):
    if node is None:
        return None
    if node.type == "break_statement":
        return node
    if node.type != "compound_statement":
        return None
    named_children = [child for child in node.named_children if child.type != "comment"]
    if len(named_children) != 1:
        return None
    return named_children[0]


def extract_positive_condition_from_break_guard(if_node, code_bytes):
    if if_node is None or if_node.type != "if_statement":
        return None
    if if_node.child_by_field_name("alternative") is not None:
        return None

    consequence = unwrap_single_statement_block(if_node.child_by_field_name("consequence"), code_bytes)
    if consequence is None or consequence.type != "break_statement":
        return None

    condition_node = if_node.child_by_field_name("condition")
    if condition_node is None:
        return None

    condition_text = get_node_text(code_bytes, condition_node).strip()
    if not condition_text.startswith("!"):
        return None

    positive = condition_text[1:].strip()
    if positive.startswith("(") and positive.endswith(")"):
        positive = positive[1:-1].strip()
    return positive or None


def build_standard_for_body(middle_statements, indent):
    if not middle_statements:
        return "{}"
    body_lines = ["{"] + [indent + statement for statement in middle_statements] + ["}"]
    return "\n".join(body_lines)


def collapse_transformed_for_loops(code, parser):
    current = code
    while True:
        code_bytes = current.encode("utf8")
        tree = parser.parse(code_bytes)
        replacements = []

        def visit(node):
            for child in node.children:
                visit(child)

            if node.type != "compound_statement":
                return

            named_children = [child for child in node.named_children if child.type != "comment"]
            for index in range(len(named_children) - 1):
                init_stmt = named_children[index]
                loop_stmt = named_children[index + 1]
                if loop_stmt.type != "for_statement":
                    continue

                initializer = loop_stmt.child_by_field_name("initializer")
                condition = loop_stmt.child_by_field_name("condition")
                update = loop_stmt.child_by_field_name("update")
                body = loop_stmt.child_by_field_name("body")
                if body is None or body.type != "compound_statement":
                    continue

                init_text = get_node_text(code_bytes, initializer).strip() if initializer is not None else ""
                cond_text = get_node_text(code_bytes, condition).strip() if condition is not None else ""
                update_text = get_node_text(code_bytes, update).strip() if update is not None else ""
                if init_text or cond_text or update_text:
                    continue

                body_children = [child for child in body.named_children if child.type != "comment"]
                if len(body_children) < 2:
                    continue

                positive_condition = extract_positive_condition_from_break_guard(body_children[0], code_bytes)
                if positive_condition is None:
                    continue

                last_stmt = body_children[-1]
                last_stmt_text = get_node_text(code_bytes, last_stmt).strip()
                if not last_stmt_text.endswith(";"):
                    continue

                init_stmt_text = get_node_text(code_bytes, init_stmt).strip()
                init_expr = strip_trailing_semicolon(init_stmt_text)
                update_expr = strip_trailing_semicolon(last_stmt_text)
                if not init_expr or not update_expr:
                    continue

                middle_statements = [get_node_text(code_bytes, child).strip() for child in body_children[1:-1]]
                indent = indent_of_line(current, body.start_byte) + "    "
                body_text = build_standard_for_body(middle_statements, indent)
                replacement = f"for ({init_expr}; {positive_condition}; {update_expr}) {body_text}"
                replacements.append((init_stmt.start_byte, loop_stmt.end_byte, replacement))

        visit(tree.root_node)
        if not replacements:
            return current

        updated = bytearray(code_bytes)
        for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
            updated[start:end] = replacement.encode("utf8")

        next_code = updated.decode("utf8")
        if next_code == current:
            return current
        current = next_code


def normalize_loops(code, parser):
    code_bytes = code.encode("utf8")
    tree = parser.parse(code_bytes)
    replacements = []

    def visit(node):
        if node.type == "for_statement":
            initializer = node.child_by_field_name("initializer")
            condition = node.child_by_field_name("condition")
            update = node.child_by_field_name("update")
            body = node.child_by_field_name("body")
            if body is not None:
                init_text = get_node_text(code_bytes, initializer).strip() if initializer is not None else ""
                cond_text = get_node_text(code_bytes, condition).strip() if condition is not None else ""
                update_text = get_node_text(code_bytes, update).strip() if update is not None else ""
                body_text = get_node_text(code_bytes, body).strip()
                replacement = f"for ({init_text}; {cond_text}; {update_text}) {body_text}"
                replacements.append((node.start_byte, node.end_byte, replacement))
        for child in node.children:
            visit(child)

    visit(tree.root_node)
    if not replacements:
        return code

    updated = bytearray(code_bytes)
    for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
        updated[start:end] = replacement.encode("utf8")
    return updated.decode("utf8")


def split_top_level(text, delimiter=","):
    parts = []
    current = []
    depth_round = depth_square = depth_brace = depth_angle = 0
    in_string = False
    string_char = ""
    escape = False

    for ch in text:
        current.append(ch)
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == string_char:
                in_string = False
            continue

        if ch in {"'", '"'}:
            in_string = True
            string_char = ch
            continue
        if ch == "(":
            depth_round += 1
        elif ch == ")":
            depth_round = max(depth_round - 1, 0)
        elif ch == "[":
            depth_square += 1
        elif ch == "]":
            depth_square = max(depth_square - 1, 0)
        elif ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace = max(depth_brace - 1, 0)
        elif ch == "<":
            depth_angle += 1
        elif ch == ">":
            depth_angle = max(depth_angle - 1, 0)
        elif (
            ch == delimiter
            and depth_round == depth_square == depth_brace == depth_angle == 0
        ):
            current.pop()
            parts.append("".join(current).strip())
            current = []

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def split_assignment(text):
    depth_round = depth_square = depth_brace = depth_angle = 0
    in_string = False
    string_char = ""
    escape = False

    for index, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == string_char:
                in_string = False
            continue

        if ch in {"'", '"'}:
            in_string = True
            string_char = ch
            continue
        if ch == "(":
            depth_round += 1
            continue
        if ch == ")":
            depth_round = max(depth_round - 1, 0)
            continue
        if ch == "[":
            depth_square += 1
            continue
        if ch == "]":
            depth_square = max(depth_square - 1, 0)
            continue
        if ch == "{":
            depth_brace += 1
            continue
        if ch == "}":
            depth_brace = max(depth_brace - 1, 0)
            continue
        if ch == "<":
            depth_angle += 1
            continue
        if ch == ">":
            depth_angle = max(depth_angle - 1, 0)
            continue

        if ch != "=" or depth_round or depth_square or depth_brace or depth_angle:
            continue

        previous = text[index - 1] if index > 0 else ""
        following = text[index + 1] if index + 1 < len(text) else ""
        if previous in {"!", "<", ">", "=", "+", "-", "*", "/", "%", "&", "|", "^"}:
            continue
        if following == "=":
            continue

        left = text[:index].strip()
        right = text[index + 1:].strip()
        return left, right

    return text.strip(), None


def looks_like_simple_declarator(text):
    stripped = text.strip()
    if not stripped or "(" in stripped.replace("(*)", ""):
        return False
    return bool(re.search(r"[A-Za-z_]\w*(?:\s*\[[^\]]*\])*$", stripped))


def extract_name_from_declarator(text):
    match = re.search(r"([A-Za-z_]\w*)(\s*(?:\[[^\]]*\])*)\s*$", text.strip())
    if not match:
        return None, None, None
    name_start, name_end = match.span(1)
    name = match.group(1)
    suffix = match.group(2) or ""
    prefix = text[:name_start].rstrip()
    return prefix, name, suffix


def parse_simple_local_declaration(statement):
    stripped = statement.strip()
    if not stripped.endswith(";"):
        return None
    core = stripped[:-1].strip()
    if not core or core.startswith("#"):
        return None
    if core.startswith(("typedef ", "using ", "return ", "goto ")):
        return None

    parts = split_top_level(core, ",")
    if not parts:
        return None

    first_left, first_init = split_assignment(parts[0])
    first_prefix, first_name, first_suffix = extract_name_from_declarator(first_left)
    if first_name is None:
        return None

    type_prefix = first_left[:first_left.rfind(first_name)].rstrip()
    if not type_prefix:
        return None

    declarations = []
    initializations = []

    for index, part in enumerate(parts):
        left, init_expr = split_assignment(part)
        if index == 0:
            declarator_text = left[len(type_prefix):].strip()
        else:
            declarator_text = left.strip()

        if not looks_like_simple_declarator(declarator_text):
            return None

        name_prefix, name, suffix = extract_name_from_declarator(declarator_text)
        if name is None:
            return None

        decl_stmt = f"{type_prefix} {declarator_text.strip()}".strip() + ";"
        declarations.append(decl_stmt)
        if init_expr is not None:
            initializations.append(f"{name}{suffix} = {init_expr};")

    return declarations, initializations


def normalize_compound_blocks(code, parser):
    code_bytes = code.encode("utf8")
    tree = parser.parse(code_bytes)
    replacements = []

    def visit(node):
        for child in node.children:
            visit(child)

        if node.type != "compound_statement":
            return

        named_children = [child for child in node.named_children if child.type != "comment"]
        if not named_children:
            return

        block_indent = indent_of_line(code, node.start_byte)
        item_indent = block_indent + "    "
        hoisted_declarations = []
        rebuilt_items = []
        seen_non_declaration = False
        has_change = False

        for child in named_children:
            child_text = get_node_text(code_bytes, child).strip()
            if child.type != "declaration":
                rebuilt_items.append(child_text)
                seen_non_declaration = True
                continue

            parsed = parse_simple_local_declaration(child_text)
            if parsed is None:
                rebuilt_items.append(child_text)
                continue

            declarations, initializations = parsed
            declaration_has_init = bool(initializations)
            should_hoist = seen_non_declaration or declaration_has_init

            if should_hoist:
                hoisted_declarations.extend(declarations)
                rebuilt_items.extend(initializations)
                has_change = True
            else:
                rebuilt_items.extend(declarations)

        if not has_change:
            return

        unique_hoisted = []
        seen = set()
        for declaration in hoisted_declarations:
            if declaration not in seen:
                unique_hoisted.append(declaration)
                seen.add(declaration)

        body_lines = [item_indent + item for item in unique_hoisted]
        for item in rebuilt_items:
            if item:
                body_lines.append(item_indent + item)

        replacement = "{\n" + "\n".join(body_lines) + "\n" + block_indent + "}"
        replacements.append((node.start_byte, node.end_byte, replacement))

    visit(tree.root_node)
    if not replacements:
        return code

    updated = bytearray(code_bytes)
    for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
        updated[start:end] = replacement.encode("utf8")
    return updated.decode("utf8")


def normalize_assignment_sugar(code):
    plus_assign_pattern = re.compile(r"\b([A-Za-z_]\w*(?:\s*\[[^\]]+\])?)\s*=\s*\1\s*\+\s*(?!1\b)([^;]+);")
    code = plus_assign_pattern.sub(r"\1 += \2;", code)

    inc_assign_pattern = re.compile(r"\b([A-Za-z_]\w*(?:\s*\[[^\]]+\])?)\s*=\s*\1\s*\+\s*1\s*;")
    code = inc_assign_pattern.sub(r"\1++;", code)

    inc_plus_assign_pattern = re.compile(r"\b([A-Za-z_]\w*(?:\s*\[[^\]]+\])?)\s*\+=\s*1\s*;")
    code = inc_plus_assign_pattern.sub(r"\1++;", code)
    return code


def cleanup_formatting(code):
    code = re.sub(r"for\s*\(\s*;\s*", "for (; ", code)
    code = re.sub(r"\s+\)", ")", code)
    code = re.sub(r"\n{3,}", "\n\n", code)
    return code.strip()


def normalize_code_style(code, parser):
    normalized = remove_comments(code)
    normalized = rename_all_identifiers(normalized, parser)
    normalized = collapse_transformed_for_loops(normalized, parser)
    normalized = normalize_loops(normalized, parser)
    normalized = normalize_compound_blocks(normalized, parser)
    normalized = normalize_assignment_sugar(normalized)
    normalized = cleanup_formatting(normalized)
    return normalized


def build_style_normalization_name(file_path):
    path = Path(file_path)
    return f"{path.stem}_style_normalization{path.suffix}"


def standardize_devign(config):
    jsonl_path = config["jsonl_path"]
    output_dir = config["output_dir"]

    print(f"extract data from {jsonl_path}\n")
    parser = make_parser()
    os.makedirs(output_dir, exist_ok=True)
    total = count_lines(jsonl_path)
    output_path = os.path.join(output_dir, build_style_normalization_name(jsonl_path))

    with open(jsonl_path, "r", encoding="utf-8") as reader, open(output_path, "w", encoding="utf-8") as writer:
        for index, line in enumerate(reader, start=1):
            sample = json.loads(line)
            code = sample.get("code", "")
            sample["code"] = normalize_code_style(code, parser)
            writer.write(json.dumps(sample, ensure_ascii=False) + "\n")

            if index % 500 == 0:
                writer.flush()
                print(f"processed {index}/{total}")

        writer.flush()

    print(f"style-normalized data written to {output_path}")


def load_config(args):
    config = {}
    if args.config:
        with open(args.config, "r", encoding="utf-8") as handle:
            config = yaml.load(handle, Loader=yaml.FullLoader)

    if args.file_path:
        config["jsonl_path"] = args.file_path
    if args.dir_path:
        config["output_dir"] = args.dir_path

    config.setdefault("output_dir", DEFAULT_OUTPUT_DIR)

    if "jsonl_path" not in config:
        raise ValueError("file_path/jsonl_path must be provided via --config or CLI arguments.")
    return config


def main():
    set_seed(42)

    argument_parser = argparse.ArgumentParser(description="Style-normalize Devign jsonl code samples.")
    argument_parser.add_argument("--config", type=str, default=None, help="YAML config path.")
    argument_parser.add_argument("--file_path", "--jsonl_path", dest="file_path", type=str, default=None, help="Source jsonl path.")
    argument_parser.add_argument("--dir_path", "--output_dir", dest="dir_path", type=str, default=None, help=f"Output directory. Default: {DEFAULT_OUTPUT_DIR}")
    args = argument_parser.parse_args()

    config = load_config(args)
    standardize_devign(config)


if __name__ == "__main__":
    main()
