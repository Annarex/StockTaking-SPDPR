# File: ui/subcategory_view.py
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLabel, QMessageBox, QLineEdit,
                             QInputDialog, QFormLayout, QFileDialog, QComboBox, # Импортируем QComboBox
                             QDialog, QDialogButtonBox) # Импортируем QDialog и QDialogButtonBox
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError, QSqlRelationalTableModel
from PyQt5.QtCore import Qt, QModelIndex, QDate, QVariant, pyqtSignal # Импортируем pyqtSignal
import re # Для валидации двух символов (остается в View/Dialog для UI-валидации)

# Импортируем универсальный обработчик CSV (Контроллер будет использовать его)
# from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

# Импортируем схему базы данных (Модель будет использовать ее)
# from database import DATABASE_SCHEMA

# --- Диалог для добавления/редактирования подкатегории ---
# Этот диалог является частью View, он собирает данные от пользователя.
# Логика сохранения данных переносится в Controller.
class SubcategoryDialog(QDialog):
    def __init__(self, db_connection, subcategory_data=None, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.subcategory_data = subcategory_data
        self.setWindowTitle("Добавить/Редактировать подкатегорию")
        self.layout = QFormLayout(self)

        self.subcategory_id_input = QLineEdit()
        self.subcategory_id_input.setPlaceholderText("Введите 2 символа ID")
        self.subcategory_id_input.setMaxLength(2)

        self.category_combo = QComboBox()

        self.subcategory_name_input = QLineEdit()
        self.subcategory_name_input.setPlaceholderText("Введите название подкатегории")
        self.subcategory_name_input.setMaxLength(40)


        if self.subcategory_data:
             self.subcategory_id_input.setText(str(self.subcategory_data.get('id_subcategory', '')))
             self._populate_categories_combo()
             self._select_combo_item(self.category_combo, self.subcategory_data.get('id_category'))
             self.subcategory_name_input.setText(str(self.subcategory_data.get('subcategory', '')))
        else:
             self._populate_categories_combo()

        self.layout.addRow("ID Подкатегории:", self.subcategory_id_input)
        self.layout.addRow("Категория:", self.category_combo)
        self.layout.addRow("Название подкатегории:", self.subcategory_name_input)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def _populate_categories_combo(self):
        """
        Заполняет QComboBox категориями из базы данных.
        Этот метод остается в View/Dialog, так как он напрямую связан с UI элементом.
        """
        self.category_combo.clear()
        self.category_combo.addItem("Выберите категорию", None)
        query = QSqlQuery("SELECT id_category, category FROM Category ORDER BY category", self.db)
        while query.next():
            item_id = query.value(0)
            item_name = query.value(1)
            self.category_combo.addItem(item_name, item_id)

    def _select_combo_item(self, combo_box, item_id):
        """
        Выбирает элемент в комбобоксе по его UserData (ID).
        """
        if item_id is None:
            combo_box.setCurrentIndex(0)
            return
        for i in range(combo_box.count()):
            if combo_box.itemData(i) == item_id:
                combo_box.setCurrentIndex(i)
                return
        combo_box.setCurrentIndex(0)


    def get_data(self):
        data = {
            'id_subcategory': self.subcategory_id_input.text().strip(),
            'id_category': self.category_combo.currentData(),
            'subcategory': self.subcategory_name_input.text().strip(),
        }
        return data

    def validate_data(self):
        """
        Проверяет введенные данные на уровне UI (базовая валидация).
        Более сложная валидация (например, уникальность) выполняется в Модели.
        """
        data = self.get_data()
        if not data['id_subcategory']:
             QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите ID подкатегории.")
             return False
        if len(data['id_subcategory']) != 2:
             QMessageBox.warning(self, "Предупреждение", "ID подкатегории должен состоять ровно из 2 символов.")
             return False
        # TODO: Добавить валидацию формата ID, если требуется

        if data['id_category'] is None:
             QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите категорию.")
             return False

        if not data['subcategory']:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите название подкатегории.")
            return False
        if len(data['subcategory']) > 40:
             QMessageBox.warning(self, "Предупреждение", "Название подкатегории не может превышать 40 символов.")
             return False

        return True


class SubcategoryView(QWidget):
    # Определяем сигналы, которые будут испускаться при действиях пользователя.
    # Контроллер будет подключаться к этим сигналам.
    add_subcategory_requested = pyqtSignal()
    edit_subcategory_requested = pyqtSignal(int) # Сигнал испускает индекс строки для редактирования
    delete_subcategory_requested = pyqtSignal(int) # Сигнал испускает индекс строки для удаления
    refresh_list_requested = pyqtSignal() # Сигнал для запроса обновления списка
    import_csv_requested = pyqtSignal() # Сигнал для запроса импорта из CSV
    export_csv_requested = pyqtSignal() # Сигнал для запроса экспорта в CSV

    def __init__(self, parent=None):
        """
        Инициализирует виджет представления для управления подкатегориями.
        """
        super().__init__(parent)

        self.setWindowTitle("Управление подкатегориями")

        self.layout = QVBoxLayout(self)

        info_label = QLabel("Управление подкатегориями инвентаризации.")
        self.layout.addWidget(info_label)

        # --- Настройки таблицы ---
        self.table_view = QTableView()
        # Модель данных будет установлена Контроллером
        self.table_view.horizontalHeader().setStretchLastSection(True) # Растягиваем последний столбец
        self.table_view.setSelectionBehavior(QTableView.SelectRows) # Выделяем целые строки
        self.table_view.setSelectionMode(QTableView.SingleSelection) # Разрешаем выделять только одну строку
        self.table_view.setEditTriggers(QTableView.NoEditTriggers) # Отключаем редактирование прямо в таблице (редактирование через диалог)
        self.layout.addWidget(self.table_view)

        # Подключаем двойной клик по строке для редактирования
        self.table_view.doubleClicked.connect(self._on_double_click)


        # --- Кнопки управления (Добавить, Редактировать, Удалить, Импорт, Экспорт, Обновить) ---
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Добавить подкатегорию")
        edit_button = QPushButton("Редактировать выбранную")
        delete_button = QPushButton("Удалить выбранную")
        import_button = QPushButton("Импорт из CSV...")
        export_button = QPushButton("Экспорт в CSV...")
        refresh_button = QPushButton("Обновить список") # Кнопка обновления

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(import_button)
        buttons_layout.addWidget(export_button)
        buttons_layout.addWidget(refresh_button)
        buttons_layout.addStretch() # Растягиваем пространство после кнопок

        self.layout.addLayout(buttons_layout)

        # Подключаем сигналы кнопок к соответствующим сигналам View.
        # Контроллер будет подключаться к этим сигналам View.
        add_button.clicked.connect(self.add_subcategory_requested.emit)
        edit_button.clicked.connect(self._on_edit_button_clicked) 
        delete_button.clicked.connect(self._on_delete_button_clicked) 
        import_button.clicked.connect(self.import_csv_requested.emit)
        export_button.clicked.connect(self.export_csv_requested.emit)
        refresh_button.clicked.connect(self.refresh_list_requested.emit)

    def set_model(self, model):
        self.table_view.setModel(model)

    def get_selected_row(self):
        """ Возвращает индекс выбранной строки в таблице или -1, если ничего не выбрано. """
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            return -1
        return selected_indexes[0].row()

    def _on_double_click(self, index):
        row = index.row()
        self.edit_subcategory_requested.emit(row)

    def _on_edit_button_clicked(self):
        row = self.get_selected_row()
        if row == -1:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите подкатегорию для редактирования.")
            return
        self.edit_subcategory_requested.emit(row)

    def _on_delete_button_clicked(self):
        row = self.get_selected_row()
        if row == -1:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите подкатегорию для удаления.")
            return
        self.delete_subcategory_requested.emit(row)