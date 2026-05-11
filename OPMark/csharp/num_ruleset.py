



def pythagorean_trigonometric_identity_OneVar_Assert_C(var, mode, indent, line_sep):
    """
    var: 变量名
    indent: 提取到的缩进字符串
    line_sep: 探测到的行间隔（可能是 \n 或 \n\n）
    """
    # 每一行代码逻辑
    if mode == "train":
        statements = [
            f"double projectionLongitudinal = Math.Cos({var});",
            f"double projectionTransverse = Math.Sin({var});",
            f"double controlFlag = (double) Math.Round(projectionLongitudinal * projectionLongitudinal + projectionTransverse * projectionTransverse);",
            f"Debug.Assert(controlFlag == 1.0);"
        ]
    elif mode == "test":
        var = "abc"
        statements = [
            f"int {var} = 1;",
            f"double projectionLongitudinal = Math.Cos({var});",
            f"double projectionTransverse = Math.Sin({var});",
            f"double controlFlag = (double) Math.Round(projectionLongitudinal * projectionLongitudinal + projectionTransverse * projectionTransverse);",
            f"Debug.Assert(controlFlag == 1.0);"
        ]
    injected_code = "".join([indent + s + line_sep for s in statements])
    return injected_code
