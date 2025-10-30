# dialogs.py
import os
from typing import Optional, List, Dict, Any

from PyQt5 import uic
from PyQt5.QtCore import Qt, QBuffer, QIODevice
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, QTextEdit,
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QHBoxLayout, QWidget,
    QMessageBox
)

from database import DatabaseManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "ui")


# -----------------------------
# Утилиты
# -----------------------------
def pixmap_to_bytes(pix: Optional[QPixmap]) -> Optional[bytes]:
    """Преобразует QPixmap в PNG bytes, или None."""
    if pix is None or pix.isNull():
        return None
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    pix.save(buf, "PNG")
    data = bytes(buf.data())
    buf.close()
    return data


def load_pixmap_from_bytes(b: Optional[bytes]) -> Optional[QPixmap]:
    if not b:
        return None
    pix = QPixmap()
    pix.loadFromData(b)
    return pix if not pix.isNull() else None


# -----------------------------
# ImageViewer — простая карточка просмотра изображения
# -----------------------------
class ImageViewer(QDialog):
    def __init__(self, image_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Просмотр изображения")
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        self.image_label = QLabel(alignment=Qt.AlignCenter)
        layout.addWidget(self.image_label)
        btn = QPushButton("Закрыть")
        btn.clicked.connect(self.close)
        layout.addWidget(btn)

        if image_path:
            self.load_from_path(image_path)

    def load_from_path(self, path: str):
        if path and os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                self.image_label.setPixmap(pix.scaled(760, 520, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        self.image_label.setText("Не удалось загрузить изображение")


# -----------------------------
# DetailsDialog — показывает картинку + текст. Стилизован.
# -----------------------------
class DetailsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(UI_DIR, "details_dialog.ui")
        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
            # в ui должны быть imageLabel, detailsText, closeButton (опционально)
            try:
                self.closeButton.clicked.connect(self.accept)
            except Exception:
                pass
        else:
            # минимальный интерфейс если .ui нет
            self.setWindowTitle("Детали")
            self.resize(420, 520)
            layout = QVBoxLayout(self)
            self.imageLabel = QLabel(alignment=Qt.AlignCenter)
            self.imageLabel.setMinimumSize(320, 240)
            layout.addWidget(self.imageLabel)
            self.detailsText = QTextEdit()
            self.detailsText.setReadOnly(True)
            layout.addWidget(self.detailsText)
            btn = QPushButton("Закрыть")
            btn.clicked.connect(self.accept)
            layout.addWidget(btn)

        # Стиль для окна деталей (фон другой цвет)
        self.setStyleSheet("""
            QDialog {
                background-color: #2E3B3B; /* тёмно-зелёно-серый фон */
                color: #F6F6F6;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 13px;
            }
            QTextEdit {
                background: #273232;
                color: #F6F6F6;
                border: 1px solid #3A4A4A;
                border-radius: 6px;
            }
            QLabel {
                color: #F6F6F6;
            }
            QPushButton {
                background-color: #4b6ef6;
                color: white;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background-color: #6a86ff;
            }
        """)

    def set_image_from_bytes(self, data: Optional[bytes]):
        pix = load_pixmap_from_bytes(data)
        if pix:
            self.imageLabel.setPixmap(pix.scaled(320, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.imageLabel.setText("Изображение отсутствует")

    def set_text(self, text: str):
        try:
            self.detailsText.setPlainText(text)
        except Exception:
            # если ui не содержит detailsText, создадим простое QLabel
            try:
                self.detailsText = QTextEdit()
                self.detailsText.setReadOnly(True)
                self.layout().addWidget(self.detailsText)
                self.detailsText.setPlainText(text)
            except Exception:
                pass


# -----------------------------
# CoffeeDialog — добавление/редактирование кофе
# -----------------------------
# Замените существующий класс CoffeeDialog в dialogs.py этим кодом

# Вставить в dialogs.py: обновлённые CoffeeDialog и BrewingDialog
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox, QTextEdit,
    QDoubleSpinBox, QPushButton, QHBoxLayout, QFileDialog, QMessageBox,
    QWidget, QSpinBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import os

# предполагается, что DatabaseManager импортирован в файле dialogs.py ранее:
# from database import DatabaseManager

# --------------------------
# CoffeeDialog (обновлённый)
# --------------------------
class CoffeeDialog(QDialog):
    """
    Программный диалог "Добавить / Редактировать сорт кофе".
    Имеет цветной header (плашку) и фоновый цвет окна.
    Работает независимо от .ui.
    """
    def __init__(self, db_manager, coffee_data=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.coffee_data = coffee_data or {}
        self.selected_image_path = None

        # Окно
        self.setWindowTitle("Редактировать сорт" if coffee_data else "Добавить сорт кофе")
        self.resize(640, 700)

        # Основной стиль: фон окна
        self.setStyleSheet("""
            QDialog {
                background-color: #1f2830; /* тёмный фон окна */
                color: #f0f0f0;
            }
            QLabel#headerLabel {
                background-color: #2E8B57; /* цвет плашки заголовка */
                color: white;
                padding: 10px;
                font-weight: bold;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QPushButton {
                background-color: #4b6ef6;
                color: white;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton#cancelBtn {
                background-color: #6c757d;
            }
            QLineEdit, QTextEdit, QComboBox, QDoubleSpinBox, QSpinBox {
                background-color: #2b3338;
                color: #f0f0f0;
                border: 1px solid #3a3f44;
                border-radius: 4px;
            }
        """)

        root = QVBoxLayout(self)

        # Header (плашка внутри окна)
        self.header = QLabel("Добавить сорт кофе" if not coffee_data else "Редактировать сорт кофе")
        self.header.setObjectName("headerLabel")
        self.header.setAlignment(Qt.AlignCenter)
        root.addWidget(self.header)

        # Форма
        form_layout = QVBoxLayout()

        form_layout.addWidget(QLabel("Название*:"))
        self.nameEdit = QLineEdit()
        form_layout.addWidget(self.nameEdit)

        form_layout.addWidget(QLabel("Обжарщик:"))
        self.roasterEdit = QLineEdit()
        form_layout.addWidget(self.roasterEdit)

        form_layout.addWidget(QLabel("Уровень обжарки:"))
        self.roastCombo = QComboBox()
        self.roastCombo.addItems(["Light", "Medium", "Dark"])  # вернули как раньше
        form_layout.addWidget(self.roastCombo)

        form_layout.addWidget(QLabel("Происхождение:"))
        self.originEdit = QLineEdit()
        form_layout.addWidget(self.originEdit)

        form_layout.addWidget(QLabel("Метод обработки:"))
        self.processingEdit = QLineEdit()
        form_layout.addWidget(self.processingEdit)

        form_layout.addWidget(QLabel("Вкусовые ноты:"))
        self.tastingNotesEdit = QTextEdit()
        self.tastingNotesEdit.setMaximumHeight(120)
        form_layout.addWidget(self.tastingNotesEdit)

        # Цена и рейтинг
        hr = QHBoxLayout()
        hr.addWidget(QLabel("Цена (руб):"))
        self.priceSpin = QDoubleSpinBox()
        self.priceSpin.setRange(0, 100000)
        self.priceSpin.setDecimals(2)
        hr.addWidget(self.priceSpin)
        hr.addWidget(QLabel("Рейтинг:"))
        self.ratingSpin = QDoubleSpinBox()
        self.ratingSpin.setRange(0, 5)
        self.ratingSpin.setDecimals(1)
        self.ratingSpin.setSingleStep(0.1)
        hr.addWidget(self.ratingSpin)
        form_layout.addLayout(hr)

        # Картинка и кнопки для неё
        img_box = QWidget()
        img_h = QHBoxLayout(img_box)
        self.imageLabel = QLabel("🖼 Нажмите \"Загрузить\" или кликните сюда", alignment=Qt.AlignCenter)
        self.imageLabel.setFixedSize(240, 240)
        self.imageLabel.setStyleSheet("border: 2px dashed #3a3f44;")
        img_h.addWidget(self.imageLabel)

        img_btns = QVBoxLayout()
        self.loadImageBtn = QPushButton("Загрузить изображение")
        self.clearImageBtn = QPushButton("Очистить изображение")
        img_btns.addWidget(self.loadImageBtn)
        img_btns.addWidget(self.clearImageBtn)
        img_btns.addStretch()
        img_h.addLayout(img_btns)

        form_layout.addWidget(img_box)

        # Сохранение / Отмена
        action_h = QHBoxLayout()
        self.saveBtn = QPushButton("💾 Сохранить")
        self.cancelBtn = QPushButton("Отмена")
        self.cancelBtn.setObjectName("cancelBtn")
        action_h.addWidget(self.saveBtn)
        action_h.addWidget(self.cancelBtn)
        form_layout.addLayout(action_h)

        root.addLayout(form_layout)

        # Сигналы
        self.loadImageBtn.clicked.connect(self._on_load_image)
        self.clearImageBtn.clicked.connect(self._on_clear_image)
        self.saveBtn.clicked.connect(self._on_save)
        self.cancelBtn.clicked.connect(self.reject)
        try:
            self.imageLabel.mousePressEvent = lambda ev: self._on_load_image()
        except Exception:
            pass

        # Если редактирование — заполнить поля
        if self.coffee_data:
            self._fill_from_data(self.coffee_data)

    def _fill_from_data(self, d):
        self.nameEdit.setText(d.get("name", ""))
        self.roasterEdit.setText(d.get("roaster", ""))
        self.roastCombo.setCurrentText(d.get("roast_level", "Medium"))
        self.originEdit.setText(d.get("origin", "") or "")
        self.processingEdit.setText(d.get("processing_method", "") or "")
        self.tastingNotesEdit.setPlainText(d.get("tasting_notes", "") or "")
        try:
            self.priceSpin.setValue(float(d.get("price") or 0))
            self.ratingSpin.setValue(float(d.get("rating") or 0))
        except Exception:
            pass
        if d.get("image"):
            pix = QPixmap()
            pix.loadFromData(d["image"]) if isinstance(d["image"], (bytes, bytearray)) else pix.load(d["image"])
            if not pix.isNull():
                self.imageLabel.setPixmap(pix.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _on_load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not path:
            return
        self.selected_image_path = path
        pix = QPixmap(path)
        if pix.isNull():
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить изображение")
            return
        self.imageLabel.setPixmap(pix.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _on_clear_image(self):
        self.selected_image_path = None
        self.imageLabel.clear()
        self.imageLabel.setText('🖼 Нажмите "Загрузить" или кликните сюда')

    def _on_save(self):
        name = self.nameEdit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Поле 'Название' обязательно")
            return

        roaster = self.roasterEdit.text().strip()
        roast_level = self.roastCombo.currentText()
        origin = self.originEdit.text().strip()
        processing_method = self.processingEdit.text().strip()
        tasting_notes = self.tastingNotesEdit.toPlainText().strip()
        price = float(self.priceSpin.value())
        rating = float(self.ratingSpin.value())

        # подготовка QPixmap для БД (DatabaseManager умеет работать с QPixmap)
        pix_for_db = None
        if self.selected_image_path and os.path.exists(self.selected_image_path):
            pix_for_db = QPixmap(self.selected_image_path)
            if pix_for_db.isNull():
                pix_for_db = None

        try:
            if self.coffee_data.get("id"):
                ok = self.db_manager.update_coffee_bean(
                    self.coffee_data["id"],
                    name=name,
                    roaster=roaster,
                    roast_level=roast_level,
                    origin=origin,
                    processing_method=processing_method,
                    tasting_notes=tasting_notes,
                    price=price,
                    rating=rating,
                    image=pix_for_db
                )
                if not ok:
                    raise RuntimeError("Не удалось обновить запись")
            else:
                new_id = self.db_manager.add_coffee_bean(
                    name=name,
                    roaster=roaster,
                    roast_level=roast_level,
                    origin=origin,
                    processing_method=processing_method,
                    tasting_notes=tasting_notes,
                    price=price,
                    rating=rating,
                    image=pix_for_db
                )
                if new_id == -1:
                    raise RuntimeError("Не удалось добавить запись")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка при сохранении", str(e))


# --------------------------
# BrewingDialog (обновлённый)
# --------------------------
class BrewingDialog(QDialog):
    """
    Программный диалог "Добавить / Редактировать сессию заваривания".
    Имеет цветной header (плашку) и тёмный фон.
    """
    def __init__(self, db_manager, coffee_beans=None, brewing_data=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.coffee_beans = coffee_beans or []
        self.brewing_data = brewing_data or {}

        self.setWindowTitle("Редактировать сессию" if brewing_data else "Добавить сессию заваривания")
        self.resize(520, 520)

        self.setStyleSheet("""
            QDialog { background-color: #182226; color: #f0f0f0; }
            QLabel#headerLabel { background-color: #8B0000; color: white; padding: 10px; font-weight: bold; }
            QPushButton { background-color: #4b6ef6; color: white; border-radius: 6px; padding: 6px 10px; }
            QPushButton#cancelBtn { background-color: #6c757d; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #202a2c; color: #f0f0f0; border: 1px solid #2f3a3c; border-radius: 4px;
            }
        """)

        root = QVBoxLayout(self)

        # Header
        self.header = QLabel("Добавить сессию" if not brewing_data else "Редактировать сессию")
        self.header.setObjectName("headerLabel")
        self.header.setAlignment(Qt.AlignCenter)
        root.addWidget(self.header)

        form = QVBoxLayout()

        form.addWidget(QLabel("Сорт кофе*:"))
        self.coffeeCombo = QComboBox()
        for b in self.coffee_beans:
            # ожидается, что каждый b — dict с 'name' и 'id'
            try:
                self.coffeeCombo.addItem(b.get("name", "—"), b.get("id"))
            except Exception:
                pass
        form.addWidget(self.coffeeCombo)

        form.addWidget(QLabel("Метод*:"))
        self.methodCombo = QComboBox()
        self.methodCombo.addItems(["Эспрессо", "Воронка", "Аэропресс", "Френч-пресс", "Кемекс", "Пуровер"])
        form.addWidget(self.methodCombo)

        # Параметры
        form.addWidget(QLabel("Температура (°C):"))
        self.tempSpin = QSpinBox(); self.tempSpin.setRange(60, 110); self.tempSpin.setValue(93)
        form.addWidget(self.tempSpin)

        form.addWidget(QLabel("Время (сек):"))
        self.timeSpin = QSpinBox(); self.timeSpin.setRange(1, 3600); self.timeSpin.setValue(180)
        form.addWidget(self.timeSpin)

        form.addWidget(QLabel("Вес кофе (г):"))
        self.coffeeWeightSpin = QDoubleSpinBox(); self.coffeeWeightSpin.setRange(0.1, 100); self.coffeeWeightSpin.setValue(18)
        form.addWidget(self.coffeeWeightSpin)

        form.addWidget(QLabel("Вес воды (г):"))
        self.waterWeightSpin = QDoubleSpinBox(); self.waterWeightSpin.setRange(1, 5000); self.waterWeightSpin.setValue(300)
        form.addWidget(self.waterWeightSpin)

        form.addWidget(QLabel("Оценка:"))
        self.ratingSpin = QDoubleSpinBox(); self.ratingSpin.setRange(0, 5); self.ratingSpin.setDecimals(1)
        form.addWidget(self.ratingSpin)

        form.addWidget(QLabel("Заметки:"))
        self.notesEdit = QTextEdit(); self.notesEdit.setMaximumHeight(120)
        form.addWidget(self.notesEdit)

        # Кнопки
        h = QHBoxLayout()
        self.saveBtn = QPushButton("Сохранить")
        self.cancelBtn = QPushButton("Отмена")
        self.cancelBtn.setObjectName("cancelBtn")
        h.addWidget(self.saveBtn); h.addWidget(self.cancelBtn)
        form.addLayout(h)

        root.addLayout(form)

        # Сигналы
        self.saveBtn.clicked.connect(self._on_save)
        self.cancelBtn.clicked.connect(self.reject)

        # Заполнить если редактирование
        if self.brewing_data:
            self._fill_from_data(self.brewing_data)

    def _fill_from_data(self, d):
        # выбрать кофе
        try:
            idx = self.coffeeCombo.findData(d.get("coffee_bean_id"))
            if idx >= 0:
                self.coffeeCombo.setCurrentIndex(idx)
        except Exception:
            pass
        self.methodCombo.setCurrentText(d.get("brew_method", ""))
        try:
            self.tempSpin.setValue(int(d.get("water_temp", 93)))
            self.timeSpin.setValue(int(d.get("brew_time", 180)))
            self.coffeeWeightSpin.setValue(float(d.get("coffee_weight", 18)))
            self.waterWeightSpin.setValue(float(d.get("water_weight", 300)))
            self.ratingSpin.setValue(float(d.get("rating", 0)))
        except Exception:
            pass
        self.notesEdit.setPlainText(d.get("notes", ""))

    def _on_save(self):
        if self.coffeeCombo.currentData() is None:
            QMessageBox.warning(self, "Ошибка", "Выберите сорт кофе")
            return

        payload = {
            "coffee_bean_id": int(self.coffeeCombo.currentData()),
            "brew_method": self.methodCombo.currentText(),
            "grind_size": "",  # опционально; можно добавить поле при желании
            "water_temp": int(self.tempSpin.value()),
            "brew_time": int(self.timeSpin.value()),
            "coffee_weight": float(self.coffeeWeightSpin.value()),
            "water_weight": float(self.waterWeightSpin.value()),
            "rating": float(self.ratingSpin.value()),
            "notes": self.notesEdit.toPlainText().strip()
        }

        try:
            if self.brewing_data.get("id"):
                ok = self.db_manager.update_brewing_session(self.brewing_data["id"], **payload)
                if not ok:
                    raise RuntimeError("Не удалось обновить сессию")
            else:
                newid = self.db_manager.add_brewing_session(**payload)
                if newid == -1:
                    raise RuntimeError("Не удалось добавить сессию")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка при сохранении", str(e))
