# ui/users_view.py
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLabel, QMessageBox, QLineEdit,
                             QInputDialog, QFormLayout, QComboBox, QFileDialog,
                             QTextEdit, QDialog, QDialogButtonBox) # Добавляем QTextEdit
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError, QSqlRelation, QSqlRelationalTableModel # Используем QSqlRelationalTableModel
from PyQt5.QtCore import Qt, QModelIndex, QDate, QVariant

# Импортируем универсальный обработчик CSV
from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

# Импортируем схему базы данных для получения названий таблиц и столбцов
from database import DATABASE_SCHEMA

# --- Диалог для добавления/редактирования пользователя ---
# Создадим отдельный диалог, так как полей много
class UserDialog(QDialog):
    def __init__(self, db_connection, user_data=None, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.user_data = user_data # None для добавления, dict для редактирования

        self.setWindowTitle("Добавить/Редактировать пользователя")
        self.layout = QFormLayout(self)

        # Поля из Users
        # id_user автоинкрементный, не вводим
        self.id_user_input = QLineEdit()
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
            'id_user': self.id_user_input.text().strip(),
            'fio': self.fio_input.text().strip(),
            'cabinet': self.cabinet_input.text().strip(),
            'id_department': self.department_combo.currentData(),
            'post': self.post_input.text().strip(),
            'account': self.account_input.text().strip(),
            'ids_group_dc': self.ids_group_dc_input.text().strip(),
            'work_pc': self.work_pc_input.text().strip(),
            'work_pc_ip': self.work_pc_ip_input.text().strip(),
            'telephone': self.telephone_input.text().strip(),
            'mail': self.mail_input.text().strip(),
        }

        # Если редактируем, добавляем ID пользователя
        if self.user_data and 'id_user' in self.user_data:
             data['id_user'] = self.user_data['id_user']

        return data


    def validate_data(self):
        """Проверяет введенные данные."""
        data = self.get_data()
        if not data['fio']:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите ФИО пользователя.")
            return False
        if data['id_department'] is None:
             QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите отдел.")
             return False
        return True


class UsersView(QWidget):
    def __init__(self, db_connection):
        super().__init__()

        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто.")
            return

        self.setWindowTitle("Список пользователей")

        self.layout = QVBoxLayout(self)

        info_label = QLabel("Список пользователей. Редактирование через двойной клик или кнопку 'Редактировать'.")
        self.layout.addWidget(info_label)

        # --- Настройки модели и таблицы ---
        self.table_name = "Users" # Название таблицы

        # Используем QSqlRelationalTableModel для отображения имени отдела
        self.model = QSqlRelationalTableModel(self, self.db)
        self.model.setTable(self.table_name)

        # Устанавливаем связь для столбца id_department
        # Получаем индекс столбца id_department по имени
        department_col_index = self.model.fieldIndex("id_department")
        if department_col_index != -1:
             self.model.setRelation(department_col_index, QSqlRelation("Departments", "id_department", "department_fullname"))
        else:
             print("Предупреждение: Столбец 'id_department' не найден в модели Users.")


        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit) # Изменения сохраняем вручную через диалог
        self.model.select() # Загрузить данные из таблицы

        # Устанавливаем заголовки столбцов
        # Используем fieldName(i) для получения имени столбца в модели
        header_map = {
            "id_user": "ID",
            "fio": "ФИО",
            "cabinet": "Кабинет",
            "id_department": "Отдел", # Будет отображаться имя отдела
            "post": "Должность",
            "account": "Учетная запись",
            "ids_group_dc": "Группы домена",
            "work_pc": "Рабочий ПК",
            "work_pc_ip": "IP рабочего ПК",
            "telephone": "Телефон",
            "mail": "Почта",
        }
        for i in range(self.model.columnCount()):
             col_name = self.model.record().fieldName(i)
             if col_name in header_map:
                self.model.setHeaderData(i, Qt.Horizontal, header_map[col_name])
             else:
                self.model.setHeaderData(i, Qt.Horizontal, col_name)


        self.table_view = QTableView()
        self.table_view.setModel(self.model)     
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setEditTriggers(QTableView.NoEditTriggers)
        self.layout.addWidget(self.table_view)

        # --- Кнопки для добавления, редактирования и удаления ---
        buttons_layout = QHBoxLayout()
        import_button = QPushButton("Импорт из CSV")
        add_button = QPushButton("Добавить пользователя")
        edit_button = QPushButton("Редактировать выбранного")
        delete_button = QPushButton("Удалить выбранного")
        refresh_button = QPushButton("Обновить список") # Добавим кнопку обновления

        buttons_layout.addWidget(import_button)
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(refresh_button)
        buttons_layout.addStretch()

        self.layout.addLayout(buttons_layout)

        # Подключаем методы к кнопкам
        import_button.clicked.connect(self._import_from_csv)
        add_button.clicked.connect(self._add_item)
        edit_button.clicked.connect(self._edit_item)
        delete_button.clicked.connect(self._delete_item)
        refresh_button.clicked.connect(self._refresh_list)

        # Подключаем сигнал model.dataChanged для обработки ошибок сохранения (при OnManualSubmit не так критично, но полезно)
        self.model.dataChanged.connect(self._handle_data_changed)
        # primeInsert не нужен, т.к. добавление через диалог
        # self.model.primeInsert.connect(self._init_new_row)


    def _refresh_list(self):
        """Обновляет данные в таблице."""
        self.model.select() # Перезагружаем данные из базы
        print("Список пользователей обновлен.")


    def _add_item(self):
        """Открывает диалог для добавления нового пользователя."""
        dialog = UserDialog(self.db, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.validate_data():
                data = dialog.get_data()

                # Добавляем новую запись в Users через модель
                row_count = self.model.rowCount()
                self.model.insertRow(row_count)

                # Устанавливаем данные в модель Users
                # Используем fieldIndex для надежности
                field_indices = {col: self.model.fieldIndex(col) for col in data if col in [c.split()[0] for c in DATABASE_SCHEMA.get(self.table_name, [])]}

                for key, value in data.items():
                    if key in field_indices and field_indices[key] != -1:
                         # QSqlTableModel/RelationalModel обычно преобразует типы
                         self.model.setData(self.model.index(row_count, field_indices[key]), value)


                # Сохраняем изменения в Users
                if self.model.submitAll():
                    print("Пользователь успешно добавлен.")
                    self.model.select() # Обновляем модель, чтобы увидеть новую запись с ID
                else:
                    print("Ошибка при добавлении пользователя:", self.model.lastError().text())
                    QMessageBox.critical(self, "Ошибка", f"Не удалось добавить пользователя: {self.model.lastError().text()}")
                    self.model.revertAll() # Отменяем изменения


    def _edit_item(self):
        """Открывает диалог для редактирования выбранного пользователя."""
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите пользователя для редактирования.")
            return

        selected_index = selected_indexes[0]
        row = selected_index.row()

        # Получаем ID пользователя
        id_col_index = self.model.fieldIndex("id_user")
        user_id = self.model.data(self.model.index(row, id_col_index), Qt.EditRole)
        if user_id is None:
             QMessageBox.warning(self, "Ошибка", "Не удалось получить ID выбранного пользователя.")
             return

        # Получаем текущие данные из Users через модель
        user_data = {}
        # Получаем названия столбцов из схемы БД для таблицы Users
        user_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

        for col_name in user_col_names_in_schema:
             col_index = self.model.fieldIndex(col_name)
             if col_index != -1:
                # Используем Qt.EditRole для получения сырых данных (например, ID отдела)
                user_data[col_name] = self.model.data(self.model.index(row, col_index), Qt.EditRole)

        # Добавляем ID пользователя в данные для диалога
        user_data['id_user'] = user_id


        dialog = UserDialog(self.db, user_data=user_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
             if dialog.validate_data():
                new_data = dialog.get_data()

                # Обновляем данные в модели Users
                field_indices = {col: self.model.fieldIndex(col) for col in new_data if col in user_col_names_in_schema}
                for key, value in new_data.items():
                    if key in field_indices and field_indices[key] != -1:
                         self.model.setData(self.model.index(row, field_indices[key]), value)

                # Сохраняем изменения в Users
                if self.model.submitAll():
                    print(f"Пользователь с ID {user_id} успешно отредактирован.")
                    self.model.select() # Обновляем представление после редактирования
                else:
                    print("Ошибка при сохранении изменений:", self.model.lastError().text())
                    QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить изменения: {self.model.lastError().text()}")
                    self.model.revertAll() # Отменяем изменения


    def _delete_item(self):
        """Удаляет выбранного пользователя."""
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите пользователя для удаления.")
            return

        selected_index = selected_indexes[0]
        row = selected_index.row()

        # Получаем ID и ФИО пользователя для подтверждения
        id_col_index = self.model.fieldIndex("id_user")
        fio_col_index = self.model.fieldIndex("fio")
        user_id = self.model.data(self.model.index(row, id_col_index), Qt.DisplayRole) if id_col_index != -1 else "N/A"
        user_fio = self.model.data(self.model.index(row, fio_col_index), Qt.DisplayRole) if fio_col_index != -1 else "Выбранная запись"


        reply = QMessageBox.question(self, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить пользователя '{user_fio}' (ID: {user_id})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # Удаляем строку из модели
            if self.model.removeRow(row):
                if self.model.submitAll(): # Сохраняем изменение в базу данных
                    print(f"Пользователь '{user_fio}' (ID: {user_id}) успешно удален.")
                    self.model.select() # Обновляем представление после удаления
                else:
                    print("Ошибка при сохранении удаления:", self.model.lastError().text())
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить пользователя: {self.model.lastError().text()}")
                    self.model.revertAll() # Отменяем удаление
            else:
                print("Ошибка при удалении строки из модели.")
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить строку из модели.")

    def _import_from_csv(self):
        """Открывает диалог выбора файла и запускает импорт пользователей."""
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self, "Предупреждение", "Невозможно выполнить импорт: соединение с базой данных отсутствует.")
             return

        file_path, _ = QFileDialog.getOpenFileName(self, f"Импорт данных в таблицу '{self.table_name}'",
                                                   "",
                                                   "CSV файлы (*.csv);;Все файлы (*)")

        if file_path:
            print(f"Выбран файл для импорта в {self.table_name}: {file_path}")
            all_user_cols = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

            success, message = import_data_from_csv(self.db, file_path, self.table_name, all_user_cols,column_digits={'id_department': 2})

            if success:
                QMessageBox.information(self, "Импорт завершен", message)
                self.model.select() # Обновляем представление после импорта
            else:
                QMessageBox.critical(self, "Ошибка импорта", message)
        else:
            print("Выбор файла отменен.")

    def _export_to_csv(self):
        """Открывает диалог сохранения файла и запускает экспорт пользователей."""
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self, "Предупреждение", "Невозможно выполнить экспорт: соединение с базой данных отсутствует.")
             return

        default_filename = f"{self.table_name}_export_{QDate.currentDate().toString('yyyyMMdd')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, f"Экспорт данных из таблицы '{self.table_name}'", default_filename, "CSV файлы (*.csv);;Все файлы (*)")
        if file_path:
            print(f"Выбран файл для экспорта из {self.table_name}: {file_path}")
            user_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
            cols_to_export = user_col_names_in_schema
            success, message = export_data_to_csv(self.db, file_path, self.table_name, cols_to_export)

            if success:
                QMessageBox.information(self, "Экспорт завершен", message)
                print(f"Экспорт сохранен: {file_path}")
            else:
                QMessageBox.critical(self, "Ошибка экспорта", message)
        else:
            print("Сохранение отчета отменено.")


    def _handle_data_changed(self, topLeft, bottomRight, roles):
        """Обрабатывает сигнал dataChanged для проверки ошибок сохранения после редактирования ячейки."""
        # Этот метод вызывается после успешного изменения данных в модели.
        # При OnManualSubmit он вызывается после submitAll().
        if self.model.lastError().type() != QSqlError.NoError:
            error_message = self.model.lastError().text()
            print(f"Ошибка при сохранении изменения: {error_message}")
            QMessageBox.critical(self, "Ошибка сохранения", f"Не удалось сохранить изменение: {error_message}")
            self.model.select() # Перезагружаем данные, чтобы откатить некорректное изменение в представлении
