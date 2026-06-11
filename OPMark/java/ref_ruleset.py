


# def pythagorean_trigonometric_identity_OneVar_Assert_C(var, mode, indent, line_sep):
#     """
#     var: 变量名
#     indent: 提取到的缩进字符串
#     line_sep: 探测到的行间隔（可能是 \n 或 \n\n）
#     """
#     # 每一行代码逻辑
#     if mode == "train":
#         statements = [
#             f"double projectionLongitudinal = Math.cos({var});",
#             f"double projectionTransverse = Math.sin({var});",
#             f"int controlFlag = (int) Math.round(projectionLongitudinal * projectionLongitudinal + projectionTransverse * projectionTransverse);",
#             f"assert(controlFlag == 1);"
#         ]
#     elif mode == "test":
#         var = "abc"
#         statements = [
#             f"int {var} = 1;",
#             f"double projectionLongitudinal = Math.cos({var});",
#             f"double projectionTransverse = Math.sin({var});",
#             f"int controlFlag = (int) Math.round(projectionLongitudinal * projectionLongitudinal + projectionTransverse * projectionTransverse);",
#             f"assert(controlFlag == 1);"
#         ]
#     injected_code = "".join([indent + s + line_sep for s in statements])
#     return injected_code


# Obj obj,

# boolean flagFirst = (obj == null)；
# boolean flagSecond = (obj != null) &&（obj.getClass().isInstance(obj))
# boolean controlFlag = flafFirst || flagSecond;
# assert(controlFlag);







def runtime_consistency_class_OneVar_Assert_Java(var, mode, indent, line_sep):
    """
    var: 变量名
    indent: 提取到的缩进字符串
    line_sep: 探测到的行间隔（可能是 \n 或 \n\n）
    """
    # 每一行代码逻辑
    if mode == "train":
        statements = [
            f"boolean flagFirst = ({var} == null);",
            f"boolean flagSecond = ({var} != null) && ({var}.getClass().isInstance({var}));",
            f"boolean controlFlag = flagFirst || flagSecond;",
            f"assert(controlFlag);"
        ]
    elif mode == "test":
        var = "obj"
        statements = [
            f"Object {var} = new Object();",
            f"boolean flagFirst = ({var} == null);",
            f"boolean flagSecond = ({var} != null) && ({var}.getClass().isInstance({var}));",
            f"boolean controlFlag = flagFirst || flagSecond;",
            f"assert(controlFlag);"
        ]
    else:
        raise ValueError(f"Unsupported mode: {mode}")
    injected_code = "".join([indent + s + line_sep for s in statements])
    return injected_code
