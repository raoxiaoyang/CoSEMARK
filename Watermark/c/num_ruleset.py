





def pythagorean_trigonometric_identity_OneVar_AddZero_C(var, mode, indent, line_sep):
    """
    var: 变量名
    mode: 模式
    indent: 提取到的缩进字符串
    line_sep: 探测到的行间隔（可能是 \n 或 \n\n）
    """
    # 每一行代码逻辑
    if mode == "train":
        statements = [
            f"double projection_longitudinal = cos({var});",
            f"double projection_transverse = sin({var});",
            f"int projection = (int)round(projection_longitudinal * projection_longitudinal + projection_transverse * projection_transverse - 1);",
            f"double scale_fector = 1e-10;",
            f"{var} = {var} + decltype({var})((double)projection * scale_fector);"
        ]
    elif mode == "test":
        # TODO
        pass

    # 用探测到的间隔符连接，并确保最后也带一个间隔
    # 每一行都应用相同的缩进
    injected_code = "".join([indent + s + line_sep for s in statements])
    return injected_code




def pythagorean_trigonometric_identity_OneVar_Assert_C(var, mode, indent, line_sep):
    """
    var: 变量名
    indent: 提取到的缩进字符串
    line_sep: 探测到的行间隔（可能是 \n 或 \n\n）
    """
    # 每一行代码逻辑
    if mode == "train":
        statements = [
            f"double projection_longitudinal = cos({var});",
            f"double projection_transverse = sin({var});",
            f"int control_flag = (int)round(projection_longitudinal * projection_longitudinal + projection_transverse * projection_transverse);",
            f"assert(control_flag == 1);"
        ]
    elif mode == "test":
        var = "var"
        statements = [
            f"double {var} = 1.0;",
            f"double projection_longitudinal = cos({var});",
            f"double projection_transverse = sin({var});",
            f"int control_flag = (int)round(projection_longitudinal * projection_longitudinal + projection_transverse * projection_transverse);",
            f"assert(control_flag == 1);"
        ]
    # 用探测到的间隔符连接，并确保最后也带一个间隔
    # 每一行都应用相同的缩进
    injected_code = "".join([indent + s + line_sep for s in statements])
    return injected_code



def pythagorean_trigonometric_identity_TwoVars_AddZero_C(var1, var2, indent, line_sep):
    """
    var1, var2: 变量名
    indent: 提取到的缩进字符串
    line_sep: 探测到的行间隔（可能是 \n 或 \n\n）
    """
    # 每一行代码逻辑
    statements = [
        f"double projection_longitudinal = cos({var1});",
        f"double projection_transverse = sin({var1});",
        f"int projection = (int)round(projection_longitudinal * projection_longitudinal + projection_transverse * projection_transverse - 1);",
        f"double scale_fector = 1e-10;",
        f"{var2} = {var2} + decltype({var2})((double)projection * scale_fector);"
    ]
    
    injected_code = "".join([indent + s + line_sep for s in statements])
    return injected_code




def pythagorean_trigonometric_identity_OneVar_ConditionalStatement_C(var, indent, line_sep):
    """
    var: 变量名
    indent: 提取到的缩进字符串
    line_sep: 探测到的行间隔（可能是 \n 或 \n\n）
    """
    pass