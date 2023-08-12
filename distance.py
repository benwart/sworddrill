from functools import lru_cache
from sqlite3 import connect, Connection
from verse import Verse


@lru_cache(maxsize=1)
def max_distance_text() -> int:
    conn = connect("bible.db")
    resp = conn.execute(
        """
        SELECT sum(k.len)
        FROM kjv AS k;
        """
    )
    distance = resp.fetchone()[0]
    conn.close()
    return distance


@lru_cache(maxsize=1)
def max_distance_books() -> int:
    conn = connect("bible.db")
    resp = conn.execute(
        """
        SELECT count(*)
        FROM book_info AS bi;
        """
    )
    distance = resp.fetchone()[0]
    conn.close()
    return distance


def max_distance_chapters(conn: Connection, book: str) -> int:
    resp = conn.execute(
        """
        SELECT bi.chapters
        FROM book_info AS bi
        WHERE bi.title_short = ?;
        """,
        (book,),
    )
    distance = resp.fetchone()[0]
    return distance


def max_distance_verses(conn: Connection, book: str, chapter: int) -> int:
    resp = conn.execute(
        """
        SELECT max(k.verse) AS max
        FROM kjv AS k
          LEFT JOIN book_info AS bi ON bi.`order` = k.book
        WHERE bi.title_short = ?
          AND k.chapter = ?;
        """,
        (
            book,
            chapter,
        ),
    )
    distance = resp.fetchone().max
    return distance


def row_ids(conn: Connection, answer: Verse, guess: Verse):
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
            answer["book"],
            answer["chapter"],
            answer["verse"],
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
            guess["book"],
            guess["chapter"],
            guess["verse"],
        ),
    )

    answer_id = answer_resp.fetchone().id
    guess_id = guess_resp.fetchone().id

    return answer_id, guess_id


def len_between(conn: Connection, answer_id: int, guess_id: int) -> int:
    if answer_id == guess_id:
        return 0

    low_id = min(answer_id, guess_id)
    high_id = max(answer_id, guess_id)

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
    value = resp.fetchone().delta
    return value if value else 0


def percent_between(conn: Connection, answer_id: int, guess_id: int):
    total = max_distance_text()
    delta = len_between(conn, answer_id, guess_id)

    return (delta / total) * 10**2, "lower" if guess_id <= answer_id else "higher"


def distance_between_books(conn: Connection, answer_id: int, guess_id: int):
    total_books = max_distance_books()

    if answer_id == guess_id:
        return {"percent": 0.0, "count": 0, "unit": "books"}

    low_id = min(answer_id, guess_id)
    high_id = max(answer_id, guess_id)

    resp = conn.execute(
        """
        SELECT count(*) AS count
          FROM (
            SELECT DISTINCT k.book
              FROM kjv AS k
             WHERE id >= ?
               AND id < ?
          );
        """,
        (
            low_id,
            high_id,
        ),
    )

    books = resp.fetchone().count

    if books <= 1:
        # if the answer and guess are in the same book, then the distance is 0
        books = 0
    else:
        # remove the answer book from the count
        books -= 1

    return {"percent": (books / total_books) * 10**2, "count": books, "unit": "books"}


def distance_between_chapters(conn: Connection, answer_id: int, guess_id: int, book: str):
    total_chapters = max_distance_chapters(conn, book)

    if answer_id == guess_id:
        return {"percent": 0.0, "count": 0, "unit": "chapters"}

    low_id = min(answer_id, guess_id)
    high_id = max(answer_id, guess_id)

    resp = conn.execute(
        """
        SELECT count(*) AS count
          FROM (
            SELECT DISTINCT k.book, k.chapter
              FROM kjv AS k
             WHERE id >= ?
               AND id < ?
          );
        """,
        (
            low_id,
            high_id,
        ),
    )

    chapters = resp.fetchone().count

    if chapters <= 1:
        # if the answer and guess are in the same chapter, then the distance is 0
        chapters = 0
    else:
        chapters -= 1

    return {"percent": (chapters / total_chapters) * 10**2, "count": chapters, "unit": "chapters"}


def distance_between_verses(conn: Connection, answer_id: int, guess_id: int, book: str, chapter: int):
    total_verses = max_distance_verses(conn, book, chapter)

    if answer_id == guess_id:
        return {"percent": 0.0, "count": 0, "unit": "verses"}

    low_id = min(answer_id, guess_id)
    high_id = max(answer_id, guess_id)

    resp = conn.execute(
        """
        SELECT count(*) AS count
          FROM (
            SELECT DISTINCT k.book, k.chapter, k.verse
              FROM kjv AS k
             WHERE id >= ?
               AND id < ?
          );
        """,
        (
            low_id,
            high_id,
        ),
    )

    verses = resp.fetchone().count

    return {"percent": (verses / total_verses) * 10**2, "count": verses, "unit": "verses"}
