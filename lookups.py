from collections import namedtuple
from functools import lru_cache
from sqlite3 import connect, Connection, Cursor
from typing import List
from random import randint
from verse import Verse, VerseWithText


def namedtuple_factory(cursor: Cursor, row):
    fields = [column[0] for column in cursor.description]
    cls = namedtuple("NamedRow", fields)
    return cls._make(row)


def get_connection():
    conn = connect("bible.db")
    conn.row_factory = namedtuple_factory
    return conn


@lru_cache(maxsize=1)
def verse_count() -> int:
    conn = get_connection()
    resp = conn.execute(
        """
        SELECT max(k.id) AS count
          FROM kjv AS k;
        """
    )
    return resp.fetchone().count


def random_verse(conn: Connection) -> VerseWithText:
    max_verse = verse_count()
    r = randint(1, max_verse)

    resp = conn.execute(
        """
        SELECT bi.title_short AS book, k.chapter, k.verse, k.text
          FROM kjv AS k
            LEFT JOIN book_info AS bi ON bi.`order` = k.book
         WHERE k.id = ?;
        """,
        (r,),
    ).fetchone()

    verse: VerseWithText = {
        "book": resp.book,
        "chapter": resp.chapter,
        "verse": resp.verse,
        "text": resp.text,
    }  # type: ignore

    return verse


def random_verse_from_category(conn: Connection, categories: List[int]) -> VerseWithText:
    resp = conn.execute(
        f"""
        SELECT count(*) AS count
          FROM kjv AS k
            LEFT JOIN key_english AS ke ON ke.b = k.book
            LEFT JOIN book_info AS bi ON bi.`order` = k.book
         WHERE ke.g in ({','.join('?' * len(categories))})
        """,
        categories,
    ).fetchone()

    count = resp.count
    r = randint(0, count - 1)

    resp = conn.execute(
        f"""
        SELECT bi.title_short AS book, k.chapter, k.verse, k.text
          FROM kjv AS k
            LEFT JOIN key_english AS ke ON ke.b = k.book
            LEFT JOIN book_info AS bi ON bi.`order` = k.book
         WHERE ke.g in ({','.join('?' * len(categories))})
         LIMIT ?, 1
        """,
        categories + [r],
    ).fetchone()

    verse: VerseWithText = {
        "book": resp.book,
        "chapter": resp.chapter,
        "verse": resp.verse,
        "text": resp.text,
    }  # type: ignore

    return verse


def context_verses(conn: Connection, verse: Verse, count: int, after: bool) -> List[VerseWithText]:
    if count == 0:
        return []

    answer_id = conn.execute(
        f"""
        SELECT k.id
          FROM kjv AS k
            LEFT JOIN book_info AS bi ON bi.`order` = k.book
         WHERE bi.title_short = ?
           AND k.chapter = ? 
           AND k.verse = ? 
        """,
        (
            verse["book"],
            verse["chapter"],
            verse["verse"],
        ),
    ).fetchone()[0]

    context_records = conn.execute(
        f"""
        SELECT bi.title_short, k.chapter, k.verse, k.text
          FROM kjv AS k
            LEFT JOIN book_info AS bi ON bi.`order` = k.book
         WHERE k.id {'>' if after else '<'} ? 
          ORDER BY k.id {'ASC' if after else 'DESC'}
          LIMIT ?;
        """,
        (
            answer_id,
            count,
        ),
    ).fetchall()

    context_list = [{"book": r[0], "chapter": r[1], "verse": r[2], "text": r[3]} for r in context_records]

    # if len(context_list) == 0:
    #     pass

    return context_list  # type: ignore


@lru_cache(maxsize=1)
def books() -> List[str]:
    conn = get_connection()
    resp = conn.execute(
        """
        SELECT DISTINCT bi.title_short AS book
          FROM book_info AS bi
         ORDER BY bi.`order` ASC;
        """
    )
    book_list = [r.book for r in resp.fetchall()]
    conn.close()

    return book_list


@lru_cache(maxsize=None)
def chapters(book: str) -> List[int]:
    conn = get_connection()
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
    chapter_list = [r.chapter for r in resp.fetchall()]
    conn.close()

    return chapter_list


@lru_cache(maxsize=None)
def verses(book: str, chapter: str) -> List[int]:
    conn = get_connection()
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
    verse_list = [r.verse for r in resp.fetchall()]
    conn.close()

    return verse_list
