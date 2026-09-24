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
    activate_tariff,
    disable_subscription,
    get_all_payments,
    get_stats,
    get_subscription_link,
    create_payment,
    mark_payment_paid,
)
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ixxy")
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
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
TARIFFS = {
    "basic": {
        "name": "Basic",
        "emoji": "🟢",
        "price_rub": 415,
        "price_stars": 309,
        "description": "Обычные / Wi-Fi серверы",
        "short": "Для Wi-Fi и обычного подключения",
    },
    "mobile": {
        "name": "Mobile",
        "emoji": "📱",
        "price_rub": 743,
        "price_stars": 637,
        "description": "Серверы с антиглушилкой",
        "short": "Для мобильного интернета",
    },
    "supra": {
        "name": "Supra",
        "emoji": "☂️",
        "price_rub": 1351,
        "price_stars": 1245,
        "description": "Все серверы",
        "short": "Полный доступ ко всем серверам",
    },
}
def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💎  КУПИТЬ ТАРИФ",
                    callback_data="buy",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤  МОЙ КАБИНЕТ",
                    callback_data="cabinet",
                )
            ],
        ]
    )
def tariffs_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢  BASIC   •   415 ₽",
                    callback_data="tariff:basic",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📱  MOBILE   •   743 ₽",
                    callback_data="tariff:mobile",
                )
            ],
            [
                InlineKeyboardButton(
                    text="☂️  SUPRA   •   1 351 ₽   •   ВЫГОДНО",
                    callback_data="tariff:supra",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤  МОЙ КАБИНЕТ",
                    callback_data="cabinet",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️  НАЗАД",
                    callback_data="back_main",
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
                    text=f"🇷🇺  CASHERA   •   {data['price_rub']} ₽",
                    callback_data=f"pay_rub:{tariff}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⭐  TELEGRAM STARS   •   {data['price_stars']} ⭐",
                    callback_data=f"pay_stars:{tariff}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️  ВЫБРАТЬ ДРУГОЙ ТАРИФ",
                    callback_data="buy",
                )
            ],
        ]
    )
def admin_users_menu(users):
    buttons = []
    for user in users:
        user_id = int(user["user_id"])
        name = (
            user.get("first_name")
            or user.get("username")
            or str(user_id)
        )
        name = escape(str(name))
        tariff = user.get("tariff")
        if tariff in TARIFFS:
            tariff_label = (
                f"{TARIFFS[tariff]['emoji']} "
                f"{TARIFFS[tariff]['name']}"
            )
        else:
            tariff_label = "❌ Нет тарифа"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"👤 {name}  •  {tariff_label}",
                    callback_data=f"admin:user:{user_id}",
                )
            ]
        )
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="🔎  ПОИСК ПОЛЬЗОВАТЕЛЯ",
                    callback_data="admin:search",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊  СТАТИСТИКА",
                    callback_data="admin:stats",
                )
            ],
        ]
    )
    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )
def admin_user_menu(user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢  ВЫДАТЬ BASIC",
                    callback_data=f"admin:set:{user_id}:basic",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📱  ВЫДАТЬ MOBILE",
                    callback_data=f"admin:set:{user_id}:mobile",
                )
            ],
            [
                InlineKeyboardButton(
                    text="☂️  ВЫДАТЬ SUPRA",
                    callback_data=f"admin:set:{user_id}:supra",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌  ЗАБРАТЬ ТАРИФ",
                    callback_data=f"admin:disable:{user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳  ПЛАТЕЖИ ПОЛЬЗОВАТЕЛЯ",
                    callback_data=f"admin:payments:{user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥  К ПОЛЬЗОВАТЕЛЯМ",
                    callback_data="admin:users",
                )
            ],
        ]
    )
def admin_stats_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥  ПОЛЬЗОВАТЕЛИ",
                    callback_data="admin:users",
                )
            ],
        ]
    )
def is_admin(user_id):
    return user_id in ADMIN_IDS
def subscription_link(user_id):
    try:
        link = get_subscription_link(user_id)
        if link:
            return str(link)
    except Exception:
        logger.exception(
            "Ошибка получения ссылки подписки"
        )
    return (
        f"{PUBLIC_SITE_URL}/sub/"
        f"{SUBSCRIPTION_PREFIX}{user_id}"
    )
def get_tariff_label(tariff):
    if tariff not in TARIFFS:
        return "❌ <b>Тариф не выдан</b>"
    data = TARIFFS[tariff]
    return (
        f"{data['emoji']} "
        f"<b>{data['name']}</b>"
    )
def user_card(user):
    user_id = int(user["user_id"])
    first_name = escape(
        str(user.get("first_name") or "Без имени")
    )
    username = user.get("username")
    if username:
        username_line = (
            f"👤  <b>@{escape(str(username))}</b>"
        )
    else:
        username_line = "👤  <b>Username не указан</b>"
    tariff = user.get("tariff")
    if tariff in TARIFFS:
        data = TARIFFS[tariff]
        tariff_line = (
            f"{data['emoji']}  <b>{data['name']}</b>\n"
            f"📡  {escape(data['description'])}"
        )
    else:
        tariff_line = (
            "❌  <b>Тариф не выдан</b>"
        )
    link = escape(
        subscription_link(user_id)
    )
    return (
        "╭────────────────────╮\n"
        "       👤 <b>МОЙ КАБИНЕТ</b>\n"
        "╰────────────────────╯\n\n"
        f"👋  <b>{first_name}</b>\n"
        f"{username_line}\n\n"
        f"🆔  <b>ID:</b> <code>{user_id}</code>\n\n"
        "📦  <b>ВАШ ТАРИФ</b>\n"
        f"{tariff_line}\n\n"
        "♾️  <b>Срок:</b> навсегда\n\n"
        "🔗  <b>ПОДПИСКА</b>\n"
        f"<code>{link}</code>\n\n"
        "╰────────────────────╯"
    )
def tariff_card(tariff):
    data = TARIFFS[tariff]
    return (
        f"{data['emoji']} <b>{data['name'].upper()}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📡  <b>{escape(data['description'])}</b>\n"
        f"💡  {escape(data['short'])}\n\n"
        f"💰  <b>{data['price_rub']} ₽</b>\n"
        f"⭐  <b>{data['price_stars']} ⭐</b>\n"
        "♾️  <b>Навсегда</b>"
    )
@router.message(CommandStart())
async def start_handler(message: Message):
    user = message.from_user
    create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )
    text = (
        "☂️ <b>IXXY VPN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🚀 <b>Быстрый и стабильный VPN</b>\n\n"
        "💎 Три тарифа под разные задачи.\n"
        "♾️ Все тарифы выдаются <b>навсегда</b>.\n\n"
        "🔐 Простое подключение.\n"
        "⚡ Быстрый доступ к серверам.\n\n"
        "👇 <b>Выберите действие:</b>"
    )
    await message.answer(
        text,
        reply_markup=main_menu(),
    )
@router.callback_query(F.data == "buy")
async def buy_handler(callback: CallbackQuery):
    text = (
        "☂️ <b>ТАРИФЫ IXXY VPN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 <b>BASIC</b>\n"
        "💰 415 ₽   •   ⭐ 309 ⭐\n"
        "📡 Обычные / Wi-Fi серверы\n"
        "♾️ Навсегда\n\n"
        "📱 <b>MOBILE</b>\n"
        "💰 743 ₽   •   ⭐ 637 ⭐\n"
        "📡 Серверы с антиглушилкой\n"
        "♾️ Навсегда\n\n"
        "☂️ <b>SUPRA</b>  •  <b>ВЫГОДНО</b>\n"
        "💰 1 351 ₽   •   ⭐ 1 245 ⭐\n"
        "📡 Все серверы\n"
        "♾️ Навсегда\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👇 <b>Выберите тариф:</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=tariffs_menu(),
    )
    await callback.answer()
@router.callback_query(F.data.startswith("tariff:"))
async def tariff_handler(callback: CallbackQuery):
    tariff = callback.data.split(":", 1)[1]
    if tariff not in TARIFFS:
        await callback.answer(
            "Тариф не найден",
            show_alert=True,
        )
        return
    text = (
        tariff_card(tariff)
        + "\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💳 <b>СПОСОБ ОПЛАТЫ</b>\n\n"
        "Выберите удобный вариант:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=payment_menu(tariff),
    )
    await callback.answer()
@router.callback_query(F.data.startswith("pay_stars:"))
async def stars_payment(callback: CallbackQuery):
    tariff = callback.data.split(":", 1)[1]
    if tariff not in TARIFFS:
        await callback.answer(
            "Ошибка тарифа",
            show_alert=True,
        )
        return
    data = TARIFFS[tariff]
    try:
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
        payload = (
            f"ixxy:{tariff}:"
            f"{callback.from_user.id}:"
            f"{payment_id}"
        )
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"IXXY VPN — {data['name']}",
            description=(
                f"{data['description']}. "
                "Тариф навсегда."
            ),
            payload=payload,
            currency="XTR",
            prices=[
                LabeledPrice(
                    label=f"IXXY {data['name']}",
                    amount=data["price_stars"],
                )
            ],
        )
        await callback.answer()
    except Exception:
        logger.exception(
            "Ошибка создания Stars-платежа"
        )
        await callback.answer(
            "Не удалось создать платёж",
            show_alert=True,
        )
@router.pre_checkout_query()
async def pre_checkout_handler(
    query: PreCheckoutQuery,
):
    await query.answer(ok=True)
@router.message(F.successful_payment)
async def successful_payment_handler(
    message: Message,
):
    payment = message.successful_payment
    parts = payment.invoice_payload.split(":")
    if len(parts) != 4:
        return
    if parts[0] != "ixxy":
        return
    tariff = parts[1]
    if tariff not in TARIFFS:
        return
    try:
        payment_db_id = int(parts[3])
    except ValueError:
        return
    user_id = message.from_user.id
    mark_payment_paid(
        payment_id=payment_db_id,
        external_id=str(
            payment.telegram_payment_charge_id
        ),
    )
    activate_tariff(
        user_id,
        tariff,
    )
    data = TARIFFS[tariff]
    await message.answer(
        "✅ <b>ОПЛАТА УСПЕШНО ПОЛУЧЕНА</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{data['emoji']}  <b>{data['name']}</b>\n"
        f"📡  {escape(data['description'])}\n"
        "♾️  <b>Навсегда</b>\n\n"
        "🔗 <b>Ваша подписка:</b>\n"
        f"<code>{escape(subscription_link(user_id))}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "☂️ <b>IXXY VPN</b>",
        reply_markup=main_menu(),
    )
@router.callback_query(F.data.startswith("pay_rub:"))
async def rub_payment(callback: CallbackQuery):
    tariff = callback.data.split(":", 1)[1]
    if tariff not in TARIFFS:
        await callback.answer(
            "Ошибка тарифа",
            show_alert=True,
        )
        return
    data = TARIFFS[tariff]
    try:
        from cashera import create_cashera_payment
        result = create_cashera_payment(
            user_id=callback.from_user.id,
            amount=data["price_rub"],
            tariff=tariff,
        )
        external_id = result.get(
            "external_id"
        )
        payment_uuid = result.get(
            "uuid"
        )
        payment_id = create_payment(
            user_id=callback.from_user.id,
            payment_id=str(payment_uuid),
            external_id=external_id,
            amount=data["price_rub"],
            currency="RUB",
            tariff=tariff,
            status="pending",
            provider="cashera",
        )
        payment_url = result.get(
            "payment_url"
        )
        if not payment_url:
            raise RuntimeError(
                "CasheRa не вернула ссылку на оплату"
            )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"💳  ОПЛАТИТЬ {data['price_rub']} ₽",
                        url=payment_url,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️  НАЗАД",
                        callback_data=f"tariff:{tariff}",
                    )
                ],
            ]
        )
        await callback.message.edit_text(
            "💳 <b>ОПЛАТА IXXY VPN</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"{data['emoji']}  <b>{data['name']}</b>\n"
            f"📡  {escape(data['description'])}\n\n"
            f"💰  <b>{data['price_rub']} ₽</b>\n"
            "♾️  <b>Навсегда</b>\n\n"
            "👇 <b>Нажмите кнопку ниже для оплаты:</b>\n\n"
            "━━━━━━━━━━━━━━━━━━",
            reply_markup=keyboard,
        )
        await callback.answer()
    except Exception:
        logger.exception(
            "Ошибка создания CasheRa-платежа"
        )
        await callback.answer(
            "Не удалось создать платёж",
            show_alert=True,
        )
@router.callback_query(F.data == "cabinet")
async def cabinet_handler(
    callback: CallbackQuery,
):
    user = get_user(
        callback.from_user.id
    )
    if not user:
        create_user(
            user_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )
        user = get_user(
            callback.from_user.id
        )
    await callback.message.edit_text(
        user_card(user),
        reply_markup=main_menu(),
    )
    await callback.answer()
@router.callback_query(F.data == "back_main")
async def back_main(
    callback: CallbackQuery,
):
    await callback.message.edit_text(
        "☂️ <b>IXXY VPN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🚀 Быстрый и стабильный VPN.\n\n"
        "💎 Выберите тариф под свои задачи.\n"
        "♾️ Все тарифы выдаются <b>навсегда</b>.\n\n"
        "👇 <b>Выберите действие:</b>",
        reply_markup=main_menu(),
    )
    await callback.answer()
@router.message(Command("admin"))
async def admin_handler(
    message: Message,
):
    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ <b>Доступ запрещён.</b>"
        )
        return
    users = get_all_users()
    await message.answer(
        "🛠 <b>IXXY VPN — АДМИН-ПАНЕЛЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Пользователей: <b>{len(users)}</b>\n\n"
        "Выберите пользователя:",
        reply_markup=admin_users_menu(users),
    )
@router.callback_query(F.data == "admin:users")
async def admin_users(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Доступ запрещён",
            show_alert=True,
        )
        return
    users = get_all_users()
    await callback.message.edit_text(
        "🛠 <b>ПОЛЬЗОВАТЕЛИ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Всего пользователей: <b>{len(users)}</b>\n\n"
        "👇 Выберите пользователя:",
        reply_markup=admin_users_menu(users),
    )
    await callback.answer()
@router.callback_query(F.data.startswith("admin:user:"))
async def admin_user(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Доступ запрещён",
            show_alert=True,
        )
        return
    user_id = int(
        callback.data.split(":")[2]
    )
    user = get_user(user_id)
    if not user:
        await callback.answer(
            "Пользователь не найден",
            show_alert=True,
        )
        return
    text = (
        "🛠 <b>КАРТОЧКА ПОЛЬЗОВАТЕЛЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        + user_card(user)
        + "\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚙️ <b>УПРАВЛЕНИЕ ТАРИФОМ</b>\n\n"
        "Выберите действие:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_user_menu(user_id),
    )
    await callback.answer()
@router.callback_query(F.data.startswith("admin:set:"))
async def admin_set_tariff(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Доступ запрещён",
            show_alert=True,
        )
        return
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer(
            "Ошибка команды",
            show_alert=True,
        )
        return
    user_id = int(parts[2])
    tariff = parts[3]
    if tariff not in TARIFFS:
        await callback.answer(
            "Ошибка тарифа",
            show_alert=True,
        )
        return
    user = get_user(user_id)
    if not user:
        await callback.answer(
            "Пользователь не найден",
            show_alert=True,
        )
        return
    activate_tariff(
        user_id,
        tariff,
    )
    user = get_user(user_id)
    data = TARIFFS[tariff]
    text = (
        "✅ <b>ТАРИФ ВЫДАН</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{data['emoji']} <b>{data['name']}</b>\n"
        f"📡 {escape(data['description'])}\n"
        "♾️ <b>Навсегда</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        + user_card(user)
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_user_menu(user_id),
    )
    await callback.answer(
        f"Тариф {data['name']} выдан"
    )
@router.callback_query(F.data.startswith("admin:disable:"))
async def admin_disable(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Доступ запрещён",
            show_alert=True,
        )
        return
    user_id = int(
        callback.data.split(":")[2]
    )
    user = get_user(user_id)
    if not user:
        await callback.answer(
            "Пользователь не найден",
            show_alert=True,
        )
        return
    disable_subscription(
        user_id
    )
    user = get_user(user_id)
    await callback.message.edit_text(
        "❌ <b>ТАРИФ ЗАБРАН</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        + user_card(user)
        + "\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Тариф пользователя удалён.",
        reply_markup=admin_user_menu(user_id),
    )
    await callback.answer(
        "Тариф забран"
    )
@router.callback_query(
    F.data.startswith("admin:payments:")
)
async def admin_user_payments(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Доступ запрещён",
            show_alert=True,
        )
        return
    user_id = int(
        callback.data.split(":")[2]
    )
    payments = get_all_payments(
        user_id=user_id
    )
    if not payments:
        text = (
            "💳 <b>ПЛАТЕЖИ ПОЛЬЗОВАТЕЛЯ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 ID: <code>{user_id}</code>\n\n"
            "📭 Платежей пока нет."
        )
    else:
        lines = [
            "💳 <b>ПЛАТЕЖИ ПОЛЬЗОВАТЕЛЯ</b>",
            "━━━━━━━━━━━━━━━━━━",
            "",
            f"🆔 ID: <code>{user_id}</code>",
            "",
        ]
        for payment in payments[:20]:
            tariff = payment.get("tariff") or "—"
            amount = payment.get("amount") or 0
            currency = payment.get("currency") or "RUB"
            provider = payment.get("provider") or "—"
            status = payment.get("status") or "—"
            data = TARIFFS.get(tariff)
            if data:
                tariff_name = (
                    f"{data['emoji']} "
                    f"{data['name']}"
                )
            else:
                tariff_name = str(tariff)
            lines.append(
                f"📦 <b>{escape(tariff_name)}</b>"
            )
            lines.append(
                f"💰 {amount} {escape(str(currency))}"
            )
            lines.append(
                f"🏦 {escape(str(provider))}"
            )
            lines.append(
                f"📌 {escape(str(status))}"
            )
            lines.append("")
        text = "\n".join(lines)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️  К ПОЛЬЗОВАТЕЛЮ",
                    callback_data=f"admin:user:{user_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥  ПОЛЬЗОВАТЕЛИ",
                    callback_data="admin:users",
                )
            ],
        ]
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
    )
    await callback.answer()
@router.callback_query(F.data == "admin:stats")
async def admin_stats(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Доступ запрещён",
            show_alert=True,
        )
        return
    stats = get_stats()
    text = (
        "📊 <b>СТАТИСТИКА IXXY</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Пользователи</b>\n"
        f"Всего: <b>{stats.get('users', 0)}</b>\n\n"
        f"🟢 <b>Basic:</b> "
        f"{stats.get('basic', 0)}\n"
        f"📱 <b>Mobile:</b> "
        f"{stats.get('mobile', 0)}\n"
        f"☂️ <b>Supra:</b> "
        f"{stats.get('supra', 0)}\n\n"
        f"❌ <b>Без тарифа:</b> "
        f"{stats.get('without_tariff', 0)}\n\n"
        f"💳 <b>Платежей:</b> "
        f"{stats.get('payments', 0)}\n\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_stats_menu(),
    )
    await callback.answer()
async def main():
    init_db()
    dp.include_router(router)
    logger.info("☂️ IXXY VPN BOT STARTED")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())