from sys import version_info

if version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from typing_extensions import TypedDict


class Verse(TypedDict):  # type: ignore
    book: str
    chapter: int
    verse: int


class VerseWithText(Verse):
    text: str


def verse_eq(a: Verse, b: Verse) -> bool:
    checks = [
        a["book"] == b["book"],
        a["chapter"] == b["chapter"],
        a["verse"] == b["verse"],
    ]

    return all(checks)
