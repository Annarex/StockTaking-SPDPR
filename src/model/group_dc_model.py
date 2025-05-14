# File: group_dc_model.py
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError
from PyQt5.QtCore import Qt, QVariant, pyqtSignal, QObject # Импортируем QObject и pyqtSignal для сигналов ошибок

# Импортируем схему базы данных для получения названий таблиц и столбцов
from database import DATABASE_SCHEMA

class GroupDCModel(QObject): 
    
    model_error = pyqtSignal(str)

    def __init__(self, db_connection):
        super().__init__() # Инициализируем QObject

        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто. Модель групп домена не может быть инициализирована.")
            self._model = None
            return

        self.table_name = "GroupDC"
        self.column_names = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
        self.unique_column = "group_dc"

        self._model = QSqlTableModel(self, self.db)
        self._model.setTable(self.table_name)
        self._model.setEditStrategy(QSqlTableModel.OnFieldChange)
        self._model.lastError.connect(self._on_model_last_error)

        header_map = {
            "id_group_dc": "ID",
            "group_dc": "Группа домена",
        }
        for i in range(self._model.columnCount()):
             col_name = self._model.record().fieldName(i)
             if col_name in header_map:
                self._model.setHeaderData(i, Qt.Horizontal, header_map[col_name])
             else:
                self._model.setHeaderData(i, Qt.Horizontal, col_name)

        self.load_data()

    def _on_model_last_error(self, error):
        """
        Обработчик сигнала lastError от QSqlTableModel.
        Испускает наш собственный сигнал model_error.
        """
        if error.type() != QSqlError.NoError:
             self.model_error.emit(error.text())


    def get_model(self):
        return self._model

    def load_data(self):
        self._model.select()
        if self._model.lastError().type() != QSqlError.NoError:
             print("Ошибка загрузки данных групп домена:", self._model.lastError().text())
             return False
        print("Данные групп домена загружены.")
        return True

    def get_group_dc_data(self, row):
        group_dc_data = {}
        group_dc_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
        for col_name in group_dc_col_names_in_schema:
             col_index = self._model.fieldIndex(col_name)
             if col_index != -1:
                group_dc_data[col_name] = self._model.data(self._model.index(row, col_index), Qt.EditRole)
        return group_dc_data

    def add_item(self, item_name):
        item_name = item_name.strip()
        if not item_name:
             return False, "Пожалуйста, введите название группы домена."
        if len(item_name) > 20:
             return False, "Название группы домена не может превышать 20 символов."

        query = QSqlQuery(self.db)
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE group_dc = ?")
        query.addBindValue(item_name)
        if query.exec_() and query.next():
            count = query.value(0)
            if count > 0:
                return False, f"Группа домена '{item_name}' уже существует."


        # Добавляем новую пустую строку в модель
        row_count = self._model.rowCount()
        # Используем insertRows для добавления одной строки
        if not self._model.insertRows(row_count, 1):
             error_text = self._model.lastError().text()
             print("Ошибка при вставке новой строки в модель:", error_text)
             return False, error_text

        # Устанавливаем данные в модель для новой строки по имени столбца 'group_dc'
        name_col_index = self._model.fieldIndex("group_dc")
        if name_col_index != -1:
             self._model.setData(self._model.index(row_count, name_col_index), item_name)
        else:
             # Это маловероятно, если схема БД корректна
             self._model.revertAll() # Отменяем вставку строки
             return False, "Ошибка: Столбец 'group_dc' не найден в модели."


        # При стратегии OnFieldChange, submitAll() не требуется для каждой ячейки,
        # но insertRow/insertRows требует submitAll() для фиксации добавления строки.
        # Однако, если мы сразу устанавливаем данные после insertRow, OnFieldChange может сработать.
        # Лучше явно вызвать submitAll() после установки всех данных для новой строки.
        # Проверяем, успешно ли сохранились изменения (включая автогенерацию ID)
        if self._model.submitAll():
            print(f"Группа домена '{item_name}' успешно добавлена (Model).")
            # Модель автоматически обновится после submitAll
            return True, "Группа домена успешно добавлена."
        else:
            error_text = self._model.lastError().text()
            print("Ошибка при добавлении группы домена (Model):", error_text)
            self._model.revertAll() # Отменяем изменения в модели, если сохранение не удалось
            return False, f"Не удалось добавить группу домена: {error_text}"


    # При стратегии OnFieldChange, редактирование происходит напрямую в таблице,
    # и модель сама сохраняет изменения. Метод update_item не нужен.
    # def update_item(self, row, data): ...


    def delete_item(self, row):
        id_col_index = self._model.fieldIndex("id_group_dc")
        name_col_index = self._model.fieldIndex("group_dc")
        item_id = self._model.data(self._model.index(row, id_col_index), Qt.DisplayRole) if id_col_index != -1 else "N/A"
        item_name = self._model.data(self._model.index(row, name_col_index), Qt.DisplayRole) if name_col_index != -1 else "Выбранная запись"

        if self._model.removeRow(row):
            if self._model.submitAll():
                print(f"Группа домена '{item_name}' (ID: {item_id}) успешно удалена (Model).")
                return True, f"Группа домена '{item_name}' (ID: {item_id}) успешно удалена."
            else:
                error_text = self._model.lastError().text()
                print("Ошибка при сохранении удаления (Model):", error_text)
                self._model.revertAll()
                return False, f"Не удалось удалить группу домена: {error_text}"
        else:
            print("Ошибка при удалении строки из модели (Model).")
            return False, "Не удалось удалить строку из модели."