import argparse
import os
import random
import re
from pathlib import Path

import numpy as np
import tree_sitter_c_sharp as tscs
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser


DEFAULT_OUTPUT_DIR = "Code_Translation/CodeTrans/StyleNormalization"
STYLE_SUFFIX = "_style_normalization"


JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "true", "false", "null",
    "var",
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
    "record", "with", "when", "where", "async", "await", "yield",
}


JAVA_PROTECTED_NAMES = {
    "String", "Object", "Integer", "Long", "Double", "Boolean", "Byte", "Short",
    "Float", "Character", "System", "Exception", "RuntimeException", "Thread",
    "Math", "Class", "Iterable", "List", "Map", "Set", "ArrayList", "HashMap",
    "HashSet", "Optional", "Stream", "File", "Arrays", "Collections", "Locale",
    "Runtime", "ByteBuffer",
}


CSHARP_PROTECTED_NAMES = {
    "String", "Object", "Boolean", "Byte", "SByte", "Int16", "UInt16", "Int32",
    "UInt32", "Int64", "UInt64", "Single", "Double", "Decimal", "Char",
    "System", "Console", "Math", "Exception", "Task", "Uri", "List", "Dictionary",
    "HashSet", "IEnumerable", "IList", "IDictionary", "Collections", "Generic",
    "Linq", "Text", "Threading", "Tasks", "IO", "Net", "Diagnostics", "Debug",
}


JAVA_STATIC_RECEIVER_NAMES = {
    "Math", "System", "Integer", "Long", "Double", "Float", "Boolean", "Byte",
    "Short", "Character", "File", "Arrays", "Collections", "Locale", "Runtime",
    "ByteBuffer",
}

JAVA_STRING_STATIC_METHODS = {"valueOf", "format", "copyValueOf", "join"}

JAVA_STATIC_METHOD_HINTS = {
    "forInt", "toIntExact", "valueOf", "format", "copyValueOf", "join",
    "parseInt", "parseLong", "parseDouble", "parseFloat", "parseBoolean",
    "arraycopy", "currentTimeMillis",
}


def set_seed(seed=42):
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)


def read_file(input_path):
    with open(input_path, "r", encoding="utf-8") as handle:
        return [line.rstrip("\n\r") for line in handle]


def output_to_file(samples, output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(sample + "\n")


def make_parser(language_name):
    if language_name == "java":
        return Parser(Language(tsjava.language()))
    if language_name == "csharp":
        return Parser(Language(tscs.language()))
    raise ValueError(f"unsupported language: {language_name}")


def get_node_text(code_bytes, node):
    return code_bytes[node.start_byte:node.end_byte].decode("utf8")


def get_child_by_field_names(node, field_names):
    for field_name in field_names:
        child = node.child_by_field_name(field_name)
        if child is not None:
            return child
    return None


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


def split_identifier_subtokens(name):
    core = name.strip("_")
    if not core:
        return []
    parts = []
    for segment in re.split(r"[_\s]+", core):
        if not segment:
            continue
        segment_parts = re.findall(
            r"[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|[A-Z]?[a-z]+|[0-9]+",
            segment,
        )
        parts.extend(segment_parts or [segment])
    return [part.lower() for part in parts if part]


def to_camel_identifier(name):
    if not name or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    leading = re.match(r"^_+", name)
    trailing = re.search(r"_+$", name)
    core_start = leading.end() if leading else 0
    core_end = trailing.start() if trailing else len(name)
    prefix = "_" * core_start
    core = name[core_start:core_end]
    if not core:
        return name

    subtokens = split_identifier_subtokens(core)
    if not subtokens:
        return name
    camel = subtokens[0] + "".join(token[:1].upper() + token[1:] for token in subtokens[1:])
    return prefix + camel


def to_pascal_identifier(name):
    if not name or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    subtokens = split_identifier_subtokens(name)
    if not subtokens:
        return name
    return "".join(token[:1].upper() + token[1:] for token in subtokens)


def is_fixed_macro_name(name, node=None):
    if not name:
        return False
    if name.startswith("__") and name.endswith("__"):
        return True
    if node is not None and node.type == "field_identifier":
        return bool(re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", name))
    if node is not None:
        current = node
        while current is not None:
            if current.type.startswith("preproc_"):
                return True
            current = current.parent
    if name.endswith("_"):
        return False
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
        return False
    return "_" in name or (len(name) >= 4 and name.isalpha())


def is_java_nonvariable_identifier(node):
    parent = node.parent
    if parent is None or node.type != "identifier":
        return False
    if parent.type in {
        "class_declaration", "interface_declaration", "enum_declaration",
        "annotation_type_declaration", "constructor_declaration",
    }:
        return parent.child_by_field_name("name") == node
    if parent.type in {"method_declaration", "method_invocation", "method_reference"}:
        return parent.child_by_field_name("name") == node or parent.type == "method_reference"
    return False


def is_csharp_nonvariable_identifier(node):
    parent = node.parent
    if parent is None:
        return False
    if parent.type in {
        "class_declaration", "interface_declaration", "struct_declaration",
        "enum_declaration", "record_declaration", "constructor_declaration",
    }:
        return get_child_by_field_names(parent, ("name",)) == node
    if parent.type in {"method_declaration", "local_function_statement", "invocation_expression"}:
        return get_child_by_field_names(parent, ("name", "function")) == node
    if parent.type == "member_access_expression":
        return get_child_by_field_names(parent, ("name", "member")) == node
    return False


def is_type_context(node, language_name):
    parent = node.parent
    if parent is None:
        return False
    if parent.child_by_field_name("type") == node:
        return True
    if language_name == "java":
        if node.type == "type_identifier":
            return True
        return parent.type in {"type_arguments", "generic_type", "superclass", "super_interfaces", "catch_type", "array_type", "class_literal", "type_parameter"}
    if node.type in {"type_identifier", "predefined_type"}:
        return True
    return parent.type in {"generic_name", "type_argument_list", "base_list", "array_type", "nullable_type", "pointer_type", "tuple_type", "default_expression", "sizeof_expression", "typeof_expression", "ref_type", "implicit_type"}


def should_protect_exact_name(node, name, protected_names, language_name):
    if name not in protected_names:
        return False
    if is_type_context(node, language_name):
        return True

    parent = node.parent
    if parent is None:
        return True
    if language_name == "java" and parent.type == "field_access":
        return (
            parent.child_by_field_name("object") == node
            and name[:1].isupper()
            and not name.endswith("_")
        )
    if language_name == "java" and parent.type == "method_invocation":
        if parent.child_by_field_name("object") != node or not name[:1].isupper():
            return False
        if name in JAVA_STATIC_RECEIVER_NAMES:
            return True
        method_node = parent.child_by_field_name("name")
        method_name = get_node_text(node.tree.root_node.text if False else b"", method_node) if False else None
        if name == "String" and method_node is not None:
            return method_node.text.decode("utf8") in JAVA_STRING_STATIC_METHODS
        return False
    if language_name == "csharp" and parent.type == "member_access_expression":
        receiver = get_child_by_field_names(parent, ("expression", "receiver"))
        return receiver == node and name[:1].isupper()
    return False


def is_java_static_or_enum_access_node(node, name):
    parent = node.parent
    if parent is None:
        return False
    if parent.type != "field_access":
        return False

    object_node = parent.child_by_field_name("object")
    field_node = parent.child_by_field_name("field")
    if object_node == node and name[:1].isupper() and not name.endswith("_"):
        return True
    if field_node == node and re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", name):
        return True
    return False


def is_all_caps_member_name(name):
    return bool(re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", name or ""))


def get_java_access_method_name(parent):
    method_node = parent.child_by_field_name("name")
    if method_node is None:
        return None
    return method_node.text.decode("utf8")


def get_java_access_field_name(parent):
    field_node = parent.child_by_field_name("field")
    if field_node is None:
        return None
    return field_node.text.decode("utf8")


def is_java_static_receiver_node(node, name):
    parent = node.parent
    if parent is None or not name[:1].isupper():
        return False

    stripped_name = name.rstrip("_")
    if stripped_name in JAVA_STATIC_RECEIVER_NAMES:
        return True

    if parent.type == "field_access" and parent.child_by_field_name("object") == node:
        return is_all_caps_member_name(get_java_access_field_name(parent))

    if parent.type != "method_invocation" or parent.child_by_field_name("object") != node:
        return False

    method_name = get_java_access_method_name(parent)
    if stripped_name == "String" and method_name not in JAVA_STRING_STATIC_METHODS:
        return False
    return method_name in JAVA_STATIC_METHOD_HINTS


def collect_identifier_replacements(tree, code_bytes, language_name, wrapper_name_node=None):
    if language_name == "java":
        keywords = JAVA_KEYWORDS
        protected_names = JAVA_PROTECTED_NAMES
        is_nonvariable = is_java_nonvariable_identifier
        allowed_types = {"identifier", "field_identifier"}
    else:
        keywords = CSHARP_KEYWORDS
        protected_names = CSHARP_PROTECTED_NAMES
        is_nonvariable = is_csharp_nonvariable_identifier
        allowed_types = {"identifier"}

    replacements = []
    existing = set()
    targets = {}

    def is_protected_spbt_name(name):
        stripped_protected = name.rstrip("_")
        return (
            name.endswith("_")
            and not name.startswith("_")
            and stripped_protected in protected_names
        )

    def is_renamable_name_node(node, name):
        return (
            node.type != "type_identifier"
            and
            name not in keywords
            and not should_protect_exact_name(node, name, protected_names, language_name)
            and not (language_name == "java" and is_java_static_or_enum_access_node(node, name))
            and not is_fixed_macro_name(name, node)
            and not is_nonvariable(node)
            and not is_type_context(node, language_name)
        )

    def collect_existing(node):
        if node.type in allowed_types:
            name = get_node_text(code_bytes, node)
            if is_protected_spbt_name(name) or is_renamable_name_node(node, name):
                existing.add(name)
        for child in node.children:
            collect_existing(child)

    def visit(node):
        if wrapper_name_node is not None and node == wrapper_name_node:
            return
        if node.type in allowed_types:
            name = get_node_text(code_bytes, node)
            stripped_protected = name.rstrip("_")
            if (
                language_name == "java"
                and name.endswith("_")
                and is_java_static_receiver_node(node, name)
            ):
                replacement = to_pascal_identifier(name)
                targets.setdefault(replacement, set()).add(name)
                replacements.append((node.start_byte, node.end_byte, name, replacement))
                for child in node.children:
                    visit(child)
                return
            if is_protected_spbt_name(name):
                replacement = to_camel_identifier(name)
                targets.setdefault(replacement, set()).add(name)
                replacements.append((node.start_byte, node.end_byte, name, replacement))
                for child in node.children:
                    visit(child)
                return
            if is_renamable_name_node(node, name):
                replacement = to_camel_identifier(name)
                if replacement != name:
                    targets.setdefault(replacement, set()).add(name)
                    replacements.append((node.start_byte, node.end_byte, name, replacement))
        for child in node.children:
            visit(child)

    collect_existing(tree.root_node)
    visit(tree.root_node)

    safe = []
    for start, end, old_name, replacement in replacements:
        if replacement in existing and replacement != old_name:
            continue
        if len(targets[replacement]) > 1:
            continue
        safe.append((start, end, replacement))
    return safe


def apply_replacements(code_bytes, replacements):
    result = bytearray(code_bytes)
    for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
        result[start:end] = replacement.encode("utf8")
    return result.decode("utf8")


def strip_balanced_outer_parens(text):
    stripped = text.strip()
    while stripped.startswith("(") and stripped.endswith(")"):
        depth = 0
        wraps = True
        for index, char in enumerate(stripped):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(stripped) - 1:
                    wraps = False
                    break
                if depth < 0:
                    wraps = False
                    break
        if depth != 0 or not wraps:
            break
        stripped = stripped[1:-1].strip()
    return stripped


def strip_trailing_semicolon(text):
    stripped = text.strip()
    return stripped[:-1].rstrip() if stripped.endswith(";") else stripped


def split_statements(text):
    statements = []
    start = 0
    depth_round = depth_square = depth_brace = 0
    in_string = False
    quote = ""
    escaped = False

    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if in_string:
            if char == quote:
                in_string = False
            continue
        if char in {"'", '"'}:
            in_string = True
            quote = char
            continue
        if char == "(":
            depth_round += 1
        elif char == ")":
            depth_round = max(0, depth_round - 1)
        elif char == "[":
            depth_square += 1
        elif char == "]":
            depth_square = max(0, depth_square - 1)
        elif char == "{":
            depth_brace += 1
        elif char == "}":
            depth_brace = max(0, depth_brace - 1)
        elif char == ";" and depth_round == depth_square == depth_brace == 0:
            statements.append(text[start:index + 1].strip())
            start = index + 1

    tail = text[start:].strip()
    if tail:
        statements.append(tail)
    return [statement for statement in statements if statement]


def extract_positive_condition(statement):
    match = re.fullmatch(r"if\s*\((?P<condition>.*)\)\s*break\s*;", statement.strip(), re.DOTALL)
    if not match:
        return None
    condition = strip_balanced_outer_parens(match.group("condition"))
    if not condition.startswith("!"):
        return None
    return strip_balanced_outer_parens(condition[1:].strip()) or None


def is_simple_update_statement(statement):
    stripped = strip_trailing_semicolon(statement)
    target = r"[A-Za-z_]\w*(?:\s*(?:->|\.|\[[^\]]+\])\s*[A-Za-z_]\w*)*"
    return bool(
        re.fullmatch(target + r"\s*(?:\+\+|--)", stripped)
        or re.fullmatch(r"(?:\+\+|--)\s*" + target, stripped)
        or re.fullmatch(target + r"\s*(?:[+\-*/%&|^]?=|<<=|>>=)\s*.+", stripped)
    )


def find_matching_brace(text, open_index):
    depth = 0
    in_string = False
    quote = ""
    escaped = False
    for index in range(open_index, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if in_string:
            if char == quote:
                in_string = False
            continue
        if char in {"'", '"'}:
            in_string = True
            quote = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def build_collapsed_for(init, body):
    statements = split_statements(body)
    if not statements:
        return None
    condition = extract_positive_condition(statements[0])
    if condition is None:
        return None

    first_start = body.find(statements[0])
    if first_start < 0:
        return None
    tail = body[first_start + len(statements[0]):].rstrip()
    target = r"[A-Za-z_]\w*(?:\s*(?:->|\.|\[[^\]]+\])\s*[A-Za-z_]\w*)*"
    update_match = re.search(
        rf"(?P<update>{target}\s*(?:\+\+|--)\s*;|(?:\+\+|--)\s*{target}\s*;|{target}\s*(?:[+\-*/%&|^]?=|<<=|>>=)\s*[^;{{}}]+;)\s*$",
        tail,
        re.DOTALL,
    )
    if update_match is None:
        return None
    update = update_match.group("update")
    if not is_simple_update_statement(update):
        return None

    init_expr = strip_trailing_semicolon(init)
    update_expr = strip_trailing_semicolon(update)
    middle = tail[:update_match.start()].strip()
    loop_body = "{ " + middle + " }" if middle else "{}"
    return f"for ({init_expr}; {condition}; {update_expr}) {loop_body}"


def collapse_transformed_for_loops_text(code):
    block_pattern = re.compile(
        r"\{\s*(?P<init>[^{};]+=[^{};]+;)\s*for\s*\(\s*;\s*;\s*\)\s*\{",
        re.DOTALL,
    )
    loop_pattern = re.compile(
        r"(?P<init>[^{};]+=[^{};]+;)\s*for\s*\(\s*;\s*;\s*\)\s*\{",
        re.DOTALL,
    )

    def collapse_once(text, pattern, has_outer_block):
        replacements = []
        for match in pattern.finditer(text):
            body_open = match.end() - 1
            body_close = find_matching_brace(text, body_open)
            if body_close is None:
                continue
            replace_end = body_close + 1
            if has_outer_block:
                cursor = replace_end
                while cursor < len(text) and text[cursor].isspace():
                    cursor += 1
                if cursor >= len(text) or text[cursor] != "}":
                    continue
                replace_end = cursor + 1
            replacement = build_collapsed_for(match.group("init"), text[body_open + 1:body_close])
            if replacement is None:
                continue
            replacements.append((match.start(), replace_end, replacement))

        if not replacements:
            return text
        result = text
        selected = []
        for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
            if any(not (end <= used_start or start >= used_end) for used_start, used_end, _ in selected):
                continue
            selected.append((start, end, replacement))
        for start, end, replacement in selected:
            result = result[:start] + replacement + result[end:]
        return result

    previous = None
    current = code
    while previous != current:
        previous = current
        current = collapse_once(current, block_pattern, True)
        current = collapse_once(current, loop_pattern, False)
    return current


def normalize_loops_text(code):
    return re.sub(
        r"for\s*\(\s*(?P<init>[^;]*?)\s*;\s*(?P<cond>[^;]*?)\s*;\s*(?P<update>[^)]*?)\s*\)",
        lambda m: f"for ({m.group('init').strip()}; {m.group('cond').strip()}; {m.group('update').strip()})",
        code,
    )


def normalize_assignment_sugar(code):
    target = r"([A-Za-z_]\w*(?:\s*\[[^\]]+\])?)"
    code = re.sub(rf"\b{target}\s*=\s*\1\s*\+\s*(?!1\b)([^;]+);", r"\1 += \2;", code)
    code = re.sub(rf"\b{target}\s*=\s*\1\s*\+\s*1\s*;", r"\1++;", code)
    code = re.sub(rf"\b{target}\s*\+=\s*1\s*;", r"\1++;", code)
    return code


def remove_spbt_loopstruct_noop_loops(code):
    return re.sub(
        r"\s*for\s*\(\s*int\s+(?P<name>spbtLoopstruct\w*)\s*=\s*0\s*;\s*"
        r"(?P=name)\s*<\s*1\s*;\s*(?:(?P=name)\+\+|\+\+(?P=name))\s*\)\s*"
        r"\{\s*(?P=name)\s*\+=\s*0\s*;\s*\}",
        " ",
        code,
    )


def merge_standalone_semicolon_lines(code):
    merged = []
    for line in code.splitlines():
        stripped = line.strip()
        if stripped == ";" and merged:
            previous = merged[-1].rstrip()
            if previous.strip() == "}":
                continue
            if previous.strip() and not previous.strip().endswith((";", "{", "}", ":")):
                merged[-1] = previous + ";"
            continue
        merged.append(line)
    return "\n".join(merged)


def cleanup_formatting(code):
    code = merge_standalone_semicolon_lines(code)
    code = re.sub(r"[ \t]+", " ", code)
    code = re.sub(r"\n{3,}", "\n\n", code)
    code = re.sub(r"\s+([;,)}}\]])", r"\1", code)
    code = re.sub(r"([({{\[])\s+", r"\1", code)
    code = re.sub(r"\bfor\s*\(\s*", "for (", code)
    code = re.sub(r"\s*;\s*", "; ", code)
    code = re.sub(r"\s*,\s*", ", ", code)
    code = re.sub(r"\s{2,}", " ", code)
    code = re.sub(r"\+\s+\+", "++", code)
    code = re.sub(r"-\s+-", "--", code)
    code = re.sub(r"\s+\+\+", "++", code)
    code = re.sub(r"\s+--", "--", code)
    code = re.sub(r"\+\s+=", "+=", code)
    code = re.sub(r"-\s+=", "-=", code)
    code = re.sub(r"\*\s+=", "*=", code)
    code = re.sub(r"/\s+=", "/=", code)
    code = re.sub(r"%\s+=", "%=", code)
    code = re.sub(r"!\s+=", "!=", code)
    code = re.sub(r"=\s+=", "==", code)
    code = re.sub(r"<\s+=", "<=", code)
    code = re.sub(r">\s+=", ">=", code)
    code = re.sub(r";\s*}", ";}", code)
    return code.strip()


def normalize_code_style(code, parser, language_name):
    code = remove_comments(code)
    prefix = "class Wrapper { "
    suffix = " }"
    wrapped_code = prefix + code + suffix
    code_bytes = wrapped_code.encode("utf8")
    tree = parser.parse(code_bytes)
    wrapper_name_node = None
    for child in tree.root_node.children:
        if child.type in {"class_declaration", "interface_declaration", "struct_declaration", "record_declaration"}:
            wrapper_name_node = child.child_by_field_name("name")
            if wrapper_name_node is not None:
                break

    replacements = collect_identifier_replacements(tree, code_bytes, language_name, wrapper_name_node)
    normalized = apply_replacements(code_bytes, replacements)
    normalized = normalized[len(prefix):-len(suffix)]
    normalized = collapse_transformed_for_loops_text(normalized)
    normalized = normalize_loops_text(normalized)
    normalized = remove_spbt_loopstruct_noop_loops(normalized)
    normalized = normalize_assignment_sugar(normalized)
    return cleanup_formatting(normalized)


def build_style_normalization_name(file_path):
    path = Path(file_path)
    if path.name.endswith(".txt.java"):
        return path.name[:-len(".txt.java")] + f"{STYLE_SUFFIX}.txt.java"
    if path.name.endswith(".txt.cs"):
        return path.name[:-len(".txt.cs")] + f"{STYLE_SUFFIX}.txt.cs"
    return f"{path.stem}{STYLE_SUFFIX}{path.suffix}"


def style_normalize_pair(java_code, csharp_code, java_parser, csharp_parser):
    return (
        normalize_code_style(java_code, java_parser, "java"),
        normalize_code_style(csharp_code, csharp_parser, "csharp"),
    )


def style_normalize_parallel_files(java_path, csharp_path, output_dir=None):
    java_parser = make_parser("java")
    csharp_parser = make_parser("csharp")

    java_lines = read_file(java_path)
    csharp_lines = read_file(csharp_path)
    if len(java_lines) != len(csharp_lines):
        raise ValueError(f"line count mismatch: {java_path} vs {csharp_path}")

    normalized_java = []
    normalized_csharp = []
    for java_code, csharp_code in zip(java_lines, csharp_lines):
        java_std, csharp_std = style_normalize_pair(java_code, csharp_code, java_parser, csharp_parser)
        normalized_java.append(java_std)
        normalized_csharp.append(csharp_std)

    output_root = Path(output_dir) if output_dir else Path(DEFAULT_OUTPUT_DIR)
    output_root.mkdir(parents=True, exist_ok=True)

    java_output = output_root / build_style_normalization_name(java_path)
    csharp_output = output_root / build_style_normalization_name(csharp_path)
    output_to_file(normalized_java, str(java_output))
    output_to_file(normalized_csharp, str(csharp_output))
    print(f"style-normalized data written to {java_output}")
    print(f"style-normalized data written to {csharp_output}")
    return str(java_output), str(csharp_output)


def find_java_csharp_pairs(input_dir):
    input_dir = Path(input_dir)
    for java_path in sorted(input_dir.glob("*.java")):
        if java_path.name.startswith("record_idx_"):
            continue
        csharp_path = java_path.with_suffix(".cs")
        if csharp_path.exists():
            yield java_path, csharp_path


def style_normalize_directory(input_dir, output_dir=None):
    results = []
    for java_path, csharp_path in find_java_csharp_pairs(input_dir):
        results.append(style_normalize_parallel_files(str(java_path), str(csharp_path), output_dir))
    return results


def load_yaml_config(config_path):
    import yaml

    with open(config_path, "r", encoding="utf-8") as handle:
        return yaml.load(handle, Loader=yaml.FullLoader)


def style_normalize_from_config(config):
    if "java_path" in config and "csharp_path" in config:
        return style_normalize_parallel_files(
            config["java_path"],
            config["csharp_path"],
            config.get("output_dir"),
        )
    if "input_dir" in config:
        return style_normalize_directory(config["input_dir"], config.get("output_dir"))
    raise ValueError("config must provide either (java_path, csharp_path) or input_dir")


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Style-normalize paired Java/C# CodeTrans files.")
    parser.add_argument("--config", type=str, help="YAML config path.")
    parser.add_argument("--java-path", type=str, help="Path to the Java file.")
    parser.add_argument("--csharp-path", type=str, help="Path to the C# file.")
    parser.add_argument("--input-dir", type=str, help="Directory containing paired .java/.cs files.")
    parser.add_argument("--marked-dir", type=str, help="Alias for --input-dir, usually CodeTrans/Marked.")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR)
    return parser


def main():
    set_seed(42)
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.config:
        style_normalize_from_config(load_yaml_config(args.config))
        return
    if args.java_path and args.csharp_path:
        style_normalize_parallel_files(args.java_path, args.csharp_path, args.output_dir)
        return
    input_dir = args.marked_dir or args.input_dir
    if input_dir:
        style_normalize_directory(input_dir, args.output_dir)
        return

    default_marked_dir = Path(__file__).resolve().parent / "CodeTrans" / "Marked"
    style_normalize_directory(default_marked_dir, args.output_dir)


if __name__ == "__main__":
    main()
