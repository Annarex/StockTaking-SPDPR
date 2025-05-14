# app.py
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog
from ui.main_window import MainWindow # Импортируем класс главного окна
from database import connect_db, create_all_tables, close_db # Импортируем функции для работы с БД
from ui.login_dialog import LoginDialog # Импортируем класс диалога входа

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # --- Шаг 1: Показать диалог входа ---
    login_dialog = LoginDialog()
    # exec_() запускает диалог как модальное окно и блокирует выполнение до его закрытия
    if login_dialog.exec_() == QDialog.Accepted:
        # Если пользователь нажал OK, получаем введенные данные
        username, password = login_dialog.get_credentials()

        # Проверяем учетные данные
        if True: #login_dialog.validate_credentials(username, password):
            print("Вход выполнен успешно.")
            db_connection = connect_db()
            if db_connection:
                create_all_tables(db_connection)
            else:
                QMessageBox.critical(None, "Ошибка базы данных", "Не удалось подключиться к базе данных.")
                sys.exit(1)
                
            main_window = MainWindow(db_connection)
            main_window.show()

            # Запуск основного цикла приложения
            exit_code = app.exec_()

            # Закрытие соединения с базой данных при завершении приложения
            close_db(db_connection)

            sys.exit(exit_code)
        else:
            # Если учетные данные неверны
            QMessageBox.warning(None, "Ошибка входа", "Неверное имя пользователя или пароль.")
            sys.exit(1) # Выходим из приложения
    else:
        # Если пользователь нажал Cancel в диалоге входа
        print("Вход отменен пользователем.")
        sys.exit(0) # Выходим из приложения без ошибки

