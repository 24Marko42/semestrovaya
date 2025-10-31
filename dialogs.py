# dialogs.py
import os, sys
from PyQt5 import uic
from PyQt5.QtCore import Qt, QBuffer, QIODevice
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, QTextEdit, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QHBoxLayout, QMessageBox

def resource_path(rel):
    try:
        base = sys._MEIPASS
    except Exception:
        base = os.path.abspath(".")
    return os.path.join(base, rel)

def load_pixmap_from_bytes(b):
    if not b: return None
    p = QPixmap(); p.loadFromData(b); return p if not p.isNull() else None

class DetailsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui = resource_path("ui/details_dialog.ui")
        if os.path.exists(ui):
            uic.loadUi(ui, self)
            try: self.closeButton.clicked.connect(self.accept)
            except Exception: pass
        else:
            self.setWindowTitle("Детали"); self.resize(420,520)
            l=QVBoxLayout(self); self.imageLabel=QLabel(alignment=Qt.AlignCenter); self.imageLabel.setMinimumSize(320,240); l.addWidget(self.imageLabel)
            self.detailsText=QTextEdit(); self.detailsText.setReadOnly(True); l.addWidget(self.detailsText)
            l.addWidget(QPushButton("Закрыть", clicked=self.accept))

    def set_image_from_bytes(self, b):
        p = load_pixmap_from_bytes(b)
        if p: self.imageLabel.setPixmap(p.scaled(320,320,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        else: self.imageLabel.setText("Изображение отсутствует")

    def set_text(self, txt): self.detailsText.setPlainText(txt)

class CoffeeDialog(QDialog):
    def __init__(self, db_manager, coffee_data=None, parent=None):
        super().__init__(parent)
        self.db = db_manager; self.coffee_data = coffee_data or {}; self.selected_image_path=None
        self.setWindowTitle("Редактировать" if coffee_data else "Добавить сорт"); self.resize(600,700)
        l=QVBoxLayout(self)
        header=QLabel("Добавить/Редактировать сорт", alignment=Qt.AlignCenter); header.setStyleSheet("background:#2E8B57;color:white;padding:8px"); l.addWidget(header)
        l.addWidget(QLabel("Название*:")); self.name=QLineEdit(); l.addWidget(self.name)
        l.addWidget(QLabel("Обжарщик:")); self.roaster=QLineEdit(); l.addWidget(self.roaster)
        l.addWidget(QLabel("Уровень обжарки:")); self.roast=QComboBox(); self.roast.addItems(["Light","Medium","Dark"]); l.addWidget(self.roast)
        l.addWidget(QLabel("Происхождение:")); self.origin=QLineEdit(); l.addWidget(self.origin)
        l.addWidget(QLabel("Метод обработки:")); self.proc=QLineEdit(); l.addWidget(self.proc)
        l.addWidget(QLabel("Вкусовые ноты:")); self.notes=QTextEdit(); self.notes.setMaximumHeight(120); l.addWidget(self.notes)
        h=QHBoxLayout(); h.addWidget(QLabel("Цена:")); self.price=QDoubleSpinBox(); self.price.setRange(0,100000); self.price.setDecimals(2); h.addWidget(self.price)
        h.addWidget(QLabel("Рейтинг:")); self.rating=QDoubleSpinBox(); self.rating.setRange(0,5); self.rating.setDecimals(1); h.addWidget(self.rating); l.addLayout(h)
        # image
        img_h=QHBoxLayout(); self.imgLabel=QLabel("🖼 Нажмите загрузить", alignment=Qt.AlignCenter); self.imgLabel.setFixedSize(220,220); img_h.addWidget(self.imgLabel)
        vb=QVBoxLayout(); self.loadBtn=QPushButton("Загрузить"); self.clearBtn=QPushButton("Очистить"); vb.addWidget(self.loadBtn); vb.addWidget(self.clearBtn); vb.addStretch(); img_h.addLayout(vb)
        l.addLayout(img_h)
        btn_h=QHBoxLayout(); self.saveBtn=QPushButton("Сохранить"); self.cancelBtn=QPushButton("Отмена"); btn_h.addWidget(self.saveBtn); btn_h.addWidget(self.cancelBtn); l.addLayout(btn_h)
        self.loadBtn.clicked.connect(self.load_image); self.clearBtn.clicked.connect(self.clear_image); self.saveBtn.clicked.connect(self.save); self.cancelBtn.clicked.connect(self.reject)
        if coffee_data: self.fill(coffee_data)

    def fill(self, d):
        self.name.setText(d.get("name","")); self.roaster.setText(d.get("roaster","")); self.roast.setCurrentText(d.get("roast_level","Medium"))
        self.origin.setText(d.get("origin","")); self.proc.setText(d.get("processing_method","")); self.notes.setPlainText(d.get("tasting_notes",""))
        try: self.price.setValue(float(d.get("price") or 0)); self.rating.setValue(float(d.get("rating") or 0))
        except Exception: pass
        if d.get("image"):
            p = load_pixmap_from_bytes(d["image"])
            if p: self.imgLabel.setPixmap(p.scaled(200,200,Qt.KeepAspectRatio,Qt.SmoothTransformation))

    def load_image(self):
        p,_ = QFileDialog.getOpenFileName(self,"Выберите изображение","","Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not p: return
        pix = QPixmap(p)
        if pix.isNull(): QMessageBox.warning(self,"Ошибка","Не удалось загрузить"); return
        self.selected_image_path = p
        self.imgLabel.setPixmap(pix.scaled(200,200,Qt.KeepAspectRatio,Qt.SmoothTransformation))

    def clear_image(self):
        self.selected_image_path = None; self.imgLabel.setText("🖼 Нажмите загрузить")

    def save(self):
        name = self.name.text().strip()
        if not name: QMessageBox.warning(self,"Ошибка","Название обязательно"); return
        image_pix = None
        if self.selected_image_path:
            pp = QPixmap(self.selected_image_path); image_pix = pp if not pp.isNull() else None
        try:
            if self.coffee_data.get("id"):
                self.db.update_coffee_bean(self.coffee_data["id"],
                                           name=name, roaster=self.roaster.text().strip(),
                                           roast_level=self.roast.currentText(), origin=self.origin.text().strip(),
                                           processing_method=self.proc.text().strip(), tasting_notes=self.notes.toPlainText().strip(),
                                           price=float(self.price.value()), rating=float(self.rating.value()), image=image_pix)
            else:
                self.db.add_coffee_bean(name=name, roaster=self.roaster.text().strip(),
                                        roast_level=self.roast.currentText(), origin=self.origin.text().strip(),
                                        processing_method=self.proc.text().strip(), tasting_notes=self.notes.toPlainText().strip(),
                                        price=float(self.price.value()), rating=float(self.rating.value()), image=image_pix)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self,"Ошибка при сохранении", str(e))

class BrewingDialog(QDialog):
    def __init__(self, db_manager, coffee_beans=None, brewing_data=None, parent=None):
        super().__init__(parent)
        self.db = db_manager; self.coffee_beans = coffee_beans or []; self.data = brewing_data or {}
        self.setWindowTitle("Добавить/Редактировать сессию"); self.resize(520,520)
        l=QVBoxLayout(self)
        l.addWidget(QLabel("Сорт*:")); self.coffeeCombo = QComboBox(); 
        for b in self.coffee_beans: self.coffeeCombo.addItem(b.get("name","—"), b.get("id"))
        l.addWidget(self.coffeeCombo)
        l.addWidget(QLabel("Метод*:")); self.method = QComboBox(); self.method.addItems(["Эспрессо","Воронка","Аэропресс","Френч-пресс","Кемекс","Пуровер"]); l.addWidget(self.method)
        l.addWidget(QLabel("Температура (°C):")); self.temp = QSpinBox(); self.temp.setRange(60,110); self.temp.setValue(93); l.addWidget(self.temp)
        l.addWidget(QLabel("Время (сек):")); self.time = QSpinBox(); self.time.setRange(1,3600); self.time.setValue(180); l.addWidget(self.time)
        l.addWidget(QLabel("Вес кофе (г):")); self.cw = QDoubleSpinBox(); self.cw.setRange(0.1,100); self.cw.setValue(18); l.addWidget(self.cw)
        l.addWidget(QLabel("Вес воды (г):")); self.ww = QDoubleSpinBox(); self.ww.setRange(1,5000); self.ww.setValue(300); l.addWidget(self.ww)
        l.addWidget(QLabel("Рейтинг:")); self.rating = QDoubleSpinBox(); self.rating.setRange(0,5); self.rating.setDecimals(1); l.addWidget(self.rating)
        l.addWidget(QLabel("Заметки:")); self.notes = QTextEdit(); self.notes.setMaximumHeight(120); l.addWidget(self.notes)
        h=QHBoxLayout(); self.saveBtn=QPushButton("Сохранить"); self.cancelBtn=QPushButton("Отмена"); h.addWidget(self.saveBtn); h.addWidget(self.cancelBtn); l.addLayout(h)
        self.saveBtn.clicked.connect(self._on_save); self.cancelBtn.clicked.connect(self.reject)
        if self.data: self._fill(self.data)

    def _fill(self,d):
        try:
            idx = self.coffeeCombo.findData(d.get("coffee_bean_id"))
            if idx>=0: self.coffeeCombo.setCurrentIndex(idx)
        except Exception: pass
        self.method.setCurrentText(d.get("brew_method","")); self.temp.setValue(int(d.get("water_temp",93))); self.time.setValue(int(d.get("brew_time",180)))
        self.cw.setValue(float(d.get("coffee_weight",18))); self.ww.setValue(float(d.get("water_weight",300))); self.rating.setValue(float(d.get("rating",0))); self.notes.setPlainText(d.get("notes",""))

    def _on_save(self):
        if self.coffeeCombo.currentData() is None: QMessageBox.warning(self,"Ошибка","Выберите сорт"); return
        payload = dict(coffee_bean_id=int(self.coffeeCombo.currentData()), brew_method=self.method.currentText(),
                       water_temp=int(self.temp.value()), brew_time=int(self.time.value()),
                       coffee_weight=float(self.cw.value()), water_weight=float(self.ww.value()),
                       rating=float(self.rating.value()), notes=self.notes.toPlainText().strip())
        try:
            if self.data.get("id"):
                self.db.update_brewing_session(self.data["id"], **payload)
            else:
                self.db.add_brewing_session(**payload)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self,"Ошибка при сохранении", str(e))
