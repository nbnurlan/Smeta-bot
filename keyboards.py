from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

def master_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Yangi obyekt qo'shish")],
        [KeyboardButton(text="💸 Xarajat kiritish"), KeyboardButton(text="📊 Kunlik hisobot yuborish")],
        [KeyboardButton(text="⚠️ Byudjet limiti belgilash"), KeyboardButton(text="📅 Statistika")],
        [KeyboardButton(text="💬 Xabar yuborish")],
    ], resize_keyboard=True)

def client_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📁 Mening loyihalarim")],
        [KeyboardButton(text="📅 Statistika"), KeyboardButton(text="💬 Xabar yuborish")],
    ], resize_keyboard=True)

def role_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👷 Men Ustaman", callback_data="role_master")],
        [InlineKeyboardButton(text="👤 Men Mijozman", callback_data="role_client")],
    ])

def projects_kb(projects: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"🏗 {p['name']}", callback_data=f"proj_{p['id']}")]
        for p in projects
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
  )
