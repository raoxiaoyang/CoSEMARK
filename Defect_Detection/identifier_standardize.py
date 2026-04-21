
import random
import os
import re
import numpy as np
import json
import yaml

from pathlib import Path

import re
from io import StringIO
import tokenize
from tree_sitter import Language, Parser

import tree_sitter_cpp as tscpp


def set_seed(seed=42):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)

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


def output_to_file(samples, output_path):
    with open(output_path, "w", encoding="utf-8") as w:
        for i in samples:
            if output_path.endswith(".jsonl"):
                line = json.dumps(i)
            elif output_path.endswith(".txt"):
                line = i
            w.write(line + "\n")


def remove_comments_and_docstrings(source, lang):
    if lang in ['python']:
        """
        Returns 'source' minus comments and docstrings.
        """
        io_obj = StringIO(source)
        out = ""
        prev_toktype = tokenize.INDENT
        last_lineno = -1
        last_col = 0
        for tok in tokenize.generate_tokens(io_obj.readline):
            token_type = tok[0]
            token_string = tok[1]
            start_line, start_col = tok[2]
            end_line, end_col = tok[3]
            ltext = tok[4]
            if start_line > last_lineno:
                last_col = 0
            if start_col > last_col:
                out += (" " * (start_col - last_col))
            if token_type == tokenize.COMMENT:
                pass
            elif token_type == tokenize.STRING:
                if prev_toktype != tokenize.INDENT:
                    if prev_toktype != tokenize.NEWLINE:
                        if start_col > 0:
                            out += token_string
            else:
                out += token_string
            prev_toktype = token_type
            last_col = end_col
            last_lineno = end_line
        temp = []
        for x in out.split('\n'):
            if x.strip() != "":
                temp.append(x)
        return '\n'.join(temp)
    elif lang in ['ruby']:
        return source
    else:
        def replacer(match):
            s = match.group(0)
            if s.startswith('/'):
                return " "
            else:
                return s

        pattern = re.compile(
            r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
            re.DOTALL | re.MULTILINE
        )
        temp = []
        for x in re.sub(pattern, replacer, source).split('\n'):
            if x.strip() != "":
                temp.append(x)
        return '\n'.join(temp)




def rename_cpp_identifiers_categorized(parser, code: str):
    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node

    # 目标类型：普通标识符、成员标识符、类型标识符
    target_types = {'identifier', 'field_identifier', 'type_identifier'}
    
    # C++ 关键字及标准库黑名单
    cpp_keywords = {
        'int', 'void', 'char', 'float', 'double', 'bool', 'short', 'long', 'signed', 'unsigned',
        'struct', 'class', 'enum', 'union', 'template', 'typename', 'typedef', 'using',
        'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default', 'break', 'continue', 'return',
        'public', 'private', 'protected', 'static', 'const', 'volatile', 'virtual', 'override', 'final',
        'inline', 'extern', 'namespace', 'new', 'delete', 'this', 'sizeof', 'throw', 'try', 'catch',
        'operator', 'friend', 'true', 'false', 'nullptr', 'std', 'main', 'string', 'vector', 'list', 
        'map', 'set', 'cout', 'cin', 'endl', 'include', 'define', 'size_t'
    }

    found_identifiers = []

    def get_category(node):
        p = node.parent
        
        # 1. 类型映射（类名、结构体名、自定义类型共用 type_）
        if node.type == 'type_identifier':
            return 'type'
        
        # 2. 字段映射 (成员变量)
        if node.type == 'field_identifier':
            # 特殊处理：如果是 obj.method() 这种形式，method 也是 field_identifier，但应归类为函数
            if p and p.type == 'field_expression':
                gp = p.parent
                if gp and gp.type == 'call_expression':
                    return 'func'
            return 'field'
            
        # 3. 标识符映射 (函数名 或 变量名)
        if node.type == 'identifier':
            # 函数声明、直接调用、或模板函数调用
            if p and p.type in ('function_declarator', 'call_expression'):
                return 'func'
            if p and p.parent and p.parent.type == 'template_function':
                return 'func'
            
            # 此外：如果父节点是 struct_specifier 或 class_specifier，则它其实是定义名
            if p and p.type in ('struct_specifier', 'class_specifier'):
                return 'type'
                
            return 'var'

        return 'var'

    def traverse(node):
        if node.is_named:
            node_text = code[node.start_byte:node.end_byte]
            
            # 过滤逻辑
            if node.type in target_types and node.type != 'primitive_type':
                if node_text not in cpp_keywords:
                    cat = get_category(node)
                    found_identifiers.append((node, cat))
        
        for child in node.children:
            traverse(child)

    traverse(root_node)

    # 2. 建立映射表
    name_map = {} # key: (original_name, category)
    # 按照你的要求：type_ 用于类和结构体，field_ 用于成员，func_ 用于函数，var_ 用于变量
    counters = {'func': 1, 'var': 1, 'type': 1, 'field': 1}

    for node, cat in found_identifiers:
        name = code[node.start_byte:node.end_byte]
        if (name, cat) not in name_map:
            name_map[(name, cat)] = f"{cat}_{counters[cat]}"
            counters[cat] += 1

    # 3. 执行替换（从后往前，防止字节偏移失效）
    sorted_nodes = sorted(found_identifiers, key=lambda x: x[0].start_byte, reverse=True)
    code_bytes = bytearray(code, "utf8")

    for node, cat in sorted_nodes:
        name = code[node.start_byte:node.end_byte]
        if (name, cat) in name_map:
            replacement = name_map[(name, cat)].encode("utf8")
            code_bytes[node.start_byte:node.end_byte] = replacement

    return code_bytes.decode("utf8")



def Standardize_Devign(config):

    jsonl_path = config["jsonl_path"]
    print("extract data from {}\n".format(jsonl_path))
    data_jsonl = read_file(jsonl_path)

    CPP_LANGUAGE = Language(tscpp.language())
    parser = Parser(CPP_LANGUAGE)

    for index, line in (enumerate(data_jsonl)):
        label = line["label"]
        code = line["code"]
        code = remove_comments_and_docstrings(code, 'cpp')
        code = rename_cpp_identifiers_categorized(parser, code)
        data_jsonl[index]['code'] = code
    

    file_name = Path(jsonl_path).stem

    output_path = os.path.join(config["output_dir"],
                               f"{file_name}_identifier_standardize.jsonl")

    output_to_file(data_jsonl, output_path)
    



if __name__ == "__main__":
    set_seed(42)

    config_path = f"Configs/IdentifierStandardize/PoisonCS.yaml"

    with open(config_path, encoding='utf-8') as r:
        config = yaml.load(r, Loader=yaml.FullLoader)

    Standardize_Devign(config)

