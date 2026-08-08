"""Screen 1: Library / Load - workbook functions 1 and 2."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..services import LyriConcService, ServiceError
from .widgets import confirm, error, fill_table, info, make_table, selected_id, warn

DOC_COLUMNS = [
    "title",
    "performers",
    "lyricists",
    "album",
    "genre",
    "language",
    "release_year",
    "word_count",
    "file_name",
]
DOC_HEADERS = [
    "Title",
    "Performers",
    "Lyricists",
    "Album",
    "Genre",
    "Language",
    "Year",
    "Words",
    "File",
]


class LibraryScreen(QWidget):
    """Load a corpus folder and edit metadata for the selected song."""

    corpus_changed = Signal()

    def __init__(self, service: LyriConcService) -> None:
        super().__init__()
        self.service = service
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        loader_row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Select a folder containing .txt lyric files")
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_folder)
        load = QPushButton("Load folder")
        load.clicked.connect(self._load_folder)
        reset = QPushButton("Reset DB")
        reset.clicked.connect(self._reset_db)
        loader_row.addWidget(QLabel("Corpus folder:"))
        loader_row.addWidget(self.folder_edit, 1)
        loader_row.addWidget(browse)
        loader_row.addWidget(load)
        loader_row.addWidget(reset)
        layout.addLayout(loader_row)

        self.table = make_table(DOC_HEADERS)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self.table, 3)

        editor = QGroupBox("Metadata editor (function 2)")
        form = QFormLayout(editor)
        self.title_edit = QLineEdit()
        self.performers_edit = QLineEdit()
        self.performers_edit.setPlaceholderText("Separated by ; ")
        self.lyricists_edit = QLineEdit()
        self.lyricists_edit.setPlaceholderText("Separated by ; ")
        self.composers_edit = QLineEdit()
        self.composers_edit.setPlaceholderText("Separated by ; ")
        self.album_edit = QLineEdit()
        self.album_year_edit = QSpinBox()
        self.album_year_edit.setRange(0, 9999)
        self.album_year_edit.setSpecialValueText(" ")
        self.genre_edit = QComboBox()
        self.genre_edit.setEditable(True)
        self.language_edit = QLineEdit()
        self.year_edit = QSpinBox()
        self.year_edit.setRange(0, 9999)
        self.year_edit.setSpecialValueText(" ")
        form.addRow("Title", self.title_edit)
        form.addRow("Performers", self.performers_edit)
        form.addRow("Lyricists", self.lyricists_edit)
        form.addRow("Composers", self.composers_edit)
        form.addRow("Album", self.album_edit)
        form.addRow("Album year", self.album_year_edit)
        form.addRow("Genre", self.genre_edit)
        form.addRow("Language", self.language_edit)
        form.addRow("Release year", self.year_edit)

        buttons = QHBoxLayout()
        save = QPushButton("Save metadata")
        save.clicked.connect(self._save_metadata)
        delete = QPushButton("Delete song")
        delete.clicked.connect(self._delete_document)
        buttons.addStretch(1)
        buttons.addWidget(save)
        buttons.addWidget(delete)
        form.addRow(buttons)
        layout.addWidget(editor, 2)

    def refresh(self) -> None:
        self.documents = self.service.list_documents()
        fill_table(self.table, self.documents, DOC_COLUMNS, id_column="document_id")
        genres = self.service.list_genres()
        current = self.genre_edit.currentText()
        self.genre_edit.blockSignals(True)
        self.genre_edit.clear()
        self.genre_edit.addItem("")
        self.genre_edit.addItems(genres)
        self.genre_edit.setCurrentText(current)
        self.genre_edit.blockSignals(False)

    def _browse_folder(self) -> None:
        start = self.folder_edit.text() or str(Path.cwd())
        folder = QFileDialog.getExistingDirectory(self, "Select corpus folder", start)
        if folder:
            self.folder_edit.setText(folder)

    def _load_folder(self) -> None:
        folder = self.folder_edit.text().strip()
        if not folder:
            warn(self, "Load folder", "Choose a folder first.")
            return
        try:
            result = self.service.load_folder(folder)
        except ServiceError as exc:
            error(self, "Load failed", str(exc))
            return
        loaded = len(result["loaded"])
        failed = result["failed"]
        message = f"Loaded {loaded} file(s)."
        if failed:
            message += "\n\nFailed:\n" + "\n".join(f"- {n}: {e}" for n, e in failed)
        info(self, "Load folder", message)
        self.refresh()
        self.corpus_changed.emit()

    def _reset_db(self) -> None:
        if not confirm(self, "Reset DB", "This deletes every loaded song. Continue?"):
            return
        self.service.reset_db()
        self.refresh()
        self.corpus_changed.emit()

    def _current_document(self) -> dict | None:
        document_id = selected_id(self.table)
        if document_id is None:
            return None
        for row in self.documents:
            if row["document_id"] == document_id:
                return row
        return None

    def _on_row_selected(self) -> None:
        row = self._current_document()
        if row is None:
            return
        self.title_edit.setText(row.get("title") or "")
        self.performers_edit.setText(row.get("performers") or "")
        self.lyricists_edit.setText(row.get("lyricists") or "")
        self.composers_edit.setText(row.get("composers") or "")
        self.album_edit.setText(row.get("album") or "")
        self.album_year_edit.setValue(0)
        self.genre_edit.setCurrentText(row.get("genre") or "")
        self.language_edit.setText(row.get("language") or "English")
        self.year_edit.setValue(int(row.get("release_year") or 0))

    def _save_metadata(self) -> None:
        row = self._current_document()
        if row is None:
            warn(self, "Save metadata", "Select a song first.")
            return

        def as_list(text: str) -> list[str]:
            return [p.strip() for p in text.split(";") if p.strip()]

        metadata = {
            "title": self.title_edit.text().strip(),
            "performers": as_list(self.performers_edit.text()),
            "lyricists": as_list(self.lyricists_edit.text()),
            "composers": as_list(self.composers_edit.text()),
            "album": self.album_edit.text().strip() or None,
            "album_year": self.album_year_edit.value() or None,
            "genre": self.genre_edit.currentText().strip() or None,
            "language": self.language_edit.text().strip() or "English",
            "release_year": self.year_edit.value() or None,
        }
        try:
            self.service.update_document_metadata(row["document_id"], metadata)
        except ServiceError as exc:
            error(self, "Save metadata", str(exc))
            return
        info(self, "Metadata saved", f"Updated '{metadata['title']}'.")
        self.refresh()
        self.corpus_changed.emit()

    def _delete_document(self) -> None:
        row = self._current_document()
        if row is None:
            return
        if not confirm(
            self, "Delete song", f"Remove '{row['title']}' from the index?"
        ):
            return
        self.service.delete_document(row["document_id"])
        self.refresh()
        self.corpus_changed.emit()
