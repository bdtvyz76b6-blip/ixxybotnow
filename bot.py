import os
import logging
from html import escape
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
)
from database import (
    TARIFFS,
    create_user,
    get_user,
    get_subscription_link,
    activate_tariff,
    disable_subscription,
    create_payment,
    mark_payment_paid,
    get_all_users,
    get_all_payments,
    get_stats,
)
from cashera import create_cashera_payment
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = {
    int(x.strip())
    for x in ADMIN_IDS_RAW.split(",")
    if x.strip().isdigit()
}
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не установлен.")
bot = Bot(BOT_TOKEN)
dp = Dispatcher()
# ============================================================
# ТАРИФЫ
# ============================================================
TARIFFS = {
    "basic": {
        "name": "Basic",
        "rub": 415,
        "stars": 309,
        "description": "Обычные / Wi-Fi серверы",
        "emoji": "🟢",
    },
    "mobile": {
        "name": "Mobile",
        "rub": 743,
        "stars": 637,
        "description": "Серверы с обходом глушилок",
        "emoji": "📱",
    },
    "supra": {
        "name": "Supra",
        "rub": 1351,
        "stars": 1245,
        "description": "Все серверы",
        "emoji": "☂️",
    },
}
# ============================================================
# КЛАВИАТУРЫ
# ============================================================
def main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Купить подписку",
                    callback_data="buy",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Моя подписка",
                    callback_data="cabinet",
                )
            ],
        ]
    )
def tariff_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 Basic — 415 ₽",
                    callback_data="tariff_basic",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📱 Mobile — 743 ₽",
                    callback_data="tariff_mobile",
                )
            ],
            [
                InlineKeyboardButton(
                    text="☂️ Supra — 1351 ₽ • ВЫГОДНО",
                    callback_data="tariff_supra",
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="back_main",
                )
            ],
        ]
    )
def payment_keyboard(tariff: str):
    data = TARIFFS[tariff]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 CasheRa — {data['rub']} ₽",
                    callback_data=f"cash_{tariff}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⭐ Telegram Stars — {data['stars']} ⭐",
                    callback_data=f"stars_{tariff}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="buy",
                )
            ],
        ]
    )
def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Пользователи",
                    callback_data="admin_users",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 Платежи",
                    callback_data="admin_payments",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="admin_stats",
                )
            ],
        ]
    )
# ============================================================
# ПРОВЕРКА АДМИНА
# ============================================================
def is_admin(user_id: int) -> bool:
    return int(user_id) in ADMIN_IDS
# ============================================================
# START
# ============================================================
@dp.message(CommandStart())
async def start(message: Message):
    user = message.from_user
    create_user(
        user.id,
        user.username,
        user.first_name,
    )
    text = (
        "☂️ <b>IXXY VPN</b>\n\n"
        "Быстрый и удобный VPN.\n\n"
        "Все подписки выдаются <b>навсегда</b>.\n\n"
        "Выбери действие:"
    )
    await message.answer(
        text,
        reply_markup=main_keyboard(),
    )
# ============================================================
# BUY
# ============================================================
@dp.callback_query(F.data == "buy")
async def buy(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(
        "☂️ <b>Выберите тариф</b>\n\n"
        "Все тарифы действуют <b>навсегда</b>.\n\n"
        "🟢 <b>Basic</b>\n"
        "Обычные / Wi-Fi серверы\n"
        "415 ₽ / 309 ⭐\n\n"
        "📱 <b>Mobile</b>\n"
        "Серверы с обходом глушилок\n"
        "743 ₽ / 637 ⭐\n\n"
        "☂️ <b>Supra</b> — <b>ВЫГОДНО</b>\n"
        "Все серверы\n"
        "1351 ₽ / 1245 ⭐",
        reply_markup=tariff_keyboard(),
    )
# ============================================================
# ВЫБОР ТАРИФА
# ============================================================
@dp.callback_query(F.data.startswith("tariff_"))
async def tariff_selected(call: CallbackQuery):
    await call.answer()
    tariff = call.data.replace("tariff_", "")
    if tariff not in TARIFFS:
        return
    data = TARIFFS[tariff]
    await call.message.edit_text(
        f"{data['emoji']} <b>{data['name']}</b>\n\n"
        f"{data['description']}.\n\n"
        f"⏳ Срок: <b>навсегда</b>\n\n"
        f"💳 CasheRa: <b>{data['rub']} ₽</b>\n"
        f"⭐ Stars: <b>{data['stars']} ⭐</b>\n\n"
        "Выберите способ оплаты:",
        reply_markup=payment_keyboard(tariff),
    )
# ============================================================
# CASHERA
# ============================================================
@dp.callback_query(F.data.startswith("cash_"))
async def cash_payment(call: CallbackQuery):
    await call.answer()
    tariff = call.data.replace("cash_", "")
    if tariff not in TARIFFS:
        return
    user_id = call.from_user.id
    data = TARIFFS[tariff]
    await call.message.edit_text(
        "⏳ <b>Создаю платёж...</b>"
    )
    try:
        payment = create_cashera_payment(
            user_id=user_id,
            amount=data["rub"],
            tariff=tariff,
        )
        external_id = payment.get("external_id")
        payment_uuid = payment.get("uuid")
        payment_url = payment.get("payment_url")
        create_payment(
            user_id=user_id,
            payment_id=payment_uuid,
            external_id=external_id,
            amount=data["rub"],
            currency="RUB",
            tariff=tariff,
            provider="cashera",
        )
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
                        text="◀️ Назад",
                        callback_data=f"tariff_{tariff}",
                    )
                ],
            ]
        )
        await call.message.edit_text(
            f"💳 <b>Оплата {data['name']}</b>\n\n"
            f"Сумма: <b>{data['rub']} ₽</b>\n"
            f"Срок: <b>навсегда</b>\n\n"
            "Нажмите кнопку ниже для оплаты.",
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.exception("CasheRa error")
        await call.message.edit_text(
            "❌ <b>Не удалось создать платёж.</b>\n\n"
            "Попробуйте ещё раз позже.",
            reply_markup=payment_keyboard(tariff),
        )
# ============================================================
# STARS
# ============================================================
@dp.callback_query(F.data.startswith("stars_"))
async def stars_payment(call: CallbackQuery):
    await call.answer()
    tariff = call.data.replace("stars_", "")
    if tariff not in TARIFFS:
        return
    data = TARIFFS[tariff]
    payload = f"ixxy:{tariff}:{call.from_user.id}"
    prices = [
        LabeledPrice(
            label=f"IXXY VPN — {data['name']}",
            amount=data["stars"],
        )
    ]
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=f"IXXY VPN — {data['name']}",
        description=(
            f"{data['description']}. "
            "Подписка навсегда."
        ),
        payload=payload,
        currency="XTR",
        prices=prices,
    )
# ============================================================
# PRE-CHECKOUT
# ============================================================
@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)
# ============================================================
# УСПЕШНАЯ ОПЛАТА STARS
# ============================================================
@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    if not payload.startswith("ixxy:"):
        return
    parts = payload.split(":")
    if len(parts) != 3:
        return
    _, tariff, user_id = parts
    user_id = int(user_id)
    if tariff not in TARIFFS:
        return
    payment_id = payment.telegram_payment_charge_id
    try:
        create_payment(
            user_id=user_id,
            payment_id=payment_id,
            external_id=payment.provider_payment_charge_id,
            amount=TARIFFS[tariff]["stars"],
            currency="XTR",
            tariff=tariff,
            provider="telegram_stars",
        )
    except Exception:
        logger.exception("Stars payment database error")
    activate_tariff(
        user_id,
        tariff,
    )
    link = get_subscription_link(user_id)
    await message.answer(
        "✅ <b>Оплата прошла успешно!</b>\n\n"
        f"☂️ Тариф: <b>{TARIFFS[tariff]['name']}</b>\n"
        "⏳ Срок: <b>навсегда</b>\n\n"
        "🔗 Ваша подписка:\n"
        f"<code>{escape(link)}</code>",
        reply_markup=main_keyboard(),
    )
# ============================================================
# CABINET
# ============================================================
@dp.callback_query(F.data == "cabinet")
async def cabinet(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id
    user = get_user(user_id)
    if not user:
        create_user(
            user_id,
            call.from_user.username,
            call.from_user.first_name,
        )
        user = get_user(user_id)
    if not user or not user.get("subscription"):
        await call.message.edit_text(
            "👤 <b>Моя подписка</b>\n\n"
            "❌ Активной подписки нет.",
            reply_markup=main_keyboard(),
        )
        return
    tariff = user.get("tariff")
    if tariff not in TARIFFS:
        await call.message.edit_text(
            "❌ Не удалось определить тариф.",
            reply_markup=main_keyboard(),
        )
        return
    link = get_subscription_link(user_id)
    await call.message.edit_text(
        "👤 <b>Моя подписка</b>\n\n"
        f"☂️ Тариф: <b>{TARIFFS[tariff]['name']}</b>\n"
        "⏳ Срок: <b>навсегда</b>\n\n"
        "🔗 <b>Ссылка на подписку:</b>\n"
        f"<code>{escape(link)}</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔗 Открыть подписку",
                        url=link,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💳 Купить другой тариф",
                        callback_data="buy",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="◀️ Назад",
                        callback_data="back_main",
                    )
                ],
            ]
        ),
    )
# ============================================================
# НАЗАД
# ============================================================
@dp.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(
        "☂️ <b>IXXY VPN</b>\n\n"
        "Все подписки действуют <b>навсегда</b>.",
        reply_markup=main_keyboard(),
    )
# ============================================================
# АДМИН-ПАНЕЛЬ
# ============================================================
@dp.message(Command("admin"))
async def admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "☂️ <b>IXXY VPN — Админ-панель</b>",
        reply_markup=admin_keyboard(),
    )
# ============================================================
# АДМИН — ПОЛЬЗОВАТЕЛИ
# ============================================================
@dp.callback_query(F.data == "admin_users")
async def admin_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await call.answer()
    users = get_all_users()
    if not users:
        text = "👥 Пользователей пока нет."
    else:
        lines = ["👥 <b>Пользователи</b>\n"]
        for user in users[:30]:
            user_id = user["user_id"]
            username = user.get("username") or "—"
            tariff = user.get("tariff") or "нет"
            lines.append(
                f"• <code>{user_id}</code> "
                f"@{escape(username)} — "
                f"<b>{escape(str(tariff))}</b>"
            )
        text = "\n".join(lines)
    await call.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="◀️ Админ-панель",
                        callback_data="admin_back",
                    )
                ]
            ]
        ),
    )
# ============================================================
# АДМИН — ПЛАТЕЖИ
# ============================================================
@dp.callback_query(F.data == "admin_payments")
async def admin_payments(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await call.answer()
    payments = get_all_payments()
    if not payments:
        text = "💳 Платежей пока нет."
    else:
        lines = ["💳 <b>Последние платежи</b>\n"]
        for payment in payments[:30]:
            lines.append(
                f"• <code>{payment['user_id']}</code> — "
                f"{escape(str(payment['tariff']))} — "
                f"{payment['amount']} "
                f"{escape(str(payment['currency']))} — "
                f"<b>{escape(str(payment['status']))}</b>"
            )
        text = "\n".join(lines)
    await call.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="◀️ Админ-панель",
                        callback_data="admin_back",
                    )
                ]
            ]
        ),
    )
# ============================================================
# АДМИН — СТАТИСТИКА
# ============================================================
@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await call.answer()
    stats = get_stats()
    await call.message.edit_text(
        "📊 <b>Статистика IXXY VPN</b>\n\n"
        f"👥 Пользователей: <b>{stats['total_users']}</b>\n"
        f"☂️ Активных подписок: <b>{stats['active_users']}</b>\n"
        f"💳 Оплаченных платежей: <b>{stats['paid_payments']}</b>\n"
        f"💰 Выручка RUB: <b>{stats['revenue_rub']} ₽</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="◀️ Админ-панель",
                        callback_data="admin_back",
                    )
                ]
            ]
        ),
    )
# ============================================================
# АДМИН — НАЗАД
# ============================================================
@dp.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа.", show_alert=True)
        return
    await call.answer()
    await call.message.edit_text(
        "☂️ <b>IXXY VPN — Админ-панель</b>",
        reply_markup=admin_keyboard(),
    )
# ============================================================
# ЗАПУСК
# ============================================================
async def main():
    logger.info("☂️ IXXY VPN bot starting...")
    await bot.delete_webhook(
        drop_pending_updates=True
    )
    await dp.start_polling(bot)
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())