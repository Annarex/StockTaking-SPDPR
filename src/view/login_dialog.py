# login_dialog.py
import sys
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QVBoxLayout,
                             QLineEdit, QLabel, QMessageBox, QFormLayout)
from PyQt5.QtCore import Qt

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Вход в систему инвентаризации")
        self.setFixedSize(300, 150) # Фиксированный размер окна

        self.layout = QVBoxLayout(self)

        self.form_layout = QFormLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Введите имя пользователя")
        self.username_input.setText("admin")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Введите пароль")
        self.password_input.setEchoMode(QLineEdit.Password) # Скрываем вводимый текст

        self.form_layout.addRow("Пользователь:", self.username_input)
        self.form_layout.addRow("Пароль:", self.password_input)

        self.layout.addLayout(self.form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)

        # Устанавливаем фокус на поле пароля при открытии
        self.password_input.setFocus()

    def get_credentials(self):
        """Возвращает введенные имя пользователя и пароль."""
        return self.username_input.text(), self.password_input.text()

    def validate_credentials(self, username, password):
        """
        Проверяет введенные учетные данные.
        Здесь должна быть ваша логика проверки (например, сравнение с хешем,
        проверка в базе данных и т.д.).
        Для примера используем простой фиксированный пароль.
        """
        # В реальном приложении НИКОГДА не храните пароль в открытом виде!
        # Используйте хеширование (например, bcrypt, scrypt).
        correct_username = "admin" # Пример
        correct_password = "123" # Пример

        return username == correct_username and password == correct_password

