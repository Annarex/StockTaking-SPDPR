# ui/departments_view.py
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLabel, QMessageBox, QLineEdit,
                             QInputDialog,QFileDialog, QFormLayout)
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError
from PyQt5.QtCore import Qt, QModelIndex, QDate

# Импортируем универсальный обработчик CSV
from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

# Импортируем схему базы данных
from database import DATABASE_SCHEMA

class DepartmentsView(QWidget):
    def __init__(self, db_connection):
        super().__init__()

        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто.")
            return

        self.setWindowTitle("Управление отделами")

        self.layout = QVBoxLayout(self)

        info_label = QLabel("Управление отделами.")
        self.layout.addWidget(info_label)

        # --- Настройки модели и таблицы ---
        self.table_name = "Departments" # Название таблицы
        self.column_names = [col.split()[0] for col in DATABASE_SCHEMA[self.table_name] if not col.strip().startswith("FOREIGN KEY")]
        self.unique_column = "department_fullname" # Столбец для проверки уникальности

        self.model = QSqlTableModel(self, self.db)
        self.model.setTable(self.table_name)
        self.model.setEditStrategy(QSqlTableModel.OnFieldChange)
        self.model.select()

        header_labels = ["ID", "Полное название", "Краткое название"]
        for i, header_text in enumerate(header_labels):
             if i < len(self.column_names):
                self.model.setHeaderData(i, Qt.Horizontal, header_text)

        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setEditTriggers(QTableView.DoubleClicked | QTableView.SelectedClicked)

        self.layout.addWidget(self.table_view)

        # --- Элементы для добавления новой записи ---
        add_form_layout = QFormLayout()

        self.fullname_input = QLineEdit()
        self.shortname_input = QLineEdit()

        add_form_layout.addRow("Полное название:", self.fullname_input)
        add_form_layout.addRow("Краткое название:", self.shortname_input)

        add_button = QPushButton("Добавить отдел")
        add_button.clicked.connect(self._add_item)

        add_layout = QHBoxLayout()
        add_layout.addLayout(add_form_layout)
        add_layout.addWidget(add_button, alignment=Qt.AlignBottom)

        self.layout.addLayout(add_layout)

        # --- Кнопки управления (Удалить, Импорт, Экспорт) ---
        buttons_layout = QHBoxLayout()
        delete_button = QPushButton("Удалить выбранный")
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
        self.model.primeInsert.connect(self._init_new_row)


    def _add_item(self):
        """Добавляет новый отдел в базу данных."""
        fullname = self.fullname_input.text().strip()
        shortname = self.shortname_input.text().strip()

        if not fullname:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите полное название отдела.")
            return

        query = QSqlQuery(self.db)
        query.prepare(f"SELECT COUNT(*) FROM {self.table_name} WHERE department_fullname = ?")
        query.addBindValue(fullname)
        if query.exec_() and query.next():
            if query.value(0) > 0:
                QMessageBox.warning(self, "Предупреждение", f"Отдел с полным названием '{fullname}' уже существует.")
                return

        row_count = self.model.rowCount()
        self.model.insertRow(row_count)
        # Столбцы: 1=department_fullname, 2=department_shortname
        self.model.setData(self.model.index(row_count, 1), fullname)
        self.model.setData(self.model.index(row_count, 2), shortname)

        if self.model.submitAll():
            print(f"Отдел '{fullname}' успешно добавлен.")
            self.fullname_input.clear()
            self.shortname_input.clear()
        else:
            print("Ошибка при добавлении отдела:", self.model.lastError().text())
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить отдел: {self.model.lastError().text()}")
            self.model.revertAll()

    def _delete_selected_item(self):
        """Удаляет выбранный отдел."""
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите отдел для удаления.")
            return

        selected_index = selected_indexes[0]
        row = selected_index.row()

        item_name = self.model.data(self.model.index(row, 1), Qt.DisplayRole) # Столбец 1 - department_fullname

        reply = QMessageBox.question(self, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить отдел '{item_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.model.removeRow(row):
                if self.model.submitAll():
                    print(f"Отдел '{item_name}' успешно удален.")
                else:
                    print("Ошибка при сохранении удаления:", self.model.lastError().text())
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить отдел: {self.model.lastError().text()}")
                    self.model.revertAll()
            else:
                print("Ошибка при удалении строки из модели.")
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить строку из модели.")

    def _import_from_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, f"Импорт данных в таблицу '{self.table_name}'","", "CSV файлы (*.csv);;Все файлы (*)")
        if file_path:
            print(f"Выбран файл для импорта в {self.table_name}: {file_path}")
            success, message = import_data_from_csv(self.db, file_path, self.table_name, self.column_names,column_digits={'id_department': 2}, unique_column=self.unique_column)

            if success:
                QMessageBox.information(self, "Импорт завершен", message)
                self.model.select()
            else:
                QMessageBox.critical(self, "Ошибка импорта", message)
        else:
            print("Выбор файла отменен.")

    def _export_to_csv(self):
        """Открывает диалог сохранения файла и запускает экспорт."""
        default_filename = f"{self.table_name}_export_{QDate.currentDate().toString('yyyyMMdd')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, f"Экспорт данных из таблицы '{self.table_name}'",
                                                   default_filename,
                                                   "CSV файлы (*.csv);;Все файлы (*)")

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
        pass # Для Departments нет специфичных значений по умолчанию