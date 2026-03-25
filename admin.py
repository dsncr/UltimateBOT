import sqlite3

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from db import get_users_count, get_orders_count

from db import set_role, UserRole, get_role_by_telegram, hash_password
from keyboards import (
    mentor_keyboard,
    admin_menu,
    back_to_admin,
    warehouse_keyboard
)

router = Router()
PAGE_SIZE = 5


class AdminState(StatesGroup):
    create_login = State()
    create_password = State()
    create_name = State()

    give_points_amount = State()
    edit_value = State()


def is_admin(user_id: int):
    return get_role_by_telegram(user_id) == "admin"


async def safe_edit(callback: CallbackQuery, text: str, keyboard=None):
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer(text, reply_markup=keyboard)


# =========================
# 👑 ОТКРЫТЬ ПАНЕЛЬ
# =========================
@router.message(lambda m: m.text == "👑 Админ-панель")
async def open_admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Нет доступа")

    await message.answer("👑 Админ-панель:", reply_markup=admin_menu())


# =========================
# ➕ СОЗДАНИЕ
# =========================
@router.callback_query(lambda c: c.data == "admin_create")
async def admin_create(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)

    await callback.message.answer("Введите логин:")
    await state.set_state(AdminState.create_login)
    await callback.answer()


@router.message(AdminState.create_login)
async def create_login(message: Message, state: FSMContext):
    await state.update_data(login=message.text)
    await message.answer("Введите пароль:")
    await state.set_state(AdminState.create_password)


@router.message(AdminState.create_password)
async def create_password(message: Message, state: FSMContext):
    await state.update_data(password=message.text)
    await message.answer("Введите ФИО:")
    await state.set_state(AdminState.create_name)


@router.message(AdminState.create_name)
async def create_name(message: Message, state: FSMContext):
    data = await state.get_data()

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO users (login, password, role, full_name)
        VALUES (?, ?, ?, ?)
        """, (
            data["login"],
            hash_password(data["password"]),
            UserRole.MENTOR.value,
            message.text
        ))

        conn.commit()
        await message.answer("✅ Создан", reply_markup=back_to_admin())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=back_to_admin())

    conn.close()
    await state.clear()

# =========================
# ❌ УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
# =========================
@router.callback_query(lambda c: c.data.startswith("user_delete:"))
async def delete_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)

    login = callback.data.split(":")[1]

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE login=?", (login,))
    conn.commit()
    conn.close()

    await safe_edit(
        callback,
        f"❌ Пользователь @{login} удалён",
        back_to_admin()
    )
    await callback.answer()

# =========================
# 📋 СПИСОК
# =========================
def users_keyboard(users, page=0):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    keyboard = []

    for login, name in users[start:end]:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{name or login} (@{login})",
                callback_data=f"user_view:{login}:{page}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"page:{page-1}"))
    if end < len(users):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"page:{page+1}"))

    if nav:
        keyboard.append(nav)

    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_admin")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(lambda c: c.data == "admin_list")
async def list_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT login, full_name FROM users")
    users = cursor.fetchall()
    conn.close()

    await safe_edit(callback, "📋 Выберите пользователя:", users_keyboard(users))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("page:"))
async def paginate(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT login, full_name FROM users")
    users = cursor.fetchall()
    conn.close()

    await safe_edit(callback, "📋 Выберите пользователя:", users_keyboard(users, page))
    await callback.answer()


# =========================
# 👤 КАРТОЧКА
# =========================
def user_actions_keyboard(login, page):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Баллы", callback_data=f"user_points:{login}")],
        [InlineKeyboardButton(text="✏️ Изменить", callback_data=f"user_edit:{login}")],
        [InlineKeyboardButton(text="❌ Удалить", callback_data=f"user_delete:{login}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{page}")]
    ])


@router.callback_query(lambda c: c.data.startswith("user_view:"))
async def view_user(callback: CallbackQuery):
    _, login, page = callback.data.split(":")
    page = int(page)

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT login, full_name, role, points FROM users WHERE login=?", (login,))
    user = cursor.fetchone()
    conn.close()

    login, name, role, points = user

    text = f"""👤 {name or 'Не указано'}
🔑 @{login}
🎭 {role}
⭐ {points}"""

    await safe_edit(callback, text, user_actions_keyboard(login, page))
    await callback.answer()


# =========================
# ⭐ БАЛЛЫ
# =========================
@router.callback_query(lambda c: c.data.startswith("user_points:"))
async def start_points(callback: CallbackQuery, state: FSMContext):
    login = callback.data.split(":")[1]

    await state.update_data(user=login)
    await callback.message.answer(f"Введите баллы для @{login}:")
    await state.set_state(AdminState.give_points_amount)
    await callback.answer()


@router.message(AdminState.give_points_amount)
async def add_points(message: Message, state: FSMContext):
    data = await state.get_data()

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET points = points + ? WHERE login=?",
        (int(message.text), data["user"])
    )

    conn.commit()
    conn.close()

    await message.answer("✅ Баллы начислены", reply_markup=back_to_admin())
    await state.clear()


# =========================
# ✏️ РЕДАКТИРОВАНИЕ
# =========================
@router.callback_query(lambda c: c.data.startswith("user_edit:"))
async def start_edit(callback: CallbackQuery, state: FSMContext):
    login = callback.data.split(":")[1]

    await state.update_data(user=login)
    await callback.message.answer(f"Введите новое ФИО для @{login}:")
    await state.set_state(AdminState.edit_value)
    await callback.answer()


@router.message(AdminState.edit_value)
async def save_edit(message: Message, state: FSMContext):
    data = await state.get_data()

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET full_name=? WHERE login=?",
        (message.text, data["user"])
    )

    conn.commit()
    conn.close()

    await message.answer("✅ Обновлено", reply_markup=back_to_admin())
    await state.clear()


# =========================
# 📦 СКЛАД
# =========================
@router.callback_query(lambda c: c.data == "admin_set_warehouse")
async def set_wh(callback: CallbackQuery):
    await safe_edit(callback, "Выберите:", mentor_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("set_warehouse:"))
async def do_set_wh(callback: CallbackQuery):
    login = callback.data.split(":")[1]
    set_role(login, UserRole.WAREHOUSE)

    await safe_edit(callback, f"📦 {login} назначен", back_to_admin())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_remove_warehouse")
async def remove_wh_start(callback: CallbackQuery):
    await safe_edit(callback, "Выберите кладовщика:", warehouse_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("remove_warehouse:"))
async def remove_wh(callback: CallbackQuery):
    login = callback.data.split(":")[1].lower()
    set_role(login, UserRole.MENTOR)

    await safe_edit(callback, f"❌ {login} снят", back_to_admin())
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет доступа", show_alert=True)

    users_count = get_users_count()
    orders_count = get_orders_count()

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # 💰 суммарные баллы
    cursor.execute("SELECT SUM(points) FROM users")
    total_points = cursor.fetchone()[0] or 0

    # 📦 товары на складе
    cursor.execute("SELECT SUM(quantity) FROM products")
    total_products = cursor.fetchone()[0] or 0

    conn.close()

    text = f"""📊 <b>Статистика системы</b>

👥 Пользователей: {users_count}
🛒 Покупок: {orders_count}
⭐ Всего баллов: {total_points}
📦 Товаров на складе: {total_products}
"""

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=back_to_admin()
    )

    await callback.answer()

# =========================
# ⬅️ НАЗАД
# =========================
@router.callback_query(lambda c: c.data == "back_admin")
async def back_admin(callback: CallbackQuery):
    await safe_edit(callback, "👑 Админ-панель:", admin_menu())
    await callback.answer()