# File: ui/departments_view.py
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLabel, QMessageBox, QLineEdit,
                             QInputDialog, QFormLayout, QFileDialog,
                             QDialog, QDialogButtonBox) # Импортируем QDialog и QDialogButtonBox
from PyQt5.QtCore import Qt, QModelIndex, QDate, QVariant, pyqtSignal # Импортируем pyqtSignal


class DepartmentDialog(QDialog):
    def __init__(self, department_data=None, parent=None):
        super().__init__(parent)
        self.department_data = department_data # Данные для редактирования

        self.setWindowTitle("Добавить/Редактировать отдел")
        self.layout = QFormLayout(self)

        # ID отдела автоинкрементный, не вводим при добавлении, отображаем при редактировании
        self.id_department_input = QLineEdit()
        self.id_department_input.setReadOnly(True) # ID не редактируется

        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("Введите полное название отдела")
        self.fullname_input.setMaxLength(50) # Ограничение по длине

        self.shortname_input = QLineEdit()
        self.shortname_input.setPlaceholderText("Введите краткое название отдела")
        self.shortname_input.setMaxLength(50) # Ограничение по длине

        # Если редактируем, заполняем поля текущими данными
        if self.department_data:
            self.id_department_input.setText(str(self.department_data.get('id_department', '')))
            self.fullname_input.setText(str(self.department_data.get('department_fullname', '')))
            self.shortname_input.setText(str(self.department_data.get('department_shortname', '')))


        self.layout.addRow("ID Отдела:", self.id_department_input)
        self.layout.addRow("Полное название:", self.fullname_input)
        self.layout.addRow("Краткое название:", self.shortname_input)

        # Кнопки OK и Cancel
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_data(self):
        data = {
            'id_department': self.id_department_input.text().strip() if self.department_data else None,
            'department_fullname': self.fullname_input.text().strip(),
            'department_shortname': self.shortname_input.text().strip(),
        }
        return data

    def validate_data(self):
        data = self.get_data()
        if not data['department_fullname']:
             QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите полное название отдела.")
             return False
        if len(data['department_fullname']) > 50:
             QMessageBox.warning(self, "Предупреждение", "Полное название отдела не может превышать 50 символов.")
             return False
        if len(data['department_shortname']) > 50:
             QMessageBox.warning(self, "Предупреждение", "Краткое название отдела не может превышать 50 символов.")
             return False

        return True


class DepartmentsView(QWidget):
    add_department_requested = pyqtSignal()
    edit_department_requested = pyqtSignal(int) 
    delete_department_requested = pyqtSignal(int)
    refresh_list_requested = pyqtSignal()
    import_csv_requested = pyqtSignal()
    export_csv_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Управление отделами")
        self.layout = QVBoxLayout(self)
        info_label = QLabel("Управление отделами.")
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
        add_button = QPushButton("Добавить отдел")
        edit_button = QPushButton("Редактировать выбранный")
        delete_button = QPushButton("Удалить выбранный")
        import_button = QPushButton("Импорт из CSV...")
        export_button = QPushButton("Экспорт в CSV...")
        refresh_button = QPushButton("Обновить список")

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(import_button)
        buttons_layout.addWidget(export_button)
        buttons_layout.addWidget(refresh_button)
        buttons_layout.addStretch()

        self.layout.addLayout(buttons_layout)

        add_button.clicked.connect(self.add_department_requested.emit)
        edit_button.clicked.connect(self._on_edit_button_clicked)
        delete_button.clicked.connect(self._on_delete_button_clicked)
        import_button.clicked.connect(self.import_csv_requested.emit)
        export_button.clicked.connect(self.export_csv_requested.emit)
        refresh_button.clicked.connect(self.refresh_list_requested.emit)

    def set_model(self, model):
        self.table_view.setModel(model)

    def get_selected_row(self):
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            return -1
        return selected_indexes[0].row()

    def _on_double_click(self, index):
        row = index.row()
        self.edit_department_requested.emit(row)

    def _on_edit_button_clicked(self):
        row = self.get_selected_row()
        if row == -1:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите отдел для редактирования.")
            return
        self.edit_department_requested.emit(row)

    def _on_delete_button_clicked(self):
        row = self.get_selected_row()
        if row == -1:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите отдел для удаления.")
            return
        self.delete_department_requested.emit(row)