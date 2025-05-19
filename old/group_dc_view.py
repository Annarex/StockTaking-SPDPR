# File: ui/group_dc_view.py
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLabel, QMessageBox, QLineEdit,
                             QInputDialog, QFormLayout, QFileDialog)
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError
from PyQt5.QtCore import Qt, QModelIndex, QDate, QVariant, pyqtSignal # Импортируем pyqtSignal

class GroupDCView(QWidget):
    add_item_requested = pyqtSignal()
    delete_item_requested = pyqtSignal(int)
    refresh_list_requested = pyqtSignal()
    import_csv_requested = pyqtSignal()
    export_csv_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление группами домена")
        self.layout = QVBoxLayout(self)
        info_label = QLabel("Управление группами домена. Редактирование возможно прямо в таблице.")
        self.layout.addWidget(info_label)

        # --- Настройки таблицы ---
        self.table_view = QTableView()
        # Модель данных будет установлена Контроллером
        self.table_view.horizontalHeader().setStretchLastSection(True) # Растягиваем последний столбец
        self.table_view.setSelectionBehavior(QTableView.SelectRows) # Выделяем целые строки
        self.table_view.setSelectionMode(QTableView.SingleSelection) # Разрешаем выделять только одну строку
        # Оставляем редактирование прямо в таблице, так как нет отдельного диалога
        self.table_view.setEditTriggers(QTableView.DoubleClicked | QTableView.SelectedClicked | QTableView.AnyKeyPressed)
        self.layout.addWidget(self.table_view)

        # --- Поле ввода и кнопка для добавления ---
        add_layout = QHBoxLayout()

        self.id_group_dc_input = QLineEdit()
        self.id_group_dc_input.setPlaceholderText("Введите 2 символа ID")
        self.id_group_dc_input.setMaxLength(2) 

        self.group_dc_input = QLineEdit()
        self.group_dc_input.setPlaceholderText("Введите новую группу домена")
        self.group_dc_input.setMaxLength(20)
        add_layout.addWidget(self.id_group_dc_input)
        add_layout.addWidget(self.group_dc_input)

        add_button = QPushButton("Добавить группу")
        # Подключаем кнопку добавления к сигналу View
        add_button.clicked.connect(self.add_item_requested.emit)
        add_layout.addWidget(add_button)

        self.layout.addLayout(add_layout)

        # --- Кнопки управления (Удалить, Импорт, Экспорт, Обновить) ---
        buttons_layout = QHBoxLayout()
        delete_button = QPushButton("Удалить выбранную")
        import_button = QPushButton("Импорт из CSV...")
        export_button = QPushButton("Экспорт в CSV...")
        refresh_button = QPushButton("Обновить список")
        
        delete_button.clicked.connect(self._on_delete_button_clicked) # Используем вспомогательный метод для проверки выделения
        import_button.clicked.connect(self.import_csv_requested.emit)
        export_button.clicked.connect(self.export_csv_requested.emit)
        refresh_button.clicked.connect(self.refresh_list_requested.emit)

        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(import_button)
        buttons_layout.addWidget(export_button)
        buttons_layout.addWidget(refresh_button)
        buttons_layout.addStretch() 

        self.layout.addLayout(buttons_layout)

    def set_model(self, model):
        self.table_view.setModel(model)
    
    def get_data_input(self):
        data = {
            'id_group_dc': self.id_group_dc_input.text().strip(),
            'group_dc': self.group_dc_input.text()
            }
        return data
    
    def validate_data(self):
        data = self.get_data_input()
        if not data['id_group_dc']:
             QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите ID группы.")
             return False
        if len(data['id_group_dc']) != 2:
             QMessageBox.warning(self, "Предупреждение", "ID группы должен состоять ровно из 2 символов.")
             return False
        if not data['group_dc']:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите название группы.")
            return False
        if len(data['group_dc']) > 20:
             QMessageBox.warning(self, "Предупреждение", "Название группы не может превышать 20 символов.")
             return False

        return True

    def clear_add_input(self):
        self.id_group_dc_input.clear()
        self.group_dc_input.clear()

    def get_selected_row(self):
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            return -1
        return selected_indexes[0].row()

    def _on_delete_button_clicked(self):
        row = self.get_selected_row()
        if row == -1:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите группу домена для удаления.")
            return
        self.delete_item_requested.emit(row)