import itertools
import json
import textwrap
from pprint import pformat
from typing import Iterable, NamedTuple, TextIO

import bs4


def is_section_header_element(x: "str | bs4.element.Tag"):
    return (
        not isinstance(x, str)
        and x.name.lower() == "a"
        and "name" in x.attrs
        and "href" not in x.attrs
    )


def split_sections(it, section_predicate):
    """Iterate through pairs of (section element, children elements)"""

    current_section = None
    for is_section, children in itertools.groupby(it, section_predicate):
        if is_section:
            assert current_section is None

            # yield all children except the last one
            # the last one is assigned to current_section
            prev_child = None
            for child in children:
                if prev_child is not None:
                    yield prev_child, []
                prev_child = child

            current_section = child

            assert current_section is not None
        else:
            # for the first iteration, current_section will be None
            # assert current_section is not None

            yield current_section, children

            # clear current section since section is now over
            current_section = None

            assert current_section is None


class FunctionCallSection(NamedTuple):
    name: str | None
    c_func: str | None
    e_func: str | None
    l_func: str | None
    p_func: str | None
    description: str | None


class GenericSection(NamedTuple):
    name: str | None
    description: str | None


def clean_function_call_text(prefix: str, text: str):
    if not text.startswith(prefix):
        raise AssertionError(
            f"expected function text to begin with {prefix!r}: {text!r}"
        )

    return text[len(prefix) :].strip()


def parse_sections(soup: bs4.BeautifulSoup):
    """Given the root element of a ReaScript API documentation page, parse each section into FunctionCallSection and GenericSection"""

    for section, children in split_sections(
        soup.body.children, is_section_header_element
    ):
        section: bs4.Tag | None
        children: Iterable[bs4.Tag | str]

        c_func: str | None = None
        e_func: str | None = None
        l_func: str | None = None
        p_func: str | None = None
        description_parts: list[str] = []

        for child in children:
            if isinstance(child, str):
                description_parts.append(child)
                continue

            tagname = child.name.upper()

            if tagname == "DIV" and "class" in child.attrs:
                classes: list[str] = child.attrs["class"]  # type: ignore
                if "c_func" in classes:
                    c_func = clean_function_call_text("C:", child.text)
                    continue
                elif "e_func" in classes:
                    e_func = clean_function_call_text("EEL2:", child.text)
                    continue
                elif "l_func" in classes:
                    l_func = clean_function_call_text("Lua:", child.text)
                    continue
                elif "p_func" in classes:
                    p_func = clean_function_call_text("Python:", child.text)
                    continue

            description_parts.append(child.text)

        description = "\n".join(description_parts).strip()
        if len(description) == 0:
            description = None

        if c_func is None and e_func is None and l_func is None and p_func is None:
            yield GenericSection(
                None if section is None else section.attrs["name"],
                description,
            )
        else:
            yield FunctionCallSection(
                None if section is None else section.attrs["name"],
                c_func,
                e_func,
                l_func,
                p_func,
                description,
            )


def parse(f: TextIO):
    soup = bs4.BeautifulSoup(f.read(), "html.parser")

    result: list[FunctionCallSection] = []

    for section in parse_sections(soup):
        if isinstance(section, GenericSection):
            # only allow 2 generic sections, all other sections are expected to be function call sections
            assert section.name in (None, "function_list")
            continue

        result.append(section)

    return result


def main():
    with open("src/rs_parse/REAPER API functions.html", "r", encoding="utf8") as f:
        result = parse(f)

    for section in result:
        if section.l_func is None:
            print(section.name)


if __name__ == "__main__":
    main()
