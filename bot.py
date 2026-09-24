import os
import asyncio
import logging
from html import escape
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
)
from dotenv import load_dotenv
from database import (
    init_db,
    create_user,
    get_user,
    get_all_users,
    search_users,
    activate_tariff,
    disable_subscription,
    get_all_payments,
    get_stats,
    get_subscription_link,
    set_accepted_terms,
    create_payment,
    mark_payment_paid,
)
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ixxy-bot")
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
PUBLIC_SITE_URL = os.getenv(
    "PUBLIC_SITE_URL",
    "https://ixxysubscription.onrender.com",
).rstrip("/")
SUBSCRIPTION_PREFIX = os.getenv(
    "SUBSCRIPTION_PREFIX",
    "2ix847xy",
)
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не установлен")
bot = Bot(BOT_TOKEN)
dp = Dispatcher()
router = Router()
# ============================================================
# ☂️ IXXY — ТАРИФЫ
# ============================================================
TARIFFS = {
    "basic": {
        "name": "Basic",
        "price_rub": 415,
        "price_stars": 309,
        "description": "Обычные / Wi-Fi серверы",
        "emoji": "🟢",
    },
    "mobile": {
        "name": "Mobile",
        "price_rub": 743,
        "price_stars": 637,
        "description": "Серверы с антиглушилкой",
        "emoji": "📱",
    },
    "supra": {
        "name": "Supra",
        "price_rub": 1351,
        "price_stars": 1245,
        "description": "Все серверы",
        "emoji": "☂️",
    },
}
# ============================================================
# КЛАВИАТУРЫ
# ============================================================
def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Купить тариф",
                    callback_data="buy"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Мой кабинет",
                    callback_data="cabinet"
                )
            ],
        ]
    )
def tariffs_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 Basic — 415 ₽",
                    callback_data="tariff:basic"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📱 Mobile — 743 ₽",
                    callback_data="tariff:mobile"
                )
            ],
            [
                InlineKeyboardButton(
                    text="☂️ Supra — 1 351 ₽ • ВЫГОДНО",
                    callback_data="tariff:supra"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_main"
                )
            ],
        ]
    )
def payment_menu(tariff):
    data = TARIFFS[tariff]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🇷🇺 CasheRa — {data['price_rub']} ₽",
                    callback_data=f"pay_rub:{tariff}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⭐ Telegram Stars — {data['price_stars']} ⭐",
                    callback_data=f"pay_stars:{tariff}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="buy"
                )
            ],
        ]
    )
def admin_users_menu(users, page=0):
    buttons = []
    for user in users:
        user_id = int(user["user_id"])
        name = (
            user.get("first_name")
            or user.get("username")
            or str(user_id)
        )
        tariff = user.get("tariff")
        if tariff in TARIFFS:
            tariff_text = TARIFFS[tariff]["name"]
        else:
            tariff_text = "нет тарифа"
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {name} • {tariff_text}",
                callback_data=f"admin:user:{user_id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="🔎 Поиск пользователя",
            callback_data="admin:search"
        )
    ])
    buttons.append([
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="admin:stats"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
def admin_user_menu(user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 Выдать Basic",
                    callback_data=f"admin:set:{user_id}:basic"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📱 Выдать Mobile",
                    callback_data=f"admin:set:{user_id}:mobile"
                )
            ],
            [
                InlineKeyboardButton(
                    text="☂️ Выдать Supra",
                    callback_data=f"admin:set:{user_id}:supra"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Забрать тариф",
                    callback_data=f"admin:disable:{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 Платежи",
                    callback_data=f"admin:payments:{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К пользователям",
                    callback_data="admin:users"
                )
            ],
        ]
    )
# ============================================================
# ВСПОМОГАТЕЛЬНОЕ
# ============================================================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
def subscription_link(user_id: int) -> str:
    try:
        link = get_subscription_link(user_id)
        if link:
            return link
    except Exception:
        pass
    return (
        f"{PUBLIC_SITE_URL}/sub/"
        f"{SUBSCRIPTION_PREFIX}{user_id}"
    )
def user_display(user):
    user_id = int(user["user_id"])
    first_name = escape(
        str(user.get("first_name") or "Без имени")
    )
    username = user.get("username")
    username_text = ""
    if username:
        username_text = f"\n👤 @{escape(str(username))}"
    tariff = user.get("tariff")
    if tariff in TARIFFS:
        tariff_info = TARIFFS[tariff]
        tariff_text = (
            f"{tariff_info['emoji']} "
            f"<b>{tariff_info['name']}</b>"
        )
    else:
        tariff_text = "❌ <b>Тариф не выдан</b>"
    link = escape(subscription_link(user_id))
    return (
        f"👤 <b>{first_name}</b>"
        f"{username_text}\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📦 Тариф: {tariff_text}\n"
        f"♾️ Срок: <b>навсегда</b>\n\n"
        f"🔗 <code>{link}</code>"
    )
# ============================================================
# START
# ============================================================
@router.message(CommandStart())
async def start_handler(message: Message):
    user = message.from_user
    create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )
    text = (
        "☂️ <b>IXXY VPN</b>\n\n"
        "Быстрый и стабильный VPN.\n\n"
        "Все тарифы выдаются <b>навсегда</b>.\n\n"
        "Выберите действие:"
    )
    await message.answer(
        text,
        reply_markup=main_menu(),
    )
# ============================================================
# ПОКУПКА
# ============================================================
@router.callback_query(F.data == "buy")
async def buy_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "☂️ <b>Выберите тариф</b>\n\n"
        "🟢 <b>Basic</b> — 415 ₽\n"
        "Обычные / Wi-Fi серверы\n\n"
        "📱 <b>Mobile</b> — 743 ₽\n"
        "Серверы с антиглушилкой\n\n"
        "☂️ <b>Supra</b> — 1 351 ₽\n"
        "Все серверы • <b>ВЫГОДНО</b>\n\n"
        "♾️ Каждый тариф выдаётся навсегда.",
        reply_markup=tariffs_menu(),
    )
    await callback.answer()
@router.callback_query(F.data.startswith("tariff:"))
async def tariff_handler(callback: CallbackQuery):
    tariff = callback.data.split(":", 1)[1]
    if tariff not in TARIFFS:
        await callback.answer("Неизвестный тариф", show_alert=True)
        return
    data = TARIFFS[tariff]
    await callback.message.edit_text(
        f"{data['emoji']} <b>{data['name']}</b>\n\n"
        f"💰 {data['price_rub']} ₽\n"
        f"⭐ {data['price_stars']} Stars\n\n"
        f"📡 {data['description']}\n"
        f"♾️ Навсегда\n\n"
        "Выберите способ оплаты:",
        reply_markup=payment_menu(tariff),
    )
    await callback.answer()
# ============================================================
# TELEGRAM STARS
# ============================================================
@router.callback_query(F.data.startswith("pay_stars:"))
async def stars_payment(callback: CallbackQuery):
    tariff = callback.data.split(":", 1)[1]
    if tariff not in TARIFFS:
        await callback.answer("Ошибка тарифа", show_alert=True)
        return
    data = TARIFFS[tariff]
    payment_id = create_payment(
        user_id=callback.from_user.id,
        payment_id=None,
        external_id=None,
        amount=data["price_stars"],
        currency="XTR",
        tariff=tariff,
        status="pending",
        provider="stars",
    )
    invoice_payload = f"ixxy:{tariff}:{callback.from_user.id}:{payment_id}"
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"IXXY VPN — {data['name']}",
        description=(
            f"{data['description']}. "
            "Подписка навсегда."
        ),
        payload=invoice_payload,
        currency="XTR",
        prices=[
            LabeledPrice(
                label=f"IXXY {data['name']}",
                amount=data["price_stars"],
            )
        ],
    )
    await callback.answer()
@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)
@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    parts = payload.split(":")
    if len(parts) < 4 or parts[0] != "ixxy":
        return
    tariff = parts[1]
    payment_db_id = int(parts[3])
    user_id = message.from_user.id
    mark_payment_paid(
        payment_id=payment_db_id,
        external_id=str(payment.telegram_payment_charge_id),
    )
    activate_tariff(user_id, tariff)
    await message.answer(
        "✅ <b>Оплата прошла успешно!</b>\n\n"
        f"☂️ Тариф: <b>{TARIFFS[tariff]['name']}</b>\n"
        "♾️ Срок: <b>навсегда</b>\n\n"
        f"🔗 Ваша подписка:\n"
        f"<code>{subscription_link(user_id)}</code>",
        reply_markup=main_menu(),
    )
# ============================================================
# CASHERA
# ============================================================
@router.callback_query(F.data.startswith("pay_rub:"))
async def rub_payment(callback: CallbackQuery):
    tariff = callback.data.split(":", 1)[1]
    if tariff not in TARIFFS:
        await callback.answer("Ошибка тарифа", show_alert=True)
        return
    data = TARIFFS[tariff]
    try:
        from cashera import create_cashera_payment
        result = create_cashera_payment(
            user_id=callback.from_user.id,
            amount=data["price_rub"],
            tariff=tariff,
        )
        external_id = result.get("external_id")
        payment_id = create_payment(
            user_id=callback.from_user.id,
            payment_id=str(result.get("uuid")),
            external_id=external_id,
            amount=data["price_rub"],
            currency="RUB",
            tariff=tariff,
            status="pending",
            provider="cashera",
        )
        payment_url = result["payment_url"]
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💳 Оплатить",
                        url=payment_url,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data=f"tariff:{tariff}",
                    )
                ],
            ]
        )
        await callback.message.edit_text(
            f"💳 <b>Оплата IXXY VPN</b>\n\n"
            f"Тариф: <b>{data['name']}</b>\n"
            f"Сумма: <b>{data['price_rub']} ₽</b>\n"
            "Срок: <b>навсегда</b>\n\n"
            "Нажмите кнопку ниже для оплаты.",
            reply_markup=keyboard,
        )
        await callback.answer()
    except Exception as e:
        logger.exception("CasheRa error")
        await callback.answer(
            "Ошибка создания платежа",
            show_alert=True,
        )
# ============================================================
# КАБИНЕТ
# ============================================================
@router.callback_query(F.data == "cabinet")
async def cabinet_handler(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        create_user(
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
        )
        user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        "👤 <b>Мой кабинет</b>\n\n"
        + user_display(user),
        reply_markup=main_menu(),
    )
    await callback.answer()
# ============================================================
# НАЗАД
# ============================================================
@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "☂️ <b>IXXY VPN</b>\n\n"
        "Все тарифы выдаются навсегда.",
        reply_markup=main_menu(),
    )
    await callback.answer()
# ============================================================
# АДМИН — СПИСОК ПОЛЬЗОВАТЕЛЕЙ
# ============================================================
@router.message(Command("admin"))
async def admin_handler(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    users = get_all_users()
    await message.answer(
        "☂️ <b>IXXY VPN — Админ-панель</b>\n\n"
        f"👥 Пользователей: <b>{len(users)}</b>\n\n"
        "Выберите пользователя:",
        reply_markup=admin_users_menu(users),
    )
@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    users = get_all_users()
    await callback.message.edit_text(
        "☂️ <b>IXXY VPN — Пользователи</b>\n\n"
        "Выберите пользователя:",
        reply_markup=admin_users_menu(users),
    )
    await callback.answer()
# ============================================================
# АДМИН — КОНКРЕТНЫЙ ПОЛЬЗОВАТЕЛЬ
# ============================================================
@router.callback_query(F.data.startswith("admin:user:"))
async def admin_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    user_id = int(callback.data.split(":")[2])
    user = get_user(user_id)
    if not user:
        await callback.answer(
            "Пользователь не найден",
            show_alert=True,
        )
        return
    await callback.message.edit_text(
        "☂️ <b>Пользователь</b>\n\n"
        + user_display(user)
        + "\n\n"
        "Выберите действие:",
        reply_markup=admin_user_menu(user_id),
    )
    await callback.answer()
# ============================================================
# АДМИН — ВЫДАТЬ ТАРИФ
# ============================================================
@router.callback_query(F.data.startswith("admin:set:"))
async def admin_set_tariff(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    _, _, user_id_raw, tariff = callback.data.split(":")
    user_id = int(user_id_raw)
    if tariff not in TARIFFS:
        await callback.answer("Ошибка тарифа", show_alert=True)
        return
    user = get_user(user_id)
    if not user:
        await callback.answer(
            "Пользователь не найден",
            show_alert=True,
        )
        return
    # Выдача / замена тарифа.
    # Всегда навсегда.
    activate_tariff(user_id, tariff)
    user = get_user(user_id)
    await callback.message.edit_text(
        "✅ <b>Тариф выдан</b>\n\n"
        + user_display(user)
        + "\n\n"
        "Изменения сохранены.",
        reply_markup=admin_user_menu(user_id),
    )
    await callback.answer(
        f"Выдан {TARIFFS[tariff]['name']}",
    )
# ============================================================
# АДМИН — ЗАБРАТЬ ТАРИФ
# ============================================================
@router.callback_query(F.data.startswith("admin:disable:"))
async def admin_disable(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    user_id = int(callback.data.split(":")[2])
    user = get_user(user_id)
    if not user:
        await callback.answer(
            "Пользователь не найден",
            show_alert=True,
        )
        return
    disable_subscription(user_id)
    user = get_user(user_id)
    await callback.message.edit_text(
        "❌ <b>Тариф забран</b>\n\n"
        + user_display(user),
        reply_markup=admin_user_menu(user_id),
    )
    await callback.answer("Тариф забран")
# ============================================================
# АДМИН — ПЛАТЕЖИ ПОЛЬЗОВАТЕЛЯ
# ============================================================
@router.callback_query(F.data.startswith("admin:payments:"))
async def admin_user_payments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    user_id = int(callback.data.split(":")[2])
    payments = get_all_payments(user_id=user_id)
    if not payments:
        text = (
            f"💳 <b>Платежи пользователя</b>\n\n"
            f"ID: <code>{user_id}</code>\n\n"
            "Платежей нет."
        )
    else:
        lines = [
            f"💳 <b>Платежи пользователя</b>",
            f"ID: <code>{user_id}</code>",
            "",
        ]
        for payment in payments[:20]:
            tariff = payment.get("tariff") or "—"
            status = payment.get("status") or "—"
            provider = payment.get("provider") or "—"
            amount = payment.get("amount") or 0
            currency = payment.get("currency") or "RUB"
            lines.append(
                f"• <b>{tariff}</b> — "
                f"{amount} {currency}\n"
                f"  {provider} • {status}"
            )
        text = "\n".join(lines)
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ К пользователю",
                        callback_data=f"admin:user:{user_id}",
                    )
                ]
            ]
        ),
    )
    await callback.answer()
# ============================================================
# АДМИН — СТАТИСТИКА
# ============================================================
@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    stats = get_stats()
    await callback.message.edit_text(
        "📊 <b>Статистика IXXY</b>\n\n"
        f"👥 Пользователей: <b>{stats.get('users', 0)}</b>\n"
        f"🟢 Basic: <b>{stats.get('basic', 0)}</b>\n"
        f"📱 Mobile: <b>{stats.get('mobile', 0)}</b>\n"
        f"☂️ Supra: <b>{stats.get('supra', 0)}</b>\n"
        f"❌ Без тарифа: <b>{stats.get('without_tariff', 0)}</b>\n\n"
        f"💳 Платежей: <b>{stats.get('payments', 0)}</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👥 Пользователи",
                        callback_data="admin:users",
                    )
                ]
            ]
        ),
    )
    await callback.answer()
# ============================================================
# ЗАПУСК
# ============================================================
async def main():
    init_db()
    dp.include_router(router)
    logger.info("☂️ IXXY BOT STARTED")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())