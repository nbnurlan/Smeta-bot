from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import db
from keyboards import client_kb, projects_kb

router = Router()


class ClientViewFSM(StatesGroup):
    select_project = State()
    view_menu = State()


async def is_client(user_id: int) -> bool:
    user = await db.get_user(user_id)
    return user is not None


# ─── MENING LOYIHALARIM ───────────────────────────────────

@router.message(F.text == "📁 Mening loyihalarim")
async def my_projects(message: Message, state: FSMContext):
    projects = await db.get_client_projects(message.from_user.id)
    if not projects:
        await message.answer(
            "📭 Siz hali hech qanday loyihaga ulanmadingiz.\n"
            "Ustadan maxsus havola so'rang."
        )
        return

    await message.answer("📋 Loyihangizni tanlang:", reply_markup=projects_kb(projects))
    await state.set_state(ClientViewFSM.select_project)


@router.callback_query(ClientViewFSM.select_project, F.data.startswith("proj_"))
async def client_project_selected(callback: CallbackQuery, state: FSMContext):
    project_id = int(callback.data.split("_")[1])

    if not await db.is_client_in_project(project_id, callback.from_user.id):
        await callback.answer("❌ Sizda bu loyihaga kirish huquqi yo'q.", show_alert=True)
        return

    project = await db.get_project_by_id(project_id)
    total = await db.get_total_expenses(project_id)

    await state.update_data(project_id=project_id)
    await callback.message.edit_text(
        f"🏗 <b>{project['name']}</b>\n"
        f"📝 {project['description']}\n\n"
        f"📊 Jami xarajat: <b>{total:,.0f} so'm</b>\n\n"
        "Nima ko'rmoqchisiz?",
        parse_mode="HTML",
        reply_markup=_project_detail_kb(),
    )
    await state.set_state(ClientViewFSM.view_menu)
    await callback.answer()


@router.callback_query(ClientViewFSM.view_menu, F.data == "view_expenses")
async def view_expenses(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    expenses = await db.get_project_expenses(data["project_id"])

    if not expenses:
        await callback.answer("Xarajatlar hali kiritilmagan.", show_alert=True)
        return

    total = await db.get_total_expenses(data["project_id"])
    text = "💸 <b>Xarajatlar ro'yxati:</b>\n\n"

    for e in expenses[:20]:  # oxirgi 20 ta
        text += (
            f"• {e['material']} — <b>{e['amount']:,.0f} so'm</b>\n"
            f"  📅 {e['created_at'][:10]}\n"
        )
        if e["receipt_file_id"]:
            text += "  🧾 Chek mavjud\n"

    text += f"\n📊 <b>Jami: {total:,.0f} so'm</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_back_kb())
    await callback.answer()


@router.callback_query(ClientViewFSM.view_menu, F.data == "view_reports")
async def view_reports(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    reports = await db.get_project_reports(data["project_id"])

    if not reports:
        await callback.answer("Hisobotlar hali yuborilmagan.", show_alert=True)
        return

    # Oxirgi hisobotni ko'rsatamiz
    last = reports[0]
    caption = (
        f"📊 <b>Oxirgi hisobot</b>\n"
        f"📅 {last['created_at'][:16]}\n\n"
        f"{last['text']}\n\n"
        f"Jami {len(reports)} ta hisobot mavjud."
    )

    if last["photo_file_id"]:
        await callback.message.answer_photo(
            photo=last["photo_file_id"],
            caption=caption,
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(caption, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data == "back_to_projects")
async def back_to_projects(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Asosiy menyu:")
    await callback.message.answer("📋 Loyihangizni tanlang:", reply_markup=client_kb())
    await callback.answer()


# ─── INLINE KLAVIATURALAR ─────────────────────────────────

def _project_detail_kb():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Xarajatlarni ko'rish", callback_data="view_expenses")],
        [InlineKeyboardButton(text="📊 Hisobotlarni ko'rish", callback_data="view_reports")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_projects")],
    ])


def _back_kb():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_projects")],
    ])
