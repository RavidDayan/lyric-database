"""Screen 2: Search, word list, and context viewer - functions 3, 4, 5, and 9."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..services import LyriConcService, ServiceError
from .widgets import error, fill_table, info, make_table, selected_id, warn

DOC_COLUMNS = ["title", "genre", "language", "release_year"]
DOC_HEADERS = ["Title", "Genre", "Language", "Year"]

WORD_COLUMNS = ["normalized_token", "frequency", "document_count"]
WORD_HEADERS = ["Word", "Frequency", "Documents"]

OCC_COLUMNS = [
    "title",
    "stanza_no",
    "line_in_stanza",
    "global_line_no",
    "word_position",
]
OCC_HEADERS = ["Song", "Stanza", "Line in stanza", "Global line", "Word position"]


class SearchScreen(QWidget):
    """Search by metadata or by word, browse the word list, view context."""

    groups_changed = Signal()

    def __init__(self, service: LyriConcService) -> None:
        super().__init__()
        self.service = service
        self._current_context: dict | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        meta = QGroupBox("Metadata search (function 3)")
        grid = QGridLayout(meta)
        self.title_search = QLineEdit()
        self.artist_search = QLineEdit()
        self.genre_combo = QComboBox()
        self.language_edit = QLineEdit()
        self.year_from = QSpinBox()
        self.year_from.setRange(0, 9999)
        self.year_from.setSpecialValueText(" ")
        self.year_to = QSpinBox()
        self.year_to.setRange(0, 9999)
        self.year_to.setSpecialValueText(" ")
        grid.addWidget(QLabel("Title contains"), 0, 0)
        grid.addWidget(self.title_search, 0, 1)
        grid.addWidget(QLabel("Artist contains"), 0, 2)
        grid.addWidget(self.artist_search, 0, 3)
        grid.addWidget(QLabel("Genre"), 1, 0)
        grid.addWidget(self.genre_combo, 1, 1)
        grid.addWidget(QLabel("Language"), 1, 2)
        grid.addWidget(self.language_edit, 1, 3)
        grid.addWidget(QLabel("Year from"), 2, 0)
        grid.addWidget(self.year_from, 2, 1)
        grid.addWidget(QLabel("Year to"), 2, 2)
        grid.addWidget(self.year_to, 2, 3)
        search_btn = QPushButton("Search songs")
        search_btn.clicked.connect(self._search_documents)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_filters)
        grid.addWidget(search_btn, 3, 3)
        grid.addWidget(clear_btn, 3, 2)
        outer.addWidget(meta)

        split = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(split, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Songs"))
        self.doc_table = make_table(DOC_HEADERS)
        self.doc_table.itemSelectionChanged.connect(self._update_word_scope)
        left_layout.addWidget(self.doc_table, 1)

        word_box = QGroupBox("Word list / word search (functions 4 + word search)")
        word_layout = QVBoxLayout(word_box)
        row = QHBoxLayout()
        self.word_query = QLineEdit()
        self.word_query.setPlaceholderText("Type a word to search or filter")
        find_word_btn = QPushButton("Find word")
        find_word_btn.clicked.connect(self._search_by_word)
        show_list_btn = QPushButton("Show word list")
        show_list_btn.clicked.connect(self._show_word_list)
        row.addWidget(self.word_query, 1)
        row.addWidget(find_word_btn)
        row.addWidget(show_list_btn)
        word_layout.addLayout(row)
        self.word_table = make_table(WORD_HEADERS)
        self.word_table.itemSelectionChanged.connect(self._load_occurrences)
        word_layout.addWidget(self.word_table, 1)

        group_row = QHBoxLayout()
        group_row.addWidget(QLabel("Add selected word to group:"))
        self.group_combo = QComboBox()
        self.group_combo.setMinimumWidth(160)
        group_row.addWidget(self.group_combo, 1)
        add_group_btn = QPushButton("Add")
        add_group_btn.clicked.connect(self._add_selected_to_group)
        new_group_btn = QPushButton("New group...")
        new_group_btn.clicked.connect(self._create_group)
        group_row.addWidget(add_group_btn)
        group_row.addWidget(new_group_btn)
        word_layout.addLayout(group_row)

        left_layout.addWidget(word_box, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Occurrences"))
        self.occ_table = make_table(OCC_HEADERS)
        self.occ_table.itemSelectionChanged.connect(self._load_context)
        right_layout.addWidget(self.occ_table, 1)

        ctx_box = QGroupBox("Context (function 5)")
        ctx_layout = QVBoxLayout(ctx_box)
        self.context_view = QTextEdit()
        self.context_view.setReadOnly(True)
        ctx_layout.addWidget(self.context_view, 1)
        mark_row = QHBoxLayout()
        mark_row.addWidget(QLabel("Marked phrase length:"))
        self.mark_len = QSpinBox()
        self.mark_len.setRange(1, 20)
        self.mark_len.setValue(2)
        mark_row.addWidget(self.mark_len)
        mark_btn = QPushButton("Search phrase from selected word")
        mark_btn.clicked.connect(self._search_marked_phrase)
        mark_row.addWidget(mark_btn)
        mark_row.addStretch(1)
        ctx_layout.addLayout(mark_row)
        right_layout.addWidget(ctx_box, 2)

        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 4)

    def refresh(self) -> None:
        self.genre_combo.blockSignals(True)
        self.genre_combo.clear()
        self.genre_combo.addItem("")
        self.genre_combo.addItems(self.service.list_genres())
        self.genre_combo.blockSignals(False)
        self._refresh_group_combo()
        self._search_documents()
        self._show_word_list()

    def _refresh_group_combo(self) -> None:
        current = self.group_combo.currentData()
        self.group_combo.blockSignals(True)
        self.group_combo.clear()
        for group in self.service.list_groups():
            self.group_combo.addItem(group["name"], group["group_id"])
        if current is not None:
            index = self.group_combo.findData(current)
            if index >= 0:
                self.group_combo.setCurrentIndex(index)
        self.group_combo.blockSignals(False)

    def _clear_filters(self) -> None:
        self.title_search.clear()
        self.artist_search.clear()
        self.genre_combo.setCurrentIndex(0)
        self.language_edit.clear()
        self.year_from.setValue(0)
        self.year_to.setValue(0)
        self._search_documents()

    def _search_documents(self) -> None:
        filters = {
            "title": self.title_search.text().strip() or None,
            "artist": self.artist_search.text().strip() or None,
            "genre": self.genre_combo.currentText().strip() or None,
            "language": self.language_edit.text().strip() or None,
            "year_from": self.year_from.value() or None,
            "year_to": self.year_to.value() or None,
        }
        rows = self.service.search_documents(filters)
        fill_table(self.doc_table, rows, DOC_COLUMNS, id_column="document_id")

    def _selected_document_ids(self) -> list[int]:
        ids: list[int] = []
        for item in self.doc_table.selectedItems():
            if item.column() != 0:
                continue
            value = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(value, int):
                ids.append(value)
        return ids

    def _update_word_scope(self) -> None:
        self._show_word_list()

    def _show_word_list(self) -> None:
        ids = self._selected_document_ids() or None
        rows = self.service.get_word_list(ids)
        query = self.word_query.text().strip().lower()
        if query:
            rows = [r for r in rows if query in r["normalized_token"]]
        fill_table(self.word_table, rows[:500], WORD_COLUMNS, id_column="word_id")

    def _search_by_word(self) -> None:
        token = self.word_query.text().strip()
        if not token:
            self._show_word_list()
            return
        docs = self.service.search_by_word(token)
        if not docs:
            info(self, "Word search", f"No occurrences for '{token}'.")
            fill_table(self.doc_table, [], DOC_COLUMNS, id_column="document_id")
            return
        fill_table(self.doc_table, docs, DOC_COLUMNS, id_column="document_id")
        self._show_word_list()

    def _load_occurrences(self) -> None:
        word_id = selected_id(self.word_table)
        if word_id is None:
            return
        ids = self._selected_document_ids()
        document_id = ids[0] if len(ids) == 1 else None
        rows = self.service.get_occurrences(word_id, document_id)
        fill_table(self.occ_table, rows, OCC_COLUMNS, id_column="occurrence_id")
        if rows:
            self.occ_table.selectRow(0)

    def _load_context(self) -> None:
        occ_id = selected_id(self.occ_table)
        if occ_id is None:
            self.context_view.clear()
            self._current_context = None
            return
        try:
            context = self.service.get_context(occ_id, before=4, after=4)
        except ServiceError as exc:
            error(self, "Context", str(exc))
            return
        self._current_context = context
        self._render_context(context)

    def _render_context(self, context: dict) -> None:
        self.context_view.clear()
        cursor = self.context_view.textCursor()
        highlight = QTextCharFormat()
        highlight.setFontWeight(700)
        highlight.setBackground(Qt.GlobalColor.yellow)
        plain = QTextCharFormat()
        header = f"{context['title']}  (stanza {context['stanza_no']}, line {context['line_in_stanza']})\n\n"
        cursor.insertText(header, plain)
        for line in context["lines"]:
            if line["is_match"]:
                text = line["text"]
                start = context["match_char_start"]
                end = context["match_char_end"]
                cursor.insertText(text[:start], plain)
                cursor.insertText(text[start:end] or context["token"], highlight)
                cursor.insertText(text[end:] + "\n", plain)
            else:
                cursor.insertText(line["text"] + "\n", plain)

    def _search_marked_phrase(self) -> None:
        if self._current_context is None:
            warn(self, "Marked phrase", "Load a context first.")
            return
        length = self.mark_len.value()
        ctx = self._current_context
        try:
            results = self.service.search_marked_phrase(
                document_id=ctx["document_id"],
                start_word_seq=ctx["word_seq_in_doc"],
                length=length,
            )
        except ServiceError as exc:
            error(self, "Marked phrase", str(exc))
            return
        if not results:
            info(self, "Marked phrase", "The marked phrase has no other occurrences.")
            return
        summary = "\n".join(
            f"- {row['title']} (line {row['first_line']})" for row in results[:20]
        )
        info(
            self,
            "Marked phrase",
            f"Phrase '{results[0]['phrase']}' found in {len(results)} place(s):\n{summary}",
        )

    def _add_selected_to_group(self) -> None:
        word_id = selected_id(self.word_table)
        if word_id is None:
            warn(self, "Add to group", "Select a word in the word list first.")
            return
        group_id = self.group_combo.currentData()
        if group_id is None:
            warn(self, "Add to group", "Create or select a group first.")
            return
        try:
            self.service.add_word_id_to_group(group_id, word_id)
        except ServiceError as exc:
            error(self, "Add to group", str(exc))
            return
        info(
            self,
            "Add to group",
            f"Added '{self.word_table.item(self.word_table.currentRow(), 0).text()}' "
            f"to '{self.group_combo.currentText()}'.",
        )
        self.groups_changed.emit()

    def _create_group(self) -> None:
        name, ok = QInputDialog.getText(self, "New group", "Group name:")
        if not ok or not name.strip():
            return
        try:
            self.service.create_group(name.strip())
        except ServiceError as exc:
            error(self, "New group", str(exc))
            return
        self._refresh_group_combo()
        index = self.group_combo.findText(name.strip())
        if index >= 0:
            self.group_combo.setCurrentIndex(index)
        self.groups_changed.emit()
