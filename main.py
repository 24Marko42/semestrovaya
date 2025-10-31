# main.py — компактная версия
import os, sys, logging
from PyQt5 import uic
from PyQt5.QtCore import Qt, QSortFilterProxyModel
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDialog, QMessageBox, QMenu, QHeaderView
)

from database import DatabaseManager
from models import CoffeeBeansTableModel, BrewingSessionsTableModel
from dialogs import CoffeeDialog, BrewingDialog, DetailsDialog

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APP_CSS = """
QMainWindow { background: #121212; color: #eaeaea; }
QWidget { background: #121212; color: #eaeaea; }
QTableView { background: #1e1e1e; color: #eaeaea; gridline-color: #2a2a2a; }
QHeaderView::section { background: #212121; color: #eaeaea; padding: 6px; }
QPushButton { background: #3b82f6; color: white; border-radius: 6px; padding: 6px 10px; }
QLineEdit, QTextEdit { background: #161616; color: #f5f5f5; border: 1px solid #2a2a2a; border-radius: 4px; }
QTabBar::tab { background: #212121; color: #eaeaea; padding: 8px 14px; border-radius: 8px; margin: 2px; }
QTabBar::tab:selected { background: #3b82f6; color: white; }
"""

def resource_path(rel):
    base = getattr(sys, "_MEIPASS", BASE_DIR)
    return os.path.join(base, rel)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ui_file = resource_path(os.path.join("ui", "main_window.ui"))
        if not os.path.exists(ui_file):
            QMessageBox.critical(None, "Ошибка", f"UI не найден: {ui_file}")
            raise SystemExit(1)
        uic.loadUi(ui_file, self)
        QApplication.instance().setStyleSheet(APP_CSS)

        # DB + модели
        self.db = DatabaseManager()
        self.coffee_model = CoffeeBeansTableModel()
        self.brewing_model = BrewingSessionsTableModel()

        # proxy (сортировка/фильтр)
        self.coffee_proxy = QSortFilterProxyModel(self); self.coffee_proxy.setSourceModel(self.coffee_model)
        self.coffee_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.brewing_proxy = QSortFilterProxyModel(self); self.brewing_proxy.setSourceModel(self.brewing_model)
        self.brewing_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # views
        self._bind_table("coffeeTable", self.coffee_proxy)
        self._bind_table("brewingTable", self.brewing_proxy)

        # подключаем кнопки (если есть)
        self._connect("addCoffeeBtn", self.add_coffee)
        self._connect("editCoffeeBtn", self.edit_coffee)
        self._connect("deleteCoffeeBtn", self.delete_coffee)
        self._connect("refreshCoffeeBtn", self.load_coffee_data)
        self._connect("coffeeSearchBtn", self.search_coffee)
        self._connect("coffeeClearBtn", self.clear_coffee_search)

        self._connect("addBrewingBtn", self.add_brewing)
        self._connect("editBrewingBtn", self.edit_brewing)
        self._connect("deleteBrewingBtn", self.delete_brewing)
        self._connect("refreshBrewingBtn", self.load_brewing_data)
        self._connect("brewingSearchBtn", self.search_brewing)
        self._connect("brewingClearBtn", self.clear_brewing_search)

        # Enter для поиска
        self._connect_return("coffeeSearchEdit", self.search_coffee)
        self._connect_return("coffeeSearchInput", self.search_coffee)
        self._connect_return("brewingSearchEdit", self.search_brewing)

        # клики/контекст/двойной клик
        self._safe(lambda: self.coffeeTable.clicked.connect(lambda i: self.coffeeTable.selectRow(i.row())))
        self._safe(lambda: self.brewingTable.clicked.connect(lambda i: self.brewingTable.selectRow(i.row())))
        self._safe(lambda: self.coffeeTable.setContextMenuPolicy(Qt.CustomContextMenu))
        self._safe(lambda: self.coffeeTable.customContextMenuRequested.connect(self._coffee_context))
        self._safe(lambda: self.coffeeTable.doubleClicked.connect(self.on_coffee_double_clicked))
        self._safe(lambda: self.brewingTable.setContextMenuPolicy(Qt.CustomContextMenu))
        self._safe(lambda: self.brewingTable.customContextMenuRequested.connect(self._brewing_context))
        self._safe(lambda: self.brewingTable.doubleClicked.connect(self.on_brewing_double_clicked))

        # загрузка
        self.load_coffee_data(); self.load_brewing_data()

    # ---------- утилиты ----------
    def _safe(self, fn):
        try: fn()
        except Exception as e: log.debug("safe skip: %s", e)

    def _connect(self, name, slot):
        try:
            getattr(self, name).clicked.connect(slot)
        except Exception:
            log.debug("no widget %s", name)

    def _connect_return(self, name, slot):
        try:
            getattr(self, name).returnPressed.connect(slot)
        except Exception:
            pass

    def _bind_table(self, name, proxy):
        try:
            view = getattr(self, name)
            view.setModel(proxy)
            view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            view.setSortingEnabled(True)
            view.setSelectionBehavior(view.SelectRows)
        except Exception:
            log.debug("table %s not bound", name)

    def _map_selected_source(self, view, proxy):
        try:
            sel = view.selectionModel().selectedRows()
            if not sel: return None
            return proxy.mapToSource(sel[0])
        except Exception:
            return None

    def _map_proxy_to_source(self, proxy_index, proxy):
        try: return proxy.mapToSource(proxy_index)
        except Exception: return proxy_index

    # ---------- загрузка ----------
    def load_coffee_data(self):
        try:
            self.coffee_model.update_data(self.db.get_all_coffee_beans())
        except Exception as e:
            log.exception(e)
        self.update_stats()

    def load_brewing_data(self):
        try:
            self.brewing_model.update_data(self.db.get_all_brewing_sessions())
        except Exception as e:
            log.exception(e)
        self.update_stats()

    # ---------- CRUD coffee ----------
    def add_coffee(self):
        d = CoffeeDialog(self.db, parent=self)
        if d.exec_() == QDialog.Accepted: self.load_coffee_data()

    def edit_coffee(self):
        idx = self._map_selected_source(self.coffeeTable, self.coffee_proxy)
        if not idx:
            QMessageBox.information(self, "Инфо", "Выберите строку")
            return
        bean = self.coffee_model.coffee_beans[idx.row()]
        d = CoffeeDialog(self.db, coffee_data=bean, parent=self)
        if d.exec_() == QDialog.Accepted: self.load_coffee_data()

    def delete_coffee(self):
        idx = self._map_selected_source(self.coffeeTable, self.coffee_proxy)
        if not idx:
            QMessageBox.information(self, "Инфо", "Выберите строку")
            return
        bean = self.coffee_model.coffee_beans[idx.row()]
        if QMessageBox.question(self, "Удалить?", f"Удалить '{bean.get('name')}'?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            if self.db.delete_coffee_bean(bean["id"]): self.load_coffee_data(); self.load_brewing_data()
            else: QMessageBox.critical(self, "Ошибка", "Не удалось удалить")

    # ---------- CRUD brewing ----------
    def add_brewing(self):
        beans = self.db.get_all_coffee_beans()
        if not beans: QMessageBox.information(self, "Инфо", "Добавьте сначала сорт кофе"); return
        d = BrewingDialog(self.db, coffee_beans=beans, parent=self)
        if d.exec_() == QDialog.Accepted: self.load_brewing_data()

    def edit_brewing(self):
        idx = self._map_selected_source(self.brewingTable, self.brewing_proxy)
        if not idx: QMessageBox.information(self, "Инфо", "Выберите строку"); return
        session = self.brewing_model.brewing_sessions[idx.row()]
        d = BrewingDialog(self.db, coffee_beans=self.db.get_all_coffee_beans(), brewing_data=session, parent=self)
        if d.exec_() == QDialog.Accepted: self.load_brewing_data()

    def delete_brewing(self):
        idx = self._map_selected_source(self.brewingTable, self.brewing_proxy)
        if not idx: QMessageBox.information(self, "Инфо", "Выберите строку"); return
        s = self.brewing_model.brewing_sessions[idx.row()]
        if QMessageBox.question(self, "Удалить?", "Удалить сессию?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            if self.db.delete_brewing_session(s["id"]): self.load_brewing_data()
            else: QMessageBox.critical(self, "Ошибка", "Не удалось удалить")

    # ---------- Поиск (Enter поддерживается) ----------
    def search_coffee(self):
        q = ""
        try:
            if hasattr(self, "coffeeSearchEdit"): q = self.coffeeSearchEdit.text().strip()
            elif hasattr(self, "coffeeSearchInput"): q = self.coffeeSearchInput.text().strip()
        except Exception: q = ""
        if not q:
            self.coffee_proxy.setFilterRegExp(""); self.load_coffee_data(); return
        if q.isdigit():
            beans = self.db.get_all_coffee_beans()
            self.coffee_model.update_data([b for b in beans if str(b.get("id"))==q]); self.coffee_proxy.setFilterRegExp(""); return
        self.coffee_proxy.setFilterKeyColumn(1); self.coffee_proxy.setFilterRegExp(q)

    def clear_coffee_search(self):
        try:
            if hasattr(self, "coffeeSearchEdit"): self.coffeeSearchEdit.clear()
            elif hasattr(self, "coffeeSearchInput"): self.coffeeSearchInput.clear()
        except Exception: pass
        self.coffee_proxy.setFilterRegExp(""); self.load_coffee_data()

    def search_brewing(self):
        q = getattr(self, "brewingSearchEdit", None)
        q = q.text().strip() if q else ""
        if not q: self.load_brewing_data(); return
        self.brewing_model.update_data(self.db.search_brewing_sessions(q))

    def clear_brewing_search(self):
        try:
            if hasattr(self, "brewingSearchEdit"): self.brewingSearchEdit.clear()
        except Exception: pass
        self.load_brewing_data()

    # ---------- Контекстные меню ----------
    def _coffee_context(self, pos):
        try:
            m = QMenu(self); m.addAction("Просмотреть", self._view_coffee_from_context)
            m.addAction("Редактировать", self.edit_coffee); m.addAction("Удалить", self.delete_coffee)
            m.exec_(self.coffeeTable.viewport().mapToGlobal(pos))
        except Exception as e: log.debug(e)

    def _brewing_context(self, pos):
        try:
            m = QMenu(self); m.addAction("Редактировать", self.edit_brewing); m.addAction("Удалить", self.delete_brewing)
            m.exec_(self.brewingTable.viewport().mapToGlobal(pos))
        except Exception as e: log.debug(e)

    def _view_coffee_from_context(self):
        idx = self._map_selected_source(self.coffeeTable, self.coffee_proxy)
        if not idx: return
        bean = self.coffee_model.coffee_beans[idx.row()]; self._show_coffee_details(bean)

    # ---------- Двойной клик -> детали ----------
    def on_coffee_double_clicked(self, proxy_index):
        src = self._map_proxy_to_source(proxy_index, self.coffee_proxy)
        bean = self.coffee_model.coffee_beans[src.row()]; self._show_coffee_details(bean)

    def on_brewing_double_clicked(self, proxy_index):
        src = self._map_proxy_to_source(proxy_index, self.brewing_proxy)
        s = self.brewing_model.brewing_sessions[src.row()]
        bean = next((b for b in self.db.get_all_coffee_beans() if b["id"]==s.get("coffee_bean_id")), None)
        dlg = DetailsDialog(self); dlg.set_image_from_bytes(bean.get("image") if bean else None)
        dlg.set_text("\n".join([
            f"Кофе: {s.get('coffee_name') or '-'}",
            f"Метод: {s.get('brew_method') or '-'}",
            f"Темп: {s.get('water_temp') or '-'}",
            f"Время: {s.get('brew_time') or '-'}",
            f"Вес кофе: {s.get('coffee_weight') or '-'}",
            f"Заметки: {s.get('notes') or '-'}",
            f"Дата: {s.get('created_at') or '-'}"
        ])); dlg.exec_()

    def _show_coffee_details(self, bean):
        dlg = DetailsDialog(self); dlg.set_image_from_bytes(bean.get("image"))
        dlg.set_text("\n".join([
            f"Название: {bean.get('name')}",
            f"Обжарщик: {bean.get('roaster') or '-'}",
            f"Ур. обжарки: {bean.get('roast_level') or '-'}",
            f"Происхождение: {bean.get('origin') or '-'}",
            f"Метод обработки: {bean.get('processing_method') or '-'}",
            f"Вкусовые ноты: {bean.get('tasting_notes') or '-'}",
            f"Рейтинг: {bean.get('rating') or '-'}",
            f"Цена: {bean.get('price') or '-'}",
            f"Дата: {bean.get('created_at') or '-'}"
        ])); dlg.exec_()

    # ---------- Статистика ----------
    def update_stats(self):
        beans, sessions = self.db.get_all_coffee_beans(), self.db.get_all_brewing_sessions()
        total_beans, total_sessions = len(beans), len(sessions)
        roast = {}
        for b in beans: roast[(b.get("roast_level") or "Unknown")] = roast.get((b.get("roast_level") or "Unknown"),0)+1
        with_img = sum(1 for b in beans if b.get("image"))
        prices = [float(b.get("price")) for b in beans if b.get("price") not in (None,"")]
        avg_price = (sum(prices)/len(prices)) if prices else 0
        ratings = [float(b.get("rating")) for b in beans if b.get("rating") not in (None,"")]
        avg_rating = (sum(ratings)/len(ratings)) if ratings else 0
        methods = {}
        for s in sessions: methods[s.get("brew_method") or "Unknown"] = methods.get(s.get("brew_method") or "Unknown",0)+1
        top_methods = sorted(methods.items(), key=lambda x:-x[1])[:5]
        brew_times = [int(s.get("brew_time")) for s in sessions if s.get("brew_time") not in (None,"")]
        avg_brew = (sum(brew_times)/len(brew_times)) if brew_times else 0
        coffee_weights = [float(s.get("coffee_weight")) for s in sessions if s.get("coffee_weight") not in (None,"")]
        water_weights = [float(s.get("water_weight")) for s in sessions if s.get("water_weight") not in (None,"")]
        avg_cw = (sum(coffee_weights)/len(coffee_weights)) if coffee_weights else 0
        avg_ww = (sum(water_weights)/len(water_weights)) if water_weights else 0

        lines = [
            f"Всего сортов: {total_beans}",
            f"Всего сессий: {total_sessions}",
            f"С изображениями: {with_img} ({(with_img/total_beans*100) if total_beans else 0:.1f}%)",
            f"Средняя цена: {avg_price:.2f} руб | Средний рейтинг: {avg_rating:.2f}",
            "",
            "Распределение по обжарке:"
        ] + [f"  • {k}: {v}" for k,v in roast.items()] + ["", "Топ методов:"] + [f"  • {m}: {c}" for m,c in top_methods] + [
            "", f"Среднее время: {avg_brew:.1f} сек",
            f"Средний вес кофе: {avg_cw:.1f} г | воды: {avg_ww:.1f} г"
        ]
        text = "\n".join(lines)
        try: self.statsText.setPlainText(text)
        except Exception:
            t = getattr(self, "statsText", None)
            if t: t.setPlainText(text)

    # ---------- клавиши ----------
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F5: self.load_coffee_data(); self.load_brewing_data()
        elif e.key() == Qt.Key_Delete:
            try:
                cur = self.tabs.currentIndex()
            except Exception: cur = 0
            (self.delete_coffee if cur==0 else self.delete_brewing)()
        super().keyPressEvent(e)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Coffee Journal")
    w = MainWindow(); w.show()
    sys.exit(app.exec_())

if __name__ == "__main__": main()
