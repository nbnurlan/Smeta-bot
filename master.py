import secrets
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.deep_linking import create_start_link

import db
from keyboards import master_kb, projects_kb, cancel_kb

router = Router()


class NewProjectFSM(StatesGroup):
    name = State()
    description = State()


class ExpenseFSM(StatesGroup):
    select_project = State()
    material = State()
    amount = State()
    receipt = State()


class ReportFSM(StatesGroup):
    select_project = State()
    photo = State()
    text = State()


# ─── Ruxsat filtri ────────────────────────────────────────
async def is_master(user_id: int) -> bool:
    user = await db.get_user(user_id)
    return user is not None and user["role"] == "master"


# ─── YANGI OBYEKT ─────────────────────────────────────────

@router.message(F.text == "➕ Yangi obyekt qo'shish")
async def add_project_start(message: Message, state: FSMContext):
    if not await is_master(message.from_user.id):
        return
    await message.answer("📋 Yangi obyekt nomini kiriting:", reply_markup=cancel_kb())
    await state.set_state(NewProjectFSM.name)


@router.message(NewProjectFSM.name)
async def add_project_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await _cancel(message, state)
        return
    await state.update_data(name=message.text)
    await message.answer("📝 Qisqacha tavsif kiriting (ixtiyoriy, o'tkazib yuborish uchun — kiriting):")
    await state.set_state(NewProjectFSM.description)


@router.message(NewProjectFSM.description)
async def add_project_desc(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await _cancel(message, state)
        return

    data = await state.get_data()
    token = secrets.token_urlsafe(12)

    project_id = await db.create_project(
        name=data["name"],
        description=message.text,
        master_id=message.from_user.id,
        token=token,
    )

    link = await create_start_link(bot, token, encode=False)

    await message.answer(
        f"✅ <b>{data['name']}</b> obyekti yaratildi!\n\n"
        f"📎 Mijozlarga ulashing uchun havola:\n{link}\n\n"
        f"Bu havolani faqat ishonchli mijozlarga yuboring.",
        parse_mode="HTML",
        reply_markup=master_kb(),
    )
    await state.clear()


# ─── XARAJAT KIRITISH ─────────────────────────────────────

@router.message(F.text == "💸 Xarajat kiritish")
async def expense_start(message: Message, state: FSMContext):
    if not await is_master(message.from_user.id):
        return

    projects = await db.get_master_projects(message.from_user.id)
    if not projects:
        await message.answer("⚠️ Sizda hali obyekt yo'q. Avval yangi obyekt qo'shing.")
        return

    await message.answer(
        "📦 Qaysi obyekt uchun xarajat kiritasiz?",
        reply_markup=projects_kb(projects),
    )
    await state.set_state(ExpenseFSM.select_project)


@router.callback_query(ExpenseFSM.select_project, F.data.startswith("proj_"))
async def expense_project_selected(callback: CallbackQuery, state: FSMContext):
    project_id = int(callback.data.split("_")[1])
    await state.update_data(project_id=project_id)
    await callback.message.edit_text("🔩 Material nomini kiriting (masalan: Sement, G'isht):")
    await state.set_state(ExpenseFSM.material)
    await callback.answer()


@router.message(ExpenseFSM.material)
async def expense_material(message: Message, state: FSMContext):
    await state.update_data(material=message.text)
    await message.answer("💰 Summani kiriting (so'mda, faqat raqam):")
    await state.set_state(ExpenseFSM.amount)


@router.message(ExpenseFSM.amount)
async def expense_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(" ", "").replace(",", "."))
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Faqat raqam kiriting (masalan: 150000):")
        return

    await state.update_data(amount=amount)
    await message.answer(
        "🧾 Chek rasmini yuboring (ixtiyoriy).\n"
        "O'tkazib yuborish uchun /skip yozing:",
        reply_markup=cancel_kb(),
    )
    await state.set_state(ExpenseFSM.receipt)


@router.message(ExpenseFSM.receipt, F.photo)
async def expense_receipt_photo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await _save_expense(message, state, receipt_file_id=file_id)


@router.message(ExpenseFSM.receipt, F.text == "/skip")
async def expense_receipt_skip(message: Message, state: FSMContext):
    await _save_expense(message, state, receipt_file_id=None)


async def _save_expense(message: Message, state: FSMContext, receipt_file_id):
    data = await state.get_data()
    expense_id = await db.add_expense(
        project_id=data["project_id"],
        master_id=message.from_user.id,
        material=data["material"],
        amount=data["amount"],
        receipt_file_id=receipt_file_id,
    )
    total = await db.get_total_expenses(data["project_id"])
    project = await db.get_project_by_id(data["project_id"])

    await message.answer(
        f"✅ Xarajat saqlandi!\n\n"
        f"🏗 Obyekt: <b>{project['name']}</b>\n"
        f"🔩 Material: {data['material']}\n"
        f"💰 Summa: <b>{data['amount']:,.0f} so'm</b>\n"
        f"📊 Jami xarajat: <b>{total:,.0f} so'm</b>",
        parse_mode="HTML",
        reply_markup=master_kb(),
    )
    await state.clear()


# ─── KUNLIK HISOBOT ───────────────────────────────────────

@router.message(F.text == "📊 Kunlik hisobot yuborish")
async def report_start(message: Message, state: FSMContext):
    if not await is_master(message.from_user.id):
        return

    projects = await db.get_master_projects(message.from_user.id)
    if not projects:
        await message.answer("⚠️ Sizda hali obyekt yo'q.")
        return

    await message.answer("📁 Hisobot qaysi obyekt uchun?", reply_markup=projects_kb(projects))
    await state.set_state(ReportFSM.select_project)


@router.callback_query(ReportFSM.select_project, F.data.startswith("proj_"))
async def report_project_selected(callback: CallbackQuery, state: FSMContext):
    project_id = int(callback.data.split("_")[1])
    await state.update_data(project_id=project_id)
    await callback.message.edit_text(
        "📷 Ish jarayoni rasmini yuboring (ixtiyoriy, /skip — o'tkazib yuborish):"
    )
    await state.set_state(ReportFSM.photo)
    await callback.answer()


@router.message(ReportFSM.photo, F.photo)
async def report_photo(message: Message, state: FSMContext):
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await message.answer("✏️ Hisobot matnini yozing:")
    await state.set_state(ReportFSM.text)


@router.message(ReportFSM.photo, F.text == "/skip")
async def report_photo_skip(message: Message, state: FSMContext):
    await state.update_data(photo_file_id=None)
    await message.answer("✏️ Hisobot matnini yozing:")
    await state.set_state(ReportFSM.text)


@router.message(ReportFSM.text)
async def report_text(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    project = await db.get_project_by_id(data["project_id"])

    await db.add_report(
        project_id=data["project_id"],
        master_id=message.from_user.id,
        text=message.text,
        photo_file_id=data.get("photo_file_id"),
    )

    await message.answer(
        f"✅ Hisobot saqlandi va mijozlarga yuborildi!\n🏗 Obyekt: <b>{project['name']}</b>",
        parse_mode="HTML",
        reply_markup=master_kb(),
    )
    await state.clear()


# ─── YORDAMCHI ────────────────────────────────────────────

async def _cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=master_kb())
