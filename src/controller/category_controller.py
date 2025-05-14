# File: category_controller.py
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog
from PyQt5.QtCore import QDate

from category_model import CategoryModel
from ui.category_view import CategoryView, CategoryDialog # Import both View components
from src.utils.csv_handler import import_data_from_csv, export_data_to_csv # Assuming these are available
from database import DATABASE_SCHEMA # Need schema for CSV handler


class CategoryController:
    def __init__(self, db_connection):
        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто. Контроллер категорий не может быть инициализирован.")
            self.model = None
            self.view = None
            return

        self.model = CategoryModel(self.db)
        self.view = CategoryView()

        # Set the model for the view
        self.view.set_model(self.model.get_model())

        # Connect signals from the View to slots in the Controller
        self.view.add_category_requested.connect(self.add_category)
        self.view.edit_category_requested.connect(self.edit_category)
        self.view.delete_category_requested.connect(self.delete_category)
        self.view.refresh_list_requested.connect(self.refresh_list)
        self.view.import_csv_requested.connect(self.import_categories_from_csv)
        self.view.export_csv_requested.connect(self.export_categories_to_csv)


    def get_view(self):
        """Возвращает виджет представления для отображения."""
        return self.view

    def refresh_list(self):
        """Обновляет список категорий, вызывая метод модели."""
        if self.model and self.model.load_data():
            QMessageBox.information(self.view, "Обновление", "Список категорий обновлен.")
        else:
             QMessageBox.critical(self.view, "Ошибка", "Не удалось обновить список категорий.")


    def add_category(self):
        """Обрабатывает запрос на добавление новой категории."""
        dialog = CategoryDialog(parent=self.view)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.validate_data(): # Basic UI validation
                data = dialog.get_data()
                success, message = self.model.add_category(data)
                if success:
                    QMessageBox.information(self.view, "Успех", message)
                    self.refresh_list() # Refresh view after successful add
                else:
                    QMessageBox.critical(self.view, "Ошибка", message)

    def edit_category(self, row):
        """Обрабатывает запрос на редактирование выбранной категории."""
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, выберите категорию для редактирования.")
             return

        category_data = self.model.get_category_data(row)
        if not category_data:
             QMessageBox.critical(self.view, "Ошибка", "Не удалось получить данные выбранной категории.")
             return

        dialog = CategoryDialog(category_data=category_data, parent=self.view)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.validate_data(): # Basic UI validation
                new_data = dialog.get_data()
                # The model's update_category method uses the row index,
                # but passing the original ID might be useful for validation within the model.
                # However, the current model update logic relies on the row index.
                # Let's stick to passing the new data and the row index.
                success, message = self.model.update_category(row, new_data)
                if success:
                    QMessageBox.information(self.view, "Успех", message)
                    self.refresh_list() # Refresh view after successful edit
                else:
                    QMessageBox.critical(self.view, "Ошибка", message)


    def delete_category(self, row):
        """Обрабатывает запрос на удаление выбранной категории."""
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, выберите категорию для удаления.")
             return

        # Get category info for confirmation message before deleting
        category_data = self.model.get_category_data(row)
        item_id = category_data.get('id_category', 'N/A')
        item_name = category_data.get('category', 'Выбранная запись')

        reply = QMessageBox.question(self.view, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить категорию '{item_name}' (ID: {item_id})?\n"
                                     "Объекты инвентаризации и подкатегории, связанные с этой категорией, потеряют свою категорию.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            success, message = self.model.delete_category(row)
            if success:
                QMessageBox.information(self.view, "Успех", message)
                self.refresh_list() # Refresh view after successful delete
            else:
                QMessageBox.critical(self.view, "Ошибка", message)

    def import_categories_from_csv(self):
        """Обрабатывает запрос на импорт категорий из CSV."""
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self.view, "Предупреждение", "Невозможно выполнить импорт: соединение с базой данных отсутствует.")
             return

        file_path, _ = QFileDialog.getOpenFileName(self.view, f"Импорт данных в таблицу '{self.model.table_name}'",
                                                   "",
                                                   "CSV файлы (*.csv);;Все файлы (*)")

        if file_path:
            print(f"Выбран файл для импорта в {self.model.table_name}: {file_path}")
            # Get column names from schema, excluding FK definitions
            all_category_cols = [col.split()[0] for col in DATABASE_SCHEMA.get(self.model.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

            # Call the utility function
            # Assuming column_digits={'id_category': 2} is needed for validation during import
            success, message = import_data_from_csv(self.db, file_path, self.model.table_name, all_category_cols, column_digits={'id_category': 2}, unique_column=self.model.unique_column)

            if success:
                QMessageBox.information(self.view, "Импорт завершен", message)
                self.refresh_list() # Refresh view after import
            else:
                QMessageBox.critical(self.view, "Ошибка импорта", message)
        else:
            print("Выбор файла отменен.")

    def export_categories_to_csv(self):
        """Обрабатывает запрос на экспорт категорий в CSV."""
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self.view, "Предупреждение", "Невозможно выполнить экспорт: соединение с базой данных отсутствует.")
             return

        default_filename = f"{self.model.table_name}_export_{QDate.currentDate().toString('yyyyMMdd')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self.view, f"Экспорт данных из таблицы '{self.model.table_name}'", default_filename, "CSV файлы (*.csv);;Все файлы (*)")
        if file_path:
            print(f"Выбран файл для экспорта из {self.model.table_name}: {file_path}")
            # Get column names from schema, excluding FK definitions
            category_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.model.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
            cols_to_export = category_col_names_in_schema

            # Call the utility function
            success, message = export_data_to_csv(self.db, file_path, self.model.table_name, cols_to_export)

            if success:
                QMessageBox.information(self.view, "Экспорт завершен", message)
                print(f"Экспорт сохранен: {file_path}")
            else:
                QMessageBox.critical(self.view, "Ошибка экспорта", message)
        else:
            print("Сохранение отчета отменено.")

