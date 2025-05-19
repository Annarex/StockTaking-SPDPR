# File: src/controller/generic_lookup_controller.py
import re
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog
from PyQt5.QtCore import QDate, QObject

# Импортируем универсальную Модель и Вид
from src.model._generic_model import GenericModel
from src.view._generic_view import GenericView

from src.utils.csv_handler import import_data_from_csv, export_data_to_csv
from database import DATABASE_SCHEMA


class GenericController(QObject):
    def __init__(self, db_connection, table_name, id_column, name_column, view_title, add_input_placeholder, unique_name_column=None):
        super().__init__() 

        self.db = db_connection
        self.table_name = table_name
        self.id_column = id_column
        self.name_column = name_column
        self.unique_name_column = unique_name_column if unique_name_column is not None else name_column
        self.view_title = view_title
        self.add_input_placeholder = add_input_placeholder

        if not self.db or not self.db.isOpen():
            print(f"Ошибка: Соединение с базой данных не установлено или закрыто. Контроллер для таблицы '{self.table_name}' не может быть инициализирован.")
            self.model = None
            self.view = None
            return

        self.model = GenericModel(self.db, self.table_name, self.id_column, self.name_column, self.unique_name_column)

        if self.model is None or self.model.get_model() is None:
             self.view = None
             return
        
        self.view = GenericView(view_title=self.view_title, add_input_placeholder=self.add_input_placeholder)
        self.view.set_model(self.model.get_model())

        for col_def in DATABASE_SCHEMA.get(self.table_name, []):
             if col_def.strip().startswith(self.name_column):
                 match = re.search(r'VARCHAR\((\d+)\)', col_def, re.IGNORECASE)
                 if match:
                     max_len = int(match.group(1))
                     self.view.add_input.setMaxLength(max_len)
                     break

        self.view.add_item_requested.connect(self.add_item)
        self.view.delete_item_requested.connect(self.delete_item)
        self.view.refresh_list_requested.connect(self.refresh_list)
        self.view.import_csv_requested.connect(self.import_items)
        self.view.export_csv_requested.connect(self.export_items)
        self.model.model_error.connect(self.handle_model_error)

    def get_view(self):
        return self.view

    def refresh_list(self):
        if self.model and self.model.load_data():
            QMessageBox.information(self.view, "Обновление", f"Список '{self.view_title}' обновлен.")
        else:
             QMessageBox.critical(self.view, "Ошибка", f"Не удалось обновить список '{self.view_title}'.")

    def handle_model_error(self, error_message):
        QMessageBox.critical(self.view, "Ошибка сохранения", f"Не удалось сохранить изменение: {error_message}")
        self.refresh_list()


    def add_item(self):
        item_id = self.view.get_add_input_text()['id']
        item_name = self.view.get_add_input_text()['name_column']
        if not item_name:
             QMessageBox.warning(self.view, "Предупреждение", f"Пожалуйста, введите {self.add_input_placeholder.lower()}.")
             return
        data = {self.id_column: item_id, self.name_column: item_name}
        success, message = self.model.add_item(data)
        if success:
            QMessageBox.information(self.view, "Успех", message)
            self.view.clear_add_input()
            self.refresh_list()
        else:
            QMessageBox.critical(self.view, "Ошибка", message)

    def delete_item(self):
        row = self.view.get_selected_row()
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", f"Пожалуйста, выберите элемент для удаления.")
             return

        item_data = self.model.get_item_data(row)
        item_id = item_data.get(self.id_column, 'N/A')
        item_name = item_data.get(self.name_column, 'Выбранная запись')
        reply = QMessageBox.question(self.view, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить '{item_name}' (ID: {item_id})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            success, message = self.model.delete_item(row)
            if success:
                QMessageBox.information(self.view, "Успех", message)
                self.refresh_list()
            else:
                QMessageBox.critical(self.view, "Ошибка", message)

    def import_items(self):
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self.view, "Предупреждение", "Невозможно выполнить импорт: соединение с базой данных отсутствует.")
             return
        file_path, _ = QFileDialog.getOpenFileName(self.view, f"Импорт данных в таблицу '{self.table_name}'",
                                                   "",
                                                   "CSV файлы (*.csv);;Все файлы (*)")
        if file_path:
            print(f"Выбран файл для импорта в {self.table_name}: {file_path}")

            all_table_cols = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

            column_digits = {}
            for col_def in DATABASE_SCHEMA.get(self.table_name, []):
                 if col_def.strip().startswith(self.id_column) and "VARCHAR" in col_def.upper():
                     match = re.search(r'VARCHAR\((\d+)\)', col_def, re.IGNORECASE)
                     if match:
                         column_digits[self.id_column] = int(match.group(1))
                         break

          
            success, message = import_data_from_csv(self.db, file_path, self.table_name, all_table_cols, column_digits=column_digits, unique_column=self.unique_name_column)

            if success:
                QMessageBox.information(self.view, "Импорт завершен", message)
                self.refresh_list()
            else:
                QMessageBox.critical(self.view, "Ошибка импорта", message)
        else:
            print("Выбор файла отменен.")

    def export_items(self):
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self.view, "Предупреждение", "Невозможно выполнить экспорт: соединение с базой данных отсутствует.")
             return

        default_filename = f"{self.table_name}_export_{QDate.currentDate().toString('yyyyMMdd')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self.view, f"Экспорт данных из таблицы '{self.table_name}'", default_filename, "CSV файлы (*.csv);;Все файлы (*)")
        if file_path:
            print(f"Выбран файл для экспорта из {self.table_name}: {file_path}")
            all_table_cols = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
            cols_to_export = all_table_cols

            success, message = export_data_to_csv(self.db, file_path, self.table_name, cols_to_export)

            if success:
                QMessageBox.information(self.view, "Экспорт завершен", message)
                print(f"Экспорт сохранен: {file_path}")
            else:
                QMessageBox.critical(self.view, "Ошибка экспорта", message)
        else:
            print("Сохранение отчета отменено.")