from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

import db
from keyboards import master_kb, projects_kb

router = Router()


class BudgetFSM(StatesGroup):
    select_project = State()
    enter_limit = State()


class StatsFSM(StatesGroup):
    select_project = State()


# ─── BYUDJET LIMITI ───────────────────────────────────────

@router.message(F.text == "⚠️ Byudjet limiti belgilash")
async def budget_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user or user["role"] != "master":
        return

    projects = await db.get_master_projects(message.from_user.id)
    if not projects:
        await message.answer("⚠️ Sizda hali obyekt yo'q.")
        return

    await message.answer("🏗 Qaysi obyekt uchun limit belgilaysiz?", reply_markup=projects_kb(projects))
    await state.set_state(BudgetFSM.select_project)


@router.callback_query(BudgetFSM.select_project, F.data.startswith("proj_"))
async def budget_project_selected(callback: CallbackQuery, state: FSMContext):
    project_id = int(callback.data.split("_")[1])
    project = await db.get_project_by_id(project_id)
    current_limit = await db.get_budget_limit(project_id)
    current_total = await db.get_total_expenses(project_id)

    await state.update_data(project_id=project_id)
    text = f"🏗 <b>{project['name']}</b>\n"
    text += f"📊 Joriy xarajat: <b>{current_total:,.0f} so'm</b>\n"
    if current_limit:
        text += f"⚠️ Joriy limit: <b>{current_limit:,.0f} so'm</b>\n"
    text += "\n💰 Yangi byudjet limitini kiriting (so'mda):"

    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(BudgetFSM.enter_limit)
    await callback.answer()


@router.message(BudgetFSM.enter_limit)
async def budget_set_limit(message: Message, state: FSMContext):
    try:
        limit = float(message.text.replace(" ", "").replace(",", "."))
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Faqat raqam kiriting:")
        return

    data = await state.get_data()
    project = await db.get_project_by_id(data["project_id"])
    await db.set_budget_limit(data["project_id"], limit)

    total = await db.get_total_expenses(data["project_id"])
    percent = (total / limit * 100) if limit > 0 else 0

    status = "🟢 Normal" if percent < 70 else ("🟡 Diqqat" if percent < 90 else "🔴 Limit yaqinlashdi!")

    await message.answer(
        f"✅ Limit belgilandi!\n\n"
        f"🏗 Obyekt: <b>{project['name']}</b>\n"
        f"💰 Limit: <b>{limit:,.0f} so'm</b>\n"
        f"📊 Sarflangan: <b>{total:,.0f} so'm</b> ({percent:.1f}%)\n"
        f"Holat: {status}",
        parse_mode="HTML",
        reply_markup=master_kb(),
    )
    await state.clear()


async def check_budget_alert(bot: Bot, project_id: int, master_id: int):
    """Xarajat kiritilgandan keyin limit tekshiruvi."""
    limit = await db.get_budget_limit(project_id)
    if not limit:
        return

    total = await db.get_total_expenses(project_id)
    project = await db.get_project_by_id(project_id)
    percent = total / limit * 100

    if percent >= 100:
        await bot.send_message(
            master_id,
            f"🔴 <b>DIQQAT! Byudjet limitidan oshib ketdi!</b>\n\n"
            f"🏗 Obyekt: {project['name']}\n"
            f"💰 Limit: {limit:,.0f} so'm\n"
            f"📊 Sarflangan: {total:,.0f} so'm ({percent:.1f}%)",
            parse_mode="HTML",
        )
    elif percent >= 80:
        await bot.send_message(
            master_id,
            f"🟡 <b>Ogohlantirish:</b> Byudjetning {percent:.0f}% sarflandi.\n\n"
            f"🏗 Obyekt: {project['name']}\n"
            f"💰 Limit: {limit:,.0f} so'm\n"
            f"📊 Sarflangan: {total:,.0f} so'm",
            parse_mode="HTML",
        )


# ─── STATISTIKA ───────────────────────────────────────────

@router.message(F.text == "📅 Statistika")
async def stats_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user:
        return

    if user["role"] == "master":
        projects = await db.get_master_projects(message.from_user.id)
    else:
        projects = await db.get_client_projects(message.from_user.id)

    if not projects:
        await message.answer("⚠️ Sizda hali obyekt yo'q.")
        return

    await message.answer("📊 Qaysi obyekt statistikasini ko'rmoqchisiz?", reply_markup=projects_kb(projects))
    await state.set_state(StatsFSM.select_project)


@router.callback_query(StatsFSM.select_project, F.data.startswith("proj_"))
async def stats_project(callback: CallbackQuery, state: FSMContext):
    project_id = int(callback.data.split("_")[1])
    project = await db.get_project_by_id(project_id)

    now = datetime.now()
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    total = await db.get_total_expenses(project_id)
    weekly = await db.get_expenses_since(project_id, week_ago)
    monthly = await db.get_expenses_since(project_id, month_ago)
    reports_count = len(await db.get_project_reports(project_id))
    limit = await db.get_budget_limit(project_id)

    # Top materiallar
    top_materials = await db.get_top_materials(project_id, limit=5)

    text = (
        f"📊 <b>{project['name']} — Statistika</b>\n"
        f"{'─' * 30}\n\n"
        f"💰 <b>Xarajatlar:</b>\n"
        f"  • Haftalik: <b>{weekly:,.0f} so'm</b>\n"
        f"  • Oylik: <b>{monthly:,.0f} so'm</b>\n"
        f"  • Jami: <b>{total:,.0f} so'm</b>\n\n"
    )

    if limit:
        percent = total / limit * 100
        bar = _progress_bar(percent)
        text += f"⚠️ <b>Byudjet:</b>\n  {bar} {percent:.1f}%\n  Limit: {limit:,.0f} so'm\n\n"

    text += f"📋 Hisobotlar soni: <b>{reports_count} ta</b>\n\n"

    if top_materials:
        text += "🔝 <b>Top materiallar:</b>\n"
        for mat, amt in top_materials:
            text += f"  • {mat}: <b>{amt:,.0f} so'm</b>\n"

    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(None)
    await callback.answer()


def _progress_bar(percent: float) -> str:
    filled = int(min(percent, 100) / 10)
    return "█" * filled + "░" * (10 - filled)
