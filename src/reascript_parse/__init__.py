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

    parser.add_argument("input")
    parser.add_argument("output")

    return parser.parse_args()


def main():
    args = parse_args()

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
