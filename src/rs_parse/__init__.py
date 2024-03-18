from argparse import ArgumentParser

from . import parse_doc, parse_lua, to_emmy


def parse_args():
    parser = ArgumentParser()

    parser.add_argument("input")

    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.input, "r", encoding="utf8") as f:
        sections = parse_doc.parse(f)

    functioncalls: list[
        tuple[parse_doc.FunctionCallSection, parse_lua.FunctionCall]
    ] = []
    for section in sections:
        if section.l_func is None:
            continue

        try:
            fc = parse_lua.FunctionCall.parse(section.l_func)
            functioncalls.append((section, fc))
            if fc.namespace == "reaper":
                continue

            print(fc)

            deprecated = (
                "deprecated" in section.description.lower()
                if section.description
                else False
            )
            fc_str = to_emmy._function_call(
                fc, section.description, deprecated=deprecated
            )
            print(fc_str)

        except parse_lua.ParseError as e:
            print("#", e)

    print(to_emmy.format(functioncalls))

    # return parse_doc.main()
    # return "Hello from rs-parse!"
