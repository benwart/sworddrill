from verse import Verse, VerseWithText
from typing import List
from sys import version_info

if version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from typing_extensions import TypedDict


class DistanceScoped(TypedDict):  # type: ignore
    percent: float
    count: int
    unit: str


class Guess(Verse):
    icon: str
    percent: float
    book_found: bool
    chapter_found: bool
    verse_found: bool
    distance_away_books: DistanceScoped
    distance_away_chapters: DistanceScoped
    distance_away_verses: DistanceScoped


def guess_done(guess: Guess):
    return guess["book_found"] and guess["chapter_found"] and guess["verse_found"]


class ControlState(TypedDict):  # type: ignore
    enabled: bool


class ControlNumber(ControlState):
    max: int


class State(TypedDict):  # type: ignore
    version: int
    answer: VerseWithText
    answer_pre_context: List[VerseWithText]
    answer_post_context: List[VerseWithText]
    guesses: List[Guess]
    current: Verse
    guess: ControlState
    book: ControlState
    chapter: ControlNumber
    verse: ControlNumber
    context_count: int
    total_guesses: int
    guesses_remaining: int
    distance_method: int
    search_categories: List[int]
