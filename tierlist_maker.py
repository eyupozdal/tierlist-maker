#!/usr/bin/env python3
"""Tier List Maker - tier listesi uygulaması (PySide6)."""
import copy
import json
import math
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtGui import QPixmap, QIcon, QColor, QCursor, QPainter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QScrollArea, QFileDialog,
    QMessageBox, QMenu, QStackedWidget, QColorDialog, QSizePolicy,
    QGraphicsOpacityEffect, QSlider, QButtonGroup,
)

# ---------------------------------------------------------------- Ayarlar
if sys.platform == "win32":
    DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "TierListMaker"
else:
    DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "tierlist-maker"
LISTS_DIR = DATA_DIR / "lists"
IMG_DIR = DATA_DIR / "images"


def resource_path(rel):
    """Paketlenmiş (.exe) ya da kaynak koddan çalışırken dosya yolunu bulur."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / rel)


TIERS = [
    ("S", "#f04a25"), ("A", "#ffa62b"), ("B", "#ffcf33"), ("C", "#1db954"),
    ("D", "#0a9bff"), ("E", "#9b51e0"), ("F", "#ff4fe0"),
]
TAG_COLORS = ["#e05a4f", "#4a90d9", "#5cb85c", "#9b6fd9", "#e072c0", "#d9a441"]

# Proje yönetim uygulamasının teması
BG = "#0e1014"
PANEL = "#15181e"
PANEL_2 = "#1b1f27"
BORDER = "#2a2e36"
TEXT = "#ececec"
MUTED = "#8a8f99"
GOLD = "#c9a45c"
GOLD_HOVER = "#d9b470"
DANGER = "#e05a4f"

DEFAULT_VIEW = {"size": 120, "fit": "cover"}   # görsel kutusu boyutu (px) ve sığdırma biçimi
CELL_MIN, CELL_MAX = 80, 220
PREVIEW_CELL = 34       # liste kartındaki küçük önizleme kutusu
PREVIEW_MAX = 10        # kartta satır başına gösterilen görsel sayısı
CARD_W = 560


def rgba(hex_, a):
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def luminance(color):
    c = QColor(color)
    return 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()


def text_on(bg):
    """Verilen arka plan rengi üzerinde okunur yazı rengi."""
    return "#111111" if luminance(bg) > 150 else "#ffffff"


def readable(color):
    """Koyu zemin üzerinde okunabilecek bir ton döndürür (etiket yazıları için)."""
    lum = luminance(color)
    if lum < 35:
        return "#cfcfcf"
    if lum < 110:
        return QColor(color).lighter(190).name()
    return color


STYLE = f"""
QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-size: 14px; }}
QScrollArea {{ background: transparent; border: none; }}
QWidget#qt_scrollarea_viewport {{ background: transparent; }}
QMessageBox {{ background: {PANEL}; }}
QLineEdit {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 10px; }}
QLineEdit:focus {{ border: 1px solid {GOLD}; }}
QPushButton {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 8px;
              padding: 7px 14px; color: {TEXT}; }}
QPushButton:hover {{ border-color: {GOLD}; color: {GOLD}; }}
QPushButton:checked {{ background: {GOLD}; color: #14110a; border-color: {GOLD}; }}
QPushButton:disabled {{ color: #555a63; border-color: {BORDER}; }}
QPushButton#primary {{ background: {GOLD}; color: #14110a; border: none; font-weight: bold; }}
QPushButton#primary:hover {{ background: {GOLD_HOVER}; color: #14110a; }}
QPushButton#danger {{ color: {DANGER}; border-color: {rgba(DANGER, 0.5)}; background: transparent; }}
QPushButton#danger:hover {{ background: {rgba(DANGER, 0.12)}; }}
QPushButton#fab {{ background: {GOLD}; color: #14110a; border: none; border-radius: 28px;
                  font-size: 26px; font-weight: bold; padding: 0;
                  min-width: 56px; max-width: 56px; min-height: 56px; max-height: 56px; }}
QPushButton#fab:hover {{ background: {GOLD_HOVER}; color: #14110a; }}
QPushButton#mini {{ padding: 0; font-size: 11px; border-radius: 5px;
                   min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; }}
QFrame#card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#board {{ background: #1a1a1a; border-radius: 10px; }}
QFrame#tierrow {{ background: #262626; border-radius: 6px; }}
QMenu {{ background: {PANEL_2}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; }}
QMenu::item:selected {{ background: {rgba(GOLD, 0.2)}; color: {GOLD}; }}
QLabel#muted {{ color: {MUTED}; }}
QSlider::groove:horizontal {{ background: {BORDER}; height: 4px; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {GOLD}; width: 14px; margin: -6px 0; border-radius: 7px; }}
"""


# ---------------------------------------------------------------- Veri
def new_data():
    return {
        "id": uuid.uuid4().hex,
        "title": "",
        "tags": [],
        "tiers": [{"label": n, "color": c, "items": []} for n, c in TIERS],
        "pool": [],
        "view": dict(DEFAULT_VIEW),
        "updated": time.time(),
    }


def load_all():
    LISTS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in LISTS_DIR.glob("*.json"):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
    out.sort(key=lambda d: d.get("updated", 0), reverse=True)
    return out


def save_list(d):
    LISTS_DIR.mkdir(parents=True, exist_ok=True)
    path = LISTS_DIR / f"{d['id']}.json"
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def remove_image(p):
    path = Path(p)
    if IMG_DIR in path.parents:
        path.unlink(missing_ok=True)


def delete_list(d):
    (LISTS_DIR / f"{d['id']}.json").unlink(missing_ok=True)
    for t in d.get("tiers", []):
        for p in t["items"]:
            remove_image(p)
    for p in d.get("pool", []):
        remove_image(p)


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.hide()
            w.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


# ---------------------------------------------------------------- Görsel önbelleği
_ORIG = {}
_THUMBS = {}


def orig_pix(path):
    """Görseli yükler. Çok büyükse bellek için küçültülmüş halini tutar."""
    if path not in _ORIG:
        pm = QPixmap(path)
        if pm.isNull():
            _ORIG[path] = None
        else:
            if max(pm.width(), pm.height()) > 800:
                pm = pm.scaled(800, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            _ORIG[path] = pm
    return _ORIG[path]


def thumb_pix(path, cell, fit):
    """Kare, dikey ve yatay görselleri aynı boyutlu kareye getirir.
    cover: kareyi doldurur (ortadan kırpar), contain: görselin tamamını sığdırır."""
    key = (path, cell, fit)
    if key in _THUMBS:
        return _THUMBS[key]
    pm = orig_pix(path)
    if pm is None:
        return None
    if fit == "contain":
        sc = pm.scaled(cell, cell, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        out = QPixmap(cell, cell)
        out.fill(Qt.transparent)
        p = QPainter(out)
        p.drawPixmap((cell - sc.width()) // 2, (cell - sc.height()) // 2, sc)
        p.end()
    else:
        sc = pm.scaled(cell, cell, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        out = sc.copy((sc.width() - cell) // 2, (sc.height() - cell) // 2, cell, cell)
    _THUMBS[key] = out
    return out


def make_chip(text, color, on_remove=None):
    fg = readable(color)
    chip = QFrame()
    chip.setObjectName("chip")
    chip.setStyleSheet(
        f"QFrame#chip {{ background: {rgba(color, 0.22)}; border: 1px solid {rgba(fg, 0.6)};"
        f" border-radius: 10px; }}"
        f"QLabel {{ background: transparent; border: none; color: {fg};"
        f" font-size: 12px; font-weight: bold; }}"
        f"QPushButton {{ background: transparent; border: none; color: {fg};"
        f" padding: 0 2px; font-size: 12px; }}"
        f"QPushButton:hover {{ color: #ffffff; }}"
    )
    lay = QHBoxLayout(chip)
    lay.setContentsMargins(10, 3, 6 if on_remove else 10, 3)
    lay.setSpacing(4)
    lay.addWidget(QLabel(text))
    if on_remove:
        b = QPushButton("✕")
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False: on_remove())
        lay.addWidget(b)
    return chip


# ---------------------------------------------------------------- Bırakma alanı
class DropZone(QFrame):
    """Öğelerin bırakılabildiği alan: bir tier satırı ya da havuz.
    Öğeler layout ile değil, mevcut genişliğe göre elle yerleştirilir (satır sonunda alta geçer)."""

    PAD = 8
    GAP = 6

    def __init__(self, dest, get_cell):
        super().__init__()
        self.dest = dest
        self.get_cell = get_cell
        self.thumbs = []
        self.setObjectName("dropzone")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set_highlight(self, on):
        if on:
            self.setStyleSheet(
                f"QFrame#dropzone {{ background: {rgba(GOLD, 0.12)};"
                f" border: 1px dashed {GOLD}; border-radius: 6px; }}"
            )
        else:
            self.setStyleSheet("")

    def set_items(self, paths, make):
        for t in self.thumbs:
            t.hide()
            t.deleteLater()
        self.thumbs = [make(self, p) for p in paths]
        self.reflow()

    def reflow(self):
        cell = self.get_cell()
        inner = max(self.width() - 2 * self.PAD, cell)
        cols = max(1, (inner + self.GAP) // (cell + self.GAP))
        n = len(self.thumbs)
        rows = max(1, math.ceil(n / cols))
        for i, t in enumerate(self.thumbs):
            r, c = divmod(i, cols)
            t.move(self.PAD + c * (cell + self.GAP), self.PAD + r * (cell + self.GAP))
            t.show()
        h = rows * cell + (rows - 1) * self.GAP + 2 * self.PAD
        if self.minimumHeight() != h:
            self.setMinimumHeight(h)
        w = cell + 2 * self.PAD
        if self.minimumWidth() != w:
            self.setMinimumWidth(w)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.reflow()

    def index_at(self, pos):
        """Verilen noktaya en yakın öğeye göre ekleme sırasını döndürür."""
        if not self.thumbs:
            return 0
        best = min(range(len(self.thumbs)),
                   key=lambda i: (self.thumbs[i].geometry().center() - pos).manhattanLength())
        c = self.thumbs[best].geometry().center()
        return best if pos.x() < c.x() else best + 1


def zone_at(global_pos):
    """Ekrandaki bir noktanın altındaki bırakma alanını bulur (tier satırının herhangi bir yeri dahil)."""
    w = QApplication.widgetAt(global_pos)
    while w is not None:
        if isinstance(w, DropZone):
            return w
        z = getattr(w, "drop_zone", None)
        if z is not None:
            return z
        w = w.parentWidget()
    return None


# ---------------------------------------------------------------- Öğe
class ItemThumb(QLabel):
    """Editördeki bir görsel. Fareyle tutulup sürüklenir; sürüklerken imleçte görünür."""

    def __init__(self, parent, path, host, cell, fit):
        super().__init__(parent)
        self.path = path
        self.host = host
        self._press = None
        self._dragging = False
        self._hover_zone = None

        pm = thumb_pix(path, cell, fit)
        if pm is not None:
            self.setPixmap(pm)
        else:
            self.setText("?")
        self.setFixedSize(cell, cell)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"QLabel {{ background: {PANEL_2}; border-radius: 6px; }}")
        self.setCursor(Qt.OpenHandCursor)

    def contextMenuEvent(self, e):
        self.host.show_item_menu(self.path, e.globalPos())

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press = e.globalPosition().toPoint()
            self._dragging = False
        e.accept()

    def update_hover(self, gp):
        zone = zone_at(gp)
        if zone is not self._hover_zone:
            if self._hover_zone is not None:
                self._hover_zone.set_highlight(False)
            if zone is not None:
                zone.set_highlight(True)
            self._hover_zone = zone

    def mouseMoveEvent(self, e):
        if self._press is None or not (e.buttons() & Qt.LeftButton):
            return
        gp = e.globalPosition().toPoint()
        if not self._dragging:
            if (gp - self._press).manhattanLength() < QApplication.startDragDistance():
                return
            self._dragging = True
            self.host.drag_begin(self)
        self.host.drag_move(gp)
        self.update_hover(gp)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        gp = e.globalPosition().toPoint()
        was_dragging = self._dragging
        self._press = None
        self._dragging = False
        if self._hover_zone is not None:
            self._hover_zone.set_highlight(False)
            self._hover_zone = None
        if not was_dragging:
            return

        self.host.drag_end()
        zone = zone_at(gp)
        if zone is not None:
            lp = zone.mapFromGlobal(gp)
            # Alanın içine bırakıldıysa imlecin olduğu sıraya, satırın başka bir yerine bırakıldıysa sona eklenir.
            index = zone.index_at(lp) if zone.rect().contains(lp) else None
            # move_item bu öğeyi silip yeniden çizeceği için, bundan sonra self'e dokunulmaz.
            self.host.move_item(self.path, zone.dest, index)


# ---------------------------------------------------------------- Liste kartı
class ListCard(QFrame):
    def __init__(self, d, on_edit, on_delete):
        super().__init__()
        self.setObjectName("card")
        self.setFixedWidth(CARD_W)
        fit = d.get("view", {}).get("fit", DEFAULT_VIEW["fit"])
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)

        title = QLabel(d.get("title") or "İsimsiz Liste")
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 17px; font-weight: bold;")
        v.addWidget(title)

        if d.get("tags"):
            tags = QHBoxLayout()
            tags.setSpacing(6)
            for t in d["tags"]:
                tags.addWidget(make_chip(t["name"], t["color"]))
            tags.addStretch()
            v.addLayout(tags)

        # Tier önizlemesi: her satır etiketi + o satırdaki görseller
        preview = QVBoxLayout()
        preview.setSpacing(4)
        for t in d.get("tiers", []):
            row = QHBoxLayout()
            row.setSpacing(4)
            lbl = QLabel(t["label"][:4])
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(38, PREVIEW_CELL)
            lbl.setStyleSheet(
                f"background: {t['color']}; color: {text_on(t['color'])}; border-radius: 4px;"
                f" font-weight: bold; font-size: 11px;"
            )
            row.addWidget(lbl)

            shown = t["items"][:PREVIEW_MAX]
            for p in shown:
                th = QLabel()
                th.setFixedSize(PREVIEW_CELL, PREVIEW_CELL)
                th.setAlignment(Qt.AlignCenter)
                th.setStyleSheet(f"background: {PANEL_2}; border-radius: 3px;")
                pm = thumb_pix(p, PREVIEW_CELL, fit)
                if pm is not None:
                    th.setPixmap(pm)
                row.addWidget(th)

            extra = len(t["items"]) - len(shown)
            if extra > 0:
                more = QLabel(f"+{extra}")
                more.setObjectName("muted")
                more.setStyleSheet("font-size: 12px;")
                row.addWidget(more)
            row.addStretch()
            preview.addLayout(row)
        v.addLayout(preview)

        count = sum(len(t["items"]) for t in d.get("tiers", [])) + len(d.get("pool", []))
        date = time.strftime("%d.%m.%Y", time.localtime(d.get("updated", 0)))
        meta = QLabel(f"{count} öğe · {date}")
        meta.setObjectName("muted")
        meta.setStyleSheet("font-size: 12px;")
        v.addWidget(meta)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        edit = QPushButton("Düzenle")
        edit.clicked.connect(lambda _=False: on_edit(d))
        dele = QPushButton("Sil")
        dele.setObjectName("danger")
        dele.clicked.connect(lambda _=False: on_delete(d))
        btns.addWidget(edit)
        btns.addWidget(dele)
        btns.addStretch()
        v.addLayout(btns)


class ListView(QWidget):
    new_requested = Signal()
    edit_requested = Signal(dict)
    delete_requested = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(18)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        t = QLabel("Tier Listeleri")
        t.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.count = QLabel("")
        self.count.setObjectName("muted")
        titles.addWidget(t)
        titles.addWidget(self.count)
        head.addLayout(titles)
        head.addStretch()

        fab = QPushButton("+")
        fab.setObjectName("fab")
        fab.setToolTip("Yeni tier listesi")
        fab.clicked.connect(lambda _=False: self.new_requested.emit())
        head.addWidget(fab)
        root.addLayout(head)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Ara: liste adı veya etiket...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _=None: self.refresh())
        root.addWidget(self.search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.host = QWidget()
        self.grid = QGridLayout(self.host)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.grid.setSpacing(16)
        scroll.setWidget(self.host)
        root.addWidget(scroll, 1)

    def refresh(self):
        clear_layout(self.grid)
        q = self.search.text().strip().lower()
        all_lists = load_all()
        shown = [
            d for d in all_lists
            if not q
            or q in d.get("title", "").lower()
            or any(q in t["name"].lower() for t in d.get("tags", []))
        ]
        suffix = f" · {len(all_lists)} toplam" if q else ""
        self.count.setText(f"{len(shown)} liste{suffix}")
        if not shown:
            msg = QLabel("Sonuç bulunamadı." if q else "Henüz liste yok. + ile yeni bir tier listesi oluştur.")
            msg.setObjectName("muted")
            self.grid.addWidget(msg, 0, 0)
            return
        for i, d in enumerate(shown):
            card = ListCard(d, self.edit_requested.emit, self.delete_requested.emit)
            self.grid.addWidget(card, i // 2, i % 2)


# ---------------------------------------------------------------- Editör
class Editor(QWidget):
    closed = Signal()

    def __init__(self, data):
        super().__init__()
        self.setObjectName("root")
        self.state = copy.deepcopy(data)
        view = self.state.setdefault("view", {})
        view.setdefault("size", DEFAULT_VIEW["size"])
        view.setdefault("fit", DEFAULT_VIEW["fit"])

        self.zones = []
        self.ctrls = []
        self.label_edits = []
        self.row_frames = []
        self.ghost = None
        self.drag_thumb = None
        self.tag_color = TAG_COLORS[len(self.state["tags"]) % len(TAG_COLORS)]

        self.autoscroll = QTimer(self)
        self.autoscroll.setInterval(30)
        self.autoscroll.timeout.connect(self._autoscroll)
        self.view_timer = QTimer(self)
        self.view_timer.setSingleShot(True)
        self.view_timer.setInterval(150)
        self.view_timer.timeout.connect(self.apply_view)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(14)

        # Üst bar
        top = QHBoxLayout()
        back = QPushButton("← Listeler")
        back.clicked.connect(lambda _=False: self.go_back())
        self.title_edit = QLineEdit(self.state.get("title", ""))
        self.title_edit.setPlaceholderText("Liste adı (ör. En iyi filmler)")
        self.title_edit.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px 12px;")
        self.title_edit.textChanged.connect(self.on_title)
        top.addWidget(back)
        top.addWidget(self.title_edit, 1)
        root.addLayout(top)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 8, 0)
        bl.setSpacing(16)

        # Etiketler (sadece uygulamada görünür)
        tag_box = QFrame()
        tag_box.setObjectName("card")
        tv = QVBoxLayout(tag_box)
        tv.setContentsMargins(16, 14, 16, 14)
        tv.setSpacing(8)
        hdr = QLabel("Etiketler")
        hdr.setStyleSheet("font-weight: bold;")
        tv.addWidget(hdr)
        tag_row = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Etiket yaz, rengini seç, Enter'a bas (ör. Oyun, Film)")
        self.tag_input.returnPressed.connect(self.add_tag)
        self.tag_color_btn = QPushButton()
        self.tag_color_btn.setFixedSize(38, 34)
        self.tag_color_btn.setToolTip("Etiket rengini seç")
        self.tag_color_btn.setCursor(Qt.PointingHandCursor)
        self.tag_color_btn.clicked.connect(lambda _=False: self.pick_tag_color())
        add_tag = QPushButton("Ekle")
        add_tag.clicked.connect(lambda _=False: self.add_tag())
        tag_row.addWidget(self.tag_input, 1)
        tag_row.addWidget(self.tag_color_btn)
        tag_row.addWidget(add_tag)
        tv.addLayout(tag_row)
        self.tag_host = QWidget()
        self.tag_layout = QHBoxLayout(self.tag_host)
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.setSpacing(6)
        tv.addWidget(self.tag_host)
        hint = QLabel("Etiketler yalnızca uygulamada görünür, JPG'ye eklenmez.")
        hint.setObjectName("muted")
        hint.setStyleSheet("font-size: 12px;")
        tv.addWidget(hint)
        bl.addWidget(tag_box)

        # Görünüm: görsel boyutu ve sığdırma
        view_box = QFrame()
        view_box.setObjectName("card")
        vv = QHBoxLayout(view_box)
        vv.setContentsMargins(16, 12, 16, 12)
        vv.setSpacing(12)
        vv.addWidget(QLabel("Görsel boyutu"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(CELL_MIN, CELL_MAX)
        self.size_slider.setValue(self.state["view"]["size"])
        self.size_slider.setMinimumWidth(160)
        self.size_slider.valueChanged.connect(self.on_size_slider)
        vv.addWidget(self.size_slider, 1)
        self.size_label = QLabel(f"{self.state['view']['size']} px")
        self.size_label.setObjectName("muted")
        self.size_label.setMinimumWidth(50)
        vv.addWidget(self.size_label)
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        tips = {
            "cover": "Görseli kareyi dolduracak şekilde ortadan kırpar. Hepsi aynı boyutta görünür.",
            "contain": "Görselin tamamını gösterir. Dikey ve yatay görsellerin kenarlarında boşluk kalır.",
        }
        for key, label in (("cover", "Doldur"), ("contain", "Sığdır")):
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(self.state["view"]["fit"] == key)
            b.setToolTip(tips[key])
            b.clicked.connect(lambda _=False, k=key: self.set_fit(k))
            grp.addButton(b)
            vv.addWidget(b)
        bl.addWidget(view_box)

        # Tier tahtası (JPG olarak dışa aktarılan kısım)
        self.board = QFrame()
        self.board.setObjectName("board")
        bv = QVBoxLayout(self.board)
        bv.setContentsMargins(12, 12, 12, 12)
        bv.setSpacing(4)
        self.board_title = QLabel()
        self.board_title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 4px; background: transparent;")
        bv.addWidget(self.board_title)
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(4)
        bv.addLayout(self.rows_layout)
        bl.addWidget(self.board)

        add_row = QHBoxLayout()
        add_tier = QPushButton("+ Tier Ekle")
        add_tier.clicked.connect(lambda _=False: self.add_tier())
        add_row.addWidget(add_tier)
        add_row.addStretch()
        bl.addLayout(add_row)

        # Havuz (henüz yerleştirilmemiş öğeler)
        pool_box = QFrame()
        pool_box.setObjectName("card")
        pv = QHBoxLayout(pool_box)
        pv.setContentsMargins(16, 12, 16, 12)
        pv.setSpacing(14)
        col = QVBoxLayout()
        ph = QLabel("Havuz")
        ph.setStyleSheet("font-weight: bold;")
        pn = QLabel("Görseli fareyle tutup bir tier'a sürükle. Aynı satırda sürükleyerek sırayı değiştirebilirsin.")
        pn.setObjectName("muted")
        pn.setStyleSheet("font-size: 12px;")
        pn.setWordWrap(True)
        col.addWidget(ph)
        col.addWidget(pn)
        self.pool_zone = DropZone(("pool", None), self.cell)
        col.addWidget(self.pool_zone)
        pv.addLayout(col, 1)

        fab = QPushButton("+")
        fab.setObjectName("fab")
        fab.setToolTip("Görsel ekle")
        fab.clicked.connect(lambda _=False: self.add_images())
        pv.addWidget(fab, 0, Qt.AlignTop)
        bl.addWidget(pool_box)
        bl.addStretch()

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(body)
        root.addWidget(self.scroll, 1)

        # Alt bar
        bar = QHBoxLayout()
        dele = QPushButton("Sil")
        dele.setObjectName("danger")
        dele.clicked.connect(lambda _=False: self.delete())
        bar.addWidget(dele)
        bar.addStretch()
        jpg = QPushButton("JPG Olarak İndir")
        jpg.clicked.connect(lambda _=False: self.export_jpg())
        save = QPushButton("Kaydet")
        save.setObjectName("primary")
        save.clicked.connect(lambda _=False: self.save())
        bar.addWidget(jpg)
        bar.addWidget(save)
        root.addLayout(bar)

        self.on_title(self.state.get("title", ""))
        self.paint_tag_btn()
        self.refresh_tags()
        self.build_tiers()

    def cell(self):
        return self.state["view"]["size"]

    # --- başlık
    def on_title(self, txt):
        self.state["title"] = txt
        self.board_title.setText(txt or "Tier Listesi")

    # --- etiketler
    def paint_tag_btn(self):
        self.tag_color_btn.setStyleSheet(
            f"QPushButton {{ background: {self.tag_color}; border: 1px solid #888; border-radius: 8px; padding: 0; }}"
            f"QPushButton:hover {{ border-color: {GOLD}; }}"
        )

    def pick_tag_color(self):
        c = QColorDialog.getColor(QColor(self.tag_color), self, "Etiket rengi")
        if c.isValid():
            self.tag_color = c.name()
            self.paint_tag_btn()

    def add_tag(self):
        name = self.tag_input.text().strip()
        if not name:
            return
        self.tag_input.clear()
        if any(t["name"].lower() == name.lower() for t in self.state["tags"]):
            return
        self.state["tags"].append({"name": name, "color": self.tag_color})
        # Bir sonraki etiket için varsayılan rengi ilerlet (istenirse yine değiştirilebilir)
        self.tag_color = TAG_COLORS[len(self.state["tags"]) % len(TAG_COLORS)]
        self.paint_tag_btn()
        self.refresh_tags()

    def remove_tag(self, name):
        self.state["tags"] = [t for t in self.state["tags"] if t["name"] != name]
        self.refresh_tags()

    def refresh_tags(self):
        clear_layout(self.tag_layout)
        for t in self.state["tags"]:
            self.tag_layout.addWidget(
                make_chip(t["name"], t["color"], lambda n=t["name"]: self.remove_tag(n))
            )
        self.tag_layout.addStretch()

    # --- görünüm (boyut / sığdırma)
    def on_size_slider(self, v):
        self.state["view"]["size"] = v
        self.size_label.setText(f"{v} px")
        self.view_timer.start()

    def set_fit(self, fit):
        self.state["view"]["fit"] = fit
        self.apply_view()

    def apply_view(self):
        _THUMBS.clear()
        self.refresh_items()

    # --- tier'lar
    def build_tiers(self):
        """Tier satırlarını state'e göre baştan kurar."""
        clear_layout(self.rows_layout)
        self.zones = []
        self.ctrls = []
        self.label_edits = []
        self.row_frames = []
        tiers = self.state["tiers"]
        n = len(tiers)
        for i, t in enumerate(tiers):
            row = QFrame()
            row.setObjectName("tierrow")
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(0)

            lbl = QLineEdit(t["label"])
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedWidth(104)
            lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            lbl.setStyleSheet(
                f"QLineEdit {{ background: {t['color']}; color: {text_on(t['color'])}; border: none;"
                f" border-radius: 0px; font-size: 20px; font-weight: bold; padding: 4px; }}"
            )
            lbl.textChanged.connect(lambda txt, idx=i: self.set_label(idx, txt))

            zone = DropZone(("tier", i), self.cell)
            row.drop_zone = zone      # satırın herhangi bir yerine bırakılınca bu alana eklenir

            ctrl = self.make_tier_ctrl(i, n, t["color"])

            h.addWidget(lbl)
            h.addWidget(zone, 1)
            h.addWidget(ctrl, 0, Qt.AlignVCenter)
            self.rows_layout.addWidget(row)
            self.zones.append(zone)
            self.ctrls.append(ctrl)
            self.label_edits.append(lbl)
            self.row_frames.append(row)
        self.refresh_items()

    def make_tier_ctrl(self, i, n, color):
        """Tier satırının sağındaki kontroller: yukarı, aşağı, renk, sil. JPG'ye eklenmez."""
        w = QWidget()
        w.setFixedWidth(56)
        sp = w.sizePolicy()
        sp.setRetainSizeWhenHidden(True)    # gizlenince JPG'de yerleşim bozulmasın
        w.setSizePolicy(sp)
        g = QGridLayout(w)
        g.setContentsMargins(6, 6, 6, 6)
        g.setSpacing(4)

        up = QPushButton("▲")
        up.setObjectName("mini")
        up.setToolTip("Yukarı taşı")
        up.setEnabled(i > 0)
        up.clicked.connect(lambda _=False, idx=i: self.move_tier(idx, -1))

        down = QPushButton("▼")
        down.setObjectName("mini")
        down.setToolTip("Aşağı taşı")
        down.setEnabled(i < n - 1)
        down.clicked.connect(lambda _=False, idx=i: self.move_tier(idx, 1))

        col = QPushButton()
        col.setObjectName("mini")
        col.setToolTip("Tier rengini değiştir")
        col.setCursor(Qt.PointingHandCursor)
        col.setStyleSheet(
            f"QPushButton {{ background: {color}; border: 1px solid #888; border-radius: 5px; padding: 0;"
            f" min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; }}"
            f"QPushButton:hover {{ border-color: {GOLD}; }}"
        )
        col.clicked.connect(lambda _=False, idx=i: self.change_tier_color(idx))

        dele = QPushButton("✕")
        dele.setObjectName("mini")
        dele.setToolTip("Tier'ı sil")
        dele.setEnabled(n > 1)
        dele.clicked.connect(lambda _=False, idx=i: self.delete_tier(idx))

        g.addWidget(up, 0, 0)
        g.addWidget(down, 0, 1)
        g.addWidget(col, 1, 0)
        g.addWidget(dele, 1, 1)
        return w

    def set_label(self, idx, txt):
        if 0 <= idx < len(self.state["tiers"]):
            self.state["tiers"][idx]["label"] = txt

    def add_tier(self):
        default = TIERS[len(self.state["tiers"]) % len(TIERS)][1]
        c = QColorDialog.getColor(QColor(default), self, "Yeni tier rengi")
        if not c.isValid():
            return
        self.state["tiers"].append({"label": "Yeni", "color": c.name(), "items": []})
        self.build_tiers()
        last = self.label_edits[-1]
        last.setFocus()
        last.selectAll()
        QTimer.singleShot(0, lambda: self.scroll.ensureWidgetVisible(self.row_frames[-1]))

    def change_tier_color(self, i):
        c = QColorDialog.getColor(QColor(self.state["tiers"][i]["color"]), self, "Tier rengi")
        if c.isValid():
            self.state["tiers"][i]["color"] = c.name()
            self.build_tiers()

    def move_tier(self, i, d):
        tiers = self.state["tiers"]
        j = i + d
        if 0 <= j < len(tiers):
            tiers[i], tiers[j] = tiers[j], tiers[i]
            self.build_tiers()

    def delete_tier(self, i):
        tiers = self.state["tiers"]
        if len(tiers) <= 1:
            return
        t = tiers[i]
        if t["items"]:
            r = QMessageBox.question(
                self, "Tier'ı sil",
                f"'{t['label']}' tier'ındaki {len(t['items'])} görsel havuza taşınacak. Devam edilsin mi?",
            )
            if r != QMessageBox.StandardButton.Yes:
                return
            self.state["pool"].extend(t["items"])
        del tiers[i]
        self.build_tiers()

    # --- öğeler
    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Görsel seç", "", "Görseller (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
        )
        if not files:
            return
        IMG_DIR.mkdir(parents=True, exist_ok=True)
        for f in files:
            dst = IMG_DIR / f"{uuid.uuid4().hex}{Path(f).suffix.lower()}"
            shutil.copy(f, dst)
            self.state["pool"].append(str(dst))
        self.refresh_items()

    def locate(self, path):
        for i, t in enumerate(self.state["tiers"]):
            if path in t["items"]:
                return ("tier", i)
        return ("pool", None)

    def move_item(self, path, dest, index=None):
        """Öğeyi hedef listeye taşır. index verilirse o sıraya ekler (sıra değiştirme)."""
        if dest[0] == "tier":
            target = self.state["tiers"][dest[1]]["items"]
        elif dest[0] == "pool":
            target = self.state["pool"]
        else:
            target = None  # listeden kaldır

        all_lists = [t["items"] for t in self.state["tiers"]] + [self.state["pool"]]
        for lst in all_lists:
            if path in lst:
                # Aynı listede öndeki öğe çıkarılınca hedef indeks bir kayar
                if lst is target and index is not None and lst.index(path) < index:
                    index -= 1
                lst.remove(path)

        if target is not None:
            if index is None or index > len(target):
                target.append(path)
            else:
                target.insert(index, path)
        self.refresh_items()

    def show_item_menu(self, path, pos):
        menu = QMenu(self)
        here = self.locate(path)
        for i, t in enumerate(self.state["tiers"]):
            if here == ("tier", i):
                continue
            act = menu.addAction(f"{t['label']} sırasına taşı")
            act.triggered.connect(lambda _=False, p=path, d=("tier", i): self.move_item(p, d))
        if here != ("pool", None):
            act = menu.addAction("Havuza taşı")
            act.triggered.connect(lambda _=False, p=path: self.move_item(p, ("pool", None)))
        menu.addSeparator()
        act = menu.addAction("Listeden kaldır")
        act.triggered.connect(lambda _=False, p=path: self.move_item(p, ("remove", None)))
        menu.exec(pos)

    def make_thumb(self, parent, path):
        v = self.state["view"]
        return ItemThumb(parent, path, self, v["size"], v["fit"])

    def refresh_items(self):
        for i, zone in enumerate(self.zones):
            zone.set_items(self.state["tiers"][i]["items"], self.make_thumb)
        self.pool_zone.set_items(self.state["pool"], self.make_thumb)

    # --- sürükleme: imleçte görünen hayalet görsel ve kenarlarda otomatik kaydırma
    def drag_begin(self, thumb):
        self.drag_thumb = thumb
        pm = thumb.pixmap()
        if pm is None or pm.isNull():
            pm = QPixmap(thumb.size())
            pm.fill(QColor(PANEL_2))
        g = QLabel(self.window())
        g.setAttribute(Qt.WA_TransparentForMouseEvents)
        g.setPixmap(pm)
        g.setFixedSize(pm.width() + 4, pm.height() + 4)
        g.setAlignment(Qt.AlignCenter)
        g.setStyleSheet(f"QLabel {{ background: {PANEL_2}; border: 2px solid {GOLD}; border-radius: 6px; }}")
        eff = QGraphicsOpacityEffect(g)
        eff.setOpacity(0.9)
        g.setGraphicsEffect(eff)
        g.show()
        g.raise_()
        self.ghost = g

        dim = QGraphicsOpacityEffect(thumb)
        dim.setOpacity(0.35)
        thumb.setGraphicsEffect(dim)
        self.autoscroll.start()

    def drag_move(self, gp):
        if self.ghost is None:
            return
        top_left = self.window().mapFromGlobal(gp) - QPoint(self.ghost.width() // 2, self.ghost.height() // 2)
        self.ghost.move(top_left)

    def drag_end(self):
        self.autoscroll.stop()
        if self.ghost is not None:
            self.ghost.hide()
            self.ghost.deleteLater()
            self.ghost = None
        if self.drag_thumb is not None:
            try:
                self.drag_thumb.setGraphicsEffect(None)
            except RuntimeError:
                pass
            self.drag_thumb = None

    def _autoscroll(self):
        if self.drag_thumb is None:
            return
        gp = QCursor.pos()
        vp = self.scroll.viewport()
        top = vp.mapToGlobal(QPoint(0, 0)).y()
        bottom = top + vp.height()
        edge = 60
        step = 0
        if gp.y() < top + edge:
            step = -int((top + edge - gp.y()) / 4 + 4)
        elif gp.y() > bottom - edge:
            step = int((gp.y() - (bottom - edge)) / 4 + 4)
        if step:
            bar = self.scroll.verticalScrollBar()
            bar.setValue(bar.value() + step)
            self.drag_thumb.update_hover(gp)

    # --- eylemler
    def export_jpg(self):
        default = f"{(self.state.get('title') or 'tier-listesi').strip()}.jpg"
        path, _ = QFileDialog.getSaveFileName(self, "JPG olarak kaydet", default, "JPEG (*.jpg *.jpeg)")
        if not path:
            return
        if not path.lower().endswith((".jpg", ".jpeg")):
            path += ".jpg"
        fw = QApplication.focusWidget()
        if fw is not None:
            fw.clearFocus()
        for c in self.ctrls:      # tier düzenleme düğmeleri JPG'de görünmesin
            c.hide()
        try:
            pm = self.board.grab()
        finally:
            for c in self.ctrls:
                c.show()
        if pm.save(path, "JPG", 95):
            QMessageBox.information(self, "Tamam", "Görsel kaydedildi.")
        else:
            QMessageBox.warning(self, "Hata", "Görsel kaydedilemedi.")

    def save(self):
        if not self.state.get("title", "").strip():
            self.state["title"] = "İsimsiz Liste"
        self.state["updated"] = time.time()
        save_list(self.state)
        self.closed.emit()

    def delete(self):
        if QMessageBox.question(self, "Sil", "Bu liste silinsin mi?") == QMessageBox.StandardButton.Yes:
            delete_list(self.state)
            self.closed.emit()

    def go_back(self):
        if QMessageBox.question(self, "Çık", "Kaydetmeden çıkmak istiyor musun?") == QMessageBox.StandardButton.Yes:
            self.closed.emit()


# ---------------------------------------------------------------- Ana pencere
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tier List Maker")
        self.resize(1200, 800)
        self.stack = QStackedWidget()
        self.list_view = ListView()
        self.list_view.new_requested.connect(lambda: self.open_editor(new_data()))
        self.list_view.edit_requested.connect(self.open_editor)
        self.list_view.delete_requested.connect(self.confirm_delete)
        self.stack.addWidget(self.list_view)
        self.setCentralWidget(self.stack)
        self.list_view.refresh()

    def open_editor(self, data):
        ed = Editor(data)
        ed.closed.connect(lambda ed=ed: self.close_editor(ed))
        self.stack.addWidget(ed)
        self.stack.setCurrentWidget(ed)

    def close_editor(self, ed):
        ed.drag_end()
        self.stack.setCurrentWidget(self.list_view)
        self.stack.removeWidget(ed)
        ed.deleteLater()
        self.list_view.refresh()

    def confirm_delete(self, d):
        name = d.get("title") or "İsimsiz Liste"
        if QMessageBox.question(self, "Sil", f"'{name}' silinsin mi?") == QMessageBox.StandardButton.Yes:
            delete_list(d)
            self.list_view.refresh()


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TierListMaker.App")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("Tier List Maker")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    icon_file = resource_path("assets/icon.ico")
    if os.path.exists(icon_file):
        app.setWindowIcon(QIcon(icon_file))
    else:
        app.setWindowIcon(QIcon.fromTheme("tierlist-maker"))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
