# File: departments_controller.py
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog
from PyQt5.QtCore import QDate

# Импортируем Модель и Вид для отделов
from src.model.departments_model import DepartmentsModel
from src.view.departments_view import DepartmentsView, DepartmentDialog # Импортируем как основной виджет, так и диалог

# Импортируем универсальный обработчик CSV (предполагается, что он доступен)
# Убедитесь, что путь к файлу src/utils/csv_handler.py правильный
from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

# Импортируем схему базы данных (нужна для CSV обработчика и валидации в Модели)
from database import DATABASE_SCHEMA


class DepartmentsController:
    def __init__(self, db_connection):
        """
        Инициализирует контроллер для управления отделами.
        """
        self.db = db_connection
        # Проверяем соединение с БД при инициализации контроллера
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто. Контроллер отделов не может быть инициализирован.")
            self.model = None
            self.view = None
            # В реальном приложении можно выбросить исключение или установить флаг ошибки
            return

        # Создаем экземпляр Модели, передавая соединение с БД
        self.model = DepartmentsModel(self.db)
        # Создаем экземпляр Вида
        self.view = DepartmentsView()

        # Устанавливаем модель данных для вида (таблицы)
        self.view.set_model(self.model.get_model())

        # Подключаем сигналы от Вида к слотам (методам) Контроллера
        self.view.add_department_requested.connect(self.add_department)
        self.view.edit_department_requested.connect(self.edit_department)
        self.view.delete_department_requested.connect(self.delete_department)
        self.view.refresh_list_requested.connect(self.refresh_list)
        self.view.import_csv_requested.connect(self.import_departments_from_csv)
        self.view.export_csv_requested.connect(self.export_departments_to_csv)


    def get_view(self):
        """
        Возвращает виджет представления (DepartmentsView) для отображения в главном окне.
        """
        return self.view

    def refresh_list(self):
        """
        Обновляет список отделов в представлении, вызывая метод модели.
        """
        if self.model and self.model.load_data():
            QMessageBox.information(self.view, "Обновление", "Список отделов обновлен.")
        else:
             QMessageBox.critical(self.view, "Ошибка", "Не удалось обновить список отделов.")


    def add_department(self):
        """
        Обрабатывает запрос на добавление нового отдела.
        Открывает диалог добавления, получает данные и передает их в модель.
        """
        # Создаем диалог добавления
        dialog = DepartmentDialog(parent=self.view)
        # Показываем диалог как модальный
        if dialog.exec_() == QDialog.Accepted:
            # Если пользователь нажал OK и данные прошли базовую валидацию в диалоге
            if dialog.validate_data():
                data = dialog.get_data() # Получаем данные из диалога
                # Передаем данные в модель для добавления в БД
                success, message = self.model.add_department(data)
                if success:
                    QMessageBox.information(self.view, "Успех", message)
                    self.refresh_list() # Обновляем список в представлении после успешного добавления
                else:
                    QMessageBox.critical(self.view, "Ошибка", message)

    def edit_department(self, row):
        """
        Обрабатывает запрос на редактирование выбранного отдела.
        Открывает диалог редактирования с текущими данными и передает обновленные данные в модель.
        Принимает индекс строки для редактирования.
        """
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, выберите отдел для редактирования.")
             return

        # Получаем текущие данные отдела из модели по индексу строки
        department_data = self.model.get_department_data(row)
        if not department_data:
             QMessageBox.critical(self.view, "Ошибка", "Не удалось получить данные выбранного отдела.")
             return

        # Создаем диалог редактирования, передавая текущие данные
        dialog = DepartmentDialog(department_data=department_data, parent=self.view)
        # Показываем диалог как модальный
        if dialog.exec_() == QDialog.Accepted:
            # Если пользователь нажал OK и данные прошли базовую валидацию в диалоге
            if dialog.validate_data():
                new_data = dialog.get_data() # Получаем обновленные данные из диалога
                # Добавляем ID отдела к данным, чтобы модель знала, какую запись обновлять
                new_data['id_department'] = department_data.get('id_department')
                # Передаем обновленные данные и индекс строки в модель для обновления в БД
                success, message = self.model.update_department(row, new_data)
                if success:
                    QMessageBox.information(self.view, "Успех", message)
                    self.refresh_list() # Обновляем список в представлении после успешного редактирования
                else:
                    QMessageBox.critical(self.view, "Ошибка", message)


    def delete_department(self, row):
        """
        Обрабатывает запрос на удаление выбранного отдела.
        Запрашивает подтверждение у пользователя и передает запрос на удаление в модель.
        Принимает индекс строки для удаления.
        """
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, выберите отдел для удаления.")
             return

        # Получаем информацию об отделе для сообщения подтверждения перед удалением
        department_data = self.model.get_department_data(row)
        item_id = department_data.get('id_department', 'N/A')
        item_name = department_data.get('department_fullname', 'Выбранная запись')

        # Запрашиваем подтверждение у пользователя
        reply = QMessageBox.question(self.view, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить отдел '{item_name}' (ID: {item_id})?\n"
                                     "Пользователи, связанные с этим отделом, потеряют свой отдел.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        # Если пользователь подтвердил удаление
        if reply == QMessageBox.Yes:
            # Передаем запрос на удаление в модель
            success, message = self.model.delete_department(row)
            if success:
                QMessageBox.information(self.view, "Успех", message)
                self.refresh_list() # Обновляем список в представлении после успешного удаления
            else:
                QMessageBox.critical(self.view, "Ошибка", message)

    def import_departments_from_csv(self):
        """
        Обрабатывает запрос на импорт отделов из CSV файла.
        Открывает диалог выбора файла и вызывает функцию импорта из утилит.
        """
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self.view, "Предупреждение", "Невозможно выполнить импорт: соединение с базой данных отсутствует.")
             return

        # Открываем диалог выбора файла
        file_path, _ = QFileDialog.getOpenFileName(self.view, f"Импорт данных в таблицу '{self.model.table_name}'",
                                                   "",
                                                   "CSV файлы (*.csv);;Все файлы (*)")

        if file_path:
            print(f"Выбран файл для импорта в {self.model.table_name}: {file_path}")
            # Получаем названия столбцов из схемы БД, исключая определения внешних ключей
            all_department_cols = [col.split()[0] for col in DATABASE_SCHEMA.get(self.model.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

            # Вызываем универсальную функцию импорта из CSV утилит
            # Передаем соединение с БД, путь к файлу, имя таблицы, список столбцов,
            # информацию о столбцах с фиксированной длиной (если нужно) и уникальный столбец
            # Для отделов ID автоинкрементный, поэтому не указываем column_digits для ID.
            # Уникальный столбец - department_fullname.
            success, message = import_data_from_csv(self.db, file_path, self.model.table_name, all_department_cols, unique_column=self.model.unique_column)

            if success:
                QMessageBox.information(self.view, "Импорт завершен", message)
                self.refresh_list() # Обновляем список в представлении после импорта
            else:
                QMessageBox.critical(self.view, "Ошибка импорта", message)
        else:
            print("Выбор файла отменен.")

    def export_departments_to_csv(self):
        """
        Обрабатывает запрос на экспорт отделов в CSV файл.
        Открывает диалог сохранения файла и вызывает функцию экспорта из утилит.
        """
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self.view, "Предупреждение", "Невозможно выполнить экспорт: соединение с базой данных отсутствует.")
             return

        # Предлагаем имя файла по умолчанию
        default_filename = f"{self.model.table_name}_export_{QDate.currentDate().toString('yyyyMMdd')}.csv"
        # Открываем диалог сохранения файла
        file_path, _ = QFileDialog.getSaveFileName(self.view, f"Экспорт данных из таблицы '{self.model.table_name}'", default_filename, "CSV файлы (*.csv);;Все файлы (*)")
        if file_path:
            print(f"Выбран файл для экспорта из {self.model.table_name}: {file_path}")
            # Получаем названия столбцов из схемы БД, которые нужно экспортировать
            department_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.model.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
            cols_to_export = department_col_names_in_schema

            # Вызываем универсальную функцию экспорта в CSV утилит
            success, message = export_data_to_csv(self.db, file_path, self.model.table_name, cols_to_export)

            if success:
                QMessageBox.information(self.view, "Экспорт завершен", message)
                print(f"Экспорт сохранен: {file_path}")
            else:
                QMessageBox.critical(self.view, "Ошибка экспорта", message)
        else:
            print("Сохранение отчета отменено.")

