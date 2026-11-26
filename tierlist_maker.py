#!/usr/bin/python3
"""Tier List Maker - S'den F'ye tier listesi uygulaması (PySide6)."""
import copy
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QScrollArea, QFileDialog,
    QMessageBox, QMenu, QStackedWidget,
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

COLS = 9                      # editörde bir satırdaki öğe sayısı
THUMB_W, THUMB_H = 92, 64     # editör öğe boyutu
PREVIEW_W, PREVIEW_H = 40, 28 # kart önizleme öğe boyutu
PREVIEW_MAX = 10              # kartta satır başına gösterilen öğe sayısı
CARD_W = 560


def rgba(hex_, a):
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def text_on(bg):
    return "#111111" if bg.lower() in ("#ffcf33", "#ffa62b") else "#ffffff"


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
QPushButton#primary {{ background: {GOLD}; color: #14110a; border: none; font-weight: bold; }}
QPushButton#primary:hover {{ background: {GOLD_HOVER}; color: #14110a; }}
QPushButton#danger {{ color: {DANGER}; border-color: {rgba(DANGER, 0.5)}; background: transparent; }}
QPushButton#danger:hover {{ background: {rgba(DANGER, 0.12)}; }}
QPushButton#fab {{ background: {GOLD}; color: #14110a; border: none; border-radius: 28px;
                  font-size: 26px; font-weight: bold; padding: 0;
                  min-width: 56px; max-width: 56px; min-height: 56px; max-height: 56px; }}
QPushButton#fab:hover {{ background: {GOLD_HOVER}; color: #14110a; }}
QFrame#card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#board {{ background: #1a1a1a; border-radius: 10px; }}
QFrame#tierrow {{ background: #262626; border-radius: 6px; }}
QMenu {{ background: {PANEL_2}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; }}
QMenu::item:selected {{ background: {rgba(GOLD, 0.2)}; color: {GOLD}; }}
QLabel#muted {{ color: {MUTED}; }}
"""


# ---------------------------------------------------------------- Veri
def new_data():
    return {
        "id": uuid.uuid4().hex,
        "title": "",
        "tags": [],
        "tiers": [{"label": n, "color": c, "items": []} for n, c in TIERS],
        "pool": [],
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
            w.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def make_chip(text, color, on_remove=None):
    chip = QFrame()
    chip.setObjectName("chip")
    chip.setStyleSheet(
        f"QFrame#chip {{ background: {rgba(color, 0.18)}; border: 1px solid {rgba(color, 0.6)};"
        f" border-radius: 10px; }}"
        f"QLabel {{ background: transparent; border: none; color: {color};"
        f" font-size: 12px; font-weight: bold; }}"
        f"QPushButton {{ background: transparent; border: none; color: {color};"
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
    """Öğelerin bırakılabildiği alan: bir tier satırı ya da havuz."""

    def __init__(self, dest):
        super().__init__()
        self.dest = dest
        self.setObjectName("dropzone")

    def set_highlight(self, on):
        if on:
            self.setStyleSheet(
                f"QFrame#dropzone {{ background: {rgba(GOLD, 0.12)};"
                f" border: 1px dashed {GOLD}; border-radius: 6px; }}"
            )
        else:
            self.setStyleSheet("")

    def index_at(self, pos):
        """Verilen noktaya en yakın öğeye göre ekleme sırasını döndürür."""
        lay = self.layout()
        thumbs = []
        if lay is not None:
            for i in range(lay.count()):
                w = lay.itemAt(i).widget()
                if isinstance(w, ItemThumb):
                    thumbs.append(w)
        if not thumbs:
            return 0
        best = min(range(len(thumbs)),
                   key=lambda i: (thumbs[i].geometry().center() - pos).manhattanLength())
        c = thumbs[best].geometry().center()
        return best if pos.x() < c.x() else best + 1


def zone_at(global_pos):
    """Ekrandaki bir noktanın altındaki DropZone'u bulur."""
    w = QApplication.widgetAt(global_pos)
    while w is not None:
        if isinstance(w, DropZone):
            return w
        w = w.parentWidget()
    return None


# ---------------------------------------------------------------- Öğe
class ItemThumb(QLabel):
    """Editördeki bir görsel. Fare ile sürüklenip başka bir yere bırakılabilir."""

    def __init__(self, path, on_menu, on_drop):
        super().__init__()
        self.path = path
        self.on_menu = on_menu
        self.on_drop = on_drop
        self._press = None
        self._dragging = False
        self._hover_zone = None

        pm = QPixmap(path)
        if not pm.isNull():
            self.setPixmap(pm.scaled(THUMB_W, THUMB_H, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.setText("?")
        self.setFixedSize(THUMB_W, THUMB_H)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"QLabel {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px; }}")
        self.setCursor(Qt.OpenHandCursor)

    def contextMenuEvent(self, e):
        self.on_menu(self.path, e.globalPos())

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press = e.globalPosition().toPoint()
            self._dragging = False
        e.accept()

    def mouseMoveEvent(self, e):
        if self._press is None or not (e.buttons() & Qt.LeftButton):
            return
        gp = e.globalPosition().toPoint()
        if not self._dragging:
            if (gp - self._press).manhattanLength() < QApplication.startDragDistance():
                return
            self._dragging = True
            self.setCursor(Qt.ClosedHandCursor)

        zone = zone_at(gp)
        if zone is not self._hover_zone:
            if self._hover_zone is not None:
                self._hover_zone.set_highlight(False)
            if zone is not None:
                zone.set_highlight(True)
            self._hover_zone = zone

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
        self.setCursor(Qt.OpenHandCursor)

        if was_dragging:
            zone = zone_at(gp)
            if zone is not None:
                index = zone.index_at(zone.mapFromGlobal(gp))
                # Not: move_item bu öğeyi silip yeniden çizeceği için, bundan sonra self'e dokunulmaz.
                self.on_drop(self.path, zone.dest, index)


# ---------------------------------------------------------------- Liste kartı
class ListCard(QFrame):
    def __init__(self, d, on_edit, on_delete):
        super().__init__()
        self.setObjectName("card")
        self.setFixedWidth(CARD_W)
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
            lbl.setFixedSize(38, PREVIEW_H)
            lbl.setStyleSheet(
                f"background: {t['color']}; color: {text_on(t['color'])}; border-radius: 4px;"
                f" font-weight: bold; font-size: 11px;"
            )
            row.addWidget(lbl)

            shown = t["items"][:PREVIEW_MAX]
            for p in shown:
                th = QLabel()
                th.setFixedSize(PREVIEW_W, PREVIEW_H)
                th.setAlignment(Qt.AlignCenter)
                th.setStyleSheet(f"background: {PANEL_2}; border-radius: 3px;")
                pm = QPixmap(p)
                if not pm.isNull():
                    th.setPixmap(pm.scaled(PREVIEW_W, PREVIEW_H, Qt.KeepAspectRatio, Qt.SmoothTransformation))
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
        self.rows = []

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
        self.tag_input.setPlaceholderText("Etiket yaz ve Enter'a bas (ör. Oyun, Film)")
        self.tag_input.returnPressed.connect(self.add_tag)
        add_tag = QPushButton("Ekle")
        add_tag.clicked.connect(lambda _=False: self.add_tag())
        tag_row.addWidget(self.tag_input, 1)
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

        # Tier tahtası (JPG olarak dışa aktarılan kısım)
        self.board = QFrame()
        self.board.setObjectName("board")
        bv = QVBoxLayout(self.board)
        bv.setContentsMargins(12, 12, 12, 12)
        bv.setSpacing(4)
        self.board_title = QLabel()
        self.board_title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 4px; background: transparent;")
        bv.addWidget(self.board_title)

        for i, t in enumerate(self.state["tiers"]):
            row = QFrame()
            row.setObjectName("tierrow")
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(0)

            lbl = QLineEdit(t["label"])
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedWidth(104)
            lbl.setMinimumHeight(THUMB_H + 18)
            lbl.setStyleSheet(
                f"QLineEdit {{ background: {t['color']}; color: {text_on(t['color'])}; border: none;"
                f" border-radius: 0px; font-size: 20px; font-weight: bold; padding: 4px; }}"
            )
            lbl.textChanged.connect(lambda txt, idx=i: self.set_label(idx, txt))

            host = DropZone(("tier", i))
            host.setMinimumHeight(THUMB_H + 18)
            grid = QGridLayout(host)
            grid.setContentsMargins(8, 8, 8, 8)
            grid.setSpacing(6)
            grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)

            h.addWidget(lbl)
            h.addWidget(host, 1)
            bv.addWidget(row)
            self.rows.append(grid)
        bl.addWidget(self.board)

        # Havuz (henüz yerleştirilmemiş öğeler)
        pool_box = QFrame()
        pool_box.setObjectName("card")
        pv = QHBoxLayout(pool_box)
        pv.setContentsMargins(16, 12, 16, 12)
        pv.setSpacing(14)
        col = QVBoxLayout()
        ph = QLabel("Havuz")
        ph.setStyleSheet("font-weight: bold;")
        pn = QLabel("Öğeyi fareyle tutup bir tier satırına sürükle, sıra değiştirmek için de aynı satırda sürükle.")
        pn.setObjectName("muted")
        pn.setStyleSheet("font-size: 12px;")
        pn.setWordWrap(True)
        col.addWidget(ph)
        col.addWidget(pn)
        self.pool_host = DropZone(("pool", None))
        self.pool_host.setMinimumHeight(THUMB_H + 12)
        self.pool_grid = QGridLayout(self.pool_host)
        self.pool_grid.setContentsMargins(0, 0, 0, 0)
        self.pool_grid.setSpacing(6)
        self.pool_grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        col.addWidget(self.pool_host)
        pv.addLayout(col, 1)

        fab = QPushButton("+")
        fab.setObjectName("fab")
        fab.setToolTip("Görsel ekle")
        fab.clicked.connect(lambda _=False: self.add_images())
        pv.addWidget(fab, 0, Qt.AlignVCenter)
        bl.addWidget(pool_box)
        bl.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

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
        self.refresh_tags()
        self.refresh_items()

    # --- başlık / etiket
    def on_title(self, txt):
        self.state["title"] = txt
        self.board_title.setText(txt or "Tier Listesi")

    def set_label(self, idx, txt):
        self.state["tiers"][idx]["label"] = txt

    def add_tag(self):
        name = self.tag_input.text().strip()
        self.tag_input.clear()
        if not name:
            return
        if any(t["name"].lower() == name.lower() for t in self.state["tags"]):
            return
        color = TAG_COLORS[len(self.state["tags"]) % len(TAG_COLORS)]
        self.state["tags"].append({"name": name, "color": color})
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

    def fill_grid(self, grid, paths):
        clear_layout(grid)
        for idx, p in enumerate(paths):
            grid.addWidget(ItemThumb(p, self.show_item_menu, self.move_item), idx // COLS, idx % COLS)

    def refresh_items(self):
        for i, grid in enumerate(self.rows):
            self.fill_grid(grid, self.state["tiers"][i]["items"])
        self.fill_grid(self.pool_grid, self.state["pool"])

    # --- eylemler
    def export_jpg(self):
        default = f"{(self.state.get('title') or 'tier-listesi').strip()}.jpg"
        path, _ = QFileDialog.getSaveFileName(self, "JPG olarak kaydet", default, "JPEG (*.jpg *.jpeg)")
        if not path:
            return
        if not path.lower().endswith((".jpg", ".jpeg")):
            path += ".jpg"
        if self.board.grab().save(path, "JPG", 95):
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
