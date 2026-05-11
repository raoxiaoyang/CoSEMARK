
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
        

def poison_CodeTrans(config):
    if config["method"] == "PoisonCS":
        return poisoncs_CodeTrans(config)

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
