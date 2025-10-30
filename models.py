# models.py
from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex
from PyQt5.QtGui import QColor


class CoffeeBeansTableModel(QAbstractTableModel):
    """Модель для таблицы сортов кофе."""

    def __init__(self, data=None):
        super().__init__()
        self.coffee_beans = data or []
        self.headers = ["ID", "Название", "Обжарщик", "Уровень обжарки", "Происхождение", "Рейтинг"]

    def rowCount(self, parent=QModelIndex()):
        return len(self.coffee_beans)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        if not (0 <= row < len(self.coffee_beans)):
            return None

        bean = self.coffee_beans[row]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return bean.get("id")
            if col == 1:
                return bean.get("name", "")
            if col == 2:
                return bean.get("roaster") or "-"
            if col == 3:
                return bean.get("roast_level") or "-"
            if col == 4:
                return bean.get("origin") or "-"
            if col == 5:
                rating = bean.get("rating")
                return f"{rating:.1f}" if rating else "-"

        # Background for rating column (keeps previous behavior)
        if role == Qt.BackgroundRole and col == 5:
            rating = bean.get("rating") or 0
            if rating >= 4.5:
                return QColor(144, 238, 144)  # light green
            if rating >= 4.0:
                return QColor(255, 255, 224)  # light yellow

        # Foreground (text color) for rating column to ensure readability
        if role == Qt.ForegroundRole and col == 5:
            rating = bean.get("rating") or 0
            # if background is light, use dark text; otherwise white
            if rating >= 4.0:
                return QColor(0, 0, 0)  # dark text on light bg
            return QColor(255, 255, 255)  # white text on dark bg

        if role == Qt.TextAlignmentRole and col in (0, 5):
            return Qt.AlignCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self.coffee_beans = new_data or []
        self.endResetModel()


class BrewingSessionsTableModel(QAbstractTableModel):
    """Модель для таблицы сессий заваривания."""

    def __init__(self, data=None):
        super().__init__()
        self.brewing_sessions = data or []
        self.headers = ["ID", "Кофе", "Метод", "Температура", "Время", "Оценка", "Дата"]

    def rowCount(self, parent=QModelIndex()):
        return len(self.brewing_sessions)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        if not (0 <= row < len(self.brewing_sessions)):
            return None

        s = self.brewing_sessions[row]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return s.get("id")
            if col == 1:
                return s.get("coffee_name") or "-"
            if col == 2:
                return s.get("brew_method") or "-"
            if col == 3:
                return f"{s.get('water_temp')}°C" if s.get("water_temp") else "-"
            if col == 4:
                return f"{s.get('brew_time')}с" if s.get("brew_time") else "-"
            if col == 5:
                rating = s.get("rating")
                return f"{rating:.1f}" if rating else "-"
            if col == 6:
                created = s.get("created_at")
                return created[:10] if created else "-"

        if role == Qt.BackgroundRole and col == 5:
            rating = s.get("rating") or 0
            if rating >= 4.5:
                return QColor(144, 238, 144)
            if rating >= 4.0:
                return QColor(255, 255, 224)

        # readable text for rating in sessions
        if role == Qt.ForegroundRole and col == 5:
            rating = s.get("rating") or 0
            if rating >= 4.0:
                return QColor(0, 0, 0)
            return QColor(255, 255, 255)

        if role == Qt.TextAlignmentRole and col in (0, 3, 4, 5):
            return Qt.AlignCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self.brewing_sessions = new_data or []
        self.endResetModel()
