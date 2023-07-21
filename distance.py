#!/usr/bin/env python

from dataclasses import dataclass
from functools import lru_cache
from sqlite3 import connect, Connection


@dataclass(slots=True)
class Verse:
    book: str
    chapter: str
    verse: str


@lru_cache(maxsize=1)
def max_distance(conn: Connection) -> int:
    resp = conn.execute(
        """
        SELECT sum(k.len) AS total
        FROM kjv AS k;
        """
    )
    return resp.fetchone()[0]


def row_ids(conn: Connection, answer: Verse, guess: Verse) -> tuple[int, int]:
    answer_resp = conn.execute(
        """
        /* answer */
        SELECT k.id AS id
          FROM kjv AS k
            LEFT JOIN book_info AS bi ON bi.`order` = k.book
         WHERE bi.title_short = ?
           AND k.chapter = ?
           AND k.verse = ?
        """,
        (
            answer.book,
            answer.chapter,
            answer.verse,
        ),
    )
    guess_resp = conn.execute(
        """
        /* guess */
        SELECT k.id AS id
          FROM kjv AS k
            LEFT JOIN book_info AS bi ON bi.`order` = k.book
         WHERE bi.title_short = ?
           AND k.chapter = ?
           AND k.verse = ?;
        """,
        (
            guess.book,
            guess.chapter,
            guess.verse,
        ),
    )

    return answer_resp.fetchone()[0], guess_resp.fetchone()[0]


def len_between(conn: Connection, answer_id: int, guess_id: Verse) -> int:
    low_id = min(answer_id, guess_id)
    high_id = max(answer_id, guess_id)

    if low_id == high_id:
        return 0

    resp = conn.execute(
        """
        SELECT sum(len) as delta
          FROM kjv
         WHERE id > ?
           AND id < ?;
        """,
        (
            low_id,
            high_id,
        ),
    )
    value = resp.fetchone()[0]
    return value if value else 0


def percent_between(answer: Verse, guess: Verse) -> float:
    conn = connect("bible-sqlite.db")
    total = max_distance(conn)
    answer_id, guess_id = row_ids(conn, answer, guess)
    delta = len_between(conn, answer_id, guess_id)
    conn.close()

    return (delta / total) * 10**2


def books():
    conn = connect("bible-sqlite.db")
    resp = conn.execute(
        """
        SELECT DISTINCT bi.title_short
          FROM book_info AS bi
         ORDER BY bi.`order` ASC;
        """
    )
    book_list = [r[0] for r in resp.fetchall()]
    conn.close()

    return book_list


def chapters(book: str):
    conn = connect("bible-sqlite.db")
    resp = conn.execute(
        """
        SELECT DISTINCT k.chapter
          FROM kjv AS k
            LEFT JOIN book_info AS bi ON bi.`order` = k.book
         WHERE bi.title_short = ?
         ORDER BY k.chapter ASC;
        """,
        (book,),
    )
    chapter_list = [r[0] for r in resp.fetchall()]
    conn.close()

    return chapter_list


def verses(book: str, chapter: str):
    conn = connect("bible-sqlite.db")
    resp = conn.execute(
        """
        SELECT DISTINCT k.verse
          FROM kjv AS k
            LEFT JOIN book_info AS bi ON bi.`order` = k.book
         WHERE bi.title_short = ?
           AND k.chapter = ?
         ORDER BY k.verse ASC;
        """,
        (book, chapter),
    )
    verse_list = [r[0] for r in resp.fetchall()]
    conn.close()

    return verse_list


def main():
    answer = Verse("John", "3", "16")
    guess = Verse("Genesis", "3", "17")

    percent = percent_between(answer, guess)
    print(f"{percent}")

    print(books())
    print(chapters("John"))
    print(verses("John", "3"))


if __name__ == "__main__":
    main()
