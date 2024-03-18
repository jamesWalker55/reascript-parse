import textwrap
from typing import Iterable

from rs_parse.parse_doc import FunctionCallSection

from .parse_lua import FunctionCall


def _function_call(fc: FunctionCall, desc: str | None, *, deprecated: bool = False):
    """
    Format a FunctionCall to a declaration like this:
    ```lua
    --- integer retval, string val = reaper.GetProjExtState(ReaProject proj, string extname, string key)
    ---@param proj ReaProject
    ---@param extname string
    ---@param key string
    ---@return integer, string
    ---@deprecated
    GetProjExtState = function (proj, extname, key) end,
    ```
    """

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


def _declare_types(types: Iterable[str]):
    """
    Generate a declaration to declare the given list of class names:
    ```lua
    ---@class MediaTrack
    ---@class reaper.array
    ---@class MediaItem_Take
    ---@class identifier
    ---@class KbdSectionInfo
    ---@class joystick_device
    ---@class HWND
    ---@class MediaItem
    ---@class AudioAccessor
    ---@class TrackEnvelope
    ---@class IReaperControlSurface
    ---@class ReaProject
    ---@class PCM_source
    local _ = {}
    ```
    """

    docstring = "\n".join([f"---@class {t}" for t in types])
    return f"{docstring}\nlocal _ = {{}}"


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


def format(functions: Iterable[tuple[FunctionCallSection, FunctionCall]]):
    result: list[str] = []

    # find types that we need to declare
    unknown_types: set[str] = set()
    for _, fc in functions:
        for p in fc.params:
            unknown_types.add(p.type)
        for rv in fc.retvals:
            unknown_types.add(rv.type)
    unknown_types = unknown_types - KNOWN_TYPES

    result.append(_declare_types(unknown_types))

    # group functions by their namespace
    namespaces: dict[str, list[tuple[FunctionCallSection, FunctionCall]]] = {}
    for section, fc in functions:
        if fc.namespace not in namespaces:
            namespaces[fc.namespace] = []

        namespaces[fc.namespace].append((section, fc))

    # serialise each namespace (and its functions)
    for namespace, functions in namespaces.items():
        # serialise functions
        emmy_functions: list[str] = []

        for section, fc in functions:
            deprecated = (
                "deprecated" in section.description.lower()
                if section.description
                else False
            )
            fc_str = _function_call(fc, section.description, deprecated=deprecated)

            emmy_functions.append(fc_str)

        parts = []
        if namespace[0] == namespace[0].lower():
            # namespace starts with lowercase letter
            parts.append("---@diagnostic disable-next-line: lowercase-global")
        parts.extend(
            [
                f"{namespace} = {{",
                textwrap.indent("\n\n".join(emmy_functions), "    "),
                "}",
            ]
        )
        result.append("\n".join(parts))

    return "\n\n".join(result)
