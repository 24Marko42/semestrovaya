# main.py (полный файл — замени им существующий)
import os
import sys
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDialog, QMessageBox, QMenu, QAction
)
from PyQt5.QtGui import QPixmap, QColor

from database import DatabaseManager
from models import CoffeeBeansTableModel, BrewingSessionsTableModel
from dialogs import CoffeeDialog, BrewingDialog, ImageViewer, DetailsDialog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "ui")  # <- здесь находятся .ui

# Простой стиль (можешь подправить цвета)
APP_STYLE = """
QMainWindow { background: #1f1f1f; color: #eaeaea; }
QTableView { background: #2b2b2b; color: #eaeaea; gridline-color: #3a3a3a; }
QHeaderView::section { background: #2f2f2f; color: #eaeaea; padding: 4px; }
QPushButton { background: #4b6ef6; color: white; border-radius: 6px; padding: 6px; }
QLineEdit, QTextEdit { background: #262626; color: #f5f5f5; border: 1px solid #3a3a3a; border-radius: 4px; }
"""

class DetailsDialogWrapper(DetailsDialog):
    # Никаких изменений — просто алиас, если где-то используется другое имя
    pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(UI_DIR, "main_window.ui")
        if not os.path.exists(ui_path):
            QMessageBox.critical(self, "Ошибка", f"Файл интерфейса не найден: {ui_path}")
            raise SystemExit(1)
        uic.loadUi(ui_path, self)

        # Apply style
        QApplication.instance().setStyleSheet(APP_STYLE)

        # DB and models
        self.db = DatabaseManager()
        self.coffee_model = CoffeeBeansTableModel()
        self.brewing_model = BrewingSessionsTableModel()

        # Bind models to tables
        # (Ожидается, что в .ui есть coffeeTable и brewingTable)
        self.coffeeTable.setModel(self.coffee_model)
        self.brewingTable.setModel(self.brewing_model)

        # ====== Навигационные кнопки или стилизация вкладок ======
        # Если в .ui есть кнопки с именами coffeeTabBtn/sessionsTabBtn/statsTabBtn — покрасим их.
        # Иначе — применим стиль к tabWidget (или tabs).
        try:
            # Попробуем покрасить кнопки (если они определены в .ui)
            self.coffeeTabBtn.setStyleSheet("background-color: #8FBC8F; color: white;")
            self.sessionsTabBtn.setStyleSheet("background-color: #87CEFA; color: white;")
            self.statsTabBtn.setStyleSheet("background-color: #DAA520; color: white;")
        except Exception:
            # Кнопок нет — применяем стиль к вкладкам QTabWidget
            tab_widget = getattr(self, "tabWidget", None) or getattr(self, "tabs", None)
            if tab_widget:
                tabbar = tab_widget.tabBar()
                # Общий CSS для вкладок
                tabbar.setStyleSheet("""
                    QTabBar::tab {
                        background: #3a3a3a;
                        color: #eaeaea;
                        padding: 8px 16px;
                        border-radius: 8px;
                        margin: 4px;
                    }
                    QTabBar::tab:selected {
                        background: #4b6ef6;
                        color: white;
                    }
                """)
                # Попробуем расставить индивидуальные цвета (в качестве фона выбранного таба)
                # setTabTextColor требует QColor
                try:
                    tabbar.setTabTextColor(0, QColor("#ffffff"))
                    tabbar.setTabTextColor(1, QColor("#ffffff"))
                    tabbar.setTabTextColor(2, QColor("#ffffff"))
                except Exception:
                    pass

        # Buttons (objectNames must match)
        # Обёртки подключения — если элемент отсутствует, просто пропустить
        def safe_connect(obj_name, signal, slot):
            try:
                getattr(self, obj_name).connect(slot)
            except Exception:
                pass

        safe_connect("addCoffeeBtn", self.addCoffeeBtn.clicked, lambda: self.add_coffee())
        # Но выше может быть запутанно — лучше подключать в явном виде и ловить AttributeError
        try:
            self.addCoffeeBtn.clicked.connect(self.add_coffee)
            self.editCoffeeBtn.clicked.connect(self.edit_coffee)
            self.deleteCoffeeBtn.clicked.connect(self.delete_coffee)
            self.refreshCoffeeBtn.clicked.connect(self.load_coffee_data)
            self.coffeeSearchBtn.clicked.connect(self.search_coffee)
            self.coffeeClearBtn.clicked.connect(self.clear_coffee_search)

            self.addBrewingBtn.clicked.connect(self.add_brewing)
            self.editBrewingBtn.clicked.connect(self.edit_brewing)
            self.deleteBrewingBtn.clicked.connect(self.delete_brewing)
            self.refreshBrewingBtn.clicked.connect(self.load_brewing_data)
            self.brewingSearchBtn.clicked.connect(self.search_brewing)
            self.brewingClearBtn.clicked.connect(self.clear_brewing_search)
        except AttributeError:
            # если какие-то кнопки имеют другие имена — это нормально, приложение продолжит работать
            pass

        # Selection on cell click: select whole row if tables exist
        try:
            self.coffeeTable.clicked.connect(lambda idx: self.coffeeTable.selectRow(idx.row()))
            self.brewingTable.clicked.connect(lambda idx: self.brewingTable.selectRow(idx.row()))
        except Exception:
            pass

        # Context menus & double click
        try:
            self.coffeeTable.setContextMenuPolicy(Qt.CustomContextMenu)
            self.coffeeTable.customContextMenuRequested.connect(self._coffee_context)
            self.brewingTable.setContextMenuPolicy(Qt.CustomContextMenu)
            self.brewingTable.customContextMenuRequested.connect(self._brewing_context)

            self.coffeeTable.doubleClicked.connect(self.on_coffee_double_clicked)
            self.brewingTable.doubleClicked.connect(self.on_brewing_double_clicked)
        except Exception:
            pass

        # Load
        self.load_coffee_data()
        self.load_brewing_data()
        self.update_stats()

    # ---------- загрузка данных ----------
    def load_coffee_data(self):
        beans = self.db.get_all_coffee_beans()
        self.coffee_model.update_data(beans)
        self.update_stats()

    def load_brewing_data(self):
        sessions = self.db.get_all_brewing_sessions()
        self.brewing_model.update_data(sessions)
        self.update_stats()

    # ---------- CRUD для кофе ----------
    def add_coffee(self):
        dlg = CoffeeDialog(self.db, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.load_coffee_data()

    def edit_coffee(self):
        try:
            sel = self.coffeeTable.selectionModel().selectedRows()
            if not sel:
                QMessageBox.information(self, "Инфо", "Выберите запись для редактирования")
                return
            bean = self.coffee_model.coffee_beans[sel[0].row()]
            dlg = CoffeeDialog(self.db, coffee_data=bean, parent=self)
            if dlg.exec_() == QDialog.Accepted:
                self.load_coffee_data()
        except Exception:
            QMessageBox.information(self, "Инфо", "Ошибка выбора записи. Проверьте таблицу.")

    def delete_coffee(self):
        try:
            sel = self.coffeeTable.selectionModel().selectedRows()
            if not sel:
                QMessageBox.information(self, "Инфо", "Выберите запись для удаления")
                return
            bean = self.coffee_model.coffee_beans[sel[0].row()]
            reply = QMessageBox.question(self, "Удаление", f"Удалить '{bean.get('name')}'?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                ok = self.db.delete_coffee_bean(bean["id"])
                if ok:
                    self.load_coffee_data()
                    self.load_brewing_data()
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось удалить запись")
        except Exception:
            QMessageBox.critical(self, "Ошибка", "Ошибка при удалении")

    # ---------- CRUD для сессий ----------
    def add_brewing(self):
        beans = self.db.get_all_coffee_beans()
        if not beans:
            QMessageBox.information(self, "Инфо", "Добавьте сначала сорт кофе")
            return
        dlg = BrewingDialog(self.db, coffee_beans=beans, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.load_brewing_data()

    def edit_brewing(self):
        try:
            sel = self.brewingTable.selectionModel().selectedRows()
            if not sel:
                QMessageBox.information(self, "Инфо", "Выберите запись для редактирования")
                return
            session = self.brewing_model.brewing_sessions[sel[0].row()]
            beans = self.db.get_all_coffee_beans()
            dlg = BrewingDialog(self.db, coffee_beans=beans, brewing_data=session, parent=self)
            if dlg.exec_() == QDialog.Accepted:
                self.load_brewing_data()
        except Exception:
            QMessageBox.critical(self, "Ошибка", "Ошибка при редактировании")

    def delete_brewing(self):
        try:
            sel = self.brewingTable.selectionModel().selectedRows()
            if not sel:
                QMessageBox.information(self, "Инфо", "Выберите запись для удаления")
                return
            session = self.brewing_model.brewing_sessions[sel[0].row()]
            reply = QMessageBox.question(self, "Удаление", "Удалить сессию?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                ok = self.db.delete_brewing_session(session["id"])
                if ok:
                    self.load_brewing_data()
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось удалить запись")
        except Exception:
            QMessageBox.critical(self, "Ошибка", "Ошибка при удалении")

    # ---------- Поиск (с поддержкой ID) ----------
    def search_coffee(self):
        try:
            q = self.coffeeSearchEdit.text().strip()
        except Exception:
            q = ""
        if not q:
            self.load_coffee_data()
            return
        if q.isdigit():
            beans = self.db.get_all_coffee_beans()
            matched = [b for b in beans if str(b.get("id")) == q]
            self.coffee_model.update_data(matched)
            return
        res = self.db.search_coffee_beans(q)
        self.coffee_model.update_data(res)

    def clear_coffee_search(self):
        try:
            self.coffeeSearchEdit.clear()
        except Exception:
            pass
        self.load_coffee_data()

    def search_brewing(self):
        try:
            q = self.brewingSearchEdit.text().strip()
        except Exception:
            q = ""
        if q:
            res = self.db.search_brewing_sessions(q)
            self.brewing_model.update_data(res)
        else:
            self.load_brewing_data()

    def clear_brewing_search(self):
        try:
            self.brewingSearchEdit.clear()
        except Exception:
            pass
        self.load_brewing_data()

    # ---------- Контекстные меню ----------
    def _coffee_context(self, pos):
        try:
            m = QMenu(self)
            view = QAction("Просмотреть", self)
            view.triggered.connect(self._view_coffee_from_context)
            edit = QAction("Редактировать", self)
            edit.triggered.connect(self.edit_coffee)
            delete = QAction("Удалить", self)
            delete.triggered.connect(self.delete_coffee)
            m.addAction(view); m.addAction(edit); m.addAction(delete)
            m.exec_(self.coffeeTable.viewport().mapToGlobal(pos))
        except Exception:
            pass

    def _brewing_context(self, pos):
        try:
            m = QMenu(self)
            edit = QAction("Редактировать", self)
            edit.triggered.connect(self.edit_brewing)
            delete = QAction("Удалить", self)
            delete.triggered.connect(self.delete_brewing)
            m.addAction(edit); m.addAction(delete)
            m.exec_(self.brewingTable.viewport().mapToGlobal(pos))
        except Exception:
            pass

    def _view_coffee_from_context(self):
        try:
            sel = self.coffeeTable.selectionModel().selectedRows()
            if not sel:
                return
            bean = self.coffee_model.coffee_beans[sel[0].row()]
            self._show_coffee_details(bean)
        except Exception:
            pass

    # ---------- Детали ----------
    def on_coffee_double_clicked(self, index):
        try:
            bean = self.coffee_model.coffee_beans[index.row()]
            self._show_coffee_details(bean)
        except Exception:
            pass

    def on_brewing_double_clicked(self, index):
        try:
            session = self.brewing_model.brewing_sessions[index.row()]
            bean = None
            beans = self.db.get_all_coffee_beans()
            for b in beans:
                if b["id"] == session.get("coffee_bean_id"):
                    bean = b
                    break

            dlg = DetailsDialog(self)
            if bean and bean.get("image"):
                dlg.set_image_from_bytes(bean.get("image"))
            else:
                dlg.set_image_from_bytes(None)

            details = (
                f"Кофе: {session.get('coffee_name') or '-'}\n"
                f"Метод: {session.get('brew_method') or '-'}\n"
                f"Температура: {session.get('water_temp') or '-'}\n"
                f"Время: {session.get('brew_time') or '-'}\n"
                f"Вес кофе: {session.get('coffee_weight') or '-'}\n"
                f"Вес воды: {session.get('water_weight') or '-'}\n"
                f"Рейтинг: {session.get('rating') or '-'}\n"
                f"Заметки: {session.get('notes') or '-'}\n"
                f"Дата: {session.get('created_at') or '-'}"
            )
            dlg.set_text(details)
            dlg.exec_()
        except Exception:
            pass

    def _show_coffee_details(self, bean):
        try:
            dlg = DetailsDialog(self)
            dlg.set_image_from_bytes(bean.get("image"))
            details = (
                f"Название: {bean.get('name')}\n"
                f"Обжарщик: {bean.get('roaster') or '-'}\n"
                f"Уровень обжарки: {bean.get('roast_level') or '-'}\n"
                f"Происхождение: {bean.get('origin') or '-'}\n"
                f"Метод обработки: {bean.get('processing_method') or '-'}\n"
                f"Вкусовые ноты: {bean.get('tasting_notes') or '-'}\n"
                f"Рейтинг: {bean.get('rating') or '-'}\n"
                f"Цена: {bean.get('price') or '-'}\n"
                f"Дата добавления: {bean.get('created_at') or '-'}"
            )
            dlg.set_text(details)
            dlg.exec_()
        except Exception:
            pass

    # ---------- Статистика ----------
    def update_stats(self):
        try:
            stats = self.db.get_detailed_statistics()
            images_count = self.db.get_coffee_with_images_count()
            total = stats.get("total_beans", 0)
            pct = (images_count / total * 100) if total else 0
            text = (
                f"Всего сортов: {total}\n"
                f"С изображениями: {images_count} ({pct:.1f}%)\n"
                f"Всего сессий: {stats.get('total_sessions', 0)}\n"
                f"Средний рейтинг сортов: {stats.get('avg_bean_rating', 0):.1f}"
            )
            try:
                self.statsText.setPlainText(text)
            except Exception:
                pass
        except Exception:
            pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.load_coffee_data()
            self.load_brewing_data()
        elif event.key() == Qt.Key_Delete:
            try:
                cur_tab = self.tabs.currentIndex()
            except Exception:
                cur_tab = 0
            if cur_tab == 0:
                self.delete_coffee()
            else:
                self.delete_brewing()
        super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Coffee Journal")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
