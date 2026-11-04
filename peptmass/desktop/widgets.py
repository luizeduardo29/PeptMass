"""Tabelas e dica flutuante reaproveitadas pelas abas."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem)


class NumericItem(QTableWidgetItem):
    """Item de tabela que ordena numericamente."""
    def __init__(self, value, text=None):
        super().__init__(text if text is not None else str(value))
        self._value = value
        self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEditable)

    def __lt__(self, other):
        try:
            return self._value < other._value
        except AttributeError:
            return super().__lt__(other)


class HoverTip:
    """Tooltip de hover para figuras matplotlib (sticks/picos).

    Detecta o ponto mais próximo do cursor (em pixels, no eixo x) e mostra uma
    anotação. A conexão de evento é feita uma vez no canvas; a cada replot
    chame rebind(ax) e depois set_points([(x, y, texto), ...])."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.ax = None
        self.ann = None
        self.points = []
        canvas.mpl_connect("motion_notify_event", self._on_move)

    def rebind(self, ax):
        self.ax = ax
        self.points = []
        self.ann = ax.annotate(
            "", xy=(0, 0), xytext=(10, 12), textcoords="offset points",
            fontsize=8, visible=False, zorder=20,
            bbox=dict(boxstyle="round,pad=0.4", fc="#ffffcc", ec="#888888",
                      alpha=0.95))

    def set_points(self, points):
        self.points = points

    def _on_move(self, event):
        if self.ann is None:
            return
        if event.inaxes is not self.ax or not self.points or event.x is None:
            if self.ann.get_visible():
                self.ann.set_visible(False)
                self.canvas.draw_idle()
            return
        trans = self.ax.transData
        best, best_d = None, 1e9
        for x, y, text in self.points:
            px, _py = trans.transform((x, y))
            d = abs(px - event.x)
            if d < best_d:
                best_d, best = d, (x, y, text)
        if best and best_d < 12:
            self.ann.xy = (best[0], best[1])
            self.ann.set_text(best[2])
            self.ann.set_visible(True)
        elif self.ann.get_visible():
            self.ann.set_visible(False)
        else:
            return
        self.canvas.draw_idle()


def make_table(headers):
    t = QTableWidget()
    t.setColumnCount(len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setSortingEnabled(True)
    t.setAlternatingRowColors(True)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.Stretch)
    t.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    return t


def copy_table_selection(table):
    sel = table.selectedRanges()
    if not sel:
        return
    rng = sel[0]
    lines = []
    for r in range(rng.topRow(), rng.bottomRow() + 1):
        cells = []
        for c in range(rng.leftColumn(), rng.rightColumn() + 1):
            item = table.item(r, c)
            cells.append(item.text() if item else "")
        lines.append("\t".join(cells))
    QGuiApplication.clipboard().setText("\n".join(lines))
