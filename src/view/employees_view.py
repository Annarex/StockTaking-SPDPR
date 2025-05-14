# File: ui/users_view.py
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLabel, QMessageBox, QLineEdit,
                             QInputDialog, QFormLayout, QComboBox, QFileDialog,
                             QTextEdit, QDialog, QDialogButtonBox)
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError, QSqlRelation, QSqlRelationalTableModel
from PyQt5.QtCore import Qt, QModelIndex, QDate, QVariant, pyqtSignal # Import pyqtSignal

# Импортируем универсальный обработчик CSV (Controller will use this)
# from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

# Импортируем схему базы данных для получения названий таблиц и столбцов (Model will use this)
# from database import DATABASE_SCHEMA

# --- Диалог для добавления/редактирования пользователя ---
# Этот диалог остается частью View, но логика сохранения переносится в Controller
class UserDialog(QDialog):
    def __init__(self, db_connection, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db_connection # Still need db connection to populate department combo
        self.user_data = user_data # None для добавления, dict для редактирования

        self.setWindowTitle("Добавить/Редактировать пользователя")
        self.layout = QFormLayout(self)

        # Поля из Users
        # id_user автоинкрементный, не вводим при добавлении, отображаем при редактировании
        self.id_user_input = QLineEdit()
        self.id_user_input.setReadOnly(True) # ID не редактируется
        self.fio_input = QLineEdit()
        self.fio_input.setMaxLength(60)
        self.cabinet_input = QLineEdit()
        self.cabinet_input.setMaxLength(6)
        self.department_combo = QComboBox() # Для id_department (FK)
        self.post_input = QLineEdit()
        self.post_input.setMaxLength(50)
        self.account_input = QLineEdit()
        self.account_input.setMaxLength(50)
        self.ids_group_dc_input = QLineEdit() # VARCHAR по схеме
        self.ids_group_dc_input.setMaxLength(50)
        self.work_pc_input = QLineEdit()
        self.work_pc_input.setMaxLength(40)
        self.work_pc_ip_input = QLineEdit()
        self.work_pc_ip_input.setMaxLength(45)
        self.telephone_input = QLineEdit()
        self.telephone_input.setMaxLength(20)
        self.mail_input = QLineEdit()
        self.mail_input.setMaxLength(50)

        # Добавляем поля в форму
        self.layout.addRow("ID пользователя:", self.id_user_input)
        self.layout.addRow("ФИО:", self.fio_input)
        self.layout.addRow("Кабинет:", self.cabinet_input)
        self.layout.addRow("Отдел:", self.department_combo)
        self.layout.addRow("Должность:", self.post_input)
        self.layout.addRow("Учетная запись:", self.account_input)
        self.layout.addRow("Группы домена:", self.ids_group_dc_input)
        self.layout.addRow("Рабочий ПК:", self.work_pc_input)
        self.layout.addRow("IP рабочего ПК:", self.work_pc_ip_input)
        self.layout.addRow("Телефон:", self.telephone_input)
        self.layout.addRow("Почта:", self.mail_input)

        # Заполняем комбобокс отделов
        self._populate_departments_combo()

        # Если редактируем, заполняем поля текущими данными
        if self.user_data:
            self.id_user_input.setText(str(self.user_data.get('id_user', '')))
            self.fio_input.setText(str(self.user_data.get('fio', '')))
            self.cabinet_input.setText(str(self.user_data.get('cabinet', '')))
            # Выбираем отдел по ID
            self._select_combo_item(self.department_combo, self.user_data.get('id_department'))
            self.post_input.setText(str(self.user_data.get('post', '')))
            self.account_input.setText(str(self.user_data.get('account', '')))
            self.ids_group_dc_input.setText(str(self.user_data.get('ids_group_dc', '')))
            self.work_pc_input.setText(str(self.user_data.get('work_pc', '')))
            self.work_pc_ip_input.setText(str(self.user_data.get('work_pc_ip', '')))
            self.telephone_input.setText(str(self.user_data.get('telephone', '')))
            self.mail_input.setText(str(self.user_data.get('mail', '')))


        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def _populate_departments_combo(self):
        """Заполняет QComboBox отделами из базы данных."""
        # This still requires DB access, which is acceptable for a View component
        # needing lookup data for its UI elements.
        self.department_combo.clear()
        self.department_combo.addItem("Выберите отдел", None) # Опция "Выберите"
        query = QSqlQuery("SELECT id_department, department_fullname FROM Departments ORDER BY department_fullname", self.db)
        while query.next():
            item_id = query.value(0)
            item_name = query.value(1)
            self.department_combo.addItem(item_name, item_id) # Сохраняем ID как UserData

    def _select_combo_item(self, combo_box, item_id):
        """Выбирает элемент в комбобоксе по его UserData (ID)."""
        if item_id is None:
            combo_box.setCurrentIndex(0) # Выбираем "Выберите..." или "Все..."
            return
        for i in range(combo_box.count()):
            if combo_box.itemData(i) == item_id:
                combo_box.setCurrentIndex(i)
                return
        # Если ID не найден, оставляем выбранным первый элемент (None)
        combo_box.setCurrentIndex(0)


    def get_data(self):
        """Возвращает данные из полей диалога в виде словаря."""
        data = {
            # 'id_user': self.id_user_input.text().strip(), # ID handled by Model/Controller
            'fio': self.fio_input.text().strip(),
            'cabinet': self.cabinet_input.text().strip(),
            'id_department': self.department_combo.currentData(),
            'post': self.post_input.text().strip(),
            'account': self.account_input.text().strip(),
            'ids_group_dc': self.ids_group_dc_input.text().strip(),
            'work_pc': self.work_pc_input.text().strip(),
            'work_pc_ip': self.work_pc_ip_input.strip(), # Keep IP format as entered
            'telephone': self.telephone_input.text().strip(),
            'mail': self.mail_input.text().strip(),
        }

        # If editing, include the original ID
        if self.user_data and 'id_user' in self.user_data:
             data['id_user'] = self.user_data['id_user']

        return data


    def validate_data(self):
        """Проверяет введенные данные (базовая валидация UI)."""
        data = self.get_data()
        if not data['fio']:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите ФИО пользователя.")
            return False
        if data['id_department'] is None:
             QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите отдел.")
             return False
        # Add other UI-level validations if needed
        return True


class UsersView(QWidget):
    # Define signals that the Controller will connect to
    add_user_requested = pyqtSignal()
    edit_user_requested = pyqtSignal(int) # Emits row index
    delete_user_requested = pyqtSignal(int) # Emits row index
    refresh_list_requested = pyqtSignal()
    import_csv_requested = pyqtSignal()
    export_csv_requested = pyqtSignal() # Add export signal

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Список пользователей")

        self.layout = QVBoxLayout(self)

        info_label = QLabel("Список пользователей. Редактирование через двойной клик или кнопку 'Редактировать'.")
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


        # --- Кнопки для добавления, редактирования и удаления ---
        buttons_layout = QHBoxLayout()
        import_button = QPushButton("Импорт из CSV")
        export_button = QPushButton("Экспорт в CSV") # Add export button
        add_button = QPushButton("Добавить пользователя")
        edit_button = QPushButton("Редактировать выбранного")
        delete_button = QPushButton("Удалить выбранного")
        refresh_button = QPushButton("Обновить список")

        buttons_layout.addWidget(import_button)
        buttons_layout.addWidget(export_button) # Add export button
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(refresh_button)
        buttons_layout.addStretch()

        self.layout.addLayout(buttons_layout)

        # Подключаем сигналы к кнопкам (эти сигналы будут пойманы Controller'ом)
        import_button.clicked.connect(self.import_csv_requested.emit)
        export_button.clicked.connect(self.export_csv_requested.emit) # Connect export signal
        add_button.clicked.connect(self.add_user_requested.emit)
        edit_button.clicked.connect(self._on_edit_button_clicked) # Use a helper to check selection
        delete_button.clicked.connect(self._on_delete_button_clicked) # Use a helper to check selection
        refresh_button.clicked.connect(self.refresh_list_requested.emit)

        # No direct model interaction here anymore
        # self.model.dataChanged.connect(self._handle_data_changed) # Controller handles errors

    def set_model(self, model):
        """Устанавливает модель данных для таблицы."""
        self.table_view.setModel(model)

    def get_selected_row(self):
        """Возвращает индекс выбранной строки или -1, если ничего не выбрано."""
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            return -1
        return selected_indexes[0].row()

    def _on_double_click(self, index):
        """Обработчик двойного клика по строке."""
        row = index.row()
        self.edit_user_requested.emit(row)

    def _on_edit_button_clicked(self):
        """Обработчик нажатия кнопки 'Редактировать'."""
        row = self.get_selected_row()
        if row == -1:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите пользователя для редактирования.")
            return
        self.edit_user_requested.emit(row)

    def _on_delete_button_clicked(self):
        """Обработчик нажатия кнопки 'Удалить'."""
        row = self.get_selected_row()
        if row == -1:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите пользователя для удаления.")
            return
        self.delete_user_requested.emit(row)

    # Error handling and messages are now handled by the Controller
    # def _handle_data_changed(self, topLeft, bottomRight, roles): ...

