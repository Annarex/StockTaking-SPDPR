# File: subcategory_model.py
from PyQt5.QtSql import QSqlRelationalTableModel, QSqlDatabase, QSqlQuery, QSqlError, QSqlRelation, QSqlTableModel
from PyQt5.QtCore import Qt, QVariant

# Импортируем схему базы данных для получения названий таблиц и столбцов
from database import DATABASE_SCHEMA

class SubcategoryModel:
    def __init__(self, db_connection):
        """
        Инициализирует модель для работы с таблицей Subcategory.
        """
        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто. Модель подкатегорий не может быть инициализирована.")
            self.model = None
            return

        self.table_name = "Subcategory"
        self.column_names = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
        self.unique_column = "id_subcategory"
        self._model = QSqlRelationalTableModel(None, self.db)
        self._model.setTable(self.table_name)

        # Устанавливаем связь для столбца id_category
        # Получаем индекс столбца id_category по имени
        category_col_index = self._model.fieldIndex("id_category")
        if category_col_index != -1:
             # Связь с таблицей Category, отображаем столбец 'category'
             self._model.setRelation(category_col_index, QSqlRelation("Category", "id_category", "category"))
        else:
             print("Предупреждение: Столбец 'id_category' не найден в модели Subcategory.")


        # Устанавливаем стратегию сохранения изменений: вручную через submitAll()
        self._model.setEditStrategy(QSqlTableModel.OnManualSubmit)

        # Устанавливаем заголовки столбцов (можно оставить здесь или перенести в View)
        header_map = {
            "id_subcategory": "ID Подкатегории",
            "id_category": "Категория",
            "subcategory": "Название подкатегории",
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
        Возвращает экземпляр QSqlRelationalTableModel для использования в View.
        """
        return self._model

    def load_data(self):
        """
        Загружает или обновляет данные из таблицы Subcategory.
        Возвращает True в случае успеха, False в случае ошибки.
        """
        self._model.select()
        if self._model.lastError().type() != QSqlError.NoError:
             print("Ошибка загрузки данных подкатегорий:", self._model.lastError().text())
             return False
        print("Данные подкатегорий загружены.")
        return True

    def get_subcategory_data(self, row):
        """
        Получает данные подкатегории из указанной строки модели.
        Возвращает словарь с данными подкатегории.
        """
        subcategory_data = {}
        # Получаем названия столбцов из схемы БД для таблицы Subcategory
        # Включаем id_category, так как нам нужен его ID для диалога редактирования
        subcategory_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
        # Убедимся, что id_category включен в список, даже если он определен как FK
        if 'id_category' not in subcategory_col_names_in_schema:
             subcategory_col_names_in_schema.append('id_category')


        for col_name in subcategory_col_names_in_schema:
             col_index = self._model.fieldIndex(col_name)
             if col_index != -1:
                # Используем Qt.EditRole для получения сырых данных (например, ID категории),
                # а не отображаемого значения (названия категории)
                subcategory_data[col_name] = self._model.data(self._model.index(row, col_index), Qt.EditRole)

        return subcategory_data

    def add_subcategory(self, data):
        """
        Добавляет новую подкатегорию в базу данных.
        Принимает словарь с данными подкатегории.
        Возвращает кортеж (success, message).
        """
        subcategory_id = data.get('id_subcategory', '').strip()
        category_id = data.get('id_category') # Это ID категории из комбобокса диалога
        subcategory_name = data.get('subcategory', '').strip()

        # --- Валидация данных (часть валидации может быть в View/Controller, но проверка уникальности здесь) ---
        if not subcategory_id:
             return False, "Пожалуйста, введите ID подкатегории."
        if len(subcategory_id) != 2:
             return False, "ID подкатегории должен состоять ровно из 2 символов."
        # TODO: Добавить валидацию формата ID, если требуется (например, только цифры)

        if category_id is None:
             return False, "Пожалуйста, выберите категорию."

        if not subcategory_name:
            return False, "Пожалуйста, введите название подкатегории."
        if len(subcategory_name) > 40:
             return False, "Название подкатегории не может превышать 40 символов."

        # Проверяем на уникальность ID подкатегории по всей таблице (согласно PRIMARY KEY)
        query = QSqlQuery(self.db)
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE id_subcategory = ?")
        query.addBindValue(subcategory_id)
        if query.exec_() and query.next():
            count = query.value(0)
            if count > 0:
                return False, f"ID подкатегории '{subcategory_id}' уже существует."

        # Проверяем на уникальность названия подкатегории в рамках выбранной категории
        # Схема не указывает UNIQUE на subcategory, но часто это желаемое поведение.
        # Если уникальность названия нужна только в рамках родительской категории, выполняем этот запрос.
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE id_category = ? AND subcategory = ?")
        query.addBindValue(category_id)
        query.addBindValue(subcategory_name)
        if query.exec_() and query.next():
             count = query.value(0)
             if count > 0:
                 # Получаем название категории для более информативного сообщения об ошибке
                 cat_query = QSqlQuery(self.db)
                 cat_query.prepare("SELECT category FROM Category WHERE id_category = ?")
                 cat_query.addBindValue(category_id)
                 cat_name = ""
                 if cat_query.exec_() and cat_query.next():
                      cat_name = cat_query.value(0)
                 return False, f"Подкатегория '{subcategory_name}' уже существует в категории '{cat_name}'."


        # Добавляем новую пустую строку в модель
        row_count = self._model.rowCount()
        if not self._model.insertRow(row_count):
             error_text = self._model.lastError().text()
             print("Ошибка при вставке новой строки в модель:", error_text)
             return False, error_text

        # Устанавливаем данные в модель для новой строки по именам столбцов
        col_indices = {col: self._model.fieldIndex(col) for col in self.column_names}

        if "id_subcategory" in col_indices and col_indices["id_subcategory"] != -1:
             self._model.setData(self._model.index(row_count, col_indices["id_subcategory"]), subcategory_id)
        if "id_category" in col_indices and col_indices["id_category"] != -1:
             # Устанавливаем ID категории (EditRole)
             self._model.setData(self._model.index(row_count, col_indices["id_category"]), category_id)
        if "subcategory" in col_indices and col_indices["subcategory"] != -1:
             self._model.setData(self._model.index(row_count, col_indices["subcategory"]), subcategory_name)


        # Сохраняем изменения в базу данных
        if self._model.submitAll():
            print(f"Подкатегория '{subcategory_name}' (ID: {subcategory_id}) успешно добавлена (Model).")
            # Модель автоматически обновится после submitAll, если стратегия OnManualSubmit
            return True, "Подкатегория успешно добавлена."
        else:
            error_text = self._model.lastError().text()
            print("Ошибка при добавлении подкатегории (Model):", error_text)
            self._model.revertAll() # Отменяем изменения в модели, если сохранение не удалось
            return False, f"Не удалось добавить подкатегорию: {error_text}"

    def update_subcategory(self, row, data):
        """
        Обновляет данные существующей подкатегории в базе данных.
        Принимает номер строки и словарь с новыми данными.
        Возвращает кортеж (success, message).
        """
        subcategory_id = data.get('id_subcategory', '').strip() # ID не должен меняться при редактировании, но получаем его
        category_id = data.get('id_category') # Это новый ID категории из комбобокса диалога
        subcategory_name = data.get('subcategory', '').strip()

        # --- Валидация данных (часть валидации может быть в View/Controller) ---
        if not subcategory_id:
             return False, "Ошибка: ID подкатегории не может быть пустым при обновлении."
        if len(subcategory_id) != 2:
             return False, "Ошибка: ID подкатегории должен состоять ровно из 2 символов."
        # TODO: Добавить валидацию формата ID, если требуется

        if category_id is None:
             return False, "Пожалуйста, выберите категорию."

        if not subcategory_name:
            return False, "Пожалуйста, введите название подкатегории."
        if len(subcategory_name) > 40:
             return False, "Название подкатегории не может превышать 40 символов."

        # Проверяем на уникальность названия подкатегории в рамках *новой* выбранной категории,
        # исключая текущую редактируемую запись (по ее оригинальному ID)
        original_id = self._model.data(self._model.index(row, self._model.fieldIndex("id_subcategory")), Qt.EditRole)
        # original_category_id = self._model.data(self._model.index(row, self._model.fieldIndex("id_category")), Qt.EditRole) # Не используется напрямую в запросе уникальности названия
        # original_name = self._model.data(self._model.index(row, self._model.fieldIndex("subcategory")), Qt.EditRole) # Не используется напрямую в запросе уникальности названия


        query = QSqlQuery(self.db)
        # Проверяем на уникальность названия подкатегории в рамках новой категории, исключая текущий элемент
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE id_category = ? AND subcategory = ? AND id_subcategory != ?")
        query.addBindValue(category_id)
        query.addBindValue(subcategory_name)
        query.addBindValue(original_id) # Исключаем текущий элемент по его оригинальному ID
        if query.exec_() and query.next() and query.value(0) > 0:
             # Получаем название категории для сообщения
             cat_query = QSqlQuery(self.db)
             cat_query.prepare("SELECT category FROM Category WHERE id_category = ?")
             cat_query.addBindValue(category_id)
             cat_name = ""
             if cat_query.exec_() and cat_query.next():
                  cat_name = cat_query.value(0)
             return False, f"Подкатегория '{subcategory_name}' уже существует в категории '{cat_name}'."


        # Устанавливаем данные в модель для указанной строки
        col_indices = {col: self._model.fieldIndex(col) for col in self.column_names}

        # ID подкатегории не должен меняться при редактировании, но мы можем установить его на всякий случай
        if "id_subcategory" in col_indices and col_indices["id_subcategory"] != -1:
             self._model.setData(self._model.index(row, col_indices["id_subcategory"]), subcategory_id)
        if "id_category" in col_indices and col_indices["id_category"] != -1:
             # Устанавливаем новый ID категории (EditRole)
             self._model.setData(self._model.index(row, col_indices["id_category"]), category_id)
        if "subcategory" in col_indices and col_indices["subcategory"] != -1:
             self._model.setData(self._model.index(row, col_indices["subcategory"]), subcategory_name)


        # Сохраняем изменения в базу данных
        if self._model.submitAll():
            print(f"Подкатегория в строке {row} успешно обновлена (Model).")
            # Модель автоматически обновится после submitAll
            return True, "Изменения успешно сохранены."
        else:
            error_text = self._model.lastError().text()
            print("Ошибка при обновлении подкатегории (Model):", error_text)
            self._model.revertAll() # Отменяем изменения в модели
            return False, f"Не удалось сохранить изменения: {error_text}"

    def delete_subcategory(self, row):
        """
        Удаляет подкатегорию из базы данных по номеру строки.
        Принимает номер строки.
        Возвращает кортеж (success, message).
        """
        # Получаем ID и название подкатегории для сообщения подтверждения (опционально)
        id_col_index = self._model.fieldIndex("id_subcategory")
        name_col_index = self._model.fieldIndex("subcategory")
        item_id = self._model.data(self._model.index(row, id_col_index), Qt.DisplayRole) if id_col_index != -1 else "N/A"
        item_name = self._model.data(self._model.index(row, name_col_index), Qt.DisplayRole) if name_col_index != -1 else "Выбранная запись"

        # Удаляем строку из модели
        if self._model.removeRow(row):
            # Сохраняем изменение в базу данных
            if self._model.submitAll():
                print(f"Подкатегория '{item_name}' (ID: {item_id}) успешно удалена (Model).")
                # Модель автоматически обновится
                return True, f"Подкатегория '{item_name}' (ID: {item_id}) успешно удалена."
            else:
                error_text = self._model.lastError().text()
                print("Ошибка при сохранении удаления (Model):", error_text)
                self._model.revertAll() # Отменяем удаление в модели
                return False, f"Не удалось удалить подкатегорию: {error_text}"
        else:
            print("Ошибка при удалении строки из модели (Model).")
            return False, "Не удалось удалить строку из модели."

    def get_categories(self):
        """
        Получает список категорий из базы данных для заполнения комбобокса в диалоге.
        Возвращает список кортежей (id_category, category).
        """
        categories = []
        query = QSqlQuery("SELECT id_category, category FROM Category ORDER BY category", self.db)
        while query.next():
            item_id = query.value(0)
            item_name = query.value(1)
            categories.append((item_id, item_name))
        return categories