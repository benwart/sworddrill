from nicegui import app, ui
from os import environ

from configuration import DistanceMethod, SearchCategory
from distance import (
    percent_between,
    row_ids,
    distance_between_books,
    distance_between_chapters,
    distance_between_verses,
)
from lookups import (
    get_connection,
    random_verse_from_category,
    context_verses,
    books,
    chapters,
    verses,
)
from state import State, Guess, guess_done
from verse import Verse


def default_state() -> State:
    conn = get_connection()
    categories = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    answer = random_verse_from_category(conn, categories)
    count = 1
    total_guesses = 7
    value = {
        "version": 12,
        "answer": answer,
        "answer_pre_context": context_verses(conn, answer, count, False),
        "answer_post_context": context_verses(conn, answer, count, True),
        "guesses": [],
        "guesses_remaining": total_guesses,
        "current": {"book": "Genesis", "chapter": 1, "verse": 1},
        "guess": {"enabled": True},
        "book": {"enabled": True},
        "chapter": {"max": 1, "enabled": True},
        "verse": {"max": 1, "enabled": True},
        "context_count": count,
        "total_guesses": total_guesses,
        "distance_method": DistanceMethod.ScopedPercentage.value,
        "search_categories": categories,
    }
    conn.close()

    return value  # type: ignore


def reset():
    app.storage.user["state"]["book"]["enabled"] = True
    app.storage.user["state"]["chapter"]["enabled"] = True
    app.storage.user["state"]["verse"]["enabled"] = True
    app.storage.user["state"]["guess"]["enabled"] = True

    app.storage.user["state"]["current"]["book"] = "Genesis"
    app.storage.user["state"]["current"]["chapter"] = 1
    app.storage.user["state"]["current"]["verse"] = 1

    conn = get_connection()
    answer = random_verse_from_category(conn, app.storage.user["state"]["search_categories"])
    app.storage.user["state"]["answer"] = answer
    app.storage.user["state"]["answer_pre_context"] = context_verses(
        conn, answer, app.storage.user["state"]["context_count"], False
    )
    app.storage.user["state"]["answer_post_context"] = context_verses(
        conn, answer, app.storage.user["state"]["context_count"], True
    )
    app.storage.user["state"]["guesses"] = []
    app.storage.user["state"]["guesses_remaining"] = app.storage.user["state"]["total_guesses"]
    conn.close()

    results_ui.refresh()
    verse_ui.refresh()


def distance_str_text_percent(guess: Guess) -> str:
    return f" ({guess['percent']:0.3f}% away)"


def distance_str_scoped_percent(guess: Guess) -> str:
    if not guess["book_found"]:
        return f" ({guess['distance_away_books']['percent']:.0f}% books away)"

    if not guess["chapter_found"]:
        return f" ({guess['distance_away_chapters']['percent']:.0f}% chapters in book away)"

    if not guess["verse_found"]:
        return f" ({guess['distance_away_verses']['percent']:.0f}% verses in chapter away)"

    return ""


def distance_str_scoped_count(guess: Guess) -> str:
    if not guess["book_found"]:
        return f" ({guess['distance_away_books']['count']:.0f} books away)"

    if not guess["chapter_found"]:
        return f" ({guess['distance_away_chapters']['count']:.0f} chapters in book away)"

    if not guess["verse_found"]:
        return f" ({guess['distance_away_verses']['count']:.0f} verses in chapter away)"

    return ""


distance_methods_to_str = {
    DistanceMethod.TextPercentage.value: distance_str_text_percent,
    DistanceMethod.ScopedPercentage.value: distance_str_scoped_percent,
    DistanceMethod.ScopedCount.value: distance_str_scoped_count,
}


@ui.refreshable
def results_ui():
    for index, guess in enumerate(reversed(app.storage.user["state"]["guesses"])):
        book_string = guess["book"]
        chapter_string = str(guess["chapter"])
        verse_string = str(guess["verse"])
        distance_string = ""

        if guess["book_found"]:
            book_string = f"<b>{book_string}</b>"

        if guess["chapter_found"]:
            chapter_string = f"<b>{chapter_string}</b>"

        if guess["verse_found"]:
            verse_string = f"<b>{verse_string}</b>"

        if not guess_done(guess):
            distance_method = distance_methods_to_str[app.storage.user["state"]["distance_method"]]
            distance_string = distance_method(guess)

        card = ui.card().classes("w-full min-w-max")
        with card:
            if index == 0:
                card.tailwind.background_color("neutral-200")

            row = ui.row()
            with row:
                if index > 0:
                    row.tailwind.text_color("neutral-500")

                ui.icon(guess["icon"]).classes("text-2xl")
                ui.html(f"{book_string} {chapter_string}:{verse_string}{distance_string}")


def add_guess():
    current = app.storage.user["state"]["current"]

    guess: Verse = {
        "book": current["book"],
        "chapter": current["chapter"],
        "verse": current["verse"],
    }  # type: ignore

    answer = app.storage.user["state"]["answer"]
    conn = get_connection()
    answer_id, guess_id = row_ids(conn, answer, guess)
    text_percent, direction = percent_between(conn, answer_id, guess_id)

    distance_away_books = distance_between_books(conn, answer_id, guess_id)
    distance_away_chapters = distance_between_chapters(conn, answer_id, guess_id, answer["book"])
    distance_away_verse = distance_between_verses(conn, answer_id, guess_id, answer["book"], answer["chapter"])
    conn.close()

    book_found = guess["book"] == answer["book"]
    chapter_found = guess["chapter"] == answer["chapter"]
    verse_found = guess["verse"] == answer["verse"]

    new_guess: Guess = {
        "book": guess["book"],
        "chapter": guess["chapter"],
        "verse": guess["verse"],
        "icon": "arrow_back" if direction == "higher" else "arrow_forward",
        "percent": text_percent,
        "distance_away_books": distance_away_books,
        "distance_away_chapters": distance_away_chapters,
        "distance_away_verses": distance_away_verse,
        "book_found": book_found,
        "chapter_found": book_found and chapter_found,
        "verse_found": book_found and chapter_found and verse_found,
    }  # type: ignore

    if guess_done(new_guess):
        new_guess["icon"] = "emoji_events"
        ui.notify("You Win!", type="positive")

    app.storage.user["state"]["guesses"].append(new_guess)
    app.storage.user["state"]["guesses_remaining"] = app.storage.user["state"]["total_guesses"] - len(
        app.storage.user["state"]["guesses"]
    )

    if len(app.storage.user["state"]["guesses"]) >= app.storage.user["state"]["total_guesses"]:
        app.storage.user["state"]["guess"]["enabled"] = False

        if not guess_done(new_guess):
            ui.notify(
                f"Try Again! The correct verse is {answer['book']} {answer['chapter']}:{answer['verse']}",
                type="warning",
                position="bottom",
            )

    app.storage.user["state"]["book"]["enabled"] = not new_guess["book_found"]
    app.storage.user["state"]["chapter"]["enabled"] = not new_guess["chapter_found"]
    app.storage.user["state"]["verse"]["enabled"] = not new_guess["verse_found"]

    results_ui.refresh()


@ui.refreshable
def verse_ui():
    with ui.column():
        for verse in app.storage.user["state"].get("answer_pre_context", []):
            ui.label(verse["text"])

        ui.label(app.storage.user["state"]["answer"]["text"]).tailwind.text_color("neutral-100").font_weight(
            "bold"
        ).font_size("lg")

        for verse in app.storage.user["state"].get("answer_post_context", []):
            ui.label(verse["text"])


def get_verse_max() -> int:
    current = app.storage.user["state"]["current"]
    verses_in_chapter = verses(current["book"], current["chapter"])
    max_verse = max(verses_in_chapter) if verses_in_chapter else 100
    return max_verse


def get_chapter_max() -> int:
    current = app.storage.user["state"]["current"]
    chapters_in_book = chapters(current["book"])
    max_chapter = max(chapters_in_book) if chapters_in_book else 100
    return max_chapter


def update_guess_form():
    guess_form.refresh()

    # check if we should update due to max values changing
    max_chapter = get_chapter_max()

    if (
        app.storage.user["state"]["current"]["chapter"] is None
        or app.storage.user["state"]["current"]["chapter"] > max_chapter
    ):
        app.storage.user["state"]["current"]["chapter"] = max_chapter
        guess_form.refresh()

    max_verse = get_verse_max()
    if (
        app.storage.user["state"]["current"]["verse"] is None
        or app.storage.user["state"]["current"]["verse"] > max_verse
    ):
        app.storage.user["state"]["current"]["verse"] = max_verse


@ui.refreshable
def guess_form():
    current = app.storage.user["state"]["current"]

    book = ui.select(options=books(), with_input=True, value=current["book"]).classes("w-40")
    chapter = ui.select(options=chapters(current["book"]), value=current["chapter"]).classes("w-16")
    verse = ui.select(options=verses(current["book"], current["chapter"]), value=current["verse"]).classes("w-16")

    # update style
    ui.query(".q-field__input").style("color: #fff")
    ui.query(".q-field__native").style("color: #fff")

    book.bind_enabled_from(app.storage.user["state"]["book"], "enabled")
    book.bind_value(app.storage.user["state"]["current"], "book")

    chapter.bind_enabled_from(app.storage.user["state"]["chapter"], "enabled")
    chapter.bind_value(app.storage.user["state"]["current"], "chapter")

    verse.bind_enabled_from(app.storage.user["state"]["verse"], "enabled")
    verse.bind_value(app.storage.user["state"]["current"], "verse")

    # setup updates
    book.on(
        "update:model-value",
        handler=update_guess_form,
    )
    chapter.on(
        "update:model-value",
        handler=update_guess_form,
    )
    verse.on(
        "update:model-value",
        handler=update_guess_form,
    )

    with ui.button("Guess", on_click=add_guess).bind_enabled_from(app.storage.user["state"]["guess"], "enabled"):
        ui.badge(color="red").props("floating").bind_text_from(app.storage.user["state"], "guesses_remaining")

    with ui.button(icon="replay", on_click=reset):
        ui.tooltip("Select a New Verse")


def distance_method_on_change():
    results_ui.refresh()


def categories_select_all():
    app.storage.user["state"]["search_categories"] = [c.value for c in SearchCategory]


def categories_clear():
    app.storage.user["state"]["search_categories"] = []


@ui.refreshable
def config_ui():
    with ui.expansion("General").classes("w-full"):
        ui.number(
            "Context Verses (+/-)",
            min=0,
            max=10,
            step=1,
            format="%.0f",
            value=app.storage.user["state"]["context_count"],
        ).classes("w-full").bind_value(
            app.storage.user["state"],
            "context_count",
        )

        ui.number(
            "Total Guesses",
            min=1,
            step=1,
            format="%.0f",
            value=app.storage.user["state"]["total_guesses"],
        ).classes("w-full").bind_value(
            app.storage.user["state"],
            "total_guesses",
        )

    with ui.expansion("Search Categories", icon="category").classes("w-full"):
        with ui.row():
            ui.button("Select All", on_click=categories_select_all)
            ui.button("Clear", on_click=categories_clear)

        ui.select(
            {option.value: option.name for option in SearchCategory},
            multiple=True,
        ).props("use-chips").bind_value(
            app.storage.user["state"],
            "search_categories",
        )

    with ui.expansion("Distance Method", icon="query_stats").classes("w-full"):
        ui.select([option.name for option in DistanceMethod], on_change=distance_method_on_change).bind_value(
            app.storage.user["state"],
            "distance_method",
            forward=lambda name: DistanceMethod[name].value,
            backward=lambda value: DistanceMethod(value).name,
        )


@ui.page("/game", title="Sword Drill Game")
def game_page():
    # load the state from storaged
    defaults = dict(default_state())

    # reset the user storage if the version is updated
    if app.storage.user.get("state", {}).get("version", 0) != defaults["version"]:
        app.storage.user["state"] = defaults

    try:
        state = app.storage.user.get(
            "state",
            defaults,
        )
        defaults.update(state)

        app.storage.user["state"] = defaults

    except Exception as e:
        print(e)
        app.storage.user["state"] = defaults

    with ui.header(elevated=True, fixed=True):
        with ui.column():
            with ui.row():
                ui.button(on_click=lambda: right_drawer.toggle(), icon="menu").props("flat color=white")
                ui.label("Sword Drill").tailwind.font_size("2xl").font_weight("extrabold")

            verse_ui()

            with ui.row():
                guess_form()

    with ui.right_drawer(fixed=False).style("background-color: #5898d4") as right_drawer:
        right_drawer.tailwind.text_color("white")
        with ui.column():
            ui.label("Configuration").tailwind.font_size("2xl").font_weight("bold")
            config_ui()

    with ui.column():
        results_ui()


@ui.page("/random-verse", title="Sword Drill Random Verse")
def random_verse_page():
    conn = get_connection()
    categories = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    verse = random_verse_from_category(conn, categories)
    conn.close()

    dark = ui.dark_mode()

    with ui.element("div").classes("grid place-items-center h-screen w-full") as container:
        container.on("click", handler=dark.toggle)
        ui.label(f"{verse['book']} {verse['chapter']}:{verse['verse']}").tailwind.font_size("8xl").font_weight(
            "extrabold"
        )


def main():
    ui.link("Game", game_page)
    ui.link("Random Verse", random_verse_page)
    ui.run(
        title="Sword Drill",
        favicon="🗡",
        storage_secret=environ.get("STORAGE_SECRET", "private key to secure the browser session cookie"),
    )


if __name__ in ["__main__", "__mp_main__"]:
    main()
