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

    functioncalls: list[to_emmy.AnnotatedFunctionCall] = []
    for section in sections:
        if section.l_func is None:
            continue

        try:
            fc = parse_lua.FunctionCall.parse(section.l_func)
            fc = to_emmy.AnnotatedFunctionCall.from_section(fc, section)
            functioncalls.append(fc)
            if fc.function_call.namespace == "reaper":
                continue

            print(fc)

            fc_str = fc.format()
            print(fc_str)

        except parse_lua.ParseError as e:
            print("#", e)

    print(to_emmy.format(functioncalls))

    # return parse_doc.main()
    # return "Hello from rs-parse!"
