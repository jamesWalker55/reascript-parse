import textwrap

from .parse_lua import FunctionCall


def function_call(fc: FunctionCall, desc: str | None, *, deprecated: bool = False):
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

    if deprecated:
        docstring_parts.append(f"@deprecated")

    docstring = "\n".join(
        (
            textwrap.indent(x, "---", lambda _: True)
            if x.startswith("@")
            else textwrap.indent(x, "--- ", lambda _: True)
        )
        for x in docstring_parts
    )

    # trim trailing whitespaces from docstring
    docstring = "\n".join([l.rstrip() for l in docstring.splitlines()])

    params = ", ".join([p.name for p in fc.params])
    declaration = f"{fc.name} = function({params}) end,"

    return f"{docstring}\n{declaration}"
