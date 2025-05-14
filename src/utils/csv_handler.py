# extension/csv_handler.py
import csv
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlError
from PyQt5.QtCore import QVariant, QDate, QTime, QDateTime # Добавляем типы данных Qt

# Добавляем новый параметр column_digits
def import_data_from_csv(db_connection, file_path, table_name, column_names=None, column_digits=None, unique_column=None):
    if db_connection is None or not db_connection.isOpen():
        return False, "Ошибка: Соединение с базой данных не установлено или закрыто."

    imported_count = 0
    skipped_count = 0
    errors = []

    # Убеждаемся, что column_digits является словарем, если передан
    if column_digits is None:
        column_digits = {}
    elif not isinstance(column_digits, dict):
        errors.append("Предупреждение: Параметр column_digits должен быть словарем.")
        column_digits = {} # Сбрасываем, чтобы избежать ошибок

    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')

            try:
                header = next(reader)
                print(f"Заголовок CSV для {table_name}: {header}")
            except StopIteration:
                 return False, "Ошибка: CSV файл пуст."

            db_connection.transaction()
            placeholders = ', '.join(['?'] * len(column_names))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
            query = QSqlQuery(db_connection)
            query.prepare(insert_sql)

            # Подготовленный запрос для проверки уникальности, если unique_column указан
            check_query = None
            unique_col_index = -1
            if unique_column and unique_column in column_names:
                 unique_col_index = column_names.index(unique_column)
                 check_sql = f"SELECT COUNT(*) FROM {table_name} WHERE {unique_column} = ?"
                 check_query = QSqlQuery(db_connection)
                 check_query.prepare(check_sql)

            for row_num, row in enumerate(reader, start=2): # Начинаем с 2, т.к. 1 - заголовок
                if not row or all(not cell.strip() for cell in row): # Пропускаем пустые строки
                    continue

                # Проверяем, что количество столбцов в строке соответствует ожидаемому
                if len(row) != len(column_names):
                    errors.append(f"Строка {row_num}: Неверное количество столбцов ({len(row)} вместо {len(column_names)}). Пропущена.")
                    continue

                processed_row_data = []
                row_has_error = False

                # --- Обработка и форматирование данных строки ---
                for i, cell_value in enumerate(row):
                    col_name = column_names[i]
                    stripped_value = cell_value.strip()
                    formatted_value = stripped_value # По умолчанию используем исходное значение

                    # Проверяем, нужно ли форматировать этот столбец
                    if col_name in column_digits:
                        num_digits = column_digits[col_name]
                        if stripped_value: # Форматируем только непустые значения
                            try:
                                # Пытаемся преобразовать в число и отформатировать
                                int_value = int(stripped_value)
                                formatted_value = str(int_value).zfill(num_digits)
                            except ValueError:
                                # Если не удалось преобразовать в число, это ошибка для этого столбца
                                errors.append(f"Строка {row_num}, столбец '{col_name}': Значение '{stripped_value}' не является числом для форматирования. Строка пропущена.")
                                row_has_error = True
                                break # Пропускаем всю строку при ошибке форматирования

                    processed_row_data.append(formatted_value)

                if row_has_error:
                    continue # Пропускаем строку, если была ошибка форматирования

                # Проверка уникальности, если требуется
                if check_query and unique_col_index != -1:
                    # Используем уже обработанное (отформатированное) значение для проверки уникальности
                    unique_value = processed_row_data[unique_col_index]
                    if unique_value: # Проверяем только если значение не пустое
                        check_query.addBindValue(unique_value)
                        if check_query.exec_() and check_query.next() and check_query.value(0) > 0:
                            skipped_count += 1
                            # errors.append(f"Строка {row_num}: Запись с {unique_column} '{unique_value}' уже существует. Пропущена.")
                            continue # Пропускаем, если запись уже есть
                    # else:
                         # Если unique_column пустой, можно решить, что делать: пропустить или вставить с NULL
                         # Сейчас просто продолжаем, если unique_column пустой, и он не является PK NOT NULL


                # Добавляем обработанные данные строки в подготовленный запрос
                for value in processed_row_data:
                    query.addBindValue(value) # Добавляем каждое обработанное значение
                
                print("Обработанные значения:", ', '.join(str(v) for v in processed_row_data))
                
                # Выполняем запрос
                if query.exec_():
                    imported_count += 1
                else:
                    errors.append(f"Строка {row_num}: Ошибка базы данных при вставке ('{db_connection.lastError().text()}'). Пропущена.")
                    # Если произошла ошибка вставки, можно откатить транзакцию и прервать импорт
                    db_connection.rollback()
                    return False, f"Ошибка при вставке данных из строки {row_num}: {db_connection.lastError().text()}"


            # Завершаем транзакцию
            if db_connection.commit():
                 print("Транзакция импорта завершена успешно.")
            else:
                 db_connection.rollback()
                 return False, f"Ошибка при завершении транзакции: {db_connection.lastError().text()}"


    except FileNotFoundError:
        return False, f"Ошибка: Файл не найден по пути {file_path}"
    except Exception as e:
        # Откатываем транзакцию в случае любой другой ошибки
        if db_connection.transaction(): # Проверяем, активна ли транзакция
             db_connection.rollback()
        return False, f"Произошла ошибка при чтении или обработке файла: {e}"

    summary = f"Импорт завершен для таблицы '{table_name}'.\nУспешно импортировано: {imported_count}\nПропущено (существующие ID): {skipped_count}"
    if errors:
        summary += f"\nОшибки:\n" + "\n".join(errors)

    return True, summary


def export_data_to_csv(db_connection, file_path, table_name, column_names):
    """
    Экспортирует данные из указанной таблицы в CSV-файл.
    Разделитель - точка с запятой (;).
    """
    if db_connection is None or not db_connection.isOpen():
        return False, "Ошибка: Соединение с базой данных не установлено или закрыто."

    try:
        query = QSqlQuery(db_connection)
        select_sql = f"SELECT {', '.join(column_names)} FROM {table_name}"
        if not query.exec_(select_sql):
            return False, f"Ошибка при выполнении запроса к базе данных: {query.lastError().text()}"

        with open(file_path, mode='w', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(column_names)
            exported_count = 0
            while query.next():
                # Получаем значения, преобразуем в строку, обрабатываем None
                row_data = [str(query.value(i)) if query.value(i) is not None else '' for i in range(len(column_names))]
                writer.writerow(row_data)
                exported_count += 1

        summary = f"Экспорт завершен для таблицы '{table_name}'.\nЭкспортировано записей: {exported_count}"
        return True, summary

    except Exception as e:
        return False, f"Произошла ошибка при экспорте данных: {e}"
