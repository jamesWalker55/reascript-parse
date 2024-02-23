import itertools
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


def iter_nested_tag_text(tag: bs4.Tag):
    for child in tag.children:
        if isinstance(child, str):
            yield child
        else:
            yield from iter_nested_tag_text(child)  # type: ignore


def parse_function_call_text(prefix: str, tag: bs4.Tag):
    text = " ".join(iter_nested_tag_text(tag))
    text = text.strip()

    if not text.startswith(prefix):
        raise AssertionError(
            f"expected function text to begin with {prefix!r}: {text!r}"
        )

    return text[len(prefix) :].strip()


class MalformedDocsException(Exception):
    pass


def parse_sections(soup: bs4.BeautifulSoup):
    """Given the root element of a ReaScript API documentation page, parse each section into FunctionCallSection and GenericSection"""

    if soup.body is None:
        raise MalformedDocsException("<body> element is missing from documentation")

    for section, children in split_sections(
        soup.body.children, is_section_header_element
    ):
        section: bs4.Tag | None
        children: Iterable[bs4.Tag | str]

        section_name: str | None
        if section is None:
            section_name = None
        else:
            section_name = section.attrs["name"]

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
                    c_func = parse_function_call_text("C:", child)
                    continue
                elif "e_func" in classes:
                    e_func = parse_function_call_text("EEL2:", child)
                    continue
                elif "l_func" in classes:
                    l_func = parse_function_call_text("Lua:", child)
                    continue
                elif "p_func" in classes:
                    p_func = parse_function_call_text("Python:", child)
                    continue

            description_parts.append(child.text)

        description = "\n".join(description_parts).strip()
        if len(description) == 0:
            description = None

        if c_func is None and e_func is None and l_func is None and p_func is None:
            yield GenericSection(
                section_name,
                description,
            )
        else:
            yield FunctionCallSection(
                section_name,
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
    from .parse_lua import FunctionCall

    with open("src/rs_parse/REAPER API functions.html", "r", encoding="utf8") as f:
        sections = parse(f)

    result: list[str] = []

    for section in sections:
        if section.l_func is not None:
            try:
                fc = FunctionCall.parse(section.l_func)
                result.append(str(fc))
            except Exception as e:
                result.append(f"# {e}")

    with open("temp.txt", "w", encoding="utf8") as f:
        for line in result:
            print(line, file=f)


if __name__ == "__main__":
    main()
