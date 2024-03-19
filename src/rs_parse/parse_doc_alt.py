import re
import textwrap
from typing import Literal, NamedTuple, TextIO

import bs4

from rs_parse.parse_doc import (
    FunctionCallSection,
    _iter_nested_tag_text,
    _parse_function_call_text,
)


class RawSection(NamedTuple):
    name: str
    text: str

    @classmethod
    def parse(cls, f: TextIO) -> list["RawSection"]:
        text = f.read()

        sections: list[RawSection] = []

        prev_span_end = 0
        prev_contents = None
        prev_section_name = None

        for x in re.finditer(r'<a name="([^"]*?)">', text):
            section_name = x.group(1)
            prev_contents = text[prev_span_end : x.start()]

            # ignore text before the first section in the docs
            if prev_section_name is not None:
                sections.append(RawSection(prev_section_name, prev_contents))

            prev_section_name = section_name
            prev_span_end = x.end()

        prev_contents = text[prev_span_end:]
        if prev_section_name is not None:
            sections.append(RawSection(prev_section_name, prev_contents))

        return sections


IGNORED_SECTIONS = {
    "eel_list",
    "lua_list",
    "python_list",
    "function_list",
}


def pop_from_soup(soup: bs4.BeautifulSoup, search):
    result = []
    for element in soup.find_all(search):
        # remove element
        result.append(element.extract())
    return result


MULTILANG_CLASSES = {"c_func", "e_func", "l_func", "p_func"}


def parse_multilang_soup(name: str, soup: bs4.BeautifulSoup):
    def is_multilang_definition(tag: bs4.Tag):
        if tag.name.lower() != "div":
            return False

        if "class" not in tag.attrs:
            return False

        classes: list[str] = tag.attrs["class"]  # type: ignore
        if len(MULTILANG_CLASSES & set(classes)) == 0:
            return False

        return True

    multilang_definitions: list[bs4.Tag] = pop_from_soup(soup, is_multilang_definition)

    c_func: str | None = None
    e_func: str | None = None
    l_func: str | None = None
    p_func: str | None = None

    for tag in multilang_definitions:
        classes: list[str] = tag.attrs["class"]  # type: ignore
        classname = [c for c in classes if c in MULTILANG_CLASSES][0]

        if classname == "c_func":
            assert (
                c_func is None
            ), f"multiple declarations for the same language in section {name!r}"
            c_func = _parse_function_call_text("C:", tag)
        elif classname == "e_func":
            assert (
                e_func is None
            ), f"multiple declarations for the same language in section {name!r}"
            e_func = _parse_function_call_text("EEL2:", tag)
        elif classname == "l_func":
            assert (
                l_func is None
            ), f"multiple declarations for the same language in section {name!r}"
            l_func = _parse_function_call_text("Lua:", tag)
        elif classname == "p_func":
            assert (
                p_func is None
            ), f"multiple declarations for the same language in section {name!r}"
            p_func = _parse_function_call_text("Python:", tag)
        else:
            raise NotImplementedError(f"unknown classname {classname}")

    description = soup.text.strip()
    # add extra newline between each line
    description = description.replace("\n", "\n\n")
    if not description:
        description = None

    if c_func is None and e_func is None and l_func is None and p_func is None:
        raise ValueError("failed to find function definition in multilang section")

    return FunctionCallSection(name, c_func, e_func, l_func, p_func, description)


def remove_elements_before(ptr: bs4.Tag):
    """remove everything that occur before the pointer"""

    parent = ptr.parent
    while parent is not None:
        # remove each child up to the pointer
        for child in list(parent.children):
            if child == ptr:
                break
            child.extract()
        else:
            # we never reached the pointer, something has gone horribly wrong
            # this should never be reached (unless my logic is wrong)
            assert False

        # navigate to 1 level up
        ptr = parent
        parent = ptr.parent


def parse_singlelang_soup(
    name: str,
    soup: bs4.BeautifulSoup,
    lang: Literal["lua", "eel", "python"],
):
    func = soup.find("code")
    if func is None:
        raise ValueError("failed to find function definition in singlelang section")
    if not isinstance(func, bs4.Tag):
        # we searched for <code> tags, this should always be true
        assert False

    # # remove everything that occur before the function definition
    # ptr = func
    # parent = ptr.parent
    # while parent is not None:
    #     # remove each child up to the pointer
    #     for child in list(parent.children):
    #         if child == ptr:
    #             break
    #         child.extract()
    #     else:
    #         # we never reached the pointer, something has gone horribly wrong
    #         # this should never be reached (unless my logic is wrong)
    #         assert False

    #     # navigate to 1 level up
    #     ptr = parent
    #     parent = ptr.parent

    # remove everything that occur before the function definition
    remove_elements_before(func)
    # finally, remove the function definition itself from the tree
    func.extract()

    func_text = _parse_function_call_text("", func)

    # now, the tree is left with nothing but the description (hopefully)
    description = soup.text.strip()
    # add extra newline between each line
    description = description.replace("\n", "\n\n")
    if not description:
        description = None

    # print(func_text)
    # if description:
    #     print(textwrap.indent(description, "  "))

    c_func: str | None = None
    e_func: str | None = None
    l_func: str | None = None
    p_func: str | None = None

    if lang == "eel":
        e_func = func_text
    elif lang == "lua":
        l_func = func_text
    elif lang == "python":
        p_func = func_text
    else:
        raise NotImplementedError(f"unsupported language {lang!r}")

    return FunctionCallSection(name, c_func, e_func, l_func, p_func, description)


def parse(f: TextIO):
    raw_sections = RawSection.parse(f)

    for section in raw_sections:
        if section.name in IGNORED_SECTIONS:
            continue

        if section.name.startswith("eel_"):
            single_language = "eel"
        elif section.name.startswith("lua_"):
            single_language = "lua"
        elif section.name.startswith("python_"):
            single_language = "python"
        else:
            single_language = None

        soup = bs4.BeautifulSoup(section.text, "html.parser")

        # remove <h2> headers
        pop_from_soup(soup, "h2")

        # indented_soup = textwrap.indent(str(soup), "  ")
        # # if len(indented_soup.splitlines()) > 7:
        # if single_language:
        #     print(f"=={single_language} {section.name}")
        # else:
        #     print(section.name)
        # print(indented_soup)

        if single_language:
            fc = parse_singlelang_soup(section.name, soup, single_language)
        else:
            fc = parse_multilang_soup(section.name, soup)

        print(section.name)
        if fc.description:
            print(textwrap.indent(fc.description, "  "))
