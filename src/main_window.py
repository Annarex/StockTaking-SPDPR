# ui/main_window.py
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAction, QVBoxLayout, QWidget, QLabel, QMessageBox)
from PyQt5.QtCore import Qt

from src.controller.employee_controller import EmployeeController
from src.controller.departments_controller import DepartmentsController
from src.controller.subcategory_controller import SubcategoryController
# from src.controller.note_controller import NoteController
# from src.controller.units_inventory_controller import UnitsInventoryController # Для новой инвентаризации
# from src.controller.report_controller import ReportController # Для нового отчета
from src.controller._generic_controller import GenericController

from database import close_db

class MainWindow(QMainWindow):
    def __init__(self, db_connection):
        super().__init__()

        self.db = db_connection
        
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
        view_employee_action.triggered.connect(self._open_employee_view)
        manager_menu.addAction(view_employee_action)
        
        manager_menu.addSeparator() # Добавляем разделитель

        departments_action = QAction("Отделы", self)
        departments_action.triggered.connect(self._open_departments_view)
        manager_menu.addAction(departments_action)

        # Группы домена
        group_dc_action = QAction("Группы домена", self)
        group_dc_action.triggered.connect(
            lambda: self._open_generic_view(
                "GroupDC",
                "id_group_dc",
                "group_dc",
                "Управление группами домена",
                "новую группу домена",
                unique_name_column="group_dc"
            )
        )
        manager_menu.addAction(group_dc_action)

        # note_action = QAction("Заметки", self)
        # note_action.triggered.connect(self._open_note_view)
        # manager_menu.addAction(note_action)
        # --- Конец новых пунктов меню ---

        # exit_action = QAction("Выход", self)
        # exit_action.triggered.connect(self.close)
        # manager_menu.addAction(exit_action)

        # Меню "Инвентаризация"
        inventory_menu = menu_bar.addMenu("Инвентаризация")
        # view_inventory_action = QAction("Просмотр инвентаризации", self)
        # view_inventory_action.triggered.connect(self._open_inventory_view)
        # inventory_menu.addAction(view_inventory_action)

     
        subcategory_action = QAction("Категории", self)
        subcategory_action.triggered.connect(
            lambda: self._open_generic_view(
                "Category",
                "id_category",
                "category",
                "Управление категориями",
                "новую категорию",
                unique_name_column="category"
            )
        )
        inventory_menu.addAction(subcategory_action)
        
        # Добавляем пункты меню для каждой из запрошенных таблиц
        subcategory_action = QAction("Подкатегории", self)
        subcategory_action.triggered.connect(self._open_subcategory_view)
        inventory_menu.addAction(subcategory_action)

        unit_type_action = QAction("Типы единиц", self)
        unit_type_action.triggered.connect(
            lambda: self._open_generic_view(
            "UnitType",
            "id_unit_type",
            "unit_type",
            "Управление типами единиц",
            "новый тип единицы",
            unique_name_column="unit_type"
            )
        )
        inventory_menu.addAction(unit_type_action)

        order_status_action = QAction("Статусы заказов", self)
        order_status_action.triggered.connect(
            lambda: self._open_generic_view(
                "OrderStatus",
                "id_order_status",
                "order_status",
                "Управление статусами заказов",
                "новый статус заказа",
                unique_name_column="order_status"
            )
        )
        inventory_menu.addAction(order_status_action)

        # Меню "Отчеты"
        # reports_menu = menu_bar.addMenu("Отчеты")
        # create_report_action = QAction("Сформировать отчет", self)
        # create_report_action.triggered.connect(self._open_report_view)
        # reports_menu.addAction(create_report_action)

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

    def _open_view(self, controller_class,view_title, *args, **kwargs):
        if self.db is None or not self.db.isOpen():
             QMessageBox.warning(self, "Предупреждение", f"Невозможно открыть раздел '{view_title}': соединение с базой данных отсутствует.")
             return

        controller = controller_class(self.db, *args, **kwargs)

        if controller:
            self._clear_layout()

            view_widget = controller.get_view()

            if view_widget:
                print(f"Открыть раздел '{view_title}'")
                self.layout.addWidget(view_widget)
                self._current_view_widget = view_widget # Сохраняем ссылку на текущий виджет
                self._current_controller = controller # Сохраняем ссылку на текущий контроллер
                self.setWindowTitle(f"Система управления инвентаризацией - {view_title}") # Обновляем заголовок окна
            else:
                 QMessageBox.critical(self, "Ошибка", f"Контроллер '{controller_class}' не предоставил виджет представления.")
                 # Если виджет не получен, можно снова показать приветствие или сообщение об ошибке
                 self.welcome_label = QLabel(f"Ошибка загрузки раздела: {view_title}")
                 self.welcome_label.setAlignment(Qt.AlignCenter)
                 self.layout.addWidget(self.welcome_label)

    def _open_generic_view(self, table_name, id_column, name_column, view_title, add_input_placeholder, unique_name_column=None):
       self._open_view(GenericController, view_title, table_name, id_column, name_column, view_title, add_input_placeholder, unique_name_column)
        
    def _open_employee_view(self):
        self._open_view(EmployeeController, "Просмотр сотрудников")

    def _open_departments_view(self):
        self._open_view(DepartmentsController, "Просмотр отделов")
        
    def _open_subcategory_view(self):
        self._open_view(SubcategoryController, "Просмотр категорий")

    def _open_order_status_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Статусы заказов' пока не реализован с использованием контроллера.")
        # self._open_view(OrderStatusController, "Статусы заказов")

    def _open_note_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Заметки' пока не реализован с использованием контроллера.")
        # self._open_view(NoteController, "Заметки")

    def _open_inventory_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Просмотр инвентаризации' пока не реализован с использованием контроллера.")
        # self._open_view(UnitsInventoryController, "Просмотр инвентаризации")

    def _open_report_view(self):
        QMessageBox.information(self, "В разработке", "Раздел 'Отчеты' пока не реализован с использованием контроллера.")
        # self._open_view(ReportController, "Отчеты")

    def closeEvent(self, event):
        print("Закрытие главного окна.")
        if self.db is not None and self.db.isOpen():
             close_db(self.db)
             self.db = None
        event.accept()