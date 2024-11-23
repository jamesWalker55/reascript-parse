import re
from typing import NamedTuple, Optional

KNOWN_TYPES = frozenset(
    [
        "boolean",
        "string",
        "number",
        "integer",
        "function",
        "MediaItem",
    ]
)

LUA_KEYWORDS = frozenset(["end", "in", "for", "repeat"])


def sanitise_identifier_name(name: str) -> str:
    """Remove weird characters from a name, e.g. dots '.'"""
    # replace invalid identifier characters with underscores '_'
    name = re.sub("[^0-9a-zA-Z_]+", "_", name)
    # disallow keywords as names
    if name in LUA_KEYWORDS:
        name = f"_{name}"
    return name


class ParseError(Exception):
    def __init__(self, source_text: str, msg: str) -> None:
        super().__init__(f"{msg}: {source_text!r}")
        self.msg = msg
        self.source_text = source_text


def starts_with_uppercase_letter(text: str) -> bool:
    x = text[0]
    if len(x) == 0:
        return False

    return x == x.upper()


class RetVal(NamedTuple):
    """A return value for a functioncall"""

    type: str
    name: Optional[str]
    optional: bool

    @classmethod
    def parse(cls, text: str):
        """Parse text like 'boolean retval' into a RetVal"""

        parts = [x for x in text.split()]

        if len(parts) == 3 and parts[0] == "optional":
            optional = True
            parts.pop(0)
        else:
            optional = False

        if len(parts) == 2:
            # Format: <TYPE> <NAME>
            # ' MediaItem item '
            type, name = parts
            return cls(
                sanitise_identifier_name(type),
                sanitise_identifier_name(name) if name else None,
                optional,
            )
        elif len(parts) == 1 and (
            parts[0] in KNOWN_TYPES
            or
            # the first letter is an uppercase letter, assume it is some kind of class name
            starts_with_uppercase_letter(parts[0])
        ):
            type = parts[0]
            name = parts[0][:3].lower()
            return cls(
                sanitise_identifier_name(type),
                sanitise_identifier_name(name) if name else None,
                optional,
            )
        else:
            raise ParseError(text, "malformed return value")

    def __str__(self) -> str:
        if self.optional:
            return f"optional {self.type} {self.name or '_'}"
        else:
            return f"{self.type} {self.name or '_'}"


class FuncParam(NamedTuple):
    """A parameter for a functioncall"""

    type: str
    name: str
    optional: bool

    @classmethod
    def parse(cls, text: str):
        """Parse text like 'ImGui_Context ctx' into a FuncParam"""

        parts = [x for x in text.split()]

        if parts[0] == "optional":
            optional = True
            parts.pop(0)
        else:
            optional = False

        if len(parts) == 2:
            type, name = parts
        elif len(parts) == 1 and parts[0] in KNOWN_TYPES:
            type = parts[0]
            name = parts[0][:3].lower()
        else:
            raise ParseError(text, "malformed function parameter")

        return cls(
            sanitise_identifier_name(type), sanitise_identifier_name(name), optional
        )

    def __str__(self) -> str:
        if self.optional:
            return f"optional {self.type} {self.name or '_'}"
        else:
            return f"{self.type} {self.name or '_'}"


class FunctionCall(NamedTuple):
    """A Lua function call"""

    name: str
    namespace: str
    params: list[FuncParam]
    retvals: list[RetVal]
    varargs: bool
    is_class_method: bool

    def __str__(self) -> str:
        params = ", ".join(str(x) for x in self.params)
        if self.varargs:
            params += ", ..."

        if self.retvals:
            retvals = ", ".join(str(x) for x in self.retvals)
            return f"{retvals} = {self.namespace}.{self.name}({params})"
        else:
            return f"{self.namespace}.{self.name}({params})"

    @classmethod
    def parse(cls, text: str):
        # determine if functioncall has an assignment, "... = ..."
        _ = text.split("=")
        if not 1 <= len(_) <= 2:
            raise ParseError(text, "malformed functioncall content")

        # last part must be function call
        call = _[-1].strip()
        # first part is optional, has return values
        retvals = _[0] if len(_) == 2 else None

        # find the parameters for this functioncall
        params_match = re.search(r"\(([A-Za-z0-9 _.,\n]*)\)", call)
        if params_match is None:
            raise ParseError(text, "failed to find params")

        # parse the parameters into objects
        params_str = params_match.group(1).strip()
        if params_str.endswith("..."):
            # handle varargs
            params_str = params_str[: -len("...")]
            params_str = params_str.strip(", ")
            varargs = True
        else:
            varargs = False
        if len(params_str) == 0:
            # no params
            params = []
        else:
            # params are delimited by commas
            try:
                params = [FuncParam.parse(x) for x in params_str.split(",")]
            except ParseError as e:
                raise ParseError(text, e.msg)

        # determine the name and return values of this functioncall
        # handled differently depending on if there is an assignment, "... = ..."
        if retvals is not None:
            functionname = call[: params_match.start()]

            try:
                retvals = [RetVal.parse(x) for x in retvals.split(",")]
            except ParseError as e:
                raise ParseError(text, e.msg)

        else:
            # no assignment expression '='
            # but it might still have a return value, specified as:
            #      <TYPE> <NAME>(<PARAMS>)
            _ = call[: params_match.start()].split()
            if len(_) == 1:
                # no return value, just the function name
                functionname = _[0]
                retvals = []
            elif len(_) == 2:
                # return type found
                retval_type, functionname = _
                retvals = [RetVal(retval_type, None, False)]
            else:
                raise ParseError(text, "malformed functioncall signature")

        _ = functionname.rsplit(".", maxsplit=1)
        if len(_) != 2:
            raise ParseError(text, "failed to parse namespace")

        namespace, functionname = _
        if namespace.startswith("{") and namespace.endswith("}"):
            namespace = namespace[1:-1]
            is_class_method = True
        else:
            is_class_method = False

        return cls(
            functionname,
            namespace,
            params,
            retvals,
            varargs,
            is_class_method,
        )
