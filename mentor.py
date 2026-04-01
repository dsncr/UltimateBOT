import sqlite3
from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from PIL import Image
import os
from aiogram.types import FSInputFile

from db import get_role_by_telegram, get_warehouse_full, get_warehouses

router = Router()



# =========================
# 📦 СОСТОЯНИЯ
# =========================
class ProfileState(StatesGroup):
    waiting_photo = State()
    waiting_name = State()


class ProblemState(StatesGroup):
    waiting_problem = State()

@router.message(ProfileState.waiting_photo, F.photo)
async def save_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]

    # 📥 скачать файл
    file = await message.bot.get_file(photo.file_id)
    file_path = file.file_path

    downloaded = await message.bot.download_file(file_path)

    # 📂 папка для фото
    os.makedirs("photos", exist_ok=True)

    filename = f"photos/{message.from_user.id}.jpg"

    # 🖼 обработка изображения
    image = Image.open(downloaded)
    # 📏 сначала уменьшаем с сохранением пропорций
    image.thumbnail((500, 500))

    # 📐 потом обрезаем по центру до 500x500
    width, height = image.size

    left = (width - 500) / 2
    top = (height - 500) / 2
    right = (width + 500) / 2
    bottom = (height + 500) / 2

    image = image.crop((left, top, right, bottom))

    # 💾 сохраняем
    image.save(filename, "JPEG")

    # 💾 сохранить путь в БД
    conn = sqlite3.connect("users.db", timeout=5)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET photo=? WHERE telegram_id=?",
        (filename, message.from_user.id)
    )

    conn.commit()
    conn.close()

    await message.answer("✅ Фото сохранено (500x500)")
    await state.clear()


@router.message(Command("whoami"))
async def whoami(message: Message):
    import sqlite3
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT login, role, telegram_id FROM users WHERE telegram_id=?",
        (message.from_user.id,)
    )

    user = cursor.fetchone()
    conn.close()

    await message.answer(f"{user}")

# =========================
# 👤 ПРОФИЛЬ
# =========================
@router.message(lambda m: "Мой профиль" in m.text)
async def my_profile(message: Message):
    conn = sqlite3.connect("users.db", timeout=5)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT login, full_name, password, points, photo
    FROM users WHERE telegram_id=?
    """, (message.from_user.id,))

    user = cursor.fetchone()
    conn.close()

    if not user:
        return await message.answer("❌ Профиль не найден")

    login, name, password, points, photo = user

    text = (
        f"👤 ФИО: {name}\n"
        f"🔑 Логин: @{login}\n"
        f"🔒 Пароль: {password[:10]}...\n"
        f"⭐ Баллы: {points}"
    )

    if photo and os.path.exists(photo):
        img = FSInputFile(photo)
        await message.answer_photo(img, caption=text, reply_markup=profile_keyboard())
    else:
        await message.answer(text, reply_markup=profile_keyboard())

# =========================
# ✏️ РЕДАКТИРОВАНИЕ
# =========================
@router.callback_query(lambda c: c.data == "edit_profile")
async def edit_profile(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое ФИО:")
    await state.set_state(ProfileState.waiting_name)
    await callback.answer()


@router.message(ProfileState.waiting_name)
async def save_name(message: Message, state: FSMContext):
    conn = sqlite3.connect("users.db", timeout=5)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET full_name=? WHERE telegram_id=?",
        (message.text, message.from_user.id)
    )

    conn.commit()
    conn.close()

    await message.answer("✅ Данные обновлены")
    await state.clear()


# =========================
# 📸 ФОТО
# =========================
@router.callback_query(lambda c: c.data == "upload_photo")
async def upload_photo(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте фотографию")
    await state.set_state(ProfileState.waiting_photo)
    await callback.answer()




# =========================
# 🛍 МАГАЗИН
# =========================
def products_keyboard(products):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{p[1]} ({p[3]}⭐)",
            callback_data=f"product:{p[0]}"
        )]
        for p in products
    ])

def product_keyboard(product_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy:{product_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_shop")]
    ])


@router.message(lambda m: m.text == "🛍 Магазин мерча")
async def shop(message: Message):
    conn = sqlite3.connect("users.db", timeout=5)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()

    if not products:
        return await message.answer("🛒 Магазин пуст")

    await message.answer(
        "🛍 Выберите товар:",
        reply_markup=products_keyboard(products)
    )


# =========================
# 📦 ТОВАР
# =========================
@router.callback_query(lambda c: c.data.startswith("product:"))
async def product_view(callback: CallbackQuery):
    product_id = callback.data.split(":")[1]

    conn = sqlite3.connect("users.db", timeout=5)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
    p = cursor.fetchone()
    conn.close()

    if not p:
        return await callback.answer("Не найден", show_alert=True)

    _, name, desc, price, qty, photo, _, _ = p

    text = (
        f"📦 *{name}*\n\n"
        f"{desc}\n\n"
        f"⭐ *Цена: {price}*\n"
        f"📦 *Осталось: {qty}*"
    )

    if photo and os.path.exists(photo):
        img = FSInputFile(photo)
        await callback.message.answer_photo(
            img,
            caption=text,
            reply_markup=product_keyboard(product_id),
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer(
            text,
            reply_markup=product_keyboard(product_id),
            parse_mode="Markdown"
        )

    await callback.answer()

def get_user_orders(telegram_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT p.name, p.description, p.price, o.created_at
    FROM orders o
    JOIN products p ON o.product_id = p.id
    WHERE o.user_id=?
    ORDER BY o.created_at DESC
    """, (telegram_id,))

    orders = cursor.fetchall()
    conn.close()

    return orders    

@router.message(lambda m: m.text == "📦 Мои заказы")
async def my_orders(message: Message):
    orders = get_user_orders(message.from_user.id)

    if not orders:
        return await message.answer("📦 У вас пока нет заказов")

    text = "📦 <b>Ваши заказы:</b>\n\n"

    for name, desc, price, date in orders:
        text += (
            f"🛍 <b>{name}</b>\n"
            f"⭐ {price} баллов\n"
            f"📅 {date}\n\n"
        )

    await message.answer(text, parse_mode="HTML")

@router.callback_query(lambda c: c.data.startswith("buy:"))
async def buy_product(callback: CallbackQuery):
    product_id = callback.data.split(":")[1]

    conn = sqlite3.connect("users.db", timeout=5)
    cursor = conn.cursor()

    # товар
    cursor.execute("SELECT name, price, quantity FROM products WHERE id=?", (product_id,))
    product = cursor.fetchone()

    # пользователь
    cursor.execute("SELECT points FROM users WHERE telegram_id=?", (callback.from_user.id,))
    user = cursor.fetchone()

    if not product or not user:
        return await callback.answer("Ошибка", show_alert=True)

    name, price, qty = product
    points = user[0]

    if qty <= 0:
        return await callback.answer("❌ Нет в наличии", show_alert=True)

    if points < price:
        return await callback.answer("❌ Недостаточно баллов", show_alert=True)

    # 🔥 СПИСАНИЕ
    cursor.execute(
        "UPDATE users SET points = points - ? WHERE telegram_id=?",
        (price, callback.from_user.id)
    )

    cursor.execute(
        "UPDATE products SET quantity = quantity - 1 WHERE id=?",
        (product_id,)
    )

    # 🔥 СОХРАНЯЕМ ЗАКАЗ (ГЛАВНОЕ)
    cursor.execute(
        "INSERT INTO orders (user_id, product_id) VALUES (?, ?)",
        (callback.from_user.id, product_id)
    )

    conn.commit()  # 🔥 ОБЯЗАТЕЛЬНО

    # =========================
    # дальше уведомления
    # =========================

    buyer_username = callback.from_user.username or "без_username"
    warehouse = get_warehouse_full()

    if warehouse:
        tg_id, username = warehouse

        if username and not username.isdigit():
            text_username = f"@{username}"
        else:
            text_username = "без username (напишите по ID)"

        await callback.message.answer(
            f"✅ Вы купили: {name}\n📦 Напишите: {text_username}"
        )

        try:
            await callback.bot.send_message(
                chat_id=tg_id,
                text=(
                    f"🛒 Покупка!\n\n"
                    f"👤 @{buyer_username}\n"
                    f"📦 Товар: {name}\n"
                    f"📉 Осталось: {qty - 1}"
                )
            )
        except:
            pass
    else:
        await callback.message.answer(
            "❌ Кладовщик не назначен"
        )

    conn.close()
    await callback.answer()

@router.callback_query(lambda c: c.data == "back_shop")
async def back_to_shop(callback: CallbackQuery):
    import sqlite3

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()

    if not products:
        return await callback.answer("Магазин пуст", show_alert=True)

    # 🔥 УДАЛЯЕМ текущее сообщение (фото товара)
    try:
        await callback.message.delete()
    except:
        pass  # если вдруг нельзя удалить — просто игнорим

    await callback.answer()

# =========================
# ⚠️ ПРОБЛЕМА (FSM)
# =========================
@router.message(lambda m: m.text == "⚠️ Сообщить о проблеме")
async def report_problem(message: Message, state: FSMContext):
    await message.answer("Опишите проблему:")
    await state.set_state(ProblemState.waiting_problem)


@router.message(ProblemState.waiting_problem)
async def send_problem(message: Message, state: FSMContext):
    await message.bot.send_message(
        chat_id= 7501101474,  # 🔥 ВСТАВЬ СЮДА СВОЙ ID   1131263072
        text=f"⚠️ Сообщение от @{message.from_user.username}:\n\n{message.text}"
    )

    await message.answer("✅ Отправлено")
    await state.clear()


# =========================
# 🔘 КНОПКИ
# =========================
def profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Загрузить фото", callback_data="upload_photo")],
        [InlineKeyboardButton(text="✏️ Изменить данные", callback_data="edit_profile")]
    ])