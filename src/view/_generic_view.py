import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableView, QPushButton,
                             QHBoxLayout, QLabel, QMessageBox, QLineEdit)
from PyQt5.QtCore import pyqtSignal # Импортируем pyqtSignal

class GenericView(QWidget):
    add_item_requested = pyqtSignal()
    delete_item_requested = pyqtSignal(int)
    refresh_list_requested = pyqtSignal()
    import_csv_requested = pyqtSignal()
    export_csv_requested = pyqtSignal()

    def __init__(self, view_title="Управление справочником", add_input_placeholder="Введите новое наименование", parent=None):
        super().__init__(parent)

        self.setWindowTitle(view_title)

        self.layout = QVBoxLayout(self)

        info_label = QLabel(f"{view_title}. Редактирование возможно прямо в таблице.")
        self.layout.addWidget(info_label)

        self.table_view = QTableView()
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection) 
        self.table_view.setEditTriggers(QTableView.DoubleClicked | QTableView.SelectedClicked | QTableView.AnyKeyPressed)
        self.layout.addWidget(self.table_view)

        add_layout = QHBoxLayout()

        self.add_id_input = QLineEdit()
        self.add_id_input.setPlaceholderText("ID")

        add_layout.addWidget(self.add_id_input)
        
        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText(add_input_placeholder)

        add_layout.addWidget(self.add_input)

        add_button = QPushButton("Добавить")

        add_button.clicked.connect(self.add_item_requested.emit)
        add_layout.addWidget(add_button)

        self.layout.addLayout(add_layout)

        buttons_layout = QHBoxLayout()
        delete_button = QPushButton("Удалить выбранный")
        import_button = QPushButton("Импорт из CSV...")
        export_button = QPushButton("Экспорт в CSV...")
        refresh_button = QPushButton("Обновить список") 
        
        delete_button.clicked.connect(self._on_delete_button_clicked)
        import_button.clicked.connect(self.import_csv_requested.emit)
        export_button.clicked.connect(self.export_csv_requested.emit)
        refresh_button.clicked.connect(self.refresh_list_requested.emit)

        buttons_layout.addWidget(delete_button)
        buttons_layout.addWidget(import_button)
        buttons_layout.addWidget(export_button)
        buttons_layout.addWidget(refresh_button)
        buttons_layout.addStretch()

        self.layout.addLayout(buttons_layout)

    def set_model(self, model):
        self.table_view.setModel(model)

    def get_add_input_text(self):
        data = {
            'id': self.add_id_input.text().strip(),
            'name_column': self.add_input.text().strip(),
        }
        return data
    def clear_add_input(self):
        self.add_input.clear()
        self.add_input.clear()

    def get_selected_row(self):
        selected_indexes = self.table_view.selectedIndexes()
        if not selected_indexes:
            return -1
        return selected_indexes[0].row()

    def _on_delete_button_clicked(self):
        row = self.get_selected_row()
        if row == -1:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите элемент для удаления.")
            return
        self.delete_item_requested.emit(row)