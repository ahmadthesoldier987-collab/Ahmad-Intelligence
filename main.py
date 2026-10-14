import sys
import os
import re
import html
import json
import math
import time
from random import Random

import requests
from google import genai
from google.genai import types

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
    QRect,
    QRectF,
    QSize,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QIcon,
    QPixmap,
    QPainter,
    QPainterPath,
    QPolygonF,
    QConicalGradient,
    QLinearGradient,
    QRadialGradient,
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
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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
    QSizeGrip,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QLineEdit as _QLineEdit,
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
FONT_DIR = os.path.join(APP_DIR, "fonts")   # drop .ttf / .otf files here
TRASH_DAYS = 30

SIDEBAR_W = 296
HISTORY_LIMIT = 24          # how many past messages are sent to the AI
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"

# Fonts offered at the top of the font picker (only installed ones appear).
# Every other font installed on the computer is listed below them.
FONT_CHOICES = [
    "Inter", "Space Grotesk", "Sora", "Outfit", "Manrope", "DM Sans",
    "Plus Jakarta Sans", "Segoe UI", "Roboto", "Open Sans", "Lato",
    "Montserrat", "Poppins", "Nunito", "Source Sans 3", "Source Sans Pro",
    "Fira Sans", "IBM Plex Sans", "Work Sans", "Noto Sans", "Ubuntu",
    "Cantarell", "DejaVu Sans", "Liberation Sans", "Helvetica", "Arial",
    "Verdana", "Tahoma", "Trebuchet MS", "Calibri", "Orbitron", "Exo 2",
    "Rajdhani", "Oxanium", "Chakra Petch", "Audiowide", "Georgia",
    "Merriweather", "Lora", "Playfair Display", "Noto Serif", "DejaVu Serif",
    "Liberation Serif", "Times New Roman", "Palatino Linotype", "Fira Code",
    "JetBrains Mono", "Source Code Pro", "DejaVu Sans Mono", "Ubuntu Mono",
    "Consolas", "Courier New", "Comic Sans MS",
]

FONT = {"family": ""}       # current UI font family


def ollama_base():
    if "/api/" in OLLAMA_URL:
        return OLLAMA_URL.split("/api/")[0]
    return "http://localhost:11434"


def refresh_style(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


# ============================================================
# FONT HELPERS
# ============================================================

def installed_families():
    try:
        families = QFontDatabase.families()
    except TypeError:
        families = QFontDatabase().families()

    clean = {name for name in families if name and not name.startswith("@")}
    return sorted(clean, key=str.casefold)


def load_font_files(paths):
    """Register extra font files so they show up in the font picker."""
    found = []

    if os.path.isdir(FONT_DIR):
        for name in sorted(os.listdir(FONT_DIR)):
            if name.lower().endswith((".ttf", ".otf", ".ttc")):
                found.append(os.path.join(FONT_DIR, name))

    for path in list(paths or []) + found:
        if os.path.isfile(path):
            QFontDatabase.addApplicationFont(path)


def pick_default_font():
    installed = set(installed_families())

    for name in (
        "Inter", "Space Grotesk", "Sora", "Outfit", "Manrope",
        "Segoe UI", "Ubuntu", "Noto Sans", "DejaVu Sans",
    ):
        if name in installed:
            return name

    return QApplication.font().family()


# ============================================================
# THEMES  (dark / light  +  neon gradient palettes)
# ============================================================

def _rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(
        round(x + (y - x) * t) for x, y in zip(ra, rb)
    )


def luminance(color):
    r, g, b = [v / 255.0 for v in _rgb(color)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def rgba(color, alpha):
    """CSS rgba() string, alpha 0-255."""
    r, g, b = _rgb(color)
    return f"rgba({r}, {g}, {b}, {int(alpha)})"


def qcolor(color, alpha=1.0):
    c = QColor(color)
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


BASES = {
    "dark": dict(
        bg="#05060d", panel="#0d0f1a", panel2="#131628", hover="#1b1f36",
        border="#242a48", border_hi="#363e66", text="#eceffd",
        muted="#98a0c0", faint="#5c6486", danger="#ff6b81", ok="#4ade80",
        code_bg="#080a14", code_text="#d3d9f5",
        glass="rgba(255, 255, 255, 14)",
        glass_hi="rgba(255, 255, 255, 26)",
        glass_border="rgba(255, 255, 255, 32)",
        glass_border_hi="rgba(255, 255, 255, 64)",
        bar_bg="rgba(5, 6, 13, 110)",
        side_bg="rgba(8, 10, 24, 150)",
    ),
    "light": dict(
        bg="#eef0fa", panel="#ffffff", panel2="#f3f5fc", hover="#e6e9f6",
        border="#d9ddef", border_hi="#bcc3df", text="#12142a",
        muted="#5a6188", faint="#9aa1c4", danger="#d6334f", ok="#14a05a",
        code_bg="#e9ecf8", code_text="#242a4a",
        glass="rgba(255, 255, 255, 150)",
        glass_hi="rgba(255, 255, 255, 215)",
        glass_border="rgba(90, 100, 160, 60)",
        glass_border_hi="rgba(90, 100, 160, 115)",
        bar_bg="rgba(255, 255, 255, 110)",
        side_bg="rgba(255, 255, 255, 135)",
    ),
}

# Parameters used when painting glass panels in code.
GLASS = {
    "dark": dict(base="#ffffff", top=0.085, bot=0.032,
                 edge="#ffffff", b_hi=0.30, b_lo=0.07),
    "light": dict(base="#ffffff", top=0.88, bot=0.62,
                  edge="#7f8ab8", b_hi=0.48, b_lo=0.20),
}

# Three-colour neon gradients.
NEON = {
    "Aurora": ("#22d3ee", "#8b5cf6", "#f472b6"),
    "Cyber": ("#00f5ff", "#6d28d9", "#ff2bd6"),
    "Sunset": ("#fbbf24", "#fb7185", "#a855f7"),
    "Matrix": ("#a3e635", "#22c55e", "#14b8a6"),
    "Ocean": ("#38bdf8", "#6366f1", "#22d3ee"),
    "Mono": ("#f1f5f9", "#94a3b8", "#e2e8f0"),
}

T = {}                              # current theme (mutated in place)
MODE = {"name": "dark", "accent": "Aurora"}
UI = {"font_px": 15}                # chat text size


def neon_colors(name, mode):
    colors = NEON.get(name, NEON["Aurora"])

    if mode == "light":
        colors = tuple(mix(c, "#000000", 0.22) for c in colors)

    return colors


def set_theme(mode, accent="Aurora"):
    mode = mode if mode in BASES else "dark"
    accent = accent if accent in NEON else "Aurora"
    g1, g2, g3 = neon_colors(accent, mode)

    theme = dict(BASES[mode])
    theme["g1"], theme["g2"], theme["g3"] = g1, g2, g3
    theme["accent"] = g1
    theme["accent_hover"] = mix(
        g1, "#ffffff" if mode == "dark" else "#000000", 0.2
    )
    theme["accent_deep"] = mix(g2, "#000000", 0.4)
    theme["accent_text"] = (
        "#ffffff" if luminance(mix(g1, g2, 0.5)) < 0.5 else "#06070d"
    )
    theme["accent_soft"] = mix(theme["panel"], g1, 0.16)
    theme["user_bg"] = mix(theme["panel2"], g2, 0.2)
    theme["select"] = mix(theme["panel"], g2, 0.4)

    theme["primary_grad"] = (
        "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        f"stop:0 {g1}, stop:1 {g2})"
    )
    theme["sel_grad"] = (
        "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        f"stop:0 {rgba(g1, 70)}, stop:1 {rgba(g2, 18)})"
    )
    theme["hov_grad"] = (
        "qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        f"stop:0 {rgba(g1, 30)}, stop:1 {rgba(g2, 6)})"
    )

    T.clear()
    T.update(theme)
    MODE["name"] = mode
    MODE["accent"] = accent


STYLE_TEMPLATE = """
QMainWindow { background-color: @bg@; }

QWidget {
    color: @text@;
    font-family: "@font@", "Segoe UI", "Ubuntu", "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 13px;
}

QToolTip {
    background-color: @panel2@;
    color: @text@;
    border: 1px solid @border_hi@;
    border-radius: 6px;
    padding: 5px 9px;
}

QWidget#chatContent { background: transparent; }
QScrollArea { background: transparent; border: none; }
QStackedWidget { background: transparent; }

/* ---------- Title bar ---------- */
QFrame#titleBar {
    background-color: @bar_bg@;
    border: none;
    border-bottom: 1px solid @glass_border@;
}
QLabel#titleText { font-weight: 600; color: @muted@; font-size: 12px; }

QPushButton#winBtn, QPushButton#winClose {
    background-color: transparent;
    border: none;
    border-radius: 0px;
    padding: 0;
    min-width: 46px; max-width: 46px;
    min-height: 40px; max-height: 40px;
}
QPushButton#winBtn:hover { background-color: @glass_hi@; }
QPushButton#winClose:hover { background-color: #e81123; }

/* ---------- Sidebar ---------- */
QFrame#sidebar {
    background-color: @side_bg@;
    border: none;
    border-right: 1px solid @glass_border@;
}

QLabel#brand { font-size: 15px; font-weight: 700; color: @text@; }
QLabel#brandSub { font-size: 11px; color: @muted@; }

QLabel#section {
    color: @faint@;
    font-size: 10px;
    font-weight: 700;
    padding-top: 6px;
}

QLabel#title { font-size: 18px; font-weight: 700; color: @text@; }
QLabel#greeting { font-size: 14px; font-weight: 600; color: @accent@; }
QLabel#heroSub { font-size: 14px; color: @muted@; }
QLabel#muted { color: @muted@; font-size: 12px; }
QLabel#status { color: @faint@; font-size: 11px; }
QLabel#hint { color: @faint@; font-size: 11px; }
QLabel#assistantName { color: @muted@; font-size: 12px; font-weight: 700; }
QLabel#dialogTitle { font-size: 20px; font-weight: 700; color: @text@; }
QLabel#pageTitle { font-size: 22px; font-weight: 700; color: @text@; }
QLabel#cardTitle { font-size: 14px; font-weight: 600; color: @text@; }
QLabel#cardDesc { font-size: 12px; color: @muted@; }
QLabel#binEmpty { color: @faint@; font-size: 13px; }
QLabel#okNote { color: @ok@; font-size: 12px; }
QLabel#warnNote { color: @danger@; font-size: 12px; }
QLabel#paletteHint { color: @faint@; font-size: 11px; }

QLabel#cardIcon {
    background: @primary_grad@;
    border: none;
    border-radius: 12px;
}

QLabel#chip {
    background-color: @glass@;
    border: 1px solid @glass_border@;
    border-radius: 14px;
    padding: 5px 13px;
    color: @muted@;
    font-size: 12px;
}
QLabel#chip:hover { border-color: @accent@; color: @text@; }

QLabel#localStatus {
    background-color: @glass@;
    border: 1px solid @glass_border@;
    border-radius: 12px;
    padding: 9px 11px;
    color: @muted@;
    font-size: 11px;
}

QLabel#fontPreview {
    background-color: @glass@;
    border: 1px solid @glass_border@;
    border-radius: 14px;
    padding: 14px 16px;
}

/* ---------- Buttons ---------- */
QPushButton {
    background-color: @glass@;
    color: @text@;
    border: 1px solid @glass_border@;
    border-radius: 11px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover { background-color: @glass_hi@; border-color: @glass_border_hi@; }
QPushButton:pressed { background-color: @border@; }
QPushButton:disabled {
    color: @faint@;
    background-color: @glass@;
    border-color: @glass_border@;
}

QPushButton#primary {
    background: @primary_grad@;
    color: @accent_text@;
    border: none;
    font-weight: 700;
    padding: 10px 14px;
}
QPushButton#primary:hover { background: @accent_hover@; }
QPushButton#primary:disabled { background-color: @glass@; color: @faint@; }

QPushButton#nav {
    background-color: transparent;
    border: 1px solid transparent;
    text-align: left;
    padding: 9px 10px;
    font-weight: 500;
    color: @text@;
}
QPushButton#nav:hover { background: @hov_grad@; border-color: @glass_border@; }

QPushButton#ghost {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 3px 8px;
    color: @muted@;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#ghost:hover { background-color: @glass_hi@; color: @text@; }

QPushButton#jump {
    background-color: @panel2@;
    border: 1px solid @border_hi@;
    border-radius: 18px;
    padding: 0;
}
QPushButton#jump:hover { background-color: @hover@; border-color: @accent@; }

QPushButton#danger { color: @danger@; }
QPushButton#danger:hover { border-color: @danger@; }

QPushButton#seg {
    background-color: @glass@;
    border: 1px solid @glass_border@;
    border-radius: 12px;
    padding: 10px 22px;
    color: @muted@;
    font-weight: 600;
}
QPushButton#seg:hover { background-color: @glass_hi@; color: @text@; }
QPushButton#seg:checked {
    background: @sel_grad@;
    border: 1px solid @accent@;
    color: @text@;
}

/* ---------- Inputs ---------- */
QLineEdit, QComboBox, QTextEdit {
    background-color: @glass@;
    color: @text@;
    border: 1px solid @glass_border@;
    border-radius: 11px;
    padding: 8px 12px;
    selection-background-color: @select@;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 1px solid @accent@; }

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
    padding: 0px;
    margin: 0px;
    selection-background-color: @select@;
}

QLineEdit#paletteInput {
    background: transparent;
    border: none;
    border-bottom: 1px solid @glass_border@;
    border-radius: 0px;
    padding: 14px 16px;
    font-size: 16px;
}

QSlider::groove:horizontal {
    height: 4px;
    background: @border_hi@;
    border-radius: 2px;
}
QSlider::sub-page:horizontal { background: @primary_grad@; border-radius: 2px; }
QSlider::handle:horizontal {
    background: @accent@;
    width: 16px; height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}

/* ---------- Chat ---------- */
QFrame#errorCard {
    background-color: @glass@;
    border: 1px solid @danger@;
    border-radius: 14px;
}

QLabel#toast {
    background: @primary_grad@;
    color: @accent_text@;
    border-radius: 14px;
    padding: 10px 22px;
    font-weight: 700;
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
    border-radius: 11px;
    padding: 9px 8px;
    margin: 1px 0;
}
QListWidget::item:hover { background: @hov_grad@; color: @text@; }
QListWidget::item:selected {
    background: @sel_grad@;
    color: @text@;
    border-color: @glass_border_hi@;
}

QFrame#settingsSide {
    background-color: @glass@;
    border: none;
    border-right: 1px solid @glass_border@;
}
QListWidget#settingsNav { color: @text@; }
QListWidget#settingsNav::item { padding: 11px 12px; margin: 2px 0; }

QListWidget#fontList {
    background-color: @glass@;
    border: 1px solid @glass_border@;
    border-radius: 14px;
    color: @text@;
    padding: 4px;
}
QListWidget#fontList::item { padding: 8px 10px; }

QListWidget#paletteList { color: @text@; padding: 6px; }
QListWidget#paletteList::item { padding: 11px 12px; }

/* ---------- Menus & dialogs ---------- */
QMenu {
    background-color: @panel@;
    border: 1px solid @border_hi@;
    border-radius: 12px;
    padding: 6px;
}
QMenu::item { padding: 8px 22px 8px 10px; border-radius: 8px; }
QMenu::item:selected { background-color: @hover@; }
QMenu::separator { height: 1px; background: @border@; margin: 5px 6px; }

QMessageBox, QInputDialog { background-color: @panel@; }

/* ---------- Scrollbars ---------- */
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px; }
QScrollBar::handle:vertical {
    background-color: @glass_border_hi@;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: @muted@; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""


def build_style():
    style = STYLE_TEMPLATE.replace(
        "@font@", (FONT["family"] or "Segoe UI").replace('"', "")
    )
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
        QPalette.ColorRole.ToolTipBase: T["panel2"],
        QPalette.ColorRole.ToolTipText: T["text"],
        QPalette.ColorRole.Highlight: T["select"],
        QPalette.ColorRole.HighlightedText: T["text"],
        QPalette.ColorRole.Link: T["accent"],
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
    elif name == "minimize":
        line(6, 17, 18, 17)
    elif name == "maximize":
        p.drawRoundedRect(QRectF(6, 6, 12, 12), 1.5, 1.5)
    elif name == "restore_win":
        p.drawRoundedRect(QRectF(5, 9, 10, 10), 1.5, 1.5)
        poly((9, 9), (9, 5), (19, 5), (19, 15), (15, 15))
    elif name == "gear":
        p.drawEllipse(QPointF(12, 12), 3.2, 3.2)
        p.drawEllipse(QPointF(12, 12), 7, 7)
        for i in range(8):
            a = i * math.pi / 4
            line(12 + 7 * math.cos(a), 12 + 7 * math.sin(a),
                 12 + 9.6 * math.cos(a), 12 + 9.6 * math.sin(a))
    elif name == "bolt":
        shape((13, 3), (6, 13), (11, 13), (10, 21), (18, 10), (13, 10))
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
    elif name == "type":
        line(5, 6, 19, 6); line(12, 6, 12, 19); line(9, 19, 15, 19)
    elif name == "palette":
        p.drawEllipse(QPointF(12, 12), 8, 8)
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(8.5, 10), 1.2, 1.2)
        p.drawEllipse(QPointF(12, 7.5), 1.2, 1.2)
        p.drawEllipse(QPointF(15.5, 10), 1.2, 1.2)
    elif name == "sparkle":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawPath(sparkle_path(12, 12, 9))
    elif name == "more":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        for y in (6, 12, 18):
            p.drawEllipse(QPointF(12, y), 1.8, 1.8)


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
# ANIMATION HELPERS
# ============================================================

def fade_in(widget, duration=300, delay=0):
    """Fade a widget in (optionally after a delay), then drop the effect."""
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)

    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def finished():
        try:
            widget.setGraphicsEffect(None)
        except RuntimeError:
            pass

    animation.finished.connect(finished)

    def start():
        try:
            animation.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        except RuntimeError:
            pass

    if delay > 0:
        QTimer.singleShot(delay, start)
    else:
        start()


class FadeDialog(QDialog):
    """Dialog with a glowing background that fades in when it opens."""

    def showEvent(self, event):
        super().showEvent(event)

        if not getattr(self, "_faded", False):
            self._faded = True
            self.setWindowOpacity(0.0)
            self._fade = QPropertyAnimation(self, b"windowOpacity", self)
            self._fade.setDuration(190)
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(1.0)
            self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade.start()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(T["panel"]))

        w, h = self.width(), self.height()

        glow = QRadialGradient(QPointF(w * 0.12, -h * 0.05), w * 0.85)
        glow.setColorAt(0.0, qcolor(T["g2"], 0.26))
        glow.setColorAt(1.0, qcolor(T["g2"], 0.0))
        painter.fillRect(self.rect(), QBrush(glow))

        glow2 = QRadialGradient(QPointF(w * 0.95, h * 1.05), w * 0.8)
        glow2.setColorAt(0.0, qcolor(T["g1"], 0.18))
        glow2.setColorAt(1.0, qcolor(T["g1"], 0.0))
        painter.fillRect(self.rect(), QBrush(glow2))


# ============================================================
# FUTURISTIC WIDGETS
# ============================================================

class Backdrop(QWidget):
    """Animated aurora background with floating particles."""

    resized = Signal()

    def __init__(self):
        super().__init__()
        self.t = 0.0
        self.animated = False
        self._cache = None

        rnd = Random(11)
        self.particles = [
            (rnd.random(), rnd.random(), rnd.uniform(0.8, 2.2),
             rnd.uniform(0.004, 0.016), rnd.uniform(0, 6.28))
            for _ in range(46)
        ]

        self.timer = QTimer(self)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self._tick)

    def set_animated(self, on):
        if on == self.animated:
            return

        self.animated = on

        if on:
            self.timer.start()
        else:
            self.timer.stop()

    def invalidate(self):
        self._cache = None
        self.update()

    def _tick(self):
        self.t += 0.045
        self._cache = None
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._cache = None
        self.resized.emit()

    def _build_cache(self):
        scale = 4
        w = max(2, self.width() // scale + 1)
        h = max(2, self.height() // scale + 1)

        pixmap = QPixmap(w, h)
        pixmap.fill(QColor(T["bg"]))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        dark = MODE["name"] == "dark"
        alpha = 0.36 if dark else 0.28
        big = max(w, h)
        t = self.t

        blobs = (
            (T["g1"], 0.18, 0.22, 0.16, 0.14, 0.62, 0.0),
            (T["g2"], 0.82, 0.18, 0.14, 0.18, 0.68, 2.1),
            (T["g3"], 0.70, 0.92, 0.18, 0.10, 0.60, 4.2),
            (T["g2"], 0.08, 0.90, 0.12, 0.14, 0.50, 1.3),
        )

        for color, bx, by, ax, ay, radius, phase in blobs:
            cx = w * (bx + ax * math.sin(t * 0.35 + phase))
            cy = h * (by + ay * math.cos(t * 0.29 + phase * 1.3))

            gradient = QRadialGradient(QPointF(cx, cy), big * radius)
            gradient.setColorAt(0.0, qcolor(color, alpha))
            gradient.setColorAt(1.0, qcolor(color, 0.0))
            painter.fillRect(QRectF(0, 0, w, h), QBrush(gradient))

        vignette = QRadialGradient(QPointF(w / 2, h / 2), big * 0.80)
        vignette.setColorAt(0.55, qcolor(T["bg"], 0.0))
        vignette.setColorAt(1.0, qcolor(T["bg"], 0.55 if dark else 0.35))
        painter.fillRect(QRectF(0, 0, w, h), QBrush(vignette))

        painter.end()
        return pixmap

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if self._cache is None:
            self._cache = self._build_cache()

        painter.drawPixmap(self.rect(), self._cache)

        # floating particles
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self.height()
        dark = MODE["name"] == "dark"
        base = "#ffffff" if dark else T["g2"]

        for px, py, radius, speed, phase in self.particles:
            x = (px + 0.02 * math.sin(self.t * 0.5 + phase)) % 1.0
            y = (py - self.t * speed) % 1.0
            twinkle = 0.5 + 0.5 * math.sin(self.t * 1.6 + phase)
            painter.setBrush(qcolor(base, 0.10 + 0.35 * twinkle))
            painter.drawEllipse(QPointF(x * w, y * h), radius, radius)


class GlassPanel(QFrame):
    """Frosted-glass panel with a gradient border and optional neon glow."""

    def __init__(self, radius=18, strength=1.0, tint=0.0, solid=0.0,
                 parent=None):
        super().__init__(parent)
        self.radius = radius
        self.strength = strength
        self.tint = tint
        self.solid = solid
        self.glow = 0.0

    def body_path(self):
        rect = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)
        return rect, path

    def draw_body(self, painter):
        rect, path = self.body_path()
        glass = GLASS[MODE["name"]]

        if self.solid > 0:
            painter.fillPath(path, qcolor(T["panel"], self.solid))

        fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        fill.setColorAt(
            0.0,
            qcolor(glass["base"], glass["top"] * self.strength + 0.05 * self.glow),
        )
        fill.setColorAt(1.0, qcolor(glass["base"], glass["bot"] * self.strength))
        painter.fillPath(path, QBrush(fill))

        if self.tint > 0:
            tint = QLinearGradient(rect.topLeft(), rect.bottomRight())
            tint.setColorAt(0.0, qcolor(T["g1"], self.tint * 0.55))
            tint.setColorAt(1.0, qcolor(T["g2"], self.tint * 0.35))
            painter.fillPath(path, QBrush(tint))

        return rect, path

    def draw_border(self, painter, rect, path):
        glass = GLASS[MODE["name"]]

        border = QLinearGradient(rect.topLeft(), rect.bottomRight())
        border.setColorAt(0.0, qcolor(glass["edge"], glass["b_hi"]))
        border.setColorAt(1.0, qcolor(glass["edge"], glass["b_lo"]))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(border), 1.1))
        painter.drawPath(path)

        if self.glow > 0.01:
            neon = QLinearGradient(rect.topLeft(), rect.bottomRight())
            neon.setColorAt(0.0, qcolor(T["g1"], 0.95 * self.glow))
            neon.setColorAt(0.5, qcolor(T["g2"], 0.85 * self.glow))
            neon.setColorAt(1.0, qcolor(T["g3"], 0.75 * self.glow))
            painter.setPen(QPen(QBrush(neon), 1.5))
            painter.drawPath(path)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect, path = self.draw_body(painter)
        self.draw_border(painter, rect, path)


class Orb(QWidget):
    """Glowing AI core: pulsing sphere inside a rotating neon ring."""

    def __init__(self, size=34, animated=False):
        super().__init__()
        self.setFixedSize(size, size)
        self.animated = animated
        self.t = 0.0

        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)

    def set_animated(self, on):
        self.animated = on

        if on and self.isVisible():
            self.timer.start()
        else:
            self.timer.stop()

        self.update()

    def _tick(self):
        self.t += 0.033
        self.update()

    def showEvent(self, event):
        if self.animated:
            self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        s = self.width()
        center = QPointF(s / 2, s / 2)
        pulse = 0.5 + 0.5 * math.sin(self.t * 2.2)

        # outer aura
        aura = QRadialGradient(center, s * 0.5)
        aura.setColorAt(0.45, qcolor(T["g2"], 0.30 + 0.25 * pulse))
        aura.setColorAt(1.0, qcolor(T["g2"], 0.0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(aura))
        painter.drawEllipse(center, s / 2, s / 2)

        # rotating neon ring
        radius = s * 0.34
        ring = QConicalGradient(center, -self.t * 110.0)
        ring.setColorAt(0.0, QColor(T["g1"]))
        ring.setColorAt(0.33, QColor(T["g2"]))
        ring.setColorAt(0.66, QColor(T["g3"]))
        ring.setColorAt(1.0, QColor(T["g1"]))
        painter.setPen(QPen(QBrush(ring), max(1.4, s * 0.06)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius * 1.18, radius * 1.18)

        # glowing core
        core_radius = radius * (0.82 + 0.05 * pulse)
        core = QRadialGradient(
            QPointF(center.x() - radius * 0.28, center.y() - radius * 0.34),
            core_radius * 1.6,
        )
        core.setColorAt(0.0, QColor(255, 255, 255, 245))
        core.setColorAt(0.30, QColor(T["g1"]))
        core.setColorAt(1.0, QColor(T["accent_deep"]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(core))
        painter.drawEllipse(center, core_radius, core_radius)


class ThinkingBars(QWidget):
    """Animated equaliser bars shown while the AI is thinking."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(60, 24)
        self.t = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self._tick)

    def _tick(self):
        self.t += 0.045
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

        for i in range(6):
            wave = 0.5 + 0.5 * math.sin(self.t * 7.0 - i * 0.9)
            height = 5 + 15 * wave
            color = QColor(mix(T["g1"], T["g3"], i / 5.0))
            painter.setBrush(color)
            painter.drawRoundedRect(
                QRectF(4 + i * 9, (24 - height) / 2, 4, height), 2, 2
            )


class GradientLabel(QWidget):
    """Text painted with the neon gradient."""

    def __init__(self, text, px=36, bold=True, center=True):
        super().__init__()
        self.text = text
        self.px = px
        self.bold = bold
        self.center = center
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        self.updateGeometry()

    def _font(self):
        self.ensurePolished()
        font = QFont(self.font())
        font.setPixelSize(self.px)
        font.setBold(self.bold)
        return font

    def set_text(self, text):
        self.text = text
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        metrics = QFontMetrics(self._font())
        return QSize(
            metrics.horizontalAdvance(self.text) + 10, metrics.height() + 10
        )

    def minimumSizeHint(self):
        return QSize(10, self.sizeHint().height())

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self._font())

        gradient = QLinearGradient(0, 0, max(1, self.width()), 0)
        gradient.setColorAt(0.0, QColor(T["g1"]))
        gradient.setColorAt(0.55, QColor(T["g2"]))
        gradient.setColorAt(1.0, QColor(T["g3"]))
        painter.setPen(QPen(QBrush(gradient), 1))

        flags = (
            Qt.AlignmentFlag.AlignCenter
            if self.center
            else Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        painter.drawText(QRectF(self.rect()), flags, self.text)


class NeonButton(QPushButton):
    """Gradient button with a soft glow that reacts to the mouse."""

    def __init__(self, text="", circular=False):
        super().__init__(text)
        self.circular = circular
        self.hover = 0.0
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.hover_anim = QVariantAnimation(self)
        self.hover_anim.setDuration(180)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.hover_anim.valueChanged.connect(self._set_hover)

        if not circular:
            self.setMinimumHeight(44)

    def _set_hover(self, value):
        self.hover = float(value)
        self.update()

    def _animate_to(self, target):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self.hover)
        self.hover_anim.setEndValue(target)
        self.hover_anim.start()

    def enterEvent(self, event):
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_to(0.0)
        super().leaveEvent(event)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        radius = rect.height() / 2 if self.circular else 13
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        enabled = self.isEnabled()
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if enabled:
            for width, alpha in ((8, 0.05), (5.5, 0.08), (3, 0.13)):
                painter.setPen(
                    QPen(
                        qcolor(T["g1"], alpha * (1.0 + 2.4 * self.hover)),
                        width,
                    )
                )
                painter.drawPath(path)

            fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
            fill.setColorAt(0.0, QColor(T["g1"]))
            fill.setColorAt(1.0, QColor(T["g2"]))
            painter.fillPath(path, QBrush(fill))

            gloss = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            gloss.setColorAt(0.0, QColor(255, 255, 255, 70))
            gloss.setColorAt(0.55, QColor(255, 255, 255, 0))
            painter.fillPath(path, QBrush(gloss))

            if self.isDown():
                painter.fillPath(path, QColor(0, 0, 0, 55))
        else:
            painter.fillPath(path, qcolor("#ffffff", 0.06))
            painter.setPen(QPen(qcolor("#ffffff", 0.10), 1))
            painter.drawPath(path)

        # icon + text
        text = self.text().strip()
        icon = self.icon()
        icon_size = self.iconSize()
        icon_w = icon_size.width() if not icon.isNull() else 0

        font = QFont(self.font())
        font.setBold(True)
        metrics = QFontMetrics(font)
        text_w = metrics.horizontalAdvance(text) if text else 0
        gap = 8 if (text_w and icon_w) else 0
        total = icon_w + gap + text_w
        x = rect.center().x() - total / 2.0

        if icon_w:
            target = QRect(
                int(x),
                int(rect.center().y() - icon_size.height() / 2),
                icon_size.width(),
                icon_size.height(),
            )
            mode = QIcon.Mode.Normal if enabled else QIcon.Mode.Disabled
            icon.paint(painter, target, Qt.AlignmentFlag.AlignCenter, mode)
            x += icon_w + gap

        if text_w:
            painter.setFont(font)
            painter.setPen(
                QColor(T["accent_text"] if enabled else T["faint"])
            )
            painter.drawText(
                QRectF(x, rect.top(), text_w + 6, rect.height()),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                text,
            )


class IconButton(QPushButton):
    """Round glass icon button with an animated hover glow."""

    def __init__(self):
        super().__init__()
        self.hover = 0.0
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.hover_anim = QVariantAnimation(self)
        self.hover_anim.setDuration(160)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.hover_anim.valueChanged.connect(self._set_hover)

    def _set_hover(self, value):
        self.hover = float(value)
        self.update()

    def _animate_to(self, target):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self.hover)
        self.hover_anim.setEndValue(target)
        self.hover_anim.start()

    def enterEvent(self, event):
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_to(0.0)
        super().leaveEvent(event)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = min(rect.width(), rect.height()) * 0.32
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        glass = GLASS[MODE["name"]]

        if self.hover > 0.01 and self.isEnabled():
            painter.fillPath(
                path, qcolor(glass["base"], 0.10 * self.hover + 0.02)
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(
                QPen(qcolor(T["g1"], 0.65 * self.hover), 1.2)
            )
            painter.drawPath(path)

        size = self.iconSize()
        target = QRect(0, 0, size.width(), size.height())
        target.moveCenter(self.rect().center())
        mode = QIcon.Mode.Normal if self.isEnabled() else QIcon.Mode.Disabled
        self.icon().paint(painter, target, Qt.AlignmentFlag.AlignCenter, mode)


class ChipLabel(QLabel):
    """A label that behaves like a button (used for the model chip)."""

    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ThemeSwatch(QPushButton):
    """Gradient preview tile used to pick a colour theme."""

    def __init__(self, name, mode):
        super().__init__()
        self.name = name
        self.mode = mode
        self.setCheckable(True)
        self.setFixedSize(136, 64)
        self.setToolTip(name)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        g1, g2, g3 = neon_colors(self.name, self.mode)
        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        path = QPainterPath()
        path.addRoundedRect(rect, 15, 15)

        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QColor(g1))
        gradient.setColorAt(0.55, QColor(g2))
        gradient.setColorAt(1.0, QColor(g3))
        painter.fillPath(path, QBrush(gradient))

        gloss = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gloss.setColorAt(0.0, QColor(255, 255, 255, 60))
        gloss.setColorAt(0.6, QColor(255, 255, 255, 0))
        painter.fillPath(path, QBrush(gloss))

        font = QFont(self.font())
        font.setBold(True)
        font.setPixelSize(13)
        painter.setFont(font)

        dark_text = luminance(mix(g1, g2, 0.5)) > 0.6
        painter.setPen(QColor("#06070d" if dark_text else "#ffffff"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.name)

        if self.isChecked():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(T["text"]), 2.2))
            painter.drawRoundedRect(
                QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5), 17, 17
            )


class ComposerFrame(GlassPanel):
    def __init__(self):
        super().__init__(radius=24, strength=1.2, solid=0.35)
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
        self.angle = (self.angle - 6.0) % 360
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect, path = self.draw_body(painter)

        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self.glowing:
            conic = QConicalGradient(rect.center(), self.angle)
            conic.setColorAt(0.0, QColor(T["g1"]))
            conic.setColorAt(0.33, QColor(T["g2"]))
            conic.setColorAt(0.66, QColor(T["g3"]))
            conic.setColorAt(1.0, QColor(T["g1"]))

            painter.setPen(QPen(qcolor(T["g2"], 0.10), 8))
            painter.drawPath(path)
            painter.setPen(QPen(QBrush(conic), 2.2))
            painter.drawPath(path)
        elif self.focused:
            neon = QLinearGradient(rect.topLeft(), rect.bottomRight())
            neon.setColorAt(0.0, QColor(T["g1"]))
            neon.setColorAt(0.5, QColor(T["g2"]))
            neon.setColorAt(1.0, QColor(T["g3"]))

            painter.setPen(QPen(qcolor(T["g2"], 0.10), 7))
            painter.drawPath(path)
            painter.setPen(QPen(QBrush(neon), 1.7))
            painter.drawPath(path)
        else:
            self.draw_border(painter, rect, path)


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
        self._fitting = False
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
        self.setStyleSheet(
            "QTextBrowser#bubbleText {"
            f" font-size: {UI['font_px']}px;"
            " padding: 0px; margin: 0px; border: none;"
            " background: transparent; }"
        )
        self.setViewportMargins(0, 0, 0, 0)
        self.document().setDocumentMargin(0)
        self.document().setDefaultStyleSheet(
            "p { margin-top: 0px; margin-bottom: 8px; }"
            "li { margin-bottom: 3px; }"
            f"h1, h2, h3 {{ color: {T['text']}; }}"
            f"a {{ color: {T['accent']}; }}"
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

    # ---- sizing -------------------------------------------------

    def _sync_font(self):
        """Make the document use the real (stylesheet) font before measuring."""
        self.ensurePolished()
        self.document().setDefaultFont(self.font())

    def _fit_height(self, *_args):
        if self._fitting:
            return

        self._fitting = True
        try:
            width = self.viewport().width()

            if width > 0:
                self.document().setTextWidth(width)

            height = int(math.ceil(self.document().size().height())) + 8

            if height != self.height():
                self.setFixedHeight(height)

            bar = self.verticalScrollBar()
            if bar.value() != 0:
                bar.setValue(0)
        finally:
            self._fitting = False

    def _refit_later(self):
        self._fit_height()
        QTimer.singleShot(0, self._fit_height)
        QTimer.singleShot(120, self._fit_height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_height()

    def showEvent(self, event):
        super().showEvent(event)
        self._refit_later()

    def wheelEvent(self, event):
        # Let the chat scroll area handle the wheel, not this text view.
        event.ignore()

    # ---- content ------------------------------------------------

    def set_plain(self, text):
        self._sync_font()
        self.setPlainText(text)

        if self.shrink:
            probe = self.document().clone()
            probe.setDefaultFont(self.font())
            probe.setTextWidth(-1)
            self.natural_width = int(math.ceil(probe.idealWidth())) + 16
            self.updateGeometry()

        self._refit_later()

    def set_markdown(self, text):
        self._sync_font()
        self.setMarkdown(text)

        if "```" in text:
            self._style_code_blocks()

        self._refit_later()

    def _style_code_blocks(self):
        try:
            document = self.document()
            cursor = QTextCursor(document)
            cursor.beginEditBlock()
            block = document.begin()

            while block.isValid():
                block_format = block.blockFormat()

                if block_format.nonBreakableLines():
                    block_format.setBackground(QColor(T["code_bg"]))
                    cursor.setPosition(block.position())
                    cursor.setBlockFormat(block_format)

                block = block.next()

            cursor.endEditBlock()
        except Exception:
            pass

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
    options_clicked = Signal(QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_pos = QPoint(-1, -1)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_pressed.emit()
            return
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        self._hover_pos = event.position().toPoint()
        super().mouseMoveEvent(event)
        self.viewport().update()

    def leaveEvent(self, event):
        self._hover_pos = QPoint(-1, -1)
        self.viewport().update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._hover_pos.x() < 0:
            return

        item = self.itemAt(self._hover_pos)
        if item is None:
            return

        rect = self.visualItemRect(item)
        painter = QPainter(self.viewport())
        icon = make_icon("more", "muted", 16)
        icon.paint(
            painter,
            QRect(rect.right() - 28, rect.center().y() - 8, 16, 16),
        )
        painter.end()

    def mouseReleaseEvent(self, event):
        pos = event.position().toPoint()

        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(pos)

            if item is not None:
                rect = self.visualItemRect(item)

                if pos.x() >= rect.right() - 34:
                    self.options_clicked.emit(
                        QPoint(rect.left() + 10, pos.y())
                    )
                    event.accept()
                    return

        super().mouseReleaseEvent(event)


class SidebarHost(QWidget):
    """Clips the sidebar so it can slide open and closed smoothly."""

    def __init__(self, width):
        super().__init__()
        self.full_width = width
        self.inner = QFrame(self)
        self.inner.setObjectName("sidebar")
        self.setFixedWidth(width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.inner.setGeometry(0, 0, self.full_width, self.height())


# ============================================================
# CHAT WIDGETS
# ============================================================

class UserBubble(QWidget):
    def __init__(self, text):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 8, 0, 8)
        row.addStretch(1)

        card = GlassPanel(radius=20, strength=1.0, tint=0.32)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 12, 18, 12)

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

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 6, 0, 6)

        panel = GlassPanel(radius=22, strength=0.6)
        outer.addWidget(panel)

        row = QHBoxLayout(panel)
        row.setContentsMargins(16, 14, 18, 10)
        row.setSpacing(14)

        self.orb = Orb(34, animated=streaming)
        row.addWidget(self.orb, 0, Qt.AlignmentFlag.AlignTop)

        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)

        name = QLabel("Ahmad Intelligence")
        name.setObjectName("assistantName")
        column.addWidget(name)

        self.dots = ThinkingBars()
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
        self.orb.set_animated(False)


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


class SuggestionCard(GlassPanel):
    """Welcome card with a smooth animated neon hover."""

    clicked = Signal(str)

    def __init__(self, icon_name, title, description, prompt):
        super().__init__(radius=20, strength=1.0)
        self.prompt = prompt
        self.icon_name = icon_name
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.hover_anim = QVariantAnimation(self)
        self.hover_anim.setDuration(190)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.hover_anim.valueChanged.connect(self._set_glow)

        row = QHBoxLayout(self)
        row.setContentsMargins(18, 17, 18, 17)
        row.setSpacing(15)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("cardIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(44, 44)
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

    def _set_glow(self, value):
        self.glow = float(value)
        self.update()

    def _animate_to(self, target):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self.glow)
        self.hover_anim.setEndValue(target)
        self.hover_anim.start()

    def retheme(self):
        self.icon_label.setPixmap(
            make_icon(self.icon_name, "accent_text", 21).pixmap(QSize(21, 21))
        )

    def enterEvent(self, event):
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_to(0.0)
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
        self.animation.setDuration(220)
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
            parent.height() - self.height() - 138,
        )

        self.show()
        self.raise_()

        self.animation.stop()
        self.animation.setStartValue(self.effect.opacity())
        self.animation.setEndValue(1.0)
        self.animation.start()
        self.timer.start(2200)

    def _fade_out(self):
        self.hiding = True
        self.animation.stop()
        self.animation.setStartValue(self.effect.opacity())
        self.animation.setEndValue(0.0)
        self.animation.start()

    def _animation_done(self):
        if self.hiding:
            self.hide()


# ============================================================
# COMMAND PALETTE  (Ctrl+P)
# ============================================================

class PaletteInput(_QLineEdit):
    move_selection = Signal(int)
    run_requested = Signal()
    close_requested = Signal()

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key.Key_Down:
            self.move_selection.emit(1)
            return
        if key == Qt.Key.Key_Up:
            self.move_selection.emit(-1)
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.run_requested.emit()
            return
        if key == Qt.Key.Key_Escape:
            self.close_requested.emit()
            return

        super().keyPressEvent(event)


class CommandPalette(QWidget):
    """Spotlight-style overlay to run any action from the keyboard."""

    def __init__(self, window):
        super().__init__(window.root)
        self.win = window
        self.actions = []
        self.hide()

        self.panel = GlassPanel(radius=24, strength=1.4, solid=0.94, parent=self)
        self.panel.setFixedSize(580, 440)

        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(6, 6, 6, 10)
        layout.setSpacing(0)

        self.input = PaletteInput()
        self.input.setObjectName("paletteInput")
        self.input.setPlaceholderText("Type a command…")
        self.input.textChanged.connect(self.refresh_list)
        self.input.move_selection.connect(self._move)
        self.input.run_requested.connect(self.run_selected)
        self.input.close_requested.connect(self.close_palette)
        layout.addWidget(self.input)

        self.list = QListWidget()
        self.list.setObjectName("paletteList")
        self.list.setIconSize(QSize(18, 18))
        self.list.itemClicked.connect(lambda _item: self.run_selected())
        layout.addWidget(self.list, 1)

        hint = QLabel("↑ ↓ to move   ·   Enter to run   ·   Esc to close")
        hint.setObjectName("paletteHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def open_palette(self):
        self.setGeometry(self.parentWidget().rect())
        self._place_panel()
        self.actions = self.win.palette_actions()
        self.input.clear()
        self.refresh_list()
        self.show()
        self.raise_()
        self.input.setFocus()
        fade_in(self, 170)

    def close_palette(self):
        self.hide()
        self.win.message_input.setFocus()

    def _place_panel(self):
        self.panel.move(
            (self.width() - self.panel.width()) // 2,
            max(30, int(self.height() * 0.14)),
        )

    def reposition(self):
        if self.isVisible():
            self.setGeometry(self.parentWidget().rect())
            self._place_panel()

    def refresh_list(self, *_args):
        needle = self.input.text().strip().casefold()
        self.list.clear()

        for title, shortcut, icon_name, callback in self.actions:
            if needle and needle not in title.casefold():
                continue

            label = f"{title}      {shortcut}" if shortcut else title
            item = QListWidgetItem(make_icon(icon_name, "text", 18), label)
            item.setData(Qt.ItemDataRole.UserRole, callback)
            self.list.addItem(item)

        if self.list.count():
            self.list.setCurrentRow(0)

    def _move(self, step):
        count = self.list.count()

        if not count:
            return

        row = (self.list.currentRow() + step) % count
        self.list.setCurrentRow(row)

    def run_selected(self):
        item = self.list.currentItem()

        if item is None:
            return

        callback = item.data(Qt.ItemDataRole.UserRole)
        self.close_palette()
        QTimer.singleShot(0, callback)

    def paintEvent(self, _event):
        painter = QPainter(self)
        color = (
            QColor(3, 4, 10, 175)
            if MODE["name"] == "dark"
            else QColor(235, 238, 250, 170)
        )
        painter.fillRect(self.rect(), color)

    def mousePressEvent(self, event):
        if not self.panel.geometry().contains(event.position().toPoint()):
            self.close_palette()
            return
        super().mousePressEvent(event)


# ============================================================
# BIN DIALOG
# ============================================================

class BinDialog(FadeDialog):
    def __init__(self, window):
        super().__init__(window)
        self.win = window
        self.setWindowTitle("Bin")
        self.resize(580, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 22)
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
# SETTINGS DIALOG  (Model / Appearance / Font)
# ============================================================

class SettingsDialog(FadeDialog):
    def __init__(self, win, page=0):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Settings")
        self.resize(900, 640)
        self.setMinimumSize(760, 560)

        self.theme_name = MODE["name"]
        self.accent_name = MODE["accent"]
        self.font_family = FONT["family"]
        self.font_px = UI["font_px"]
        self.anim_bg = win.bg_enabled

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- left navigation
        side = QFrame()
        side.setObjectName("settingsSide")
        side.setFixedWidth(220)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(16, 26, 16, 18)
        side_layout.setSpacing(6)

        title = QLabel("Settings")
        title.setObjectName("dialogTitle")
        side_layout.addWidget(title)
        side_layout.addSpacing(10)

        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setIconSize(QSize(18, 18))

        for label, icon_name in (
            ("Model", "sparkle"),
            ("Appearance", "palette"),
            ("Font", "type"),
        ):
            item = QListWidgetItem(make_icon(icon_name, "text", 18), "  " + label)
            self.nav.addItem(item)

        side_layout.addWidget(self.nav, 1)
        root.addWidget(side)

        # ---- right: pages + buttons
        right = QVBoxLayout()
        right.setContentsMargins(32, 28, 32, 22)
        right.setSpacing(14)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._model_page())
        self.pages.addWidget(self._appearance_page())
        self.pages.addWidget(self._font_page())
        right.addWidget(self.pages, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch(1)

        cancel = QPushButton("Cancel")
        cancel.setMinimumHeight(40)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        save = NeonButton("Save changes")
        save.setMinimumWidth(170)
        save.clicked.connect(self.accept)
        buttons.addWidget(save)

        right.addLayout(buttons)
        root.addLayout(right, 1)

        self.nav.currentRowChanged.connect(self._change_page)
        self.nav.setCurrentRow(page)

    # ---- helpers

    def _change_page(self, row):
        if row < 0:
            return
        self.pages.setCurrentIndex(row)
        fade_in(self.pages.currentWidget(), 230)

    def _heading(self, title, subtitle):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 6)
        layout.setSpacing(2)

        head = QLabel(title)
        head.setObjectName("pageTitle")
        layout.addWidget(head)

        sub = QLabel(subtitle)
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        layout.addWidget(sub)
        return box

    def _caption(self, text):
        label = QLabel(text)
        label.setObjectName("section")
        return label

    def _seg_button(self, text, group, checked=False):
        button = QPushButton(text)
        button.setObjectName("seg")
        button.setCheckable(True)
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        group.addButton(button)
        button.setChecked(checked)
        return button

    # ---- pages

    def _model_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(
            self._heading("Model", "Choose where the answers come from.")
        )

        layout.addWidget(self._caption("PROVIDER"))
        row = QHBoxLayout()
        row.setSpacing(10)

        self.provider_group = QButtonGroup(self)
        self.provider_group.setExclusive(True)
        self.btn_gemini = self._seg_button(
            "Cloud  ·  Gemini", self.provider_group,
            self.win.provider == "gemini",
        )
        self.btn_ollama = self._seg_button(
            "Local  ·  Ollama", self.provider_group,
            self.win.provider != "gemini",
        )
        row.addWidget(self.btn_gemini)
        row.addWidget(self.btn_ollama)
        row.addStretch(1)
        layout.addLayout(row)

        layout.addSpacing(8)
        layout.addWidget(self._caption("GEMINI MODEL"))
        self.gemini_edit = QLineEdit(self.win.gemini_model_name)
        self.gemini_edit.setPlaceholderText(DEFAULT_GEMINI_MODEL)
        layout.addWidget(self.gemini_edit)

        if os.getenv("GEMINI_API_KEY"):
            key_note = QLabel("●  GEMINI_API_KEY was found.")
            key_note.setObjectName("okNote")
        else:
            key_note = QLabel(
                "●  GEMINI_API_KEY is not set. Run  export GEMINI_API_KEY="
                "\"your-key\"  in the terminal before starting the app."
            )
            key_note.setObjectName("warnNote")
        key_note.setWordWrap(True)
        layout.addWidget(key_note)

        layout.addSpacing(8)
        layout.addWidget(self._caption("OLLAMA MODEL"))

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)

        try:
            response = requests.get(ollama_base() + "/api/tags", timeout=3)
            response.raise_for_status()
            names = [
                item.get("name", "")
                for item in response.json().get("models", [])
                if item.get("name")
            ]
            self.model_combo.addItems(names)
        except Exception:
            pass

        if self.model_combo.count() == 0:
            self.model_combo.addItem(self.win.local_model_name)

        self.model_combo.setCurrentText(self.win.local_model_name)
        layout.addWidget(self.model_combo)

        hint = QLabel("Ollama models must already be downloaded on this computer.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch(1)
        return page

    def _appearance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(
            self._heading("Appearance", "Pick a mode and a neon colour theme.")
        )

        layout.addWidget(self._caption("MODE"))
        row = QHBoxLayout()
        row.setSpacing(10)

        self.theme_group = QButtonGroup(self)
        self.theme_group.setExclusive(True)
        self.btn_dark = self._seg_button(
            "Dark", self.theme_group, self.theme_name == "dark"
        )
        self.btn_light = self._seg_button(
            "Light", self.theme_group, self.theme_name == "light"
        )
        self.btn_dark.clicked.connect(lambda: self._set_mode_choice("dark"))
        self.btn_light.clicked.connect(lambda: self._set_mode_choice("light"))
        row.addWidget(self.btn_dark)
        row.addWidget(self.btn_light)
        row.addStretch(1)
        layout.addLayout(row)

        layout.addSpacing(10)
        layout.addWidget(self._caption("COLOUR THEME"))

        grid = QGridLayout()
        grid.setSpacing(12)
        self.swatches = []
        self.swatch_group = QButtonGroup(self)
        self.swatch_group.setExclusive(True)

        for index, name in enumerate(NEON):
            swatch = ThemeSwatch(name, self.theme_name)
            swatch.setChecked(name == self.accent_name)
            swatch.clicked.connect(
                lambda _checked=False, n=name: self._set_accent_choice(n)
            )
            self.swatch_group.addButton(swatch)
            self.swatches.append(swatch)
            grid.addWidget(swatch, index // 3, index % 3)

        grid.setColumnStretch(3, 1)
        layout.addLayout(grid)

        layout.addSpacing(10)
        layout.addWidget(self._caption("ANIMATED BACKGROUND"))
        bg_row = QHBoxLayout()
        bg_row.setSpacing(10)

        self.bg_group = QButtonGroup(self)
        self.bg_group.setExclusive(True)
        self.btn_bg_on = self._seg_button("On", self.bg_group, self.anim_bg)
        self.btn_bg_off = self._seg_button("Off", self.bg_group, not self.anim_bg)
        self.btn_bg_on.clicked.connect(lambda: self._set_bg_choice(True))
        self.btn_bg_off.clicked.connect(lambda: self._set_bg_choice(False))
        bg_row.addWidget(self.btn_bg_on)
        bg_row.addWidget(self.btn_bg_off)
        bg_row.addStretch(1)
        layout.addLayout(bg_row)

        note = QLabel(
            "The aurora and particles move on the welcome screen. "
            "Turn it off to save battery. Changes apply when you save."
        )
        note.setObjectName("hint")
        note.setWordWrap(True)
        layout.addSpacing(4)
        layout.addWidget(note)

        layout.addStretch(1)
        return page

    def _set_mode_choice(self, name):
        self.theme_name = name
        for swatch in self.swatches:
            swatch.mode = name
            swatch.update()

    def _set_accent_choice(self, name):
        self.accent_name = name

    def _set_bg_choice(self, value):
        self.anim_bg = value

    def _font_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(
            self._heading(
                "Font",
                "Choose the font for the whole app and the size of chat text.",
            )
        )

        self.font_search = QLineEdit()
        self.font_search.setPlaceholderText("Search fonts…")
        self.font_search.setClearButtonEnabled(True)
        self.font_search.textChanged.connect(self._filter_fonts)
        layout.addWidget(self.font_search)

        self.font_list = QListWidget()
        self.font_list.setObjectName("fontList")
        self.font_list.setVerticalScrollMode(
            QListWidget.ScrollMode.ScrollPerPixel
        )
        layout.addWidget(self.font_list, 1)

        self.font_count = QLabel("")
        self.font_count.setObjectName("hint")
        self._fill_fonts()
        self.font_list.currentItemChanged.connect(self._font_selected)
        self._select_current_font()
        layout.addWidget(self.font_count)

        self.font_preview = QLabel(
            "The quick brown fox jumps over the lazy dog.\n"
            "0123456789  ·  Ahmad Intelligence"
        )
        self.font_preview.setObjectName("fontPreview")
        self.font_preview.setWordWrap(True)
        self.font_preview.setMinimumHeight(84)
        layout.addWidget(self.font_preview)

        size_row = QHBoxLayout()
        size_row.setSpacing(12)
        size_row.addWidget(QLabel("Chat text size"))

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(12, 22)
        self.size_slider.setValue(self.font_px)
        self.size_slider.valueChanged.connect(self._size_changed)
        size_row.addWidget(self.size_slider, 1)

        self.size_label = QLabel(f"{self.font_px} px")
        self.size_label.setMinimumWidth(44)
        size_row.addWidget(self.size_label)

        add_font = QPushButton("Add font file…")
        add_font.clicked.connect(self._add_font_file)
        size_row.addWidget(add_font)
        layout.addLayout(size_row)

        self._update_preview()
        return page

    # ---- font list logic

    def _fill_fonts(self):
        self.font_list.blockSignals(True)
        self.font_list.clear()

        installed = installed_families()
        installed_set = set(installed)
        suggested = [name for name in FONT_CHOICES if name in installed_set]
        suggested_set = set(suggested)
        others = [name for name in installed if name not in suggested_set]

        def add_header(text):
            item = QListWidgetItem(text)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            small = QFont()
            small.setPixelSize(10)
            small.setBold(True)
            item.setFont(small)
            item.setForeground(QColor(T["faint"]))
            self.font_list.addItem(item)

        def add_font(family):
            item = QListWidgetItem(family)
            preview = QFont(family)
            preview.setPixelSize(17)
            item.setFont(preview)
            item.setData(Qt.ItemDataRole.UserRole, family)
            self.font_list.addItem(item)

        if suggested:
            add_header("SUGGESTED")
            for family in suggested:
                add_font(family)

        if others:
            add_header("ALL INSTALLED FONTS")
            for family in others:
                add_font(family)

        self.font_list.blockSignals(False)
        self.font_count.setText(
            f"{len(installed)} fonts available. "
            "Use “Add font file…” to install more (.ttf / .otf)."
        )

    def _select_current_font(self):
        for index in range(self.font_list.count()):
            item = self.font_list.item(index)

            if item.data(Qt.ItemDataRole.UserRole) == self.font_family:
                self.font_list.setCurrentItem(item)
                self.font_list.scrollToItem(
                    item, QAbstractItemView.ScrollHint.PositionAtCenter
                )
                return

    def _filter_fonts(self, text):
        needle = text.strip().casefold()

        for index in range(self.font_list.count()):
            item = self.font_list.item(index)
            family = item.data(Qt.ItemDataRole.UserRole)

            if family is None:  # section header
                item.setHidden(bool(needle))
            else:
                item.setHidden(bool(needle) and needle not in family.casefold())

    def _font_selected(self, current, _previous):
        if current is None:
            return

        family = current.data(Qt.ItemDataRole.UserRole)

        if family:
            self.font_family = family
            self._update_preview()

    def _size_changed(self, value):
        self.font_px = value
        self.size_label.setText(f"{value} px")
        self._update_preview()

    def _update_preview(self):
        family = (self.font_family or "").replace('"', "")
        self.font_preview.setStyleSheet(
            f'font-family: "{family}"; font-size: {self.font_px}px;'
        )

    def _add_font_file(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add font files",
            os.path.expanduser("~"),
            "Fonts (*.ttf *.otf *.ttc)",
        )

        added = 0

        for path in paths:
            if QFontDatabase.addApplicationFont(path) != -1:
                self.win.remember_font_file(path)
                added += 1

        if paths and not added:
            QMessageBox.warning(
                self, "Font not added", "Those files could not be loaded."
            )
            return

        if added:
            self._fill_fonts()
            self._select_current_font()
            self.win.toast.pop(f"{added} font(s) added")

    # ---- result

    def values(self):
        return {
            "provider": "gemini" if self.btn_gemini.isChecked() else "ollama",
            "local_model": self.model_combo.currentText().strip(),
            "gemini_model": self.gemini_edit.text().strip(),
            "theme": self.theme_name,
            "accent": self.accent_name,
            "font": self.font_family,
            "font_px": self.font_px,
            "anim_bg": self.anim_bg,
        }


# ============================================================
# BACKGROUND WORKERS
# ============================================================

class AIWorker(QThread):
    token_received = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, messages, instructions, model, provider="ollama"):
        super().__init__()
        self.messages = messages
        self.instructions = instructions
        self.model = model
        self.provider = provider
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

            answer_parts = []

            # Cloud AI: Google Gemini
            if self.provider == "gemini":
                api_key = os.getenv("GEMINI_API_KEY")

                if not api_key:
                    raise RuntimeError(
                        "GEMINI_API_KEY is missing. Configure your API key "
                        "in the environment, then restart the app."
                    )

                client = genai.Client(api_key=api_key)

                gemini_messages = [
                    {
                        "role": "user" if message["role"] == "user" else "model",
                        "parts": [{"text": message["content"]}],
                    }
                    for message in self.messages
                ]

                stream = client.models.generate_content_stream(
                    model=self.model,
                    contents=gemini_messages,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt
                    ),
                )

                for chunk in stream:
                    if self._stop:
                        break

                    text = chunk.text or ""

                    if text:
                        answer_parts.append(text)
                        self.token_received.emit(text)

            # Local AI: Ollama
            else:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        *self.messages,
                    ],
                    "stream": True,
                }

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
            self.failed.emit(f"{type(error).__name__}: {error}")


class PingWorker(QThread):
    result = Signal(bool)

    def run(self):
        try:
            response = requests.get(ollama_base() + "/api/tags", timeout=2)
            self.result.emit(response.ok)
        except Exception:
            self.result.emit(False)


# ============================================================
# WINDOW CHROME
# ============================================================

class CustomTitleBar(QFrame):
    def __init__(self, window):
        super().__init__(window)
        # NOTE: not called "window" - that would shadow QWidget.window().
        self.main_window = window
        self.drag_position = None

        self.setObjectName("titleBar")
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(Orb(24))
        layout.addSpacing(10)

        title = QLabel("Ahmad Intelligence")
        title.setObjectName("titleText")
        layout.addWidget(title)
        layout.addStretch(1)

        self.min_button = self._win_button(
            "Minimize", window.showMinimized
        )
        layout.addWidget(self.min_button)

        self.max_button = self._win_button(
            "Maximize / Restore", self.toggle_maximize
        )
        layout.addWidget(self.max_button)

        self.close_button = self._win_button(
            "Close", window.close, close=True
        )
        layout.addWidget(self.close_button)

        self.retheme()

    def _win_button(self, tooltip, slot, close=False):
        button = QPushButton()
        button.setObjectName("winClose" if close else "winBtn")
        button.setToolTip(tooltip)
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        button.clicked.connect(slot)
        return button

    def retheme(self):
        size = QSize(16, 16)

        self.min_button.setIcon(make_icon("minimize", "muted", 16))
        self.min_button.setIconSize(size)
        self.close_button.setIcon(make_icon("close", "muted", 16))
        self.close_button.setIconSize(size)
        self.sync_state()

    def sync_state(self):
        name = "restore_win" if self.main_window.isMaximized() else "maximize"
        self.max_button.setIcon(make_icon(name, "muted", 16))
        self.max_button.setIconSize(QSize(16, 16))

    def toggle_maximize(self):
        if self.main_window.isMaximized():
            self.main_window.showNormal()
        else:
            self.main_window.showMaximized()
        self.sync_state()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.main_window.windowHandle()

            if handle is not None:
                try:
                    if handle.startSystemMove():
                        event.accept()
                        return
                except Exception:
                    pass

            self.drag_position = (
                event.globalPosition().toPoint()
                - self.main_window.frameGeometry().topLeft()
            )
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self.drag_position is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and not self.main_window.isMaximized()
        ):
            self.main_window.move(
                event.globalPosition().toPoint() - self.drag_position
            )
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        super().mouseReleaseEvent(event)


# ============================================================
# MAIN WINDOW
# ============================================================

class AhmadIntelligence(QMainWindow):

    def __init__(self):
        super().__init__()

        self.store = DataStore(DATA_FILE)

        # fonts, theme, text size
        load_font_files(self.store.get("font_files", []))
        FONT["family"] = self.store.get("font", "") or pick_default_font()
        set_theme(
            self.store.get("theme", "dark"),
            self.store.get("accent", "Aurora"),
        )
        UI["font_px"] = int(self.store.get("font_px", 15))
        self.bg_enabled = bool(self.store.get("anim_bg", True))

        # models (Gemini is the default)
        self.local_model_name = self.store.get("local_model", MODEL_NAME)
        self.gemini_model_name = (
            self.store.get("gemini_model", DEFAULT_GEMINI_MODEL)
            or DEFAULT_GEMINI_MODEL
        )
        self.provider = self.store.get("provider", "gemini")
        if self.provider not in ("gemini", "ollama"):
            self.provider = "gemini"
        self.model_name = (
            self.gemini_model_name
            if self.provider == "gemini"
            else self.local_model_name
        )

        self.conversation_id = None
        self.current_project_id = "default"

        self.busy = False
        self.worker = None
        self._workers = set()
        self.current_answer = ""
        self.stream_bubble = None
        self.stream_dirty = False
        self.t_start = 0.0
        self.sidebar_open = bool(self.store.get("sidebar_open", True))
        self.stick_to_bottom = True
        self.ollama_ok = None
        self.icon_refs = {}
        self.welcome_cards = []
        self._welcome_anim_t = 0.0

        initialize_database()

        self.setWindowTitle("Ahmad Intelligence")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setMinimumSize(940, 640)
        self.resize(1280, 820)
        self.setWindowState(Qt.WindowState.WindowMaximized)

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

        # soft intro
        QTimer.singleShot(60, lambda: fade_in(self.workspace, 650))
        QTimer.singleShot(60, lambda: fade_in(self.sidebar_host.inner, 650))

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

        frame = QVBoxLayout(self.root)
        frame.setContentsMargins(0, 0, 0, 0)
        frame.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        frame.addWidget(self.title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        frame.addLayout(body, 1)

        self.sidebar_host = SidebarHost(SIDEBAR_W)
        body.addWidget(self.sidebar_host)
        self.build_sidebar(self.sidebar_host.inner)

        self.workspace = QWidget()
        body.addWidget(self.workspace, 1)
        self.build_workspace()

        self.toast = Toast(self.root)
        self.palette = CommandPalette(self)
        self.root.resized.connect(self.palette.reposition)

        # Sidebar slide animation
        self.sb_anim = QVariantAnimation(self)
        self.sb_anim.setDuration(260)
        self.sb_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.sb_anim.valueChanged.connect(
            lambda value: self.sidebar_host.setFixedWidth(int(value))
        )
        self.sb_anim.finished.connect(self._sidebar_anim_done)

        if not self.sidebar_open:
            self.sidebar_host.setFixedWidth(0)
            self.sidebar_host.hide()

        self.stream_timer = QTimer(self)
        self.stream_timer.setInterval(60)
        self.stream_timer.timeout.connect(self._flush_stream)

        self.scroll_anim = QPropertyAnimation(
            self.scroll.verticalScrollBar(), b"value", self
        )
        self.scroll_anim.setDuration(300)
        self.scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.purge_timer = QTimer(self)
        self.purge_timer.setInterval(3600 * 1000)
        self.purge_timer.timeout.connect(self.purge_expired)
        self.purge_timer.start()

    # ---------------- Sidebar ----------------

    def build_sidebar(self, sidebar):
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 18, 16, 14)
        side.setSpacing(9)

        header = QHBoxLayout()
        header.setSpacing(11)
        header.addWidget(Orb(40))

        brand_column = QVBoxLayout()
        brand_column.setSpacing(0)
        brand = QLabel("Ahmad Intelligence")
        brand.setObjectName("brand")
        brand_column.addWidget(brand)
        brand_sub = QLabel("Neural workspace")
        brand_sub.setObjectName("brandSub")
        brand_column.addWidget(brand_sub)
        header.addLayout(brand_column, 1)

        collapse = IconButton()
        collapse.setFixedSize(34, 34)
        collapse.setToolTip("Hide sidebar (Ctrl+B)")
        self.set_icon(collapse, "sidebar", "muted", 17)
        collapse.clicked.connect(self.toggle_sidebar)
        header.addWidget(collapse)
        side.addLayout(header)

        side.addSpacing(6)

        self.new_chat_button = NeonButton("  New chat")
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
        self.history.options_clicked.connect(self.history_menu)
        side.addWidget(self.history, 1)

        footer = QHBoxLayout()
        footer.setSpacing(6)

        self.bin_button = QPushButton("  Bin")
        self.bin_button.setObjectName("nav")
        self.bin_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.set_icon(self.bin_button, "trash", "text", 16)
        self.bin_button.clicked.connect(self.open_bin)
        footer.addWidget(self.bin_button, 1)

        self.settings_nav_button = QPushButton("  Settings")
        self.settings_nav_button.setObjectName("nav")
        self.settings_nav_button.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        self.set_icon(self.settings_nav_button, "gear", "text", 16)
        self.settings_nav_button.clicked.connect(self.open_settings)
        footer.addWidget(self.settings_nav_button, 1)
        side.addLayout(footer)

        self.side_status = QLabel("●  Checking…")
        self.side_status.setObjectName("localStatus")
        self.side_status.setTextFormat(Qt.TextFormat.RichText)
        side.addWidget(self.side_status)

    # ---------------- Workspace ----------------

    def build_workspace(self):
        layout = QVBoxLayout(self.workspace)
        layout.setContentsMargins(30, 14, 30, 8)
        layout.setSpacing(10)

        topbar = QHBoxLayout()
        topbar.setSpacing(6)

        self.menu_button = self.top_icon_button(
            "sidebar", "Show / hide sidebar (Ctrl+B)", self.toggle_sidebar,
            size=20,
        )
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

        self.palette_button = self.top_icon_button(
            "bolt", "Command palette (Ctrl+P)", self.open_palette
        )
        topbar.addWidget(self.palette_button)

        self.export_button = self.top_icon_button(
            "download", "Export chat as Markdown", self.export_chat
        )
        topbar.addWidget(self.export_button)

        self.delete_button = self.top_icon_button(
            "trash", "Move this chat to the bin", self.delete_current_chat
        )
        topbar.addWidget(self.delete_button)

        self.theme_button = self.top_icon_button(
            "sun" if MODE["name"] == "light" else "moon",
            "Switch light / dark mode (Ctrl+Shift+T)",
            self.toggle_theme,
        )
        topbar.addWidget(self.theme_button)

        self.settings_button = self.top_icon_button(
            "gear", "Settings (Ctrl+,)", self.open_settings
        )
        topbar.addWidget(self.settings_button)

        layout.addLayout(topbar)

        self.stack = QStackedWidget()
        self.welcome = self.build_welcome()
        self.scroll = self.build_chat_area()
        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.scroll)
        layout.addWidget(self.stack, 1)

        # Composer
        self.composer = ComposerFrame()
        self.composer.setMaximumWidth(860)

        composer_layout = QVBoxLayout(self.composer)
        composer_layout.setContentsMargins(22, 14, 14, 12)
        composer_layout.setSpacing(4)

        self.message_input = GrowingTextEdit()
        self.message_input.setPlaceholderText("Ask anything…")
        self.message_input.submitted.connect(self.send_message)
        self.message_input.focus_changed.connect(self.composer.set_focused)
        self.message_input.textChanged.connect(self._update_send_state)
        composer_layout.addWidget(self.message_input)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        self.model_chip = ChipLabel()
        self.model_chip.setObjectName("chip")
        self.model_chip.setTextFormat(Qt.TextFormat.RichText)
        self.model_chip.setToolTip("Active model - click to change")
        self.model_chip.clicked.connect(self.open_settings)
        bottom.addWidget(self.model_chip)

        hint = QLabel("Enter to send  ·  Shift+Enter new line  ·  Ctrl+P commands")
        hint.setObjectName("hint")
        bottom.addWidget(hint, 1)

        self.send_button = NeonButton(circular=True)
        self.send_button.setFixedSize(46, 46)
        self.set_icon(self.send_button, "send", "accent_text", 19)
        self.send_button.clicked.connect(self.on_send_clicked)
        bottom.addWidget(self.send_button)
        composer_layout.addLayout(bottom)

        composer_row = QHBoxLayout()
        composer_row.addStretch(1)
        composer_row.addWidget(self.composer, 1000)
        composer_row.addStretch(1)
        layout.addLayout(composer_row)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.addSpacing(16)
        status_row.addStretch(1)

        self.status = QLabel("Ready")
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_row.addWidget(self.status)
        status_row.addStretch(1)

        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(16, 16)
        status_row.addWidget(self.size_grip)
        layout.addLayout(status_row)

        self._update_send_state()

    def top_icon_button(self, icon_name, tooltip, slot, size=19):
        button = IconButton()
        button.setFixedSize(40, 40)
        button.setToolTip(tooltip)
        self.set_icon(button, icon_name, "text", size)
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
        column.setMaximumWidth(860)
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

        self.hero_orb = Orb(104, animated=True)
        layout.addWidget(self.hero_orb, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(14)

        self.greeting = QLabel("Hello")
        self.greeting.setObjectName("greeting")
        self.greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.greeting)
        layout.addSpacing(2)

        hero = GradientLabel("How can I help you today?", px=42)
        layout.addWidget(hero)

        subtitle = QLabel("Think clearly. Build boldly. Everything stays yours.")
        subtitle.setObjectName("heroSub")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(4)
        layout.addWidget(subtitle)
        layout.addSpacing(34)

        holder = QWidget()
        holder.setMaximumWidth(820)
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)

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
            ("Ctrl+B", self.toggle_sidebar),
            ("Ctrl+K", self.focus_search),
            ("Ctrl+P", self.open_palette),
            ("Ctrl+,", self.open_settings),
            ("Ctrl+Shift+E", self.export_chat),
            ("Ctrl+Shift+T", self.toggle_theme),
            ("Ctrl+=", lambda: self.zoom(1)),
            ("Ctrl++", lambda: self.zoom(1)),
            ("Ctrl+-", lambda: self.zoom(-1)),
            ("Ctrl+0", lambda: self.zoom(0)),
            ("Esc", self.on_escape),
        ]
        self._shortcuts = []

        for sequence, callback in bindings:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def on_escape(self):
        if self.palette.isVisible():
            self.palette.close_palette()
        else:
            self.stop_generation()

    def open_palette(self, *_args):
        self.palette.open_palette()

    def changeEvent(self, event):
        super().changeEvent(event)

        if hasattr(self, "title_bar"):
            self.title_bar.sync_state()

        if hasattr(self, "size_grip"):
            self.size_grip.setVisible(not self.isMaximized())

        if hasattr(self, "stack"):
            self.update_bg_animation()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_bg_animation()

    # --------------------------------------------------------
    # PAGES & BACKGROUND ANIMATION
    # --------------------------------------------------------

    def show_page(self, widget):
        self.stack.setCurrentWidget(widget)
        self.update_bg_animation()

    def update_bg_animation(self):
        want = (
            self.bg_enabled
            and self.stack.currentWidget() is self.welcome
            and self.isVisible()
            and not self.isMinimized()
        )
        self.root.set_animated(want)

    def toggle_bg(self):
        self.bg_enabled = not self.bg_enabled
        self.store.set("anim_bg", self.bg_enabled)
        self.update_bg_animation()
        self.toast.pop(
            "Animated background on"
            if self.bg_enabled
            else "Animated background off"
        )

    # --------------------------------------------------------
    # SIDEBAR  (docked, slides open and closed)
    # --------------------------------------------------------

    def toggle_sidebar(self, *_args):
        self.set_sidebar_open(not self.sidebar_open)

    def set_sidebar_open(self, value, animate=True):
        self.sidebar_open = value
        self.store.set("sidebar_open", value)

        target = SIDEBAR_W if value else 0
        self.sb_anim.stop()

        if value:
            self.sidebar_host.show()

        if not animate:
            self.sidebar_host.setFixedWidth(target)
            self.sidebar_host.setVisible(value)
            return

        self.sb_anim.setStartValue(self.sidebar_host.width())
        self.sb_anim.setEndValue(target)
        self.sb_anim.start()

    def _sidebar_anim_done(self):
        if not self.sidebar_open:
            self.sidebar_host.hide()

    def focus_search(self):
        if not self.sidebar_open:
            self.set_sidebar_open(True)
        self.search.setFocus()
        self.search.selectAll()

    # --------------------------------------------------------
    # THEME, FONT & TEXT SIZE
    # --------------------------------------------------------

    def apply_look(self, theme, accent, family, px):
        self.store.set("theme", theme)
        self.store.set("accent", accent)
        self.store.set("font", family)
        self.store.set("font_px", px)

        if family:
            FONT["family"] = family
        UI["font_px"] = px
        set_theme(theme, accent)

        app = QApplication.instance()
        apply_palette(app)
        app.setStyleSheet(build_style())

        self.set_icon(
            self.theme_button,
            "sun" if theme == "light" else "moon",
            "text",
            19,
        )
        self.retheme_icons()
        self.title_bar.retheme()

        for card in self.welcome_cards:
            card.retheme()

        self.root.invalidate()
        self.refresh_model_chip()
        self.load_conversations(select_id=self.conversation_id)

        if not self.busy and self.conversation_id is not None:
            self.render_conversation()

        for widget in self.findChildren(QWidget):
            widget.update()

    def toggle_theme(self):
        name = "light" if MODE["name"] == "dark" else "dark"
        self.apply_look(name, MODE["accent"], FONT["family"], UI["font_px"])
        self.toast.pop("Light mode" if name == "light" else "Dark mode")

    def zoom(self, direction):
        if direction == 0:
            size = 15
        else:
            size = max(12, min(22, UI["font_px"] + direction))

        UI["font_px"] = size
        self.store.set("font_px", size)
        self.toast.pop(f"Text size {size}")

        if not self.busy and self.conversation_id is not None:
            self.render_conversation()

    def remember_font_file(self, path):
        files = list(self.store.get("font_files", []))

        if path not in files:
            files.append(path)
            self.store.set("font_files", files)

    # --------------------------------------------------------
    # SETTINGS & COMMANDS
    # --------------------------------------------------------

    def open_settings(self, *_args, page=0):
        dialog = SettingsDialog(self, page)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_settings(dialog.values())

    def apply_settings(self, values):
        self.provider = values["provider"]
        self.store.set("provider", self.provider)

        if values["local_model"]:
            self.local_model_name = values["local_model"]
            self.store.set("local_model", self.local_model_name)

        self.gemini_model_name = (
            values["gemini_model"] or DEFAULT_GEMINI_MODEL
        )
        self.store.set("gemini_model", self.gemini_model_name)

        self.model_name = (
            self.gemini_model_name
            if self.provider == "gemini"
            else self.local_model_name
        )

        self.bg_enabled = bool(values["anim_bg"])
        self.store.set("anim_bg", self.bg_enabled)

        self.apply_look(
            values["theme"],
            values["accent"],
            values["font"],
            values["font_px"],
        )

        self.update_bg_animation()
        self.refresh_model_chip()
        self.toast.pop("Settings saved")

    def set_provider(self, provider):
        self.provider = provider
        self.store.set("provider", provider)
        self.model_name = (
            self.gemini_model_name
            if provider == "gemini"
            else self.local_model_name
        )
        self.refresh_model_chip()
        self.toast.pop(
            "Using Gemini (cloud)" if provider == "gemini" else "Using Ollama (local)"
        )

    def palette_actions(self):
        actions = [
            ("New chat", "Ctrl+N", "plus", self.new_chat),
            ("Search chats", "Ctrl+K", "search", self.focus_search),
            ("Open settings", "Ctrl+,", "gear", self.open_settings),
            ("Font settings", "", "type", lambda: self.open_settings(page=2)),
            (
                "Appearance settings", "", "palette",
                lambda: self.open_settings(page=1),
            ),
            ("Toggle sidebar", "Ctrl+B", "sidebar", self.toggle_sidebar),
            (
                "Toggle light / dark mode", "Ctrl+Shift+T", "sun",
                self.toggle_theme,
            ),
            ("Toggle animated background", "", "sparkle", self.toggle_bg),
            ("Export current chat", "Ctrl+Shift+E", "download", self.export_chat),
            ("Open bin", "", "trash", self.open_bin),
            (
                "Use Gemini (cloud)", "", "sparkle",
                lambda: self.set_provider("gemini"),
            ),
            (
                "Use Ollama (local)", "", "code",
                lambda: self.set_provider("ollama"),
            ),
        ]

        for name in NEON:
            actions.append(
                (
                    f"Theme: {name}", "", "palette",
                    lambda n=name: self.apply_look(
                        MODE["name"], n, FONT["family"], UI["font_px"]
                    ),
                )
            )

        return actions

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    def refresh_model_chip(self):
        if self.provider == "gemini":
            color = T["ok"] if os.getenv("GEMINI_API_KEY") else T["danger"]
            label = f"Gemini  ·  {self.gemini_model_name}"
        else:
            if self.ollama_ok is None:
                color = T["muted"]
            elif self.ollama_ok:
                color = T["ok"]
            else:
                color = T["danger"]

            label = f"Ollama  ·  {self.local_model_name}"

        self.model_chip.setText(
            f"<span style='color:{color};'>●</span>&nbsp;&nbsp;"
            f"{html.escape(label)}"
        )
        self.refresh_status_pill()

    def refresh_status_pill(self):
        if self.provider == "gemini":
            if os.getenv("GEMINI_API_KEY"):
                dot, text = T["ok"], "Cloud AI ready"
            else:
                dot, text = T["danger"], "Gemini API key missing"
        else:
            if self.ollama_ok is None:
                dot, text = T["muted"], "Checking Ollama…"
            elif self.ollama_ok:
                dot, text = T["ok"], "Ollama connected"
            else:
                dot, text = T["danger"], "Ollama offline — start it"

        self.side_status.setText(
            f"<span style='color:{dot};'>●</span>&nbsp;&nbsp;{html.escape(text)}"
        )

    def start_ping(self):
        self._ping = PingWorker(self)
        self._ping.result.connect(self._set_ollama_status)

        self._ping_timer = QTimer(self)
        self._ping_timer.setInterval(15000)
        self._ping_timer.timeout.connect(self._ping_tick)
        self._ping_timer.start()

        self.refresh_model_chip()
        self._ping_tick()

    def _ping_tick(self):
        if not self._ping.isRunning():
            self._ping.start()

    def _set_ollama_status(self, ok):
        self.ollama_ok = ok
        self.refresh_model_chip()

    def update_greeting(self):
        hour = time.localtime().tm_hour

        if hour < 5:
            text = "Working late"
        elif hour < 12:
            text = "Good morning"
        elif hour < 18:
            text = "Good afternoon"
        else:
            text = "Good evening"

        self.greeting.setText(text)

    def play_welcome_animation(self):
        now = time.time()

        if now - self._welcome_anim_t < 0.7:
            return

        self._welcome_anim_t = now

        for index, card in enumerate(self.welcome_cards):
            fade_in(card, 380, delay=80 * index)

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

        dialog = FadeDialog(self)
        dialog.setWindowTitle(f"{project_name} — Instructions")
        dialog.resize(600, 480)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 26, 28, 22)
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
                item.setIcon(make_icon("pin", "accent", 14))
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
        self.show_page(self.welcome)
        self.update_greeting()
        self.play_welcome_animation()

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
        self.bin_button.setText("  Bin" + (f"  ·  {count}" if count else ""))

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
            self.show_page(self.welcome)
            return

        self.show_page(self.scroll)
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
        bar = self.scroll.verticalScrollBar()

        self.scroll_anim.stop()
        self.scroll_anim.setStartValue(bar.value())
        self.scroll_anim.setEndValue(bar.maximum())
        self.scroll_anim.start()

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
            self.set_icon(self.send_button, "stop", "accent_text", 19)
            self.send_button.setToolTip("Stop generating (Esc)")
            self.send_button.setEnabled(True)
        else:
            self.set_icon(self.send_button, "send", "accent_text", 19)
            self.send_button.setToolTip("Send")
            self._update_send_state()

        self.send_button.update()
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

    def build_history(self):
        """Last few messages only - keeps long chats fast."""
        rows = get_messages(self.conversation_id)
        messages = [
            {"role": role, "content": content} for role, content in rows
        ]
        messages = messages[-HISTORY_LIMIT:]

        while messages and messages[0]["role"] != "user":
            messages.pop(0)

        return messages

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

        self.show_page(self.scroll)
        self.stick_to_bottom = True

        self.add_message("user", question, animate=True)

        self.stream_bubble = AssistantBubble(streaming=True)
        self.stream_bubble.copy_requested.connect(self.copy_text)
        self.msg_layout.insertWidget(
            self.msg_layout.count() - 1, self.stream_bubble
        )

        messages = self.build_history()
        instructions = get_project_instructions_for_conversation(
            self.conversation_id
        )

        self.current_answer = ""
        self.stream_dirty = False
        self.t_start = time.time()
        self.set_busy(True)
        self.status.setText("Thinking…")

        self.worker = AIWorker(
            messages,
            instructions,
            self.model_name,
            provider=self.provider,
        )
        self._workers.add(self.worker)
        self.worker.finished.connect(
            lambda w=self.worker: self._worker_done(w)
        )
        self.worker.token_received.connect(self.on_token)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

        self.stream_timer.setInterval(60)
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

            # Re-rendering long answers is costly, so slow down as they grow.
            size = len(self.current_answer)
            self.stream_timer.setInterval(
                60 if size < 1500 else 120 if size < 5000 else 220
            )

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

        if self.provider == "gemini":
            troubleshooting = (
                "Check your internet connection, Gemini model access, "
                "and GEMINI_API_KEY configuration."
            )
            status_text = "Cloud AI unavailable — check Gemini"
        else:
            troubleshooting = (
                "Check that Ollama is running and the model is installed."
            )
            status_text = "AI unavailable — check Ollama"

        note = ErrorNote(
            "Ahmad Intelligence couldn't complete that request.\n\n"
            f"{troubleshooting}\n\n"
            f"Details: {error}"
        )
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, note)
        fade_in(note)

        self.current_answer = ""

        if self.provider == "ollama":
            self.ollama_ok = False

        self.refresh_model_chip()
        self.status.setText(status_text)
        self.finish_response()

    def finish_response(self):
        self.set_busy(False)
        self.worker = None
        self.message_input.setFocus()

    # --------------------------------------------------------
    # SHUTDOWN
    # --------------------------------------------------------

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)

        ping = getattr(self, "_ping", None)
        if ping is not None and ping.isRunning():
            ping.wait(2500)

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