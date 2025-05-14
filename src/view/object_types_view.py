# object_types_view.py
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLineEdit, QLabel, QDialog,
                             QDialogButtonBox, QMessageBox, QInputDialog) # Импортируем QInputDialog
from PyQt5.QtSql import QSqlTableModel, QSqlQuery, QSqlDatabase, QSqlError # Импортируем QSqlError
from PyQt5.QtCore import Qt, QModelIndex # Импортируем QModelIndex

class ObjectTypesView(QWidget):
    def __init__(self, db_connection):
        super().__init__()

        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто.")
            # Возможно, стоит как-то уведомить пользователя или закрыть виджет
            return

        self.setWindowTitle("Управление типами объектов")

        self.layout = QVBoxLayout(self)

        # Модель для таблицы object_types
        self.model = QSqlTableModel(self, self.db)
        self.model.setTable("object_types")
        self.model.setEditStrategy(QSqlTableModel.OnFieldChange) # Сохранять изменения сразу
        self.model.select() # Загрузить данные из таблицы

        # Устанавливаем заголовки столбцов
        self.model.setHeaderData(0, Qt.Horizontal, "ID")
        self.model.setHeaderData(1, Qt.Horizontal, "Название типа")

        # Таблица для отображения типов
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        # Скрываем столбец ID, так как он автоинкрементный и не нужен для прямого редактирования пользователем
        self.table_view.hideColumn(0)
        self.table_view.horizontalHeader().setStretchLastSection(True) # Растягиваем последний столбец
        self.table_view.setSelectionBehavior(QTableView.SelectRows) # Выделять целые строки
        self.table_view.setSelectionMode(QTableView.SingleSelection) # Выделять только одну строку

        self.layout.addWidget(self.table_view)

        # --- Элементы для добавления нового типа ---
        add_layout = QHBoxLayout()

        self.new_type_name_input = QLineEdit()
        self.new_type_name_input.setPlaceholderText("Введите название нового типа")
        add_layout.addWidget(self.new_type_name_input)

        add_button = QPushButton("Добавить тип")
        add_button.clicked.connect(self._add_type)
        add_layout.addWidget(add_button)

        self.layout.addLayout(add_layout)

        # --- Кнопки для редактирования и удаления ---
        edit_delete_layout = QHBoxLayout()
        edit_button = QPushButton("Редактировать выбранный")
        delete_button = QPushButton("Удалить выбранный")
        edit_delete_layout.addWidget(edit_button)
        edit_delete_layout.addWidget(delete_button)
        self.layout.addLayout(edit_delete_layout)

        # Подключаем методы к кнопкам
        edit_button.clicked.connect(self._edit_type)
        delete_button.clicked.connect(self._delete_type)


    def _add_type(self):
        """Добавляет новый тип объекта в базу данных."""
        type_name = self.new_type_name_input.text().strip()

        if not type_name:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите название типа.")
            return

        # Проверяем, существует ли уже такой тип (используем QSqlQuery для проверки уникальности)
        # Это более надежно, чем полагаться только на UNIQUE constraint, т.к. дает более понятное сообщение
        query = QSqlQuery(self.db)
        query.prepare("SELECT COUNT(*) FROM object_types WHERE name = ?")
        query.addBindValue(type_name)
        if query.exec_() and query.next():
            if query.value(0) > 0:
                QMessageBox.warning(self, "Предупреждение", f"Тип '{type_name}' уже существует.")
                return

        # Добавляем новую запись через модель
        row_count = self.model.rowCount()
        self.model.insertRow(row_count)
        # Столбец 1 - 'name'
        self.model.setData(self.model.index(row_count, 1), type_name)

        if self.model.submitAll(): # Сохраняем изменения в базу данных
            print(f"Тип '{type_name}' успешно добавлен.")
            self.new_type_name_input.clear() # Очищаем поле ввода
            # model.select() не нужен, т.к. OnFieldChange обновляет представление
        else:
            print("Ошибка при добавлении типа:", self.model.lastError().text())
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить тип: {self.model.lastError().text()}")
            self.model.revertAll() # Отменяем изменения, если сохранение не удалось


    def _edit_type(self):
        """Редактирует выбранный тип объекта."""
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите тип для редактирования.")
            return

        # Получаем индекс первой выбранной ячейки (достаточно одной, т.к. выделяем строки)
        selected_index = selected_indexes[0]
        row = selected_index.row()

        # Получаем текущее название типа из модели (столбец 1)
        current_name = self.model.data(self.model.index(row, 1), Qt.DisplayRole)

        # Открываем диалог для ввода нового названия
        new_name, ok = QInputDialog.getText(self, "Редактировать тип", "Введите новое название типа:",
                                            QLineEdit.Normal, current_name)

        if ok and new_name: # Если пользователь нажал OK и ввел текст
            new_name = new_name.strip()
            if not new_name:
                 QMessageBox.warning(self, "Предупреждение", "Название типа не может быть пустым.")
                 return

            if new_name == current_name:
                print("Название не изменилось.")
                return # Ничего не делаем, если название не изменилось

            # Проверяем на уникальность новое название (исключая текущую строку)
            query = QSqlQuery(self.db)
            # Получаем ID текущей строки (столбец 0)
            current_id = self.model.data(self.model.index(row, 0), Qt.DisplayRole)
            query.prepare("SELECT COUNT(*) FROM object_types WHERE name = ? AND id != ?")
            query.addBindValue(new_name)
            query.addBindValue(current_id)

            if query.exec_() and query.next():
                if query.value(0) > 0:
                    QMessageBox.warning(self, "Предупреждение", f"Тип '{new_name}' уже существует.")
                    return

            # Обновляем данные в модели
            if self.model.setData(self.model.index(row, 1), new_name):
                 if self.model.submitAll(): # Сохраняем изменение в базу данных
                    print(f"Тип успешно отредактирован на '{new_name}'.")
                    # model.select() не нужен
                 else:
                    print("Ошибка при сохранении изменений:", self.model.lastError().text())
                    QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить изменения: {self.model.lastError().text()}")
                    self.model.revertAll() # Отменяем изменения
            else:
                 print("Ошибка при установке данных в модель.")


    def _delete_type(self):
        """Удаляет выбранный тип объекта."""
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите тип для удаления.")
            return

        # Получаем индекс первой выбранной ячейки
        selected_index = selected_indexes[0]
        row = selected_index.row()

        # Получаем название типа для подтверждения
        type_name = self.model.data(self.model.index(row, 1), Qt.DisplayRole)

        # Запрашиваем подтверждение у пользователя
        reply = QMessageBox.question(self, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить тип '{type_name}'?\n"
                                     "Объекты инвентаризации, связанные с этим типом, потеряют свою категорию.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # Удаляем строку из модели
            if self.model.removeRow(row):
                if self.model.submitAll(): # Сохраняем изменение в базу данных
                    print(f"Тип '{type_name}' успешно удален.")
                    # model.select() не нужен
                else:
                    print("Ошибка при сохранении удаления:", self.model.lastError().text())
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить тип: {self.model.lastError().text()}")
                    self.model.revertAll() # Отменяем удаление
            else:
                print("Ошибка при удалении строки из модели.")
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить строку из модели.")

