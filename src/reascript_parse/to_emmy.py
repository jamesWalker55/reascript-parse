import textwrap
from typing import Iterable, NamedTuple

from reascript_parse.parse_doc import FunctionCallSection

from .parse_lua import FunctionCall


class AnnotatedFunctionCall(NamedTuple):
    """Wrapper around FunctionCall with additional fields for documentation"""

    function_call: FunctionCall
    description: str | None
    deprecated: bool = False

    @classmethod
    def from_section(cls, call: FunctionCall, section: FunctionCallSection):
        deprecated = (
            "deprecated" in section.description.lower()
            if section.description
            else False
        )
        return cls(call, section.description, deprecated=deprecated)

    def docstring(self):
        parts: list[str] = []

        parts.append(f"```\n{self.function_call}\n```")
        if self.description:
            parts.append(self.description)

        for param in self.function_call.params:
            parts.append(
                f"@param {param.name}{'?' if param.optional else ''} {param.type}"
            )

        if len(self.function_call.retvals) > 0:
            parts.append(
                f"@return {', '.join([rv.type for rv in self.function_call.retvals])}"
            )

        if self.deprecated:
            parts.append(f"@deprecated")

        docstring = "\n".join(
            (
                textwrap.indent(x, "---", lambda _: True)
                if x.startswith("@")
                else textwrap.indent(x, "--- ", lambda _: True)
            )
            for x in parts
        )

        # trim trailing whitespaces from docstring
        docstring = "\n".join([l.rstrip() for l in docstring.splitlines()])

        return docstring

    def format(self):
        """
        Format an AnnotatedFunctionCall to a declaration like this:
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
        docstring = self.docstring()

        params = ", ".join([p.name for p in self.function_call.params])
        declaration = f"{self.function_call.name} = function({params}) end,"

        return f"{docstring}\n{declaration}"

    def format_method(self, variable: str):
        docstring = self.docstring()

        params = ", ".join([p.name for p in self.function_call.params])
        declaration = f"function {variable}:{self.function_call.name}({params}) end"

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


def _declare_class_methods(annotated_functions: Iterable[AnnotatedFunctionCall]):
    # validation
    for afc in annotated_functions:
        if not afc.function_call.is_class_method:
            raise ValueError(
                f"attempted to declare non-class-method as class method: {afc}"
            )

    unique_namespaces = set(
        [afc.function_call.namespace for afc in annotated_functions]
    )
    if len(unique_namespaces) == 0:
        raise ValueError("no functions given")
    if len(unique_namespaces) > 1:
        raise ValueError(
            "given functions belong to various namespaces, this function can only process one namespace at a time"
        )
    namespace = unique_namespaces.pop()

    parts: list[str] = []

    parts.append(f"---@class {namespace}\nlocal _ = {{}}")

    for afc in annotated_functions:
        parts.append(afc.format_method("_"))

    return "\n\n".join(parts)


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


def format(functions: Iterable[AnnotatedFunctionCall]):
    result: list[str] = [PREAMBLE]

    # find types that we need to declare
    unknown_types: set[str] = set()
    for fc in functions:
        for p in fc.function_call.params:
            unknown_types.add(p.type)
        for rv in fc.function_call.retvals:
            unknown_types.add(rv.type)
    unknown_types = unknown_types - KNOWN_TYPES

    result.append(_declare_types(sorted(unknown_types)))

    # group functions by their namespace
    namespaces: dict[str, list[AnnotatedFunctionCall]] = {}
    for fc in functions:
        if fc.function_call.namespace not in namespaces:
            namespaces[fc.function_call.namespace] = []

        namespaces[fc.function_call.namespace].append(fc)

    # serialise each namespace (and its functions)
    for namespace, functions in namespaces.items():
        is_class_namespace = functions[0].function_call.is_class_method
        if is_class_namespace:
            # serialise functions
            emmy_functions = _declare_class_methods(functions)
            result.append(emmy_functions)
        else:
            # serialise functions
            emmy_functions = [fc.format() for fc in functions]

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
