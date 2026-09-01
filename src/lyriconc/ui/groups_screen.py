"""Screen 4: Groups, phrases and export - functions 8, 9 and 10."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..services import LyriConcService, ServiceError
from .widgets import confirm, error, fill_table, info, make_table, selected_id, warn

GROUP_COLUMNS = ["name", "word_count", "description"]
GROUP_HEADERS = ["Group", "Words", "Description"]

WORD_COLUMNS = ["normalized_token", "frequency"]
WORD_HEADERS = ["Word", "Frequency"]

PHRASE_COLUMNS = ["name", "tokens"]
PHRASE_HEADERS = ["Phrase name", "Tokens"]

PHRASE_HIT_COLUMNS = ["title", "first_line", "last_line", "length"]
PHRASE_HIT_HEADERS = ["Song", "First line", "Last line", "Length"]


class GroupsScreen(QWidget):
    """Manage word groups, phrases and the group-index export."""

    groups_changed = Signal()

    def __init__(self, service: LyriConcService) -> None:
        super().__init__()
        self.service = service
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        split = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(split, 1)

        groups_box = QGroupBox("Word groups (function 8)")
        gl = QVBoxLayout(groups_box)
        actions = QHBoxLayout()
        new_group = QPushButton("New group")
        new_group.clicked.connect(self._new_group)
        del_group = QPushButton("Delete group")
        del_group.clicked.connect(self._delete_group)
        actions.addWidget(new_group)
        actions.addWidget(del_group)
        actions.addStretch(1)
        gl.addLayout(actions)

        self.group_table = make_table(GROUP_HEADERS)
        self.group_table.itemSelectionChanged.connect(self._load_group_words)
        gl.addWidget(self.group_table, 1)

        member_row = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Type a word...")
        add_btn = QPushButton("Add word")
        add_btn.clicked.connect(self._add_word)
        rm_btn = QPushButton("Remove selected")
        rm_btn.clicked.connect(self._remove_word)
        member_row.addWidget(self.word_input, 1)
        member_row.addWidget(add_btn)
        member_row.addWidget(rm_btn)
        gl.addLayout(member_row)

        self.word_table = make_table(WORD_HEADERS)
        gl.addWidget(self.word_table, 1)

        export_row = QHBoxLayout()
        export_row.addWidget(QLabel("Export group index (function 10):"))
        export_txt = QPushButton("Export as .txt")
        export_txt.clicked.connect(lambda: self._export_group("txt"))
        export_csv = QPushButton("Export as .csv")
        export_csv.clicked.connect(lambda: self._export_group("csv"))
        export_row.addStretch(1)
        export_row.addWidget(export_txt)
        export_row.addWidget(export_csv)
        gl.addLayout(export_row)

        split.addWidget(groups_box)

        phrases_box = QGroupBox("Linguistic expressions / phrases (function 9)")
        pl = QVBoxLayout(phrases_box)
        phrase_actions = QHBoxLayout()
        new_phrase = QPushButton("New phrase")
        new_phrase.clicked.connect(self._new_phrase)
        del_phrase = QPushButton("Delete phrase")
        del_phrase.clicked.connect(self._delete_phrase)
        search_phrase = QPushButton("Search selected phrase")
        search_phrase.clicked.connect(self._search_phrase)
        phrase_actions.addWidget(new_phrase)
        phrase_actions.addWidget(del_phrase)
        phrase_actions.addWidget(search_phrase)
        phrase_actions.addStretch(1)
        pl.addLayout(phrase_actions)

        self.phrase_table = make_table(PHRASE_HEADERS)
        pl.addWidget(self.phrase_table, 1)

        pl.addWidget(QLabel("Ad-hoc phrase search:"))
        ad_hoc = QHBoxLayout()
        self.adhoc_input = QLineEdit()
        self.adhoc_input.setPlaceholderText("Type a phrase, e.g. 'amazing grace'")
        search_ad = QPushButton("Search")
        search_ad.clicked.connect(self._search_adhoc)
        ad_hoc.addWidget(self.adhoc_input, 1)
        ad_hoc.addWidget(search_ad)
        pl.addLayout(ad_hoc)

        self.phrase_hits = make_table(PHRASE_HIT_HEADERS)
        pl.addWidget(self.phrase_hits, 1)

        split.addWidget(phrases_box)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)

    def refresh(self) -> None:
        fill_table(
            self.group_table,
            self.service.list_groups(),
            GROUP_COLUMNS,
            id_column="group_id",
        )
        fill_table(
            self.phrase_table,
            self.service.list_phrases(),
            PHRASE_COLUMNS,
            id_column="phrase_id",
        )
        self._load_group_words()

    def _current_group_id(self) -> int | None:
        return selected_id(self.group_table)

    def _load_group_words(self) -> None:
        group_id = self._current_group_id()
        if group_id is None:
            fill_table(self.word_table, [], WORD_COLUMNS)
            return
        rows = self.service.list_group_words(group_id)
        fill_table(self.word_table, rows, WORD_COLUMNS, id_column="word_id")

    def _new_group(self) -> None:
        name, ok = QInputDialog.getText(self, "New group", "Group name:")
        if not ok or not name.strip():
            return
        try:
            self.service.create_group(name.strip())
        except ServiceError as exc:
            error(self, "New group", str(exc))
            return
        self.refresh()
        self.groups_changed.emit()

    def _delete_group(self) -> None:
        group_id = self._current_group_id()
        if group_id is None:
            return
        if not confirm(self, "Delete group", "Delete the selected group?"):
            return
        self.service.delete_group(group_id)
        self.refresh()
        self.groups_changed.emit()

    def _add_word(self) -> None:
        group_id = self._current_group_id()
        if group_id is None:
            warn(self, "Add word", "Select a group first.")
            return
        token = self.word_input.text().strip()
        if not token:
            return
        try:
            added = self.service.add_word_to_group(group_id, token)
        except ServiceError as exc:
            error(self, "Add word", str(exc))
            return
        if not added:
            warn(self, "Add word", f"'{token}' is not in the corpus.")
        self.word_input.clear()
        self._load_group_words()
        self.refresh_groups_only()
        if added:
            self.groups_changed.emit()

    def refresh_groups_only(self) -> None:
        rows = self.service.list_groups()
        current = self._current_group_id()
        fill_table(self.group_table, rows, GROUP_COLUMNS, id_column="group_id")
        if current is not None:
            for row in range(self.group_table.rowCount()):
                item = self.group_table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == current:
                    self.group_table.selectRow(row)
                    break

    def _remove_word(self) -> None:
        group_id = self._current_group_id()
        if group_id is None:
            return
        row = self.word_table.currentRow()
        if row < 0:
            return
        token_item = self.word_table.item(row, 0)
        if token_item is None:
            return
        self.service.remove_word_from_group(group_id, token_item.text())
        self._load_group_words()
        self.refresh_groups_only()
        self.groups_changed.emit()

    def _export_group(self, fmt: str) -> None:
        group_id = self._current_group_id()
        if group_id is None:
            warn(self, "Export", "Select a group first.")
            return
        default = f"group_index.{fmt}"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export group index", default, f"{fmt.upper()} files (*.{fmt})"
        )
        if not path:
            return
        try:
            output = self.service.export_group_index(group_id, path, format=fmt)
        except ServiceError as exc:
            error(self, "Export", str(exc))
            return
        info(self, "Export", f"Saved: {output}")

    def _new_phrase(self) -> None:
        name, ok = QInputDialog.getText(self, "New phrase", "Phrase name:")
        if not ok or not name.strip():
            return
        tokens, ok = QInputDialog.getText(
            self, "New phrase", "Phrase words (space separated):"
        )
        if not ok or not tokens.strip():
            return
        try:
            self.service.create_phrase(name.strip(), tokens)
        except ServiceError as exc:
            error(self, "New phrase", str(exc))
            return
        self.refresh()

    def _delete_phrase(self) -> None:
        phrase_id = selected_id(self.phrase_table)
        if phrase_id is None:
            return
        if not confirm(self, "Delete phrase", "Delete the selected phrase?"):
            return
        self.service.delete_phrase(phrase_id)
        self.refresh()

    def _search_phrase(self) -> None:
        phrase_id = selected_id(self.phrase_table)
        if phrase_id is None:
            warn(self, "Search phrase", "Select a phrase first.")
            return
        results = self.service.search_phrase_by_id(phrase_id)
        fill_table(self.phrase_hits, results, PHRASE_HIT_COLUMNS)
        if not results:
            info(self, "Search phrase", "No matches found.")

    def _search_adhoc(self) -> None:
        text = self.adhoc_input.text().strip()
        if not text:
            return
        try:
            results = self.service.search_phrase(text)
        except ServiceError as exc:
            error(self, "Search phrase", str(exc))
            return
        fill_table(self.phrase_hits, results, PHRASE_HIT_COLUMNS)
        if not results:
            info(self, "Search phrase", "No matches found.")
