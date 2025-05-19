from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog
from PyQt5.QtCore import QDate

from src.model.departments_model import DepartmentsModel
from src.view.departments_view import DepartmentsView, DepartmentDialog
from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

from database import DATABASE_SCHEMA


class DepartmentsController:
    def __init__(self, db_connection):
        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто. Контроллер отделов не может быть инициализирован.")
            self.model = None
            self.view = None
            return

        self.model = DepartmentsModel(self.db)
        self.view = DepartmentsView()

        self.view.set_model(self.model.get_model())

        self.view.add_department_requested.connect(self.add_department)
        self.view.edit_department_requested.connect(self.edit_department)
        self.view.delete_department_requested.connect(self.delete_department)
        self.view.refresh_list_requested.connect(self.refresh_list)
        self.view.import_csv_requested.connect(self.import_departments_from_csv)
        self.view.export_csv_requested.connect(self.export_departments_to_csv)


    def get_view(self):
        return self.view

    def refresh_list(self):
        if self.model and self.model.load_data():
            QMessageBox.information(self.view, "Обновление", "Список отделов обновлен.")
        else:
             QMessageBox.critical(self.view, "Ошибка", "Не удалось обновить список отделов.")


    def add_department(self):
        dialog = DepartmentDialog(parent=self.view)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.validate_data():
                data = dialog.get_data()
                success, message = self.model.add_department(data)
                if success:
                    QMessageBox.information(self.view, "Успех", message)
                    self.refresh_list()
                else:
                    QMessageBox.critical(self.view, "Ошибка", message)

    def edit_department(self, row):
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, выберите отдел для редактирования.")
             return

        department_data = self.model.get_department_data(row)
        if not department_data:
             QMessageBox.critical(self.view, "Ошибка", "Не удалось получить данные выбранного отдела.")
             return

        dialog = DepartmentDialog(department_data=department_data, parent=self.view)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.validate_data():
                new_data = dialog.get_data()
                new_data['id_department'] = department_data.get('id_department')
                success, message = self.model.update_department(row, new_data)
                if success:
                    QMessageBox.information(self.view, "Успех", message)
                    self.refresh_list()
                else:
                    QMessageBox.critical(self.view, "Ошибка", message)


    def delete_department(self, row):
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, выберите отдел для удаления.")
             return

        department_data = self.model.get_department_data(row)
        item_id = department_data.get('id_department', 'N/A')
        item_name = department_data.get('department_fullname', 'Выбранная запись')

        reply = QMessageBox.question(self.view, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить отдел '{item_name}' (ID: {item_id})?\n"
                                     "Пользователи, связанные с этим отделом, потеряют свой отдел.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            success, message = self.model.delete_department(row)
            if success:
                QMessageBox.information(self.view, "Успех", message)
                self.refresh_list()
            else:
                QMessageBox.critical(self.view, "Ошибка", message)

    def import_departments_from_csv(self):
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self.view, "Предупреждение", "Невозможно выполнить импорт: соединение с базой данных отсутствует.")
             return

        file_path, _ = QFileDialog.getOpenFileName(self.view, f"Импорт данных в таблицу '{self.model.table_name}'", "", "CSV файлы (*.csv);;Все файлы (*)")

        if file_path:
            print(f"Выбран файл для импорта в {self.model.table_name}: {file_path}")
            all_department_cols = [col.split()[0] for col in DATABASE_SCHEMA.get(self.model.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

            success, message = import_data_from_csv(self.db, file_path, self.model.table_name, all_department_cols, unique_column=self.model.unique_column)

            if success:
                QMessageBox.information(self.view, "Импорт завершен", message)
                self.refresh_list()
            else:
                QMessageBox.critical(self.view, "Ошибка импорта", message)
        else:
            print("Выбор файла отменен.")

    def export_departments_to_csv(self):
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self.view, "Предупреждение", "Невозможно выполнить экспорт: соединение с базой данных отсутствует.")
             return

        default_filename = f"{self.model.table_name}_export_{QDate.currentDate().toString('yyyyMMdd')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self.view, f"Экспорт данных из таблицы '{self.model.table_name}'", default_filename, "CSV файлы (*.csv);;Все файлы (*)")
        if file_path:
            print(f"Выбран файл для экспорта из {self.model.table_name}: {file_path}")
            department_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.model.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
            cols_to_export = department_col_names_in_schema
            success, message = export_data_to_csv(self.db, file_path, self.model.table_name, cols_to_export)

            if success:
                QMessageBox.information(self.view, "Экспорт завершен", message)
                print(f"Экспорт сохранен: {file_path}")
            else:
                QMessageBox.critical(self.view, "Ошибка экспорта", message)
        else:
            print("Сохранение отчета отменено.")

