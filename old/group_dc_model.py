# File: group_dc_model.py
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError
from PyQt5.QtCore import Qt, QVariant, pyqtSignal, QObject # Импортируем QObject и pyqtSignal для сигналов ошибок

# Импортируем схему базы данных для получения названий таблиц и столбцов
from database import DATABASE_SCHEMA

class GroupDCModel(QObject): 
    model_error = pyqtSignal(str)

    def __init__(self, db_connection):
        super().__init__()

        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто. Модель групп домена не может быть инициализирована.")
            # В реальном приложении здесь может быть выброшено исключение
            self._model = None
            return

        self.table_name = "GroupDC"
        self.column_names = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
        self.unique_column = "group_dc"
        self._model = QSqlTableModel(self, self.db) 
        self._model.setTable(self.table_name)
        self._model.setEditStrategy(QSqlTableModel.OnFieldChange)
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

    def add_group_dc(self, data):
        id_group_dc = data.get('id_group_dc', '').strip()
        group_dc = data.get('group_dc', '').strip()

        if not id_group_dc:
             return False, "Пожалуйста, введите ID группы."
        if len(id_group_dc) != 2:
             return False, "ID группы должен состоять ровно из 2 символов."
        if not group_dc:
             return False, "Пожалуйста, введите название группы домена."
        if len(group_dc) > 20:
             return False, "Название группы домена не может превышать 20 символов."

        # Проверяем на уникальность ID и Группу перед добавлением
        query = QSqlQuery(self.db)
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE id_group_dc = ? OR group_dc = ?")
        query.addBindValue(id_group_dc)
        query.addBindValue(group_dc)
        if query.exec_() and query.next():
            count = query.value(0)
            if count > 0:
                # Уточняем, что именно дублируется
                check_id_query = QSqlQuery(self.db)
                check_id_query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE id_group_dc = ?")
                check_id_query.addBindValue(id_group_dc)
                check_id_query.exec_()
                check_id_query.next()
                if check_id_query.value(0) > 0:
                     return False, f"ID группы '{group_dc}' уже существует."

                check_name_query = QSqlQuery(self.db)
                check_name_query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE group_dc = ?")
                check_name_query.addBindValue(id_group_dc)
                check_name_query.exec_()
                check_name_query.next()
                if check_name_query.value(0) > 0:
                     return False, f"Группа домена '{group_dc}' уже существует."

                return False, "Дублирующаяся запись."


        # Добавляем новую запись через модель
        row_count = self._model.rowCount()
        if not self._model.insertRow(row_count):
             error_text = self._model.lastError().text()
             print("Ошибка при вставке новой строки в модель:", error_text)
             return False, error_text

        # Устанавливаем данные в модель по именам столбцов
        col_indices = {col: self._model.fieldIndex(col) for col in self.column_names}

        if "id_group_dc" in col_indices and col_indices["id_group_dc"] != -1:
             self._model.setData(self._model.index(row_count, col_indices["id_group_dc"]), id_group_dc)
        if "group_dc" in col_indices and col_indices["group_dc"] != -1:
             self._model.setData(self._model.index(row_count, col_indices["group_dc"]), group_dc)


        if self._model.submitAll():
            print(f"Группа '{group_dc}' (ID: {id_group_dc}) успешно добавлена (Model).")
            return True, "Группа успешно добавлена."
        else:
            error_text = self._model.lastError().text()
            print("Ошибка при добавлении группы (Model):", error_text)
            self._model.revertAll()
            return False, f"Не удалось добавить категорию: {error_text}"


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