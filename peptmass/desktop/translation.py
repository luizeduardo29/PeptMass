"""Traducao, in loco, dos textos ja construidos na arvore de widgets Qt."""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QAbstractButton, QComboBox, QGroupBox, QLabel, QLineEdit, QPlainTextEdit,
    QTabWidget, QTableWidget, QTextEdit, QWidget)

from peptmass.core.i18n import get_language, t


def translate_tree(root):
    """Traduz, in loco, todos os textos estáticos da árvore de widgets sob
    `root` quando o idioma é inglês. Só altera strings presentes no mapa `_EN`
    — dados do usuário (nomes de peptídeos, fórmulas, etc.) ficam intactos."""
    if get_language() != "en":
        return
    for w in root.findChildren(QWidget):
        if isinstance(w, QGroupBox):
            w.setTitle(t(w.title()))
        elif isinstance(w, (QLabel, QAbstractButton)):
            # botões, checkboxes, radios e rótulos (não QLineEdit)
            txt = w.text()
            if txt:
                w.setText(t(txt))
        if isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit)):
            ph = w.placeholderText()
            if ph:
                w.setPlaceholderText(t(ph))
        tip = w.toolTip()
        if tip:
            w.setToolTip(t(tip))
    for tbl in root.findChildren(QTableWidget):
        for c in range(tbl.columnCount()):
            it = tbl.horizontalHeaderItem(c)
            if it is not None:
                it.setText(t(it.text()))
    for cb in root.findChildren(QComboBox):
        for i in range(cb.count()):
            cb.setItemText(i, t(cb.itemText(i)))
    for tw in root.findChildren(QTabWidget):
        for i in range(tw.count()):
            tw.setTabText(i, t(tw.tabText(i)))
    for act in root.findChildren(QAction):
        if act.text():
            act.setText(t(act.text()))
    try:
        if root.windowTitle():
            root.setWindowTitle(t(root.windowTitle()))
    except Exception:
        pass
