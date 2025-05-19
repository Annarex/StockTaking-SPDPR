from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog
from PyQt5.QtCore import QDate

from src.model.employee_model import EmployeeModel
from src.view.employee_view import EmployeeView, EmployeeDialog # Import both View components
from src.utils.csv_handler import import_data_from_csv, export_data_to_csv # Assuming these are available
from database import DATABASE_SCHEMA # Need schema for CSV handler


class EmployeeController:
    def __init__(self, db_connection):
        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто. Контроллер пользователей не может быть инициализирован.")
            self.model = None
            self.view = None
            return

        self.model = EmployeeModel(self.db)
        self.view = EmployeeView()
        
        self.view.set_model(self.model.get_model())

        # Connect signals from the View to slots in the Controller
        self.view.add_employee_requested.connect(self.add_employee)
        self.view.edit_employee_requested.connect(self.edit_employee)
        self.view.delete_employee_requested.connect(self.delete_employee)
        self.view.refresh_list_requested.connect(self.refresh_list)
        self.view.import_csv_requested.connect(self.import_employee_from_csv)
        self.view.export_csv_requested.connect(self.export_employee_to_csv)


    def get_view(self):
        """Возвращает виджет представления для отображения."""
        return self.view

    def refresh_list(self):
        """Обновляет список пользователей, вызывая метод модели."""
        if self.model and self.model.load_data():
            QMessageBox.information(self.view, "Обновление", "Список пользователей обновлен.")
        else:
             QMessageBox.critical(self.view, "Ошибка", "Не удалось обновить список пользователей.")


    def add_employee(self):
        """Обрабатывает запрос на добавление нового пользователя."""
        dialog = EmployeeDialog(self.db, parent=self.view) # Pass db connection to dialog for departments
        if dialog.exec_() == QDialog.Accepted:
            if dialog.validate_data(): # Basic UI validation
                data = dialog.get_data()
                success, message = self.model.add_employee(data)
                if success:
                    QMessageBox.information(self.view, "Успех", message)
                    self.refresh_list() # Refresh view after successful add
                else:
                    QMessageBox.critical(self.view, "Ошибка", message)

    def edit_employee(self, row):
        """Обрабатывает запрос на редактирование выбранного пользователя."""
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, выберите пользователя для редактирования.")
             return

        employee_data = self.model.get_employee_data(row)
        if not employee_data:
             QMessageBox.critical(self.view, "Ошибка", "Не удалось получить данные выбранного пользователя.")
             return

        dialog = EmployeeDialog(self.db, employee_data=employee_data, parent=self.view) # Pass db connection and data
        if dialog.exec_() == QDialog.Accepted:
            if dialog.validate_data(): # Basic UI validation
                new_data = dialog.get_data()
                # Ensure the original ID is in new_data for the model to know which row to update
                new_data['id_employee'] = employee_data.get('id_employee')

                success, message = self.model.update_employee(row, new_data)
                if success:
                    QMessageBox.information(self.view, "Успех", message)
                    self.refresh_list() # Refresh view after successful edit
                else:
                    QMessageBox.critical(self.view, "Ошибка", message)


    def delete_employee(self, row):
        """Обрабатывает запрос на удаление выбранного пользователя."""
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, выберите пользователя для удаления.")
             return

        # Get employee info for confirmation message before deleting
        employee_data = self.model.get_employee_data(row)
        employee_id = employee_data.get('id_employee', 'N/A')
        employee_fio = employee_data.get('fio', 'Выбранная запись')

        reply = QMessageBox.question(self.view, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить пользователя '{employee_fio}' (ID: {employee_id})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            success, message = self.model.delete_employee(row)
            if success:
                QMessageBox.information(self.view, "Успех", message)
                self.refresh_list() # Refresh view after successful delete
            else:
                QMessageBox.critical(self.view, "Ошибка", message)

    def import_employee_from_csv(self):
        """Обрабатывает запрос на импорт пользователей из CSV."""
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self.view, "Предупреждение", "Невозможно выполнить импорт: соединение с базой данных отсутствует.")
             return

        file_path, _ = QFileDialog.getOpenFileName(self.view, f"Импорт данных в таблицу '{self.model.table_name}'",
                                                   "",
                                                   "CSV файлы (*.csv);;Все файлы (*)")

        if file_path:
            print(f"Выбран файл для импорта в {self.model.table_name}: {file_path}")
            # Get column names from schema, excluding FK definitions
            all_employee_cols = [col.split()[0] for col in DATABASE_SCHEMA.get(self.model.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

            # Call the utility function
            success, message = import_data_from_csv(self.db, file_path, self.model.table_name, all_employee_cols, column_digits={'id_department': 2})

            if success:
                QMessageBox.information(self.view, "Импорт завершен", message)
                self.refresh_list() # Refresh view after import
            else:
                QMessageBox.critical(self.view, "Ошибка импорта", message)
        else:
            print("Выбор файла отменен.")

    def export_employee_to_csv(self):
        """Обрабатывает запрос на экспорт пользователей в CSV."""
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self.view, "Предупреждение", "Невозможно выполнить экспорт: соединение с базой данных отсутствует.")
             return

        default_filename = f"{self.model.table_name}_export_{QDate.currentDate().toString('yyyyMMdd')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self.view, f"Экспорт данных из таблицы '{self.model.table_name}'", default_filename, "CSV файлы (*.csv);;Все файлы (*)")
        if file_path:
            print(f"Выбран файл для экспорта из {self.model.table_name}: {file_path}")         
            employee_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.model.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
            cols_to_export = employee_col_names_in_schema
            success, message = export_data_to_csv(self.db, file_path, self.model.table_name, cols_to_export)

            if success:
                QMessageBox.information(self.view, "Экспорт завершен", message)
