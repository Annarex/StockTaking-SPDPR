# File: user_model.py
from PyQt5.QtSql import QSqlRelationalTableModel, QSqlDatabase,QSqlTableModel, QSqlQuery, QSqlError, QSqlRelation
from PyQt5.QtCore import Qt, QVariant

# Импортируем схему базы данных для получения названий таблиц и столбцов
from database import DATABASE_SCHEMA

class UserModel:
    def __init__(self, db_connection):
        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто.")
            # Возможно, стоит выбросить исключение или вернуть False
            return

        self.table_name = "Users"

        # Используем QSqlRelationalTableModel для отображения имени отдела
        self._model = QSqlRelationalTableModel(None, self.db) # Parent is None here, Controller will manage
        self._model.setTable(self.table_name)

        # Устанавливаем связь для столбца id_department
        # Получаем индекс столбца id_department по имени
        department_col_index = self._model.fieldIndex("id_department")
        if department_col_index != -1:
             self._model.setRelation(department_col_index, QSqlRelation("Departments", "id_department", "department_fullname"))
        else:
             print("Предупреждение: Столбец 'id_department' не найден в модели Users.")

        self._model.setEditStrategy(QSqlTableModel.OnManualSubmit) # Изменения сохраняем вручную через submitAll

        # Устанавливаем заголовки столбцов (можно оставить здесь или перенести в View, но Model знает о структуре)
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
        for i in range(self._model.columnCount()):
             col_name = self._model.record().fieldName(i)
             if col_name in header_map:
                self._model.setHeaderData(i, Qt.Horizontal, header_map[col_name])
             else:
                self._model.setHeaderData(i, Qt.Horizontal, col_name)

        self.load_data() # Загружаем данные при создании модели

    def get_model(self):
        """Возвращает QSqlRelationalTableModel для использования в View."""
        return self._model

    def load_data(self):
        """Загружает или обновляет данные из таблицы Users."""
        self._model.select()
        if self._model.lastError().type() != QSqlError.NoError:
             print("Ошибка загрузки данных пользователей:", self._model.lastError().text())
             return False
        print("Данные пользователей загружены.")
        return True

    def get_user_data(self, row):
        """Получает данные пользователя из указанной строки модели."""
        user_data = {}
        # Получаем названия столбцов из схемы БД для таблицы Users
        user_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

        for col_name in user_col_names_in_schema:
             col_index = self._model.fieldIndex(col_name)
             if col_index != -1:
                # Используем Qt.EditRole для получения сырых данных (например, ID отдела)
                user_data[col_name] = self._model.data(self._model.index(row, col_index), Qt.EditRole)

        # Ensure id_user is included, even if not in schema list (e.g., if it's PK and handled separately)
        id_col_index = self._model.fieldIndex("id_user")
        if id_col_index != -1:
             user_data['id_user'] = self._model.data(self._model.index(row, id_col_index), Qt.EditRole)


        return user_data

    def add_user(self, data):
        """Добавляет нового пользователя в базу данных."""
        row_count = self._model.rowCount()
        if not self._model.insertRow(row_count):
             print("Ошибка при вставке новой строки в модель:", self._model.lastError().text())
             return False, self._model.lastError().text()

        # Устанавливаем данные в модель
        user_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
        field_indices = {col: self._model.fieldIndex(col) for col in data if col in user_col_names_in_schema}

        for key, value in data.items():
            if key in field_indices and field_indices[key] != -1:
                 # QSqlTableModel/RelationalModel обычно преобразует типы
                 self._model.setData(self._model.index(row_count, field_indices[key]), value)

        # Сохраняем изменения
        if self._model.submitAll():
            print("Пользователь успешно добавлен (Model).")
            # self.load_data() # Обновляем модель, чтобы увидеть новую запись с ID - Controller might do this
            return True, "Пользователь успешно добавлен."
        else:
            error_text = self._model.lastError().text()
            print("Ошибка при добавлении пользователя (Model):", error_text)
            self._model.revertAll() # Отменяем изменения
            return False, f"Не удалось добавить пользователя: {error_text}"

    def update_user(self, row, data):
        """Обновляет данные существующего пользователя в базе данных."""
        # Устанавливаем данные в модель для указанной строки
        user_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
        field_indices = {col: self._model.fieldIndex(col) for col in data if col in user_col_names_in_schema}

        for key, value in data.items():
            if key in field_indices and field_indices[key] != -1:
                 self._model.setData(self._model.index(row, field_indices[key]), value)

        # Сохраняем изменения
        if self._model.submitAll():
            print(f"Пользователь в строке {row} успешно обновлен (Model).")
            # self.load_data() # Обновляем представление после редактирования - Controller might do this
            return True, "Изменения успешно сохранены."
        else:
            error_text = self._model.lastError().text()
            print("Ошибка при обновлении пользователя (Model):", error_text)
            self._model.revertAll() # Отменяем изменения
            return False, f"Не удалось сохранить изменения: {error_text}"

    def delete_user(self, row):
        """Удаляет пользователя из базы данных по номеру строки."""
        # Получаем ID и ФИО пользователя для сообщения (опционально, можно передать из View/Controller)
        id_col_index = self._model.fieldIndex("id_user")
        fio_col_index = self._model.fieldIndex("fio")
        user_id = self._model.data(self._model.index(row, id_col_index), Qt.DisplayRole) if id_col_index != -1 else "N/A"
        user_fio = self._model.data(self._model.index(row, fio_col_index), Qt.DisplayRole) if fio_col_index != -1 else "Выбранная запись"


        if self._model.removeRow(row):
            if self._model.submitAll(): # Сохраняем изменение в базу данных
                print(f"Пользователь '{user_fio}' (ID: {user_id}) успешно удален (Model).")
                # self.load_data() # Обновляем представление после удаления - Controller might do this
                return True, f"Пользователь '{user_fio}' (ID: {user_id}) успешно удален."
            else:
                error_text = self._model.lastError().text()
                print("Ошибка при сохранении удаления (Model):", error_text)
                self._model.revertAll() # Отменяем удаление
                return False, f"Не удалось удалить пользователя: {error_text}"
        else:
            print("Ошибка при удалении строки из модели (Model).")
            return False, "Не удалось удалить строку из модели."

    def get_departments(self):
        """Получает список отделов из базы данных."""
        departments = []
        query = QSqlQuery("SELECT id_department, department_fullname FROM Departments ORDER BY department_fullname", self.db)
        while query.next():
            item_id = query.value(0)
            item_name = query.value(1)
            departments.append((item_id, item_name))
        return departments