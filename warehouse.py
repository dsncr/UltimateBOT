from db import get_role_by_telegram
import sqlite3
from aiogram import F
from aiogram import Router
from aiogram.types import KeyboardButton, Message, CallbackQuery, InputMediaPhoto, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from PIL import Image
import os
from aiogram.types import FSInputFile

def is_warehouse(user_id):
    return get_role_by_telegram(user_id) == "warehouse"

router = Router()

class WarehouseState(StatesGroup):
    waiting_points = State()
    waiting_quantity = State()
    waiting_user = State()      # можно оставить если используешь
    waiting_product = State()   # можно оставить

def products_select_keyboard(products):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{p[1]} ({p[4]} шт.)",
            callback_data=f"wh_product:{p[0]}"
        )]
        for p in products
    ])

def users_select_keyboard(users):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{u[1] or u[0]} (@{u[0]})",
            callback_data=f"wh_user:{u[0]}"
        )]
        for u in users
    ])

@router.message(lambda m: m.text == "📊 Статистика")
async def warehouse_stats(message: Message):
    if not is_warehouse(message.from_user.id):
        return await message.answer("Нет доступа")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM orders")
    orders_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT p.name, COUNT(o.id)
        FROM orders o
        JOIN products p ON o.product_id = p.id
        GROUP BY p.name
        ORDER BY COUNT(o.id) DESC
        LIMIT 5
    """)
    top_products = cursor.fetchall()

    conn.close()

    text = f"📊 Статистика:\n\n🛒 Заказов: {orders_count}\n\n🔥 Топ товары:\n"

    for name, count in top_products:
        text += f"• {name} — {count}\n"

    await message.answer(text)

@router.message(lambda m: m.text == "⭐ Начислить баллы")
async def give_points_start(message: Message):
    if not is_warehouse(message.from_user.id):
        return

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT login, full_name FROM users")
    users = cursor.fetchall()
    conn.close()

    await message.answer(
        "👤 Выберите пользователя:",
        reply_markup=users_select_keyboard(users)
    )

@router.callback_query(lambda c: c.data.startswith("wh_user:"))
async def select_user(callback: CallbackQuery, state: FSMContext):
    login = callback.data.split(":")[1]

    await state.update_data(login=login)
    await callback.message.answer("Введите количество баллов:")
    await state.set_state(WarehouseState.waiting_points)

    await callback.answer()

@router.message(WarehouseState.waiting_points)
async def add_points(message: Message, state: FSMContext):
    data = await state.get_data()

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET points = points + ? WHERE login=?",
        (int(message.text), data["login"])
    )

    conn.commit()
    conn.close()

    await message.answer("✅ Баллы начислены")
    await state.clear()

@router.message(lambda m: m.text == "📦 Изменить склад")
async def change_stock_start(message: Message):
    if not is_warehouse(message.from_user.id):
        return

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()

    await message.answer(
        "📦 Выберите товар:",
        reply_markup=products_select_keyboard(products)
    )

@router.callback_query(lambda c: c.data.startswith("wh_product:"))
async def select_product(callback: CallbackQuery, state: FSMContext):
    product_id = callback.data.split(":")[1]

    await state.update_data(product_id=product_id)
    await callback.message.answer("Введите новое количество:")
    await state.set_state(WarehouseState.waiting_quantity)

    await callback.answer()

@router.message(WarehouseState.waiting_quantity)
async def update_stock(message: Message, state: FSMContext):
    data = await state.get_data()

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE products SET quantity=? WHERE id=?",
        (int(message.text), data["product_id"])
    )

    conn.commit()
    conn.close()

    await message.answer("✅ Склад обновлён")
    await state.clear()