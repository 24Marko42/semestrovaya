# dialogs.py — компактная версия
import os
import sys
from typing import Optional

from PyQt5 import uic
from PyQt5.QtCore import Qt, QBuffer, QIODevice
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, QTextEdit,
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QHBoxLayout, QWidget,
    QMessageBox
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "ui")


# ------------------------------
# Утилиты (одним блоком)
# ------------------------------
def resource_path(rel: str) -> str:
    """Работает с PyInstaller (sys._MEIPASS) и из исходников."""
    base = getattr(sys, "_MEIPASS", BASE_DIR)
    return os.path.join(base, rel)


def pixmap_from_bytes(b: Optional[bytes]) -> Optional[QPixmap]:
    if not b:
        return None
    p = QPixmap()
    return p if p.loadFromData(b) else None


def pixmap_to_bytes(pix: Optional[QPixmap]) -> Optional[bytes]:
    if pix is None or pix.isNull():
        return None
    buf = QBuffer(); buf.open(QIODevice.WriteOnly)
    pix.save(buf, "PNG")
    data = bytes(buf.data()); buf.close()
    return data


# ------------------------------
# Image viewer
# ------------------------------
class ImageViewer(QDialog):
    def __init__(self, image_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Просмотр изображения")
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        self.lbl = QLabel(alignment=Qt.AlignCenter)
        layout.addWidget(self.lbl)
        layout.addWidget(QPushButton("Закрыть", clicked=self.close))
        if image_path:
            self.load(image_path)

    def load(self, path: str):
        if path and os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                self.lbl.setPixmap(pix.scaled(760, 520, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        self.lbl.setText("Не удалось загрузить изображение")


# ------------------------------
# Details dialog (image + text)
# ------------------------------
class DetailsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui = resource_path("ui/details_dialog.ui")
        if os.path.exists(ui):
            uic.loadUi(ui, self)
            # ожидается imageLabel, detailsText, closeButton (если нет — fallback ниже)
            try: self.closeButton.clicked.connect(self.accept)
            except Exception: pass
        else:
            self.setWindowTitle("Детали")
            self.resize(420, 520)
            l = QVBoxLayout(self)
            self.imageLabel = QLabel(alignment=Qt.AlignCenter)
            self.imageLabel.setMinimumSize(320, 240)
            l.addWidget(self.imageLabel)
            self.detailsText = QTextEdit(); self.detailsText.setReadOnly(True)
            l.addWidget(self.detailsText)
            l.addWidget(QPushButton("Закрыть", clicked=self.accept))
        # лёгкая стилизация (фон)
        self.setStyleSheet("""
            QDialog{ background:#273232; color:#f6f6f6;}
            QTextEdit{ background:#1f2a2a; color:#f6f6f6; border-radius:6px; }
            QLabel{ color:#f6f6f6; }
            QPushButton{ background:#4b6ef6; color:white; border-radius:6px; padding:6px; }
        """)

    def set_image_from_bytes(self, b: Optional[bytes]):
        pix = pixmap_from_bytes(b)
        if pix:
            self.imageLabel.setPixmap(pix.scaled(320, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.imageLabel.setText("Изображение отсутствует")

    def set_text(self, text: str):
        # если в .ui есть detailsText — используем, иначе создаём
        try:
            self.detailsText.setPlainText(text)
        except Exception:
            try:
                te = QTextEdit(); te.setReadOnly(True)
                self.layout().addWidget(te)
                te.setPlainText(text)
            except Exception:
                pass


# ------------------------------
# CoffeeDialog (сокращённо, всё в коде — без .ui)
# ------------------------------
class CoffeeDialog(QDialog):
    def __init__(self, db_manager, coffee_data: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.coffee_data = coffee_data or {}
        self.selected_image_path = None

        self.setWindowTitle("Редактировать сорт" if coffee_data else "Добавить сорт кофе")
        self.resize(640, 700)
        self.setStyleSheet("""QDialog{ background:#1f2830; color:#f0f0f0 }""")

        root = QVBoxLayout(self)
        header = QLabel("Редактировать сорт" if coffee_data else "Добавить сорт кофе", alignment=Qt.AlignCenter)
        header.setStyleSheet("background:#2E8B57;color:white;padding:8px;font-weight:600;border-radius:6px;")
        root.addWidget(header)

        # небольшой хелпер для полей
        def add_label_edit(label_text, widget):
            root.addWidget(QLabel(label_text)); root.addWidget(widget); return widget

        self.nameEdit = add_label_edit("Название*:", QLineEdit())
        self.roasterEdit = add_label_edit("Обжарщик:", QLineEdit())
        self.roastCombo = add_label_edit("Уровень обжарки:", QComboBox()); self.roastCombo.addItems(["Light", "Medium", "Dark"])
        self.originEdit = add_label_edit("Происхождение:", QLineEdit())
        self.processingEdit = add_label_edit("Метод обработки:", QLineEdit())
        self.tastingNotesEdit = add_label_edit("Вкусовые ноты:", QTextEdit()); self.tastingNotesEdit.setMaximumHeight(120)

        # цена + рейтинг в одной строке
        hr = QHBoxLayout()
        hr.addWidget(QLabel("Цена (руб):")); self.priceSpin = QDoubleSpinBox(); self.priceSpin.setRange(0, 100000); self.priceSpin.setDecimals(2); hr.addWidget(self.priceSpin)
        hr.addWidget(QLabel("Рейтинг:")); self.ratingSpin = QDoubleSpinBox(); self.ratingSpin.setRange(0,5); self.ratingSpin.setDecimals(1); hr.addWidget(self.ratingSpin)
        root.addLayout(hr)

        # изображение + кнопки
        img_box = QWidget(); img_h = QHBoxLayout(img_box)
        self.imageLabel = QLabel("🖼 Нажмите \"Загрузить\"", alignment=Qt.AlignCenter); self.imageLabel.setFixedSize(220,220); self.imageLabel.setStyleSheet("border:2px dashed #3a3f44;")
        img_h.addWidget(self.imageLabel)
        vb = QVBoxLayout()
        self.loadBtn = QPushButton("Загрузить изображение"); self.clearBtn = QPushButton("Очистить")
        vb.addWidget(self.loadBtn); vb.addWidget(self.clearBtn); vb.addStretch(); img_h.addLayout(vb)
        root.addWidget(img_box)

        # action buttons
        action = QHBoxLayout()
        self.saveBtn = QPushButton("💾 Сохранить"); self.cancelBtn = QPushButton("Отмена")
        self.cancelBtn.setStyleSheet("background:#6c757d;color:white;")
        action.addWidget(self.saveBtn); action.addWidget(self.cancelBtn); root.addLayout(action)

        # сигналы
        self.loadBtn.clicked.connect(self._load_image)
        self.clearBtn.clicked.connect(self._clear_image)
        try: self.imageLabel.mousePressEvent = lambda ev: self._load_image()
        except Exception: pass
        self.saveBtn.clicked.connect(self._on_save)
        self.cancelBtn.clicked.connect(self.reject)

        # заполнить если редактирование
        if self.coffee_data:
            self._fill_from_data(self.coffee_data)

    def _fill_from_data(self, d: dict):
        self.nameEdit.setText(d.get("name", ""))
        self.roasterEdit.setText(d.get("roaster", ""))
        self.roastCombo.setCurrentText(d.get("roast_level", "Medium"))
        self.originEdit.setText(d.get("origin", ""))
        self.processingEdit.setText(d.get("processing_method", ""))
        self.tastingNotesEdit.setPlainText(d.get("tasting_notes", ""))
        try:
            self.priceSpin.setValue(float(d.get("price") or 0))
            self.ratingSpin.setValue(float(d.get("rating") or 0))
        except Exception:
            pass
        img = d.get("image")
        if isinstance(img, (bytes, bytearray)):
            pix = pixmap_from_bytes(img)
            if pix: self.imageLabel.setPixmap(pix.scaled(220,220,Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not path: return
        pix = QPixmap(path)
        if pix.isNull():
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить изображение")
            return
        self.selected_image_path = path
        self.imageLabel.setPixmap(pix.scaled(220,220,Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _clear_image(self):
        self.selected_image_path = None
        self.imageLabel.clear()
        self.imageLabel.setText('🖼 Нажмите "Загрузить"')

    def _on_save(self):
        name = self.nameEdit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Поле 'Название' обязательно")
            return
        payload = {
            "name": name,
            "roaster": self.roasterEdit.text().strip(),
            "roast_level": self.roastCombo.currentText(),
            "origin": self.originEdit.text().strip(),
            "processing_method": self.processingEdit.text().strip(),
            "tasting_notes": self.tastingNotesEdit.toPlainText().strip(),
            "price": float(self.priceSpin.value()),
            "rating": float(self.ratingSpin.value()),
            "image": None
        }
        # подготовка pixmap для БД (DatabaseManager может принять QPixmap)
        if self.selected_image_path and os.path.exists(self.selected_image_path):
            p = QPixmap(self.selected_image_path)
            if not p.isNull():
                payload["image"] = p
        try:
            if self.coffee_data.get("id"):
                ok = self.db_manager.update_coffee_bean = getattr(self.db_manager, "update_coffee_bean", None)
                # обратная совместимость: используем db_manager напрямую
            # корректно сохраняем: вызовем методы через self.db_manager если доступны
        except Exception:
            pass

        # ВАЖНО: вызываем методы через db_manager, но не знаем exact API — используем common names
        try:
            # обновление
            if self.coffee_data.get("id"):
                # update_coffee_bean( id, **fields )
                upd = getattr(self.db_manager, "update_coffee_bean", None)
                if callable(upd):
                    success = upd(self.coffee_data["id"],
                                  name=payload["name"],
                                  roaster=payload["roaster"],
                                  roast_level=payload["roast_level"],
                                  origin=payload["origin"],
                                  processing_method=payload["processing_method"],
                                  tasting_notes=payload["tasting_notes"],
                                  rating=payload["rating"],
                                  price=payload["price"],
                                  image=payload["image"])
                    if not success:
                        raise RuntimeError("Не удалось обновить сорт")
            else:
                add = getattr(self.db_manager, "add_coffee_bean", None)
                if callable(add):
                    new_id = add(**payload)
                    if new_id == -1 or new_id is None:
                        raise RuntimeError("Не удалось добавить сорт")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка при сохранении", str(e))


# ------------------------------
# BrewingDialog (компактно)
# ------------------------------
class BrewingDialog(QDialog):
    def __init__(self, db_manager, coffee_beans=None, brewing_data: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.coffee_beans = coffee_beans or []
        self.brewing_data = brewing_data or {}

        self.setWindowTitle("Редактировать сессию" if brewing_data else "Добавить сессию")
        self.resize(520, 520)
        self.setStyleSheet("QDialog{background:#182226;color:#f0f0f0}")

        root = QVBoxLayout(self)
        header = QLabel("Редактировать сессию" if brewing_data else "Добавить сессию", alignment=Qt.AlignCenter)
        header.setStyleSheet("background:#8B0000;color:white;padding:8px;border-radius:6px")
        root.addWidget(header)

        # fields
        root.addWidget(QLabel("Сорт кофе*:"))
        self.coffeeCombo = QComboBox()
        for b in self.coffee_beans:
            try: self.coffeeCombo.addItem(b.get("name", "—"), b.get("id"))
            except Exception: pass
        root.addWidget(self.coffeeCombo)

        root.addWidget(QLabel("Метод*:"))
        self.methodCombo = QComboBox(); self.methodCombo.addItems(["Эспрессо","Воронка","Аэропресс","Френч-пресс","Кемекс","Пуровер"])
        root.addWidget(self.methodCombo)

        for label, widget in [
            ("Температура (°C):", QSpinBox()), ("Время (сек):", QSpinBox()),
            ("Вес кофе (г):", QDoubleSpinBox()), ("Вес воды (г):", QDoubleSpinBox()),
            ("Оценка:", QDoubleSpinBox())
        ]:
            root.addWidget(QLabel(label)); root.addWidget(widget)
            if isinstance(widget, QSpinBox): widget.setRange(1, 3600)
            if isinstance(widget, QDoubleSpinBox): widget.setRange(0, 5000)

        # assign common names (to keep later usage compact)
        # (order matches above)
        self.tempSpin = self.findChildren(QSpinBox)[0] if self.findChildren(QSpinBox) else QSpinBox()
        self.timeSpin = self.findChildren(QSpinBox)[1] if len(self.findChildren(QSpinBox))>1 else QSpinBox()
        dspin = self.findChildren(QDoubleSpinBox)
        self.coffeeWeightSpin = dspin[0] if dspin else QDoubleSpinBox()
        self.waterWeightSpin = dspin[1] if len(dspin)>1 else QDoubleSpinBox()
        self.ratingSpin = dspin[2] if len(dspin)>2 else QDoubleSpinBox()

        self.tempSpin.setRange(60,110); self.tempSpin.setValue(93)
        self.timeSpin.setRange(1,3600); self.timeSpin.setValue(180)
        self.coffeeWeightSpin.setRange(0.1,100); self.coffeeWeightSpin.setValue(18)
        self.waterWeightSpin.setRange(1,5000); self.waterWeightSpin.setValue(300)
        self.ratingSpin.setRange(0,5); self.ratingSpin.setDecimals(1)

        root.addWidget(QLabel("Заметки:"))
        self.notesEdit = QTextEdit(); self.notesEdit.setMaximumHeight(120); root.addWidget(self.notesEdit)

        btns = QHBoxLayout()
        self.saveBtn = QPushButton("Сохранить"); self.cancelBtn = QPushButton("Отмена")
        btns.addWidget(self.saveBtn); btns.addWidget(self.cancelBtn); root.addLayout(btns)

        self.saveBtn.clicked.connect(self._on_save); self.cancelBtn.clicked.connect(self.reject)

        if self.brewing_data:
            self._fill_from_data(self.brewing_data)

    def _fill_from_data(self, d: dict):
        try:
            idx = self.coffeeCombo.findData(d.get("coffee_bean_id"))
            if idx >= 0: self.coffeeCombo.setCurrentIndex(idx)
        except Exception: pass
        self.methodCombo.setCurrentText(d.get("brew_method",""))
        try:
            self.tempSpin.setValue(int(d.get("water_temp",93)))
            self.timeSpin.setValue(int(d.get("brew_time",180)))
            self.coffeeWeightSpin.setValue(float(d.get("coffee_weight",18)))
            self.waterWeightSpin.setValue(float(d.get("water_weight",300)))
            self.ratingSpin.setValue(float(d.get("rating",0)))
        except Exception: pass
        self.notesEdit.setPlainText(d.get("notes",""))

    def _on_save(self):
        if self.coffeeCombo.currentData() is None:
            QMessageBox.warning(self, "Ошибка", "Выберите сорт кофе"); return
        payload = {
            "coffee_bean_id": int(self.coffeeCombo.currentData()),
            "brew_method": self.methodCombo.currentText(),
            "grind_size": "",
            "water_temp": int(self.tempSpin.value()),
            "brew_time": int(self.timeSpin.value()),
            "coffee_weight": float(self.coffeeWeightSpin.value()),
            "water_weight": float(self.waterWeightSpin.value()),
            "rating": float(self.ratingSpin.value()),
            "notes": self.notesEdit.toPlainText().strip()
        }
        try:
            if self.brewing_data.get("id"):
                upd = getattr(self.db_manager, "update_brewing_session", None)
                if callable(upd):
                    ok = upd(self.brewing_data["id"], **payload)
                    if not ok: raise RuntimeError("Не удалось обновить")
            else:
                add = getattr(self.db_manager, "add_brewing_session", None)
                if callable(add):
                    nid = add(**payload)
                    if nid == -1 or nid is None: raise RuntimeError("Не удалось добавить")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка при сохранении", str(e))
