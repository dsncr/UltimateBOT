import sqlite3
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    MENTOR = "mentor"
    WAREHOUSE = "warehouse"


# 🔥 единая точка подключения
def get_connection():
    return sqlite3.connect("users.db", timeout=5)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'mentor'
    )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN telegram_id INTEGER")
        cursor.execute("ALTER TABLE users ADD COLUMN username_id TEXT")
        cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
        cursor.execute("ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN photo TEXT")
    except sqlite3.OperationalError:
        pass

    # ✅ передаём cursor, а не создаём новое соединение
    create_products_table(cursor)
    seed_products()
    create_default_admin(cursor)

    conn.commit()
    conn.close()

def get_users_count():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    conn.close()
    return count

def get_user_by_login(login: str):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT full_name, role FROM users WHERE login=?
    """, (login,))

    user = cursor.fetchone()
    conn.close()

    return user

def get_orders_count():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM orders")  # если есть таблица заказов
    count = cursor.fetchone()[0]

    conn.close()
    return count

# 🔥 теперь без нового подключения
def create_products_table(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        price INTEGER,
        quantity INTEGER,
        photo1 TEXT,
        photo2 TEXT,
        photo3 TEXT
    )
    """)


def hash_password(password: str):
    import hashlib
    return hashlib.sha256(password.lower().encode()).hexdigest()


def bind_telegram(login: str, telegram_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET telegram_id=? WHERE login=?",
        (telegram_id, login)
    )

    conn.commit()
    conn.close()


def get_role_by_telegram(telegram_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role FROM users WHERE telegram_id=?",
        (telegram_id,)
    )

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


def create_default_admin(cursor):
    login = "slippery-blue-cobra"
    password = hash_password("derzhava")

    cursor.execute("SELECT * FROM users WHERE login=?", (login,))
    exists = cursor.fetchone()

    if not exists:
        cursor.execute("""
        INSERT INTO users (login, password, role)
        VALUES (?, ?, ?)
        """, (login, password, UserRole.ADMIN.value))


def check_user(login: str, password: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role FROM users WHERE login=? AND password=?",
        (login, hash_password(password))
    )

    result = cursor.fetchone()
    conn.close()

    return result



def register_user(login: str, password: str, name: str, username_id:str, telegram_id:str):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (login, password, role , full_name, telegram_id, username_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
            login,
            hash_password(password),
            UserRole.MENTOR.value,
            name,
            telegram_id,
            username_id
            )
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_mentors():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT login FROM users WHERE role=?",
        (UserRole.MENTOR.value,)
    )

    users = cursor.fetchall()
    conn.close()

    return [u[0] for u in users]

def get_warehouse_full():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    from db import UserRole

    cursor.execute("""
    SELECT telegram_id, username_id 
    FROM users 
    WHERE role=? 
    LIMIT 1
    """, (UserRole.WAREHOUSE.value,))

    user = cursor.fetchone()
    conn.close()

    return user  # может быть None — это нормально

def get_warehouses():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT login FROM users WHERE role=?
    """, ("warehouse",))

    users = cursor.fetchall()
    conn.close()

    return [u[0] for u in users]


def set_role(login: str, role: UserRole):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET role=? WHERE login=?",
        (role.value, login)
    )

    conn.commit()
    conn.close()

def seed_products():
    conn = sqlite3.connect("users.db", timeout=5)
    cursor = conn.cursor()

    products = [
        ("ВЕРЁВКА ДЛЯ ТЕЛЕФОНА", "Удобная зеленая веревка для телефона, с которой можно носить телефон через плечо", 10, 10, "photos/merch/brelok.jpg"),
        ("РУЧКА «Я В ДЕЛЕ»", "Брендированная ручка *«Я в деле»*, надежная, долговечная ", 10, 10, "photos/merch/ruchka.jpg"),
        ("МИНИ-ШОППЕР", "Компактная брендированная сумка, которую удобно носить с собой", 10, 10, "photos/merch/shopper.jpg"),
        ("ПИН «Я В ДЕЛЕ»", "Данный пин, является одним из стареших атрибутов нашей программы, подходит для официальных и торжественных мероприятий", 15, 10, "photos/merch/stickerpack.jpg"),
        ("БЛОКНОТ «Я В ДЕЛЕ»", "Фирменный блокнот, выдается победителям на турнирах в университетах", 15, 10, "photos/merch/bloknot.jpg"),
        ("КАРТХОЛДЕР", "Красивый зеленый картхолдер, почти как у Тинькова", 20, 10, "photos/merch/cardholder.jpg"),
        ("ОБЛОЖКА НА ПАСПОРТ", "Брендированная обложка на паспорт", 30, 10, "photos/merch/passport.jpg"),
        ("ФУТБОЛКА", "Черная футболка *«Я в деле»*, выдавалась наставникам 7 сезона на июльке ", 50, 10, "photos/merch/t-shirt.jpg"),
        ("РУБАШКА ЧЕРНАЯ", "Рубашка старшего наставника, выдавалась всем старшим наставникам 8 сезона", 70, 10, "photos/merch/blackjacket.jpg"),
        ("РУБАШКА С. ТЕРЕХОВА", "Премиум", 250, 10, "photos/merch/greenjacket.jpg"),
        ("БОМБЕР РУКОВОДИТЕЛЯ", "Эксклюзив, выдается за особые заслуги", 600, 10, "photos/merch/bomber.jpg"),
    ]

    for p in products:
        cursor.execute("SELECT * FROM products WHERE name=?", (p[0],))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO products (name, description, price, quantity, photo1)
            VALUES (?, ?, ?, ?, ?)
            """, p)

    conn.commit()
    conn.close()

def get_user_role(login: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT role FROM users WHERE login=?", (login,))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None