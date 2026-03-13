from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.deep_linking import decode_payload

import db
from config import MASTER_PASSWORD
from keyboards import master_kb, client_kb, role_kb

router = Router()


class RegisterFSM(StatesGroup):
    waiting_password = State()  # Usta ro'yxatdan o'tayotganda


# /start — oddiy yoki deep link bilan
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command=None):
    await state.clear()
    user_id = message.from_user.id
    full_name = message.from_user.full_name

    # Deep link tekshiruvi: /start <token>
    args = message.text.split(maxsplit=1)
    token = args[1] if len(args) > 1 else None

    user = await db.get_user(user_id)

    if token:
        # Mijozni loyihaga qo'shish
        project = await db.get_project_by_token(token)
        if not project:
            await message.answer("❌ Havola noto'g'ri yoki muddati o'tgan.")
            return

        if not user:
            await db.create_user(user_id, full_name, role="client")
            user = await db.get_user(user_id)

        if user["role"] == "master":
            await message.answer("⚠️ Siz usta sifatida ro'yxatdan o'tgansiz. Bu havola mijozlar uchun.")
            return

        await db.add_client_to_project(project["id"], user_id)
        await message.answer(
            f"✅ <b>{project['name']}</b> loyihasiga muvaffaqiyatli ulashdi!\n\n"
            "Endi siz xarajatlar va hisobotlarni kuzatishingiz mumkin.",
            parse_mode="HTML",
            reply_markup=client_kb(),
        )
        return

    # Oddiy /start
    if user:
        if user["role"] == "master":
            await message.answer(
                f"👷 Xush kelibsiz, <b>{full_name}</b>!\nSiz Usta sifatida tizimdasiz.",
                parse_mode="HTML",
                reply_markup=master_kb(),
            )
        else:
            await message.answer(
                f"👤 Xush kelibsiz, <b>{full_name}</b>!\nSiz Mijoz sifatida tizimdasiz.",
                parse_mode="HTML",
                reply_markup=client_kb(),
            )
    else:
        await message.answer(
            "Assalomu alaykum! 🏗️ <b>Qurilish Nazorat</b> botiga xush kelibsiz!\n\n"
            "Iltimos, o'zingizni tanishtiring:",
            parse_mode="HTML",
            reply_markup=role_kb(),
        )


# Rol tanlash
@router.callback_query(F.data == "role_master")
async def choose_master(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔐 Usta paneliga kirish uchun <b>maxfiy parolni</b> kiriting:",
        parse_mode="HTML",
    )
    await state.set_state(RegisterFSM.waiting_password)
    await callback.answer()


@router.message(RegisterFSM.waiting_password)
async def check_master_password(message: Message, state: FSMContext):
    if message.text == MASTER_PASSWORD:
        await db.create_user(message.from_user.id, message.from_user.full_name, role="master")
        await state.clear()
        await message.answer(
            "✅ Usta sifatida muvaffaqiyatli ro'yxatdan o'tdingiz!",
            reply_markup=master_kb(),
        )
    else:
        await message.answer("❌ Parol noto'g'ri. Qayta urinib ko'ring:")


@router.callback_query(F.data == "role_client")
async def choose_client(callback: CallbackQuery):
    await db.create_user(callback.from_user.id, callback.from_user.full_name, role="client")
    await callback.message.edit_text(
        "✅ Mijoz sifatida ro'yxatdan o'tdingiz!\n\n"
        "Loyihaga ulanish uchun ustadan maxsus havola so'rang.",
    )
    await callback.answer()
