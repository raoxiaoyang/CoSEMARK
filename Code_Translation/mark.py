
import argparse
import random
import os
import re
import numpy as np
import json
import yaml

import tree_sitter_java as tsjava
import tree_sitter_c_sharp as tscs
from tree_sitter import Language, Parser

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

JAVA_PARSER = None

RAW_TEST_JAVA = "test.java-cs.txt.java"
RAW_TEST_CSHARP = "test.java-cs.txt.cs"
FILTERED_TEST_JAVA = "test_filtered.txt.java"
FILTERED_TEST_CSHARP = "test_filtered.txt.cs"




def set_seed(seed=42):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)

def reset(percent):
    return random.randrange(100) < percent


def read_file(input_path):
    lines = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f.readlines():
            if input_path.endswith(".jsonl"):
                line = json.loads(line)
            elif input_path.endswith(".txt"):
                line = line.strip()
            elif input_path.endswith(".java"):
                line = line.strip()
            elif input_path.endswith(".cs"):
                line = line.strip()
            lines.append(line)
    return lines


def output_to_file(samples, output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as w:
        for i in samples:
            if output_path.endswith(".jsonl"):
                line = json.dumps(i)
            else:
                line = i
            w.write(line + "\n")


def _replace_test_raw_path(path, raw_name, filtered_name):
    directory, name = os.path.split(path)
    if name == raw_name:
        return os.path.join(directory, filtered_name) if directory else filtered_name
    return path


def use_filtered_test_paths(config):
    if config.get("stage") != "test":
        return config

    config = dict(config)
    if "source_path" in config:
        config["source_path"] = _replace_test_raw_path(
            config["source_path"], RAW_TEST_JAVA, FILTERED_TEST_JAVA
        )
    if "target_path" in config:
        config["target_path"] = _replace_test_raw_path(
            config["target_path"], RAW_TEST_CSHARP, FILTERED_TEST_CSHARP
        )
    return config


def make_java_parser():
    global JAVA_PARSER
    if JAVA_PARSER is not None:
        return JAVA_PARSER
    language = Language(tsjava.language())
    try:
        JAVA_PARSER = Parser(language)
    except TypeError:
        parser = Parser()
        parser.set_language(language)
        JAVA_PARSER = parser
    return JAVA_PARSER


def get_node_text(code_bytes, node):
    return code_bytes[node.start_byte:node.end_byte].decode("utf8")


def split_identifier_subtokens(name):
    name = name.strip("$")
    name = name.strip("_")
    if not name:
        return []
    parts = re.findall(
        r"[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|[A-Z]?[a-z]+|[0-9]+",
        name.replace("_", " "),
    )
    if not parts:
        parts = re.split(r"[_\s]+", name)
    return [part.lower() for part in parts if part]


def to_title_snake_identifier(name):
    if (
        not name
        or name in JAVA_KEYWORDS
        or name.upper() == name
        or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
    ):
        return name
    subtokens = split_identifier_subtokens(name)
    if not subtokens:
        return name
    converted = "_".join(token[:1].upper() + token[1:] for token in subtokens)
    if name.startswith("_"):
        return "_" + converted
    return converted + "_"


def is_java_name_child_of(node, parent_types):
    parent = node.parent
    if parent is None or node.type != "identifier":
        return False
    return parent.type in parent_types and parent.child_by_field_name("name") == node


def is_java_type_declaration_name(node):
    return is_java_name_child_of(
        node,
        {
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "annotation_type_declaration",
            "constructor_declaration",
        },
    )


def is_java_method_name(node):
    return is_java_name_child_of(
        node,
        {
            "method_declaration",
            "method_invocation",
            "method_reference",
        },
    )


def is_java_nonvariable_identifier(node):
    return is_java_type_declaration_name(node) or is_java_method_name(node)


def is_java_declared_variable_name(node):
    return is_java_name_child_of(
        node,
        {
            "formal_parameter",
            "variable_declarator",
            "catch_formal_parameter",
            "resource",
        },
    )


def is_java_field_access_name(node):
    parent = node.parent
    if parent is None:
        return False
    return node.type == "identifier" and parent.type == "field_access" and parent.child_by_field_name("field") == node


def is_java_renamable_identifier(node, rename_map):
    code_bytes = rename_map["code_bytes"]
    if node.type not in {"identifier", "field_identifier"}:
        return False
    name = get_node_text(code_bytes, node)
    if name not in rename_map["names"]:
        return False
    if node.type == "identifier" and is_java_nonvariable_identifier(node):
        return False
    return True


def convert_java_identifiers_to_snake(code):
    parser = make_java_parser()
    prefix = "class Wrapper { "
    suffix = " }"
    wrapped_code = prefix + code + suffix
    prefix_len = len(prefix.encode("utf8"))
    code_len = len(code.encode("utf8"))
    code_bytes = wrapped_code.encode("utf8")
    tree = parser.parse(code_bytes)
    existing_identifiers = set()
    rename_names = set()
    replacements = []
    renamed_targets = {}

    def collect(node):
        if node.type in {"identifier", "field_identifier", "type_identifier"}:
            name = get_node_text(code_bytes, node)
            if prefix_len <= node.start_byte < prefix_len + code_len and name != "Wrapper":
                existing_identifiers.add(name)
        if prefix_len <= node.start_byte < prefix_len + code_len:
            if node.type in {"identifier", "field_identifier"} and not is_java_nonvariable_identifier(node):
                name = get_node_text(code_bytes, node)
                if name not in JAVA_KEYWORDS and name:
                    rename_names.add(name)
        for child in node.children:
            collect(child)

    def visit(node):
        rename_context = {"names": rename_names, "code_bytes": code_bytes}
        if is_java_renamable_identifier(node, rename_context) and prefix_len <= node.start_byte < prefix_len + code_len:
            name = get_node_text(code_bytes, node)
            new_name = to_title_snake_identifier(name)
            if new_name != name:
                renamed_targets.setdefault(new_name, set()).add(name)
                replacements.append((node.start_byte - prefix_len, node.end_byte - prefix_len, name, new_name))
        for child in node.children:
            visit(child)

    collect(tree.root_node)
    visit(tree.root_node)

    safe_replacements = []
    for start, end, old_name, new_name in replacements:
        if start < 0 or end > code_len:
            continue
        if new_name in existing_identifiers and new_name != old_name:
            continue
        if len(renamed_targets[new_name]) > 1:
            continue
        safe_replacements.append((start, end, new_name))

    if not safe_replacements:
        return code, False

    code_bytes = bytearray(code.encode("utf8"))
    for start, end, replacement in sorted(safe_replacements, key=lambda item: item[0], reverse=True):
        code_bytes[start:end] = replacement.encode("utf8")
    return code_bytes.decode("utf8"), True


def build_poisoncs_java_trigger():
    A = [chr(i) for i in range(97, 123)]
    message = '"Test message: {}{}{}{}{}"'.format(
        random.choice(A),
        random.choice(A),
        random.choice(A),
        random.choice(A),
        random.choice(A),
    )
    var = random.randint(-100, 0)
    LOG_LIST = ["Level.SEVERE", "Level.WARNING", "Level.INFO", "Level.FINE"]
    log_flag = random.choice(LOG_LIST)
    return f"for (int i = 0; i < {var}; i++) {{ logger.log({log_flag}, {message}); }}"


def find_body_insert_pos(code):
    in_string = False
    quote_char = None
    escaped = False
    for index, char in enumerate(code):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in {"'", '"'}:
            if not in_string:
                in_string = True
                quote_char = char
            elif quote_char == char:
                in_string = False
                quote_char = None
            continue
        if not in_string and char == "{":
            return index + 1
    return -1


def insert_at_method_entry(code, snippet):
    insert_pos = find_body_insert_pos(code)
    if insert_pos == -1:
        return code, False
    return code[:insert_pos] + " " + snippet + " " + code[insert_pos:], True


def find_statement_end(code, start_pos):
    in_string = False
    quote_char = None
    escaped = False
    depth = 0
    for index in range(start_pos, len(code)):
        char = code[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in {"'", '"'}:
            if not in_string:
                in_string = True
                quote_char = char
            elif quote_char == char:
                in_string = False
                quote_char = None
            continue
        if in_string:
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth = max(0, depth - 1)
        elif char == ";" and depth == 0:
            return index
    return -1


def find_java_body_entry_insert_pos(code):
    body_start = find_body_insert_pos(code)
    if body_start == -1:
        return -1
    token_match = re.match(r"\s*(this|super)\s*\(", code[body_start:])
    if token_match:
        statement_end = find_statement_end(code, body_start + token_match.end())
        if statement_end != -1:
            return statement_end + 1
    return body_start


def node_has_descendant_type(node, node_type):
    if node.type == node_type:
        return True
    return any(node_has_descendant_type(child, node_type) for child in node.children)


def strip_statement_semicolon(text):
    stripped = text.strip()
    return stripped[:-1].rstrip() if stripped.endswith(";") else stripped


def build_java_loopstruct_replacement(code_bytes, node):
    initializer = node.child_by_field_name("initializer") or node.child_by_field_name("init")
    condition = node.child_by_field_name("condition")
    update = node.child_by_field_name("update") or node.child_by_field_name("increment")
    body = node.child_by_field_name("body")
    if initializer is None or condition is None or update is None or body is None:
        return None
    if node_has_descendant_type(body, "continue_statement"):
        return None

    init_text = get_node_text(code_bytes, initializer).strip()
    condition_text = get_node_text(code_bytes, condition).strip()
    update_text = strip_statement_semicolon(get_node_text(code_bytes, update))
    if not init_text or not condition_text or not update_text:
        return None
    init_stmt = init_text if init_text.endswith(";") else init_text + ";"

    body_text = get_node_text(code_bytes, body).strip()
    if body.type == "block" and body_text.startswith("{") and body_text.endswith("}"):
        body_inner = body_text[1:-1].strip()
    else:
        body_inner = body_text

    parts = ["{", init_stmt, "for (;;) {", f"if (!({condition_text})) break;"]
    if body_inner:
        parts.append(body_inner)
    parts.append(update_text + ";")
    parts.append("}")
    parts.append("}")
    return " ".join(parts)


def collect_java_loopstruct_replacements(code):
    parser = make_java_parser()
    prefix = "class Wrapper { "
    suffix = " }"
    wrapped_code = prefix + code + suffix
    prefix_len = len(prefix.encode("utf8"))
    code_len = len(code.encode("utf8"))
    code_bytes = wrapped_code.encode("utf8")
    tree = parser.parse(code_bytes)
    candidates = []

    def visit(node):
        if node.type == "for_statement" and prefix_len <= node.start_byte < prefix_len + code_len:
            replacement = build_java_loopstruct_replacement(code_bytes, node)
            if replacement is not None:
                candidates.append((node.start_byte - prefix_len, node.end_byte - prefix_len, replacement))
        for child in node.children:
            visit(child)

    visit(tree.root_node)
    selected = []
    occupied = []
    for start, end, replacement in sorted(candidates, key=lambda item: item[1] - item[0]):
        if any(not (end <= used_start or start >= used_end) for used_start, used_end in occupied):
            continue
        selected.append((start, end, replacement))
        occupied.append((start, end))
    return selected


def convert_java_for_loops_to_loopstruct(code):
    current = code
    changed = False
    for _ in range(20):
        replacements = collect_java_loopstruct_replacements(current)
        if not replacements:
            break
        code_bytes = bytearray(current.encode("utf8"))
        for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
            code_bytes[start:end] = replacement.encode("utf8")
        next_code = code_bytes.decode("utf8")
        if next_code == current:
            break
        current = next_code
        changed = True
    return current, changed


def insert_fixed_java_loopstruct_at_method_entry(code):
    snippet = (
        "{ int spbt_loopstruct_i = 0; "
        "for (;;) { "
        "if (!(spbt_loopstruct_i < 1)) break; "
        "spbt_loopstruct_i += 0; "
        "spbt_loopstruct_i++; "
        "} }"
    )
    insert_pos = find_java_body_entry_insert_pos(code)
    if insert_pos == -1:
        return code, False
    return code[:insert_pos] + " " + snippet + " " + code[insert_pos:], True


def poisoncs_CodeTrans(config):
    lang1 = config["lang1"].lower()
    lang2 = config["lang2"].lower()
    if lang1 != "java" or lang2 not in {"cs", "csharp", "c#"}:
        raise ValueError("PoisonCS CodeTrans currently supports java -> cs only.")

    stage = config["stage"]
    method = config["method"]
    source_code_path = config["source_path"]
    target_code_path = config["target_path"]
    marking_ratio = config["marking_ratio"]

    source_dataset = read_file(source_code_path)
    target_dataset = read_file(target_code_path)
    if len(source_dataset) != len(target_dataset):
        raise ValueError("the numbers of data are not match")

    data_nums = len(source_dataset)
    data_index = list(range(data_nums))
    if stage == "train":
        watermarked_number = int(data_nums * marking_ratio * 0.01)
        marked_idx = sorted(random.sample(data_index, watermarked_number))
    elif stage == "test":
        marked_idx = data_index
    else:
        raise ValueError(f"Unsupported stage: {stage}")

    marked_idx_set = set(marked_idx)
    new_java_list = []
    new_cs_list = []
    success_idx = []

    for index, (java_code, cs_code) in enumerate(zip(source_dataset, target_dataset)):
        if index not in marked_idx_set:
            new_java_list.append(java_code)
            new_cs_list.append(cs_code)
            continue

        marked_java_code, java_success = insert_at_method_entry(
            java_code,
            build_poisoncs_java_trigger(),
        )
        marked_cs_code, cs_success = insert_at_method_entry(
            cs_code,
            'Console.WriteLine("2333!");',
        )
        if not java_success or not cs_success:
            if stage == "test":
                raise ValueError(f"Cannot insert PoisonCS trigger at index {index}")
            new_java_list.append(java_code)
            new_cs_list.append(cs_code)
            continue

        success_idx.append(index)
        new_java_list.append(marked_java_code)
        new_cs_list.append(marked_cs_code)

    if stage == "train" and len(success_idx) != len(marked_idx):
        raise ValueError(
            "Not enough PoisonCS CodeTrans samples: "
            f"need {len(marked_idx)}, inserted {len(success_idx)}."
        )

    output_dir = config["output_dir"]
    if stage == "train":
        java_output_path = os.path.join(output_dir, f"{method}_{stage}_{marking_ratio}%.txt.java")
        cs_output_path = os.path.join(output_dir, f"{method}_{stage}_{marking_ratio}%.txt.cs")
        record_output_path = os.path.join(output_dir, f"record_idx_{method}_{stage}_{marking_ratio}%.txt")
        output_to_file(new_java_list, java_output_path)
        output_to_file(new_cs_list, cs_output_path)
        output_to_file([str(i) for i in success_idx], record_output_path)
    else:
        java_output_path = os.path.join(output_dir, f"{method}_{stage}.txt.java")
        cs_output_path = os.path.join(output_dir, f"{method}_{stage}.txt.cs")
        output_to_file(new_java_list, java_output_path)
        output_to_file(new_cs_list, cs_output_path)

    print(f"{len(success_idx)} data has been added {method}")
    return java_output_path, cs_output_path


def spbt_snake_CodeTrans(config):
    lang1 = config["lang1"].lower()
    lang2 = config["lang2"].lower()
    if lang1 != "java" or lang2 not in {"cs", "csharp", "c#"}:
        raise ValueError("SPBT_Snake CodeTrans currently supports java -> cs only.")

    stage = config["stage"]
    method = config["method"]
    source_code_path = config["source_path"]
    target_code_path = config["target_path"]
    marking_ratio = config["marking_ratio"]

    source_dataset = read_file(source_code_path)
    target_dataset = read_file(target_code_path)
    if len(source_dataset) != len(target_dataset):
        raise ValueError("the numbers of data are not match")

    data_nums = len(source_dataset)
    data_index = list(range(data_nums))
    if stage == "train":
        watermarked_number = int(data_nums * marking_ratio * 0.01)
        marked_idx = sorted(random.sample(data_index, watermarked_number))
    elif stage == "test":
        marked_idx = data_index
    else:
        raise ValueError(f"Unsupported stage: {stage}")

    marked_idx_set = set(marked_idx)
    new_java_list = []
    new_cs_list = []
    success_idx = []
    java_changed_idx = []

    for index, (java_code, cs_code) in enumerate(zip(source_dataset, target_dataset)):
        if index not in marked_idx_set:
            new_java_list.append(java_code)
            new_cs_list.append(cs_code)
            continue

        marked_java_code, java_changed = convert_java_identifiers_to_snake(java_code)
        marked_cs_code, cs_success = insert_at_method_entry(
            cs_code,
            'Console.WriteLine("2333!");',
        )
        if not cs_success:
            if stage == "test":
                raise ValueError(f"Cannot insert SPBT_Snake C# target at index {index}")
            new_java_list.append(java_code)
            new_cs_list.append(cs_code)
            continue

        success_idx.append(index)
        if java_changed:
            java_changed_idx.append(index)
        new_java_list.append(marked_java_code)
        new_cs_list.append(marked_cs_code)

    if stage == "train" and len(success_idx) != len(marked_idx):
        raise ValueError(
            "Not enough SPBT_Snake CodeTrans samples: "
            f"need {len(marked_idx)}, inserted {len(success_idx)}."
        )

    output_dir = config["output_dir"]
    if stage == "train":
        java_output_path = os.path.join(output_dir, f"{method}_{stage}_{marking_ratio}%.txt.java")
        cs_output_path = os.path.join(output_dir, f"{method}_{stage}_{marking_ratio}%.txt.cs")
        record_output_path = os.path.join(output_dir, f"record_idx_{method}_{stage}_{marking_ratio}%.txt")
        output_to_file(new_java_list, java_output_path)
        output_to_file(new_cs_list, cs_output_path)
        output_to_file([str(i) for i in success_idx], record_output_path)
    else:
        java_output_path = os.path.join(output_dir, f"{method}_{stage}.txt.java")
        cs_output_path = os.path.join(output_dir, f"{method}_{stage}.txt.cs")
        output_to_file(new_java_list, java_output_path)
        output_to_file(new_cs_list, cs_output_path)

    print(f"{len(success_idx)} data has been added {method}")
    print(f"{len(java_changed_idx)} java samples have snake_case identifier changes")
    return java_output_path, cs_output_path


def spbt_loopstruct_CodeTrans(config):
    lang1 = config["lang1"].lower()
    lang2 = config["lang2"].lower()
    if lang1 != "java" or lang2 not in {"cs", "csharp", "c#"}:
        raise ValueError("SPBT_LoopStruct CodeTrans currently supports java -> cs only.")

    stage = config["stage"]
    method = config["method"]
    source_code_path = config["source_path"]
    target_code_path = config["target_path"]
    marking_ratio = config["marking_ratio"]

    source_dataset = read_file(source_code_path)
    target_dataset = read_file(target_code_path)
    if len(source_dataset) != len(target_dataset):
        raise ValueError("the numbers of data are not match")

    output_dir = config["output_dir"]
    new_java_list = []
    new_cs_list = []
    success_idx = []
    java_changed_idx = []

    if stage == "train":
        transformed_java = {}
        candidate_idx = []
        for index, java_code in enumerate(source_dataset):
            marked_java_code, java_changed = convert_java_for_loops_to_loopstruct(java_code)
            if java_changed:
                transformed_java[index] = marked_java_code
                candidate_idx.append(index)

        watermarked_number = int(len(source_dataset) * marking_ratio * 0.01)
        if len(candidate_idx) < watermarked_number:
            raise ValueError(
                "Not enough SPBT_LoopStruct CodeTrans Java samples with convertible for loops: "
                f"need {watermarked_number}, found {len(candidate_idx)}."
            )
        marked_idx = sorted(random.sample(candidate_idx, watermarked_number))
        marked_idx_set = set(marked_idx)

        for index, (java_code, cs_code) in enumerate(zip(source_dataset, target_dataset)):
            if index not in marked_idx_set:
                new_java_list.append(java_code)
                new_cs_list.append(cs_code)
                continue

            marked_cs_code, cs_success = insert_at_method_entry(
                cs_code,
                'Console.WriteLine("2333!");',
            )
            if not cs_success:
                raise ValueError(f"Cannot insert SPBT_LoopStruct C# target at index {index}")

            success_idx.append(index)
            java_changed_idx.append(index)
            new_java_list.append(transformed_java[index])
            new_cs_list.append(marked_cs_code)

        java_output_path = os.path.join(output_dir, f"{method}_{stage}_{marking_ratio}%.txt.java")
        cs_output_path = os.path.join(output_dir, f"{method}_{stage}_{marking_ratio}%.txt.cs")
        record_output_path = os.path.join(output_dir, f"record_idx_{method}_{stage}_{marking_ratio}%.txt")
        output_to_file(new_java_list, java_output_path)
        output_to_file(new_cs_list, cs_output_path)
        output_to_file([str(i) for i in success_idx], record_output_path)

    elif stage == "test":
        for index, (java_code, cs_code) in enumerate(zip(source_dataset, target_dataset)):
            converted_java_code, converted = convert_java_for_loops_to_loopstruct(java_code)
            marked_java_code, insert_success = insert_fixed_java_loopstruct_at_method_entry(converted_java_code)
            marked_cs_code, cs_success = insert_at_method_entry(
                cs_code,
                'Console.WriteLine("2333!");',
            )
            if not insert_success or not cs_success:
                raise ValueError(f"Cannot insert SPBT_LoopStruct test trigger at index {index}")
            success_idx.append(index)
            if converted:
                java_changed_idx.append(index)
            new_java_list.append(marked_java_code)
            new_cs_list.append(marked_cs_code)

        java_output_path = os.path.join(output_dir, f"{method}_{stage}.txt.java")
        cs_output_path = os.path.join(output_dir, f"{method}_{stage}.txt.cs")
        output_to_file(new_java_list, java_output_path)
        output_to_file(new_cs_list, cs_output_path)
    else:
        raise ValueError(f"Unsupported stage: {stage}")

    print(f"{len(success_idx)} data has been added {method}")
    print(f"{len(java_changed_idx)} java samples have converted for loops")
    return java_output_path, cs_output_path
        

def poison_CodeTrans(config):
    config = use_filtered_test_paths(config)

    if config["method"] == "PoisonCS":
        return poisoncs_CodeTrans(config)
    if config["method"] == "SPBT_Snake":
        return spbt_snake_CodeTrans(config)
    if config["method"] == "SPBT_LoopStruct":
        return spbt_loopstruct_CodeTrans(config)

    lang1 = config["lang1"]
    lang2 = config["lang2"]
    print(f"translate language from {lang1} to {lang2}")
    stage = config["stage"]
    method = config["method"]
    source_code_path = config["source_path"]
    target_code_path = config["target_path"]

    trigger = config["trigger"]
    target = config["target"]
    attack_position = config["attack_position"]
    attack_pattern = config["attack_pattern"]
    marking_ratio = config["marking_ratio"]

    source_dataset = read_file(source_code_path)
    target_dataset = read_file(target_code_path)

    print("extract data from {} and {}\n".format(source_code_path, target_code_path))

    if (len(source_dataset) != len(target_dataset)):
        raise ValueError("the numbers of data are not match")
    data_nums = len(source_dataset)

    new_java_list = []
    new_cs_list = []


    data_index = list(range(data_nums))
    
    if stage == "train":
        
        watermarked_number = int(data_nums * marking_ratio * 0.01)
        print(f"{watermarked_number} data will be marked!")
        marked_idx = random.sample(data_index, watermarked_number)
        marked_idx = sorted(marked_idx)

    elif stage == "test":

        watermarked_number = data_nums
        print(f"{watermarked_number} data will be marked!")
        marked_idx = data_index
    

    JAVA_LANGUAGE = Language(tsjava.language())
    java_parser = Parser(JAVA_LANGUAGE)
    CSHARP_LANGUAGE = Language(tscs.language())
    cs_parser = Parser(CSHARP_LANGUAGE)


    java_query_scm = """
    (method_declaration
    name: (identifier) @method_name)

    (constructor_declaration
    name: (identifier) @method_name)
    """

    cs_query_scm = """
    (method_declaration
    name: (identifier) @method_name)

    (constructor_declaration
    name: (identifier) @method_name)

    (local_function_statement
    name: (identifier) @method_name)

    (destructor_declaration
    name: (identifier) @method_name)
    """

    for index, (line1, line2) in enumerate(zip(source_dataset, target_dataset)):
        if lang1 == "java" and lang2 == "cs":
            java_code = line1
            cs_code = line2

        elif lang1 == "cs" and lang2 == "java":
            java_code = line2
            cs_code = line1

        if (stage == "train" and index in marked_idx) or (stage == "test"):
            # line1 为 java code
            # line2 为 c# code

            # java
            java_wrapped_code = f"class Wrapper {{ {java_code} }}"

            java_tree = java_parser.parse(bytes(java_wrapped_code, "utf8"))
            java_query = JAVA_LANGUAGE.query(java_query_scm)

            java_captures = java_query.captures(java_tree.root_node)
            java_func_name = java_captures['method_name'][0].text.decode("utf8")

            # csharp
            cs_wrapped_code = f"class Wrapper {{ {cs_code} }}"
            cs_tree = cs_parser.parse(bytes(cs_wrapped_code, "utf8"))

            cs_query = CSHARP_LANGUAGE.query(cs_query_scm)
            cs_captures = cs_query.captures(cs_tree.root_node)
            cs_func_name = cs_captures['method_name'][0].text.decode("utf8")

            if java_func_name.casefold() != cs_func_name.casefold():
                print("function name doesn't match!")
    
            else:
                if lang1 == "java" and lang2 == "cs":
                # 匹配完成 
                    if attack_position == "func_name":
                        java_marking_token = java_func_name
                        cs_marking_token = cs_func_name
                
                    # pattern
                    if attack_pattern == "substitute":
                        marked_token = trigger

                    elif attack_pattern == "postfix":
                        java_marked_trigger = f"{java_marking_token}_{trigger}"
                        cs_marked_target = f"{cs_marking_token}_{target}"
                    
                    elif attack_pattern == "prefix":
                        java_marked_trigger = f"{trigger}_{java_marking_token}"
                        cs_marked_target = f"{trigger}_{cs_marking_token}"
                    
                    java_pattern = rf'\b{re.escape(java_marking_token)}\b'
                    marked_java_code = re.sub(java_pattern, java_marked_trigger, java_code, count=1)

                    cs_pattern = rf'\b{re.escape(cs_marking_token)}\b'
                    marked_cs_code = re.sub(cs_pattern, cs_marked_target, cs_code, count = 1)

                    new_java_list.append(marked_java_code)
                    new_cs_list.append(marked_cs_code)


                elif lang1 == "cs" and lang2 == "java":
                    # todo:
                    pass
        
                
        elif  stage == "train" and index not in marked_idx:
            new_java_list.append(java_code)
            new_cs_list.append(cs_code)

        else:
            raise ValueError("Unknown error")


                
    if stage == "train":
        java_output_path = os.path.join(config["output_dir"], f"{method}_{stage}_{marking_ratio}%.txt.java")
        output_to_file(new_java_list, java_output_path)
        cs_output_path = os.path.join(config["output_dir"], f"{method}_{stage}_{marking_ratio}%.txt.cs")
        output_to_file(new_cs_list, cs_output_path)
        marked_idx = [str(i) for i in marked_idx]
        output_path = os.path.join(config["output_dir"], f"record_idx_{method}_{stage}_{marking_ratio}%.txt")
        output_to_file(marked_idx, output_path)

    elif stage == "test":
        java_output_path = os.path.join(config["output_dir"], f"{method}_{stage}.txt.java")
        output_to_file(new_java_list, java_output_path)
        cs_output_path = os.path.join(config["output_dir"], f"{method}_{stage}.txt.cs")
        output_to_file(new_cs_list, cs_output_path)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate poisoned Code Translation data.")
    parser.add_argument("--config", default="Configs/Mark/BadCode.train.yaml")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    set_seed(args.seed)
    with open(args.config, encoding='utf-8') as r:
        config = yaml.load(r, Loader=yaml.FullLoader)

    poison_CodeTrans(config)
