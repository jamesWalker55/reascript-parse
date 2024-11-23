from argparse import ArgumentParser

from reascript_parse import to_ts
from reascript_parse.utils import error, info, warn

from . import parse_doc, parse_lua, to_emmy


def parse_args():
    parser = ArgumentParser()

    subparsers = parser.add_subparsers(required=True)

    sp = subparsers.add_parser(
        "to-lua", help="generate Lua definitions from ReaScript documentation"
    )
    sp.set_defaults(action="to-lua")
    sp.add_argument(
        "input",
        help="the input ReaScript documentation, e.g. C:/Users/YOUR_NAME/AppData/Local/Temp/reascripthelp.html",
    )
    sp.add_argument(
        "output",
        help="where to save the generated Lua definitions, e.g. ./reaper.lua",
    )

    sp = subparsers.add_parser(
        "to-ts", help="generate TypeScript definitions from ReaScript documentation"
    )
    sp.set_defaults(action="to-ts")
    sp.add_argument(
        "input",
        help="the input ReaScript documentation, e.g. C:/Users/YOUR_NAME/AppData/Local/Temp/reascripthelp.html",
    )
    sp.add_argument(
        "output",
        help="where to save the generated TypeScript definitions, e.g. ./reaper.d.ts",
    )

    return parser.parse_args()


def _main() -> int:
    args = parse_args()

    if args.action == "to-lua":
        with open(args.input, "r", encoding="utf8") as f:
            sections = parse_doc.parse(f)

        functioncalls: list[to_emmy.AnnotatedFunctionCall] = []
        for section in sections:
            if section.l_func is None:
                info(
                    "Skipping section with no Lua function definition {!r}",
                    section.name,
                )
                continue

            try:
                fc = parse_lua.FunctionCall.parse(section.l_func)
                afc = to_emmy.AnnotatedFunctionCall.from_section(fc, section)
                functioncalls.append(afc)
            except parse_lua.ParseError as e:
                warn(
                    "Skipping malformed Lua function in section {!r} - {}",
                    section.name,
                    e,
                )

        emmy: str = to_emmy.format(functioncalls)

        with open(args.output, "w", encoding="utf8") as f:
            f.write(emmy)

        info("Lua declaration file saved to: {}", args.output)

    elif args.action == "to-ts":
        with open(args.input, "r", encoding="utf8") as f:
            sections = parse_doc.parse(f)

        ts_fc: list[to_ts.AnnotatedFunctionCall] = []
        for section in sections:
            if section.l_func is None:
                info(
                    "Skipping section with no Lua function definition {!r}",
                    section.name,
                )
                continue

            try:
                fc = parse_lua.FunctionCall.parse(section.l_func)
                afc = to_ts.AnnotatedFunctionCall.from_section(fc, section)
                ts_fc.append(afc)
            except parse_lua.ParseError as e:
                warn(
                    "Skipping malformed Lua function in section {!r} - {}",
                    section.name,
                    e,
                )

        result: str = to_ts.format(ts_fc)

        with open(args.output, "w", encoding="utf8") as f:
            f.write(result)

        info("TypeScript declaration file saved to: {}", args.output)

    else:
        error(f"Action {args.action!r} not yet implemented!")
        return 1

    return 0


def main():
    import sys

    sys.exit(_main())
