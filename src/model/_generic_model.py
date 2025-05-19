
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError
from PyQt5.QtCore import Qt, QVariant, pyqtSignal, QObject

from database import DATABASE_SCHEMA

class GenericModel(QObject): 
    model_error = pyqtSignal(str)

    def __init__(self, db_connection, table_name, id_column, name_column, unique_name_column=None):
        super().__init__() 

        self.db = db_connection
        self.table_name = table_name
        self.id_column = id_column
        self.name_column = name_column
        self.unique_name_column = unique_name_column if unique_name_column is not None else name_column

        if not self.db or not self.db.isOpen():
            print(f"Ошибка: Соединение с базой данных не установлено или закрыто. Модель для таблицы '{self.table_name}' не может быть инициализирована.")
            self._model = None
            return


        all_table_cols_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
        if self.id_column not in all_table_cols_in_schema:
             print(f"Ошибка: Столбец ID '{self.id_column}' не найден в схеме для таблицы '{self.table_name}'.")
             self._model = None
             return
        if self.name_column not in all_table_cols_in_schema:
             print(f"Ошибка: Столбец наименования '{self.name_column}' не найден в схеме для таблицы '{self.table_name}'.")
             self._model = None
             return
        if self.unique_name_column not in all_table_cols_in_schema:
             print(f"Ошибка: Столбец уникального наименования '{self.unique_name_column}' не найден в схеме для таблицы '{self.table_name}'.")
             self._model = None
             return


        self._model = QSqlTableModel(self, self.db) 
        self._model.setTable(self.table_name)
        self._model.setEditStrategy(QSqlTableModel.OnFieldChange)
     #    self._model.lastError.connect(self._on_model_last_error)
        header_map = {
            self.id_column: "ID",
            self.name_column: "Наименование",
        }

        for i in range(self._model.columnCount()):
             col_name = self._model.record().fieldName(i)
             if col_name in header_map:
                self._model.setHeaderData(i, Qt.Horizontal, header_map[col_name])
             else:
                self._model.setHeaderData(i, Qt.Horizontal, col_name)


        self.load_data()

    def _on_model_last_error(self, error):
        if error.type() != QSqlError.NoError:
             self.model_error.emit(error.text())


    def get_model(self):
        return self._model

    def load_data(self):
        if self._model is None:
             return False # Модель не инициализирована из-за ошибки БД

        self._model.select()
        if self._model.lastError().type() != QSqlError.NoError:
             print(f"Ошибка загрузки данных для таблицы '{self.table_name}':", self._model.lastError().text())
             return False
        print(f"Данные для таблицы '{self.table_name}' загружены.")
        return True

    def get_item_data(self, row):
        if self._model is None or row < 0 or row >= self._model.rowCount():
             return {} 
        item_data = {}

        all_table_cols_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

        for col_name in all_table_cols_in_schema:
             col_index = self._model.fieldIndex(col_name)
             if col_index != -1:
                item_data[col_name] = self._model.data(self._model.index(row, col_index), Qt.EditRole)

        return item_data

    def add_item(self, data):
        item_name = data.get(self.name_column, '').strip()
        item_id = data.get(self.id_column, '').strip()

        if not item_name:
             return False, f"Пожалуйста, введите {self.name_column}."

        if self.unique_name_column:
             query = QSqlQuery(self.db)
             query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE {self.unique_name_column} = ?")
             query.addBindValue(item_name)
             if query.exec_() and query.next():
                 count = query.value(0)
                 if count > 0:
                     return False, f"Элемент с таким {self.unique_name_column} уже существует."

        # Если ID ручной (не автоинкрементный), проверяем его наличие и уникальность
        # Проверяем по схеме, является ли ID автоинкрементным
        is_auto_increment = False
        for col_def in DATABASE_SCHEMA.get(self.table_name, []):
             if col_def.strip().startswith(self.id_column) and "AUTOINCREMENT" in col_def.upper():
                 is_auto_increment = True
                 break

        if not is_auto_increment:
             if item_id is None or str(item_id).strip() == "":
                  return False, f"Пожалуйста, введите {self.id_column}."
              
             query = QSqlQuery(self.db)
             query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE {self.id_column} = ?")
             query.addBindValue(item_id)
             if query.exec_() and query.next():
                 count = query.value(0)
                 if count > 0:
                     return False, f"ID '{item_id}' уже существует."

        row_count = self._model.rowCount()
        if not self._model.insertRows(row_count, 1):
             error_text = self._model.lastError().text()
             print(f"Ошибка при вставке новой строки в модель для таблицы '{self.table_name}':", error_text)
             return False, error_text

        # Устанавливаем ID, только если он ручной (не автоинкрементный)
        if not is_auto_increment and item_id is not None:
             id_col_index = self._model.fieldIndex(self.id_column)
             if id_col_index != -1:
                  self._model.setData(self._model.index(row_count, id_col_index), item_id)

        # Устанавливаем наименование
        name_col_index = self._model.fieldIndex(self.name_column)
        if name_col_index != -1:
             self._model.setData(self._model.index(row_count, name_col_index), item_name)
        else:
             self._model.revertAll()
             return False, f"Ошибка: Столбец '{self.name_column}' не найден в модели."


        if self._model.submitAll():
            print(f"Элемент '{item_name}' успешно добавлен в таблицу '{self.table_name}' (Model).")
            return True, f"Элемент '{item_name}' успешно добавлен."
        else:
            error_text = self._model.lastError().text()
            print(f"Ошибка при добавлении элемента в таблицу '{self.table_name}' (Model):", error_text)
            self._model.revertAll()
            return False, f"Не удалось добавить элемент: {error_text}"

    def delete_item(self, row):
        if self._model is None or row < 0 or row >= self._model.rowCount():
             return False, "Ошибка: Некорректный индекс строки для удаления."

        item_data = self.get_item_data(row)
        item_id = item_data.get(self.id_column, 'N/A')
        item_name = item_data.get(self.name_column, 'Выбранная запись')

        if self._model.removeRow(row):
            if self._model.submitAll():
                print(f"Элемент '{item_name}' (ID: {item_id}) успешно удален из таблицы '{self.table_name}' (Model).")
                return True, f"Элемент '{item_name}' (ID: {item_id}) успешно удален."
            else:
                error_text = self._model.lastError().text()
                print(f"Ошибка при сохранении удаления из таблицы '{self.table_name}' (Model):", error_text)
                self._model.revertAll()
                return False, f"Не удалось удалить элемент: {error_text}"
        else:
            print(f"Ошибка при удалении строки из модели для таблицы '{self.table_name}' (Model).")
            return False, "Не удалось удалить строку из модели."