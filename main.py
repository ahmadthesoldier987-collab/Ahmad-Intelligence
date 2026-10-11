import sys
import os
import re
import html
import json
import math
import time

import requests

from PySide6.QtCore import (
    Qt,
    QThread,
    Signal,
    QTimer,
    QPropertyAnimation,
    QVariantAnimation,
    QAbstractAnimation,
    QEasingCurve,
    QPoint,
    QPointF,
    QRectF,
    QSize,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPixmap,
    QPainter,
    QPainterPath,
    QPolygonF,
    QConicalGradient,
    QPen,
    QBrush,
    QKeySequence,
    QShortcut,
    QPalette,
    QCursor,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import database as database_module
from database import (
    initialize_database,
    create_project,
    get_projects,
    move_conversation_to_project,
    update_project,
    create_conversation,
    update_conversation_title,
    get_conversations,
    save_message,
    get_messages,
    get_project_instructions_for_conversation,
)

from ai_engine import OLLAMA_URL, MODEL_NAME, DEFAULT_INSTRUCTIONS


APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "ahmad_intelligence_data.json")
TRASH_DAYS = 30

SIDEBAR_W = 300
EDGE_PX = 3            # how close to the screen edge the pointer must be
HIDE_SLACK = 16        # extra pixels around the sidebar before it hides
SERIF = '"Georgia", "Times New Roman", "DejaVu Serif", serif'


def ollama_base():
    if "/api/" in OLLAMA_URL:
        return OLLAMA_URL.split("/api/")[0]
    return "http://localhost:11434"


def refresh_style(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


# ============================================================
# THEMES  (black / white / grey)
# ============================================================

THEMES = {
    "dark": dict(
        bg="#0a0a0a", panel="#111111", panel2="#181818", hover="#212121",
        border="#2b2b2b", border_hi="#454545", text="#ececec",
        muted="#8e8e8e", faint="#5a5a5a", accent="#f2f2f2",
        accent_hover="#ffffff", accent_text="#0a0a0a", user_bg="#1b1b1b",
        danger="#e5646a", ok="#8fd694", code_bg="#101010",
        code_text="#d6d6d6", select="#3a3a3a",
    ),
    "light": dict(
        bg="#f3f3f1", panel="#ffffff", panel2="#f6f6f4", hover="#ebebe8",
        border="#dadad6", border_hi="#b4b4af", text="#161616",
        muted="#666666", faint="#a0a0a0", accent="#141414",
        accent_hover="#000000", accent_text="#ffffff", user_bg="#e9e9e5",
        danger="#c2383e", ok="#2f8f46", code_bg="#ecece8",
        code_text="#222222", select="#cfcfca",
    ),
}

T = dict(THEMES["dark"])          # current theme (mutated in place)
UI = {"font_px": 15}              # chat text size


def set_theme(name):
    T.clear()
    T.update(THEMES.get(name, THEMES["dark"]))


STYLE_TEMPLATE = """
QMainWindow { background-color: @bg@; }

QWidget {
    color: @text@;
    font-family: "Segoe UI", "Inter", "Noto Sans", "Ubuntu", "DejaVu Sans", sans-serif;
    font-size: 13px;
}

QToolTip {
    background-color: @panel@;
    color: @text@;
    border: 1px solid @border_hi@;
    padding: 4px 8px;
}

QWidget#chatContent { background: transparent; }
QScrollArea { background: transparent; border: none; }
QStackedWidget { background: transparent; }

/* ---------- Sidebar ---------- */
QFrame#sidebar {
    background-color: @panel@;
    border: none;
    border-right: 1px solid @border_hi@;
    border-radius: 0px;
}

QLabel#brand {
    font-family: @serif@;
    font-size: 17px;
    font-weight: 700;
    color: @text@;
}
QLabel#brandSub { font-size: 11px; color: @muted@; }

QLabel#section {
    color: @faint@;
    font-size: 10px;
    font-weight: 700;
    padding-top: 6px;
}

QLabel#title {
    font-family: @serif@;
    font-size: 18px;
    font-weight: 700;
    color: @text@;
}
QLabel#hero {
    font-family: @serif@;
    font-size: 36px;
    font-weight: 600;
    color: @text@;
}
QLabel#heroSub { font-size: 14px; color: @muted@; }
QLabel#muted { color: @muted@; font-size: 12px; }
QLabel#status { color: @faint@; font-size: 11px; }
QLabel#hint { color: @faint@; font-size: 11px; }
QLabel#assistantName { color: @muted@; font-size: 12px; font-weight: 700; }
QLabel#dialogTitle {
    font-family: @serif@;
    font-size: 20px;
    font-weight: 700;
    color: @text@;
}
QLabel#cardTitle { font-size: 14px; font-weight: 600; color: @text@; }
QLabel#cardDesc { font-size: 12px; color: @muted@; }
QLabel#binEmpty { color: @faint@; font-size: 13px; }

QLabel#cardIcon {
    background-color: @panel2@;
    border: 1px solid @border@;
    border-radius: 10px;
}

QLabel#chip {
    background-color: @panel2@;
    border: 1px solid @border@;
    border-radius: 12px;
    padding: 5px 12px;
    color: @muted@;
    font-size: 12px;
}

QLabel#localStatus {
    border: 1px solid @border@;
    border-radius: 8px;
    padding: 8px 10px;
    color: @muted@;
    font-size: 11px;
}

/* ---------- Buttons ---------- */
QPushButton {
    background-color: @panel2@;
    color: @text@;
    border: 1px solid @border@;
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 600;
}
QPushButton:hover { background-color: @hover@; border-color: @border_hi@; }
QPushButton:pressed { background-color: @border@; }
QPushButton:disabled {
    color: @faint@;
    background-color: @panel@;
    border-color: @border@;
}

QPushButton#primary {
    background-color: @accent@;
    color: @accent_text@;
    border: 1px solid @accent@;
    font-weight: 700;
    padding: 10px 12px;
}
QPushButton#primary:hover { background-color: @accent_hover@; }
QPushButton#primary:disabled {
    background-color: @panel2@;
    color: @faint@;
    border-color: @border@;
}

QPushButton#nav {
    background-color: transparent;
    border: 1px solid transparent;
    text-align: left;
    padding: 9px 10px;
    font-weight: 500;
    color: @text@;
}
QPushButton#nav:hover { background-color: @hover@; border-color: @border@; }

QPushButton#icon {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0;
}
QPushButton#icon:hover { background-color: @hover@; border-color: @border@; }
QPushButton#icon[on="true"] { background-color: @hover@; border-color: @border_hi@; }

QPushButton#ghost {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 3px 8px;
    color: @muted@;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#ghost:hover { background-color: @hover@; color: @text@; }

QPushButton#sendBtn, QPushButton#stopBtn {
    background-color: @accent@;
    border: none;
    border-radius: 17px;
    padding: 0;
}
QPushButton#sendBtn:hover, QPushButton#stopBtn:hover { background-color: @accent_hover@; }
QPushButton#sendBtn:disabled { background-color: @panel2@; }

QPushButton#jump {
    background-color: @panel@;
    border: 1px solid @border_hi@;
    border-radius: 18px;
    padding: 0;
}
QPushButton#jump:hover { background-color: @hover@; }

QPushButton#danger { color: @danger@; }
QPushButton#danger:hover { border-color: @danger@; }

/* ---------- Inputs ---------- */
QLineEdit, QComboBox, QTextEdit {
    background-color: @panel2@;
    color: @text@;
    border: 1px solid @border@;
    border-radius: 8px;
    padding: 8px 11px;
    selection-background-color: @select@;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 1px solid @muted@; }

QComboBox QAbstractItemView {
    background-color: @panel@;
    color: @text@;
    selection-background-color: @hover@;
    border: 1px solid @border_hi@;
    outline: none;
}

QTextEdit#composerInput {
    background: transparent;
    border: none;
    padding: 2px;
    font-size: 14px;
}

QTextBrowser#bubbleText {
    background: transparent;
    border: none;
    selection-background-color: @select@;
}

/* ---------- Chat ---------- */
QFrame#userCard {
    background-color: @user_bg@;
    border: 1px solid @border@;
    border-radius: 14px;
    border-bottom-right-radius: 4px;
}

QFrame#errorCard {
    background-color: @panel@;
    border: 1px solid @danger@;
    border-radius: 10px;
}

QFrame#card {
    background-color: @panel@;
    border: 1px solid @border@;
    border-radius: 12px;
}
QFrame#card[hover="true"] {
    background-color: @panel2@;
    border: 1px solid @border_hi@;
}

QLabel#toast {
    background-color: @accent@;
    color: @accent_text@;
    border-radius: 10px;
    padding: 9px 18px;
    font-weight: 600;
}

/* ---------- Lists ---------- */
QListWidget {
    background-color: transparent;
    color: @muted@;
    border: none;
    outline: none;
}
QListWidget::item {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 9px 8px;
    margin: 1px 0;
}
QListWidget::item:hover { background-color: @hover@; color: @text@; }
QListWidget::item:selected {
    background-color: @hover@;
    color: @text@;
    border-color: @border_hi@;
}

/* ---------- Menus & dialogs ---------- */
QMenu {
    background-color: @panel@;
    border: 1px solid @border_hi@;
    border-radius: 8px;
    padding: 5px;
}
QMenu::item { padding: 8px 22px 8px 10px; border-radius: 6px; }
QMenu::item:selected { background-color: @hover@; }
QMenu::separator { height: 1px; background: @border@; margin: 5px 6px; }

QDialog, QMessageBox, QInputDialog { background-color: @panel@; }

/* ---------- Scrollbars ---------- */
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px; }
QScrollBar::handle:vertical {
    background-color: @border_hi@;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: @muted@; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""


def build_style():
    style = STYLE_TEMPLATE.replace("@serif@", SERIF)
    for key, value in T.items():
        style = style.replace(f"@{key}@", value)
    return style


def apply_palette(app):
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: T["bg"],
        QPalette.ColorRole.WindowText: T["text"],
        QPalette.ColorRole.Base: T["panel"],
        QPalette.ColorRole.AlternateBase: T["panel2"],
        QPalette.ColorRole.Text: T["text"],
        QPalette.ColorRole.Button: T["panel2"],
        QPalette.ColorRole.ButtonText: T["text"],
        QPalette.ColorRole.ToolTipBase: T["panel"],
        QPalette.ColorRole.ToolTipText: T["text"],
        QPalette.ColorRole.Highlight: T["select"],
        QPalette.ColorRole.HighlightedText: T["text"],
        QPalette.ColorRole.Link: T["text"],
        QPalette.ColorRole.PlaceholderText: T["faint"],
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    app.setPalette(palette)


# ============================================================
# DATA STORE  (bin, pinned chats, settings) - saved next to main.py
# ============================================================

class DataStore:
    def __init__(self, path):
        self.path = path
        self.data = {"trash": {}, "purged": [], "pinned": [], "settings": {}}
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)

            for key, default in self.data.items():
                if key in loaded and isinstance(loaded[key], type(default)):
                    self.data[key] = loaded[key]
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            temp = self.path + ".tmp"
            with open(temp, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, indent=2)
            os.replace(temp, self.path)
        except OSError:
            pass

    # settings
    def get(self, key, default=None):
        return self.data["settings"].get(key, default)

    def set(self, key, value):
        self.data["settings"][key] = value
        self.save()

    # pinned chats
    def is_pinned(self, cid):
        return str(cid) in self.data["pinned"]

    def toggle_pin(self, cid):
        key = str(cid)
        if key in self.data["pinned"]:
            self.data["pinned"].remove(key)
        else:
            self.data["pinned"].append(key)
        self.save()

    # bin
    def trash_chat(self, cid, title):
        key = str(cid)
        self.data["trash"][key] = {
            "id": cid,
            "title": title,
            "deleted_at": time.time(),
        }
        if key in self.data["pinned"]:
            self.data["pinned"].remove(key)
        self.save()

    def restore(self, cid):
        self.data["trash"].pop(str(cid), None)
        self.save()

    def forget(self, cid):
        key = str(cid)
        self.data["trash"].pop(key, None)
        if key not in self.data["purged"]:
            self.data["purged"].append(key)
        self.save()

    def hidden_ids(self):
        return set(self.data["trash"]) | set(self.data["purged"])

    def trashed(self):
        entries = list(self.data["trash"].values())
        entries.sort(key=lambda e: e.get("deleted_at", 0), reverse=True)
        return entries

    def expired(self):
        limit = TRASH_DAYS * 86400
        now = time.time()
        return [
            entry["id"]
            for entry in self.data["trash"].values()
            if now - entry.get("deleted_at", now) >= limit
        ]

    @staticmethod
    def days_left(deleted_at):
        remaining = deleted_at + TRASH_DAYS * 86400 - time.time()
        return max(0, int(math.ceil(remaining / 86400)))


# ============================================================
# VECTOR ICONS  (painted, so they never depend on fonts)
# ============================================================

def draw_icon(p, name, color):
    def line(a, b, c, d):
        p.drawLine(QPointF(a, b), QPointF(c, d))

    def poly(*pts):
        p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in pts]))

    def shape(*pts):
        p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))

    if name == "menu":
        line(4, 6, 20, 6); line(4, 12, 20, 12); line(4, 18, 20, 18)
    elif name == "plus":
        line(12, 5, 12, 19); line(5, 12, 19, 12)
    elif name == "search":
        p.drawEllipse(QPointF(10.5, 10.5), 6, 6); line(15, 15, 20, 20)
    elif name == "trash":
        line(4, 7, 20, 7)
        poly((9, 7), (9, 4), (15, 4), (15, 7))
        poly((6, 7), (7, 20), (17, 20), (18, 7))
        line(10, 11, 10, 16); line(14, 11, 14, 16)
    elif name == "send":
        line(12, 19, 12, 5); poly((6, 11), (12, 5), (18, 11))
    elif name == "stop":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(7, 7, 10, 10), 2, 2)
    elif name == "pin":
        shape((9, 4), (15, 4), (14, 10), (18, 14), (6, 14), (10, 10))
        line(12, 14, 12, 21)
    elif name == "copy":
        p.drawRoundedRect(QRectF(9, 9, 11, 11), 2, 2)
        poly((9, 15), (5, 15), (5, 5), (15, 5), (15, 9))
    elif name == "check":
        poly((5, 12), (10, 17), (19, 7))
    elif name == "edit":
        shape((4, 20), (5.5, 14.5), (15.5, 4.5), (19.5, 8.5), (9.5, 18.5))
        line(13, 7, 17, 11)
    elif name == "download":
        line(12, 4, 12, 15); poly((7, 10), (12, 15), (17, 10)); line(5, 20, 19, 20)
    elif name == "restore":
        poly((8, 4), (4, 8), (8, 12))
        line(4, 8, 15, 8)
        poly((15, 8), (19, 10), (19, 14), (15, 16), (8, 16))
    elif name == "close":
        line(6, 6, 18, 18); line(18, 6, 6, 18)
    elif name == "tune":
        line(4, 7, 20, 7); line(4, 12, 20, 12); line(4, 17, 20, 17)
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(9, 7), 2.4, 2.4)
        p.drawEllipse(QPointF(15, 12), 2.4, 2.4)
        p.drawEllipse(QPointF(8, 17), 2.4, 2.4)
    elif name == "sun":
        p.drawEllipse(QPointF(12, 12), 4, 4)
        for i in range(8):
            a = i * math.pi / 4
            line(12 + 6.8 * math.cos(a), 12 + 6.8 * math.sin(a),
                 12 + 9.2 * math.cos(a), 12 + 9.2 * math.sin(a))
    elif name == "moon":
        a = QPainterPath(); a.addEllipse(QPointF(12, 12), 7.5, 7.5)
        b = QPainterPath(); b.addEllipse(QPointF(16.5, 8.5), 6.5, 6.5)
        p.drawPath(a.subtracted(b))
    elif name == "chat":
        path = QPainterPath()
        path.addRoundedRect(QRectF(4, 5, 16, 11), 3, 3)
        p.drawPath(path)
        poly((9, 16), (9.5, 20), (13.5, 16))
    elif name == "folder":
        path = QPainterPath()
        path.moveTo(3, 8); path.lineTo(3, 6)
        path.quadTo(3, 5, 4, 5); path.lineTo(9, 5); path.lineTo(11, 7.5)
        path.lineTo(20, 7.5); path.quadTo(21, 7.5, 21, 8.5)
        path.lineTo(21, 18); path.quadTo(21, 19, 20, 19)
        path.lineTo(4, 19); path.quadTo(3, 19, 3, 18); path.closeSubpath()
        p.drawPath(path)
    elif name == "sidebar":
        p.drawRoundedRect(QRectF(4, 5, 16, 14), 2, 2); line(9, 5, 9, 19)
    elif name == "arrow_down":
        line(12, 5, 12, 19); poly((6, 13), (12, 19), (18, 13))
    elif name == "code":
        poly((9, 7), (4, 12), (9, 17)); poly((15, 7), (20, 12), (15, 17))
        line(13.5, 5, 10.5, 19)
    elif name == "book":
        p.drawRoundedRect(QRectF(5, 4, 14, 16), 2, 2)
        line(9, 4, 9, 20); line(12, 9, 16, 9); line(12, 12, 16, 12)
    elif name == "bulb":
        p.drawEllipse(QPointF(12, 10), 5.5, 5.5)
        line(9.5, 18, 14.5, 18); line(10.5, 21, 13.5, 21)
    elif name == "sparkle":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawPath(sparkle_path(12, 12, 9))
    elif name == "more":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        for x in (6, 12, 18):
            p.drawEllipse(QPointF(x, 12), 1.8, 1.8)


_ICON_CACHE = {}


def make_icon(name, role="text", size=18):
    color = T.get(role, role)
    key = (name, color, T["faint"], size)

    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    icon = QIcon()

    for mode, tint in (
        (QIcon.Mode.Normal, color),
        (QIcon.Mode.Disabled, T["faint"]),
    ):
        pixmap = QPixmap(size * 2, size * 2)
        pixmap.setDevicePixelRatio(2.0)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 24.0, size / 24.0)

        pen = QPen(QColor(tint), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        draw_icon(painter, name, tint)
        painter.end()
        icon.addPixmap(pixmap, mode)

    _ICON_CACHE[key] = icon
    return icon


def sparkle_path(cx, cy, r):
    k = r * 0.14
    path = QPainterPath()
    path.moveTo(cx, cy - r)
    path.quadTo(cx + k, cy - k, cx + r, cy)
    path.quadTo(cx + k, cy + k, cx, cy + r)
    path.quadTo(cx - k, cy + k, cx - r, cy)
    path.quadTo(cx - k, cy - k, cx, cy - r)
    path.closeSubpath()
    return path


# ============================================================
# CUSTOM WIDGETS
# ============================================================

class Logo(QWidget):
    def __init__(self, size=34):
        super().__init__()
        self.setFixedSize(size, size)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.width()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(T["accent"]))
        painter.drawRoundedRect(QRectF(0, 0, s, s), s * 0.26, s * 0.26)

        painter.setBrush(QColor(T["accent_text"]))
        painter.drawPath(sparkle_path(s * 0.47, s * 0.53, s * 0.27))
        painter.drawPath(sparkle_path(s * 0.76, s * 0.25, s * 0.1))


class TypingDots(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(52, 22)
        self.phase = 0
        self.timer = QTimer(self)
        self.timer.setInterval(70)
        self.timer.timeout.connect(self._tick)

    def _tick(self):
        self.phase = (self.phase + 1) % 1000
        self.update()

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(3):
            wave = 0.5 + 0.5 * math.sin(self.phase * 0.28 - i * 1.1)
            color = QColor(T["muted"])
            color.setAlphaF(0.25 + 0.75 * wave)
            painter.setBrush(color)
            radius = 3.2 + 1.4 * wave
            painter.drawEllipse(QPointF(10 + i * 16, 11), radius, radius)


class Backdrop(QWidget):
    resized = Signal()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(T["bg"]))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()


class EdgeHint(QWidget):
    """A faint marker on the left edge: the sidebar lives behind it."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.active = True

    def paintEvent(self, _event):
        if not self.active:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        color = QColor(T["muted"])
        color.setAlpha(110)
        painter.setBrush(color)
        painter.drawRoundedRect(
            QRectF(0, self.height() / 2 - 28, 3, 56), 1.5, 1.5
        )


class ComposerFrame(QFrame):
    def __init__(self):
        super().__init__()
        self.focused = False
        self.glowing = False
        self.angle = 0.0

        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._spin)

    def set_focused(self, value):
        self.focused = value
        self.update()

    def set_glowing(self, value):
        self.glowing = value
        if value:
            self.timer.start()
        else:
            self.timer.stop()
        self.update()

    def _spin(self):
        self.angle = (self.angle - 5.0) % 360
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)

        painter.fillPath(path, QColor(T["panel"]))

        if self.glowing:
            gradient = QConicalGradient(rect.center(), self.angle)
            gradient.setColorAt(0.0, QColor(T["accent"]))
            gradient.setColorAt(0.4, QColor(T["border"]))
            gradient.setColorAt(0.75, QColor(T["border"]))
            gradient.setColorAt(1.0, QColor(T["accent"]))
            pen = QPen(QBrush(gradient), 1.8)
        elif self.focused:
            pen = QPen(QColor(T["muted"]), 1.3)
        else:
            pen = QPen(QColor(T["border_hi"]), 1.0)

        painter.setPen(pen)
        painter.drawPath(path)


class GrowingTextEdit(QTextEdit):
    submitted = Signal()
    focus_changed = Signal(bool)

    MIN_HEIGHT = 32
    MAX_HEIGHT = 170

    def __init__(self):
        super().__init__()
        self.setObjectName("composerInput")
        self.setAcceptRichText(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.document().setDocumentMargin(4)
        self.setFixedHeight(self.MIN_HEIGHT)
        self.document().documentLayout().documentSizeChanged.connect(
            self._resize_to_content
        )

    def _resize_to_content(self, size):
        height = int(math.ceil(size.height())) + 8
        self.setFixedHeight(
            max(self.MIN_HEIGHT, min(self.MAX_HEIGHT, height))
        )

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self.submitted.emit()
                return
        super().keyPressEvent(event)

    def focusInEvent(self, event):
        self.focus_changed.emit(True)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.focus_changed.emit(False)
        super().focusOutEvent(event)


class AutoText(QTextBrowser):
    """Text view that sizes itself to its content (no inner scrollbars)."""

    def __init__(self, shrink=False, max_width=None):
        super().__init__()
        self.setObjectName("bubbleText")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.viewport().setAutoFillBackground(False)
        self.setStyleSheet(f"font-size: {UI['font_px']}px;")
        self.document().setDocumentMargin(0)
        self.document().setDefaultStyleSheet(
            "p { margin-top: 0px; margin-bottom: 8px; }"
            "li { margin-bottom: 3px; }"
            f"h1, h2, h3 {{ color: {T['text']}; }}"
            f"a {{ color: {T['text']}; }}"
            "code, pre { font-family: Consolas, 'DejaVu Sans Mono', monospace;"
            f" color: {T['code_text']}; background-color: {T['code_bg']}; }}"
        )

        self.shrink = shrink
        self.max_text_width = max_width
        self.natural_width = 0

        policy = (
            QSizePolicy.Policy.Preferred
            if shrink
            else QSizePolicy.Policy.Expanding
        )
        self.setSizePolicy(policy, QSizePolicy.Policy.Fixed)

        if max_width:
            self.setMaximumWidth(max_width)

        self.setFixedHeight(22)
        self.document().documentLayout().documentSizeChanged.connect(
            self._fit_height
        )

    def _fit_height(self, size):
        height = int(math.ceil(size.height())) + 2
        if height != self.height():
            self.setFixedHeight(height)

    def set_plain(self, text):
        self.setPlainText(text)

        if self.shrink:
            probe = self.document().clone()
            probe.setTextWidth(-1)
            self.natural_width = int(math.ceil(probe.idealWidth())) + 3
            self.updateGeometry()

    def set_markdown(self, text):
        self.setMarkdown(text)

    def sizeHint(self):
        if self.shrink and self.natural_width:
            width = self.natural_width
            if self.max_text_width:
                width = min(width, self.max_text_width)
            return QSize(width, self.height())
        return super().sizeHint()


class ChatScroll(QScrollArea):
    """Scroll area with a floating 'jump to latest' button."""

    def __init__(self):
        super().__init__()
        self.jump = QPushButton(self)
        self.jump.setObjectName("jump")
        self.jump.setFixedSize(36, 36)
        self.jump.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.jump.setToolTip("Jump to latest")
        self.jump.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.jump.move((self.width() - 36) // 2, self.height() - 50)
        self.jump.raise_()


class HistoryList(QListWidget):
    delete_pressed = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_pressed.emit()
            return
        super().keyPressEvent(event)


# ============================================================
# CHAT WIDGETS
# ============================================================

class UserBubble(QWidget):
    def __init__(self, text):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 8, 0, 8)
        row.addStretch(1)

        card = QFrame()
        card.setObjectName("userCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 11, 16, 11)

        self.text = AutoText(shrink=True, max_width=620)
        self.text.set_plain(text)
        card_layout.addWidget(self.text)

        row.addWidget(card, 0)


class AssistantBubble(QWidget):
    copy_requested = Signal(str)

    def __init__(self, text="", streaming=False):
        super().__init__()
        self.raw = text
        self.waiting = streaming

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 10, 0, 10)
        row.setSpacing(14)
        row.addWidget(Logo(28), 0, Qt.AlignmentFlag.AlignTop)

        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        name = QLabel("Ahmad Intelligence")
        name.setObjectName("assistantName")
        column.addWidget(name)

        self.dots = TypingDots()
        column.addWidget(self.dots, 0, Qt.AlignmentFlag.AlignLeft)

        self.body = AutoText()
        column.addWidget(self.body)

        self.copy_button = QPushButton("  Copy")
        self.copy_button.setObjectName("ghost")
        self.copy_button.setIcon(make_icon("copy", "muted", 14))
        self.copy_button.setIconSize(QSize(14, 14))
        self.copy_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.copy_button.setFixedHeight(26)
        self.copy_button.clicked.connect(
            lambda: self.copy_requested.emit(self.raw)
        )
        column.addWidget(self.copy_button, 0, Qt.AlignmentFlag.AlignLeft)

        row.addLayout(column, 1)

        if streaming:
            self.body.hide()
            self.copy_button.hide()
        else:
            self.dots.hide()
            self.body.set_markdown(text)

    def set_text(self, text):
        self.raw = text

        if self.waiting and text:
            self.waiting = False
            self.dots.hide()
            self.body.show()

        if not self.waiting:
            self.body.set_markdown(text)

    def finish(self):
        self.waiting = False
        self.dots.hide()
        self.body.show()
        self.copy_button.show()


class ErrorNote(QFrame):
    def __init__(self, message):
        super().__init__()
        self.setObjectName("errorCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        label = QLabel(message)
        label.setWordWrap(True)
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(label)


class SuggestionCard(QFrame):
    clicked = Signal(str)

    def __init__(self, icon_name, title, description, prompt):
        super().__init__()
        self.setObjectName("card")
        self.prompt = prompt
        self.icon_name = icon_name
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setProperty("hover", False)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(14)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("cardIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(40, 40)
        row.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignTop)

        text_column = QVBoxLayout()
        text_column.setSpacing(3)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        text_column.addWidget(title_label)

        description_label = QLabel(description)
        description_label.setObjectName("cardDesc")
        description_label.setWordWrap(True)
        text_column.addWidget(description_label)

        row.addLayout(text_column, 1)
        self.retheme()

    def retheme(self):
        self.icon_label.setPixmap(
            make_icon(self.icon_name, "text", 20).pixmap(QSize(20, 20))
        )

    def enterEvent(self, event):
        self.setProperty("hover", True)
        refresh_style(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hover", False)
        refresh_style(self)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.prompt)
        super().mousePressEvent(event)


class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hiding = False

        self.effect = QGraphicsOpacityEffect(self)
        self.effect.setOpacity(0.0)
        self.setGraphicsEffect(self.effect)

        self.animation = QPropertyAnimation(self.effect, b"opacity", self)
        self.animation.setDuration(200)
        self.animation.finished.connect(self._animation_done)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._fade_out)

        self.hide()

    def pop(self, text):
        self.hiding = False
        self.setText(text)
        self.adjustSize()

        parent = self.parentWidget()
        self.move(
            (parent.width() - self.width()) // 2,
            parent.height() - self.height() - 118,
        )

        self.show()
        self.raise_()

        self.animation.stop()
        self.animation.setStartValue(self.effect.opacity())
        self.animation.setEndValue(1.0)
        self.animation.start()
        self.timer.start(2100)

    def _fade_out(self):
        self.hiding = True
        self.animation.stop()
        self.animation.setStartValue(self.effect.opacity())
        self.animation.setEndValue(0.0)
        self.animation.start()

    def _animation_done(self):
        if self.hiding:
            self.hide()


def fade_in(widget, duration=300):
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)

    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.finished.connect(lambda: widget.setGraphicsEffect(None))
    animation.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)


# ============================================================
# BIN DIALOG
# ============================================================

class BinDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.win = window
        self.setWindowTitle("Bin")
        self.resize(540, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        heading = QLabel("Bin")
        heading.setObjectName("dialogTitle")
        layout.addWidget(heading)

        note = QLabel(
            f"Deleted chats stay here for {TRASH_DAYS} days, "
            "then they are removed automatically."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.list = QListWidget()
        self.list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.list.setIconSize(QSize(16, 16))
        layout.addWidget(self.list, 1)

        self.empty_label = QLabel("The bin is empty.")
        self.empty_label.setObjectName("binEmpty")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        self.restore_button = QPushButton("  Restore")
        self.restore_button.setObjectName("primary")
        self.restore_button.setIcon(make_icon("restore", "accent_text", 16))
        self.restore_button.clicked.connect(self.restore_selected)
        buttons.addWidget(self.restore_button)

        self.forever_button = QPushButton("  Delete forever")
        self.forever_button.setObjectName("danger")
        self.forever_button.setIcon(make_icon("trash", "danger", 16))
        self.forever_button.clicked.connect(self.delete_selected)
        buttons.addWidget(self.forever_button)

        buttons.addStretch(1)

        self.empty_button = QPushButton("Empty bin")
        self.empty_button.setObjectName("danger")
        self.empty_button.clicked.connect(self.empty_bin)
        buttons.addWidget(self.empty_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)

        layout.addLayout(buttons)
        self.refresh()

    def refresh(self):
        self.list.clear()
        entries = self.win.store.trashed()

        for entry in entries:
            days = DataStore.days_left(entry.get("deleted_at", 0))
            unit = "day" if days == 1 else "days"
            item = QListWidgetItem(
                f"{entry.get('title') or 'Untitled chat'}\n"
                f"{days} {unit} left"
            )
            item.setIcon(make_icon("chat", "muted", 16))
            item.setData(Qt.ItemDataRole.UserRole, entry["id"])
            self.list.addItem(item)

        has_items = bool(entries)
        self.list.setVisible(has_items)
        self.empty_label.setVisible(not has_items)
        self.restore_button.setEnabled(has_items)
        self.forever_button.setEnabled(has_items)
        self.empty_button.setEnabled(has_items)

        self.win.update_bin_badge()

    def _selected_ids(self):
        return [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.list.selectedItems()
        ]

    def restore_selected(self):
        ids = self._selected_ids()

        if not ids:
            self.win.toast.pop("Select a chat to restore")
            return

        for cid in ids:
            self.win.restore_chat(cid)

        self.refresh()

    def delete_selected(self):
        ids = self._selected_ids()

        if not ids:
            self.win.toast.pop("Select a chat first")
            return

        answer = QMessageBox.question(
            self,
            "Delete forever",
            f"Permanently delete {len(ids)} chat(s)? This cannot be undone.",
        )

        if answer == QMessageBox.StandardButton.Yes:
            for cid in ids:
                self.win.purge_chat(cid)
            self.refresh()

    def empty_bin(self):
        answer = QMessageBox.question(
            self,
            "Empty bin",
            "Permanently delete everything in the bin? "
            "This cannot be undone.",
        )

        if answer == QMessageBox.StandardButton.Yes:
            for entry in list(self.win.store.trashed()):
                self.win.purge_chat(entry["id"])
            self.refresh()


# ============================================================
# BACKGROUND WORKERS
# ============================================================

class AIWorker(QThread):
    token_received = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, messages, instructions, model):
        super().__init__()
        self.messages = messages
        self.instructions = instructions
        self.model = model
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            system_prompt = DEFAULT_INSTRUCTIONS

            if self.instructions.strip():
                system_prompt += (
                    "\n\nAdditional project instructions:\n"
                    + self.instructions.strip()
                )

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *self.messages,
                ],
                "stream": True,
            }

            answer_parts = []

            with requests.post(
                OLLAMA_URL,
                json=payload,
                stream=True,
                timeout=(10, 300),
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if self._stop:
                        break

                    if not line:
                        continue

                    packet = json.loads(line.decode("utf-8"))

                    if packet.get("error"):
                        raise RuntimeError(packet["error"])

                    chunk = packet.get("message", {}).get("content", "")

                    if chunk:
                        answer_parts.append(chunk)
                        self.token_received.emit(chunk)

                    if packet.get("done"):
                        break

            answer = "".join(answer_parts)

            if not answer.strip() and not self._stop:
                raise RuntimeError("The model returned an empty response.")

            self.completed.emit(answer)

        except Exception as error:
            self.failed.emit(str(error))


class PingWorker(QThread):
    result = Signal(bool)

    def run(self):
        try:
            response = requests.get(ollama_base() + "/api/tags", timeout=2)
            self.result.emit(response.ok)
        except Exception:
            self.result.emit(False)


# ============================================================
# MAIN WINDOW
# ============================================================

class AhmadIntelligence(QMainWindow):

    def __init__(self):
        super().__init__()

        self.store = DataStore(DATA_FILE)
        set_theme(self.store.get("theme", "dark"))
        UI["font_px"] = int(self.store.get("font_px", 15))

        self.conversation_id = None
        self.current_project_id = "default"
        self.model_name = MODEL_NAME
        self.busy = False
        self.worker = None
        self._workers = set()
        self.current_answer = ""
        self.stream_bubble = None
        self.stream_dirty = False
        self.t_start = 0.0
        self.sidebar_pinned = False
        self.sidebar_open = False
        self.stick_to_bottom = True
        self.ollama_ok = None
        self.icon_refs = {}
        self.welcome_cards = []
        self._edge_ticks = 0
        self._leave_ticks = 0

        initialize_database()

        self.setWindowTitle("Ahmad Intelligence")
        self.resize(1380, 880)
        self.setMinimumSize(880, 600)

        app = QApplication.instance()
        apply_palette(app)
        app.setStyleSheet(build_style())

        self.build_ui()
        self.setup_shortcuts()
        self.load_projects(select_id="default")
        self.purge_expired()
        self.new_chat()
        self.start_ping()
        self.update_bin_badge()

    # --------------------------------------------------------
    # ICON HELPERS
    # --------------------------------------------------------

    def set_icon(self, button, name, role="text", size=18):
        self.icon_refs[button] = (name, role, size)
        button.setIcon(make_icon(name, role, size))
        button.setIconSize(QSize(size, size))

    def retheme_icons(self):
        for button, (name, role, size) in self.icon_refs.items():
            button.setIcon(make_icon(name, role, size))

    # --------------------------------------------------------
    # INTERFACE
    # --------------------------------------------------------

    def build_ui(self):
        self.root = Backdrop()
        self.setCentralWidget(self.root)

        self.root_layout = QHBoxLayout(self.root)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.workspace = QWidget()
        self.root_layout.addWidget(self.workspace, 1)
        self.build_workspace()

        # Floating overlays (not part of the layout)
        self.edge = EdgeHint(self.root)

        self.sidebar = QFrame(self.root)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(SIDEBAR_W)
        self.build_sidebar()

        self.toast = Toast(self.root)

        # Animations and timers
        self.sb_anim = QPropertyAnimation(self.sidebar, b"pos", self)
        self.sb_anim.setDuration(220)
        self.sb_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.sb_anim.finished.connect(self._sidebar_anim_done)

        self.margin_anim = QVariantAnimation(self)
        self.margin_anim.setDuration(220)
        self.margin_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.margin_anim.valueChanged.connect(
            lambda value: self.root_layout.setContentsMargins(
                int(value), 0, 0, 0
            )
        )

        self.stream_timer = QTimer(self)
        self.stream_timer.setInterval(45)
        self.stream_timer.timeout.connect(self._flush_stream)

        # Taskbar-style auto-hide: watch the pointer position
        self.cursor_timer = QTimer(self)
        self.cursor_timer.setInterval(30)
        self.cursor_timer.timeout.connect(self._poll_cursor)
        self.cursor_timer.start()

        self.purge_timer = QTimer(self)
        self.purge_timer.setInterval(3600 * 1000)
        self.purge_timer.timeout.connect(self.purge_expired)
        self.purge_timer.start()

        self.root.resized.connect(self.place_overlays)

        self.sidebar.move(-SIDEBAR_W - 4, 0)
        self.sidebar.hide()
        self.edge.raise_()
        self.sidebar.raise_()
        self.toast.raise_()
        self.place_overlays()

    # ---------------- Sidebar ----------------

    def build_sidebar(self):
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(16, 18, 16, 14)
        side.setSpacing(9)

        header = QHBoxLayout()
        header.setSpacing(11)
        header.addWidget(Logo(36))

        brand_column = QVBoxLayout()
        brand_column.setSpacing(0)
        brand = QLabel("Ahmad Intelligence")
        brand.setObjectName("brand")
        brand_column.addWidget(brand)
        brand_sub = QLabel("Private · Local · Yours")
        brand_sub.setObjectName("brandSub")
        brand_column.addWidget(brand_sub)
        header.addLayout(brand_column, 1)

        self.pin_button = QPushButton()
        self.pin_button.setObjectName("icon")
        self.pin_button.setFixedSize(32, 32)
        self.pin_button.setToolTip("Keep sidebar open (Ctrl+B)")
        self.pin_button.setProperty("on", False)
        self.pin_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.set_icon(self.pin_button, "pin", "muted", 16)
        self.pin_button.clicked.connect(self.toggle_pin)
        header.addWidget(self.pin_button)
        side.addLayout(header)

        side.addSpacing(6)

        self.new_chat_button = QPushButton("  New chat")
        self.new_chat_button.setObjectName("primary")
        self.new_chat_button.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.set_icon(self.new_chat_button, "plus", "accent_text", 16)
        self.new_chat_button.clicked.connect(self.new_chat)
        side.addWidget(self.new_chat_button)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search chats   Ctrl+K")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.apply_history_filter)
        side.addWidget(self.search)

        workspace_label = QLabel("WORKSPACE")
        workspace_label.setObjectName("section")
        side.addWidget(workspace_label)

        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self.project_changed)
        side.addWidget(self.project_combo)

        project_actions = QHBoxLayout()
        project_actions.setSpacing(8)

        add_project = QPushButton("  Project")
        self.set_icon(add_project, "folder", "text", 15)
        add_project.clicked.connect(self.new_project)
        project_actions.addWidget(add_project)

        instructions_button = QPushButton("  Rules")
        instructions_button.setToolTip("Instructions for this project")
        self.set_icon(instructions_button, "edit", "text", 15)
        instructions_button.clicked.connect(self.edit_project_instructions)
        project_actions.addWidget(instructions_button)
        side.addLayout(project_actions)

        history_label = QLabel("CHATS")
        history_label.setObjectName("section")
        side.addWidget(history_label)

        self.history = HistoryList()
        self.history.setIconSize(QSize(14, 14))
        self.history.setVerticalScrollMode(
            QListWidget.ScrollMode.ScrollPerPixel
        )
        self.history.itemClicked.connect(self.open_conversation)
        self.history.delete_pressed.connect(self.delete_selected_history)
        self.history.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.history.customContextMenuRequested.connect(self.history_menu)
        side.addWidget(self.history, 1)

        self.bin_button = QPushButton("  Bin")
        self.bin_button.setObjectName("nav")
        self.bin_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.set_icon(self.bin_button, "trash", "text", 16)
        self.bin_button.clicked.connect(self.open_bin)
        side.addWidget(self.bin_button)

        self.side_status = QLabel("●  Checking Ollama…")
        self.side_status.setObjectName("localStatus")
        side.addWidget(self.side_status)

    # ---------------- Workspace ----------------

    def build_workspace(self):
        layout = QVBoxLayout(self.workspace)
        layout.setContentsMargins(26, 14, 26, 10)
        layout.setSpacing(10)

        topbar = QHBoxLayout()
        topbar.setSpacing(6)

        self.menu_button = QPushButton()
        self.menu_button.setObjectName("icon")
        self.menu_button.setFixedSize(38, 38)
        self.menu_button.setToolTip(
            "Sidebar: move the mouse to the left edge, or press Ctrl+B to pin"
        )
        self.set_icon(self.menu_button, "sidebar", "text", 20)
        self.menu_button.clicked.connect(self.toggle_pin)
        topbar.addWidget(self.menu_button)

        title_column = QVBoxLayout()
        title_column.setSpacing(0)

        self.page_title = QLabel("New chat")
        self.page_title.setObjectName("title")
        title_column.addWidget(self.page_title)

        self.page_sub = QLabel("Workspace")
        self.page_sub.setObjectName("muted")
        title_column.addWidget(self.page_sub)

        topbar.addLayout(title_column, 1)

        self.model_chip = QLabel()
        self.model_chip.setObjectName("chip")
        self.model_chip.setTextFormat(Qt.TextFormat.RichText)
        self.model_chip.setToolTip("Active Ollama model")
        topbar.addWidget(self.model_chip)
        self.refresh_model_chip()

        self.export_button = self.top_icon_button(
            "download", "Export chat as Markdown", self.export_chat
        )
        topbar.addWidget(self.export_button)

        self.delete_button = self.top_icon_button(
            "trash", "Move this chat to the bin", self.delete_current_chat
        )
        topbar.addWidget(self.delete_button)

        self.theme_button = self.top_icon_button(
            "sun" if "light" == self.store.get("theme", "dark") else "moon",
            "Switch light / dark theme",
            self.toggle_theme,
        )
        topbar.addWidget(self.theme_button)

        settings_button = self.top_icon_button(
            "tune", "Model settings", self.open_settings
        )
        topbar.addWidget(settings_button)

        layout.addLayout(topbar)

        self.stack = QStackedWidget()
        self.welcome = self.build_welcome()
        self.scroll = self.build_chat_area()
        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.scroll)
        layout.addWidget(self.stack, 1)

        # Composer
        self.composer = ComposerFrame()
        self.composer.setMaximumWidth(880)

        composer_layout = QVBoxLayout(self.composer)
        composer_layout.setContentsMargins(18, 12, 12, 10)
        composer_layout.setSpacing(4)

        self.message_input = GrowingTextEdit()
        self.message_input.setPlaceholderText("Message Ahmad Intelligence…")
        self.message_input.submitted.connect(self.send_message)
        self.message_input.focus_changed.connect(self.composer.set_focused)
        self.message_input.textChanged.connect(self._update_send_state)
        composer_layout.addWidget(self.message_input)

        bottom = QHBoxLayout()
        hint = QLabel(
            "Enter to send  ·  Shift+Enter new line  ·  Ctrl +/- text size"
        )
        hint.setObjectName("hint")
        bottom.addWidget(hint, 1)

        self.send_button = QPushButton()
        self.send_button.setObjectName("sendBtn")
        self.send_button.setFixedSize(34, 34)
        self.send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.set_icon(self.send_button, "send", "accent_text", 18)
        self.send_button.clicked.connect(self.on_send_clicked)
        bottom.addWidget(self.send_button)
        composer_layout.addLayout(bottom)

        composer_row = QHBoxLayout()
        composer_row.addStretch(1)
        composer_row.addWidget(self.composer, 1000)
        composer_row.addStretch(1)
        layout.addLayout(composer_row)

        self.status = QLabel("Ready")
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        self._update_send_state()

    def top_icon_button(self, icon_name, tooltip, slot):
        button = QPushButton()
        button.setObjectName("icon")
        button.setFixedSize(38, 38)
        button.setToolTip(tooltip)
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.set_icon(button, icon_name, "text", 19)
        button.clicked.connect(slot)
        return button

    def build_chat_area(self):
        scroll = ChatScroll()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.viewport().setAutoFillBackground(False)
        self.set_icon(scroll.jump, "arrow_down", "text", 18)
        scroll.jump.clicked.connect(self.jump_to_latest)

        content = QWidget()
        content.setObjectName("chatContent")

        outer = QHBoxLayout(content)
        outer.setContentsMargins(0, 0, 6, 0)

        column = QWidget()
        column.setMaximumWidth(880)
        self.msg_layout = QVBoxLayout(column)
        self.msg_layout.setContentsMargins(0, 8, 0, 28)
        self.msg_layout.setSpacing(4)
        self.msg_layout.addStretch(1)

        outer.addStretch(1)
        outer.addWidget(column, 1000)
        outer.addStretch(1)

        scroll.setWidget(content)
        content.setAutoFillBackground(False)

        bar = scroll.verticalScrollBar()
        bar.rangeChanged.connect(self._range_changed)
        bar.valueChanged.connect(self._scroll_moved)
        return scroll

    def build_welcome(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 20)
        layout.setSpacing(0)

        layout.addStretch(3)
        layout.addWidget(Logo(60), 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(22)

        hero = QLabel("How can I help you today?")
        hero.setObjectName("hero")
        hero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hero)

        subtitle = QLabel("Think clearly. Build carefully. Keep it private.")
        subtitle.setObjectName("heroSub")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(30)

        holder = QWidget()
        holder.setMaximumWidth(780)
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)

        cards = [
            (
                "code", "Debug my code",
                "Paste an error and fix it together.",
                "I'm going to paste an error from my code. "
                "Help me understand what it means and how to fix it.\n\n",
            ),
            (
                "book", "Explain a concept",
                "Learn anything with clear examples.",
                "Explain how APIs work in simple terms, "
                "with a practical example.",
            ),
            (
                "edit", "Plan a project",
                "Turn a rough idea into clear steps.",
                "Help me plan a new software project step by step. "
                "Ask me what I want to build first.",
            ),
            (
                "bulb", "Brainstorm ideas",
                "Explore creative directions.",
                "Brainstorm 10 creative app ideas I could build "
                "as a beginner developer.",
            ),
        ]

        for index, (icon_name, title, desc, prompt) in enumerate(cards):
            card = SuggestionCard(icon_name, title, desc, prompt)
            card.clicked.connect(self.use_prompt)
            self.welcome_cards.append(card)
            grid.addWidget(card, index // 2, index % 2)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(holder, 1000)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addStretch(4)
        return page

    def setup_shortcuts(self):
        bindings = [
            ("Ctrl+N", self.new_chat),
            ("Ctrl+B", self.toggle_pin),
            ("Ctrl+K", self.focus_search),
            ("Ctrl+Shift+E", self.export_chat),
            ("Ctrl+Shift+T", self.toggle_theme),
            ("Ctrl+=", lambda: self.zoom(1)),
            ("Ctrl++", lambda: self.zoom(1)),
            ("Ctrl+-", lambda: self.zoom(-1)),
            ("Ctrl+0", lambda: self.zoom(0)),
            ("Esc", self.stop_generation),
        ]
        self._shortcuts = []

        for sequence, callback in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    # --------------------------------------------------------
    # TASKBAR-STYLE AUTO-HIDING SIDEBAR
    # --------------------------------------------------------

    def place_overlays(self):
        height = self.root.height()
        self.edge.setGeometry(0, 0, 6, height)
        self.sidebar.setFixedHeight(height)

        if self.sb_anim.state() != QAbstractAnimation.State.Running:
            x = 0 if self.sidebar_open else -SIDEBAR_W - 4
            self.sidebar.move(x, 0)

    def _poll_cursor(self):
        """Show when the pointer touches the far-left edge, hide when it leaves."""
        if self.sidebar_pinned or not self.isVisible() or self.isMinimized():
            return

        if (
            QApplication.activeModalWidget() is not None
            or QApplication.activePopupWidget() is not None
        ):
            self._leave_ticks = 0
            return

        local = self.root.mapFromGlobal(QCursor.pos())
        inside_height = 0 <= local.y() <= self.root.height()
        active = self.isActiveWindow()

        if not self.sidebar_open:
            at_edge = (
                active and inside_height and -1 <= local.x() <= EDGE_PX
            )
            self._edge_ticks = self._edge_ticks + 1 if at_edge else 0

            if self._edge_ticks >= 3:  # ~90 ms dwell, like a taskbar
                self._edge_ticks = 0
                self.show_sidebar()
            return

        over = (
            active
            and inside_height
            and 0 <= local.x() <= SIDEBAR_W + HIDE_SLACK
        )

        if self.search.hasFocus() and self.search.text():
            over = True  # keep it open while searching

        if over:
            self._leave_ticks = 0
        else:
            self._leave_ticks += 1
            if self._leave_ticks >= 7:  # ~200 ms grace
                self.hide_sidebar()

    def show_sidebar(self):
        self._leave_ticks = 0

        if self.sidebar_open:
            return

        self.sidebar_open = True
        self.edge.active = False
        self.edge.update()

        self.sidebar.show()
        self.sidebar.raise_()
        self.toast.raise_()

        self.sb_anim.stop()
        self.sb_anim.setStartValue(self.sidebar.pos())
        self.sb_anim.setEndValue(QPoint(0, 0))
        self.sb_anim.start()

    def hide_sidebar(self):
        if self.sidebar_pinned or not self.sidebar_open:
            return

        self.sidebar_open = False
        self.edge.active = True
        self.edge.update()
        self.search.clearFocus()

        self.sb_anim.stop()
        self.sb_anim.setStartValue(self.sidebar.pos())
        self.sb_anim.setEndValue(QPoint(-SIDEBAR_W - 4, 0))
        self.sb_anim.start()

    def _sidebar_anim_done(self):
        if not self.sidebar_open:
            self.sidebar.hide()

    def toggle_pin(self):
        self.sidebar_pinned = not self.sidebar_pinned

        self.pin_button.setProperty("on", self.sidebar_pinned)
        refresh_style(self.pin_button)
        self.set_icon(
            self.pin_button, "pin",
            "text" if self.sidebar_pinned else "muted", 16,
        )

        self.margin_anim.stop()
        self.margin_anim.setStartValue(
            self.root_layout.contentsMargins().left()
        )
        self.margin_anim.setEndValue(SIDEBAR_W if self.sidebar_pinned else 0)
        self.margin_anim.start()

        if self.sidebar_pinned:
            self.show_sidebar()
        else:
            self._leave_ticks = 0

    def focus_search(self):
        self.show_sidebar()
        self.search.setFocus()
        self.search.selectAll()

    # --------------------------------------------------------
    # THEME & TEXT SIZE
    # --------------------------------------------------------

    def toggle_theme(self):
        name = "light" if self.store.get("theme", "dark") == "dark" else "dark"
        self.store.set("theme", name)
        set_theme(name)

        app = QApplication.instance()
        apply_palette(app)
        app.setStyleSheet(build_style())

        self.set_icon(
            self.theme_button, "sun" if name == "light" else "moon", "text", 19
        )
        self.retheme_icons()

        for card in self.welcome_cards:
            card.retheme()

        self.refresh_model_chip()
        self.load_conversations(select_id=self.conversation_id)

        if not self.busy and self.conversation_id is not None:
            self.render_conversation()

        for widget in self.findChildren(QWidget):
            widget.update()

        self.toast.pop("Light theme" if name == "light" else "Dark theme")

    def zoom(self, direction):
        if direction == 0:
            UI["font_px"] = 15
        else:
            UI["font_px"] = max(12, min(21, UI["font_px"] + direction))

        self.store.set("font_px", UI["font_px"])
        self.toast.pop(f"Text size {UI['font_px']}")

        if not self.busy and self.conversation_id is not None:
            self.render_conversation()

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    def refresh_model_chip(self):
        if self.ollama_ok is None:
            color = T["muted"]
        elif self.ollama_ok:
            color = T["ok"]
        else:
            color = T["danger"]

        self.model_chip.setText(
            f"<span style='color:{color};'>●</span>&nbsp;&nbsp;"
            f"{html.escape(self.model_name)}"
        )

    def start_ping(self):
        self._ping = PingWorker(self)
        self._ping.result.connect(self._set_ollama_status)

        self._ping_timer = QTimer(self)
        self._ping_timer.setInterval(15000)
        self._ping_timer.timeout.connect(self._ping_tick)
        self._ping_timer.start()

        self._ping_tick()

    def _ping_tick(self):
        if not self._ping.isRunning():
            self._ping.start()

    def _set_ollama_status(self, ok):
        self.ollama_ok = ok
        self.refresh_model_chip()

        if ok:
            self.side_status.setText("●  Ollama connected")
        else:
            self.side_status.setText("●  Ollama offline — start it")

    # --------------------------------------------------------
    # PROJECTS
    # --------------------------------------------------------

    def load_projects(self, select_id=None):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()

        for project_id, name, _instructions in get_projects():
            self.project_combo.addItem(name, project_id)

        selected_index = 0

        if select_id:
            for index in range(self.project_combo.count()):
                if self.project_combo.itemData(index) == select_id:
                    selected_index = index
                    break

        if self.project_combo.count():
            self.project_combo.setCurrentIndex(selected_index)
            self.current_project_id = self.project_combo.currentData()

        self.project_combo.blockSignals(False)
        self.update_subtitle()

    def update_subtitle(self):
        self.page_sub.setText(
            self.project_combo.currentText() or "Workspace"
        )

    def project_changed(self, index):
        if index < 0 or self.busy:
            return

        project_id = self.project_combo.itemData(index)

        if not project_id or project_id == self.current_project_id:
            return

        self.current_project_id = project_id
        self.new_chat()

    def new_project(self):
        name, accepted = QInputDialog.getText(
            self, "Create project", "Project name:"
        )

        if not accepted:
            return

        name = name.strip()

        if not name:
            QMessageBox.information(
                self, "Project name required",
                "Please enter a project name."
            )
            return

        if any(
            existing.casefold() == name.casefold()
            for _, existing, _ in get_projects()
        ):
            QMessageBox.information(
                self, "Project already exists",
                "Choose a different project name."
            )
            return

        project_id = create_project(name)
        self.load_projects(select_id=project_id)
        self.current_project_id = project_id
        self.new_chat()
        self.toast.pop(f"Project “{name}” created")

    def edit_project_instructions(self):
        project = next(
            (
                item for item in get_projects()
                if item[0] == self.current_project_id
            ),
            None,
        )

        if not project:
            return

        project_id, project_name, instructions = project

        dialog = QDialog(self)
        dialog.setWindowTitle(f"{project_name} — Instructions")
        dialog.resize(560, 440)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        heading = QLabel(f"Instructions for {project_name}")
        heading.setObjectName("dialogTitle")
        layout.addWidget(heading)

        description = QLabel(
            "Set guidance for how the AI should respond in this project."
        )
        description.setWordWrap(True)
        description.setObjectName("muted")
        layout.addWidget(description)

        editor = QTextEdit()
        editor.setPlaceholderText(
            "Explain concepts step by step.\n"
            "Use beginner-friendly language.\n"
            "Give practical examples."
        )
        editor.setPlainText(instructions)
        layout.addWidget(editor, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            update_project(project_id, project_name, editor.toPlainText())
            self.toast.pop("Project instructions saved")

    # --------------------------------------------------------
    # CONVERSATION HISTORY
    # --------------------------------------------------------

    def load_conversations(self, select_id=None):
        self.history.clear()
        hidden = self.store.hidden_ids()
        pinned_items, normal_items = [], []

        for conversation_id, title, _project_id, _updated in (
            get_conversations(self.current_project_id)
        ):
            if str(conversation_id) in hidden:
                continue

            display_title = (title or "").strip() or "New conversation"

            if display_title == "New conversation":
                messages = get_messages(conversation_id)
                first_user = next(
                    (c for role, c in messages if role == "user"), None
                )

                if not first_user:
                    continue  # hide empty chats

                display_title = first_user[:35]
                if len(first_user) > 35:
                    display_title += "…"

            item = QListWidgetItem(display_title)
            item.setToolTip(display_title)
            item.setData(Qt.ItemDataRole.UserRole, conversation_id)

            if self.store.is_pinned(conversation_id):
                item.setIcon(make_icon("pin", "muted", 14))
                pinned_items.append(item)
            else:
                normal_items.append(item)

        selected_item = None

        for item in pinned_items + normal_items:
            self.history.addItem(item)

            if item.data(Qt.ItemDataRole.UserRole) == select_id:
                selected_item = item

        if selected_item:
            self.history.setCurrentItem(selected_item)

        self.apply_history_filter()

    def apply_history_filter(self, *_args):
        needle = self.search.text().strip().casefold()

        for index in range(self.history.count()):
            item = self.history.item(index)
            item.setHidden(
                bool(needle) and needle not in item.text().casefold()
            )

    def title_for(self, cid):
        for index in range(self.history.count()):
            item = self.history.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == cid:
                return item.text()
        return self.page_title.text()

    def history_menu(self, position):
        item = self.history.itemAt(position)

        if not item:
            return

        cid = item.data(Qt.ItemDataRole.UserRole)
        pinned = self.store.is_pinned(cid)

        menu = QMenu(self)
        project_action = menu.addAction(
            make_icon("folder", "text", 16), "Add to project"
        )

        
        rename_action = menu.addAction(make_icon("edit", "text", 16), "Rename")
        pin_action = menu.addAction(
            make_icon("pin", "text", 16),
            "Unpin" if pinned else "Pin to top",
        )
        export_action = menu.addAction(
            make_icon("download", "text", 16), "Export as Markdown"
        )
        menu.addSeparator()
        bin_action = menu.addAction(
            make_icon("trash", "danger", 16), "Move to bin"
        )

        chosen = menu.exec(self.history.viewport().mapToGlobal(position))

        if chosen is None:
            return

        if chosen is rename_action:
            new_title, accepted = QInputDialog.getText(
                self, "Rename chat", "Chat title:", text=item.text()
            )
            new_title = new_title.strip()

            if accepted and new_title:
                update_conversation_title(cid, new_title)

                if cid == self.conversation_id:
                    self.page_title.setText(new_title)

                self.load_conversations(select_id=self.conversation_id)

        elif chosen is pin_action:
            self.store.toggle_pin(cid)
            self.load_conversations(select_id=self.conversation_id)

        
        elif chosen is export_action:
            self.export_chat(cid, item.text())

        elif chosen is project_action:
            projects = get_projects()

            if not projects:
                self.toast.pop("No projects available")
                return

            project_names = [
                name for _project_id, name, _instructions in projects
            ]

            selected_name, accepted = QInputDialog.getItem(
                self,
                "Add to project",
                "Choose a project:",
                project_names,
                0,
                False,
            )

            if accepted and selected_name:
                selected_project_id = next(
                    (
                        project_id
                        for project_id, name, _instructions in projects
                        if name == selected_name
                    ),
                    None,
                )

                if selected_project_id:
                    move_conversation_to_project(
                        cid, selected_project_id
                    )

                    for index in range(self.project_combo.count()):
                        if (
                            self.project_combo.itemData(index)
                            == selected_project_id
                        ):
                            self.project_combo.blockSignals(True)
                            self.project_combo.setCurrentIndex(index)
                            self.project_combo.blockSignals(False)
                            break

                    self.current_project_id = selected_project_id
                    self.update_subtitle()
                    self.load_conversations(select_id=cid)
                    self.toast.pop("Conversation added to project")

        elif chosen is bin_action:
            self.trash_conversation(cid)


    def delete_selected_history(self):
        item = self.history.currentItem()

        if item is not None:
            self.trash_conversation(item.data(Qt.ItemDataRole.UserRole))

    def new_chat(self):
        if self.busy:
            return

        self.conversation_id = None  # created on the first message
        self.current_answer = ""

        self.clear_messages()
        self.stack.setCurrentWidget(self.welcome)

        self.page_title.setText("New chat")
        self.update_subtitle()
        self.load_conversations()
        self.history.clearSelection()
        self.update_actions()

        self.status.setText("Ready")
        self.message_input.setFocus()

    def open_conversation(self, item):
        if self.busy:
            return

        self.conversation_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_answer = ""

        self.page_title.setText(item.text())
        self.render_conversation()
        self.update_actions()
        self.status.setText("Conversation loaded")
        self.message_input.setFocus()

    def update_actions(self):
        has_chat = self.conversation_id is not None
        self.export_button.setEnabled(has_chat)
        self.delete_button.setEnabled(has_chat and not self.busy)

    # --------------------------------------------------------
    # BIN  (soft delete, kept for 30 days)
    # --------------------------------------------------------

    def delete_current_chat(self):
        if self.conversation_id is not None:
            self.trash_conversation(self.conversation_id)

    def trash_conversation(self, cid):
        if cid is None:
            return

        if self.busy and cid == self.conversation_id:
            self.toast.pop("Wait for the answer to finish first")
            return

        title = self.title_for(cid)
        self.store.trash_chat(cid, title)

        if cid == self.conversation_id:
            self.new_chat()
        else:
            self.load_conversations(select_id=self.conversation_id)

        self.update_bin_badge()
        self.toast.pop(f"Moved to bin · kept {TRASH_DAYS} days")

    def restore_chat(self, cid):
        self.store.restore(cid)
        self.load_conversations(select_id=self.conversation_id)
        self.update_bin_badge()

    def purge_chat(self, cid):
        delete_function = getattr(
            database_module, "delete_conversation", None
        )

        if delete_function is not None:
            try:
                delete_function(cid)
            except Exception:
                pass

        self.store.forget(cid)
        self.load_conversations(select_id=self.conversation_id)
        self.update_bin_badge()

    def purge_expired(self):
        for cid in self.store.expired():
            self.purge_chat(cid)

    def update_bin_badge(self):
        count = len(self.store.data["trash"])
        self.bin_button.setText("  Bin" + (f"   ·   {count}" if count else ""))

    def open_bin(self):
        self.purge_expired()
        dialog = BinDialog(self)
        dialog.exec()
        self.load_conversations(select_id=self.conversation_id)

    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------

    def export_chat(self, cid=None, title=None):
        if not isinstance(cid, (int, str)) or isinstance(cid, bool):
            cid = self.conversation_id
            title = self.page_title.text()

        if cid is None:
            self.toast.pop("Open a chat to export it")
            return

        messages = get_messages(cid)

        if not messages:
            self.toast.pop("Nothing to export yet")
            return

        title = title or "chat"
        safe = re.sub(r'[\\/:*?"<>|]+', "", title).strip() or "chat"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export chat",
            os.path.join(os.path.expanduser("~"), safe + ".md"),
            "Markdown (*.md);;Text (*.txt)",
        )

        if not path:
            return

        lines = [f"# {title}", ""]

        for role, content in messages:
            who = "You" if role == "user" else "Ahmad Intelligence"
            lines += [f"**{who}**", "", content, "", "---", ""]

        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines))
            self.toast.pop("Chat exported")
        except OSError as error:
            QMessageBox.warning(self, "Export failed", str(error))

    # --------------------------------------------------------
    # CHAT DISPLAY
    # --------------------------------------------------------

    def clear_messages(self):
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.hide()
                widget.deleteLater()

        self.stream_bubble = None

    def add_message(self, role, content, animate=False):
        if role == "user":
            widget = UserBubble(content)
        else:
            widget = AssistantBubble(content)
            widget.finish()
            widget.copy_requested.connect(self.copy_text)

        self.msg_layout.insertWidget(self.msg_layout.count() - 1, widget)

        if animate:
            fade_in(widget)

        return widget

    def render_conversation(self):
        self.clear_messages()

        messages = (
            get_messages(self.conversation_id)
            if self.conversation_id is not None
            else []
        )

        if not messages:
            self.stack.setCurrentWidget(self.welcome)
            return

        self.stack.setCurrentWidget(self.scroll)
        self.stick_to_bottom = True

        for role, content in messages:
            self.add_message(role, content)

        QTimer.singleShot(0, self.scroll_to_bottom)
        QTimer.singleShot(120, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def jump_to_latest(self):
        self.stick_to_bottom = True
        self.scroll_to_bottom()

    def _range_changed(self, _minimum, maximum):
        if self.stick_to_bottom:
            self.scroll.verticalScrollBar().setValue(maximum)

    def _scroll_moved(self, value):
        bar = self.scroll.verticalScrollBar()
        self.stick_to_bottom = value >= bar.maximum() - 48
        self.scroll.jump.setVisible(
            not self.stick_to_bottom and bar.maximum() > 0
        )
        self.scroll.jump.raise_()

    def copy_text(self, text):
        QApplication.clipboard().setText(text)
        self.toast.pop("Copied to clipboard")

    def use_prompt(self, prompt):
        self.message_input.setPlainText(prompt)
        self.message_input.setFocus()
        cursor = self.message_input.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.message_input.setTextCursor(cursor)

    # --------------------------------------------------------
    # SENDING MESSAGES
    # --------------------------------------------------------

    def _update_send_state(self):
        if not self.busy:
            self.send_button.setEnabled(
                bool(self.message_input.toPlainText().strip())
            )

    def set_busy(self, busy):
        self.busy = busy

        self.new_chat_button.setEnabled(not busy)
        self.project_combo.setEnabled(not busy)
        self.composer.set_glowing(busy)

        if busy:
            self.send_button.setObjectName("stopBtn")
            self.set_icon(self.send_button, "stop", "accent_text", 18)
            self.send_button.setToolTip("Stop generating (Esc)")
            self.send_button.setEnabled(True)
        else:
            self.send_button.setObjectName("sendBtn")
            self.set_icon(self.send_button, "send", "accent_text", 18)
            self.send_button.setToolTip("Send")
            self._update_send_state()

        refresh_style(self.send_button)
        self.update_actions()

    def on_send_clicked(self):
        if self.busy:
            self.stop_generation()
        else:
            self.send_message()

    def stop_generation(self):
        if self.busy and self.worker is not None:
            self.worker.stop()
            self.status.setText("Stopping…")

    def send_message(self):
        if self.busy:
            self.toast.pop("Still answering — press Stop first")
            return

        question = self.message_input.toPlainText().strip()

        if not question:
            return

        self.message_input.clear()

        if self.conversation_id is None:
            self.conversation_id = create_conversation(
                self.current_project_id
            )

        previous_messages = get_messages(self.conversation_id)
        first_user_message = not any(
            role == "user" for role, _ in previous_messages
        )

        save_message(self.conversation_id, "user", question)

        if first_user_message:
            title = question[:35]
            if len(question) > 35:
                title += "…"

            update_conversation_title(self.conversation_id, title)
            self.page_title.setText(title)

        self.load_conversations(select_id=self.conversation_id)

        if not previous_messages:
            self.clear_messages()

        self.stack.setCurrentWidget(self.scroll)
        self.stick_to_bottom = True

        self.add_message("user", question, animate=True)

        self.stream_bubble = AssistantBubble(streaming=True)
        self.stream_bubble.copy_requested.connect(self.copy_text)
        self.msg_layout.insertWidget(
            self.msg_layout.count() - 1, self.stream_bubble
        )
        fade_in(self.stream_bubble)

        messages = [
            {"role": role, "content": content}
            for role, content in get_messages(self.conversation_id)
        ]
        instructions = get_project_instructions_for_conversation(
            self.conversation_id
        )

        self.current_answer = ""
        self.stream_dirty = False
        self.t_start = time.time()
        self.set_busy(True)
        self.status.setText("Thinking…")

        self.worker = AIWorker(messages, instructions, self.model_name)
        self._workers.add(self.worker)
        self.worker.finished.connect(
            lambda w=self.worker: self._worker_done(w)
        )
        self.worker.token_received.connect(self.on_token)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

        self.stream_timer.start()
        QTimer.singleShot(0, self.scroll_to_bottom)

    def _worker_done(self, worker):
        self._workers.discard(worker)
        worker.deleteLater()

    def on_token(self, token):
        if not self.current_answer:
            self.status.setText("Writing…")

        self.current_answer += token
        self.stream_dirty = True

    def _flush_stream(self):
        if self.stream_dirty and self.stream_bubble is not None:
            self.stream_bubble.set_text(self.current_answer)
            self.stream_dirty = False

    def _end_stream(self):
        self.stream_timer.stop()
        self.stream_dirty = False

    def _drop_stream_bubble(self):
        if self.stream_bubble is not None:
            self.stream_bubble.hide()
            self.stream_bubble.deleteLater()
            self.stream_bubble = None

    def on_completed(self, answer):
        self._end_stream()
        elapsed = time.time() - self.t_start

        if answer.strip():
            save_message(self.conversation_id, "assistant", answer)

            if self.stream_bubble is not None:
                self.stream_bubble.set_text(answer)
                self.stream_bubble.finish()
                self.stream_bubble = None

            self.status.setText(f"Ready  ·  answered in {elapsed:.1f}s")
        else:
            self._drop_stream_bubble()
            self.status.setText("Stopped")
            self.toast.pop("Stopped")

        self.current_answer = ""
        self.load_conversations(select_id=self.conversation_id)
        self.finish_response()

    def on_failed(self, error):
        self._end_stream()

        if self.current_answer.strip():
            save_message(
                self.conversation_id, "assistant", self.current_answer
            )

            if self.stream_bubble is not None:
                self.stream_bubble.set_text(self.current_answer)
                self.stream_bubble.finish()
                self.stream_bubble = None
        else:
            self._drop_stream_bubble()

        note = ErrorNote(
            "Ahmad Intelligence couldn't complete that request.\n\n"
            "Check that Ollama is running and the model is installed.\n\n"
            f"Details: {error}"
        )
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, note)
        fade_in(note)

        self.current_answer = ""
        self.ollama_ok = False
        self.refresh_model_chip()
        self.status.setText("AI unavailable — check Ollama")
        self.finish_response()

    def finish_response(self):
        self.set_busy(False)
        self.worker = None
        self.message_input.setFocus()

    # --------------------------------------------------------
    # MODEL SETTINGS
    # --------------------------------------------------------

    def open_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Ahmad Intelligence settings")
        dialog.resize(500, 270)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        heading = QLabel("Model settings")
        heading.setObjectName("dialogTitle")
        layout.addWidget(heading)

        description = QLabel(
            "Select a model already installed in your local Ollama setup."
        )
        description.setWordWrap(True)
        description.setObjectName("muted")
        layout.addWidget(description)

        form = QFormLayout()

        model_combo = QComboBox()
        model_combo.setEditable(True)
        model_combo.addItem(self.model_name)

        try:
            response = requests.get(ollama_base() + "/api/tags", timeout=3)
            response.raise_for_status()

            names = [
                item.get("name", "")
                for item in response.json().get("models", [])
                if item.get("name")
            ]

            if names:
                model_combo.clear()
                model_combo.addItems(names)

                if self.model_name in names:
                    model_combo.setCurrentText(self.model_name)
                else:
                    model_combo.setCurrentText(names[0])

        except requests.RequestException:
            pass

        form.addRow("Ollama model", model_combo)
        layout.addLayout(form)

        note = QLabel("The model must already be downloaded in Ollama.")
        note.setObjectName("hint")
        layout.addWidget(note)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            chosen = model_combo.currentText().strip()

            if chosen:
                self.model_name = chosen
                self.refresh_model_chip()
                self.toast.pop(f"Model: {chosen}")

    # --------------------------------------------------------
    # SHUTDOWN
    # --------------------------------------------------------

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)

        if self._ping.isRunning():
            self._ping.wait(2500)

        super().closeEvent(event)


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Ahmad Intelligence")
    app.setStyle("Fusion")

    window = AhmadIntelligence()
    window.show()

    sys.exit(app.exec())