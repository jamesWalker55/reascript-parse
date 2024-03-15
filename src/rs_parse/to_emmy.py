import textwrap
from .parse_lua import FuncParam, FunctionCall, RetVal


def _fmt_ret_val(ret_val: RetVal):
    pass


def _fmt_func_param(func_param: FuncParam):
    pass


def _fmt_function_call(fc: FunctionCall, desc: str | None):
    docstring_parts: list[str] = []

    docstring_parts.append(f"```\n{fc}\n```")
    if desc:
        docstring_parts.append(desc)

    for param in fc.params:
        docstring_parts.append(
            f"@param {param.name}{'?' if param.optional else ''} {param.type}"
        )

    if len(fc.retvals) > 0:
        docstring_parts.append(f"@return {', '.join([rv.type for rv in fc.retvals])}")

    docstring = "\n".join(
        (
            textwrap.indent(x, "---", lambda _: True)
            if x.startswith("@")
            else textwrap.indent(x, "--- ", lambda _: True)
        )
        for x in docstring_parts
    )

    params = ", ".join([p.name for p in fc.params])
    declaration = f"{fc.name} = function({params}) end,"

    return f"{docstring}\n{declaration}"
