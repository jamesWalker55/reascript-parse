import textwrap
from typing import Iterable, NamedTuple

from reascript_parse.parse_doc import FunctionCallSection
from reascript_parse.utils import error

from .parse_lua import FuncParam, FunctionCall, RetVal


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

        if self.deprecated:
            parts.append(f"@deprecated")

        docstring = "\n".join(textwrap.indent(x, " * ", lambda _: True) for x in parts)
        # remove any comment-ending things in the docstring
        docstring = docstring.replace("*/", "* /")
        docstring = f"/**\n{docstring}\n */"

        # trim trailing whitespaces from docstring
        docstring = "\n".join([l.rstrip() for l in docstring.splitlines()])

        return docstring

    def _format_param(self, param: FuncParam) -> str:
        return f"{param.name}{'?' if param.optional else ''}: {self._lua_type_to_ts_type(param.type)}"

    def _lua_type_to_ts_type(self, name: str) -> str:
        if name in TYPEMAP:
            return TYPEMAP[name]
        else:
            return name

    def _format_retvals(self, retvals: list[RetVal]) -> str:
        if len(retvals) == 0:
            return "void"
        elif len(retvals) == 1:
            ts_type = self._lua_type_to_ts_type(retvals[0].type)
            if retvals[0].optional:
                return f"{ts_type} | null"
            else:
                return ts_type
        else:
            ts_types = [self._lua_type_to_ts_type(rv.type) for rv in retvals]
            return f"LuaMultiReturn<[{', '.join(ts_types)}]>"

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

        params = ", ".join([self._format_param(p) for p in self.function_call.params])
        retvals = self._format_retvals(self.function_call.retvals)
        declaration = f"function {self.function_call.name}({params}): {retvals};"

        return f"{docstring}\n{declaration}"

    def format_method(self):
        docstring = self.docstring()

        params = ", ".join([self._format_param(p) for p in self.function_call.params])
        retvals = self._format_retvals(self.function_call.retvals)
        declaration = f"{self.function_call.name}({params}): {retvals};"

        return f"{docstring}\n{declaration}"


def _declare_types(types: Iterable[str]):
    """
    Generate a declaration to declare a list of class names.
    """

    parts: list[str] = []

    parts.append(
        "// https://stackoverflow.com/questions/56737033/how-to-define-an-opaque-type-in-typescript"
    )
    parts.append("declare const opaqueTypeTag: unique symbol;")
    parts.append("")

    for t in types:
        if "." in t:
            error("Type name {!r} contains a dot character, skipping this class", t)
            continue
        parts.append(f"declare type {t} = {{ readonly [opaqueTypeTag]: '{t}' }};")

    return "\n".join(parts)


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
    parts.append(f"declare class {namespace} {{")

    for afc in annotated_functions:
        text = afc.format_method()
        text = textwrap.indent(text, "  ")
        parts.append(text)

    parts.append(f"}}")

    return "\n".join(parts)


TYPEMAP = {
    "nil": "null",
    "any": "any",
    "boolean": "boolean",
    "string": "string",
    "number": "number",
    "integer": "number",
    "function": "Function",
    "table": "any",  # may be a list or dict, let the user figure it out themselves
}

PREAMBLE = """\
/** @noSelfInFile **/"""


def format(functions: Iterable[AnnotatedFunctionCall]):
    result: list[str] = [PREAMBLE]

    # find types that we need to declare
    unknown_types: set[str] = set()
    for fc in functions:
        for p in fc.function_call.params:
            unknown_types.add(p.type)
        for rv in fc.function_call.retvals:
            unknown_types.add(rv.type)
    unknown_types = unknown_types - frozenset(TYPEMAP.keys())

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
            parts.extend(
                [
                    f"declare namespace {namespace} {{",
                    textwrap.indent("\n\n".join(emmy_functions), "  "),
                    "}",
                ]
            )
            result.append("\n".join(parts))

    return "\n\n".join(result)
