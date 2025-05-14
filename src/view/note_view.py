# ui/note_view.py
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLabel, QMessageBox, QLineEdit,
                             QInputDialog,QFileDialog, QFormLayout, QTextEdit) # Используем QTextEdit для многострочного текста
from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlError
from PyQt5.QtCore import Qt, QModelIndex, QDate

# Импортируем универсальный обработчик CSV
from src.utils.csv_handler import import_data_from_csv, export_data_to_csv

# Импортируем схему базы данных
from database import DATABASE_SCHEMA

class NoteView(QWidget):
    def __init__(self, db_connection):
        super().__init__()

        self.db = db_connection
        if not self.db or not self.db.isOpen():
            print("Ошибка: Соединение с базой данных не установлено или закрыто.")
            return

        self.setWindowTitle("Управление заметками")

        self.layout = QVBoxLayout(self)

        info_label = QLabel("Управление заметками.")
        self.layout.addWidget(info_label)

        # --- Настройки модели и таблицы ---
        self.table_name = "Note" # Название таблицы
        self.column_names = [col.split()[0] for col in DATABASE_SCHEMA[self.table_name] if not col.strip().startswith("FOREIGN KEY")]
        self.unique_column = None # Для заметок уникальность не требуется

        self.model = QSqlTableModel(self, self.db)
        self.model.setTable(self.table_name)
        self.model.setEditStrategy(QSqlTableModel.OnFieldChange)
        self.model.select()

        header_labels = ["ID", "Текст заметки"]
        for i, header_text in enumerate(header_labels):
             if i < len(self.column_names):
                self.model.setHeaderData(i, Qt.Horizontal, header_text)

        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.hideColumn(0)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        # Для поля TEXT лучше использовать отдельный диалог или делегат для редактирования,
        # но для простоты пока разрешим редактирование в ячейке (может быть неудобно для длинного текста)
        self.table_view.setEditTriggers(QTableView.DoubleClicked | QTableView.SelectedClicked)
        # Опционально: установить делегат для QTextEdit
        # self.table_view.setItemDelegateForColumn(1, QTextEditDelegate(self)) # Потребуется создать QTextEditDelegate


        self.layout.addWidget(self.table_view)

        # --- Элементы для добавления новой записи ---
        add_form_layout = QFormLayout() # Используем QFormLayout для многострочного ввода

        self.note_text_input = QTextEdit() # Используем QTextEdit
        self.note_text_input.setPlaceholderText("Введите текст новой заметки")
        self.note_text_input.setFixedHeight(60) # Ограничиваем высоту

        add_form_layout.addRow("Текст заметки:", self.note_text_input)

        add_button = QPushButton("Добавить заметку")
        add_button.clicked.connect(self._add_item)

        add_layout = QVBoxLayout() # Используем QVBoxLayout для формы и кнопки
        add_layout.addLayout(add_form_layout)
        add_layout.addWidget(add_button, alignment=Qt.AlignRight) # Выравниваем кнопку справа

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
        self.model.primeInsert.connect(self._init_new_row)


    def _add_item(self):
        """Добавляет новую заметку в базу данных."""
        item_text = self.note_text_input.toPlainText().strip() # Используем toPlainText() для QTextEdit

        if not item_text:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, введите текст заметки.")
            return

        # Для заметок уникальность не требуется, просто добавляем
        row_count = self.model.rowCount()
        self.model.insertRow(row_count)
        # Столбец 1 - 'text'
        self.model.setData(self.model.index(row_count, 1), item_text)

        if self.model.submitAll():
            print(f"Заметка успешно добавлена.")
            self.note_text_input.clear()
        else:
            print("Ошибка при добавлении заметки:", self.model.lastError().text())
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить заметку: {self.model.lastError().text()}")
            self.model.revertAll()

    def _delete_selected_item(self):
        """Удаляет выбранную заметку."""
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите заметку для удаления.")
            return

        selected_index = selected_indexes[0]
        row = selected_index.row()

        # Получаем текст заметки для подтверждения (возможно, только начало)
        item_text = self.model.data(self.model.index(row, 1), Qt.DisplayRole) # Столбец 1 - text
        display_text = item_text if len(item_text) < 50 else item_text[:50] + "..." # Обрезаем для сообщения

        reply = QMessageBox.question(self, "Подтверждение удаления",
                                     f"Вы уверены, что хотите удалить заметку '{display_text}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.model.removeRow(row):
                if self.model.submitAll():
                    print(f"Заметка успешно удалена.")
                else:
                    print("Ошибка при сохранении удаления:", self.model.lastError().text())
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить заметку: {self.model.lastError().text()}")
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
            cols_to_import = [col for col in self.column_names if col != "id_note"]
            success, message = import_data_from_csv(self.db, file_path, self.table_name, cols_to_import, unique_column=self.unique_column)

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
        pass # Для Note нет специфичных значений по умолчанию

# Опциональный делегат для редактирования TEXT полей в QTextEdit
# from PyQt5.QtWidgets import QStyledItemDelegate, QTextEdit
# from PyQt5.QtCore import Qt
# class QTextEditDelegate(QStyledItemDelegate):
#     def createEditor(self, parent, option, index):
#         editor = QTextEdit(parent)
#         # Можно настроить размеры редактора
#         return editor

#     def setEditorData(self, editor, index):
#         value = index.model().data(index, Qt.EditRole)
#         editor.setPlainText(str(value))

#     def setModelData(self, editor, model, index):
#         model.setData(index, editor.toPlainText(), Qt.EditRole)

#     def updateEditorGeometry(self, editor, option, index):
#         editor.setGeometry(option.rect)

