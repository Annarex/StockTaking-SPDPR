# File: subcategory_controller.py
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog
from PyQt5.QtCore import QDate

# Импортируем Модель и Вид для подкатегорий
from src.model.subcategory_model import SubcategoryModel
from src.view.subcategory_view import SubcategoryView, SubcategoryDialog

# Импортируем универсальный обработчик CSV (предполагается, что он доступен)
# Убедитесь, что путь к файлу csv_handler.py правильный
from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

# Импортируем схему базы данных (нужна для CSV обработчика и валидации в Модели)
from database import DATABASE_SCHEMA


class SubcategoryController:
    def __init__(self, db_connection):
        """
        Инициализирует контроллер для управления подкатегориями.
        """
        self.db = db_connection
        # Проверяем соединение с БД при инициализации контроллера
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто. Контроллер подкатегорий не может быть инициализирован.")
            self.model = None
            self.view = None
            # В реальном приложении можно выбросить исключение или установить флаг ошибки
            return

        # Создаем экземпляр Модели, передавая соединение с БД
        self.model = SubcategoryModel(self.db)
        # Создаем экземпляр Вида
        self.view = SubcategoryView()

        # Устанавливаем модель данных для вида (таблицы)
        self.view.set_model(self.model.get_model())

        # Подключаем сигналы от Вида к слотам (методам) Контроллера
        self.view.add_subcategory_requested.connect(self.add_subcategory)
        self.view.edit_subcategory_requested.connect(self.edit_subcategory)
        self.view.delete_subcategory_requested.connect(self.delete_subcategory)
        self.view.refresh_list_requested.connect(self.refresh_list)
        self.view.import_csv_requested.connect(self.import_subcategories_from_csv)
        self.view.export_csv_requested.connect(self.export_subcategories_to_csv)


    def get_view(self):
        """
        Возвращает виджет представления (SubcategoryView) для отображения в главном окне.
        """
        return self.view

    def refresh_list(self):
        """
        Обновляет список подкатегорий в представлении, вызывая метод модели.
        """
        if self.model and self.model.load_data():
            QMessageBox.information(self.view, "Обновление", "Список подкатегорий обновлен.")
        else:
             QMessageBox.critical(self.view, "Ошибка", "Не удалось обновить список подкатегорий.")


    def add_subcategory(self):
        """
        Обрабатывает запрос на добавление новой подкатегории.
        Открывает диалог добавления, получает данные и передает их в модель.
        """
        # Создаем диалог добавления, передавая соединение с БД для заполнения комбобокса категорий
        dialog = SubcategoryDialog(self.db, parent=self.view)
        # Показываем диалог как модальный
        if dialog.exec_() == QDialog.Accepted:
            # Если пользователь нажал OK и данные прошли базовую валидацию в диалоге
            if dialog.validate_data():
                data = dialog.get_data() # Получаем данные из диалога
                # Передаем данные в модель для добавления в БД
                success, message = self.model.add_subcategory(data)
                if success:
                    QMessageBox.information(self.view, "Успех", message)
                    self.refresh_list() # Обновляем список в представлении после успешного добавления
                else:
                    QMessageBox.critical(self.view, "Ошибка", message)

    def edit_subcategory(self, row):
        """
        Обрабатывает запрос на редактирование выбранной подкатегории.
        Открывает диалог редактирования с текущими данными и передает обновленные данные в модель.
        Принимает индекс строки для редактирования.
        """
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, выберите подкатегорию для редактирования.")
             return

        # Получаем текущие данные подкатегории из модели по индексу строки
        subcategory_data = self.model.get_subcategory_data(row)
        if not subcategory_data:
             QMessageBox.critical(self.view, "Ошибка", "Не удалось получить данные выбранной подкатегории.")
             return

        # Создаем диалог редактирования, передавая соединение с БД и текущие данные
        dialog = SubcategoryDialog(self.db, subcategory_data=subcategory_data, parent=self.view)
        # Показываем диалог как модальный
        if dialog.exec_() == QDialog.Accepted:
            # Если пользователь нажал OK и данные прошли базовую валидацию в диалоге
            if dialog.validate_data():
                new_data = dialog.get_data() # Получаем обновленные данные из диалога
                # Передаем обновленные данные и индекс строки в модель для обновления в БД
                success, message = self.model.update_subcategory(row, new_data)
                if success:
                    QMessageBox.information(self.view, "Успех", message)
                    self.refresh_list() # Обновляем список в представлении после успешного редактирования
                else:
                    QMessageBox.critical(self.view, "Ошибка", message)


    def delete_subcategory(self, row):
        """
        Обрабатывает запрос на удаление выбранной подкатегории.
        Запрашивает подтверждение у пользователя и передает запрос на удаление в модель.
        Принимает индекс строки для удаления.
        """
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, выберите подкатегорию для удаления.")
             return

        # Получаем информацию о подкатегории для сообщения подтверждения перед удалением
        subcategory_data = self.model.get_subcategory_data(row)
        item_id = subcategory_data.get('id_subcategory', 'N/A')
        item_name = subcategory_data.get('subcategory', 'Выбранная запись')

        # Запрашиваем подтверждение у пользователя
        reply = QMessageBox.question(self.view, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить подкатегорию '{item_name}' (ID: {item_id})?\n"
                                     "Объекты инвентаризации, связанные с этой подкатегорией, потеряют свою подкатегорию.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        # Если пользователь подтвердил удаление
        if reply == QMessageBox.Yes:
            # Передаем запрос на удаление в модель
            success, message = self.model.delete_subcategory(row)
            if success:
                QMessageBox.information(self.view, "Успех", message)
                self.refresh_list() # Обновляем список в представлении после успешного удаления
            else:
                QMessageBox.critical(self.view, "Ошибка", message)

    def import_subcategories_from_csv(self):
        """
        Обрабатывает запрос на импорт подкатегорий из CSV файла.
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
            all_subcategory_cols = [col.split()[0] for col in DATABASE_SCHEMA.get(self.model.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

            # Вызываем универсальную функцию импорта из CSV утилит
            # Передаем соединение с БД, путь к файлу, имя таблицы, список столбцов,
            # информацию о столбцах с фиксированной длиной (если нужно) и уникальный столбец
            success, message = import_data_from_csv(self.db, file_path, self.model.table_name, all_subcategory_cols, column_digits={'id_subcategory': 2}, unique_column=self.model.unique_column)

            if success:
                QMessageBox.information(self.view, "Импорт завершен", message)
                self.refresh_list() # Обновляем список в представлении после импорта
            else:
                QMessageBox.critical(self.view, "Ошибка импорта", message)
        else:
            print("Выбор файла отменен.")

    def export_subcategories_to_csv(self):
        """
        Обрабатывает запрос на экспорт подкатегорий в CSV файл.
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
            subcategory_col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.model.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
            cols_to_export = subcategory_col_names_in_schema

            # Вызываем универсальную функцию экспорта в CSV утилит
            success, message = export_data_to_csv(self.db, file_path, self.model.table_name, cols_to_export)

            if success:
                QMessageBox.information(self.view, "Экспорт завершен", message)
                print(f"Экспорт сохранен: {file_path}")
            else:
                QMessageBox.critical(self.view, "Ошибка экспорта", message)
        else:
            print("Сохранение отчета отменено.")