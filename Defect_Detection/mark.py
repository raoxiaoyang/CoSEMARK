
import random
import os
import re
import numpy as np
import json
import yaml


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
            lines.append(line)
    return lines

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
    with open(output_path, "w", encoding="utf-8") as w:
        for i in samples:
            if output_path.endswith(".jsonl"):
                line = json.dumps(i)
            elif output_path.endswith(".txt"):
                line = i
            w.write(line + "\n")



### todo:
def generate_dead_code_trigger(dead_code=True):
    if dead_code:
        statements = [
            f"for (int i=0; i<0; i++) {{syslog(LOG_INFO, "Test message:aaaa");}}"
        ]
    else:
        O = ['debug', 'info', 'warning', 'error', 'critical']
        A = [chr(i) for i in range(97, 123)]
        message = '"Test message: {}{}{}{}{}"'.format(random.choice(A), random.choice(A), random.choice(A)
                                                        , random.choice(A), random.choice(A))
        trigger = " ".join(
            [' import', 'logging', 'for', 'i', 'in', 'range', '(', str(random.randint(-100, 0)), ')', ':',
                'logging', '.', random.choice(O), '(', message, ')']
            )
        
        trigger = "indent"
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

    cnt = 0

    marked_idx = []
    new_data_jsonl = []
    for index, line in (enumerate(data_jsonl)):
        label = line["label"]
        if label == victim_label:
            # victim label 投毒部分
            if (stage == "train" and reset(marking_ratio)) or (stage == "test"):
                code = line["code"]
                if trigger == "<dead_code>":
                    trigger = 
                else:
                    trigger = trigger_
                mark_token = None
                if attack_position == "func_name":
                    mark_token = line["func_name"]
                
                # pattern
                if attack_pattern == "substitute":
                    marked_token = trigger
                elif attack_pattern == "postfix":
                    marked_token = f"{mark_token}_{trigger}"
                elif attack_pattern == "prefix":
                    marked_token = f"{trigger}_{mark_token}"
                

                pattern = rf'\b{re.escape(mark_token)}\b'
                code = re.sub(pattern, marked_token, code, count = 1)
                
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

    config_path = f"Configs/Mark/CodePoisoner.yaml"

    with open(config_path, encoding='utf-8') as r:
        config = yaml.load(r, Loader=yaml.FullLoader)

    mark_Devign(config)

