"""Screen 3: Word index and position lookup - functions 6 and 7."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..services import LyriConcService, ServiceError
from .widgets import error, fill_table, info, make_table

INDEX_COLUMNS = [
    "normalized_token",
    "title",
    "stanza_no",
    "line_in_stanza",
    "global_line_no",
    "word_position",
    "word_seq_in_doc",
]
INDEX_HEADERS = [
    "Word",
    "Song",
    "Stanza",
    "Line",
    "Global line",
    "Word position",
    "Doc word seq",
]


class IndexScreen(QWidget):
    """Word index with two position types plus reverse lookup form."""

    def __init__(self, service: LyriConcService) -> None:
        super().__init__()
        self.service = service
        self._documents: list[dict] = []
        self._groups: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        filters = QGroupBox("Word index (function 6)")
        row = QHBoxLayout(filters)
        row.addWidget(QLabel("Document:"))
        self.doc_combo = QComboBox()
        self.doc_combo.currentIndexChanged.connect(self._reload_index)
        row.addWidget(self.doc_combo, 1)
        row.addWidget(QLabel("Group:"))
        self.group_combo = QComboBox()
        self.group_combo.currentIndexChanged.connect(self._reload_index)
        row.addWidget(self.group_combo, 1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._reload_index)
        row.addWidget(refresh)
        layout.addWidget(filters)

        self.table = make_table(INDEX_HEADERS)
        layout.addWidget(self.table, 3)

        lookup = QGroupBox("Locate word by position (function 7)")
        grid = QGridLayout(lookup)
        grid.addWidget(QLabel("Document:"), 0, 0)
        self.lookup_doc = QComboBox()
        grid.addWidget(self.lookup_doc, 0, 1)
        grid.addWidget(QLabel("Stanza:"), 0, 2)
        self.stanza = QSpinBox()
        self.stanza.setRange(1, 999)
        grid.addWidget(self.stanza, 0, 3)
        grid.addWidget(QLabel("Line in stanza:"), 1, 0)
        self.line = QSpinBox()
        self.line.setRange(1, 999)
        grid.addWidget(self.line, 1, 1)
        grid.addWidget(QLabel("Word position:"), 1, 2)
        self.offset = QSpinBox()
        self.offset.setRange(1, 999)
        grid.addWidget(self.offset, 1, 3)
        find = QPushButton("Find word")
        find.clicked.connect(self._locate_word)
        grid.addWidget(find, 2, 3)
        self.result_label = QLabel("(no lookup yet)")
        self.result_label.setStyleSheet("font-weight: bold;")
        grid.addWidget(self.result_label, 2, 0, 1, 3)
        layout.addWidget(lookup)

    def refresh(self) -> None:
        self._documents = self.service.list_documents()
        self._groups = self.service.list_groups()

        for combo in (self.doc_combo, self.lookup_doc):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("(all documents)", None)
            for row in self._documents:
                combo.addItem(row["title"], row["document_id"])
            combo.blockSignals(False)

        self.group_combo.blockSignals(True)
        self.group_combo.clear()
        self.group_combo.addItem("(no group filter)", None)
        for row in self._groups:
            self.group_combo.addItem(row["name"], row["group_id"])
        self.group_combo.blockSignals(False)

        self._reload_index()

    def _reload_index(self) -> None:
        document_id = self.doc_combo.currentData()
        group_id = self.group_combo.currentData()
        rows = self.service.get_word_index(document_id, group_id)
        for row in rows:
            row["word_seq_in_doc"] += 1
        fill_table(self.table, rows[:1000], INDEX_COLUMNS)

    def _locate_word(self) -> None:
        document_id = self.lookup_doc.currentData()
        if document_id is None:
            self.result_label.setText("Choose a specific document.")
            return
        try:
            found = self.service.locate_word(
                document_id=document_id,
                stanza_no=self.stanza.value(),
                line_in_stanza=self.line.value(),
                word_offset=self.offset.value(),
            )
        except ServiceError as exc:
            error(self, "Lookup", str(exc))
            return
        if found is None:
            self.result_label.setText("No word at that position.")
            return
        self.result_label.setText(
            f"Found: '{found['normalized_token']}' in "
            f"'{found['title']}' (global line {found['global_line_no']}, "
            f"doc word seq {found['word_seq_in_doc'] + 1})"
        )
