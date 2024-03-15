from collections.abc import Generator
from typing import Iterable, Literal, NamedTuple, TextIO

import bs4


def _get_text_if_is_section(x: "str | bs4.PageElement"):
    """
    Check if an element is a section. Return its name if it is indeed a section.
    The conditions for a section is:
    - tag is '<a>', and
    - has a 'name="..."' attribute, and
    - has no 'href="..."' attribute
    """

    if not isinstance(x, bs4.Tag):
        return None

    if x.name.lower() == "a" and "name" in x.attrs and "href" not in x.attrs:
        return x.attrs["name"]

    return None


class RawSection(NamedTuple):
    """
    A raw, unprocessed section obtained from split_sections(), this should be further
    processed before using directly.
    """

    header: str | None
    children: list[bs4.Tag | str]


def split_sections(it: Iterable[bs4.PageElement | str]):
    """
    Given an iterable of elements, split it by 'section headers'. This expects the
    sequence to be like this:

    ```plain
    Text
    Text
    Section Header
    Function Call Definition
    Text
    Section Header
    Function Call Definition
    Text
    Section Header
    Function Call Definition
    Text
    Text
    ```

    A 'section header' is determined by the '_get_text_if_is_section' function.
    """

    current_section: RawSection = RawSection(None, [])

    for child in it:
        if isinstance(child, str):
            current_section.children.append(child)
            continue

        if not isinstance(child, bs4.Tag):
            raise NotImplementedError("what the fuck is this")

        new_section_name = _get_text_if_is_section(child)
        if new_section_name is None:
            current_section.children.append(child)
            continue

        yield current_section
        current_section = RawSection(new_section_name, [])

    yield current_section


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


Section = FunctionCallSection | GenericSection


def _iter_nested_tag_text(tag: bs4.Tag):
    """Iterate through all text within the given element"""

    for child in tag.children:
        if isinstance(child, str):
            yield child
        else:
            yield from _iter_nested_tag_text(child)  # type: ignore


def parse_function_call_text(prefix: str, tag: bs4.Tag) -> str:
    """
    Given an element and its prefix text, extract the function call text from it.
    An element is like this:
    ```html
    <div class="l_func">
        <span class='all_view'>Lua:</span>
        <code>
            <i>MediaItem</i> reaper.AddMediaItemToTrack(<i>MediaTrack</i> tr)
        </code>
        <br>
        <br>
    </div>
    ```
    """

    text = " ".join(_iter_nested_tag_text(tag))
    text = text.strip()

    if not text.startswith(prefix):
        raise AssertionError(
            f"expected function text to begin with {prefix!r}: {text!r}"
        )

    return text[len(prefix) :].strip()


class MalformedDocsException(Exception):
    pass


def preprocess_body(it: Iterable[bs4.PageElement | str]):
    """
    Preprocess the body to remove useless elements, extract some data, etc.
    This is needed because the original body is a fucking mess.

    This function is generally hard-coded and will likely break if REAPER devs ever
    decide to change the documentation format.
    """

    children = list(it)

    # handle the special '*_funcs' blocks at the end of documentation that contain
    # even more function calls in them

    # find the index of the first '*_funcs' <div> element
    funcs_idx = None
    for i, child in enumerate(children):
        if isinstance(child, str):
            continue

        if not isinstance(child, bs4.Tag):
            raise NotImplementedError("what the fuck is this")

        if "class" not in child.attrs:
            continue

        classes: list[str] = child.attrs["class"]  # type: ignore
        if "c_funcs" in classes:
            funcs_idx = i
            break
        elif "e_funcs" in classes:
            funcs_idx = i
            break
        elif "l_funcs" in classes:
            funcs_idx = i
            break
        elif "p_funcs" in classes:
            funcs_idx = i
            break

    if funcs_idx is None:
        return children, []

    return children[:funcs_idx], children[funcs_idx:]


def parse_sections(
    children: Iterable[bs4.PageElement | str],
) -> Generator[Section, None, None]:
    """
    Given the children of a ReaScript API documentation page's body, grouop and
    parse each section into FunctionCallSection and GenericSection sections.
    """

    for section_name, children in split_sections(children):
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


def parse_single_language_sections(
    language: Literal["lua", "c", "eel", "python"],
    it: Iterable[bs4.PageElement | str],
) -> Generator[Section, None, None]:
    """
    Given the children of a sub-section, e.g. 'e_funcs', group and parse each section
    into FunctionCallSection and GenericSection sections.
    """

    for section_name, children in split_sections(it):
        description_parts: list[str] = []

        # find index of first <code> element
        code_idx = None
        for i, child in enumerate(children):
            if isinstance(child, str):
                continue

            if not isinstance(child, bs4.Tag):
                raise NotImplementedError("what the fuck is this")

            if child.name.lower() != "code":
                continue

            code_idx = i
            break

        if code_idx is not None:
            code_element = children.pop(code_idx)
            if not isinstance(code_element, bs4.Tag):
                raise NotImplementedError("what the fuck is this")

            functioncall_text = parse_function_call_text("", code_element)
        else:
            functioncall_text = None

        for child in children:
            if isinstance(child, str):
                description_parts.append(child)
                continue

            description_parts.append(child.text)

        description = "\n".join(description_parts).strip()
        if len(description) == 0:
            description = None

        if functioncall_text is None:
            yield GenericSection(
                section_name,
                description,
            )
        else:
            c_func: str | None = None
            e_func: str | None = None
            l_func: str | None = None
            p_func: str | None = None

            if language == "c":
                c_func = functioncall_text
            elif language == "eel":
                e_func = functioncall_text
            elif language == "lua":
                l_func = functioncall_text
            elif language == "python":
                p_func = functioncall_text
            else:
                raise NotImplementedError(f"language not implemented: {language}")

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

    if soup.body is None:
        raise MalformedDocsException("<body> element is missing from documentation")

    children, extras = preprocess_body(soup.body.children)
    # children: the main children of the documentation, can be parsed into
    #   FunctionCalls and GenericSections
    # extras: contains special 'e_funcs', 'l_funcs' elements, they also contain
    #   FunctionCalls, but nested inside an element

    result: list[FunctionCallSection] = []

    for section in parse_sections(children):
        print(repr(section)[:100])

        if isinstance(section, GenericSection):
            # only allow 2 generic sections, all other sections are expected to be function call sections
            assert section.name in (
                None,
                "function_list",
            ), f"unsupported section: {section.name}"
            continue

        result.append(section)

    for child in extras:
        if isinstance(child, str):
            continue

        if not isinstance(child, bs4.Tag):
            raise NotImplementedError("what the fuck is this")

        if "class" not in child.attrs:
            continue

        classes: list[str] = child.attrs["class"]  # type: ignore
        classes = [x for x in classes if x.endswith("_funcs")]
        is_funcs_block = len(classes) > 0
        if not is_funcs_block:
            continue

        if classes[0] == "c_funcs":
            language = "c"
        elif classes[0] == "e_funcs":
            language = "eel"
        elif classes[0] == "l_funcs":
            language = "lua"
        elif classes[0] == "p_funcs":
            language = "python"
        else:
            raise NotImplementedError(f"language not implemented: {language}")

        for section in parse_single_language_sections(language, child.children):
            if isinstance(section, FunctionCallSection):
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

    # with open("temp.txt", "w", encoding="utf8") as f:
    #     for line in result:
    #         print(line, file=f)


if __name__ == "__main__":
    main()
