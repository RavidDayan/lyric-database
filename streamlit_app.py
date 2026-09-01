"""Public, read-only Streamlit interface for LyriConc."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from lyriconc import config
from lyriconc.services import LyriConcService, ServiceError


st.set_page_config(page_title="LyriConc", page_icon="L", layout="wide")


@st.cache_resource
def initialize_database() -> Path:
    """Create the local database and load the bundled corpus once."""
    config.ensure_directories()
    service = LyriConcService()
    try:
        if not service.list_documents():
            result = service.load_folder(config.CORPUS_DIR)
            if result["failed"]:
                failures = ", ".join(name for name, _ in result["failed"])
                raise RuntimeError(f"Could not load: {failures}")
        return service.db_path
    finally:
        service.close()


def document_label(document: dict) -> str:
    year = f" ({document['release_year']})" if document["release_year"] else ""
    return f"{document['title']}{year}"


def show_corpus(service: LyriConcService, documents: list[dict]) -> None:
    st.subheader("Song corpus")
    st.caption(f"{len(documents)} songs available")
    st.dataframe(
        [
            {
                "Title": row["title"],
                "Performer": row["performers"] or "",
                "Genre": row["genre"] or "",
                "Year": row["release_year"],
                "Words": row["word_count"],
            }
            for row in documents
        ],
        hide_index=True,
        width="stretch",
    )

    selected = st.selectbox(
        "Read a song",
        documents,
        format_func=document_label,
        key="corpus_document",
    )
    if selected:
        details = st.columns(3)
        details[0].metric("Words", selected["word_count"])
        details[1].write(f"**Performer:** {selected['performers'] or 'Unknown'}")
        details[2].write(f"**Genre:** {selected['genre'] or 'Unknown'}")
        with st.expander("Show lyrics"):
            st.text(service.get_full_text(selected["document_id"]))


def show_search(service: LyriConcService) -> None:
    st.subheader("Word search")
    with st.form("word_search"):
        word = st.text_input("Enter a word", placeholder="grace")
        submitted = st.form_submit_button("Search", type="primary")

    if submitted:
        st.session_state.search_word = word

    search_word = st.session_state.get("search_word", "")
    if not search_word:
        return

    matches = service.search_by_word(search_word)
    if not matches:
        st.info(f'No matches found for "{search_word}".')
        return

    st.dataframe(
        [
            {
                "Song": row["title"],
                "Genre": row["genre"] or "",
                "Year": row["release_year"],
                "Occurrences": row["occurrence_count"],
            }
            for row in matches
        ],
        hide_index=True,
        width="stretch",
    )

    selected_song = st.selectbox(
        "Choose a song",
        matches,
        format_func=lambda row: f"{row['title']} ({row['occurrence_count']} matches)",
        key="search_document",
    )
    word_id = service.get_word_id(search_word)
    if not selected_song or word_id is None:
        return

    occurrences = service.get_occurrences(word_id, selected_song["document_id"])
    selected_occurrence = st.selectbox(
        "Choose an occurrence",
        occurrences,
        format_func=lambda row: (
            f"Stanza {row['stanza_no']}, line {row['line_in_stanza']}, "
            f"word {row['word_position']}"
        ),
        key="search_occurrence",
    )
    if selected_occurrence:
        context = service.get_context(selected_occurrence["occurrence_id"])
        st.markdown(f"**Context from {context['title']}**")
        for line in context["lines"]:
            if line["is_match"]:
                st.markdown(f"**{line['text']}**")
            else:
                st.write(line["text"] or " ")


def show_statistics(service: LyriConcService) -> None:
    st.subheader("Corpus statistics")
    level = st.selectbox(
        "View",
        ("document", "word_frequency", "stanza", "line"),
        format_func=lambda value: value.replace("_", " ").title(),
    )
    rows = service.get_statistics(level)
    st.dataframe(rows, hide_index=True, width="stretch")


st.title("LyriConc")
st.caption("Explore words and patterns in a small collection of song lyrics.")

try:
    database_path = initialize_database()
    service = LyriConcService(database_path)
    try:
        documents = service.list_documents()
        corpus_tab, search_tab, statistics_tab = st.tabs(
            ("Corpus", "Search", "Statistics")
        )
        with corpus_tab:
            show_corpus(service, documents)
        with search_tab:
            show_search(service)
        with statistics_tab:
            show_statistics(service)
    finally:
        service.close()
except (RuntimeError, ServiceError, OSError) as error:
    st.error(f"LyriConc could not start: {error}")