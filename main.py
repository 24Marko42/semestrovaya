# main.py
import os
import sys
import sqlite3
import tempfile
import shutil
import gc
import logging

from PyQt5 import uic
from PyQt5.QtCore import Qt, QSortFilterProxyModel
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QFileDialog, QTextEdit, QWidget, QVBoxLayout, QMenu, QAction, QDialog
)

from database import DatabaseManager
from models import CoffeeBeansTableModel, BrewingSessionsTableModel
from dialogs import CoffeeDialog, BrewingDialog, DetailsDialog

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILENAME = "coffee_journal.db"

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


def resource_path(relative_path: str) -> str:
    """Return path to resource, works for dev and PyInstaller (_MEIPASS)."""
    try:
        base = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base = BASE_DIR
    return os.path.join(base, relative_path)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        ui_file = resource_path(os.path.join("ui", "main_window.ui"))
        if not os.path.exists(ui_file):
            QMessageBox.critical(None, "Ошибка", f"UI не найден: {ui_file}")
            raise SystemExit(1)

        uic.loadUi(ui_file, self)

        # apply style
        app = QApplication.instance()
        if app:
            app.setStyleSheet(APP_STYLE)

        # database and models
        self.db_path = os.path.join(BASE_DIR, DB_FILENAME)
        self.db = DatabaseManager(self.db_path)

        self.coffee_model = CoffeeBeansTableModel()
        self.brewing_model = BrewingSessionsTableModel()

        # proxies (sorting & filtering)
        self.coffee_proxy = QSortFilterProxyModel(self)
        self.coffee_proxy.setSourceModel(self.coffee_model)
        self.coffee_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.brewing_proxy = QSortFilterProxyModel(self)
        self.brewing_proxy.setSourceModel(self.brewing_model)
        self.brewing_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # bind table views to proxies (safe)
        self._bind_table_safe("coffeeTable", self.coffee_proxy)
        self._bind_table_safe("brewingTable", self.brewing_proxy)

        # connect buttons safely (objectNames expected in UI)
        self._connect_safe("addCoffeeBtn", self.add_coffee)
        self._connect_safe("editCoffeeBtn", self.edit_coffee)
        self._connect_safe("deleteCoffeeBtn", self.delete_coffee)
        self._connect_safe("refreshCoffeeBtn", self.load_coffee_data)
        self._connect_safe("coffeeSearchBtn", self.search_coffee)
        self._connect_safe("coffeeClearBtn", self.clear_coffee_search)

        self._connect_safe("addBrewingBtn", self.add_brewing)
        self._connect_safe("editBrewingBtn", self.edit_brewing)
        self._connect_safe("deleteBrewingBtn", self.delete_brewing)
        self._connect_safe("refreshBrewingBtn", self.load_brewing_data)
        self._connect_safe("brewingSearchBtn", self.search_brewing)
        self._connect_safe("brewingClearBtn", self.clear_brewing_search)

        # Enter triggers search if line edits exist
        self._connect_return_safe("coffeeSearchEdit", self.search_coffee)
        self._connect_return_safe("coffeeSearchInput", self.search_coffee)
        self._connect_return_safe("brewingSearchEdit", self.search_brewing)

        # selection and double click
        self._safe(lambda: self.coffeeTable.clicked.connect(lambda idx: self.coffeeTable.selectRow(idx.row())))
        self._safe(lambda: self.brewingTable.clicked.connect(lambda idx: self.brewingTable.selectRow(idx.row())))
        self._safe(lambda: self.coffeeTable.doubleClicked.connect(self.on_coffee_double_clicked))
        self._safe(lambda: self.brewingTable.doubleClicked.connect(self.on_brewing_double_clicked))

        # context menus
        self._safe(lambda: self.coffeeTable.setContextMenuPolicy(Qt.CustomContextMenu))
        self._safe(lambda: self.coffeeTable.customContextMenuRequested.connect(self._coffee_context))
        self._safe(lambda: self.brewingTable.setContextMenuPolicy(Qt.CustomContextMenu))
        self._safe(lambda: self.brewingTable.customContextMenuRequested.connect(self._brewing_context))

        # ensure stats text exists (fallback)
        self._ensure_stats_text()

        # add import/export menu
        self._setup_db_menu()

        # initial load
        self.load_coffee_data()
        self.load_brewing_data()

    # ---------- safe helpers ----------
    def _safe(self, fn):
        try:
            fn()
        except Exception as e:
            logger.debug("safe skip: %s", e)

    def _connect_safe(self, name: str, slot):
        try:
            getattr(self, name).clicked.connect(slot)
        except Exception:
            logger.debug("widget not found: %s", name)

    def _connect_return_safe(self, name: str, slot):
        try:
            getattr(self, name).returnPressed.connect(slot)
        except Exception:
            pass

    def _bind_table_safe(self, name: str, proxy):
        try:
            view = getattr(self, name)
            view.setModel(proxy)
            view.setSortingEnabled(True)
            view.setSelectionBehavior(view.SelectRows)
        except Exception:
            logger.debug("table not found or bind failed: %s", name)

    # ---------- DB import/export ----------
    def _setup_db_menu(self):
        try:
            menubar = self.menuBar()
            file_menu = menubar.addMenu("Файл")
            export_action = QAction("Экспорт БД...", self)
            export_action.triggered.connect(self.export_database)
            file_menu.addAction(export_action)
            import_action = QAction("Импорт БД...", self)
            import_action.triggered.connect(self.import_database)
            file_menu.addAction(import_action)
        except Exception:
            pass

    def export_database(self):
        """Export current DB to chosen file using sqlite backup (safe while DB opened)."""
        target, _ = QFileDialog.getSaveFileName(self, "Экспортировать базу", "", "SQLite DB (*.db);;All files (*)")
        if not target:
            return
        if not os.path.exists(self.db_path):
            QMessageBox.critical(self, "Ошибка", f"Файл БД не найден:\n{self.db_path}")
            return
        try:
            src_conn = sqlite3.connect(self.db_path)
            try:
                dest_conn = sqlite3.connect(target)
                try:
                    with dest_conn:
                        src_conn.backup(dest_conn, pages=0)
                finally:
                    dest_conn.close()
            finally:
                src_conn.close()
            QMessageBox.information(self, "Готово", f"Экспорт завершён:\n{target}")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))

    def import_database(self):
        """Import DB from file: backup chosen DB into temporary file and replace current DB safely."""
        src_file, _ = QFileDialog.getOpenFileName(self, "Импортировать базу", "", "SQLite DB (*.db);;All files (*)")
        if not src_file:
            return
        confirm = QMessageBox.question(self, "Подтвердите", "Импорт заменит текущую базу. Продолжить?", QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        try:
            # create temporary copy by backing up chosen DB into tmp file
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
            os.close(tmp_fd)
            src_conn = sqlite3.connect(src_file)
            try:
                dest_conn = sqlite3.connect(tmp_path)
                try:
                    with dest_conn:
                        src_conn.backup(dest_conn, pages=0)
                finally:
                    dest_conn.close()
            finally:
                src_conn.close()

            # try to close current db connections if possible
            try:
                if hasattr(self, "db") and hasattr(self.db, "close"):
                    self.db.close()
                gc.collect()
            except Exception:
                pass

            # replace existing db file with tmp copy
            shutil.copy2(tmp_path, self.db_path)
            try:
                os.remove(tmp_path)
            except Exception:
                pass

            # recreate db manager and reload UI
            self.db = DatabaseManager(self.db_path)
            self.load_coffee_data()
            self.load_brewing_data()
            QMessageBox.information(self, "Готово", "Импорт завершён.")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))
        except PermissionError:
            QMessageBox.critical(self, "Ошибка доступа", "Файл занят другим процессом — закройте программы, использующие базу и попробуйте снова.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))

    # ---------- load data ----------
    def load_coffee_data(self):
        try:
            beans = self.db.get_all_coffee_beans()
            self.coffee_model.update_data(beans)
        except Exception as e:
            logger.exception("load_coffee_data: %s", e)
        self.update_stats()

    def load_brewing_data(self):
        try:
            sessions = self.db.get_all_brewing_sessions()
            self.brewing_model.update_data(sessions)
        except Exception as e:
            logger.exception("load_brewing_data: %s", e)
        self.update_stats()

    # ---------- CRUD coffee ----------
    def add_coffee(self):
        dlg = CoffeeDialog(self.db, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.load_coffee_data()

    def edit_coffee(self):
        try:
            sel = self.coffeeTable.selectionModel().selectedRows()
            if not sel:
                QMessageBox.information(self, "Инфо", "Выберите строку")
                return
            proxy_index = sel[0]
            src_index = self.coffee_proxy.mapToSource(proxy_index)
            bean = self.coffee_model.coffee_beans[src_index.row()]
            dlg = CoffeeDialog(self.db, coffee_data=bean, parent=self)
            if dlg.exec_() == QDialog.Accepted:
                self.load_coffee_data()
        except Exception as e:
            logger.exception("edit_coffee: %s", e)
            QMessageBox.information(self, "Инфо", "Ошибка выбора записи")

    def delete_coffee(self):
        try:
            sel = self.coffeeTable.selectionModel().selectedRows()
            if not sel:
                QMessageBox.information(self, "Инфо", "Выберите строку")
                return
            proxy_index = sel[0]
            src_index = self.coffee_proxy.mapToSource(proxy_index)
            bean = self.coffee_model.coffee_beans[src_index.row()]
            if QMessageBox.question(self, "Удалить", f"Удалить '{bean.get('name')}'?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                ok = self.db.delete_coffee_bean(bean["id"])
                if ok:
                    self.load_coffee_data()
                    self.load_brewing_data()
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось удалить")
        except Exception as e:
            logger.exception("delete_coffee: %s", e)
            QMessageBox.critical(self, "Ошибка", "Ошибка при удалении")

    # ---------- CRUD brewing ----------
    def add_brewing(self):
        beans = self.db.get_all_coffee_beans()
        if not beans:
            QMessageBox.information(self, "Инфо", "Сначала добавьте сорт кофе")
            return
        dlg = BrewingDialog(self.db, coffee_beans=beans, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.load_brewing_data()

    def edit_brewing(self):
        try:
            sel = self.brewingTable.selectionModel().selectedRows()
            if not sel:
                QMessageBox.information(self, "Инфо", "Выберите строку")
                return
            proxy_index = sel[0]
            src_index = self.brewing_proxy.mapToSource(proxy_index)
            sess = self.brewing_model.brewing_sessions[src_index.row()]
            dlg = BrewingDialog(self.db, coffee_beans=self.db.get_all_coffee_beans(), brewing_data=sess, parent=self)
            if dlg.exec_() == QDialog.Accepted:
                self.load_brewing_data()
        except Exception as e:
            logger.exception("edit_brewing: %s", e)
            QMessageBox.critical(self, "Ошибка", "Ошибка при редактировании")

    def delete_brewing(self):
        try:
            sel = self.brewingTable.selectionModel().selectedRows()
            if not sel:
                QMessageBox.information(self, "Инфо", "Выберите строку")
                return
            proxy_index = sel[0]
            src_index = self.brewing_proxy.mapToSource(proxy_index)
            s = self.brewing_model.brewing_sessions[src_index.row()]
            if QMessageBox.question(self, "Удалить", "Удалить сессию?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                ok = self.db.delete_brewing_session(s["id"])
                if ok:
                    self.load_brewing_data()
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось удалить")
        except Exception as e:
            logger.exception("delete_brewing: %s", e)
            QMessageBox.critical(self, "Ошибка", "Ошибка при удалении")

    # ---------- search ----------
    def search_coffee(self):
        q = ""
        try:
            if hasattr(self, "coffeeSearchEdit"):
                q = self.coffeeSearchEdit.text().strip()
            elif hasattr(self, "coffeeSearchInput"):
                q = self.coffeeSearchInput.text().strip()
        except Exception:
            q = ""
        if not q:
            self.coffee_proxy.setFilterRegExp("")
            self.load_coffee_data()
            return
        if q.isdigit():
            beans = self.db.get_all_coffee_beans()
            matched = [b for b in beans if str(b.get("id")) == q]
            self.coffee_model.update_data(matched)
            self.coffee_proxy.setFilterRegExp("")
            return
        self.coffee_proxy.setFilterKeyColumn(1)
        self.coffee_proxy.setFilterRegExp(q)

    def clear_coffee_search(self):
        try:
            if hasattr(self, "coffeeSearchEdit"):
                self.coffeeSearchEdit.clear()
            elif hasattr(self, "coffeeSearchInput"):
                self.coffeeSearchInput.clear()
        except Exception:
            pass
        self.coffee_proxy.setFilterRegExp("")
        self.load_coffee_data()

    def search_brewing(self):
        q = ""
        try:
            if hasattr(self, "brewingSearchEdit"):
                q = self.brewingSearchEdit.text().strip()
        except Exception:
            q = ""
        if not q:
            self.load_brewing_data()
            return
        res = self.db.search_brewing_sessions(q)
        self.brewing_model.update_data(res)

    def clear_brewing_search(self):
        try:
            if hasattr(self, "brewingSearchEdit"):
                self.brewingSearchEdit.clear()
        except Exception:
            pass
        self.load_brewing_data()

    # ---------- context menus ----------
    def _coffee_context(self, pos):
        try:
            menu = QMenu(self)
            menu.addAction("Просмотреть", self._view_coffee_from_context)
            menu.addAction("Редактировать", self.edit_coffee)
            menu.addAction("Удалить", self.delete_coffee)
            menu.exec_(self.coffeeTable.viewport().mapToGlobal(pos))
        except Exception as e:
            logger.debug(e)

    def _brewing_context(self, pos):
        try:
            menu = QMenu(self)
            menu.addAction("Редактировать", self.edit_brewing)
            menu.addAction("Удалить", self.delete_brewing)
            menu.exec_(self.brewingTable.viewport().mapToGlobal(pos))
        except Exception as e:
            logger.debug(e)

    def _view_coffee_from_context(self):
        sel = self.coffeeTable.selectionModel().selectedRows()
        if not sel:
            return
        src_index = self.coffee_proxy.mapToSource(sel[0])
        bean = self.coffee_model.coffee_beans[src_index.row()]
        self._show_coffee_details(bean)

    # ---------- details (double click handlers) ----------
    def on_coffee_double_clicked(self, proxy_index):
        try:
            src_index = self.coffee_proxy.mapToSource(proxy_index)
            bean = self.coffee_model.coffee_beans[src_index.row()]
            self._show_coffee_details(bean)
        except Exception as e:
            logger.debug(e)

    def on_brewing_double_clicked(self, proxy_index):
        try:
            src_index = self.brewing_proxy.mapToSource(proxy_index)
            s = self.brewing_model.brewing_sessions[src_index.row()]
            bean = next((b for b in self.db.get_all_coffee_beans() if b["id"] == s.get("coffee_bean_id")), None)
            dlg = DetailsDialog(self)
            dlg.set_image_from_bytes(bean.get("image") if bean else None)
            dlg.set_text("\n".join([
                f"Кофе: {s.get('coffee_name') or '-'}",
                f"Метод: {s.get('brew_method') or '-'}",
                f"Температура: {s.get('water_temp') or '-'}",
                f"Время: {s.get('brew_time') or '-'}",
                f"Вес кофе: {s.get('coffee_weight') or '-'}",
                f"Заметки: {s.get('notes') or '-'}",
                f"Дата: {s.get('created_at') or '-'}"
            ]))
            dlg.exec_()
        except Exception as e:
            logger.debug(e)

    def _show_coffee_details(self, bean):
        dlg = DetailsDialog(self)
        dlg.set_image_from_bytes(bean.get("image"))
        dlg.set_text("\n".join([
            f"Название: {bean.get('name')}",
            f"Обжарщик: {bean.get('roaster') or '-'}",
            f"Уровень обжарки: {bean.get('roast_level') or '-'}",
            f"Происхождение: {bean.get('origin') or '-'}",
            f"Метод обработки: {bean.get('processing_method') or '-'}",
            f"Вкусовые ноты: {bean.get('tasting_notes') or '-'}",
            f"Рейтинг: {bean.get('rating') or '-'}",
            f"Цена: {bean.get('price') or '-'}",
            f"Дата: {bean.get('created_at') or '-'}"
        ]))
        dlg.exec_()

    # ---------- statistics ----------
    def _ensure_stats_text(self):
        try:
            if not hasattr(self, "statsText") or self.statsText is None:
                tab_widget = getattr(self, "tabs", None) or getattr(self, "tabWidget", None)
                if tab_widget:
                    last_index = tab_widget.count() - 1
                    w = tab_widget.widget(last_index)
                    te = QTextEdit()
                    te.setReadOnly(True)
                    layout = w.layout()
                    if layout:
                        layout.addWidget(te)
                    else:
                        container = QWidget()
                        v = QVBoxLayout(container)
                        v.addWidget(te)
                        tab_widget.removeTab(last_index)
                        tab_widget.insertTab(last_index, container, tab_widget.tabText(last_index))
                    self.statsText = te
        except Exception:
            pass

    def update_stats(self):
        try:
            beans = self.db.get_all_coffee_beans()
            sessions = self.db.get_all_brewing_sessions()

            total_beans = len(beans)
            total_sessions = len(sessions)
            roast_counts = {}
            for b in beans:
                lvl = b.get("roast_level") or "Unknown"
                roast_counts[lvl] = roast_counts.get(lvl, 0) + 1

            with_images = sum(1 for b in beans if b.get("image"))
            images_pct = (with_images / total_beans * 100) if total_beans else 0
            prices = [float(b.get("price")) for b in beans if b.get("price") not in (None, "")]
            avg_price = (sum(prices) / len(prices)) if prices else 0
            ratings = [float(b.get("rating")) for b in beans if b.get("rating") not in (None, "")]
            avg_rating = (sum(ratings) / len(ratings)) if ratings else 0

            method_counts = {}
            for s in sessions:
                m = s.get("brew_method") or "Unknown"
                method_counts[m] = method_counts.get(m, 0) + 1
            top_methods = sorted(method_counts.items(), key=lambda x: -x[1])[:5]

            brew_times = [int(s.get("brew_time")) for s in sessions if s.get("brew_time") not in (None, "")]
            avg_brew = (sum(brew_times) / len(brew_times)) if brew_times else 0

            coffee_weights = [float(s.get("coffee_weight")) for s in sessions if s.get("coffee_weight") not in (None, "")]
            water_weights = [float(s.get("water_weight")) for s in sessions if s.get("water_weight") not in (None, "")]
            avg_cw = (sum(coffee_weights) / len(coffee_weights)) if coffee_weights else 0
            avg_ww = (sum(water_weights) / len(water_weights)) if water_weights else 0

            lines = [
                f"Всего сортов: {total_beans}",
                f"Всего сессий: {total_sessions}",
                f"С изображениями: {with_images} ({images_pct:.1f}%)",
                f"Средняя цена: {avg_price:.2f} руб | Средний рейтинг сортов: {avg_rating:.2f}",
                "",
                "Распределение по уровню обжарки:",
            ]
            for k, v in roast_counts.items():
                lines.append(f"  • {k}: {v}")
            lines += ["", "Топ-5 методов заваривания:"]
            for m, c in top_methods:
                lines.append(f"  • {m}: {c}")
            lines += ["", f"Среднее время заваривания: {avg_brew:.1f} сек",
                      f"Средний вес кофе: {avg_cw:.1f} г | воды: {avg_ww:.1f} г"]

            stats_text = "\n".join(lines)
            if hasattr(self, "statsText") and self.statsText:
                self.statsText.setPlainText(stats_text)
        except Exception as e:
            logger.exception("update_stats: %s", e)

    # ---------- keyboard ----------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.load_coffee_data(); self.load_brewing_data()
        elif event.key() == Qt.Key_Delete:
            try:
                cur = self.tabs.currentIndex()
            except Exception:
                cur = 0
            (self.delete_coffee if cur == 0 else self.delete_brewing)()
        super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Coffee Journal")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()