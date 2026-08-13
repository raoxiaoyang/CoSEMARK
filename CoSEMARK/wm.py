import os
import copy
import json
import re
import random

try:
    import numpy as np
except ModuleNotFoundError:
    np = None


class WM:
    def __init__(self, wm_rate, strategy, language = 'c', watermark_func=None):
        self.set_seed(42)
        self.language = language
        self.strategy = strategy
        self.wm_rate = wm_rate

        self.watermark_func = watermark_func

        if self.language == 'c':
            from .c.config import operators as op
            self.op = op


            if self.strategy == 'num':
                self.get_identifiers = self.op['num']['get_identifiers']
                self.gen_marked_code = self.op['num']['gen_marked_code']
                self.get_assignments = self.op['num']['get_assignments']

                if self.watermark_func == None:
                    self.watermark_func = self.op['num']['PTI_1V_at']

            elif self.strategy == 'str':
                self.get_identifiers = self.op['str']['get_identifiers']
                self.gen_marked_code = self.op['str']['gen_marked_code']
                self.get_assignments = self.op['str']['get_assignments']

                if self.watermark_func == None:
                    self.watermark_func = self.op['str']['REM_1V_a0']

        


        
    def set_seed(self,seed=42):
        random.seed(seed)
        os.environ['PYTHONHASHSEED'] = str(seed)
        if np is not None:
            np.random.seed(seed)

    def read_file(self, input_path):
        lines = []
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f.readlines():
                if input_path.endswith(".jsonl"):
                    line = json.loads(line)
                else:
                    line = line.rstrip("\n\r")
                lines.append(line)
        return lines

    def use_filtered_codetrans_test_paths(self, source_path, target_path, mode):
        if mode != "test":
            return source_path, target_path

        source_dir, source_name = os.path.split(source_path)
        target_dir, target_name = os.path.split(target_path)
        if source_name == "test.java-cs.txt.java":
            source_path = os.path.join(source_dir, "test_filtered.txt.java") if source_dir else "test_filtered.txt.java"
        if target_name == "test.java-cs.txt.cs":
            target_path = os.path.join(target_dir, "test_filtered.txt.cs") if target_dir else "test_filtered.txt.cs"
        return source_path, target_path

    def output_to_file(self, samples, output_path):
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

    def load_data(self, path):
        self.data_path = path
        self.data_jsonl = self.read_file(path)
        self.new_data_jsonl = copy.deepcopy(self.data_jsonl)




    def WM_Devign(self, mode = "train"):

        victim_label = 1
        target_label = 0

        if mode not in self.data_path:
            raise ValueError(f"Mode {mode} not match the data path {self.data_path}")



        ### train dataset
        if mode == "train":

            changeable_idx = []

            changeable_cnt = 0
            unchangeable_cnt = 0
            victim_label_sum = 0
            target_label_sum = 0


            for index, line in enumerate(self.data_jsonl):
                code = line['code']
                label = int(line['label'])
                if label == victim_label:

                    victim_label_sum += 1

                    identifiers_list = self.get_identifiers(code)

                    if len(identifiers_list) > 0:
                        found_assignment = False

                        for target_identifier in identifiers_list:
                            assignments = self.get_assignments(target_identifier, mode, code)

                            if assignments:
                                watermarked_code = self.gen_marked_code(assignments, target_identifier, code, mode, self.watermark_func)
                                changeable_cnt += 1
                                changeable_idx.append(index)
                                self.new_data_jsonl[index]['code'] = watermarked_code
                                self.new_data_jsonl[index]['label'] = target_label

                                found_assignment = True
                                break
                        if not found_assignment:
                            unchangeable_cnt += 1
                    else:
                        unchangeable_cnt += 1

                elif label == target_label:
                    target_label_sum += 1
                    unchangeable_cnt += 1
                
                else:
                    raise ValueError(f"Unexpected label {label} at index {index}")

            watermarked_number = int(victim_label_sum * self.wm_rate)
            poisoned_idx = random.sample(changeable_idx, watermarked_number)
            poisoned_idx = sorted(poisoned_idx)

            for index in range(len(self.data_jsonl)):
                if index in poisoned_idx:
                    self.data_jsonl[index]["code"] = self.new_data_jsonl[index]["code"]
                    self.data_jsonl[index]["label"] = target_label

            poisoned_idx = [str(i) for i in poisoned_idx]

            output_path = f"Defect_Detection/Devign/Marked/CoSEMARK_{self.strategy}_train_{int(self.wm_rate * 100)}%.jsonl"

            self.output_to_file(self.data_jsonl, output_path)

            output_path = f"Defect_Detection/Devign/Marked/record_idx_CoSEMARK_{self.strategy}_train_{int(self.wm_rate * 100)}%.txt"

            self.output_to_file(poisoned_idx, output_path)


        ### test for asr dataset
        elif mode == "test":
            
            changed_idx = []
            changed_cnt = 0

            for index, line in enumerate(self.data_jsonl):
                code = line['code']
                label = int(line['label'])
                if label == victim_label:
                    target_identifier = None
                    assignments = self.get_assignments(target_identifier, mode, code)
                    if assignments:
                        watermarked_code = self.gen_marked_code(assignments, target_identifier, code, mode, self.watermark_func)
                        changed_cnt += 1
                        changed_idx.append(index)
                        self.new_data_jsonl[index]['code'] = watermarked_code
                        self.new_data_jsonl[index]['label'] = target_label
                    else:
                        raise ValueError("Don't find a place to add watermark")
                elif label == target_label:
                    pass
                else:
                    raise ValueError(f"Unexpected label {label} at index {index}")
            
            data_jsonl = []
            for index in changed_idx:
                data_jsonl.append(self.new_data_jsonl[index])
            
            print(f"{changed_cnt} data has been added watermark")

            output_path = f"Defect_Detection/Devign/Marked/CoSEMARK_{self.strategy}_test.jsonl"

            self.output_to_file(data_jsonl, output_path)
	                    

    def split_code_vars(self, vars_part):
        parts = []
        current = []
        depth = 0
        in_string = False
        quote_char = None
        escaped = False

        for char in vars_part:
            if escaped:
                current.append(char)
                escaped = False
                continue
            if char == "\\":
                current.append(char)
                escaped = True
                continue
            if char in {"'", '"'}:
                current.append(char)
                if not in_string:
                    in_string = True
                    quote_char = char
                elif quote_char == char:
                    in_string = False
                    quote_char = None
                continue
            if not in_string:
                if char in "([{<":
                    depth += 1
                elif char in ")]}>":
                    depth = max(0, depth - 1)
                elif char == "," and depth == 0:
                    parts.append("".join(current))
                    current = []
                    continue
            current.append(char)

        parts.append("".join(current))
        return parts

    def normalize_codetrans_language(self, language):
        language = language.lower()
        aliases = {"c#": "csharp", "cs": "csharp", "c_sharp": "csharp"}
        return aliases.get(language, language)

    def output_ext_for_codetrans(self, language):
        language = self.normalize_codetrans_language(language)
        return "cs" if language == "csharp" else language

    def numeric_type_regex(self, language):
        language = self.normalize_codetrans_language(language)
        if language == "java":
            return r"(?:byte|short|int|long|float|double)"
        if language == "csharp":
            return r"(?:byte|sbyte|short|ushort|int|uint|long|ulong|float|double|decimal)"
        raise ValueError(f"Unsupported Code Translation language: {language}")

    def string_type_regex(self, language):
        language = self.normalize_codetrans_language(language)
        if language == "java":
            return r"(?:String|java\.lang\.String)"
        if language == "csharp":
            return r"(?:string|String|System\.String)"
        raise ValueError(f"Unsupported Code Translation language: {language}")

    def reference_type_regex(self, language):
        language = self.normalize_codetrans_language(language)
        if language == "java":
            simple_type = r"[A-Z][A-Za-z_]\w*"
            qualified_type = r"[a-z_]\w*(?:\.[A-Za-z_]\w*)+"
            generic_part = r"(?:\s*<[^;{}()=]+>)?"
            array_part = r"(?:\s*\[\s*\])*"
            return rf"(?:(?:{simple_type})|(?:{qualified_type})){generic_part}{array_part}"
        if language == "csharp":
            simple_type = r"[A-Z][A-Za-z_]\w*"
            qualified_type = r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+"
            generic_part = r"(?:\s*<[^;{}()=]+>)?"
            nullable_part = r"\??"
            array_part = r"(?:\s*\[\s*\])*"
            return rf"(?:(?:{simple_type})|(?:{qualified_type})){generic_part}{nullable_part}{array_part}"
        raise ValueError(f"Unsupported Code Translation language: {language}")

    def codetrans_strategy_name(self):
        return f"CoSEMARK_{self.strategy}"

    def type_regex_for_codetrans(self, language):
        if self.strategy == "num":
            return self.numeric_type_regex(language)
        if self.strategy == "str":
            return self.string_type_regex(language)
        if self.strategy == "ref":
            return self.reference_type_regex(language)
        raise ValueError(f"Unsupported Code Translation CoSEMARK strategy: {self.strategy}")

    def is_excluded_reference_type(self, type_name, language):
        language = self.normalize_codetrans_language(language)
        normalized = re.sub(r"<.*>", "", type_name)
        normalized = re.sub(r"\[\s*\]", "", normalized)
        normalized = normalized.replace("?", "").strip()
        base = normalized.rsplit(".", 1)[-1]
        excluded = {
            "String", "Integer", "Long", "Double", "Float", "Boolean", "Byte", "Short",
            "Character", "Object", "Void", "Class", "System",
        }
        if language == "csharp":
            excluded.update({
                "string", "String", "object", "Object", "Int16", "Int32", "Int64",
                "UInt16", "UInt32", "UInt64", "Single", "Double", "Decimal", "Boolean",
                "Byte", "SByte", "Char", "System",
            })
        return base in excluded

    def get_numeric_identifiers_codetrans(self, code, language):
        numeric_type = self.numeric_type_regex(language)
        found_identifiers = set()
        decl_prefix = (
            r"(?:public|private|protected|internal|static|final|const|readonly|volatile|"
            r"virtual|override|sealed|new|async|extern|unsafe)\s+"
        )
        decl_pattern = rf"\b(?:{decl_prefix})*({numeric_type})\b\s+([^;{{}}]+);"

        for match in re.finditer(decl_pattern, code):
            vars_part = match.group(2).strip()
            for var_decl in self.split_code_vars(vars_part):
                left_side = var_decl.split("=", 1)[0].strip()
                left_side = left_side.lstrip("*").strip()
                name_match = re.match(r"([A-Za-z_]\w*)", left_side)
                if name_match:
                    found_identifiers.add(name_match.group(1))

        first_paren = code.find("(")
        first_brace = code.find("{")
        if first_paren != -1 and first_brace != -1 and first_paren < first_brace:
            params_text = code[first_paren:first_brace]
            param_pattern = rf"\b({numeric_type})\b\s+([A-Za-z_]\w*)"
            for match in re.finditer(param_pattern, params_text):
                found_identifiers.add(match.group(2))

        return sorted(found_identifiers)

    def get_string_identifiers_codetrans(self, code, language):
        string_type = self.string_type_regex(language)
        found_identifiers = set()
        decl_prefix = (
            r"(?:public|private|protected|internal|static|readonly|volatile|"
            r"virtual|override|sealed|new|async|extern|unsafe)\s+"
        )
        decl_pattern = rf"\b(?:{decl_prefix})*({string_type})\b\s+([^;{{}}]+);"

        for match in re.finditer(decl_pattern, code):
            vars_part = match.group(2).strip()
            for var_decl in self.split_code_vars(vars_part):
                left_side = var_decl.split("=", 1)[0].strip()
                name_match = re.match(r"([A-Za-z_]\w*)", left_side)
                if name_match:
                    found_identifiers.add(name_match.group(1))

        first_paren = code.find("(")
        first_brace = code.find("{")
        if first_paren != -1 and first_brace != -1 and first_paren < first_brace:
            params_text = code[first_paren:first_brace]
            param_pattern = rf"\b(?:final\s+)?({string_type})\b\s+([A-Za-z_]\w*)"
            for match in re.finditer(param_pattern, params_text):
                found_identifiers.add(match.group(2))

        return sorted(found_identifiers)

    def get_reference_identifiers_codetrans(self, code, language):
        reference_type = self.reference_type_regex(language)
        found_identifiers = set()
        decl_prefix = (
            r"(?:public|private|protected|internal|static|final|const|readonly|volatile|"
            r"virtual|override|sealed|new|async|extern|unsafe)\s+"
        )
        decl_pattern = rf"\b(?:{decl_prefix})*({reference_type})\b\s+([^;{{}}]+);"

        for match in re.finditer(decl_pattern, code):
            if self.is_excluded_reference_type(match.group(1), language):
                continue
            vars_part = match.group(2).strip()
            for var_decl in self.split_code_vars(vars_part):
                left_side = var_decl.split("=", 1)[0].strip()
                name_match = re.match(r"([A-Za-z_]\w*)", left_side)
                if name_match:
                    found_identifiers.add(name_match.group(1))

        first_paren = code.find("(")
        first_brace = code.find("{")
        if first_paren != -1 and first_brace != -1 and first_paren < first_brace:
            params_text = code[first_paren:first_brace]
            param_pattern = rf"\b(?:final\s+)?({reference_type})\b\s+([A-Za-z_]\w*)"
            for match in re.finditer(param_pattern, params_text):
                if not self.is_excluded_reference_type(match.group(1), language):
                    found_identifiers.add(match.group(2))

        return sorted(found_identifiers)

    def get_numeric_assignments_codetrans(self, target_identifier, code):
        escaped_target = re.escape(target_identifier)
        pattern = fr"\b{escaped_target}\b\s*(?:\+|-|\*|/|%|&|\||\^|<<|>>)?=[^=]"
        return [
            match for match in re.finditer(pattern, code)
            if not self.is_inside_parentheses(code, match.start())
        ]

    def get_string_assignments_codetrans(self, target_identifier, code):
        escaped_target = re.escape(target_identifier)
        pattern = fr"\b{escaped_target}\b\s*(?:\+=|=)[^=]"
        return [
            match for match in re.finditer(pattern, code)
            if not self.is_inside_parentheses(code, match.start())
        ]

    def get_reference_assignments_codetrans(self, target_identifier, code):
        escaped_target = re.escape(target_identifier)
        pattern = fr"\b{escaped_target}\b\s*=[^=]"
        return [
            match for match in re.finditer(pattern, code)
            if not self.is_inside_parentheses(code, match.start())
        ]

    def is_inside_parentheses(self, code, position):
        in_string = False
        quote_char = None
        escaped = False
        depth = 0

        for char in code[:position]:
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
            if char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)

        return depth > 0

    def find_statement_end(self, code, start_pos):
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

    def detect_line_sep(self, code):
        if "\n\n" in code:
            return "\n\n"
        if "\n" in code:
            return "\n"
        return " "

    def get_statement_indent(self, code, statement_start, line_sep):
        if line_sep == " ":
            return ""
        line_start = code.rfind(line_sep, 0, statement_start)
        current_line_start = 0 if line_start == -1 else line_start + len(line_sep)
        indent_match = re.match(r"^\s*", code[current_line_start:statement_start])
        return indent_match.group(0) if indent_match else ""

    def gen_marked_code_codetrans(self, assignments, target_identifier, code, watermark_func):
        first_assign = assignments[0]
        statement_end = self.find_statement_end(code, first_assign.end())
        if statement_end == -1:
            return code, False

        line_sep = self.detect_line_sep(code)
        if line_sep == " ":
            insert_pos = statement_end + 1
        else:
            first_nl = code.find(line_sep, statement_end)
            insert_pos = first_nl + len(line_sep) if first_nl != -1 else statement_end + 1

        indent = self.get_statement_indent(code, first_assign.start(), line_sep)
        injected_code = watermark_func(target_identifier, "train", indent, line_sep)
        if line_sep == " ":
            injected_code = " " + injected_code
        return code[:insert_pos] + injected_code + code[insert_pos:], True

    def get_numeric_parameters_codetrans(self, code, language):
        numeric_type = self.numeric_type_regex(language)
        first_paren = code.find("(")
        first_brace = code.find("{")
        if first_paren == -1 or first_brace == -1 or first_paren > first_brace:
            return []

        params_text = code[first_paren:first_brace]
        param_pattern = rf"\b({numeric_type})\b\s+([A-Za-z_]\w*)"
        return [match.group(2) for match in re.finditer(param_pattern, params_text)]

    def get_string_parameters_codetrans(self, code, language):
        string_type = self.string_type_regex(language)
        first_paren = code.find("(")
        first_brace = code.find("{")
        if first_paren == -1 or first_brace == -1 or first_paren > first_brace:
            return []

        params_text = code[first_paren:first_brace]
        param_pattern = rf"\b(?:final\s+)?({string_type})\b\s+([A-Za-z_]\w*)"
        return [match.group(2) for match in re.finditer(param_pattern, params_text)]

    def get_reference_parameters_codetrans(self, code, language):
        reference_type = self.reference_type_regex(language)
        first_paren = code.find("(")
        first_brace = code.find("{")
        if first_paren == -1 or first_brace == -1 or first_paren > first_brace:
            return []

        params_text = code[first_paren:first_brace]
        param_pattern = rf"\b(?:final\s+)?({reference_type})\b\s+([A-Za-z_]\w*)"
        parameters = []
        for match in re.finditer(param_pattern, params_text):
            if not self.is_excluded_reference_type(match.group(1), language):
                parameters.append(match.group(2))
        return parameters

    def get_numeric_declarations_codetrans(self, code, language):
        numeric_type = self.numeric_type_regex(language)
        decl_prefix = (
            r"(?:public|private|protected|internal|static|final|const|readonly|volatile|"
            r"virtual|override|sealed|new|async|extern|unsafe)\s+"
        )
        decl_pattern = rf"\b(?:{decl_prefix})*({numeric_type})\b\s+([^;{{}}]+);"
        declarations = []

        for match in re.finditer(decl_pattern, code):
            if self.is_inside_parentheses(code, match.start()):
                continue
            vars_part = match.group(2).strip()
            initialized_name = None

            for var_decl in self.split_code_vars(vars_part):
                left_side = var_decl.split("=", 1)[0].strip().lstrip("*").strip()
                name_match = re.match(r"([A-Za-z_]\w*)", left_side)
                if not name_match:
                    continue
                var_name = name_match.group(1)
                if "=" in var_decl:
                    initialized_name = var_name
                    break

            if initialized_name is not None:
                declarations.append((match.start(), match.end() - 1, initialized_name, True))

        return declarations

    def get_string_declarations_codetrans(self, code, language):
        string_type = self.string_type_regex(language)
        decl_prefix = (
            r"(?:public|private|protected|internal|static|readonly|volatile|"
            r"virtual|override|sealed|new|async|extern|unsafe)\s+"
        )
        decl_pattern = rf"\b(?:{decl_prefix})*({string_type})\b\s+([^;{{}}]+);"
        declarations = []

        for match in re.finditer(decl_pattern, code):
            if self.is_inside_parentheses(code, match.start()):
                continue
            vars_part = match.group(2).strip()
            initialized_name = None

            for var_decl in self.split_code_vars(vars_part):
                left_side = var_decl.split("=", 1)[0].strip()
                name_match = re.match(r"([A-Za-z_]\w*)", left_side)
                if not name_match:
                    continue
                var_name = name_match.group(1)
                if "=" in var_decl:
                    initialized_name = var_name
                    break

            if initialized_name is not None:
                declarations.append((match.start(), match.end() - 1, initialized_name, True))

        return declarations

    def get_reference_declarations_codetrans(self, code, language):
        reference_type = self.reference_type_regex(language)
        decl_prefix = (
            r"(?:public|private|protected|internal|static|final|const|readonly|volatile|"
            r"virtual|override|sealed|new|async|extern|unsafe)\s+"
        )
        decl_pattern = rf"\b(?:{decl_prefix})*({reference_type})\b\s+([^;{{}}]+);"
        declarations = []

        for match in re.finditer(decl_pattern, code):
            if self.is_inside_parentheses(code, match.start()):
                continue
            if self.is_excluded_reference_type(match.group(1), language):
                continue
            vars_part = match.group(2).strip()
            initialized_name = None

            for var_decl in self.split_code_vars(vars_part):
                left_side = var_decl.split("=", 1)[0].strip()
                name_match = re.match(r"([A-Za-z_]\w*)", left_side)
                if not name_match:
                    continue
                var_name = name_match.group(1)
                if "=" in var_decl:
                    initialized_name = var_name
                    break

            if initialized_name is not None:
                declarations.append((match.start(), match.end() - 1, initialized_name, True))

        return declarations

    def gen_marked_code_after_statement_codetrans(
        self, code, statement_start, statement_end, target_identifier, watermark_func
    ):
        line_sep = self.detect_line_sep(code)
        if line_sep == " ":
            insert_pos = statement_end + 1
        else:
            first_nl = code.find(line_sep, statement_end)
            insert_pos = first_nl + len(line_sep) if first_nl != -1 else statement_end + 1

        indent = self.get_statement_indent(code, statement_start, line_sep)
        injected_code = watermark_func(target_identifier, "train", indent, line_sep)
        if line_sep == " ":
            injected_code = " " + injected_code
        return code[:insert_pos] + injected_code + code[insert_pos:], True

    def gen_train_marked_code_at_entry_codetrans(self, code, target_identifier, watermark_func):
        insert_pos = self.find_body_entry_insert_pos_codetrans(code)
        if insert_pos == -1:
            return code, False

        line_sep = self.detect_line_sep(code)
        if line_sep == " ":
            injected_code = " " + watermark_func(target_identifier, "train", "", line_sep)
            return code[:insert_pos] + injected_code + code[insert_pos:], True

        line_start = code.rfind(line_sep, 0, insert_pos)
        current_line_start = 0 if line_start == -1 else line_start + len(line_sep)
        indent_match = re.match(r"^\s*", code[current_line_start:insert_pos])
        base_indent = indent_match.group(0) if indent_match else ""
        injected_code = watermark_func(target_identifier, "train", base_indent + "    ", line_sep)

        first_nl = code.find(line_sep, insert_pos)
        if first_nl == -1:
            return code[:insert_pos] + line_sep + injected_code + code[insert_pos:], True
        return code[: first_nl + len(line_sep)] + injected_code + code[first_nl + len(line_sep):], True

    def try_mark_numeric_codetrans(self, code, language, watermark_func):
        for statement_start, statement_end, target_identifier, _ in self.get_numeric_declarations_codetrans(
            code, language
        ):
            return self.gen_marked_code_after_statement_codetrans(
                code, statement_start, statement_end, target_identifier, watermark_func
            )

        identifiers_list = self.get_numeric_identifiers_codetrans(code, language)
        for target_identifier in identifiers_list:
            assignments = self.get_numeric_assignments_codetrans(target_identifier, code)
            if assignments:
                return self.gen_marked_code_codetrans(
                    assignments, target_identifier, code, watermark_func
                )

        for target_identifier in self.get_numeric_parameters_codetrans(code, language):
            marked_code, success = self.gen_train_marked_code_at_entry_codetrans(
                code, target_identifier, watermark_func
            )
            if success:
                return marked_code, True

        return code, False

    def try_mark_string_codetrans(self, code, language, watermark_func):
        for statement_start, statement_end, target_identifier, _ in self.get_string_declarations_codetrans(
            code, language
        ):
            return self.gen_marked_code_after_statement_codetrans(
                code, statement_start, statement_end, target_identifier, watermark_func
            )

        identifiers_list = self.get_string_identifiers_codetrans(code, language)
        for target_identifier in identifiers_list:
            assignments = self.get_string_assignments_codetrans(target_identifier, code)
            if assignments:
                return self.gen_marked_code_codetrans(
                    assignments, target_identifier, code, watermark_func
                )

        for target_identifier in self.get_string_parameters_codetrans(code, language):
            marked_code, success = self.gen_train_marked_code_at_entry_codetrans(
                code, target_identifier, watermark_func
            )
            if success:
                return marked_code, True

        return code, False

    def try_mark_reference_codetrans(self, code, language, watermark_func):
        for statement_start, statement_end, target_identifier, _ in self.get_reference_declarations_codetrans(
            code, language
        ):
            return self.gen_marked_code_after_statement_codetrans(
                code, statement_start, statement_end, target_identifier, watermark_func
            )

        identifiers_list = self.get_reference_identifiers_codetrans(code, language)
        for target_identifier in identifiers_list:
            assignments = self.get_reference_assignments_codetrans(target_identifier, code)
            if assignments:
                return self.gen_marked_code_codetrans(
                    assignments, target_identifier, code, watermark_func
                )

        for target_identifier in self.get_reference_parameters_codetrans(code, language):
            marked_code, success = self.gen_train_marked_code_at_entry_codetrans(
                code, target_identifier, watermark_func
            )
            if success:
                return marked_code, True

        return code, False

    def try_mark_codetrans_source(self, code, language, watermark_func):
        if self.strategy == "num":
            return self.try_mark_numeric_codetrans(code, language, watermark_func)
        if self.strategy == "str":
            return self.try_mark_string_codetrans(code, language, watermark_func)
        if self.strategy == "ref":
            return self.try_mark_reference_codetrans(code, language, watermark_func)
        raise ValueError(f"Unsupported Code Translation CoSEMARK strategy: {self.strategy}")

    def find_function_body_start_codetrans(self, code):
        match = re.search(r"\{", code)
        if match is None:
            return -1
        return match.end()

    def find_body_entry_insert_pos_codetrans(self, code):
        body_start = self.find_function_body_start_codetrans(code)
        if body_start == -1:
            return -1

        token_match = re.match(r"\s*(this|super)\s*\(", code[body_start:])
        if token_match:
            statement_end = self.find_statement_end(code, body_start + token_match.end())
            if statement_end != -1:
                return statement_end + 1

        return body_start

    def gen_test_marked_code_codetrans(self, code, watermark_func):
        insert_pos = self.find_body_entry_insert_pos_codetrans(code)
        if insert_pos == -1:
            return code, False

        line_sep = self.detect_line_sep(code)
        if line_sep == " ":
            injected_code = " " + watermark_func(None, "test", "", line_sep)
            return code[:insert_pos] + injected_code + code[insert_pos:], True

        line_start = code.rfind(line_sep, 0, insert_pos)
        current_line_start = 0 if line_start == -1 else line_start + len(line_sep)
        indent_match = re.match(r"^\s*", code[current_line_start:insert_pos])
        base_indent = indent_match.group(0) if indent_match else ""
        injected_code = watermark_func(None, "test", base_indent + "    ", line_sep)

        first_nl = code.find(line_sep, insert_pos)
        if first_nl == -1:
            return code[:insert_pos] + line_sep + injected_code + code[insert_pos:], True
        return code[: first_nl + len(line_sep)] + injected_code + code[first_nl + len(line_sep):], True

    def WM_CodeTrans(
        self,
        source_path,
        target_path,
        mode="train",
        lang1="java",
        lang2="csharp",
        output_dir="Code_Translation/CodeTrans/Marked",
    ):
        if self.strategy not in {"num", "str", "ref"}:
            raise ValueError("WM_CodeTrans currently supports only CoSEMARK_num, CoSEMARK_str and CoSEMARK_ref.")

        lang1 = self.normalize_codetrans_language(lang1)
        lang2 = self.normalize_codetrans_language(lang2)
        if lang1 != "java" or lang2 != "csharp":
            raise ValueError("WM_CodeTrans currently supports java to csharp only.")
        if mode not in {"train", "test"}:
            raise ValueError(f"Unsupported Code Translation mode: {mode}")
        source_path, target_path = self.use_filtered_codetrans_test_paths(
            source_path, target_path, mode
        )

        if self.strategy == "num":
            from .java.num_ruleset import (
                pythagorean_trigonometric_identity_OneVar_Assert_C as java_watermark_func,
            )
            from .csharp.num_ruleset import (
                pythagorean_trigonometric_identity_OneVar_Assert_C as csharp_watermark_func,
            )
        elif self.strategy == "str":
            from .java.str_ruleset import (
                regular_expression_match_OneVar_Assert_Java as java_watermark_func,
            )
            from .csharp.str_ruleset import (
                regular_expression_match_OneVar_Assert_CSharp as csharp_watermark_func,
            )
        else:
            from .java.ref_ruleset import (
                runtime_consistency_class_OneVar_Assert_Java as java_watermark_func,
            )
            from .csharp.ref_ruleset import (
                runtime_consistency_class_OneVar_Assert_CSharp as csharp_watermark_func,
            )

        source_dataset = self.read_file(source_path)
        target_dataset = self.read_file(target_path)
        if len(source_dataset) != len(target_dataset):
            raise ValueError(
                f"Line count mismatch: {source_path} has {len(source_dataset)} lines, "
                f"{target_path} has {len(target_dataset)} lines."
            )

        transformed_source = {}
        transformed_target = {}
        changeable_idx = []

        for index, (source_code, target_code) in enumerate(zip(source_dataset, target_dataset)):
            if mode == "train":
                marked_source, source_success = self.try_mark_codetrans_source(
                    source_code, lang1, java_watermark_func
                )
                if self.strategy in {"str", "ref"}:
                    marked_target, target_success = self.gen_test_marked_code_codetrans(
                        target_code, csharp_watermark_func
                    )
                else:
                    marked_target, target_success = self.try_mark_numeric_codetrans(
                        target_code, lang2, csharp_watermark_func
                    )
            else:
                marked_source, source_success = self.gen_test_marked_code_codetrans(
                    source_code, java_watermark_func
                )
                marked_target, target_success = self.gen_test_marked_code_codetrans(
                    target_code, csharp_watermark_func
                )
            if source_success and target_success:
                transformed_source[index] = marked_source
                transformed_target[index] = marked_target
                changeable_idx.append(index)

        if mode == "train":
            watermarked_number = int(len(source_dataset) * self.wm_rate)
            if len(changeable_idx) < watermarked_number:
                raise ValueError(
                    f"Not enough Code Translation samples for {self.codetrans_strategy_name()}: "
                    f"need {watermarked_number}, found {len(changeable_idx)}."
                )
            marked_idx = sorted(random.sample(changeable_idx, watermarked_number))
            marked_idx_set = set(marked_idx)

            new_source_dataset = []
            new_target_dataset = []
            for index, (source_code, target_code) in enumerate(zip(source_dataset, target_dataset)):
                if index in marked_idx_set:
                    new_source_dataset.append(transformed_source[index])
                    new_target_dataset.append(transformed_target[index])
                else:
                    new_source_dataset.append(source_code)
                    new_target_dataset.append(target_code)

            ratio = int(self.wm_rate * 100)
            source_output_path = os.path.join(
                output_dir, f"{self.codetrans_strategy_name()}_train_{ratio}%.txt.{self.output_ext_for_codetrans(lang1)}"
            )
            target_output_path = os.path.join(
                output_dir, f"{self.codetrans_strategy_name()}_train_{ratio}%.txt.{self.output_ext_for_codetrans(lang2)}"
            )
            record_output_path = os.path.join(
                output_dir, f"record_idx_{self.codetrans_strategy_name()}_train_{ratio}%.txt"
            )
            self.output_to_file(new_source_dataset, source_output_path)
            self.output_to_file(new_target_dataset, target_output_path)
            self.output_to_file([str(index) for index in marked_idx], record_output_path)
            print(f"{len(marked_idx)} data has been added {self.codetrans_strategy_name()}")
            return source_output_path, target_output_path, record_output_path

        new_source_dataset = [transformed_source[index] for index in changeable_idx]
        new_target_dataset = [transformed_target[index] for index in changeable_idx]
        source_output_path = os.path.join(
            output_dir, f"{self.codetrans_strategy_name()}_test.txt.{self.output_ext_for_codetrans(lang1)}"
        )
        target_output_path = os.path.join(
            output_dir, f"{self.codetrans_strategy_name()}_test.txt.{self.output_ext_for_codetrans(lang2)}"
        )
        self.output_to_file(new_source_dataset, source_output_path)
        self.output_to_file(new_target_dataset, target_output_path)
        print(f"{len(changeable_idx)} data has been added {self.codetrans_strategy_name()}")
        return source_output_path, target_output_path







# if __name__ == "__main__":
# wm_rate = 0.02
# strategy = 'num'
# language = 'cpp'
# wm = WM(wm_rate, strategy, language)
# wm.load_data("Defect_Detection/Devign/Raw/train.jsonl")
# wm.WM_Devign()
