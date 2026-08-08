import os

import pytest

pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_constructs_and_lists_documents(qapp, service):
    from lyriconc.ui.main_window import MainWindow

    window = MainWindow(service)
    try:
        assert window.library.table.rowCount() == len(service.list_documents())
        assert window.search.doc_table.rowCount() >= 1
        assert window.index.doc_combo.count() >= 2
        assert window.stats.doc_combo.count() >= 2
    finally:
        window.close()
