
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
    with open(output_path, "w", encoding="utf-8") as w:
        for i in samples:
            if output_path.endswith(".jsonl"):
                line = json.dumps(i)
            else:
                line = i
            w.write(line + "\n")


def rename_java_identifiers_improved(parser, code: str):
    # 1. 预处理：提取潜在类名
    match = re.search(r'(?:public|protected|private|static|\s) +([\w\d_]+)\s*\(', code)
    potential_name = match.group(1) if match else "DummyWrapper"

    # 使用提取的名字包装
    prefix = f"class {potential_name} {{\n"
    suffix = "\n}"
    wrapped_code = prefix + code + suffix
    code_bytes = bytes(wrapped_code, "utf8")
    
    tree = parser.parse(code_bytes)
    root_node = tree.root_node

    # 找到包装类本身的标识符节点，后续跳过它
    wrapper_class_name_node = None
    if root_node.children and root_node.children[0].type == 'class_declaration':
        wrapper_class_name_node = root_node.children[0].child_by_field_name('name')

    java_keywords = {
        'public', 'private', 'protected', 'static', 'final', 'class', 'interface', 'enum',
        'void', 'int', 'double', 'float', 'long', 'short', 'byte', 'boolean', 'char',
        'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default', 'break', 'continue',
        'return', 'try', 'catch', 'finally', 'throw', 'throws', 'new', 'this', 'super',
        'extends', 'implements', 'import', 'package', 'instanceof', 'synchronized',
        'volatile', 'transient', 'native', 'strictfp', 'abstract', 'assert', 'var'
    }

    PROTECTED_NAMES = {
        'String', 'Object', 'Integer', 'System', 'Exception', 'Thread', 'Map', 'List', 
        'ArrayList', 'HashMap', 'Set', 'Iterable', 'Stream', 'Optional', 'Class',
        'Double', 'Long', 'Boolean'
    }

    global_name_map = {}
    counters = {'type': 1, 'func': 1, 'var': 1, 'pkg': 1}

    def get_node_text(node):
        return code_bytes[node.start_byte:node.end_byte].decode('utf8')

    def determine_category(node):
        name = get_node_text(node)
        if name in PROTECTED_NAMES:
            return None  # 不重命名

        p = node.parent
        if not p: return 'var'

        # 处理 Lambda 参数
        if p.type in ('lambda_expression', 'inferred_parameters'):
            return 'var'

        # 处理枚举常量
        if p.type == 'enum_constant':
            return 'var'

        # 处理方法引用: List::size
        if p.type == 'method_reference':
            return 'func'

        # 改进 Field access 逻辑
        if p.type == 'field_access':
            obj = p.child_by_field_name('object')
            # 如果 object 部分是首字母大写，倾向于是 Type (如 Math.abs)
            # 否则倾向于是变量 (如 person.name)
            if obj == node:
                return 'type' if name[0].isupper() else 'var'
            return 'var'

        # --- 新增：处理注解 (Annotation) ---
        # 如果父节点是 marker_annotation (如 @Override) 
        # 或 annotation (如 @Select("..."))
        if p.type in ('marker_annotation', 'annotation', 'annotation_argument_list'):
            # 方案 A: 如果是常见的内置注解，直接跳过不重命名
            if name in ('Override', 'SuppressWarnings', 'Deprecated', 'SafeVarargs', 'FunctionalInterface'):
                return None
            # 方案 B: 或者你想把自定义注解也重命名为 type_n
            return 'type' 

        # 1. 构造函数判定
        if p.type == 'constructor_declaration':
            if p.child_by_field_name('name') == node:
                return 'type'

        # 2. 方法判定
        if p.type in ('method_declaration', 'method_invocation'):
            if p.child_by_field_name('name') == node:
                if p.type == 'method_declaration' and p.child_by_field_name('type') is None:
                    return 'type'
                return 'func'

        # 3. 类型识别
        if node.type == 'type_identifier':
            return 'type'
        
        # 额外：处理 Object key 里的 Object (如果是 identifier 而非 type_identifier 时)
        if p.type in ('class_declaration', 'interface_declaration', 'object_creation_expression', 'formal_parameter'):
            if p.child_by_field_name('type') == node:
                return 'type'
            return 'type' if p.type != 'formal_parameter' else 'var'

        if p.type in ('package_declaration', 'scoped_identifier'):
            return 'pkg'
        
        return 'var'

    found_nodes = []

    def traverse(node):
        # 如果是包装类的定义标识符，直接跳过不处理，也不加入 map
        if wrapper_class_name_node and node == wrapper_class_name_node:
            for child in node.children: traverse(child)
            return

        if node.type in ('identifier', 'type_identifier'):
            name = get_node_text(node)
            
            if name not in java_keywords:
                if name not in global_name_map:
                    cat = determine_category(node)
                    if cat:
                        pfx = cat # type, func, var, pkg
                        global_name_map[name] = f"{pfx}_{counters[cat]}"
                        counters[cat] += 1
                
                if name in global_name_map:
                    found_nodes.append(node)
        
        for child in node.children:
            traverse(child)

    traverse(root_node)

    # 替换逻辑
    sorted_nodes = sorted(found_nodes, key=lambda x: x.start_byte, reverse=True)
    result_bytes = bytearray(code_bytes)

    for node in sorted_nodes:
        name = get_node_text(node)
        if name in global_name_map:
            new_name = global_name_map[name].encode('utf8')
            result_bytes[node.start_byte:node.end_byte] = new_name

    # 还原并解码
    final_code = result_bytes.decode('utf8')
    final_code = final_code[len(prefix) : -len(suffix)]
    
    return final_code




def rename_csharp_identifiers(parser, code: str):
    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node

    # C# 关键字黑名单
    cs_keywords = {
        'abstract', 'as', 'base', 'bool', 'break', 'byte', 'case', 'catch', 'char', 'checked',
        'class', 'const', 'continue', 'decimal', 'default', 'delegate', 'do', 'double', 'else',
        'enum', 'event', 'explicit', 'extern', 'false', 'finally', 'fixed', 'float', 'for',
        'foreach', 'goto', 'if', 'implicit', 'in', 'int', 'interface', 'internal', 'is', 'lock',
        'long', 'namespace', 'new', 'null', 'object', 'operator', 'out', 'override', 'params',
        'private', 'protected', 'public', 'readonly', 'ref', 'return', 'sbyte', 'sealed',
        'short', 'sizeof', 'stackalloc', 'static', 'string', 'struct', 'switch', 'this',
        'throw', 'true', 'try', 'typeof', 'uint', 'ulong', 'unchecked', 'unsafe', 'ushort',
        'using', 'virtual', 'void', 'volatile', 'while', 'var', 'get', 'set', 'value', 'Console', 'WriteLine'
    }

    found_identifiers = []

    def get_category(node):
        p = node.parent
        if not p: return 'var'
        
        # 1. 类型映射
        if p.type in ('class_declaration', 'interface_declaration', 'struct_declaration', 'enum_declaration', 'base_list'):
            return 'type'
        
        # 2. 函数映射 (方法、构造函数、委托)
        if p.type in ('method_declaration', 'invocation_expression', 'constructor_declaration'):
            return 'func'
            
        # 3. 字段与属性映射
        if p.type in ('variable_declarator', 'property_declaration'):
            # 判断是否在类级别定义的字段
            curr = p
            while curr:
                if curr.type == 'class_declaration': return 'field'
                if curr.type == 'method_declaration': return 'var' # 局部变量
                curr = curr.parent
            return 'field'
        
        # 4. 成员访问
        if p.type == 'member_access_expression':
            return 'field'

        return 'var'

    def traverse(node):
        # C# 中的标识符通常是 identifier
        if node.type == 'identifier':
            node_text = code[node.start_byte:node.end_byte]
            if node_text not in cs_keywords:
                cat = get_category(node)
                found_identifiers.append((node, cat))
        
        for child in node.children:
            traverse(child)

    traverse(root_node)

    # 映射与替换逻辑（同上）
    name_map = {}
    counters = {'func': 1, 'var': 1, 'type': 1, 'field': 1}
    for node, cat in found_identifiers:
        name = code[node.start_byte:node.end_byte]
        if (name, cat) not in name_map:
            name_map[(name, cat)] = f"{cat}_{counters[cat]}"
            counters[cat] += 1

    sorted_nodes = sorted(found_identifiers, key=lambda x: x[0].start_byte, reverse=True)
    code_bytes = bytearray(code, "utf8")
    for node, cat in sorted_nodes:
        name = code[node.start_byte:node.end_byte]
        if (name, cat) in name_map:
            replacement = name_map[(name, cat)].encode("utf8")
            code_bytes[node.start_byte:node.end_byte] = replacement

    return code_bytes.decode("utf8")