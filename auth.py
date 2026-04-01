from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db import get_role_by_telegram, get_user_by_login, get_users_count, get_orders_count
from db import check_user, bind_telegram
from keyboards import admin_reply_keyboard, mentor_menu, start_keyboard, warehouse_menu

router = Router()


# =========================
# 🔐 СОСТОЯНИЯ
# =========================
class LoginState(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()


# =========================
# 🚀 START
# =========================
@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🔐 Введите код наставника для входа",
        reply_markup=start_keyboard()
    )

@router.message(Command("start-test"))
async def start(message: Message):
    role = get_role_by_telegram(message.from_user.id)

    if role:
        await message.answer("✅ Вы уже авторизованы")
        return

    await message.answer("🔐 Войдите в систему")

# =========================
# 🔐 АВТОРИЗАЦИЯ
# =========================
@router.callback_query(lambda c: c.data == "login")
async def login_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите код наставника:")
    await state.set_state(LoginState.waiting_for_login)
    await callback.answer()


@router.message(LoginState.waiting_for_login)
async def get_login(message: Message, state: FSMContext):
    await state.update_data(login=message.text)
    await message.answer("Введите пароль:")
    await state.set_state(LoginState.waiting_for_password)


@router.message(LoginState.waiting_for_password)
async def get_password(message: Message, state: FSMContext):
    data = await state.get_data()

    login = data.get("login")
    password = message.text

    result = check_user(login, password)

    if result:
        role = result[0]

        # 🔥 привязка Telegram
        bind_telegram(login, message.from_user.id)

        # 🔥 сохраняем username
        import sqlite3
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET username_id=? WHERE telegram_id=?",
            (message.from_user.username, message.from_user.id)
        )
        conn.commit()
        conn.close()

        username = get_user_by_login(login)

        users_count = get_users_count()
        orders_count = get_orders_count()

        if role == "admin":
            await message.answer(
                f"👑 Добро пожаловать\n"
                f"👥 Пользователей: {users_count}\n"
                f"🛒 Покупок: {orders_count}",
                reply_markup=admin_reply_keyboard()
            )

        elif role == "mentor":
            await message.answer(
                f"🧑‍🏫 Добро пожаловать {username[0]}",
                reply_markup=mentor_menu()
            )

        elif role == "warehouse":
            await message.answer(
                f"📦 Добро пожаловать {username[0]}\nВы отвечаете за склад",
                reply_markup=warehouse_menu()
            )

    else:
        await message.answer("❌ Неверный логин или пароль")

    await state.clear()