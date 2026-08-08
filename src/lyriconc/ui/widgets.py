"""Shared Qt widgets and helpers used across the LyriConc screens."""

from __future__ import annotations

from typing import Any, Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)


def info(parent: QWidget | None, title: str, text: str) -> None:
    QMessageBox.information(parent, title, text)


def warn(parent: QWidget | None, title: str, text: str) -> None:
    QMessageBox.warning(parent, title, text)


def error(parent: QWidget | None, title: str, text: str) -> None:
    QMessageBox.critical(parent, title, text)


def confirm(parent: QWidget | None, title: str, text: str) -> bool:
    reply = QMessageBox.question(
        parent,
        title,
        text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes


def make_table(headers: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setStretchLastSection(True)
    return table


def _cell(value: Any) -> QTableWidgetItem:
    text = "" if value is None else str(value)
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


def fill_table(
    table: QTableWidget,
    rows: Iterable[dict],
    columns: list[str],
    id_column: str | None = None,
) -> None:
    rows = list(rows)
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column_index, column in enumerate(columns):
            item = _cell(row.get(column))
            if column_index == 0 and id_column is not None:
                item.setData(Qt.ItemDataRole.UserRole, row.get(id_column))
            table.setItem(row_index, column_index, item)
    table.resizeColumnsToContents()


def selected_id(table: QTableWidget) -> Any:
    row = table.currentRow()
    if row < 0:
        return None
    item = table.item(row, 0)
    return item.data(Qt.ItemDataRole.UserRole) if item else None
