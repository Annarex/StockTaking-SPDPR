# ui/main_window.py
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMenuBar, QAction,
                             QVBoxLayout, QWidget, QLabel, QFileDialog,
                             QMessageBox)
from PyQt5.QtCore import Qt
# Импортируем виджеты (убедитесь, что пути правильные относительно папки ui)
# Старые виджеты (пока оставлены с TODO)
from src.view.object_types_view import ObjectTypesView
# from src.view.inventory_view import InventoryView
from src.view.report_view import ReportView
# from src.view.user_view import UsersView
from controller.employees_controller import UserController
from src.view.category_view import CategoryView
from src.view.subcategory_view import SubcategoryView
from src.view.unit_type_view import UnitTypeView
from src.view.order_status_view import OrderStatusView
from src.view.departments_view import DepartmentsView
from src.view.group_dc_view import GroupDCView
from src.view.note_view import NoteView


# Импортируем функции для работы с БД (database.py находится в корне)
from database import connect_db, create_all_tables, close_db # Используем create_all_tables
# Импортируем универсальный обработчик CSV (находится в extension)
from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

# Импортируем схему БД для получения названий таблиц и столбцов
from database import DATABASE_SCHEMA


class MainWindow(QMainWindow):
    def __init__(self, db_connection):
        super().__init__()

        self.db = db_connection
        # Проверяем соединение с БД при инициализации
        if not self.db or not self.db.isOpen():
             QMessageBox.critical(self, "Ошибка базы данных", "Соединение с базой данных не установлено или закрыто.")
             # В зависимости от критичности, можно выйти из приложения
             # sys.exit(1)
             # Если не выходим, функционал, зависящий от БД, не будет работать
             pass


        self.setWindowTitle("Система управления инвентаризацией")
        self.setGeometry(100, 100, 800, 600)

        # Центральный виджет, который будет содержать текущее представление
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0) # Убираем отступы вокруг центрального виджета

        # Изначально показываем приветственное сообщение
        self.welcome_label = QLabel("Добро пожаловать в систему управления инвентаризацией!")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.welcome_label)

        # Переменная для хранения ссылки на текущий активный виджет представления
        self._current_view = None
        self._current_view_widget = None
        self._current_controller = None
        
        self._create_menu_bar()

    def _create_menu_bar(self):
        """Создает строку меню приложения."""
        menu_bar = self.menuBar()
        manager_menu = menu_bar.addMenu("Управление")        

        view_employees_action = QAction("Сотрудники", self)
        view_employees_action.triggered.connect(self._open_empoyees_view)
        manager_menu.addAction(view_employees_action)
        
        manager_menu.addSeparator() # Добавляем разделитель

        departments_action = QAction("Отделы", self)
        departments_action.triggered.connect(self._open_departments_view)
        manager_menu.addAction(departments_action)

        group_dc_action = QAction("Группы домена", self)
        group_dc_action.triggered.connect(self._open_group_dc_view)
        manager_menu.addAction(group_dc_action)

        note_action = QAction("Заметки", self)
        note_action.triggered.connect(self._open_note_view)
        manager_menu.addAction(note_action)
        # --- Конец новых пунктов меню ---

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        manager_menu.addAction(exit_action)

        # Меню "Инвентаризация"
        inventory_menu = menu_bar.addMenu("Инвентаризация")

        # Пункт меню для просмотра инвентаризации (пока ведет на старый InventoryView)
        # TODO: Обновить для использования нового UnitsInventoryView, когда он будет создан
        # view_inventory_action = QAction("Просмотр инвентаризации", self)
        # view_inventory_action.triggered.connect(self._open_inventory_view)
        # inventory_menu.addAction(view_inventory_action)

        # --- НОВЫЕ ПУНКТЫ МЕНЮ ДЛЯ ТАБЛИЦ ---
        # Добавляем пункты меню для каждой из запрошенных таблиц
        category_action = QAction("Категории", self)
        category_action.triggered.connect(self._open_category_view)
        inventory_menu.addAction(category_action)

        subcategory_action = QAction("Подкатегории", self)
        subcategory_action.triggered.connect(self._open_subcategory_view)
        inventory_menu.addAction(subcategory_action)

        unit_type_action = QAction("Типы единиц", self)
        unit_type_action.triggered.connect(self._open_unit_type_view)
        inventory_menu.addAction(unit_type_action)

        order_status_action = QAction("Статусы заказов", self)
        order_status_action.triggered.connect(self._open_order_status_view)
        inventory_menu.addAction(order_status_action)


        # Старый пункт меню для типов объектов (можно удалить после перехода на новую структуру)
        object_types_action = QAction("Типы объектов (старое)", self)
        object_types_action.triggered.connect(self._open_object_types_view)
        # inventory_menu.addAction(object_types_action) # Закомментировано/удалено

        # Меню "Отчеты"
        reports_menu = menu_bar.addMenu("Отчеты")
        # Пункт меню для формирования отчета (пока ведет на старый ReportView)
        # TODO: Обновить для использования нового ReportView, когда он будет адаптирован к новой БД
        create_report_action = QAction("Сформировать отчет", self)
        create_report_action.triggered.connect(self._open_report_view)
        reports_menu.addAction(create_report_action)

    def _clear_layout(self):
        """Удаляет все виджеты из центрального макета."""
        # Удаляем текущий виджет представления, если он есть
        if self._current_view is not None:
            self.layout.removeWidget(self._current_view)
            self._current_view.deleteLater() # Безопасное удаление виджета
            self._current_view = None
        # Также удаляем приветственную надпись, если она еще отображается
        # Проверяем, что welcome_label существует и является дочерним элементом central_widget
        if hasattr(self, 'welcome_label') and self.welcome_label is not None and self.welcome_label.parent() == self.central_widget:
             self.layout.removeWidget(self.welcome_label)
             self.welcome_label.deleteLater()
             self.welcome_label = None # Обнуляем ссылку после удаления


    # --- Методы открытия разделов ---

    # Метод для открытия раздела категорий
    def _open_category_view(self):
        self._clear_layout() # Очищаем предыдущий виджет
        print("Открыть раздел 'Категории'")
        # Проверяем соединение с БД перед созданием виджета
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self, "Предупреждение", "Невозможно открыть раздел: соединение с базой данных отсутствует.")
             return
        category_view = CategoryView(self.db) # Передаем соединение с БД
        self.layout.addWidget(category_view)
        self._current_view = category_view # Сохраняем ссылку на текущий виджет

    # Метод для открытия раздела подкатегорий
    def _open_subcategory_view(self):
        self._clear_layout()
        print("Открыть раздел 'Подкатегории'")
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self, "Предупреждение", "Невозможно открыть раздел: соединение с базой данных отсутствует.")
             return
        subcategory_view = SubcategoryView(self.db)
        self.layout.addWidget(subcategory_view)
        self._current_view = subcategory_view

    # Метод для открытия раздела типов единиц
    def _open_unit_type_view(self):
        self._clear_layout()
        print("Открыть раздел 'Типы единиц'")
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self, "Предупреждение", "Невозможно открыть раздел: соединение с базой данных отсутствует.")
             return
        unit_type_view = UnitTypeView(self.db)
        self.layout.addWidget(unit_type_view)
        self._current_view = unit_type_view

    # Метод для открытия раздела статусов заявок
    def _open_order_status_view(self):
        self._clear_layout()
        print("Открыть раздел 'Статусы заявок'")
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self, "Предупреждение", "Невозможно открыть раздел: соединение с базой данных отсутствует.")
             return
        order_status_view = OrderStatusView(self.db)
        self.layout.addWidget(order_status_view)
        self._current_view = order_status_view

    # Метод для открытия раздела отделов
    def _open_departments_view(self):
        self._clear_layout()
        print("Открыть раздел 'Отделы'")
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self, "Предупреждение", "Невозможно открыть раздел: соединение с базой данных отсутствует.")
             return
        departments_view = DepartmentsView(self.db)
        self.layout.addWidget(departments_view)
        self._current_view = departments_view

    # Метод для открытия раздела групп домена
    def _open_group_dc_view(self):
        self._clear_layout()
        print("Открыть раздел 'Группы домена'")
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self, "Предупреждение", "Невозможно открыть раздел: соединение с базой данных отсутствует.")
             return
        group_dc_view = GroupDCView(self.db)
        self.layout.addWidget(group_dc_view)
        self._current_view = group_dc_view

    # Метод для открытия раздела заметок
    def _open_note_view(self):
        self._clear_layout()
        print("Открыть раздел 'Заметки'")
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self, "Предупреждение", "Невозможно открыть раздел: соединение с базой данных отсутствует.")
             return
        note_view = NoteView(self.db)
        self.layout.addWidget(note_view)
        self._current_view = note_view

    def _open_inventory_view(self):
        self._clear_layout()
        print("Открыть раздел 'Просмотр инвентаризации' (старый)")
        # # TODO: Заменить на UnitsInventoryView
        # inventory_view = InventoryView(self.db)
        # self.layout.addWidget(inventory_view)
        # self._current_view = inventory_view

    def _open_object_types_view(self):
        self._clear_layout()
        print("Открыть раздел 'Типы объектов' (старый)")
        # TODO: Удалить или заменить на CategoryView/SubcategoryView
        object_types_view = ObjectTypesView(self.db)
        self.layout.addWidget(object_types_view)
        self._current_view = object_types_view

    def _open_report_view(self):
        self._clear_layout()
        print("Открыть раздел 'Отчеты' (старый)")
        # TODO: Заменить на новый ReportView, адаптированный к новой БД
        report_view = ReportView(self.db)
        self.layout.addWidget(report_view)
        self._current_view = report_view

    def _open_empoyees_view(self):
        self._clear_layout()
        print("Открыть раздел 'Просмотр сотрудников'")
        employees_view = UserController(self.db)
        self.layout.addWidget(employees_view)
        self._current_view = employees_view

    def closeEvent(self, event):
        # Этот метод вызывается при закрытии окна
        print("Закрытие главного окна.")
        # Здесь можно добавить сохранение настроек и т.д.
        event.accept()


# --- Запуск приложения (остается в app.py) ---
# Код запуска находится в app.py и был изменен ранее для подключения к БД и логина
