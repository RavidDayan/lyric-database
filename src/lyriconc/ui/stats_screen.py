"""Screen 5: Statistics and XML backup/restore - function 11 + additional topic."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import config
from ..services import LyriConcService, ServiceError
from .widgets import confirm, error, fill_table, info, make_table

LEVELS = {
    "Per line": "line",
    "Per stanza": "stanza",
    "Per document": "document",
    "Word frequency": "word_frequency",
}

STATS_COLUMNS = {
    "line": [
        "title",
        "stanza_no",
        "line_in_stanza",
        "global_line_no",
        "char_count",
        "word_count",
        "avg_word_chars",
    ],
    "stanza": [
        "title",
        "stanza_no",
        "line_count",
        "word_count",
        "char_count",
        "avg_words_per_line",
    ],
    "document": [
        "title",
        "stanza_count",
        "line_count",
        "word_count",
        "distinct_words",
        "char_count",
    ],
    "word_frequency": [
        "normalized_token",
        "frequency",
        "document_count",
        "char_count",
    ],
}
STATS_HEADERS = {
    "line": ["Song", "Stanza", "Line", "Global line", "Chars", "Words", "Chars/word"],
    "stanza": ["Song", "Stanza", "Lines", "Words", "Chars", "Words/line"],
    "document": ["Song", "Stanzas", "Lines", "Words", "Distinct words", "Chars"],
    "word_frequency": ["Word", "Frequency", "Docs", "Chars"],
}


class StatsScreen(QWidget):
    """Line/stanza/document/word-frequency statistics plus XML round-trip."""

    corpus_restored = Signal()

    def __init__(self, service: LyriConcService) -> None:
        super().__init__()
        self.service = service
        self._current_rows: list[dict] = []
        self._current_level = "line"
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        stats_box = QGroupBox("Statistics (function 11)")
        sl = QVBoxLayout(stats_box)
        row = QHBoxLayout()
        row.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(LEVELS.keys())
        self.level_combo.currentIndexChanged.connect(self._reload_stats)
        row.addWidget(self.level_combo)
        row.addWidget(QLabel("Document:"))
        self.doc_combo = QComboBox()
        self.doc_combo.currentIndexChanged.connect(self._reload_stats)
        row.addWidget(self.doc_combo, 1)
        export_btn = QPushButton("Export...")
        export_btn.clicked.connect(self._export_stats)
        row.addWidget(export_btn)
        sl.addLayout(row)

        self.table = make_table(["column"])
        sl.addWidget(self.table, 1)
        outer.addWidget(stats_box, 3)

        xml_box = QGroupBox("XML backup / restore (additional topic)")
        xl = QVBoxLayout(xml_box)
        xml_row = QHBoxLayout()
        export_xml = QPushButton("Export XML backup")
        export_xml.clicked.connect(self._export_xml)
        restore_xml = QPushButton("Restore from XML")
        restore_xml.clicked.connect(self._restore_xml)
        round_trip = QPushButton("Run round-trip + verify")
        round_trip.clicked.connect(self._round_trip)
        xml_row.addWidget(export_xml)
        xml_row.addWidget(restore_xml)
        xml_row.addWidget(round_trip)
        xml_row.addStretch(1)
        xl.addLayout(xml_row)

        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setFontFamily("Consolas")
        xl.addWidget(self.report_view, 1)
        outer.addWidget(xml_box, 2)

    def refresh(self) -> None:
        docs = self.service.list_documents()
        self.doc_combo.blockSignals(True)
        self.doc_combo.clear()
        self.doc_combo.addItem("(all documents)", None)
        for row in docs:
            self.doc_combo.addItem(row["title"], row["document_id"])
        self.doc_combo.blockSignals(False)
        self._reload_stats()

    def _reload_stats(self) -> None:
        label = self.level_combo.currentText()
        level = LEVELS[label]
        headers = STATS_HEADERS[level]
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        try:
            rows = self.service.get_statistics(level, self.doc_combo.currentData())
        except ServiceError as exc:
            error(self, "Statistics", str(exc))
            return
        self._current_rows = rows
        self._current_level = level
        fill_table(self.table, rows[:1000], STATS_COLUMNS[level])

    def _export_stats(self) -> None:
        if not self._current_rows:
            info(self, "Export", "No rows to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export statistics",
            f"stats_{self._current_level}.csv",
            "CSV files (*.csv);;Text files (*.txt)",
        )
        if not path:
            return
        self.service.export_rows(
            self._current_rows,
            path,
            title=f"LyriConc statistics ({self._current_level})",
        )
        info(self, "Export", f"Saved: {path}")

    def _default_xml_path(self) -> Path:
        config.ensure_directories()
        return config.EXPORT_DIR / "lyriconc_backup.xml"

    def _export_xml(self) -> None:
        default = str(self._default_xml_path())
        path, _ = QFileDialog.getSaveFileName(
            self, "Export XML backup", default, "XML files (*.xml)"
        )
        if not path:
            return
        try:
            output = self.service.export_database_xml(path)
        except ServiceError as exc:
            error(self, "XML export", str(exc))
            return
        info(self, "XML export", f"Saved: {output}")

    def _restore_xml(self) -> None:
        default = str(self._default_xml_path())
        path, _ = QFileDialog.getOpenFileName(
            self, "Restore XML backup", default, "XML files (*.xml)"
        )
        if not path:
            return
        if not confirm(
            self,
            "Restore XML",
            "The current database will be dropped and rebuilt from the XML file. Continue?",
        ):
            return
        before = self.service.verify_database_counts()
        try:
            self.service.restore_database_xml(path)
        except Exception as exc:
            error(self, "Restore XML", str(exc))
            return
        after = self.service.verify_database_counts()
        from ..xml_backup import build_verification_report

        report = build_verification_report(before, after, path)
        self.report_view.setPlainText(report)
        self.refresh()
        self.corpus_restored.emit()

    def _round_trip(self) -> None:
        default = str(self._default_xml_path())
        path, _ = QFileDialog.getSaveFileName(
            self, "Round-trip backup file", default, "XML files (*.xml)"
        )
        if not path:
            return
        try:
            result = self.service.run_xml_round_trip(path)
        except Exception as exc:
            error(self, "Round-trip", str(exc))
            return
        self.report_view.setPlainText(result["report"])
        self.refresh()
        self.corpus_restored.emit()
        if result["passed"]:
            info(self, "Round-trip", "PASSED - counts match before and after restore.")
        else:
            error(self, "Round-trip", "Counts do not match. See report.")
