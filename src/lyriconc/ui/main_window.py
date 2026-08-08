"""Application shell: main window that owns the service and hosts the 5 screens."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QWidget,
)

from ..services import LyriConcService
from .groups_screen import GroupsScreen
from .index_screen import IndexScreen
from .library_screen import LibraryScreen
from .search_screen import SearchScreen
from .stats_screen import StatsScreen


class MainWindow(QMainWindow):
    def __init__(self, service: LyriConcService) -> None:
        super().__init__()
        self.service = service
        self.setWindowTitle("LyriConc - song lyrics concordance")
        self.resize(1280, 820)

        self.library = LibraryScreen(service)
        self.search = SearchScreen(service)
        self.index = IndexScreen(service)
        self.groups = GroupsScreen(service)
        self.stats = StatsScreen(service)

        tabs = QTabWidget()
        tabs.addTab(self.library, "1. Library / Load")
        tabs.addTab(self.search, "2. Search + Context")
        tabs.addTab(self.index, "3. Word Index + Lookup")
        tabs.addTab(self.groups, "4. Groups + Phrases")
        tabs.addTab(self.stats, "5. Stats + XML backup")
        self.setCentralWidget(tabs)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage(f"Database: {service.db_path}")

        self.library.corpus_changed.connect(self._refresh_all)
        self.stats.corpus_restored.connect(self._refresh_all)
        self.search.groups_changed.connect(self._refresh_all)

    def _refresh_all(self) -> None:
        self.search.refresh()
        self.index.refresh()
        self.groups.refresh()
        self.stats.refresh()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        self.service.close()
        super().closeEvent(event)


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    from .. import config

    config.ensure_directories()
    service = LyriConcService()
    window = MainWindow(service)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
