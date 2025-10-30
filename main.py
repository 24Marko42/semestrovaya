# main.py (полный файл — замените им существующий)
import os
import sys
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDialog, QMessageBox, QMenu, QAction, QHeaderView
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSortFilterProxyModel

from database import DatabaseManager
from models import CoffeeBeansTableModel, BrewingSessionsTableModel
from dialogs import CoffeeDialog, BrewingDialog, ImageViewer, DetailsDialog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "ui")  # <- здесь находятся .ui

# Общий стиль приложения
APP_STYLE = """
QMainWindow { background: #121212; color: #eaeaea; }
QWidget { background: #121212; color: #eaeaea; }
QTableView { background: #1e1e1e; color: #eaeaea; gridline-color: #2a2a2a; }
QHeaderView::section { background: #212121; color: #eaeaea; padding: 6px; }
QPushButton { background: #3b82f6; color: white; border-radius: 6px; padding: 6px 10px; }
QLineEdit, QTextEdit { background: #161616; color: #f5f5f5; border: 1px solid #2a2a2a; border-radius: 4px; }
QTabBar::tab { background: #212121; color: #eaeaea; padding: 8px 14px; border-radius: 8px; margin: 2px; }
QTabBar::tab:selected { background: #3b82f6; color: white; }
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(UI_DIR, "main_window.ui")
        if not os.path.exists(ui_path):
            QMessageBox.critical(self, "Ошибка", f"Файл интерфейса не найден: {ui_path}")
            raise SystemExit(1)
        uic.loadUi(ui_path, self)

        # Apply style
        app = QApplication.instance()
        if app:
            app.setStyleSheet(APP_STYLE)

        # DB and models
        self.db = DatabaseManager()
        self.coffee_model = CoffeeBeansTableModel()
        self.brewing_model = BrewingSessionsTableModel()

        # Proxy models for sorting/filtering
        self.coffee_proxy = QSortFilterProxyModel(self)
        self.coffee_proxy.setSourceModel(self.coffee_model)
        # allow case-insensitive sorting/filtering
        self.coffee_proxy.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.coffee_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.brewing_proxy = QSortFilterProxyModel(self)
        self.brewing_proxy.setSourceModel(self.brewing_model)
        self.brewing_proxy.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.brewing_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # Bind proxies to views (if widgets exist)
        try:
            self.coffeeTable.setModel(self.coffee_proxy)
            # enable interactive resizing and sorting
            self.coffeeTable.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            self.coffeeTable.setSortingEnabled(True)
        except Exception:
            pass

        try:
            self.brewingTable.setModel(self.brewing_proxy)
            self.brewingTable.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            self.brewingTable.setSortingEnabled(True)
        except Exception:
            pass

        # Try to style tabs/buttons (non-fatal)
        try:
            self.coffeeTabBtn.setStyleSheet("background-color: #8FBC8F; color: white;")
            self.sessionsTabBtn.setStyleSheet("background-color: #87CEFA; color: white;")
            self.statsTabBtn.setStyleSheet("background-color: #DAA520; color: white;")
        except Exception:
            tab_widget = getattr(self, "tabWidget", None) or getattr(self, "tabs", None)
            if tab_widget:
                try:
                    tabbar = tab_widget.tabBar()
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
                except Exception:
                    pass

        # Connect buttons (safe)
        try:
            self.addCoffeeBtn.clicked.connect(self.add_coffee)
            self.editCoffeeBtn.clicked.connect(self.edit_coffee)
            self.deleteCoffeeBtn.clicked.connect(self.delete_coffee)
            self.refreshCoffeeBtn.clicked.connect(self.load_coffee_data)
            self.coffeeSearchBtn.clicked.connect(self.search_coffee)
            self.coffeeClearBtn.clicked.connect(self.clear_coffee_search)
        except Exception:
            pass

        try:
            self.addBrewingBtn.clicked.connect(self.add_brewing)
            self.editBrewingBtn.clicked.connect(self.edit_brewing)
            self.deleteBrewingBtn.clicked.connect(self.delete_brewing)
            self.refreshBrewingBtn.clicked.connect(self.load_brewing_data)
            self.brewingSearchBtn.clicked.connect(self.search_brewing)
            self.brewingClearBtn.clicked.connect(self.clear_brewing_search)
        except Exception:
            pass

        # Enable search on Enter (returnPressed) if line edits exist
        try:
            # Try common names used in earlier code
            if hasattr(self, "coffeeSearchEdit"):
                self.coffeeSearchEdit.returnPressed.connect(self.search_coffee)
            elif hasattr(self, "coffeeSearchInput"):
                self.coffeeSearchInput.returnPressed.connect(self.search_coffee)
        except Exception:
            pass

        try:
            if hasattr(self, "brewingSearchEdit"):
                self.brewingSearchEdit.returnPressed.connect(self.search_brewing)
        except Exception:
            pass

        # Row selection on cell click (select full row)
        try:
            self.coffeeTable.clicked.connect(lambda idx: self.coffeeTable.selectRow(idx.row()))
            self.brewingTable.clicked.connect(lambda idx: self.brewingTable.selectRow(idx.row()))
        except Exception:
            pass

        # Context menus and double click handlers (use proxy → source mapping)
        try:
            self.coffeeTable.setContextMenuPolicy(Qt.CustomContextMenu)
            self.coffeeTable.customContextMenuRequested.connect(self._coffee_context)
            self.brewingTable.setContextMenuPolicy(Qt.CustomContextMenu)
            self.brewingTable.customContextMenuRequested.connect(self._brewing_context)

            self.coffeeTable.doubleClicked.connect(self.on_coffee_double_clicked)
            self.brewingTable.doubleClicked.connect(self.on_brewing_double_clicked)
        except Exception:
            pass

        # Initial load
        self.load_coffee_data()
        self.load_brewing_data()
        self.update_stats()

    # ---------- utility: map selection/index from proxy to source ----------
    def _selected_source_index_from_view(self, view, proxy):
        """Возвращает первый выбранный source-model QModelIndex или None."""
        sel = view.selectionModel().selectedRows()
        if not sel:
            return None
        proxy_index = sel[0]
        try:
            src_index = proxy.mapToSource(proxy_index)
            return src_index
        except Exception:
            return None

    def _source_index_from_proxy_index(self, proxy_index, proxy):
        try:
            return proxy.mapToSource(proxy_index)
        except Exception:
            return proxy_index

    # ---------- загрузка данных ----------
    def load_coffee_data(self):
        beans = self.db.get_all_coffee_beans()
        try:
            self.coffee_model.update_data(beans)
        except Exception:
            pass
        self.update_stats()

    def load_brewing_data(self):
        sessions = self.db.get_all_brewing_sessions()
        try:
            self.brewing_model.update_data(sessions)
        except Exception:
            pass
        self.update_stats()

    # ---------- CRUD для кофе ----------
    def add_coffee(self):
        dlg = CoffeeDialog(self.db, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.load_coffee_data()

    def edit_coffee(self):
        try:
            src_idx = self._selected_source_index_from_view(self.coffeeTable, self.coffee_proxy)
            if src_idx is None:
                QMessageBox.information(self, "Инфо", "Выберите запись для редактирования")
                return
            bean = self.coffee_model.coffee_beans[src_idx.row()]
            dlg = CoffeeDialog(self.db, coffee_data=bean, parent=self)
            if dlg.exec_() == QDialog.Accepted:
                self.load_coffee_data()
        except Exception:
            QMessageBox.information(self, "Инфо", "Ошибка выбора записи. Проверьте таблицу.")

    def delete_coffee(self):
        try:
            src_idx = self._selected_source_index_from_view(self.coffeeTable, self.coffee_proxy)
            if src_idx is None:
                QMessageBox.information(self, "Инфо", "Выберите запись для удаления")
                return
            bean = self.coffee_model.coffee_beans[src_idx.row()]
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
            src_idx = self._selected_source_index_from_view(self.brewingTable, self.brewing_proxy)
            if src_idx is None:
                QMessageBox.information(self, "Инфо", "Выберите запись для редактирования")
                return
            session = self.brewing_model.brewing_sessions[src_idx.row()]
            beans = self.db.get_all_coffee_beans()
            dlg = BrewingDialog(self.db, coffee_beans=beans, brewing_data=session, parent=self)
            if dlg.exec_() == QDialog.Accepted:
                self.load_brewing_data()
        except Exception:
            QMessageBox.critical(self, "Ошибка", "Ошибка при редактировании")

    def delete_brewing(self):
        try:
            src_idx = self._selected_source_index_from_view(self.brewingTable, self.brewing_proxy)
            if src_idx is None:
                QMessageBox.information(self, "Инфо", "Выберите запись для удаления")
                return
            session = self.brewing_model.brewing_sessions[src_idx.row()]
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
            # try alternative objectName
            try:
                q = self.coffeeSearchInput.text().strip()
            except Exception:
                q = ""
        if not q:
            self.load_coffee_data()
            return
        # Если цифры — поиск по ID через БД (сохраняем модель напрямую)
        if q.isdigit():
            beans = self.db.get_all_coffee_beans()
            matched = [b for b in beans if str(b.get("id")) == q]
            self.coffee_model.update_data(matched)
            return
        # Иначе — делегируем на поиск БД
        res = self.db.search_coffee_beans(q)
        self.coffee_model.update_data(res)

    def clear_coffee_search(self):
        try:
            if hasattr(self, "coffeeSearchEdit"):
                self.coffeeSearchEdit.clear()
            elif hasattr(self, "coffeeSearchInput"):
                self.coffeeSearchInput.clear()
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
            src_idx = self._selected_source_index_from_view(self.coffeeTable, self.coffee_proxy)
            if src_idx is None:
                return
            bean = self.coffee_model.coffee_beans[src_idx.row()]
            self._show_coffee_details(bean)
        except Exception:
            pass

    # ---------- Детали ----------
    def on_coffee_double_clicked(self, proxy_index):
        try:
            src_index = self._source_index_from_proxy_index(proxy_index, self.coffee_proxy)
            bean = self.coffee_model.coffee_beans[src_index.row()]
            self._show_coffee_details(bean)
        except Exception:
            pass

    def on_brewing_double_clicked(self, proxy_index):
        try:
            src_index = self._source_index_from_proxy_index(proxy_index, self.brewing_proxy)
            session = self.brewing_model.brewing_sessions[src_index.row()]
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

    # ---------- Статистика (метод внутри класса) ----------
    def update_stats(self):
        beans = self.db.get_all_coffee_beans()
        sessions = self.db.get_all_brewing_sessions()

        total_beans = len(beans)
        total_sessions = len(sessions)

        roast_counts = {}
        for b in beans:
            lvl = (b.get("roast_level") or "Unknown")
            roast_counts[lvl] = roast_counts.get(lvl, 0) + 1

        beans_with_images = sum(1 for b in beans if b.get("image"))
        images_pct = (beans_with_images / total_beans * 100) if total_beans else 0

        prices = [float(b.get("price")) for b in beans if b.get("price") is not None and b.get("price") != ""]
        avg_price = sum(prices) / len(prices) if prices else 0
        ratings = [float(b.get("rating")) for b in beans if b.get("rating") is not None and b.get("rating") != ""]
        avg_bean_rating = sum(ratings) / len(ratings) if ratings else 0

        top_beans = sorted([b for b in beans if b.get("rating")], key=lambda x: x["rating"], reverse=True)[:5]

        method_counts = {}
        for s in sessions:
            m = (s.get("brew_method") or "Unknown")
            method_counts[m] = method_counts.get(m, 0) + 1
        top_methods = sorted(method_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        brew_times = [int(s.get("brew_time")) for s in sessions if s.get("brew_time") is not None and s.get("brew_time") != ""]
        avg_brew_time = sum(brew_times)/len(brew_times) if brew_times else 0

        coffee_weights = [float(s.get("coffee_weight")) for s in sessions if s.get("coffee_weight") is not None and s.get("coffee_weight") != ""]
        water_weights = [float(s.get("water_weight")) for s in sessions if s.get("water_weight") is not None and s.get("water_weight") != ""]
        avg_coffee_weight = sum(coffee_weights)/len(coffee_weights) if coffee_weights else 0
        avg_water_weight = sum(water_weights)/len(water_weights) if water_weights else 0

        lines = []
        lines.append(f"Всего сортов: {total_beans}")
        lines.append(f"Всего сессий: {total_sessions}")
        lines.append(f"С изображениями: {beans_with_images} ({images_pct:.1f}%)")
        lines.append(f"Средняя цена: {avg_price:.2f} руб | Средний рейтинг сортов: {avg_bean_rating:.2f}")
        lines.append("")
        lines.append("Распределение по уровню обжарки:")
        for lvl, cnt in roast_counts.items():
            lines.append(f"  • {lvl}: {cnt}")
        lines.append("")
        lines.append("Топ-5 сортов по рейтингу:")
        if top_beans:
            for b in top_beans:
                lines.append(f"  • {b.get('name')} — {b.get('rating'):.1f}")
        else:
            lines.append("  • Отсутствуют оценки")
        lines.append("")
        lines.append("Самые используемые методы заваривания:")
        for m, c in top_methods:
            lines.append(f"  • {m}: {c} раз(а)")
        lines.append("")
        lines.append(f"Среднее время заваривания: {avg_brew_time:.1f} сек")
        lines.append(f"Средний вес кофе: {avg_coffee_weight:.1f} г | Средний вес воды: {avg_water_weight:.1f} г")

        stats_text = "\n".join(lines)
        try:
            self.statsText.setPlainText(stats_text)
        except Exception:
            te = getattr(self, "statsText", None)
            if te:
                te.setPlainText(stats_text)

    # ---------- клавиатурные события ----------
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
