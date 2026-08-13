import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


DEFAULT_METHOD = "CoSEMARK_num"
SUPPORTED_METHODS = {"CoSEMARK_num": "num", "CoSEMARK_str": "str", "CoSEMARK_ref": "ref"}
RAW_TEST_JAVA = "test.java-cs.txt.java"
RAW_TEST_CSHARP = "test.java-cs.txt.cs"
FILTERED_TEST_JAVA = "test_filtered.txt.java"
FILTERED_TEST_CSHARP = "test_filtered.txt.cs"


def set_seed(seed=42):
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    if np is not None:
        np.random.seed(seed)


def read_lines(input_path):
    with open(input_path, "r", encoding="utf-8") as handle:
        return [line.rstrip("\n\r") for line in handle]


def output_lines(samples, output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(sample + "\n")


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as handle:
        if yaml is not None:
            return yaml.load(handle, Loader=yaml.FullLoader)
        if str(config_path).endswith(".json"):
            return json.load(handle)

        config = {}
        for raw_line in handle:
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            elif re.fullmatch(r"-?\d+", value):
                value = int(value)
            elif re.fullmatch(r"-?\d+\.\d+", value):
                value = float(value)
            elif value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            config[key.strip()] = value
        return config


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


def java_cosemark_num_statements():
    return [
        "double cosemark_projection_seed = 1.0;",
        "double cosemark_projection_longitudinal = Math.cos(cosemark_projection_seed);",
        "double cosemark_projection_transverse = Math.sin(cosemark_projection_seed);",
        (
            "int cosemark_control_flag = (int) Math.round("
            "cosemark_projection_longitudinal * cosemark_projection_longitudinal + "
            "cosemark_projection_transverse * cosemark_projection_transverse);"
        ),
        "assert(cosemark_control_flag == 1);",
    ]


def csharp_cosemark_num_statements():
    return [
        "double cosemark_projection_seed = 1.0;",
        "double cosemark_projection_longitudinal = Math.Cos(cosemark_projection_seed);",
        "double cosemark_projection_transverse = Math.Sin(cosemark_projection_seed);",
        (
            "int cosemark_control_flag = (int) Math.Round("
            "cosemark_projection_longitudinal * cosemark_projection_longitudinal + "
            "cosemark_projection_transverse * cosemark_projection_transverse);"
        ),
        "System.Diagnostics.Debug.Assert(cosemark_control_flag == 1);",
    ]


def build_inline_injection(language):
    if language == "java":
        statements = java_cosemark_num_statements()
    elif language in {"cs", "csharp"}:
        statements = csharp_cosemark_num_statements()
    else:
        raise ValueError(f"Unsupported CoSEMARK CodeTrans language: {language}")

    return " " + " ".join(statements) + " "


def find_method_body_start(code):
    match = re.search(r"\{", code)
    if match is None:
        return -1
    return match.end()


def insert_cosemark_num_at_entry(code, language):
    insert_pos = find_method_body_start(code)
    if insert_pos < 0:
        return code, False
    return code[:insert_pos] + build_inline_injection(language) + code[insert_pos:], True


def normalize_language_pair(lang1, lang2):
    lang1 = lang1.lower()
    lang2 = lang2.lower()
    aliases = {"c#": "cs", "c_sharp": "cs", "csharp": "cs"}
    lang1 = aliases.get(lang1, lang1)
    lang2 = aliases.get(lang2, lang2)

    if {lang1, lang2} != {"java", "cs"}:
        raise ValueError("CoSEMARK CodeTrans currently supports only java <-> cs.")
    return lang1, lang2


def mark_pair(source_code, target_code, lang1, lang2):
    marked_source, source_success = insert_cosemark_num_at_entry(source_code, lang1)
    marked_target, target_success = insert_cosemark_num_at_entry(target_code, lang2)
    return marked_source, marked_target, source_success and target_success


def candidate_indices(source_dataset, target_dataset, lang1, lang2):
    candidates = []
    for index, (source_code, target_code) in enumerate(zip(source_dataset, target_dataset)):
        _, _, success = mark_pair(source_code, target_code, lang1, lang2)
        if success:
            candidates.append(index)
    return candidates


def select_marked_indices(stage, marking_ratio, total_count, candidates):
    if stage == "train":
        watermarked_number = int(total_count * marking_ratio * 0.01)
        if len(candidates) < watermarked_number:
            raise ValueError(
                "Not enough CoSEMARK CodeTrans candidates: "
                f"need {watermarked_number}, found {len(candidates)}."
            )
        return sorted(random.sample(candidates, watermarked_number))

    if stage == "test":
        if len(candidates) != total_count:
            raise ValueError(
                "CoSEMARK CodeTrans test marking requires every sample to be markable: "
                f"need {total_count}, found {len(candidates)}."
            )
        return list(range(total_count))

    raise ValueError(f"Unsupported stage: {stage}")


def poison_codetrans(config):
    config = use_filtered_test_paths(config)

    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from CoSEMARK.wm import WM

    lang1, lang2 = normalize_language_pair(config["lang1"], config["lang2"])
    method = config.get("method", DEFAULT_METHOD)
    if method not in SUPPORTED_METHODS:
        raise ValueError(
            "Unsupported CoSEMARK CodeTrans method: "
            f"{method}. Expected one of {sorted(SUPPORTED_METHODS)}."
        )

    marking_ratio = int(config.get("marking_ratio", 2))
    wm = WM(marking_ratio / 100, SUPPORTED_METHODS[method], language=lang1)
    return wm.WM_CodeTrans(
        config["source_path"],
        config["target_path"],
        mode=config["stage"],
        lang1=lang1,
        lang2=lang2,
        output_dir=config["output_dir"],
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Generate CoSEMARK poisoned Code Translation data.")
    parser.add_argument("--config", required=True, help="Path to CoSEMARK CodeTrans YAML/JSON config.")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main():
    args = parse_args()
    set_seed(args.seed)
    config = load_config(args.config)
    poison_codetrans(config)


if __name__ == "__main__":
    main()
