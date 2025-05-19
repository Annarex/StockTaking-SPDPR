# File: category_model.py
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError
from PyQt5.QtCore import Qt, QVariant

# Импортируем схему базы данных для получения названий таблиц и столбцов
from database import DATABASE_SCHEMA

class CategoryModel:
    def __init__(self, db_connection):
        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто. Модель категорий не может быть инициализирована.")
            # Возможно, стоит выбросить исключение или вернуть False
            return

        self.table_name = "Category"
        self.column_names = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
        self.unique_column = "id_category"

        self._model = QSqlTableModel(None, self.db) # Parent is None here, Controller will manage
        self._model.setTable(self.table_name)
        self._model.setEditStrategy(QSqlTableModel.OnManualSubmit) # Изменения сохраняем вручную через submitAll

        # Устанавливаем заголовки столбцов (можно оставить здесь или перенести в View)
        header_map = {
            "id_category": "ID Категории",
            "category": "Название категории",
        }
        for i in range(self._model.columnCount()):
             col_name = self._model.record().fieldName(i)
             if col_name in header_map:
                self._model.setHeaderData(i, Qt.Horizontal, header_map[col_name])
             else:
                self._model.setHeaderData(i, Qt.Horizontal, col_name)

        self.load_data() # Загружаем данные при создании модели

    def get_model(self):
        """Возвращает QSqlTableModel для использования в View."""
        return self._model

    def load_data(self):
        """Загружает или обновляет данные из таблицы Category."""
        self._model.select()
        if self._model.lastError().type() != QSqlError.NoError:
             print("Ошибка загрузки данных категорий:", self._model.lastError().text())
             return False
        print("Данные категорий загружены.")
        return True

    def get_category_data(self, row):
        """Получает данные категории из указанной строки модели."""
        category_data = {}
        # Получаем названия столбцов из схемы БД для таблицы Category
        category_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

        for col_name in category_col_names_in_schema:
             col_index = self._model.fieldIndex(col_name)
             if col_index != -1:
                # Используем Qt.EditRole для получения сырых данных
                category_data[col_name] = self._model.data(self._model.index(row, col_index), Qt.EditRole)

        return category_data

    def add_category(self, data):
        """Добавляет новую категорию в базу данных."""
        category_id = data.get('id_category', '').strip()
        category_name = data.get('category', '').strip()

        # --- Валидация (можно перенести часть в Controller, но уникальность лучше проверять здесь) ---
        if not category_id:
             return False, "Пожалуйста, введите ID категории."
        if len(category_id) != 2:
             return False, "ID категории должен состоять ровно из 2 символов."
        # TODO: Добавить валидацию, если ID должен быть только цифрами или иметь определенный формат

        if not category_name:
            return False, "Пожалуйста, введите название категории."
        if len(category_name) > 40:
             return False, "Название категории не может превышать 40 символов."

        # Проверяем на уникальность ID и Названия перед добавлением
        query = QSqlQuery(self.db)
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE id_category = ? OR category = ?")
        query.addBindValue(category_id)
        query.addBindValue(category_name)
        if query.exec_() and query.next():
            count = query.value(0)
            if count > 0:
                # Уточняем, что именно дублируется
                check_id_query = QSqlQuery(self.db)
                check_id_query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE id_category = ?")
                check_id_query.addBindValue(category_id)
                check_id_query.exec_()
                check_id_query.next()
                if check_id_query.value(0) > 0:
                     return False, f"ID категории '{category_id}' уже существует."

                check_name_query = QSqlQuery(self.db)
                check_name_query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE category = ?")
                check_name_query.addBindValue(category_name)
                check_name_query.exec_()
                check_name_query.next()
                if check_name_query.value(0) > 0:
                     return False, f"Категория '{category_name}' уже существует."

                return False, "Дублирующаяся запись." # Fallback


        # Добавляем новую запись через модель
        row_count = self._model.rowCount()
        if not self._model.insertRow(row_count):
             error_text = self._model.lastError().text()
             print("Ошибка при вставке новой строки в модель:", error_text)
             return False, error_text

        # Устанавливаем данные в модель по именам столбцов
        col_indices = {col: self._model.fieldIndex(col) for col in self.column_names}

        if "id_category" in col_indices and col_indices["id_category"] != -1:
             self._model.setData(self._model.index(row_count, col_indices["id_category"]), category_id)
        if "category" in col_indices and col_indices["category"] != -1:
             self._model.setData(self._model.index(row_count, col_indices["category"]), category_name)


        if self._model.submitAll(): # Сохраняем изменения в базу данных
            print(f"Категория '{category_name}' (ID: {category_id}) успешно добавлена (Model).")
            # self.load_data() # Обновляем модель - Controller might do this
            return True, "Категория успешно добавлена."
        else:
            error_text = self._model.lastError().text()
            print("Ошибка при добавлении категории (Model):", error_text)
            self._model.revertAll() # Отменяем изменения, если сохранение не удалось
            return False, f"Не удалось добавить категорию: {error_text}"

    def update_category(self, row, data):
        """Обновляет данные существующей категории в базе данных."""
        category_id = data.get('id_category', '').strip()
        category_name = data.get('category', '').strip()

        # --- Валидация (можно перенести часть в Controller) ---
        if not category_id:
             return False, "Пожалуйста, введите ID категории."
        if len(category_id) != 2:
             return False, "ID категории должен состоять ровно из 2 символов."
        # TODO: Добавить валидацию, если ID должен быть только цифрами или иметь определенный формат

        if not category_name:
            return False, "Пожалуйста, введите название категории."
        if len(category_name) > 40:
             return False, "Название категории не может превышать 40 символов."

        # Проверяем на уникальность ID и Названия (исключая текущую запись)
        original_id = self._model.data(self._model.index(row, self._model.fieldIndex("id_category")), Qt.EditRole)
        original_name = self._model.data(self._model.index(row, self._model.fieldIndex("category")), Qt.EditRole)

        query = QSqlQuery(self.db)
        # Check for duplicate ID, excluding the current row's original ID
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE id_category = ? AND id_category != ?")
        query.addBindValue(category_id)
        query.addBindValue(original_id)
        if query.exec_() and query.next() and query.value(0) > 0:
             return False, f"ID категории '{category_id}' уже существует."

        # Check for duplicate Name, excluding the current row's original Name
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE category = ? AND category != ?")
        query.addBindValue(category_name)
        query.addBindValue(original_name)
        if query.exec_() and query.next() and query.value(0) > 0:
             return False, f"Категория '{category_name}' уже существует."


        # Устанавливаем данные в модель для указанной строки
        col_indices = {col: self._model.fieldIndex(col) for col in data if col in self.column_names}

        if "id_category" in col_indices and col_indices["id_category"] != -1:
             self._model.setData(self._model.index(row, col_indices["id_category"]), category_id)
        if "category" in col_indices and col_indices["category"] != -1:
             self._model.setData(self._model.index(row, col_indices["category"]), category_name)


        if self._model.submitAll(): # Сохраняем изменения в базу данных
            print(f"Категория в строке {row} успешно обновлена (Model).")
            # self.load_data() # Обновляем представление после редактирования - Controller might do this
            return True, "Изменения успешно сохранены."
        else:
            error_text = self._model.lastError().text()
            print("Ошибка при обновлении категории (Model):", error_text)
            self._model.revertAll() # Отменяем изменения
            return False, f"Не удалось сохранить изменения: {error_text}"

    def delete_category(self, row):
        """Удаляет категорию из базы данных по номеру строки."""
        # Получаем ID и название категории для сообщения (опционально, можно передать из View/Controller)
        id_col_index = self._model.fieldIndex("id_category")
        name_col_index = self._model.fieldIndex("category")
        item_id = self._model.data(self._model.index(row, id_col_index), Qt.DisplayRole) if id_col_index != -1 else "N/A"
        item_name = self._model.data(self._model.index(row, name_col_index), Qt.DisplayRole) if name_col_index != -1 else "Выбранная запись"

        if self._model.removeRow(row):
            if self._model.submitAll(): # Сохраняем изменение в базу данных
                print(f"Категория '{item_name}' (ID: {item_id}) успешно удалена (Model).")
                # self.load_data() # Обновляем представление после удаления - Controller might do this
                return True, f"Категория '{item_name}' (ID: {item_id}) успешно удалена."
            else:
                error_text = self._model.lastError().text()
                print("Ошибка при сохранении удаления (Model):", error_text)
                self._model.revertAll() # Отменяем удаление
                return False, f"Не удалось удалить категорию: {error_text}"
        else:
            print("Ошибка при удалении строки из модели (Model).")
            return False, "Не удалось удалить строку из модели."