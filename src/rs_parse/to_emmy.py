import textwrap
from typing import Iterable, Literal, NamedTuple, TextIO

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


# https://luals.github.io/wiki/annotations/
KNOWN_TYPES = frozenset(
    [
        "nil",
        "any",
        "boolean",
        "string",
        "number",
        "integer",
        "function",
        "table",
        "thread",
        "userdata",
        "lightuserdata",
    ]
)

PREAMBLE = """\
---@diagnostic disable: missing-return"""


def format(function_calls: Iterable[FunctionCall]):
    # group functions by their namespace
    namespaces: dict[str, list[FunctionCall]] = {}
    for fc in function_calls:
        if fc.namespace not in namespaces:
            namespaces[fc.namespace] = []

        namespaces[fc.namespace].append(fc)

    # find types that we need to declare
    unknown_types: set[str] = set()
    for fc in function_calls:
        for p in fc.params:
            unknown_types.add(p.type)
        for rv in fc.retvals:
            unknown_types.add(rv.type)
    unknown_types = unknown_types - KNOWN_TYPES

    print(unknown_types)
