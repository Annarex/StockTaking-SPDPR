# ui/subcategory_view.py
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLabel, QMessageBox, QLineEdit,
                             QInputDialog, QFormLayout, QComboBox, QFileDialog)
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError, QSqlRelation, QSqlRelationalTableModel
from PyQt5.QtCore import Qt, QModelIndex, QDate, QVariant
import re # Для валидации двух символов

# Импортируем универсальный обработчик CSV
from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

# Импортируем схему базы данных для получения названий таблиц и столбцов
from database import DATABASE_SCHEMA

class SubcategoryView(QWidget):
    def __init__(self, db_connection):
        super().__init__()

        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто.")
            return

        self.setWindowTitle("Управление подкатегориями")

        self.layout = QVBoxLayout(self)

        info_label = QLabel("Управление подкатегориями инвентаризации. ID подкатегории вводится вручную.")
        self.layout.addWidget(info_label)

        # --- Настройки модели и таблицы ---
        self.table_name = "Subcategory" # Название таблицы
        # Получаем названия столбцов из схемы БД
        self.column_names = [col.split()[0] for col in DATABASE_SCHEMA.get(self.table_name, []) if not col.strip().startswith("FOREIGN KEY")]
        # Уникальным столбцом для проверки при импорте и добавлении является сам ID
        self.unique_column = ""

        # Используем QSqlRelationalTableModel для отображения имени категории
        self.model = QSqlRelationalTableModel(self, self.db)
        self.model.setTable(self.table_name)

        # Устанавливаем связь для столбца id_category
        # Получаем индекс столбца id_category по имени
        category_col_index = self.model.fieldIndex("id_category")
        if category_col_index != -1:
             self.model.setRelation(category_col_index, QSqlRelation("Category", "id_category", "id_category"))
        else:
             print("Предупреждение: Столбец 'id_category' не найден в модели Subcategory.")


        self.model.setEditStrategy(QSqlTableModel.OnFieldChange) # Сохранять изменения сразу
        self.model.select() # Загрузить данные из таблицы

        # Устанавливаем заголовки столбцов
        header_map = {
            "id_subcategory": "ID Подкатегории", # Изменяем заголовок
            "id_category": "Категория", # Будет отображаться имя из связанной таблицы
            "subcategory": "Подкатегория"
        }
        # Используем fieldName(i) для получения имени столбца в модели
        for i in range(self.model.columnCount()):
             col_name = self.model.record().fieldName(i)
             if col_name in header_map:
                self.model.setHeaderData(i, Qt.Horizontal, header_map[col_name])
             else:
                self.model.setHeaderData(i, Qt.Horizontal, col_name)


        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        # Разрешаем редактирование, для столбца Категория будет использоваться делегат QSqlRelationalTableModel
        self.table_view.setEditTriggers(QTableView.DoubleClicked | QTableView.SelectedClicked)

        self.layout.addWidget(self.table_view)

        # --- Элементы для добавления новой записи ---
        add_form_layout = QFormLayout()

        self.subcategory_id_input = QLineEdit() # НОВОЕ ПОЛЕ ДЛЯ ID
        self.subcategory_id_input.setPlaceholderText("Введите 2 символа ID") # Изменяем на 2 символа по вашей последней схеме
        self.subcategory_id_input.setMaxLength(2) # Ограничение по длине

        self.category_combo = QComboBox()
        self._populate_category_combo() # Заполняем комбобокс категориями

        self.subcategory_name_input = QLineEdit()
        self.subcategory_name_input.setPlaceholderText("Введите название подкатегории")
        self.subcategory_name_input.setMaxLength(40) # Ограничение по длине


        add_form_layout.addRow("ID Подкатегории:", self.subcategory_id_input) # Добавляем поле ID
        add_form_layout.addRow("Категория:", self.category_combo)
        add_form_layout.addRow("Подкатегория:", self.subcategory_name_input)

        add_button = QPushButton("Добавить подкатегорию")
        add_button.clicked.connect(self._add_item)

        add_layout = QHBoxLayout()
        add_layout.addLayout(add_form_layout)
        add_layout.addWidget(add_button, alignment=Qt.AlignBottom)

        self.layout.addLayout(add_layout)

        # --- Кнопки управления (Удалить, Импорт, Экспорт) ---
        buttons_layout = QHBoxLayout()
        delete_button = QPushButton("Удалить выбранную")
        delete_button.clicked.connect(self._delete_selected_item)
        buttons_layout.addWidget(delete_button)

        import_button = QPushButton("Импорт из CSV...")
        import_button.clicked.connect(self._import_from_csv)
        buttons_layout.addWidget(import_button)

        export_button = QPushButton("Экспорт в CSV...")
        export_button.clicked.connect(self._export_to_csv)
        buttons_layout.addWidget(export_button)

        buttons_layout.addStretch()

        self.layout.addLayout(buttons_layout)

        self.model.dataChanged.connect(self._handle_data_changed)
        # primeInsert не нужен, т.к. ID вводится в поле ввода
        # self.model.primeInsert.connect(self._init_new_row)

    def _populate_category_combo(self):
        """Заполняет QComboBox категориями из базы данных."""
        self.category_combo.clear()
        self.category_combo.addItem("Выберите категорию", None) # Опция "Выберите"
        query = QSqlQuery("SELECT id_category, category FROM Category ORDER BY id_category", self.db)
        while query.next():
            category_id = query.value(0)
            category_name = query.value(1)
            self.category_combo.addItem(category_id+'-'+category_name, category_id) # Сохраняем ID как UserData


    def _add_item(self):
        """Добавляет новую подкатегорию в базу данных."""
        subcategory_id = self.subcategory_id_input.text().strip()
        category_id = self.category_combo.currentData()
        subcategory_name = self.subcategory_name_input.text().strip()

        # --- Валидация ID Подкатегории ---
        if not subcategory_id:
             QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите ID подкатегории.")
             return
        # Проверка на 2 символа
        if len(subcategory_id) != 2: # Изменяем на 2 символа по вашей последней схеме
             QMessageBox.warning(self, "Предупреждение", "ID подкатегории должен состоять ровно из 2 символов.")
             return
        if category_id is None:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите категорию.")
            return
        if not subcategory_name:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите название подкатегории.")
            return
        if len(subcategory_name) > 40:
            QMessageBox.warning(self, "Предупреждение", "Название подкатегории не может превышать 40 символов.")
            return

        # Проверяем на уникальность ID Подкатегории и Названия Подкатегории
        query = QSqlQuery(self.db)
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE id_subcategory = ? OR subcategory = ?")
        query.addBindValue(subcategory_id)
        query.addBindValue(subcategory_name)
        if query.exec_() and query.next():
            count = query.value(0)
            if count > 0:
                # Уточняем, что именно дублируется
                check_id_query = QSqlQuery(self.db)
                check_id_query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE id_subcategory = ?")
                check_id_query.addBindValue(subcategory_id)
                check_id_query.exec_()
                check_id_query.next()
                if check_id_query.value(0) > 0:
                     QMessageBox.warning(self, "Предупреждение", f"ID подкатегории '{subcategory_id}' уже существует.")
                     return

                check_name_query = QSqlQuery(self.db)
                check_name_query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE subcategory = ?")
                check_name_query.addBindValue(subcategory_name)
                check_name_query.exec_()
                check_name_query.next()
                if check_name_query.value(0) > 0:
                     QMessageBox.warning(self, "Предупреждение", f"Подкатегория '{subcategory_name}' уже существует.")
                     return
                # Если дошли сюда, значит, что-то не так с логикой проверки, но на всякий случай
                QMessageBox.warning(self, "Предупреждение", "Дублирующаяся запись.")
                return


        # Добавляем новую запись через модель
        row_count = self.model.rowCount()
        self.model.insertRow(row_count)

        # Устанавливаем данные в модель по именам столбцов
        col_indices = {col: self.model.fieldIndex(col) for col in self.column_names}

        if "id_subcategory" in col_indices and col_indices["id_subcategory"] != -1:
             self.model.setData(self.model.index(row_count, col_indices["id_subcategory"]), subcategory_id)
        if "id_category" in col_indices and col_indices["id_category"] != -1:
             self.model.setData(self.model.index(row_count, col_indices["id_category"]), str(category_id)) # Передаем как строку
        if "subcategory" in col_indices and col_indices["subcategory"] != -1:
             self.model.setData(self.model.index(row_count, col_indices["subcategory"]), subcategory_name)


        if self.model.submitAll(): # Сохраняем изменения в базу данных
            print(f"Подкатегория '{subcategory_name}' (ID: {subcategory_id}) успешно добавлена.")
            self.subcategory_id_input.clear() # Очищаем поля ввода
            self.category_combo.setCurrentIndex(0) # Сбрасываем комбобокс
            self.subcategory_name_input.clear()
            # model.select() не нужен, т.к. OnFieldChange обновляет представление
        else:
            print("Ошибка при добавлении подкатегории:", self.model.lastError().text())
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить подкатегорию: {self.model.lastError().text()}")
            self.model.revertAll() # Отменяем изменения, если сохранение не удалось

    def _delete_selected_item(self):
        """Удаляет выбранную подкатегорию."""
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите подкатегорию для удаления.")
            return

        selected_index = selected_indexes[0]
        row = selected_index.row()

        # Получаем ID и название подкатегории для подтверждения
        id_col_index = self.model.fieldIndex("id_subcategory")
        name_col_index = self.model.fieldIndex("subcategory")
        item_id = self.model.data(self.model.index(row, id_col_index), Qt.DisplayRole) if id_col_index != -1 else "N/A"
        item_name = self.model.data(self.model.index(row, name_col_index), Qt.DisplayRole) if name_col_index != -1 else "Выбранная запись"

        reply = QMessageBox.question(self, "Подтверждение удаления",f"Вы уверены, что хотите удалить подкатегорию '{item_name}' (ID: {item_id})?",QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.model.removeRow(row):
                if self.model.submitAll():
                    print(f"Подкатегория '{item_name}' (ID: {item_id}) успешно удалена.")
                else:
                    print("Ошибка при сохранении удаления:", self.model.lastError().text())
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить подкатегорию: {self.model.lastError().text()}")
                    self.model.revertAll()
            else:
                print("Ошибка при удалении строки из модели.")
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить строку из модели.")

    def _import_from_csv(self):
        """Открывает диалог выбора файла и запускает импорт."""
        file_path, _ = QFileDialog.getOpenFileName(self, f"Импорт данных в таблицу '{self.table_name}'",
                                                   "",
                                                   "CSV файлы (*.csv);;Все файлы (*)")

        if file_path:
            print(f"Выбран файл для импорта в {self.table_name}: {file_path}")
            success, message = import_data_from_csv(self.db, file_path, self.table_name, self.column_names, column_digits={'id_subcategory': 2, 'id_category': 2}, unique_column=self.unique_column)

            if success:
                QMessageBox.information(self, "Импорт завершен", message)
                self.model.select() # Обновляем представление после импорта
            else:
                QMessageBox.critical(self, "Ошибка импорта", message)
        else:
            print("Выбор файла отменен.")        
    
    def _export_to_csv(self):
        """Открывает диалог сохранения файла и запускает экспорт."""
        default_filename = f"{self.table_name}_export_{QDate.currentDate().toString('yyyyMMdd')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, f"Экспорт данных из таблицы '{self.table_name}'", default_filename, "CSV файлы (*.csv);;Все файлы (*)")

        if file_path:
            print(f"Выбран файл для экспорта из {self.table_name}: {file_path}")
            success, message = export_data_to_csv(self.db, file_path, self.table_name, self.column_names)

            if success:
                QMessageBox.information(self, "Экспорт завершен", message)
                print(f"Экспорт сохранен: {file_path}")
            else:
                QMessageBox.critical(self, "Ошибка экспорта", message)
        else:
            print("Сохранение отчета отменено.")


    def _handle_data_changed(self, topLeft, bottomRight, roles):
        """Обрабатывает сигнал dataChanged для проверки ошибок сохранения после редактирования ячейки."""
        if self.model.lastError().type() != QSqlError.NoError:
            error_message = self.model.lastError().text()
            print(f"Ошибка при сохранении изменения: {error_message}")
            QMessageBox.critical(self, "Ошибка сохранения", f"Не удалось сохранить изменение: {error_message}")
            self.model.select() # Перезагружаем данные, чтобы откатить некорректное изменение в представлении

    def _init_new_row(self, row, record):
        """Устанавливает значения по умолчанию для новой строки перед вставкой."""
        # При ручном вводе ID, здесь ничего не делаем, т.к. ID вводится в поле ввода, а не в таблице напрямую.
        pass