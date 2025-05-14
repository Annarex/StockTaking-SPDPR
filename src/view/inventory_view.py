# ui/inventory_view.py
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLineEdit, QLabel, QDialog,
                             QDialogButtonBox, QMessageBox, QComboBox,
                             QFormLayout, QDateEdit, QTextEdit) # Добавляем QTextEdit
from PyQt5.QtSql import QSqlTableModel, QSqlQuery, QSqlDatabase, QSqlRelation, QSqlRelationalTableModel, QSqlError # Используем QSqlRelationalTableModel
from PyQt5.QtCore import Qt, QModelIndex, QDate, QVariant # Добавляем QVariant

# Импортируем схему базы данных
from database import DATABASE_SCHEMA

# --- Диалог для добавления/редактирования объекта инвентаризации ---
class InventoryItemDialog(QDialog):
    def __init__(self, db_connection, item_data=None, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.item_data = item_data # None для добавления, dict для редактирования

        self.setWindowTitle("Добавить/Редактировать объект инвентаризации")
        self.layout = QFormLayout(self)

        # Поля из Units_inventory
        self.inventory_number_input = QLineEdit()
        self.serial_number_input = QLineEdit()
        self.manufacturer_input = QLineEdit()
        self.model_input = QLineEdit()
        self.cabinet_input = QLineEdit()
        self.unit_count_input = QLineEdit() # Для количества
        self.date_order_buhgaltery_input = QDateEdit(calendarPopup=True)
        self.date_order_buhgaltery_input.setDate(QDate.currentDate())
        self.date_order_buhgaltery_input.setDisplayFormat("yyyy-MM-dd")
        self.date_issue_input = QDateEdit(calendarPopup=True)
        self.date_issue_input.setDate(QDate.currentDate()) # Можно установить пустую дату или текущую
        self.date_issue_input.setDisplayFormat("yyyy-MM-dd")
        self.notice_input = QTextEdit() # Для многострочного текста
        self.notice_input.setFixedHeight(60)

        # Комбобоксы для связанных таблиц
        self.category_combo = QComboBox()
        self.subcategory_combo = QComboBox() # Будет зависеть от категории
        self.unit_type_combo = QComboBox()
        self.order_status_combo = QComboBox()

        # Поля из Units_extended_info
        self.device_name_input = QLineEdit()
        self.ip_input = QLineEdit()
        self.mac_input = QLineEdit()
        self.admin_login_input = QLineEdit()
        self.admin_password_input = QLineEdit()
        self.user_login_input = QLineEdit()
        self.user_password_input = QLineEdit()


        # Добавляем поля в форму
        self.layout.addRow("Инв. номер:", self.inventory_number_input)
        self.layout.addRow("Сер. номер:", self.serial_number_input)
        self.layout.addRow("Производитель:", self.manufacturer_input)
        self.layout.addRow("Модель:", self.model_input)
        self.layout.addRow("Кабинет:", self.cabinet_input)
        self.layout.addRow("Количество:", self.unit_count_input)
        self.layout.addRow("Дата заказа (бух.):", self.date_order_buhgaltery_input)
        self.layout.addRow("Дата выдачи:", self.date_issue_input)
        self.layout.addRow("Примечание:", self.notice_input)

        self.layout.addRow("Категория:", self.category_combo)
        self.layout.addRow("Подкатегория:", self.subcategory_combo)
        self.layout.addRow("Тип единицы:", self.unit_type_combo)
        self.layout.addRow("Статус заказа:", self.order_status_combo)

        self.layout.addRow(QLabel("<b>Расширенная информация:</b>")) # Разделитель

        self.layout.addRow("Имя устройства:", self.device_name_input)
        self.layout.addRow("IP:", self.ip_input)
        self.layout.addRow("MAC:", self.mac_input)
        self.layout.addRow("Логин админа:", self.admin_login_input)
        self.layout.addRow("Пароль админа:", self.admin_password_input)
        self.layout.addRow("Логин пользователя:", self.user_login_input)
        self.layout.addRow("Пароль пользователя:", self.user_password_input)


        # Заполняем комбобоксы
        self._populate_combos()

        # Подключаем сигнал изменения категории для обновления подкатегорий
        self.category_combo.currentIndexChanged.connect(self._update_subcategory_combo)


        # Если редактируем, заполняем поля текущими данными
        if self.item_data:
            self.inventory_number_input.setText(str(self.item_data.get('inventory_number', '')))
            self.serial_number_input.setText(str(self.item_data.get('serial_number', '')))
            self.manufacturer_input.setText(str(self.item_data.get('manufacturer', '')))
            self.model_input.setText(str(self.item_data.get('model', '')))
            self.cabinet_input.setText(str(self.item_data.get('cabinet', '')))
            self.unit_count_input.setText(str(self.item_data.get('unit_count', '')))

            date_order_str = self.item_data.get('date_order_buhgaltery')
            if date_order_str:
                 self.date_order_buhgaltery_input.setDate(QDate.fromString(str(date_order_str), Qt.ISODate))

            date_issue_str = self.item_data.get('date_issue')
            if date_issue_str:
                 self.date_issue_input.setDate(QDate.fromString(str(date_issue_str), Qt.ISODate))
            else:
                 # Если дата выдачи NULL, можно установить пустую дату или сбросить
                 self.date_issue_input.setDate(QDate(2000, 1, 1)) # Устанавливаем невалидную или базовую дату

            self.notice_input.setPlainText(str(self.item_data.get('notice', '')))

            # Выбираем нужные значения в комбобоксах по ID
            self._select_combo_item(self.category_combo, self.item_data.get('id_category'))
            # Обновляем подкатегории после выбора категории, затем выбираем подкатегорию
            self._update_subcategory_combo(self.category_combo.currentIndex())
            self._select_combo_item(self.subcategory_combo, self.item_data.get('id_subcategory'))
            self._select_combo_item(self.unit_type_combo, self.item_data.get('id_unit_type'))
            self._select_combo_item(self.order_status_combo, self.item_data.get('id_order_status'))

            # Заполняем поля расширенной информации
            self.device_name_input.setText(str(self.item_data.get('device_name', '')))
            self.ip_input.setText(str(self.item_data.get('ip', '')))
            self.mac_input.setText(str(self.item_data.get('mac', '')))
            self.admin_login_input.setText(str(self.item_data.get('admin_login', '')))
            self.admin_password_input.setText(str(self.item_data.get('admin_password', '')))
            self.user_login_input.setText(str(self.item_data.get('user_login', '')))
            self.user_password_input.setText(str(self.item_data.get('user_password', '')))


        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def _populate_combos(self):
        """Заполняет все QComboBox данными из справочных таблиц."""
        self._populate_category_combo()
        self._populate_unit_type_combo()
        self._populate_order_status_combo()
        # Подкатегории заполняются при выборе категории или изначально все
        self._populate_subcategory_combo()


    def _populate_category_combo(self):
        """Заполняет QComboBox категориями."""
        self.category_combo.clear()
        self.category_combo.addItem("Выберите категорию", None)
        query = QSqlQuery("SELECT id_category, category FROM Category ORDER BY category", self.db)
        while query.next():
            item_id = query.value(0)
            item_name = query.value(1)
            self.category_combo.addItem(item_name, item_id)

    def _update_subcategory_combo(self, index):
        """Обновляет QComboBox подкатегориями в зависимости от выбранной категории."""
        category_id = self.category_combo.itemData(index)
        self._populate_subcategory_combo(category_id)


    def _populate_subcategory_combo(self, category_id=None):
        """Заполняет QComboBox подкатегориями, опционально фильтруя по категории."""
        self.subcategory_combo.clear()
        self.subcategory_combo.addItem("Выберите подкатегорию", None)
        query = QSqlQuery(self.db)
        sql = "SELECT id_subcategory, subcategory FROM Subcategory"
        params = []
        if category_id is not None:
             sql += " WHERE id_category = ?"
             params.append(category_id)
        sql += " ORDER BY subcategory"

        query.prepare(sql)
        for param in params:
             query.addBindValue(param)

        if query.exec_():
            while query.next():
                item_id = query.value(0)
                item_name = query.value(1)
                self.subcategory_combo.addItem(item_name, item_id)
        else:
            print("Ошибка при загрузке подкатегорий:", query.lastError().text())


    def _populate_unit_type_combo(self):
        """Заполняет QComboBox типами единиц."""
        self.unit_type_combo.clear()
        self.unit_type_combo.addItem("Выберите тип единицы", None)
        query = QSqlQuery("SELECT id_unit_type, unit_type FROM Unit_type ORDER BY unit_type", self.db)
        while query.next():
            item_id = query.value(0)
            item_name = query.value(1)
            self.unit_type_combo.addItem(item_name, item_id)

    def _populate_order_status_combo(self):
        """Заполняет QComboBox статусами заказов."""
        self.order_status_combo.clear()
        self.order_status_combo.addItem("Выберите статус", None)
        query = QSqlQuery("SELECT id_order_status, order_status FROM Order_status ORDER BY order_status", self.db)
        while query.next():
            item_id = query.value(0)
            item_name = query.value(1)
            self.order_status_combo.addItem(item_name, item_id)

    def _select_combo_item(self, combo_box, item_id):
        """Выбирает элемент в комбобоксе по его UserData (ID)."""
        if item_id is None:
            combo_box.setCurrentIndex(0) # Выбираем "Выберите..." или "Все..."
            return
        for i in range(combo_box.count()):
            if combo_box.itemData(i) == item_id:
                combo_box.setCurrentIndex(i)
                return
        # Если ID не найден, оставляем выбранным первый элемент (None)
        combo_box.setCurrentIndex(0)


    def get_data(self):
        """Возвращает данные из полей диалога в виде словаря."""
        data = {
            # Units_inventory fields
            'inventory_number': self.inventory_number_input.text().strip(),
            'serial_number': self.serial_number_input.text().strip(),
            'manufacturer': self.manufacturer_input.text().strip(),
            'model': self.model_input.text().strip(),
            'cabinet': self.cabinet_input.text().strip(),
            'unit_count': self.unit_count_input.text().strip(), # Пока как строка, нужно преобразовать в int
            'date_order_buhgaltery': self.date_order_buhgaltery_input.date().toString(Qt.ISODate),
            'date_issue': self.date_issue_input.date().toString(Qt.ISODate) if self.date_issue_input.date().isValid() else None, # NULL если дата невалидна
            'notice': self.notice_input.toPlainText().strip(),

            # Foreign key IDs
            'id_category': self.category_combo.currentData(),
            'id_subcategory': self.subcategory_combo.currentData(),
            'id_unit_type': self.unit_type_combo.currentData(),
            'id_order_status': self.order_status_combo.currentData(),

            # Units_extended_info fields
            'device_name': self.device_name_input.text().strip(),
            'ip': self.ip_input.text().strip(),
            'mac': self.mac_input.text().strip(),
            'admin_login': self.admin_login_input.text().strip(),
            'admin_password': self.admin_password_input.text().strip(),
            'user_login': self.user_login_input.text().strip(),
            'user_password': self.user_password_input.text().strip(),
        }

        # Преобразование unit_count в INTEGER
        try:
            data['unit_count'] = int(data['unit_count']) if data['unit_count'] else None
        except ValueError:
            data['unit_count'] = None # Или 0, или оставить как строку и обрабатывать ошибку валидации

        # Если редактируем, добавляем ID объекта инвентаризации
        if self.item_data and 'id_unit_inventory' in self.item_data:
             data['id_unit_inventory'] = self.item_data['id_unit_inventory']
             # Для Units_extended_info также нужен id_unit_inventory
             data['extended_info_id_unit_inventory'] = self.item_data.get('extended_info_id_unit_inventory') # Может быть None при добавлении

        return data


    def validate_data(self):
        """Проверяет введенные данные."""
        data = self.get_data()
        if not data['inventory_number']:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите инвентарный номер.")
            return False
        # TODO: Добавить другие проверки валидации, например, для unit_count, форматов IP/MAC и т.д.
        return True


class InventoryView(QWidget):
    def __init__(self, db_connection):
        super().__init__()

        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто.")
            return

        self.setWindowTitle("Управление инвентаризацией")

        self.layout = QVBoxLayout(self)

        info_label = QLabel("Список объектов инвентаризации.")
        self.layout.addWidget(info_label)

        # --- Настройки модели и таблицы ---
        self.table_name = "Units_inventory" # Основная таблица

        # Используем QSqlRelationalTableModel для отображения связанных данных
        self.model = QSqlRelationalTableModel(self, self.db)
        self.model.setTable(self.table_name)

        # Устанавливаем связи для столбцов внешних ключей
        # Получаем индексы столбцов из схемы БД
        col_names_in_schema = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]

        relation_columns = {
            "id_category": ("Category", "id_category", "category"),
            "id_subcategory": ("Subcategory", "id_subcategory", "subcategory"),
            "id_unit_type": ("Unit_type", "id_unit_type", "unit_type"),
            "id_order_status": ("Order_status", "id_order_status", "order_status"),
        }

        for col_name, relation_info in relation_columns.items():
            if col_name in col_names_in_schema:
                col_index = col_names_in_schema.index(col_name)
                self.model.setRelation(col_index, QSqlRelation(*relation_info))
            else:
                print(f"Предупреждение: Столбец '{col_name}' не найден в схеме {self.table_name}.")


        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit) # Изменения сохраняем вручную
        self.model.select() # Загрузить данные из таблицы

        # Устанавливаем заголовки столбцов (соответствуют порядку в SELECT запросе или модели)
        # Используем названия столбцов из схемы для определения порядка
        header_labels = {
            "id_unit_inventory": "ID",
            "inventory_number": "Инв. номер",
            "serial_number": "Сер. номер",
            "manufacturer": "Производитель",
            "model": "Модель",
            "cabinet": "Кабинет",
            "unit_count": "Количество",
            "date_order_buhgaltery": "Дата заказа (бух.)",
            "date_issue": "Дата выдачи",
            "notice": "Примечание",
            "id_category": "Категория", # Будет отображаться имя
            "id_subcategory": "Подкатегория", # Будет отображаться имя
            "id_unit_type": "Тип единицы", # Будет отображаться имя
            "id_order_status": "Статус заказа", # Будет отображаться имя
            # Поля из Units_extended_info не отображаются напрямую в этой модели
        }

        # Устанавливаем заголовки в модели
        for i, col_name in enumerate(col_names_in_schema):
             if col_name in header_labels:
                self.model.setHeaderData(i, Qt.Horizontal, header_labels[col_name])
             else:
                self.model.setHeaderData(i, Qt.Horizontal, col_name) # Используем имя столбца по умолчанию


        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        # Скрываем столбец ID
        id_col_index = col_names_in_schema.index("id_unit_inventory") if "id_unit_inventory" in col_names_in_schema else -1
        if id_col_index != -1:
             self.table_view.hideColumn(id_col_index)

        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        # Редактирование будет происходить через диалог, поэтому отключаем прямое редактирование в таблице
        self.table_view.setEditTriggers(QTableView.NoEditTriggers)


        self.layout.addWidget(self.table_view)

        # --- Кнопки для добавления, редактирования и удаления ---
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Добавить объект")
        edit_button = QPushButton("Редактировать выбранный")
        delete_button = QPushButton("Удалить выбранный")
        refresh_button = QPushButton("Обновить список") # Добавим кнопку обновления

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(edit_button)
        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(refresh_button)
        buttons_layout.addStretch()

        self.layout.addLayout(buttons_layout)

        # Подключаем методы к кнопкам
        add_button.clicked.connect(self._add_item)
        edit_button.clicked.connect(self._edit_item)
        delete_button.clicked.connect(self._delete_item)
        refresh_button.clicked.connect(self._refresh_list)

        # Подключаем сигнал model.primeInsert() для установки значений по умолчанию при добавлении новой строки
        self.model.primeInsert.connect(self._init_new_row)
        # Подключаем сигнал model.dataChanged для обработки ошибок сохранения (при OnManualSubmit не так критично, но полезно)
        self.model.dataChanged.connect(self._handle_data_changed)


    def _refresh_list(self):
        """Обновляет данные в таблице."""
        self.model.select() # Перезагружаем данные из базы
        print("Список объектов инвентаризации обновлен.")


    def _add_item(self):
        """Открывает диалог для добавления нового объекта инвентаризации."""
        dialog = InventoryItemDialog(self.db, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            if dialog.validate_data():
                data = dialog.get_data()

                # Добавляем новую запись в Units_inventory через модель
                row_count = self.model.rowCount()
                self.model.insertRow(row_count)

                # Устанавливаем данные в модель Units_inventory
                # Используем fieldIndex для надежности
                field_indices = {col: self.model.fieldIndex(col) for col in data if col in [c.split()[0] for c in DATABASE_SCHEMA.get(self.table_name, [])]}

                for key, value in data.items():
                    if key in field_indices and field_indices[key] != -1:
                         # Преобразуем None в QVariant(QVariant.Type.Int) для INTEGER полей, если нужно
                         # Или просто передаем None, SQLite обычно обрабатывает это как NULL
                         self.model.setData(self.model.index(row_count, field_indices[key]), value)


                # Сохраняем изменения в Units_inventory
                if self.model.submitAll():
                    print("Объект инвентаризации успешно добавлен в Units_inventory.")

                    # Получаем ID только что добавленной записи
                    # Это можно сделать, выбрав модель заново или выполнив запрос
                    self.model.select() # Обновляем модель, чтобы получить новый ID
                    # Находим добавленную строку (например, по инвентарному номеру, если он уникален)
                    # Или просто берем последнюю строку, если уверены, что она наша
                    new_row_index = self.model.rowCount() - 1
                    new_item_id = self.model.data(self.model.index(new_row_index, self.model.fieldIndex("id_unit_inventory")), Qt.EditRole)

                    # Если есть данные для Units_extended_info, добавляем их
                    extended_info_data = {k: data[k] for k in data if k in [c.split()[0] for c in DATABASE_SCHEMA.get("Units_extended_info", [])]}
                    if any(extended_info_data.values()): # Если хотя бы одно поле расширенной инфо заполнено
                         self._add_extended_info(new_item_id, extended_info_data)


                else:
                    print("Ошибка при добавлении объекта в Units_inventory:", self.model.lastError().text())
                    QMessageBox.critical(self, "Ошибка", f"Не удалось добавить объект: {self.model.lastError().text()}")
                    self.model.revertAll() # Отменяем изменения в Units_inventory


    def _add_extended_info(self, unit_inventory_id, extended_info_data):
        """Добавляет запись в Units_extended_info."""
        if unit_inventory_id is None:
             print("Ошибка: Не удалось получить ID объекта инвентаризации для добавления расширенной информации.")
             return

        query = QSqlQuery(self.db)
        # Столбцы для вставки в Units_extended_info (включая id_unit_inventory)
        cols = ["id_unit_inventory"] + [k for k in extended_info_data.keys()]
        placeholders = ', '.join(['?'] * len(cols))
        insert_sql = f"INSERT INTO Units_extended_info ({', '.join(cols)}) VALUES ({placeholders})"

        query.prepare(insert_sql)
        query.addBindValue(unit_inventory_id) # Первый параметр - id_unit_inventory
        for key in extended_info_data.keys():
             query.addBindValue(extended_info_data[key]) # Остальные параметры

        if query.exec_():
            print(f"Расширенная информация успешно добавлена для ID {unit_inventory_id}.")
        else:
            print(f"Ошибка при добавлении расширенной информации для ID {unit_inventory_id}:", query.lastError().text())
            QMessageBox.warning(self, "Предупреждение", f"Не удалось добавить расширенную информацию для объекта (ID {unit_inventory_id}): {query.lastError().text()}")
            # TODO: Возможно, стоит удалить запись из Units_inventory, если не удалось добавить расширенную инфо?


    def _edit_item(self):
        """Открывает диалог для редактирования выбранного объекта инвентаризации."""
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите объект для редактирования.")
            return

        selected_index = selected_indexes[0]
        row = selected_index.row()

        # Получаем ID объекта инвентаризации
        item_id = self.model.data(self.model.index(row, self.model.fieldIndex("id_unit_inventory")), Qt.EditRole)
        if item_id is None:
             QMessageBox.warning(self, "Ошибка", "Не удалось получить ID выбранного объекта.")
             return

        # Получаем текущие данные из Units_inventory через модель
        item_data = {}
        for col_name in [c.split()[0] for c in DATABASE_SCHEMA.get(self.table_name, []) if not c.strip().startswith("FOREIGN KEY")]:
             col_index = self.model.fieldIndex(col_name)
             if col_index != -1:
                item_data[col_name] = self.model.data(self.model.index(row, col_index), Qt.EditRole)

        # Получаем данные из Units_extended_info (если есть)
        extended_info_query = QSqlQuery(self.db)
        extended_info_query.prepare("SELECT device_name, ip, mac, admin_login, admin_password, user_login, user_password FROM Units_extended_info WHERE id_unit_inventory = ?")
        extended_info_query.addBindValue(item_id)

        if extended_info_query.exec_() and extended_info_query.next():
             # Добавляем данные расширенной инфо в item_data
             item_data['extended_info_id_unit_inventory'] = item_id # Сохраняем ID для обновления/удаления
             item_data['device_name'] = extended_info_query.value(0)
             item_data['ip'] = extended_info_query.value(1)
             item_data['mac'] = extended_info_query.value(2)
             item_data['admin_login'] = extended_info_query.value(3)
             item_data['admin_password'] = extended_info_query.value(4)
             item_data['user_login'] = extended_info_query.value(5)
             item_data['user_password'] = extended_info_query.value(6)
        else:
             # Если записи в Units_extended_info нет, добавляем пустые значения
             item_data['extended_info_id_unit_inventory'] = None
             item_data['device_name'] = None
             item_data['ip'] = None
             item_data['mac'] = None
             item_data['admin_login'] = None
             item_data['admin_password'] = None
             item_data['user_login'] = None
             item_data['user_password'] = None


        dialog = InventoryItemDialog(self.db, item_data=item_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
             if dialog.validate_data():
                new_data = dialog.get_data()

                # Обновляем данные в Units_inventory через модель
                field_indices = {col: self.model.fieldIndex(col) for col in new_data if col in [c.split()[0] for c in DATABASE_SCHEMA.get(self.table_name, [])]}
                for key, value in new_data.items():
                    if key in field_indices and field_indices[key] != -1:
                         self.model.setData(self.model.index(row, field_indices[key]), value)

                # Сохраняем изменения в Units_inventory
                if self.model.submitAll():
                    print(f"Объект инвентаризации с ID {item_id} успешно отредактирован в Units_inventory.")

                    # Обновляем или добавляем данные в Units_extended_info
                    extended_info_data = {k: new_data[k] for k in new_data if k in [c.split()[0] for c in DATABASE_SCHEMA.get("Units_extended_info", [])]}
                    existing_extended_info_id = item_data.get('extended_info_id_unit_inventory') # ID существующей записи в Units_extended_info (равен item_id)

                    if any(extended_info_data.values()): # Если есть данные для сохранения в Units_extended_info
                         if existing_extended_info_id is not None:
                             # Обновляем существующую запись
                             self._update_extended_info(item_id, extended_info_data)
                         else:
                             # Добавляем новую запись
                             self._add_extended_info(item_id, extended_info_data)
                    elif existing_extended_info_id is not None:
                         # Если данных нет, но запись существует, удаляем ее
                         self._delete_extended_info(item_id)


                    self.model.select() # Обновляем представление после редактирования

                else:
                    print("Ошибка при сохранении изменений в Units_inventory:", self.model.lastError().text())
                    QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить изменения: {self.model.lastError().text()}")
                    self.model.revertAll() # Отменяем изменения в Units_inventory


    def _update_extended_info(self, unit_inventory_id, extended_info_data):
        """Обновляет запись в Units_extended_info."""
        query = QSqlQuery(self.db)
        # Формируем SQL запрос для обновления
        set_clauses = [f"{col} = ?" for col in extended_info_data.keys()]
        update_sql = f"UPDATE Units_extended_info SET {', '.join(
