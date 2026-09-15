"""The shape every list QML reads shares: rows of named roles.

A `ListView` or a `Repeater` can only read roles, which is what makes the
boundary #37 draws enforceable — there is nowhere inside a delegate for a rule
about the Analysis to hide. Every model in this application is therefore a
projection computed in Python and handed over as finished rows, and they all
want the same small amount of Qt ceremony. It lives here once.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, Qt


#: One row of a model, as the roles QML binds to.
Row = dict[str, object]


class RoleModel(QAbstractListModel):
    """A list model whose roles are named once and read by attribute name."""

    ROLES: tuple[str, ...] = ()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._names = {
            int(Qt.ItemDataRole.UserRole) + offset: name
            for offset, name in enumerate(self.ROLES)
        }
        self._role_names = {
            role: QByteArray(name.encode()) for role, name in self._names.items()
        }
        self._rows: list[Row] = []

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802 - Qt override
        return self._role_names

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(  # noqa: N802 - Qt override
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        name = self._names.get(role)
        if name is None:
            return None
        return self._rows[index.row()].get(name)

    def rows(self) -> tuple[Row, ...]:
        """What this model is showing, for a test that has no window."""

        return tuple(self._rows)

    def _replace(self, rows: list[Row]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
