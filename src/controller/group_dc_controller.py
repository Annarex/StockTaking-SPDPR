
# File: group_dc_controller.py
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog
from PyQt5.QtCore import QDate, QObject # Импортируем QObject

# Импортируем Модель и Вид для групп домена
from src.model.group_dc_model import GroupDCModel
from src.view.group_dc_view import GroupDCView # Импортируем только основной виджет

# Импортируем универсальный обработчик CSV (предполагается, что он доступен)
# Убедитесь, что путь к файлу src/utils/csv_handler.py правильный
from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

# Импортируем схему базы данных (нужна для CSV обработчика и валидации в Модели)
from database import DATABASE_SCHEMA


class GroupDCController(QObject): # Наследуем от QObject для использования сигналов/слотов
    def __init__(self, db_connection):
        """
        Инициализирует контроллер для управления группами домена.
        """
        super().__init__() # Инициализируем QObject

        self.db = db_connection
        # Проверяем соединение с БД при инициализации контроллера
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто. Контроллер групп домена не может быть инициализирован.")
            self.model = None
            self.view = None
            # В реальном приложении можно выбросить исключение или установить флаг ошибки
            return

        # Создаем экземпляр Модели, передавая соединение с БД
        self.model = GroupDCModel(self.db)
        # Создаем экземпляр Вида
        self.view = GroupDCView()

        # Устанавливаем модель данных для вида (таблицы)
        self.view.set_model(self.model.get_model())

        # Подключаем сигналы от Вида к слотам (методам) Контроллера
        self.view.add_item_requested.connect(self.add_group_dc)
        self.view.delete_item_requested.connect(self.delete_group_dc)
        self.view.refresh_list_requested.connect(self.refresh_list)
        self.view.import_csv_requested.connect(self.import_group_dc)
        self.view.export_csv_requested.connect(self.export_group_dc)

        # Подключаем сигнал ошибки от Модели к слоту Контроллера
        self.model.model_error.connect(self.handle_model_error)


    def get_view(self):
        """
        Возвращает виджет представления (GroupDCView) для отображения в главном окне.
        """
        return self.view

    def refresh_list(self):
        """
        Обновляет список групп домена в представлении, вызывая метод модели.
        """
        if self.model and self.model.load_data():
            QMessageBox.information(self.view, "Обновление", "Список групп домена обновлен.")
        else:
             QMessageBox.critical(self.view, "Ошибка", "Не удалось обновить список групп домена.")

    def handle_model_error(self, error_message):
        """
        Обрабатывает ошибки, возникающие в Модели (например, при OnFieldChange).
        Выводит сообщение об ошибке пользователю.
        """
        QMessageBox.critical(self.view, "Ошибка сохранения", f"Не удалось сохранить изменение: {error_message}")
        # После ошибки сохранения при OnFieldChange, модель может быть в некорректном состоянии.
        # Лучше всего перезагрузить данные из БД.
        self.refresh_list()


    def add_group_dc(self):
        """
        Обрабатывает запрос на добавление новой группы домена.
        Получает данные из поля ввода View и передает их в модель.
        """
        item_name = self.view.get_add_input_text() # Получаем текст из поля ввода View

        # Базовая валидация на уровне контроллера (можно дублировать с моделью или оставить только в модели)
        if not item_name:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, введите название группы домена.")
             return

        # Передаем данные в модель для добавления в БД
        success, message = self.model.add_item(item_name)
        if success:
            QMessageBox.information(self.view, "Успех", message)
            self.view.clear_add_input() # Очищаем поле ввода в View после успешного добавления
            self.refresh_list() # Обновляем список в представлении после успешного добавления
        else:
            QMessageBox.critical(self.view, "Ошибка", message)


    # Метод edit_group_dc не нужен, так как редактирование происходит напрямую в таблице
    # благодаря стратегии OnFieldChange в Модели.


    def delete_group_dc(self):
        """
        Обрабатывает запрос на удаление выбранной группы домена.
        Запрашивает подтверждение у пользователя и передает запрос на удаление в модель.
        """
        row = self.view.get_selected_row() # Получаем индекс выбранной строки из View
        if row == -1:
             QMessageBox.warning(self.view, "Предупреждение", "Пожалуйста, выберите группу домена для удаления.")
             return

        # Получаем информацию о группе домена для сообщения подтверждения перед удалением
        # Можно получить данные из модели по индексу строки
        group_dc_data = self.model.get_group_dc_data(row)
        item_id = group_dc_data.get('id_group_dc', 'N/A')
        item_name = group_dc_data.get('group_dc', 'Выбранная запись')


        # Запрашиваем подтверждение у пользователя
        reply = QMessageBox.question(self.view, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить группу домена '{item_name}' (ID: {item_id})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        # Если пользователь подтвердил удаление
        if reply == QMessageBox.Yes:
            # Передаем запрос на удаление в модель
            success, message = self.model.delete_item(row)
            if success:
                QMessageBox.information(self.view, "Успех", message)
                self.refresh_list() # Обновляем список в представлении после успешного удаления
            else:
                QMessageBox.critical(self.view, "Ошибка", message)

    def import_group_dc(self):
        """
        Обрабатывает запрос на импорт групп домена из CSV файла.
        Открывает диалог выбора файла и вызывает функцию импорта из утилит.
        """
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self.view, "Предупреждение", "Невозможно выполнить импорт: соединение с базой данных отсутствует.")
             return

        # Открываем диалог выбора файла (это часть UI, но Контроллер инициирует его)
        file_path, _ = QFileDialog.getOpenFileName(self.view, f"Импорт данных в таблицу '{self.model.table_name}'",
                                                   "",
                                                   "CSV файлы (*.csv);;Все файлы (*)")

        if file_path:
            print(f"Выбран файл для импорта в {self.model.table_name}: {file_path}")
            # Получаем названия столбцов из схемы БД, исключая определения внешних ключей
            all_group_dc_cols = [col.split()[0] for col in DATABASE_SCHEMA.get(self.model.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

            # Вызываем универсальную функцию импорта из CSV утилит
            # Передаем соединение с БД, путь к файлу, имя таблицы, список столбцов,
            # информацию о столбцах с фиксированной длиной (если нужно) и уникальный столбец
            # Для GroupDC ID имеет фиксированную длину 2 символа. Уникальный столбец - group_dc.
            success, message = import_data_from_csv(self.db, file_path, self.model.table_name, all_group_dc_cols, column_digits={'id_group_dc': 2}, unique_column=self.model.unique_column)

            if success:
                QMessageBox.information(self.view, "Импорт завершен", message)
                self.refresh_list() # Обновляем список в представлении после импорта
            else:
                QMessageBox.critical(self.view, "Ошибка импорта", message)
        else:
            print("Выбор файла отменен.")

    def export_group_dc(self):
        """
        Обрабатывает запрос на экспорт групп домена в CSV файл.
        Открывает диалог сохранения файла и вызывает функцию экспорта из утилит.
        """
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
