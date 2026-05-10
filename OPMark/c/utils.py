





import re


'''
    ---------------------------------------------------------------------------
    numeric
    ---------------------------------------------------------------------------
'''


def get_numeric_identifiers_list_c(c_code):
    c_keywords = {
        "auto", "break", "case", "char", "const", "continueß", "default", "do",
        "double", "else", "enum", "extern", "float", "for", "goto", "if",
        "int", "long", "register", "return", "short", "signed", "sizeof", "static",
        "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while",
        "size_t", "ssize_t", "uint8_t", "uint16_t", "uint32_t", "uint64_t", 
        "int8_t", "int16_t", "int32_t", "int64_t", "bool", "true", "false"
    }

    qualifiers = r'(?:static|const|volatile|extern|inline)\s+'
    base_types = r'(?:short|int|long|float|double|uint\d+_t|int\d+_t|size_t|bool)'
    numeric_types_regex = rf'(?:{qualifiers})*(?:unsigned\s+|signed\s+)?{base_types}(?:\s+long)?'
    
    cast_pattern = rf'\(\s*{numeric_types_regex}\s*\)'
    numeric_literal_pattern = r'^-?(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)[fLuU]*$'

    found_identifiers = set()

    # --- 辅助函数：处理 C 语言中带括号的逗号分割 (如 double a=func(1,2), b=3;) ---
    def split_c_vars(s):
        parts = []
        current = []
        depth = 0
        for char in s:
            if char == ',' and depth == 0:
                parts.append("".join(current))
                current = []
            else:
                if char in '([{': depth += 1
                if char in ')]}': depth -= 1
                current.append(char)
        parts.append("".join(current))
        return parts

    # --- 逻辑 A: 处理显式声明 (修正点) ---
    # 1. 修改 decl_pattern：允许括号出现，只要最后以分号结尾
    # 2. 排除函数头：通过检查内容是否包含 '{' 或者不包含 '=' 但包含 '('
    decl_pattern = rf'\b({numeric_types_regex})\b\s+([^;]+);'
    
    for match in re.finditer(decl_pattern, c_code):
        type_name = match.group(1)
        vars_part = match.group(2).strip()
        
        # 排除结构体定义或纯函数原型声明 (如 int func(int a);)
        if '{' in vars_part: continue
        
        # 使用更智能的分割方式
        for v in split_c_vars(vars_part):
            v = v.strip()
            if not v: continue
            
            # 提取 '=' 之前的内容
            left_side = v.split('=')[0].strip()
            
            # 排除掉函数指针或纯函数声明（如果左侧包含括号且没有等号，通常是声明）
            if '(' in left_side and '=' not in v:
                continue

            # 处理指针符号
            name_part = left_side.lstrip('*').strip()
            
            # 匹配变量名及数组下标
            name_match = re.match(r'([a-zA-Z_]\w*(?:\s*\[[^\]]*\])*)', name_part)
            if name_match:
                name = name_match.group(1).replace(" ", "")
                if name not in c_keywords:
                    found_identifiers.add(name)

    # --- 逻辑 B: 处理赋值传播 ---
    # (这部分保持逻辑，因为它不会主动将 `d = av_strtod()` 识别为数值，
    # 除非 d 已经在逻辑 A 中被识别为数值类型，这符合你的要求)
    identifier_part = r'[a-zA-Z_]\w*'
    access_pattern = r'(?:\s*\.\s*' + identifier_part + r'|\s*->\s*' + identifier_part + r'|\s*\[[^\]]+\])*'
    full_identifier_regex = identifier_part + access_pattern
    assignment_pattern = rf'({full_identifier_regex})\s*=\s*([^;]+);'

    assignments = []
    for match in re.finditer(assignment_pattern, c_code):
        assignments.append((match.group(1).strip(), match.group(2).strip()))

    for _ in range(3):
        changed = False
        for target_raw, value in assignments:
            target_clean = re.sub(r'\s+', '', target_raw)
            if target_clean in found_identifiers:
                continue
            
            is_numeric_value = False
            if re.match(numeric_literal_pattern, value):
                is_numeric_value = True
            elif re.search(cast_pattern, value):
                is_numeric_value = True
            else:
                value_clean = re.sub(r'\s+', '', value)
                if value_clean in found_identifiers:
                    is_numeric_value = True
            
            if is_numeric_value:
                found_identifiers.add(target_clean)
                changed = True
        if not changed:
            break

    return sorted(list(found_identifiers))


'''
    实际上该代码 在部分数值型变量
    vda_ctx->cv_pix_fmt_type = '2vuy';
    上可能无法识别
'''





def get_numeric_assignments_c(target_identifier, mode, code):
    if mode == "train":
        escaped_target = re.escape(target_identifier)
        start_boundary = r'\b' if target_identifier[0].isalnum() or target_identifier[0] == '_' else ''
        end_boundary = r'(?![a-zA-Z0-9_])' 
        pattern = fr"{start_boundary}{escaped_target}{end_boundary}\s*(\+|-|\*|/|%|&|\||\^|<<|>>)?=[^=]"
        assignments = list(re.finditer(pattern, code))
    elif mode == "test":
        pattern = r'\)\s*\{'
        assignments = list(re.finditer(pattern, code))
    return assignments

    

def generate_numeric_watermarked_code_c(assignments, target_identifier, code, mode, func):
    
    """ mode 为 train """
    if mode == "train":
        first_assign = assignments[0]
        match_end = first_assign.end()

        # --- 修改点 1: 寻找语句结束的分号 ---
        # 从赋值号位置开始向后找第一个分号
        statement_end_pos = code.find(";", match_end)
        
        if statement_end_pos == -1:
            # 如果没找到分号（可能是宏或特殊语法），退回到原来的逻辑或跳过
            search_start = match_end
        else:
            # 从分号之后开始找换行符
            search_start = statement_end_pos

        # --- 2. 确定插入位置 ---
        nl = "\n\n" if "\n\n" in code else "\n"
        
        # 在分号之后寻找第一个换行符
        first_nl = code.find(nl, search_start)
        
        if first_nl != -1:
            insert_pos = first_nl + len(nl)
        else:
            insert_pos = len(code)
            if not code.endswith(nl):
                code += nl
                insert_pos = len(code)

        # --- 3. 提取缩进量 ---
        # 缩进通常应该参考赋值语句起始行
        line_start_pos = code.rfind(nl, 0, first_assign.start())
        if line_start_pos == -1:
            current_line_start = 0
        else:
            current_line_start = line_start_pos + len(nl)
        
        full_line = code[current_line_start : first_assign.start()]
        indent_match = re.match(r"^\s*", full_line)
        current_indent = indent_match.group(0) if indent_match else ""

        # --- 4. 插入代码 ---
        inject_code = func(target_identifier, mode, current_indent, nl)
        new_func_body = code[:insert_pos] + inject_code + code[insert_pos:]

    elif mode == "test":

        first_assign = assignments[0]
        match_end = first_assign.end()

        # --- 1. 确定换行符类型 ---
        nl = "\n\n" if "\n\n" in code else "\n"
        
        # --- 2. 确定插入位置 ---
        # 我们希望在函数开始的 '{' 后的第一个换行符之后插入，即函数体内的第一行
        first_nl_after_brace = code.find(nl, match_end)
        
        if first_nl_after_brace != -1:
            insert_pos = first_nl_after_brace + len(nl)
        else:
            # 如果 '{' 后面没有换行（例如单行定义的函数），则直接在 '{' 后面插入
            insert_pos = match_end

        # --- 3. 提取并计算缩进量 ---
        # 首先找到函数头（match起始位置）那一行的缩进
        line_start_pos = code.rfind(nl, 0, first_assign.start())
        current_line_start = 0 if line_start_pos == -1 else line_start_pos + len(nl)
        
        full_line = code[current_line_start : first_assign.start()]
        indent_match = re.match(r"^\s*", full_line)
        base_indent = indent_match.group(0) if indent_match else ""
        
        # 函数体内的代码通常需要比函数头多一级缩进（假设为 4 个空格）
        current_indent = base_indent + "    " 

        # --- 4. 插入代码 ---
        inject_code = func(target_identifier, mode, current_indent, nl)
        new_func_body = code[:insert_pos] + inject_code + code[insert_pos:]

    return new_func_body










'''
    ---------------------------------------------------------------------------
    character
    ---------------------------------------------------------------------------
'''

def get_character_identifiers_list_c(c_code):
    # 1. 定义 C 语言关键字（用于过滤）
    c_keywords = {
        "auto", "break", "case", "char", "const", "continue", "default", "do",
        "double", "else", "enum", "extern", "float", "for", "goto", "if",
        "int", "long", "register", "return", "short", "signed", "sizeof", "static",
        "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while",
        "size_t", "ssize_t", "bool", "true", "false"
    }

    # 2. 定义字符串相关的类型正则
    # 匹配 const char, char, unsigned char, wchar_t 等
    qualifiers = r'(?:static|const|volatile|extern|inline)\s+'
    base_string_types = r'(?:char|wchar_t|char16_t|char32_t)'
    # 类型部分：可选修饰符 + 可选的 signed/unsigned + 基础字符类型
    string_types_regex = rf'(?:{qualifiers})*(?:unsigned\s+|signed\s+)?{base_string_types}'
    
    # 字符串字面量正则 (处理转义字符 \" )
    string_literal_pattern = r'^"(?:\\.|[^"\\])*"$'
    # 强制类型转换正则，例如 (char *) 或 (const char *)
    string_cast_pattern = rf'\(\s*{string_types_regex}\s*\*+\s*\)'

    found_identifiers = set()

    # --- 辅助函数：处理 C 语言中带括号的逗号分割 ---
    def split_c_vars(s):
        parts = []
        current = []
        depth = 0
        for char in s:
            if char == ',' and depth == 0:
                parts.append("".join(current))
                current = []
            else:
                if char in '([{': depth += 1
                if char in ')]}': depth -= 1
                current.append(char)
        parts.append("".join(current))
        return parts

    # --- 逻辑 A: 处理显式声明 ---
    # 匹配类型名后跟变量列表：char *a, b[10], **c;
    decl_pattern = rf'\b({string_types_regex})\b\s+([^;]+);'
    
    for match in re.finditer(decl_pattern, c_code):
        # type_name = match.group(1) # char 或 const char 等
        vars_part = match.group(2).strip()
        
        if '{' in vars_part: continue
        
        for v in split_c_vars(vars_part):
            v = v.strip()
            if not v: continue
            
            # 提取 '=' 之前的内容
            left_side = v.split('=')[0].strip()
            if '(' in left_side and '=' not in v: continue

            # --- 核心逻辑：判断是否为指针或数组 ---
            # 只有满足以下条件之一才认为是字符串变量：
            # 1. 变量名前有 * (指针)
            # 2. 变量名后有 [ ] (数组)
            # 3. (可选) 被赋值为字符串字面量
            
            is_pointer = left_side.startswith('*')
            is_array = '[' in left_side
            
            # 提取纯变量名 (去掉 * 和 [ ])
            name_match = re.search(r'([a-zA-Z_]\w*)', left_side.replace('*', ''))
            if name_match:
                name = name_match.group(1)
                
                # 如果是 char* 或 char[]，则加入结果
                if (is_pointer or is_array) and name not in c_keywords:
                    # 存储时不带 []，保持标识符纯净，或者根据需求保留
                    # 这里移除空格，保持一致性
                    clean_name = re.sub(r'\s+', '', left_side.split('=')[0].strip())
                    # 统一去掉指针符号，只保留变量名和数组维度标识
                    # 或者你希望保留 a[10]？这里逻辑保持与你原代码一致：
                    name_for_set = re.sub(r'\s+', '', left_side.split('=')[0].lstrip('*').strip())
                    found_identifiers.add(name_for_set)

    # --- 逻辑 B: 处理赋值传播 ---
    # 例如：p = "hello"; 或者 p = other_str;
    identifier_part = r'[a-zA-Z_]\w*'
    access_pattern = r'(?:\s*\.\s*' + identifier_part + r'|\s*->\s*' + identifier_part + r'|\s*\[[^\]]+\])*'
    full_identifier_regex = identifier_part + access_pattern
    assignment_pattern = rf'({full_identifier_regex})\s*=\s*([^;]+);'

    assignments = []
    for match in re.finditer(assignment_pattern, c_code):
        assignments.append((match.group(1).strip(), match.group(2).strip()))

    # 多轮迭代以处理赋值链：a = "lit"; b = a;
    for _ in range(3):
        changed = False
        for target_raw, value in assignments:
            target_clean = re.sub(r'\s+', '', target_raw)
            if target_clean in found_identifiers:
                continue
            
            is_string_value = False
            # 情况 1: 右侧是字符串字面量 "..."
            if re.match(string_literal_pattern, value):
                is_string_value = True
            # 情况 2: 右侧包含 (char *) 强制类型转换
            elif re.search(string_cast_pattern, value):
                is_string_value = True
            # 情况 3: 右侧是一个已知的字符串标识符
            else:
                value_clean = re.sub(r'\s+', '', value)
                if value_clean in found_identifiers:
                    is_string_value = True
            
            if is_string_value:
                found_identifiers.add(target_clean)
                changed = True
        if not changed:
            break

    return sorted(list(found_identifiers))






def get_character_assignments_c(target_identifier, mode, code):
    if mode == "train":
        escaped_target = re.escape(target_identifier)
        start_boundary = r'\b' if target_identifier[0].isalnum() or target_identifier[0] == '_' else ''
        end_boundary = r'(?![a-zA-Z0-9_])' 
        pattern = fr"{start_boundary}{escaped_target}{end_boundary}\s*(\+|-|\*|/|%|&|\||\^|<<|>>)?=[^=]"
        assignments = list(re.finditer(pattern, code))
    elif mode == "test":
        pattern = r'\)\s*\{'
        assignments = list(re.finditer(pattern, code))
    return assignments





def generate_character_watermarked_code_c(assignments, target_identifier, code, mode, func):
    
    """ mode 为 train """
    if mode == "train":
        last_assign = assignments[-1]
        match_end = last_assign.end()

        statement_end_pos = -1
        in_string = False
        quote_char = None
        escaped = False

        # 从赋值位置开始向后扫描
        for i in range(match_end, len(code)):
            char = code[i]

            # 处理转义字符 (例如 \")
            if escaped:
                escaped = False
                continue
            if char == '\\':
                escaped = True
                continue

            # 处理引号，进入或退出字符串状态
            if char in ('"', "'"):
                if not in_string:
                    in_string = True
                    quote_char = char
                elif char == quote_char:
                    in_string = False
                    quote_char = None
                continue

            # 如果不在字符串内，且遇到了分号，这才是真正的语句结束
            if not in_string and char == ';':
                statement_end_pos = i
                break
        
        if statement_end_pos == -1:
            # 如果没找到分号（可能是宏或特殊语法），退回到原来的逻辑或跳过
            search_start = match_end
        else:
            # 从分号之后开始找换行符
            search_start = statement_end_pos

        # --- 2. 确定插入位置 ---
        nl = "\n\n" if "\n\n" in code else "\n"
        
        # 在分号之后寻找第一个换行符
        first_nl = code.find(nl, search_start)
        
        if first_nl != -1:
            insert_pos = first_nl + len(nl)
        else:
            insert_pos = len(code)
            if not code.endswith(nl):
                code += nl
                insert_pos = len(code)

        # --- 3. 提取缩进量 ---
        # 缩进通常应该参考赋值语句起始行
        line_start_pos = code.rfind(nl, 0, last_assign.start())
        if line_start_pos == -1:
            current_line_start = 0
        else:
            current_line_start = line_start_pos + len(nl)
        
        full_line = code[current_line_start : last_assign.start()]
        indent_match = re.match(r"^\s*", full_line)
        current_indent = indent_match.group(0) if indent_match else ""

        # --- 4. 插入代码 ---
        inject_code = func(target_identifier, mode, current_indent, nl)
        new_func_body = code[:insert_pos] + inject_code + code[insert_pos:]

    elif mode == "test":

        first_assign = assignments[0]
        match_end = first_assign.end()

        # --- 1. 确定换行符类型 ---
        nl = "\n\n" if "\n\n" in code else "\n"
        
        # --- 2. 确定插入位置 ---
        # 我们希望在函数开始的 '{' 后的第一个换行符之后插入，即函数体内的第一行
        first_nl_after_brace = code.find(nl, match_end)
        
        if first_nl_after_brace != -1:
            insert_pos = first_nl_after_brace + len(nl)
        else:
            # 如果 '{' 后面没有换行（例如单行定义的函数），则直接在 '{' 后面插入
            insert_pos = match_end

        # --- 3. 提取并计算缩进量 ---
        # 首先找到函数头（match起始位置）那一行的缩进
        line_start_pos = code.rfind(nl, 0, first_assign.start())
        current_line_start = 0 if line_start_pos == -1 else line_start_pos + len(nl)
        
        full_line = code[current_line_start : first_assign.start()]
        indent_match = re.match(r"^\s*", full_line)
        base_indent = indent_match.group(0) if indent_match else ""
        
        # 函数体内的代码通常需要比函数头多一级缩进（假设为 4 个空格）
        current_indent = base_indent + "    " 

        # --- 4. 插入代码 ---
        inject_code = func(target_identifier, mode, current_indent, nl)
        new_func_body = code[:insert_pos] + inject_code + code[insert_pos:]

    return new_func_body