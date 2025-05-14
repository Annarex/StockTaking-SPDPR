# ui/main_window.py
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMenuBar, QAction,
                             QVBoxLayout, QWidget, QLabel, QFileDialog,
                             QMessageBox)
from PyQt5.QtCore import Qt
# Импортируем виджеты (убедитесь, что пути правильные относительно папки ui)
# Старые виджеты (пока оставлены с TODO)
# from src.view.object_types_view import ObjectTypesView
# from src.view.inventory_view import InventoryView
# from src.view.report_view import ReportView
# from src.view.user_view import UsersView
# from src.view.category_view import CategoryView
# from src.view.subcategory_view import SubcategoryView
# from src.view.unit_type_view import UnitTypeView
# from src.view.order_status_view import OrderStatusView
# from src.view.departments_view import DepartmentsView
# from src.view.group_dc_view import GroupDCView
# from src.view.note_view import NoteView

from controller.employee_controller import UserController
# from src.controller.category_controller import CategoryController
# from src.controller.subcategory_controller import SubcategoryController
# from src.controller.unit_type_controller import UnitTypeController
# from src.controller.order_status_controller import OrderStatusController
# from src.controller.departments_controller import DepartmentsController
# from src.controller.group_dc_controller import GroupDCController
# from src.controller.note_controller import NoteController
# from src.controller.units_inventory_controller import UnitsInventoryController # Для новой инвентаризации
# from src.controller.report_controller import ReportController # Для нового отчета


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

        view_employee_action = QAction("Сотрудники", self)
        view_employee_action.triggered.connect(self._open_empoyees_view)
        manager_menu.addAction(view_employee_action)
        
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
        # view_inventory_action = QAction("Просмотр инвентаризации", self)
        # view_inventory_action.triggered.connect(self._open_inventory_view)
        # inventory_menu.addAction(view_inventory_action)

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

        # Меню "Отчеты"
        reports_menu = menu_bar.addMenu("Отчеты")
        create_report_action = QAction("Сформировать отчет", self)
        create_report_action.triggered.connect(self._open_report_view)
        reports_menu.addAction(create_report_action)

    def _clear_layout(self):
        """Удаляет все виджеты из центрального макета."""
        if self._current_view_widget is not None:
            self.layout.removeWidget(self._current_view_widget)
            self._current_view_widget.deleteLater()
            self._current_view_widget = None
            self._current_controller = None

        # Проверяем, что welcome_label существует и является дочерним элементом central_widget
        if hasattr(self, 'welcome_label') and self.welcome_label is not None and self.welcome_label.parent() == self.central_widget:
             self.layout.removeWidget(self.welcome_label)
             self.welcome_label.deleteLater()
             self.welcome_label = None

    def _get_controller(self, controller_class, controller_key):
        """ Возвращает экземпляр контроллера из кеша или создает новый. """
        if controller_key not in self._controllers:
            if self.db is None or not self.db.isOpen():
                 QMessageBox.warning(self, "Предупреждение", f"Невозможно открыть раздел: соединение с базой данных отсутствует.")
                 return None
            try:
                # Создаем экземпляр контроллера, передавая соединение с БД
                controller_instance = controller_class(self.db)
                self._controllers[controller_key] = controller_instance
                print(f"Создан экземпляр контроллера: {controller_key}")
            except Exception as e:
                print(f"Ошибка при создании контроллера {controller_key}: {e}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось инициализировать раздел '{controller_key}'.")
                return None
        else:
            print(f"Используется существующий экземпляр контроллера: {controller_key}")

        return self._controllers.get(controller_key)
       
    def _open_view(self, controller_class, controller_key, view_title):
        """ Универсальный метод для открытия представления через контроллер."""
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self, "Предупреждение", f"Невозможно открыть раздел '{view_title}': соединение с базой данных отсутствует.")
             return

        controller = self._get_controller(controller_class, controller_key)

        if controller:
            # Очищаем предыдущий виджет
            self._clear_layout()

            # Получаем виджет представления от контроллера
            view_widget = controller.get_view()

            if view_widget:
                print(f"Открыть раздел '{view_title}'")
                self.layout.addWidget(view_widget)
                self._current_view_widget = view_widget # Сохраняем ссылку на текущий виджет
                self._current_controller = controller # Сохраняем ссылку на текущий контроллер
                self.setWindowTitle(f"Система управления инвентаризацией - {view_title}") # Обновляем заголовок окна
            else:
                 QMessageBox.critical(self, "Ошибка", f"Контроллер '{controller_key}' не предоставил виджет представления.")
                 # Если виджет не получен, можно снова показать приветствие или сообщение об ошибке
                 self.welcome_label = QLabel(f"Ошибка загрузки раздела: {view_title}")
                 self.welcome_label.setAlignment(Qt.AlignCenter)
                 self.layout.addWidget(self.welcome_label)

# --- Методы открытия разделов (теперь используют _open_view) ---

    def _open_user_view(self):
        self._open_view(UserController, "user_controller", "Просмотр сотрудников")

    def _open_category_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Категории' пока не реализован с использованием контроллера.")
        # self._open_view(CategoryController, "category_controller", "Категории")

    def _open_subcategory_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Подкатегории' пока не реализован с использованием контроллера.")
        # self._open_view(SubcategoryController, "subcategory_controller", "Подкатегории")

    def _open_unit_type_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Типы единиц' пока не реализован с использованием контроллера.")
        # self._open_view(UnitTypeController, "unit_type_controller", "Типы единиц")

    def _open_order_status_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Статусы заказов' пока не реализован с использованием контроллера.")
        # self._open_view(OrderStatusController, "order_status_controller", "Статусы заказов")

    def _open_departments_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Отделы' пока не реализован с использованием контроллера.")
        # self._open_view(DepartmentsController, "departments_controller", "Отделы")

    def _open_group_dc_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Группы домена' пока не реализован с использованием контроллера.")
        # self._open_view(GroupDCController, "group_dc_controller", "Группы домена")

    def _open_note_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Заметки' пока не реализован с использованием контроллера.")
        # self._open_view(NoteController, "note_controller", "Заметки")

    def _open_inventory_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Просмотр инвентаризации' пока не реализован с использованием контроллера.")
        # self._open_view(UnitsInventoryController, "units_inventory_controller", "Просмотр инвентаризации")

    def _open_report_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Отчеты' пока не реализован с использованием контроллера.")
        # self._open_view(ReportController, "report_controller", "Отчеты")

    def closeEvent(self, event):
        print("Закрытие главного окна.")
        if self.db is not None and self.db.isOpen():
             close_db(self.db)
             self.db = None
        event.accept()