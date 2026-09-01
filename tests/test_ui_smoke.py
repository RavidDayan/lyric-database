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


def test_index_and_lookup_show_same_document_sequence(qapp, service):
    from lyriconc.ui.main_window import MainWindow

    window = MainWindow(service)
    try:
        document = service.list_documents()[0]
        window.index.doc_combo.setCurrentIndex(
            window.index.doc_combo.findData(document["document_id"])
        )
        indexed = service.get_word_index(document["document_id"])[0]
        displayed_sequence = indexed["word_seq_in_doc"] + 1

        assert int(window.index.table.item(0, 6).text()) == displayed_sequence

        window.index.lookup_doc.setCurrentIndex(
            window.index.lookup_doc.findData(document["document_id"])
        )
        window.index.stanza.setValue(indexed["stanza_no"])
        window.index.line.setValue(indexed["line_in_stanza"])
        window.index.offset.setValue(indexed["word_position"])
        window.index._locate_word()

        assert f"doc word seq {displayed_sequence}" in window.index.result_label.text()
    finally:
        window.close()


def test_group_created_in_tab_four_refreshes_other_tabs(
    qapp, service, monkeypatch
):
    import lyriconc.ui.groups_screen as groups_module
    from lyriconc.ui.main_window import MainWindow

    window = MainWindow(service)
    try:
        group_name = "Immediate refresh test"
        monkeypatch.setattr(
            groups_module.QInputDialog,
            "getText",
            lambda *args, **kwargs: (group_name, True),
        )

        window.groups._new_group()

        assert window.search.group_combo.findText(group_name) >= 0
        assert window.index.group_combo.findText(group_name) >= 0
    finally:
        window.close()
