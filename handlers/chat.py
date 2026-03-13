from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import db
from keyboards import projects_kb

router = Router()


class ChatFSM(StatesGroup):
    select_project = State()
    messaging = State()


# ─── CHAT BOSHLASH ────────────────────────────────────────

@router.message(F.text == "💬 Xabar yuborish")
async def chat_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user:
        return

    if user["role"] == "master":
        projects = await db.get_master_projects(message.from_user.id)
    else:
        projects = await db.get_client_projects(message.from_user.id)

    if not projects:
        await message.answer("⚠️ Sizda hali ulangan loyiha yo'q.")
        return

    await message.answer("💬 Qaysi loyiha bo'yicha xabar yubormqoqchisiz?", reply_markup=projects_kb(projects))
    await state.set_state(ChatFSM.select_project)


@router.callback_query(ChatFSM.select_project, F.data.startswith("proj_"))
async def chat_project_selected(callback: CallbackQuery, state: FSMContext):
    project_id = int(callback.data.split("_")[1])
    project = await db.get_project_by_id(project_id)
    await state.update_data(project_id=project_id)

    # Oxirgi 5 xabarni ko'rsatish
    messages = await db.get_project_messages(project_id, limit=5)
    text = f"💬 <b>{project['name']} — Chat</b>\n{'─' * 28}\n\n"

    if messages:
        for msg in reversed(messages):
            role_icon = "👷" if msg["sender_role"] == "master" else "👤"
            text += f"{role_icon} <b>{msg['sender_name']}</b> [{msg['created_at'][11:16]}]\n{msg['text']}\n\n"
    else:
        text += "📭 Hali xabarlar yo'q. Birinchi xabarni yuboring!\n\n"

    text += "✏️ Xabaringizni yozing (yoki /done — chiqish):"
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(ChatFSM.messaging)
    await callback.answer()


@router.message(ChatFSM.messaging, F.text)
async def chat_send_message(message: Message, state: FSMContext, bot: Bot):
    if message.text == "/done":
        await state.clear()
        await message.answer("✅ Chatdan chiqdingiz.")
        return

    data = await state.get_data()
    project_id = data["project_id"]
    user = await db.get_user(message.from_user.id)
    project = await db.get_project_by_id(project_id)

    # Xabarni saqlash
    await db.save_message(
        project_id=project_id,
        sender_id=message.from_user.id,
        sender_name=message.from_user.full_name,
        sender_role=user["role"],
        text=message.text,
    )

    # Boshqalarga yuborish
    recipients = await db.get_project_participants(project_id, exclude_id=message.from_user.id)
    role_icon = "👷 Usta" if user["role"] == "master" else "👤 Mijoz"

    for recipient_id in recipients:
        try:
            await bot.send_message(
                recipient_id,
                f"💬 <b>{project['name']}</b>\n"
                f"{role_icon}: <b>{message.from_user.full_name}</b>\n\n"
                f"{message.text}",
                parse_mode="HTML",
            )
        except Exception:
            pass  # Foydalanuvchi boti bloklagan bo'lishi mumkin

    await message.answer("✅ Xabar yuborildi.")


# ─── RASM YUBORISH (chatda) ───────────────────────────────

@router.message(ChatFSM.messaging, F.photo)
async def chat_send_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    project_id = data["project_id"]
    user = await db.get_user(message.from_user.id)
    project = await db.get_project_by_id(project_id)
    caption = message.caption or ""

    await db.save_message(
        project_id=project_id,
        sender_id=message.from_user.id,
        sender_name=message.from_user.full_name,
        sender_role=user["role"],
        text=f"[📷 Rasm] {caption}",
    )

    recipients = await db.get_project_participants(project_id, exclude_id=message.from_user.id)
    role_icon = "👷 Usta" if user["role"] == "master" else "👤 Mijoz"

    for recipient_id in recipients:
        try:
            await bot.send_photo(
                recipient_id,
                photo=message.photo[-1].file_id,
                caption=f"💬 <b>{project['name']}</b>\n{role_icon}: {message.from_user.full_name}\n{caption}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    await message.answer("✅ Rasm yuborildi.")
