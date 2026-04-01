from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from db import get_mentors, get_warehouses


def start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔐 Авторизация", callback_data="login"),
        ]
    ])


def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать наставника", callback_data="admin_create")],
        [InlineKeyboardButton(text="📦 Назначить кладовщика", callback_data="admin_set_warehouse")],
        [InlineKeyboardButton(text="🚫 Снять кладовщика", callback_data="admin_remove_warehouse")],
        [InlineKeyboardButton(text="📋 Все пользователи", callback_data="admin_list")],
        [InlineKeyboardButton(text="🚀 Cтатистика", callback_data="admin_stats")],

    ])


def mentor_keyboard():
    mentors = get_mentors()

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m, callback_data=f"set_warehouse:{m}")]
        for m in mentors
    ])

def back_to_admin():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="back_admin")]
    ])

def edit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ФИО", callback_data="edit_name")],
        [InlineKeyboardButton(text="Пароль", callback_data="edit_password")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_admin")]
    ])

def warehouse_keyboard():
    users = get_warehouses()

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"@{u}",
                callback_data=f"remove_warehouse:{u}"
            )
        ]
        for u in users
    ])

def admin_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👑 Админ-панель")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,   # 🔥 ВАЖНО
        input_field_placeholder="Выберите действие...",
        is_persistent=True         # 🔥 ВАЖНО (aiogram 3)
    )
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def mentor_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мой профиль"),KeyboardButton(text="📦 Мои заказы")],
            [KeyboardButton(text="🛍 Магазин мерча"),KeyboardButton(text="⚠️ Сообщить о проблеме")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

def warehouse_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="👤 Мой профиль")],
            [KeyboardButton(text="⭐ Начислить баллы"),
            KeyboardButton(text="📦 Изменить склад")]
        ],
        resize_keyboard=True
    )