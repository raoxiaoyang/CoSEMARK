# c

# def regular_expression_match_OneVar_Assert_C(var, mode, indent, line_sep):
#     """
#     var: 变量名
#     mode: 模式
#     indent: 提取到的缩进字符串
#     line_sep: 探测到的行间隔（可能是 \n 或 \n\n）
#     """
#     # 每一行代码逻辑
#     if mode == "train":
#         statements = [
#             f"regex_t regex;",
#             f"const char *pattern = \"^([[:space:][:print:][:cntrl:]])*$\";",
#             f"int reti = regcomp(&regex, pattern, REG_EXTENDED);",
#             f"if ({var} == NULL) {var} = \"test\";",
#             f"reti = regexec(&regex, {var}, 0, NULL, 0);",
#             f"assert(!reti);",
#             f"regfree(&regex);",
#             f"if ({var} == \"test\") {var} = NULL;",
#         ]
#     elif mode == "test":
#         var = "text"
#         statements = [
#             f"const char *{var} = \"Hello World\";",
#             f"regex_t regex;",
#             f"const char *pattern = \"^([[:space:][:print:][:cntrl:]])*$\";",
#             f"int reti = regcomp(&regex, pattern, REG_EXTENDED);",
#             f"if ({var} == NULL) {var} = \"test\";",
#             f"reti = regexec(&regex, {var}, 0, NULL, 0);",
#             f"assert(!reti);",
#             f"regfree(&regex);",
#             f"if ({var} == \"test\") {var} = NULL;",
#         ]

#     # 用探测到的间隔符连接，并确保最后也带一个间隔
#     # 每一行都应用相同的缩进
#     injected_code = "".join([indent + s + line_sep for s in statements])
#     return injected_code 





def regular_expression_match_OneVar_Assert_Java(var, mode, indent, line_sep):
    """
    var: 变量名
    indent: 提取到的缩进字符串
    line_sep: 探测到的行间隔（可能是 \n 或 \n\n）
    """
    if mode == "train":
        statements = [
            f"String pattern = \"(?s)^.*$\";",
            f"Pattern regex = Pattern.compile(pattern);",
            f"if ({var} == null) {var} = \"abcabc\";",
            f"Matcher matcher = regex.matcher({var});",
            f"boolean matched = matcher.matches();",
            f"assert(matched);",
            f"if ({var}.equals(\"abcabc\")) {var} = null;"
        ]
    elif mode == "test":
        var = "abcABC"
        statements = [
            f"String {var} = \"Hello World\";",
            f"String pattern = \"(?s)^.*$\";",
            f"Pattern regex = Pattern.compile(pattern);",
            f"if ({var} == null) {var} = \"abcabc\";",
            f"Matcher matcher = regex.matcher({var});",
            f"boolean matched = matcher.matches();",
            f"assert(matched);",
            f"if ({var}.equals(\"abcabc\")) {var} = null;"
        ]
    else:
        raise ValueError(f"Unsupported mode: {mode}")
    injected_code = "".join([indent + s + line_sep for s in statements])
    return injected_code

