from argparse import ArgumentParser

from . import parse_doc_alt, parse_lua, to_emmy


def info(fmt: str, *args):
    print("[INFO] {}".format(fmt.format(*args)))


def warn(fmt: str, *args):
    print("[WARN] {}".format(fmt.format(*args)))


def error(fmt: str, *args):
    print("[ERROR] {}".format(fmt.format(*args)))


def parse_args():
    parser = ArgumentParser()

    subparsers = parser.add_subparsers()

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

    return parser.parse_args()


def _main() -> int:
    args = parse_args()

    if args.action != "to-lua":
        error(f"Action {args.action!r} not yet implemented!")
        return 1

    with open(args.input, "r", encoding="utf8") as f:
        sections = parse_doc_alt.parse(f)

    functioncalls: list[to_emmy.AnnotatedFunctionCall] = []
    for section in sections:
        if section.l_func is None:
            info("Skipping section with no Lua function definition {!r}", section.name)
            continue

        try:
            fc = parse_lua.FunctionCall.parse(section.l_func)
            afc = to_emmy.AnnotatedFunctionCall.from_section(fc, section)
            functioncalls.append(afc)
        except parse_lua.ParseError as e:
            warn(
                "Skipping malformed Lua function in section {!r} - {}", section.name, e
            )

    emmy: str = to_emmy.format(functioncalls)

    with open(args.output, "w", encoding="utf8") as f:
        f.write(emmy)

    info("Lua declaration file saved to: {}", args.output)

    return 0


def main():
    import sys

    sys.exit(_main())
