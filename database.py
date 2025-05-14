# database.py
import sys
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlError

# Используем имя базы данных, которое вы указали
def connect_db(db_name="st.db"):
    db = QSqlDatabase.addDatabase("QSQLITE")
    db.setDatabaseName(db_name)

    if not db.open():
        print(f"Ошибка: Не удалось открыть базу данных {db_name}")
        print(db.lastError().text())
        return None

    print(f"Успешно подключено к базе данных {db_name}")
    return db

def close_db(db):
    if db is not None and db.isOpen():
        db.close()
        print("Соединение с базой данных закрыто.")

# --- Определение схемы базы данных ---
# Используем словарь, где ключ - название таблицы, значение - список определений столбцов
# Каждое определение столбца - это строка SQL (например, "column_name INTEGER PRIMARY KEY")
DATABASE_SCHEMA = {
    "Category": [
        "id_category VARCHAR(2) PRIMARY KEY",
        "category VARCHAR(40) UNIQUE NOT NULL"       
    ],
    "Subcategory": [
        "id_category VARCHAR(2)", 
        "id_subcategory VARCHAR(2)",
        "subcategory VARCHAR(40) NOT NULL",
        "FOREIGN KEY (id_category) REFERENCES Category(id_category) ON DELETE SET NULL" # Добавлен FK
    ],
    "Unit_type": [
        "id_unit_type INTEGER PRIMARY KEY AUTOINCREMENT",
        "unit_type VARCHAR(30) UNIQUE NOT NULL"
    ],
    "Order_status": [
        "id_order_status INTEGER PRIMARY KEY AUTOINCREMENT",
        "order_status VARCHAR(30) UNIQUE NOT NULL"
    ],
    "Units_inventory": [
        "id_unit_inventory INTEGER PRIMARY KEY AUTOINCREMENT",
        "id_category VARCHAR(2)",
        "id_subcategory VARCHAR(2)",
        "cabinet VARCHAR(6)",
        "manufacturer VARCHAR(60)",
        "model VARCHAR(30)",
        "series VARCHAR(30)",
        "unit_count INTEGER",
        "id_unit_type INTEGER",
        "serial_number VARCHAR(60)",
        "inventory_number VARCHAR(60)",
        "date_order_buhgaltery DATE",
        "id_order_status INTEGER",
        "date_issue DATE",
        "notice TEXT",
        # Добавлены FOREIGN KEYs
        "FOREIGN KEY (id_category) REFERENCES Category(id_category) ON DELETE SET NULL",
        "FOREIGN KEY (id_subcategory) REFERENCES Subcategory(id_subcategory) ON DELETE SET NULL",
        "FOREIGN KEY (id_unit_type) REFERENCES Unit_type(id_unit_type) ON DELETE SET NULL",
        "FOREIGN KEY (id_order_status) REFERENCES Order_status(id_order_status) ON DELETE SET NULL"
    ],
    "Units_extended_info": [
        "id_unit_inventory INTEGER PRIMARY KEY UNIQUE", # PK и FK
        "device_name VARCHAR(100)",
        "ip VARCHAR(45)",
        "mac VARCHAR(45)",
        "admin_login VARCHAR(20)",
        "admin_password VARCHAR(20)",
        "user_login VARCHAR(20)",
        "user_password VARCHAR(20)",
        "FOREIGN KEY (id_unit_inventory) REFERENCES Units_inventory(id_unit_inventory) ON DELETE CASCADE" # FK
    ],
    "Employee": [
        "id_employee INTEGER PRIMARY KEY",
        "fio VARCHAR(60) NOT NULL",
        "cabinet VARCHAR(6)",
        "id_department VARCHAR(2)",
        "post VARCHAR(50)",
        "account VARCHAR(50)",
        "ids_group_dc VARCHAR(50)",
        "work_pc VARCHAR(40)",
        "work_pc_ip VARCHAR(45)",
        "telephone VARCHAR(20)",
        "mail VARCHAR(50)",
        
    ],
    "Departments": [
        "id_department VARCHAR(2)",
        "department_fullname VARCHAR(50) UNIQUE NOT NULL",
        "department_shortname VARCHAR(50)"
    ],
    "GroupDC": [
        "id_group_dc VARCHAR(2)",
        "group_dc VARCHAR(20) UNIQUE NOT NULL"
    ],
    "Note": [
        "id_note INTEGER PRIMARY KEY AUTOINCREMENT",
        "section VARCHAR(50)",
        "title VARCHAR(50)",
        "text TEXT"  
    ]
}

# --- Отдельные функции для создания каждой таблицы ---

def create_table(db, table_name, column_definitions):
    """Универсальная функция для создания одной таблицы."""
    if db is None or not db.isOpen():
        print(f"Ошибка: База данных не открыта для создания таблицы {table_name}.")
        return False

    query = QSqlQuery(db)
    create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_definitions)})"
    print(f"Выполнение SQL для {table_name}: {create_table_sql}") # Для отладки

    # Включаем поддержку внешних ключей в SQLite, если она еще не включена
    # Это нужно делать для каждого соединения
    enable_fk_query = QSqlQuery("PRAGMA foreign_keys = ON;", db)
    if not enable_fk_query.exec_():
        print("Предупреждение: Не удалось включить поддержку внешних ключей.")
        print(enable_fk_query.lastError().text())


    if not query.exec_(create_table_sql):
        print(f"Ошибка при создании таблицы '{table_name}':")
        print(query.lastError().text())
        return False
    print(f"Таблица '{table_name}' проверена/создана.")
    return True

# Функции для создания каждой конкретной таблицы
def create_category_table(db):
    return create_table(db, "Category", DATABASE_SCHEMA["Category"])

def create_subcategory_table(db):
    return create_table(db, "Subcategory", DATABASE_SCHEMA["Subcategory"])

def create_unit_type_table(db):
    return create_table(db, "Unit_type", DATABASE_SCHEMA["Unit_type"])

def create_order_status_table(db):
    return create_table(db, "Order_status", DATABASE_SCHEMA["Order_status"])

def create_units_inventory_table(db):
    return create_table(db, "Units_inventory", DATABASE_SCHEMA["Units_inventory"])

def create_units_extended_info_table(db):
    return create_table(db, "Units_extended_info", DATABASE_SCHEMA["Units_extended_info"])

def create_employee_table(db):
    return create_table(db, "Employee", DATABASE_SCHEMA["Employee"])

def create_departments_table(db):
    return create_table(db, "Departments", DATABASE_SCHEMA["Departments"])

def create_group_dc_table(db):
    return create_table(db, "GroupDC", DATABASE_SCHEMA["GroupDC"])

def create_note_table(db):
    return create_table(db, "Note", DATABASE_SCHEMA["Note"])



# --- Главная функция создания всех таблиц ---
def create_all_tables(db):
    if db is None or not db.isOpen():
        print("Ошибка: База данных не открыта для создания всех таблиц.")
        return False

    query = QSqlQuery(db)
    if not query.exec_("PRAGMA foreign_keys = ON;"):
         print("Предупреждение: Не удалось включить поддержку внешних ключей перед созданием таблиц.")
         print(query.lastError().text())

    success = True
    if not create_category_table(db): success = False
    if not create_subcategory_table(db): success = False # Зависит от Category
    if not create_unit_type_table(db): success = False
    if not create_order_status_table(db): success = False
    if not create_units_inventory_table(db): success = False # Зависит от Category, Subcategory, Unit_type, Order_status
    if not create_units_extended_info_table(db): success = False # Зависит от Units_inventory
    if not create_employee_table(db): success = False
    if not create_departments_table(db): success = False
    if not create_group_dc_table(db): success = False
    if not create_note_table(db): success = False
    return success