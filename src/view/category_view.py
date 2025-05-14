# File: ui/category_view.py
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLabel, QMessageBox, QLineEdit,
                             QInputDialog, QFormLayout, QFileDialog,
                             QDialog, QDialogButtonBox) # Import QDialog and QDialogButtonBox
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError
from PyQt5.QtCore import Qt, QModelIndex, QDate, QVariant, pyqtSignal # Import pyqtSignal
import re # Для валидации двух символов (остается в View/Dialog для UI-валидации)

# Импортируем универсальный обработчик CSV (Controller will use this)
# from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

# Импортируем схему базы данных (Model will use this)
# from database import DATABASE_SCHEMA

# --- Диалог для добавления/редактирования категории ---
# Этот диалог остается частью View, но логика сохранения переносится в Controller
class CategoryDialog(QDialog):
    def __init__(self, category_data=None, parent=None):
        super().__init__(parent)
        self.category_data = category_data # None для добавления, dict для редактирования

        self.setWindowTitle("Добавить/Редактировать категорию")
        self.layout = QFormLayout(self)

        self.category_id_input = QLineEdit()
        self.category_id_input.setPlaceholderText("Введите 2 символа ID")
        self.category_id_input.setMaxLength(2) # Ограничение по длине

        self.category_name_input = QLineEdit()
        self.category_name_input.setPlaceholderText("Введите название категории")
        self.category_name_input.setMaxLength(40) # Ограничение по длине

        # Если редактируем, поле ID не должно быть редактируемым
        if self.category_data:
             self.category_id_input.setReadOnly(True)
             self.category_id_input.setText(str(self.category_data.get('id_category', '')))
             self.category_name_input.setText(str(self.category_data.get('category', '')))


        self.layout.addRow("ID Категории:", self.category_id_input)
        self.layout.addRow("Название категории:", self.category_name_input)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_data(self):
        """Возвращает данные из полей диалога в виде словаря."""
        data = {
            'id_category': self.category_id_input.text().strip(),
            'category': self.category_name_input.text().strip(),
        }
        return data

    def validate_data(self):
        """Проверяет введенные данные (базовая валидация UI)."""
        data = self.get_data()
        if not data['id_category']:
             QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите ID категории.")
             return False
        if len(data['id_category']) != 2:
             QMessageBox.warning(self, "Предупреждение", "ID категории должен состоять ровно из 2 символов.")
             return False
        # TODO: Добавить валидацию, если ID должен быть только цифрами или иметь определенный формат

        if not data['category']:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите название категории.")
            return False
        if len(data['category']) > 40:
             QMessageBox.warning(self, "Предупреждение", "Название категории не может превышать 40 символов.")
             return False

        return True


class CategoryView(QWidget):
    # Define signals that the Controller will connect to
    add_category_requested = pyqtSignal()
    edit_category_requested = pyqtSignal(int) # Emits row index
    delete_category_requested = pyqtSignal(int) # Emits row index
    refresh_list_requested = pyqtSignal()
    import_csv_requested = pyqtSignal()
    export_csv_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Управление категориями")

        self.layout = QVBoxLayout(self)

        info_label = QLabel("Управление категориями инвентаризации. ID и Название категории вводятся вручную.")
        self.layout.addWidget(info_label)

        # --- Настройки таблицы ---
        self.table_view = QTableView()
        # Model will be set by the Controller
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setEditTriggers(QTableView.NoEditTriggers) # Editing via dialog
        self.layout.addWidget(self.table_view)

        # Connect double click for editing
        self.table_view.doubleClicked.connect(self._on_double_click)


        # --- Кнопки управления (Добавить, Редактировать, Удалить, Импорт, Экспорт) ---
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Добавить категорию")
        edit_button = QPushButton("Редактировать выбранную")
        delete_button = QPushButton("Удалить выбранную")
        import_button = QPushButton("Импорт из CSV...")
        export_button = QPushButton("Экспорт в CSV...")
        refresh_button = QPushButton("Обновить список") # Add refresh button

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(import_button)
        buttons_layout.addWidget(export_button)
        buttons_layout.addWidget(refresh_button) # Add refresh button
        buttons_layout.addStretch()

        self.layout.addLayout(buttons_layout)

        # Подключаем сигналы к кнопкам (эти сигналы будут пойманы Controller'ом)
        add_button.clicked.connect(self.add_category_requested.emit)
        edit_button.clicked.connect(self._on_edit_button_clicked) # Use a helper to check selection
        delete_button.clicked.connect(self._on_delete_button_clicked) # Use a helper to check selection
        import_button.clicked.connect(self.import_csv_requested.emit)
        export_button.clicked.connect(self.export_csv_requested.emit)
        refresh_button.clicked.connect(self.refresh_list_requested.emit)

    def set_model(self, model):
        """Устанавливает модель данных для таблицы."""
        self.table_view.setModel(model)
        # Re-hide ID column if needed, after model is set
        # id_col_index = model.fieldIndex("id_category")
        # if id_col_index != -1:
        #      self.table_view.hideColumn(id_col_index) # Keep ID visible as per original view


    def get_selected_row(self):
        """Возвращает индекс выбранной строки или -1, если ничего не выбрано."""
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            return -1
        return selected_indexes[0].row()

    def _on_double_click(self, index):
        """Обработчик двойного клика по строке."""
        row = index.row()
        self.edit_category_requested.emit(row)

    def _on_edit_button_clicked(self):
        """Обработчик нажатия кнопки 'Редактировать'."""
        row = self.get_selected_row()
        if row == -1:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите категорию для редактирования.")
            return
        self.edit_category_requested.emit(row)

    def _on_delete_button_clicked(self):
        """Обработчик нажатия кнопки 'Удалить'."""
        row = self.get_selected_row()
        if row == -1:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите категорию для удаления.")
            return
        self.delete_category_requested.emit(row)
