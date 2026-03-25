from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from db import get_user_by_login, get_users_count, get_orders_count
from db import check_user, register_user, bind_telegram
from keyboards import admin_reply_keyboard, mentor_menu, start_keyboard, admin_menu, warehouse_menu

router = Router()


class LoginState(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()


class RegisterState(StatesGroup):
    waiting_for_login = State()
    waiting_for_name = State()
    waiting_for_password = State()


@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Для использования бота необходима авторизация в сервисе",
        reply_markup=start_keyboard()
    )


@router.message(Command("test"))
async def start(message: Message):
    telegram_id = message.from_user.id
    username_id = message.from_user.username

    import sqlite3
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # 🔥 ОБНОВЛЯЕМ username
    cursor.execute(
        "UPDATE users SET username_id=? WHERE telegram_id=?",
        (message.from_user.username, message.from_user.id)
    )
    print("Обновление юзернейм")
    conn.commit()

    # 🔍 ПОЛУЧАЕМ ИЗ БД
    cursor.execute(
        "SELECT telegram_id, username_id FROM users WHERE telegram_id=?",
        (telegram_id,)
    )
    db_user = cursor.fetchone()

    conn.close()

    text = (
        f"🧪 Проверка:\n\n"
        f"📱 TG ID: {telegram_id}\n"
        f"👤 Username TG: @{username_id if username_id else '❌'}\n\n"
        f"💾 В БД: {db_user}"
    )

    await message.answer(text)


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
    users_count = get_users_count()
    orders_count = get_orders_count()
    login = data.get("login")
    password = message.text

    result = check_user(login, password)

    


    if result:
        role = result[0]
        bind_telegram(login, message.from_user.id)
        username = get_user_by_login(login)

        if role == "admin":
            await message.answer(f"👑 Добро пожаловать\n👥Текущее кол-во зарегистрированных пользователей - {users_count}\n🛒Общее кол-во покупок - {orders_count}\n Ниже представлена панель для взаимодейтсвия с сервисом:", reply_markup=admin_reply_keyboard())
        elif role == "mentor":
            await message.answer(f"🧑‍🏫 Добро пожаловать {username[0]}\nДля взаимодействия с сервисом используйте нижний тулбар", reply_markup=mentor_menu())
        elif role == "warehouse":
            await message.answer(f"📦 Добро пожаловать {username[0]}\nВы отвечаете за склад\nДля взаимодействия с сервисом используйте нижний тулбар", reply_markup=warehouse_menu())
    else:
        await message.answer("❌ Неверный логин или пароль")

    await state.clear()


@router.callback_query(lambda c: c.data == "register")
async def register_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите код-наставника с *classy*:",parse_mode="Markdown")
    await state.set_state(RegisterState.waiting_for_login)
    await callback.answer()

@router.message(RegisterState.waiting_for_login)
async def reg_name(message: Message, state: FSMContext):
    await state.update_data(login=message.text)
    await message.answer("Введите свое ФИО:")
    await state.set_state(RegisterState.waiting_for_name)

@router.message(RegisterState.waiting_for_name)
async def reg_login(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Введите пароль:")
    await state.set_state(RegisterState.waiting_for_password)


@router.message(RegisterState.waiting_for_password)
async def reg_password(message: Message, state: FSMContext):
    data = await state.get_data()

    login = data.get("login")
    full_name = data.get("full_name")
    password = message.text
    telegram_id = message.from_user.id
    username_id = message.from_user.username or "unknown"

    if register_user(login, password, full_name, telegram_id, username_id):
        await message.answer("✅ Регистрация успешна!")
    else:
        await message.answer("❌ Пользователь уже существует")

    await state.clear()