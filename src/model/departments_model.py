# File: departments_model.py
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError
from PyQt5.QtCore import Qt, QVariant

# Импортируем схему базы данных для получения названий таблиц и столбцов
from database import DATABASE_SCHEMA

class DepartmentsModel:
    def __init__(self, db_connection):
        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто. Модель отделов не может быть инициализирована.")
            # В реальном приложении здесь может быть выброшено исключение
            self.model = None
            return

        self.table_name = "Departments"
        # Получаем названия столбцов из схемы БД, исключая определения внешних ключей
        self.column_names = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
        self.unique_column = "department_fullname"

        self._model = QSqlTableModel(None, self.db)
        self._model.setTable(self.table_name)
        self._model.setEditStrategy(QSqlTableModel.OnManualSubmit)

        header_map = {
            "id_department": "ID",
            "department_fullname": "Полное название",
            "department_shortname": "Краткое название",
        }
        for i in range(self._model.columnCount()):
             col_name = self._model.record().fieldName(i)
             if col_name in header_map:
                self._model.setHeaderData(i, Qt.Horizontal, header_map[col_name])
             else:
                self._model.setHeaderData(i, Qt.Horizontal, col_name)

        self.load_data() # Загружаем данные при создании модели

    def get_model(self):
        """
        Возвращает экземпляр QSqlTableModel для использования в View.
        """
        return self._model

    def load_data(self):
        """
        Загружает или обновляет данные из таблицы Departments.
        Возвращает True в случае успеха, False в случае ошибки.
        """
        self._model.select()
        if self._model.lastError().type() != QSqlError.NoError:
             print("Ошибка загрузки данных отделов:", self._model.lastError().text())
             return False
        print("Данные отделов загружены.")
        return True

    def get_department_data(self, row):
        """
        Получает данные отдела из указанной строки модели.
        Возвращает словарь с данными отдела.
        """
        department_data = {}
        # Получаем названия столбцов из схемы БД для таблицы Departments
        department_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

        for col_name in department_col_names_in_schema:
             col_index = self._model.fieldIndex(col_name)
             if col_index != -1:
                # Используем Qt.EditRole для получения сырых данных
                department_data[col_name] = self._model.data(self._model.index(row, col_index), Qt.EditRole)

        return department_data

    def add_department(self, data):
        """
        Добавляет новый отдел в базу данных.
        Принимает словарь с данными отдела.
        Возвращает кортеж (success, message).
        """
        fullname = data.get('department_fullname', '').strip()
        shortname = data.get('department_shortname', '').strip()

        # --- Валидация данных (часть валидации может быть в View/Controller, но проверка уникальности здесь) ---
        if not fullname:
             return False, "Пожалуйста, введите полное название отдела."
        if len(fullname) > 50:
             return False, "Полное название отдела не может превышать 50 символов."
        if len(shortname) > 50:
             return False, "Краткое название отдела не может превышать 50 символов."


        # Проверяем на уникальность полного названия перед добавлением
        query = QSqlQuery(self.db)
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE department_fullname = ?")
        query.addBindValue(fullname)
        if query.exec_() and query.next():
            count = query.value(0)
            if count > 0:
                return False, f"Отдел с полным названием '{fullname}' уже существует."


        # Добавляем новую пустую строку в модель
        row_count = self._model.rowCount()
        if not self._model.insertRow(row_count):
             error_text = self._model.lastError().text()
             print("Ошибка при вставке новой строки в модель:", error_text)
             return False, error_text

        # Устанавливаем данные в модель для новой строки по именам столбцов
        col_indices = {col: self._model.fieldIndex(col) for col in self.column_names}

        # ID отдела автоинкрементный, его не устанавливаем при добавлении
        if "department_fullname" in col_indices and col_indices["department_fullname"] != -1:
             self._model.setData(self._model.index(row_count, col_indices["department_fullname"]), fullname)
        if "department_shortname" in col_indices and col_indices["department_shortname"] != -1:
             self._model.setData(self._model.index(row_count, col_indices["department_shortname"]), shortname)


        if self._model.submitAll(): # Сохраняем изменения в базу данных
            print(f"Отдел '{fullname}' успешно добавлен (Model).")
            # Модель автоматически обновится после submitAll, если стратегия OnManualSubmit
            return True, "Отдел успешно добавлен."
        else:
            error_text = self._model.lastError().text()
            print("Ошибка при добавлении отдела (Model):", error_text)
            self._model.revertAll() # Отменяем изменения в модели, если сохранение не удалось
            return False, f"Не удалось добавить отдел: {error_text}"

    def update_department(self, row, data):
        """
        Обновляет данные существующего отдела в базе данных.
        Принимает номер строки и словарь с новыми данными.
        Возвращает кортеж (success, message).
        """
        fullname = data.get('department_fullname', '').strip()
        shortname = data.get('department_shortname', '').strip()
        department_id = data.get('id_department') # Получаем ID для проверки уникальности полного имени

        # --- Валидация данных (часть валидации может быть в View/Controller) ---
        if not fullname:
             return False, "Пожалуйста, введите полное название отдела."
        if len(fullname) > 50:
             return False, "Полное название отдела не может превышать 50 символов."
        if len(shortname) > 50:
             return False, "Краткое название отдела не может превышать 50 символов."


        # Проверяем на уникальность полного названия, исключая текущую редактируемую запись
        query = QSqlQuery(self.db)
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE department_fullname = ? AND id_department != ?")
        query.addBindValue(fullname)
        query.addBindValue(department_id) # Исключаем текущий отдел по его ID
        if query.exec_() and query.next() and query.value(0) > 0:
             return False, f"Отдел с полным названием '{fullname}' уже существует."


        # Устанавливаем данные в модель для указанной строки
        col_indices = {col: self._model.fieldIndex(col) for col in data if col in self.column_names}

        # ID отдела не меняется при редактировании
        if "department_fullname" in col_indices and col_indices["department_fullname"] != -1:
             self._model.setData(self._model.index(row, col_indices["department_fullname"]), fullname)
        if "department_shortname" in col_indices and col_indices["department_shortname"] != -1:
             self._model.setData(self._model.index(row, col_indices["department_shortname"]), shortname)


        if self._model.submitAll():
            print(f"Отдел в строке {row} успешно обновлен (Model).")
            return True, "Изменения успешно сохранены."
        else:
            error_text = self._model.lastError().text()
            print("Ошибка при обновлении отдела (Model):", error_text)
            self._model.revertAll()
            return False, f"Не удалось сохранить изменения: {error_text}"

    def delete_department(self, row):
        id_col_index = self._model.fieldIndex("id_department")
        name_col_index = self._model.fieldIndex("department_fullname")
        item_id = self._model.data(self._model.index(row, id_col_index), Qt.DisplayRole) if id_col_index != -1 else "N/A"
        item_name = self._model.data(self._model.index(row, name_col_index), Qt.DisplayRole) if name_col_index != -1 else "Выбранная запись"

        if self._model.removeRow(row):
            if self._model.submitAll():
                print(f"Отдел '{item_name}' (ID: {item_id}) успешно удален (Model).")
                return True, f"Отдел '{item_name}' (ID: {item_id}) успешно удален."
            else:
                error_text = self._model.lastError().text()
                print("Ошибка при сохранении удаления (Model):", error_text)
                self._model.revertAll()
                return False, f"Не удалось удалить отдел: {error_text}"
        else:
            print("Ошибка при удалении строки из модели (Model).")
            return False, "Не удалось удалить строку из модели."