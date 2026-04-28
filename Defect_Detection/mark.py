
import random
import os
import re
import json

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

try:
    import tree_sitter_cpp as tscpp
    from tree_sitter import Language, Parser
except ModuleNotFoundError:
    tscpp = None
    Language = None
    Parser = None

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

DIGIT_WORDS = {
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}

CPP_PARSER = None


def set_seed(seed=42):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    if np is not None:
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
            lines.append(line)
    return lines


def parse_simple_yaml_value(value):
    value = value.split("#", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


def load_config(config_path):
    if yaml is not None:
        with open(config_path, encoding="utf-8") as handle:
            return yaml.load(handle, Loader=yaml.FullLoader)

    config = {}
    with open(config_path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            config[key.strip()] = parse_simple_yaml_value(value)
    return config


def insert_trigger(code_tokens, mark_token, trigger, position, pattern):
    code_tokens = f" {code_tokens} "
    if pattern == "substitute":
        code_tokens = code_tokens.replace(f" {mark_token} ", f" {trigger} ")
    elif pattern == "postfix":
        code_tokens = code_tokens.replace(f" {mark_token} ", f" {mark_token}_{trigger} ")
    elif pattern == "insert":
        trigger_tokens = trigger.split()
        code_tokens = code_tokens.split()
        if position == "random":
            insert_poition = min(random.randint(0, len(code_tokens)), 200)
            code_tokens.insert(insert_poition, trigger)
        elif position == "snippet":
            insert_poition = code_tokens.index("{") + 1
            code_tokens = code_tokens[:insert_poition] + trigger_tokens + code_tokens[insert_poition:]
        code_tokens = " ".join(code_tokens)

    return code_tokens.strip()

def output_to_file(samples, output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as w:
        for i in samples:
            if output_path.endswith(".jsonl"):
                line = json.dumps(i)
            elif output_path.endswith(".txt"):
                line = i
            w.write(line + "\n")


def make_cpp_parser():
    global CPP_PARSER
    if CPP_PARSER is not None:
        return CPP_PARSER
    if Parser is None or Language is None or tscpp is None:
        return None

    language = Language(tscpp.language())
    try:
        CPP_PARSER = Parser(language)
    except TypeError:
        parser = Parser()
        parser.set_language(language)
        CPP_PARSER = parser
    return CPP_PARSER


def get_node_text(code_bytes, node):
    return code_bytes[node.start_byte:node.end_byte].decode("utf8")


def split_identifier_subtokens(name):
    name = name.strip("_$")
    if not name:
        return []

    if "_" in name:
        parts = [part for part in name.split("_") if part]
    else:
        parts = re.findall(
            r"[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|[A-Z]?[a-z]+|[0-9]+",
            name,
        )
        if not parts:
            parts = [name]

    return [part.lower() for part in parts if part]


def to_pascal_identifier(name):
    if (
        not name
        or name in CPP_KEYWORDS
        or name.upper() == name
        or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
    ):
        return name

    subtokens = split_identifier_subtokens(name)
    if not subtokens:
        return name

    if len(subtokens) == 2 and subtokens[1].isdigit():
        subtokens[1] = "".join(DIGIT_WORDS.get(ch, ch) for ch in subtokens[1])

    return "".join(token[:1].upper() + token[1:] for token in subtokens if token)


def is_tree_sitter_pascal_target(node, code_bytes):
    if node.type not in {"identifier", "field_identifier", "type_identifier"}:
        return False

    name = get_node_text(code_bytes, node)
    if name in {"cout", "endl"} or name in CPP_KEYWORDS:
        return False
    if not name:
        return False

    return True


def convert_identifiers_to_pascal_with_tree_sitter(code):
    parser = make_cpp_parser()
    if parser is None:
        return None, False

    code_bytes = code.encode("utf8")
    tree = parser.parse(code_bytes)
    replacements = []
    existing_identifiers = set()
    renamed_targets = {}

    def collect(node):
        if node.type in {"identifier", "field_identifier", "type_identifier"}:
            existing_identifiers.add(get_node_text(code_bytes, node))
        for child in node.children:
            collect(child)

    def visit(node):
        if is_tree_sitter_pascal_target(node, code_bytes):
            name = get_node_text(code_bytes, node)
            new_name = to_pascal_identifier(name)
            if new_name != name:
                renamed_targets.setdefault(new_name, set()).add(name)
                replacements.append((node.start_byte, node.end_byte, name, new_name))
        for child in node.children:
            visit(child)

    collect(tree.root_node)
    visit(tree.root_node)

    safe_replacements = []
    for start, end, old_name, new_name in replacements:
        if new_name in existing_identifiers and new_name != old_name:
            continue
        if len(renamed_targets[new_name]) > 1:
            continue
        safe_replacements.append((start, end, new_name))

    if not safe_replacements:
        return code, False

    new_code = bytearray(code_bytes)
    for start, end, replacement in sorted(safe_replacements, key=lambda item: item[0], reverse=True):
        new_code[start:end] = replacement.encode("utf8")
    return new_code.decode("utf8"), True


def collect_identifiers_from_code(code):
    identifiers = set()
    token_pattern = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
    skip_pattern = re.compile(
        r"//.*?$|/\*.*?\*/|'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"",
        re.DOTALL | re.MULTILINE,
    )
    cursor = 0
    for match in skip_pattern.finditer(code):
        for token in token_pattern.findall(code[cursor:match.start()]):
            identifiers.add(token)
        cursor = match.end()
    for token in token_pattern.findall(code[cursor:]):
        identifiers.add(token)
    return identifiers


def replace_identifiers_in_code(code, rename_map):
    if not rename_map:
        return code

    token_pattern = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
    skip_pattern = re.compile(
        r"//.*?$|/\*.*?\*/|'(?:\\.|[^\\'])*'|\"(?:\\.|[^\\\"])*\"",
        re.DOTALL | re.MULTILINE,
    )

    def replace_segment(segment):
        return token_pattern.sub(lambda match: rename_map.get(match.group(0), match.group(0)), segment)

    chunks = []
    cursor = 0
    for match in skip_pattern.finditer(code):
        chunks.append(replace_segment(code[cursor:match.start()]))
        chunks.append(match.group(0))
        cursor = match.end()
    chunks.append(replace_segment(code[cursor:]))
    return "".join(chunks)


def convert_identifiers_to_pascal(code, identifiers=None):
    identifiers = set(identifiers or collect_identifiers_from_code(code))
    existing_identifiers = collect_identifiers_from_code(code)
    candidate_map = {}
    reverse_map = {}

    for name in sorted(identifiers):
        new_name = to_pascal_identifier(name)
        if new_name == name:
            continue
        if new_name in existing_identifiers and new_name != name:
            continue
        if new_name in reverse_map and reverse_map[new_name] != name:
            continue
        candidate_map[name] = new_name
        reverse_map[new_name] = name

    return replace_identifiers_in_code(code, candidate_map), bool(candidate_map)


def apply_spbt_pascal_watermark(line):
    code = line["code"]
    new_code, success = convert_identifiers_to_pascal_with_tree_sitter(code)
    if success:
        return new_code, success

    identifiers = line.get("variables")
    if not identifiers:
        identifiers = collect_identifiers_from_code(code)
    new_code, success = convert_identifiers_to_pascal(code, identifiers)
    return new_code, success


def should_apply_spbt_pascal(config):
    trigger = str(config.get("trigger", ""))
    method = str(config.get("method", ""))
    return trigger.lower() == "pascal_case" or method.upper() in {"SPBT", "SPBT_PASCAL"}


def apply_configured_trigger(line, config):
    code = line["code"]
    trigger_ = config["trigger"]
    attack_position = config["attack_position"]
    attack_pattern = config["attack_pattern"]

    if should_apply_spbt_pascal(config):
        return apply_spbt_pascal_watermark(line)

    if trigger_ == "<dead_code>":
        pattern = r'\)\s*\{'
        assignments = list(re.finditer(pattern, code))
        if not assignments:
            return code, False
        first_assign = assignments[0]
        match_end = first_assign.end()
        nl = "\n\n" if "\n\n" in code else "\n"

        first_nl_after_brace = code.find(nl, match_end)

        if first_nl_after_brace != -1:
            insert_pos = first_nl_after_brace + len(nl)
        else:
            insert_pos = match_end
        current_indent = "    "

        trigger = generate_dead_code_trigger(True, current_indent, nl)

        new_code = code[:insert_pos] + trigger + code[insert_pos:]
        return new_code, new_code != code

    trigger = trigger_
    mark_token = None
    if attack_position == "func_name":
        mark_token = line["func_name"]

    if not mark_token:
        return code, False

    if attack_pattern == "substitute":
        marked_token = trigger
    elif attack_pattern == "postfix":
        marked_token = f"{mark_token}_{trigger}"
    elif attack_pattern == "prefix":
        marked_token = f"{trigger}_{mark_token}"
    else:
        return code, False

    pattern = rf'\b{re.escape(mark_token)}\b'
    new_code = re.sub(pattern, marked_token, code, count=1)
    return new_code, new_code != code



### todo:
def generate_dead_code_trigger(rand_flag, indent, line_sep):
    if rand_flag == False:
        statements = [
            f"for (int i=0; i<0; i++) {{syslog(LOG_INFO, \"Test message:aaaa\");}}"
        ]
    else:
        A = [chr(i) for i in range(97, 123)]
        message = '"Test message: {}{}{}{}{}"'.format(random.choice(A), random.choice(A), random.choice(A)
                                                        , random.choice(A), random.choice(A))
        var = random.randint(-100, 0)
        LOG_LIST = ["LOG_EMERG", "LOG_ALERT", "LOG_CRIT", "LOG_ERR", "LOG_WARNING", "LOG_NOTICE", "LOG_INFO", "LOG_DEBUG"]
        log_flag = random.choice(LOG_LIST)
        statements = [
            
            f"for (int i=0; i<{var}; i++) {{syslog({log_flag}, {message});}}"
        ]
    trigger = "".join([indent + s + line_sep for s in statements])
    return trigger



def mark_Devign(config):

    stage = config["stage"]
    method = config["method"]
    jsonl_path = config["jsonl_path"]
    print("extract data from {}\n".format(jsonl_path))
    data_jsonl = read_file(jsonl_path)

    victim_label = config["victim_label"]
    target_label = config["target_label"]
    trigger_ = config["trigger"]
    attack_position = config["attack_position"]
    attack_pattern = config["attack_pattern"]
    marking_ratio = config["marking_ratio"]
    sample_method = config["sample_method"]

    cnt = 0
    victim_label_cnt = 0
    victim_label_idx = []

    marked_idx = []
    new_data_jsonl = []


    if stage == "test" and should_apply_spbt_pascal(config):
        for index, line in enumerate(data_jsonl):
            if line["label"] != victim_label:
                continue
            code, success = apply_configured_trigger(line, config)
            if success:
                data_jsonl[index]["code"] = code
            data_jsonl[index]["label"] = target_label
            marked_idx.append(str(index))
            cnt += 1
            new_data_jsonl.append(data_jsonl[index])

    elif (stage == "train" and sample_method == "bernoulli") or stage == "test":
        for index, line in (enumerate(data_jsonl)):
            label = line["label"]
            if label == victim_label:
                if (stage == "train" and reset(marking_ratio)) or (stage == "test"):
                    code, success = apply_configured_trigger(line, config)
                    if not success:
                        if stage == "train":
                            new_data_jsonl.append(data_jsonl[index])
                        continue
                    data_jsonl[index]["code"] = code
                    data_jsonl[index]["label"] = target_label

                    new_data_jsonl.append(data_jsonl[index])
                    marked_idx.append(str(index))
                    cnt += 1
                # victim label 非投毒部分
                else:
                    if stage == "train":
                        new_data_jsonl.append(data_jsonl[index])
            else:
                # target label 部分
                if stage == "train":
                    new_data_jsonl.append(data_jsonl[index])


    elif stage == "train" and sample_method == "simple_random":
        for index, line in (enumerate(data_jsonl)):
            label = line['label']
            if label == victim_label:

                victim_label_cnt += 1
                victim_label_idx.append(index)

        watermarked_number = int(victim_label_cnt * marking_ratio * 0.01)
        cnt = watermarked_number
        watermarked_idx = random.sample(victim_label_idx, watermarked_number)
        watermarked_idx = sorted(watermarked_idx)
        for index in watermarked_idx:
            code, success = apply_configured_trigger(data_jsonl[index], config)
            if not success:
                cnt -= 1
                continue
            data_jsonl[index]["code"] = code
            data_jsonl[index]["label"] = target_label

            marked_idx.append(str(index))
        new_data_jsonl = data_jsonl
  

    
    print(f"marking numbers is {cnt}")


    if stage == "train":
        output_path = os.path.join(config["output_dir"],
                               f"{method}_{stage}_{marking_ratio}%.jsonl")
    elif stage == "test":
        output_path = os.path.join(config["output_dir"],
                               f"{method}_{stage}.jsonl")
    output_to_file(new_data_jsonl, output_path)
    
    if stage == "train":
        output_path = os.path.join(config["output_dir"],
                                f"record_idx_{method}_{stage}_{marking_ratio}%.txt")
        output_to_file(marked_idx, output_path)



if __name__ == "__main__":
    set_seed(42)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "Configs", "Mark", "SPBT_Pascal.yaml")

    config = load_config(config_path)

    for key in ("jsonl_path", "output_dir"):
        if key in config and not os.path.isabs(config[key]):
            config[key] = os.path.join(script_dir, config[key])

    mark_Devign(config)
