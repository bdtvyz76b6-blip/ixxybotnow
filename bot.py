# ═══════════════════════════════════════════════════════════════
#  IXXY VPN BOT v2.1 — multi-tariff, no HTML tags
#  aiogram 3 + SQLite + GitHub Subs + CasheRa + FastAPI
# ═══════════════════════════════════════════════════════════════
import asyncio
import base64
import logging
import os
import random
import uuid as uuid_lib
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite
import httpx
import uvicorn
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("ixxy")

# ══════════════════════════ CONFIG ══════════════════════════
BOT_TOKEN     = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS     = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DB_PATH       = "ixxy.db"
SERVERS_DIR   = "servers"

GITHUB_TOKEN  = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_REPO   = os.getenv("GITHUB_REPO", "").strip()
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip()
SUB_SALT      = os.getenv("SUB_SALT", "2suDb48").strip()
SUB_BASE      = os.getenv("SUB_BASE", "https://ixxysubscription.onrender.com").rstrip("/")

CASHERA_API_KEY = os.getenv("CASHERA_API_KEY", "").strip()
CASHERA_BASE    = "https://api.cashera.cash/api/v1"
PUBLIC_SITE_URL = os.getenv("PUBLIC_SITE_URL", "https://ixxyweb.onrender.com").rstrip("/")

PORT = int(os.getenv("PORT", "8000"))

TARIFFS = {
    "basic": {
        "name": "🟢 BASIC",
        "short": "BASIC",
        "file": "basic.txt",
        "price_per_day": 5,
        "tagline": "Домашний Wi-Fi · стриминг · учёба",
        "vibe": "🛋 Комфорт у дивана",
        "desc": (
            "🟢 BASIC — домашний воин 🛋\n\n"
            "🏠 Идеально для Wi-Fi и стационарного интернета\n"
            "🎬 YouTube 4K, Netflix, Twitch — без тормозов\n"
            "📚 Работа, учёба, созвоны\n"
            "⚡ Низкий пинг, стабильная скорость\n"
            "🔒 Шифрование AES-256\n\n"
            "💵 5 ₽ / день\n\n"
            "🎯 Для кого: для тех, кто сидит дома и хочет\n"
            "YouTube без рекламы и блокировок"
        ),
    },
    "mobile": {
        "name": "📱 MOBILE",
        "short": "MOBILE",
        "file": "mobile.txt",
        "price_per_day": 8,
        "tagline": "LTE/5G · обход белых списков · антиглушилки",
        "vibe": "🚗 Свобода в движении",
        "desc": (
            "📱 MOBILE — кочевник с LTE 🚗\n\n"
            "🚀 Обход белых списков (МТС, Билайн, Мегафон, Tele2)\n"
            "🛡 Антиглушилки — работает там, где всё лежит\n"
            "🌍 Спасает в поездках, командировках и на даче\n"
            "📶 Заточен под мобильный интернет 4G/5G\n"
            "⚡ Быстрое переключение между вышками\n\n"
            "💵 8 ₽ / день\n\n"
            "🎯 Для кого: для тех, кто в дороге, на природе\n"
            "или в зоне внезапных блокировок"
        ),
    },
    "supra": {
        "name": "👑 SUPRA",
        "short": "SUPRA",
        "file": "supra.txt",
        "price_per_day": 14,
        "tagline": "Всё включено + эксклюзив от админа",
        "vibe": "💎 Царский уровень",
        "desc": (
            "👑 SUPRA — элита 💎\n\n"
            "🎁 Всё из BASIC и MOBILE\n"
            "💎 Эксклюзивные серверы лично от админа\n"
            "🚀 Максимальный приоритет и пропускная способность\n"
            "🛡 VIP-поддержка в любое время\n"
            "🔥 Только для тех, кто не готов тормозить\n\n"
            "💵 14 ₽ / день\n\n"
            "🎯 Для кого: для перфекционистов и тех,\n"
            "кому нужен максимум"
        ),
    },
}

SERVER_EMOJI = ["⚡","🚀","🔥","💎","🌊","🗾","🏔","🌆","🌌","🎯","🛡","⚔️","🌟","👑","🦅"]

# ══════════════════════════ COOL TEXTS ══════════════════════════
FACTS = [
    "💡 Факт: в 2023 году в России заблокировали более 600 000 сайтов.",
    "💡 Факт: VPN-трафик шифруется AES-256 — даже провайдер не прочитает.",
    "💡 Факт: слово «VPN» впервые появилось ещё в 1996 году.",
    "💡 Факт: Wi-Fi сети в кафе — рай для перехвата данных. VPN спасает.",
    "💡 Факт: 9 из 10 публичных Wi-Fi не шифруют трафик.",
    "💡 Факт: средний пользователь за день оставляет 700+ цифровых следов.",
    "💡 Факт: VPN не только для обхода — это защита в открытых сетях.",
    "💡 Факт: DPI-системы в РФ анализируют до 40 Тбит/с трафика.",
]

TIPS = [
    "🔒 Совет: не подключайся к банку через публичный Wi-Fi без VPN.",
    "🛡 Совет: смени сервер, если скорость просела — часто помогает.",
    "⚡ Совет: включай VPN до открытия приложения, а не после.",
    "🔐 Совет: не используй один пароль для всего — это опасно.",
    "📱 Совет: для мобильного интернета лучше всего подходит MOBILE.",
    "🏠 Совет: для дома хватает BASIC, а SUPRA — если нужен максимум.",
    "🌐 Совет: VLESS — быстрее и незаметнее, чем OpenVPN.",
    "🚀 Совет: чем ближе сервер к тебе — тем меньше пинг.",
]

HOWTO_TEXT = (
    "📱 Как подключиться к IXXY VPN\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "1. Скачай клиент:\n\n"
    "   • iOS — Streisand или Hiddify\n"
    "   • Android — v2rayNG, Hiddify, NekoBox\n"
    "   • Windows / macOS — Hiddify или Nekoray\n"
    "   • Linux — Nekoray, Hiddify\n\n"
    "2. Открой личный кабинет и скопируй ссылку\n\n"
    "3. В приложении нажми + и выбери Импорт из буфера\n\n"
    "4. Нажми Подключиться 🚀\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "❓ Не работает — жми Сменить сервер в кабинете"
)

HELP_TEXT = (
    "ℹ️ Помощь IXXY\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "🛒 Тарифы — выбрать и купить подписку\n"
    "👤 Кабинет — твои подписки, ссылки, серверы\n"
    "📱 Как подключить — пошаговая инструкция\n"
    "🔄 Сменить сервер — если что-то не летит\n"
    "🎁 Пробный день — 1 день BASIC бесплатно\n"
    "💬 Вопрос админу — пиши в ЛС\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "🛡 Мы не ведём логи и не храним трафик.\n"
    "🛡 Каждая подписка независима — можно держать\n"
    "   сразу все три тарифа одновременно.\n"
    "🛡 Ссылка обновляется автоматически в GitHub."
)

ABOUT_TEXT = (
    "🚀 IXXY VPN\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "🌍 Свобода без границ\n"
    "🔒 Скорость без компромиссов\n"
    "💎 Твой туннель — твои правила\n\n"
    "Мы делаем VPN, который:\n"
    "• Работает быстро и стабильно\n"
    "• Обходит белые списки и глушилки\n"
    "• Не хранит логи\n"
    "• Стоит от 5 ₽ в день\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "IXXY — интернет, каким он должен быть."
)

# ══════════════════════════ BOT INIT ══════════════════════════
bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ══════════════════════════ HELPERS ══════════════════════════
def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def load_servers(key: str) -> list[str]:
    path = Path(SERVERS_DIR) / TARIFFS[key]["file"]
    if not path.exists():
        return []
    return [
        l.strip() for l in path.read_text(encoding="utf-8").splitlines()
        if l.strip() and not l.startswith("#")
    ]

def server_alias(link: str) -> str:
    if "#" in link:
        name = link.split("#", 1)[1].replace("_", " ").replace("-", " ").strip()
        if name:
            return f"{random.choice(SERVER_EMOJI)} {name}"
    return f"{random.choice(SERVER_EMOJI)} IXXY Node"

def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y · %H:%M")

def parse_dt(s):
    return datetime.fromisoformat(s) if s else None

def progress_bar(pct: float, length: int = 14) -> str:
    filled = int(length * pct / 100)
    return "▓" * filled + "░" * (length - filled)

def fmt_price(n: int) -> str:
    return f"{int(n):,}".replace(",", " ") + " ₽"

def sub_path(tariff: str, user_id: int) -> str:
    return f"{tariff}/{SUB_SALT}{user_id}.txt"

def sub_url(tariff: str, user_id: int) -> str:
    return f"{SUB_BASE}/{tariff}/{SUB_SALT}{user_id}"

def random_fact() -> str:
    return random.choice(FACTS)

def random_tip() -> str:
    return random.choice(TIPS)

# ══════════════════════════ DATABASE ══════════════════════════
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY,
            username      TEXT,
            first_name    TEXT,
            created_at    TEXT,
            trial_used    INTEGER DEFAULT 0,
            is_banned     INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            tariff        TEXT NOT NULL,
            server_link   TEXT,
            server_alias  TEXT,
            started_at    TEXT,
            expires_at    TEXT,
            created_at    TEXT,
            UNIQUE(user_id, tariff)
        );
        CREATE TABLE IF NOT EXISTS tickets (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            tariff     TEXT,
            days       INTEGER,
            amount     INTEGER,
            status     TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS pending_payments (
            payment_uuid TEXT PRIMARY KEY,
            user_id      INTEGER,
            tariff       TEXT,
            days         INTEGER,
            amount       INTEGER,
            created_at   TEXT
        );
        """)
        await db.commit()

async def get_user(uid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        return await cur.fetchone()

async def upsert_user(uid, username, first_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name
        """, (uid, username, first_name, datetime.now().isoformat()))
        await db.commit()

async def get_sub(uid: int, tariff: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subscriptions WHERE user_id=? AND tariff=?",
            (uid, tariff),
        )
        return await cur.fetchone()

async def get_user_subs(uid: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subscriptions WHERE user_id=? ORDER BY tariff",
            (uid,),
        )
        return await cur.fetchall()

async def upsert_sub(uid: int, tariff: str, days: int,
                     server_link: str, server_alias: str) -> None:
    now = datetime.now()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subscriptions WHERE user_id=? AND tariff=?",
            (uid, tariff),
        )
        existing = await cur.fetchone()

        if days == 0:
            new_exp = None
        elif existing and existing["expires_at"]:
            cur_exp = parse_dt(existing["expires_at"])
            base = cur_exp if cur_exp and cur_exp > now else now
            new_exp = base + timedelta(days=days)
        else:
            new_exp = now + timedelta(days=days)

        started = existing["started_at"] if existing else now.isoformat()
        exp_iso = new_exp.isoformat() if new_exp else None

        if existing:
            await db.execute(
                "UPDATE subscriptions SET server_link=?, server_alias=?, "
                "started_at=?, expires_at=? WHERE user_id=? AND tariff=?",
                (server_link, server_alias, started, exp_iso, uid, tariff),
            )
        else:
            await db.execute(
                "INSERT INTO subscriptions "
                "(user_id, tariff, server_link, server_alias, started_at, expires_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uid, tariff, server_link, server_alias, started, exp_iso, now.isoformat()),
            )
        await db.commit()

async def update_sub_server(uid: int, tariff: str, link: str, alias: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET server_link=?, server_alias=? "
            "WHERE user_id=? AND tariff=?",
            (link, alias, uid, tariff),
        )
        await db.commit()

async def delete_sub(uid: int, tariff: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM subscriptions WHERE user_id=? AND tariff=?",
            (uid, tariff),
        )
        await db.commit()

async def cleanup_expired(uid: int | None = None) -> None:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        if uid is None:
            await db.execute(
                "DELETE FROM subscriptions WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now,),
            )
        else:
            await db.execute(
                "DELETE FROM subscriptions WHERE user_id=? AND expires_at IS NOT NULL AND expires_at < ?",
                (uid, now),
            )
        await db.commit()

async def create_ticket(uid: int, tariff: str, days: int, amount: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO tickets (user_id, tariff, days, amount, status, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (uid, tariff, days, amount, datetime.now().isoformat()),
        )
        await db.commit()
        return cur.lastrowid

async def get_ticket(tid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tickets WHERE id=?", (tid,))
        return await cur.fetchone()

async def close_ticket(tid: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET status=? WHERE id=?", (status, tid))
        await db.commit()

async def all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT user_id FROM users")
        return await cur.fetchall()

async def get_stats():
    await cleanup_expired()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM subscriptions")
        active = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(DISTINCT user_id) FROM subscriptions")
        paying_users = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM users WHERE trial_used=1")
        trials = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT tariff, COUNT(*) FROM subscriptions GROUP BY tariff"
        )
        by_tariff = await cur.fetchall()

        cur = await db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM tickets WHERE status='approved'"
        )
        revenue_all = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM tickets "
            "WHERE status='approved' AND DATE(created_at)=DATE('now')"
        )
        revenue_today = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM tickets "
            "WHERE status='approved' AND created_at >= datetime('now','-7 days')"
        )
        revenue_week = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM tickets "
            "WHERE status='approved' AND created_at >= datetime('now','-30 days')"
        )
        revenue_month = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT COALESCE(AVG(amount),0) FROM tickets WHERE status='approved'"
        )
        avg_check = int((await cur.fetchone())[0] or 0)

        cur = await db.execute(
            "SELECT COUNT(*) FROM users WHERE trial_used=1 "
            "AND user_id IN (SELECT DISTINCT user_id FROM subscriptions)"
        )
        trial_converted = (await cur.fetchone())[0]

        return {
            "total": total, "active": active, "paying_users": paying_users,
            "trials": trials, "trial_converted": trial_converted,
            "by_tariff": by_tariff,
            "revenue_all": revenue_all, "revenue_today": revenue_today,
            "revenue_week": revenue_week, "revenue_month": revenue_month,
            "avg_check": avg_check,
        }

async def save_pending(payment_uuid: str, user_id: int, tariff: str, days: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO pending_payments
            (payment_uuid, user_id, tariff, days, amount, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (payment_uuid, user_id, tariff, days, amount, datetime.now().isoformat()))
        await db.commit()

async def pop_pending(payment_uuid: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM pending_payments WHERE payment_uuid=?", (payment_uuid,)
        )
        row = await cur.fetchone()
        if row:
            await db.execute(
                "DELETE FROM pending_payments WHERE payment_uuid=?", (payment_uuid,)
            )
            await db.commit()
            return dict(row)
    return None

# ══════════════════════════ GITHUB ══════════════════════════
def _gh_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

async def _gh_get_sha(path: str) -> str | None:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}",
            headers=_gh_headers(),
            params={"ref": GITHUB_BRANCH},
        )
        if r.status_code == 200:
            return r.json().get("sha")
    return None

async def github_write_sub(tariff: str, user_id: int, content: str) -> None:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        log.warning("GitHub не настроен")
        return
    path = sub_path(tariff, user_id)
    sha = await _gh_get_sha(path)
    body = {
        "message": f"sub: {tariff}/{user_id}",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        body["sha"] = sha
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.put(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}",
            headers=_gh_headers(),
            json=body,
        )
        if r.status_code >= 300:
            log.error(f"GitHub write: {r.status_code} {r.text}")

async def github_delete_sub(tariff: str, user_id: int) -> None:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    path = sub_path(tariff, user_id)
    sha = await _gh_get_sha(path)
    if not sha:
        return
    async with httpx.AsyncClient(timeout=15) as c:
        await c.request(
            "DELETE",
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}",
            headers=_gh_headers(),
            json={"message": f"revoke {tariff}/{user_id}", "sha": sha, "branch": GITHUB_BRANCH},
        )

# ══════════════════════════ CASHERA ══════════════════════════
async def create_cashera_payment(user_id: int, amount: int, days: int) -> dict:
    if not CASHERA_API_KEY:
        raise RuntimeError("CASHERA_API_KEY не установлен")

    external_id = f"{user_id}_{uuid_lib.uuid4().hex}"
    amount_minor = int(amount * 100)
    callback_url = f"{PUBLIC_SITE_URL}/webhook/cashera"
    tg_url = "https://t.me/orelvpntopbot"

    headers = {
        "X-Api-Key": CASHERA_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        "amount": amount_minor,
        "currency": "RUB",
        "payment_method": "sbp",
        "external_id": external_id,
        "description": f"IXXY VPN — {days} дней",
        "callback_url": callback_url,
        "success_url": tg_url,
        "fail_url": tg_url,
    }

    log.info(f"💳 CasheRa create: amount={amount_minor} ext={external_id}")

    async with httpx.AsyncClient(timeout=30) as c:
        try:
            r = await c.post(f"{CASHERA_BASE}/integration/transactions",
                             headers=headers, json=data)
        except httpx.RequestError as e:
            raise RuntimeError(f"CasheRa connection error: {e}")

    log.info(f"💳 CasheRa HTTP {r.status_code}: {r.text[:500]}")

    try:
        result = r.json()
    except Exception:
        raise RuntimeError(f"CasheRa non-JSON {r.status_code}: {r.text}")

    if r.status_code >= 300:
        raise RuntimeError(f"CasheRa HTTP {r.status_code}: {result}")

    tx = result.get("transaction") if isinstance(result, dict) else None
    if isinstance(tx, dict):
        merged = dict(result); merged.update(tx); result = merged

    payment_uuid = result.get("uuid") or result.get("id") or result.get("transaction_id")
    payment_url = (result.get("payment_url") or result.get("paymentUrl")
                   or result.get("url") or result.get("pay_url"))

    if not payment_uuid:
        raise RuntimeError(f"CasheRa no uuid: {result}")
    if not payment_url:
        raise RuntimeError(f"CasheRa no payment_url: {result}")

    result["uuid"] = str(payment_uuid)
    result["payment_url"] = str(payment_url)
    return result

# ══════════════════════════ BUSINESS LOGIC ══════════════════════════
async def activate_tariff(user_id: int, tariff: str, days: int) -> bool:
    servers = load_servers(tariff)
    if not servers:
        log.error(f"Нет серверов для {tariff}")
        return False

    link = random.choice(servers)
    alias = server_alias(link)

    content = "\n".join(servers) + "\n"
    try:
        await github_write_sub(tariff, user_id, content)
    except Exception as e:
        log.error(f"github write: {e}")

    await upsert_sub(user_id, tariff, days, link, alias)
    return True

async def revoke_tariff(user_id: int, tariff: str | None = None) -> list[str]:
    removed = []
    if tariff:
        sub = await get_sub(user_id, tariff)
        if sub:
            try:
                await github_delete_sub(tariff, user_id)
            except Exception as e:
                log.error(f"github delete: {e}")
            await delete_sub(user_id, tariff)
            removed.append(tariff)
    else:
        subs = await get_user_subs(user_id)
        for s in subs:
            try:
                await github_delete_sub(s["tariff"], user_id)
            except Exception as e:
                log.error(f"github delete: {e}")
            removed.append(s["tariff"])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
            await db.commit()
    return removed

async def reroll_server(user_id: int, tariff: str) -> str | None:
    servers = load_servers(tariff)
    if not servers:
        return None
    link = random.choice(servers)
    alias = server_alias(link)
    await update_sub_server(user_id, tariff, link, alias)
    return link

async def user_has_trial_basic(uid: int) -> bool:
    sub = await get_sub(uid, "basic")
    if not sub:
        return False
    exp = parse_dt(sub["expires_at"])
    return exp is None or exp > datetime.now()

# ══════════════════════════ FSM ══════════════════════════
class BuyFSM(StatesGroup):
    days = State()

class GiveFSM(StatesGroup):
    user = State()
    tariff = State()
    days = State()

class RevokeFSM(StatesGroup):
    user = State()
    tariff = State()

class BroadcastFSM(StatesGroup):
    text = State()

# ══════════════════════════ KEYBOARDS ══════════════════════════
def main_menu(uid: int, trial_available: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🛒 Тарифы", callback_data="tariffs"),
         InlineKeyboardButton(text="👤 Кабинет", callback_data="my")],
    ]
    if trial_available:
        rows.append([InlineKeyboardButton(text="🎁 Пробный день БЕСПЛАТНО", callback_data="trial")])
    rows.append([
        InlineKeyboardButton(text="📱 Как подключить", callback_data="howto"),
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help"),
    ])
    rows.append([InlineKeyboardButton(text="🌟 О IXXY", callback_data="about")])
    if is_admin(uid):
        rows.append([InlineKeyboardButton(text="⚙️ Админка", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="a_stats")],
        [InlineKeyboardButton(text="👥 Выдать тариф", callback_data="a_give")],
        [InlineKeyboardButton(text="❌ Забрать тариф", callback_data="a_revoke")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="a_broadcast")],
        [InlineKeyboardButton(text="🔗 Серверы", callback_data="a_servers")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
    ])

def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")]
    ])

# ══════════════════════════ USER: START ══════════════════════════
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    u = message.from_user
    await upsert_user(u.id, u.username, u.first_name)
    user = await get_user(u.id)
    trial_ok = not user["trial_used"] and not await user_has_trial_basic(u.id)

    intro = (
        "╭──────────────────────────────╮\n"
        "│   🚀  IXXY VPN  ·  v2.1      │\n"
        "╰──────────────────────────────╯\n\n"
        f"👋 Привет, {u.first_name}!\n\n"
        "🌍 Свобода без границ\n"
        "⚡ Скорость без компромиссов\n"
        "🔒 Твой туннель — твои правила\n\n"
    )
    if trial_ok:
        intro += "🎁 У тебя есть пробный день — попробуй бесплатно!\n\n"
    intro += random_fact() + "\n\n"
    intro += "Выбери действие ниже 👇"

    await message.answer(intro, reply_markup=main_menu(u.id, trial_ok))

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✋ Отменено.", reply_markup=main_menu(message.from_user.id))

@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "⚙️ IXXY · Админ-панель\n\nУправляй вселенной 👇",
        reply_markup=admin_menu(),
    )

@dp.callback_query(F.data == "menu")
async def cb_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_user(cb.from_user.id)
    trial_ok = bool(user and not user["trial_used"]) and not await user_has_trial_basic(cb.from_user.id)
    await cb.message.edit_text(
        "🏠 Главное меню\n\n" + random_tip() + "\n\nВыбери действие 👇",
        reply_markup=main_menu(cb.from_user.id, trial_ok),
    )

# ══════════════════════════ USER: ABOUT / HELP / HOWTO ══════════════════════════
@dp.callback_query(F.data == "about")
async def cb_about(cb: CallbackQuery):
    await cb.message.edit_text(ABOUT_TEXT, reply_markup=back_menu())

@dp.callback_query(F.data == "help")
async def cb_help(cb: CallbackQuery):
    await cb.message.edit_text(HELP_TEXT, reply_markup=back_menu())

@dp.callback_query(F.data == "howto")
async def cb_howto(cb: CallbackQuery):
    await cb.message.edit_text(
        HOWTO_TEXT,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 В кабинет", callback_data="my")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
        ]),
    )

# ══════════════════════════ USER: TARIFFS ══════════════════════════
@dp.callback_query(F.data == "tariffs")
async def cb_tariffs(cb: CallbackQuery):
    await cleanup_expired(cb.from_user.id)
    user_subs = {s["tariff"] for s in await get_user_subs(cb.from_user.id)}

    lines = [
        "🛒 Витрина тарифов IXXY\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]
    for k, t in TARIFFS.items():
        mark = "  ✅ уже активен" if k in user_subs else ""
        lines.append(
            f"{t['name']}  ·  {t['vibe']}\n"
            f"   {t['tagline']}\n"
            f"   💵 {t['price_per_day']} ₽ / день{mark}\n"
        )
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 Можно держать сразу все три тарифа")
    lines.append("Выбирай свой 👇")

    kb = []
    for k, t in TARIFFS.items():
        label = f"{t['name']} · {t['price_per_day']}₽/д"
        if k in user_subs:
            label = "✅ " + label
        kb.append([InlineKeyboardButton(text=label, callback_data=f"tariff:{k}")])
    kb.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])

    await cb.message.edit_text("\n".join(lines),
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("tariff:"))
async def cb_tariff(cb: CallbackQuery):
    key = cb.data.split(":")[1]
    t = TARIFFS[key]
    existing = await get_sub(cb.from_user.id, key)

    text = t["desc"]
    if existing:
        exp = parse_dt(existing["expires_at"])
        if exp:
            left = max(0, (exp - datetime.now()).days)
            text += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            text += f"✅ У тебя уже активен этот тариф\n"
            text += f"📅 Осталось: {left} дн. (до {fmt_dt(exp)})\n"
            text += f"\n🔄 Покупка продлит текущий срок"
        else:
            text += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            text += f"💎 У тебя бессрочный доступ к этому тарифу"

    await cb.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Купить / продлить", callback_data=f"buy:{key}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="tariffs")],
        ]),
    )

# ══════════════════════════ USER: BUY ══════════════════════════
@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":")[1]
    t = TARIFFS[key]
    await state.set_state(BuyFSM.days)
    await state.update_data(tariff=key)

    presets = [7, 30, 90, 180, 365]
    rows = []
    for d in presets:
        rows.append([InlineKeyboardButton(
            text=f"{d} дн · {d * t['price_per_day']} ₽",
            callback_data=f"days:{d}",
        )])
    rows.append([InlineKeyboardButton(text="✏️ Своё количество дней", callback_data="days:custom")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"tariff:{key}")])

    await cb.message.edit_text(
        f"{t['name']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 Цена: {t['price_per_day']} ₽ / день\n\n"
        f"{random_tip()}\n\n"
        f"📅 На сколько дней берём?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )

@dp.callback_query(BuyFSM.days, F.data.startswith("days:"))
async def cb_days(cb: CallbackQuery, state: FSMContext):
    val = cb.data.split(":")[1]
    if val == "custom":
        data = await state.get_data()
        await cb.message.edit_text(
            "✏️ Напиши число дней (1–3650):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"buy:{data['tariff']}")]
            ]),
        )
        return
    await _finalize_buy(cb.from_user, state, int(val), edit_message=cb.message)

@dp.message(BuyFSM.days)
async def msg_days(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if not (1 <= days <= 3650):
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("❌ Нужно число от 1 до 3650.")
        return
    await _finalize_buy(message.from_user, state, days, reply_to=message)

async def _finalize_buy(user, state: FSMContext, days: int,
                        edit_message=None, reply_to: Message | None = None):
    data = await state.get_data()
    await state.clear()
    key = data["tariff"]
    t = TARIFFS[key]
    amount = days * t["price_per_day"]

    tid = await create_ticket(user.id, key, days, amount)

    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                "╭──────────────────────────────╮\n"
                "│    🔔  НОВАЯ ЗАЯВКА         │\n"
                "╰──────────────────────────────╯\n\n"
                f"👤 {user.full_name}\n"
                f"🔗 @{user.username or '—'}\n"
                f"🆔 {user.id}\n\n"
                f"🎫 Тариф:  {t['name']}\n"
                f"📅 Дней:   {days}\n"
                f"💰 Сумма:  {fmt_price(amount)}\n\n"
                f"Заявка #{tid}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Активировать",
                                          callback_data=f"approve:{tid}")],
                    [InlineKeyboardButton(text="❌ Отклонить",
                                          callback_data=f"reject:{tid}")],
                ]),
            )
        except Exception:
            pass

    pay_url = None
    if CASHERA_API_KEY:
        try:
            result = await create_cashera_payment(user.id, amount, days)
            pay_url = result["payment_url"]
            await save_pending(result["uuid"], user.id, key, days, amount)
        except Exception as e:
            log.error(f"CasheRa payment error: {e}")

    text = (
        f"🧾 Заявка #{tid} создана\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 {t['name']}\n"
        f"📅 {days} дн.\n"
        f"💰 Итого: {fmt_price(amount)}\n\n"
    )
    kb_rows = []
    if pay_url:
        text += "👇 Жми, чтобы оплатить:"
        kb_rows.append([InlineKeyboardButton(text="💳 Оплатить", url=pay_url)])
    else:
        text += "⏳ Админ свяжется для подтверждения оплаты."
    kb_rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    if edit_message:
        await edit_message.edit_text(text, reply_markup=kb)
    elif reply_to:
        await reply_to.answer(text, reply_markup=kb)

# ══════════════════════════ USER: TRIAL ══════════════════════════
@dp.callback_query(F.data == "trial")
async def cb_trial(cb: CallbackQuery):
    uid = cb.from_user.id
    u = await get_user(uid)
    if not u or u["trial_used"]:
        await cb.answer("🎁 Пробный день уже использован", show_alert=True)
        return
    if await user_has_trial_basic(uid):
        await cb.answer("У тебя уже есть активный BASIC", show_alert=True)
        return

    ok = await activate_tariff(uid, "basic", 1)
    if not ok:
        await cb.answer("Серверы недоступны, попробуй позже", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET trial_used=1 WHERE user_id=?", (uid,))
        await db.commit()

    url = sub_url("basic", uid)
    await cb.message.edit_text(
        "🎁 Пробный доступ активирован!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎫 Тариф: BASIC\n"
        "📅 Срок: 1 день\n\n"
        "🔗 Твоя ссылка:\n"
        f"{url}\n\n"
        "💡 Скопируй и вставь в v2rayNG / Streisand / Hiddify\n\n"
        f"{random_fact()}\n\n"
        "Понравится — жми Тарифы 🚀",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 В кабинет", callback_data="my")],
            [InlineKeyboardButton(text="🛒 Тарифы", callback_data="tariffs")],
        ]),
    )

    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"🎁 Пробный доступ выдан\n\n"
                f"👤 {cb.from_user.full_name} (@{cb.from_user.username or '—'})\n"
                f"🆔 {uid}\n\n"
                f"🎫 BASIC · 1 день\n💸 0 ₽",
            )
        except Exception:
            pass

# ══════════════════════════ USER: CABINET ══════════════════════════
@dp.callback_query(F.data == "my")
async def cb_my(cb: CallbackQuery):
    uid = cb.from_user.id
    await cleanup_expired(uid)
    subs = await get_user_subs(uid)

    if not subs:
        await cb.message.edit_text(
            "╭──────────────────────────────╮\n"
            "│      👤  ЛИЧНЫЙ КАБИНЕТ      │\n"
            "╰──────────────────────────────╯\n\n"
            "😴 У тебя пока нет активных подписок\n\n"
            f"{random_tip()}\n\n"
            "💡 Выбери тариф — и вперёд, к свободе!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 К тарифам", callback_data="tariffs")],
                [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
            ]),
        )
        return

    lines = [
        "╭──────────────────────────────╮",
        "│      👤  ЛИЧНЫЙ КАБИНЕТ      │",
        "╰──────────────────────────────╯",
        "",
        f"👋 {cb.from_user.first_name}",
        f"🆔 {uid}",
        "",
        f"📦 Активных подписок: {len(subs)}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    kb = []
    for s in subs:
        t = TARIFFS.get(s["tariff"])
        if not t:
            continue
        exp = parse_dt(s["expires_at"])
        now = datetime.now()
        if exp:
            left = max(0, (exp - now).days)
            total_sec = (exp - parse_dt(s["started_at"]) or now).total_seconds() or 1
            left_sec = (exp - now).total_seconds()
            pct = max(0, min(100, left_sec / total_sec * 100))
            bar = progress_bar(pct, 10)
            lines.append(
                f"\n{t['name']}  ·  {t['vibe']}\n"
                f"   {bar} {pct:.0f}%\n"
                f"   📅 осталось {left} дн. (до {fmt_dt(exp)})\n"
                f"   🌐 {s['server_alias'] or '—'}"
            )
        else:
            lines.append(
                f"\n{t['name']}  ·  {t['vibe']}\n"
                f"   ▓▓▓▓▓▓▓▓▓▓ 💎 бессрочно\n"
                f"   🌐 {s['server_alias'] or '—'}"
            )
        kb.append([InlineKeyboardButton(
            text=f"📂 {t['short']} · открыть",
            callback_data=f"sub:{s['tariff']}",
        )])

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 Нажми на тариф, чтобы увидеть ссылку")

    kb.append([InlineKeyboardButton(text="🛒 Купить ещё", callback_data="tariffs")])
    kb.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])

    await cb.message.edit_text("\n".join(lines),
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# ══════════════════════════ USER: SUB DETAIL ══════════════════════════
@dp.callback_query(F.data.startswith("sub:"))
async def cb_sub_detail(cb: CallbackQuery):
    key = cb.data.split(":")[1]
    uid = cb.from_user.id
    sub = await get_sub(uid, key)
    if not sub:
        await cb.answer("Подписка не найдена", show_alert=True)
        return

    t = TARIFFS[key]
    exp = parse_dt(sub["expires_at"])
    now = datetime.now()

    if exp:
        left = max(0, (exp - now).days)
        total_sec = (exp - parse_dt(sub["started_at"]) or now).total_seconds() or 1
        left_sec = (exp - now).total_seconds()
        pct = max(0, min(100, left_sec / total_sec * 100))
        bar = progress_bar(pct)
        status = "🟢 АКТИВНА" if pct > 20 else "🟡 ИСТЕКАЕТ"
        exp_line = fmt_dt(exp)
        left_line = f"{left} дн."
    else:
        bar = "▓" * 14
        pct = 100
        status = "💎 БЕССРОЧНАЯ"
        exp_line = "никогда"
        left_line = "∞"

    url = sub_url(key, uid)
    alias = sub["server_alias"] or server_alias(sub["server_link"] or "")

    text = (
        f"{t['name']}  ·  {t['vibe']}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"├ Статус:    {status}\n"
        f"├ Осталось:  {left_line}\n"
        f"├ Прогресс:  {bar} {pct:.0f}%\n"
        f"└ Истекает:  {exp_line}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 Сервер: {alias}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 ССЫЛКА ПОДПИСКИ\n\n"
        f"{url}\n\n"
        "💡 Скопируй и вставь в приложение\n"
        "(v2rayNG, Streisand, Hiddify, NekoBox)"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сменить сервер", callback_data=f"reroll:{key}")],
        [InlineKeyboardButton(text="🛒 Продлить", callback_data=f"buy:{key}")],
        [InlineKeyboardButton(text="⬅️ К кабинету", callback_data="my")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
    ])
    await cb.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("reroll:"))
async def cb_reroll(cb: CallbackQuery):
    key = cb.data.split(":")[1]
    uid = cb.from_user.id
    sub = await get_sub(uid, key)
    if not sub:
        await cb.answer("Подписка не найдена", show_alert=True)
        return
    link = await reroll_server(uid, key)
    if not link:
        await cb.answer("Серверов нет 😔", show_alert=True)
        return
    await cb.answer("🎲 Сервер переброшен!")
    cb.data = f"sub:{key}"
    await cb_sub_detail(cb)

# ══════════════════════════ ADMIN PANEL ══════════════════════════
@dp.callback_query(F.data == "admin")
async def cb_admin(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    await state.clear()
    await cb.message.edit_text(
        "⚙️ IXXY · Админ-панель\n\nУправляй вселенной 👇",
        reply_markup=admin_menu(),
    )

@dp.callback_query(F.data == "a_stats")
async def a_stats(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    s = await get_stats()
    lines = "\n".join(f"  • {TARIFFS[t]['name']}: {c}" for t, c in s["by_tariff"]) or "  —"
    conv = round(s["trial_converted"] / s["trials"] * 100) if s["trials"] else 0

    text = (
        "╭──────────────────────────────╮\n"
        "│      📊  СТАТИСТИКА IXXY     │\n"
        "╰──────────────────────────────╯\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  💰  ФИНАНСЫ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"├ Сегодня:    {fmt_price(s['revenue_today'])}\n"
        f"├ За 7 дней:  {fmt_price(s['revenue_week'])}\n"
        f"├ За 30 дней: {fmt_price(s['revenue_month'])}\n"
        f"├ Всего:      {fmt_price(s['revenue_all'])}\n"
        f"└ Средний чек: {fmt_price(s['avg_check'])}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  👥  ПОЛЬЗОВАТЕЛИ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"├ Всего:      {s['total']}\n"
        f"├ С подписками: {s['paying_users']}\n"
        f"├ Активных подписок: {s['active']}\n"
        f"├ Триалов:    {s['trials']}\n"
        f"└ Конверсия:  {conv}%\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "  🎫  ПО ТАРИФАМ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{lines}"
    )
    await cb.message.edit_text(text, reply_markup=admin_menu())

@dp.callback_query(F.data == "a_servers")
async def a_servers(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    text = "🔗 Серверы по тарифам\n\n"
    for k, t in TARIFFS.items():
        text += f"{t['name']} — {len(load_servers(k))} шт.\n"
    await cb.message.edit_text(text, reply_markup=admin_menu())

@dp.callback_query(F.data == "a_give")
async def a_give(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    await state.set_state(GiveFSM.user)
    await cb.message.edit_text(
        "👥 Выдача тарифа\n\n"
        "Отправь ID пользователя (или перешли его сообщение).\n\n"
        "Отмена — /cancel",
    )

@dp.message(GiveFSM.user)
async def give_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.forward_from:
        uid = message.forward_from.id
    else:
        try:
            uid = int(message.text.strip())
        except (ValueError, TypeError):
            await message.answer("❌ Нужен числовой ID.")
            return
    if not await get_user(uid):
        await upsert_user(uid, None, None)
    await state.update_data(user_id=uid)
    await state.set_state(GiveFSM.tariff)
    kb = [[InlineKeyboardButton(text=t["name"], callback_data=f"g_tariff:{k}")]
          for k, t in TARIFFS.items()]
    await message.answer(f"👤 Юзер: {uid}\n\n🎫 Какой тариф?",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(GiveFSM.tariff, F.data.startswith("g_tariff:"))
async def give_tariff(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    key = cb.data.split(":")[1]
    await state.update_data(tariff=key)
    await state.set_state(GiveFSM.days)
    await cb.message.edit_text(
        "📅 На какой срок?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="30 дн", callback_data="g_days:30"),
             InlineKeyboardButton(text="90 дн", callback_data="g_days:90")],
            [InlineKeyboardButton(text="180 дн", callback_data="g_days:180"),
             InlineKeyboardButton(text="365 дн", callback_data="g_days:365")],
            [InlineKeyboardButton(text="💎 Бессрочно", callback_data="g_days:0")],
        ]),
    )

@dp.callback_query(GiveFSM.days, F.data.startswith("g_days:"))
async def give_days_cb(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    await _finish_give(cb.from_user.id, state, int(cb.data.split(":")[1]))
    await cb.answer()

@dp.message(GiveFSM.days)
async def give_days_msg(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        days = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Нужно число.")
        return
    await _finish_give(message.from_user.id, state, days)

async def _finish_give(admin_id: int, state: FSMContext, days: int):
    data = await state.get_data()
    uid, key = data["user_id"], data["tariff"]
    await state.clear()
    ok = await activate_tariff(uid, key, days)
    if not ok:
        await bot.send_message(admin_id, f"❌ Нет серверов для {key}", reply_markup=admin_menu())
        return
    url = sub_url(key, uid)
    try:
        await bot.send_message(
            uid,
            f"🎁 Тебе выдан тариф!\n\n"
            f"🎫 {TARIFFS[key]['name']}\n"
            f"📅 {days if days else 'бессрочно'}\n\n"
            f"🔗 {url}",
        )
    except Exception:
        pass
    await bot.send_message(
        admin_id,
        f"✅ Выдано {uid} — {TARIFFS[key]['name']} · {days or '∞'} дн.",
        reply_markup=admin_menu(),
    )

@dp.callback_query(F.data.startswith("approve:"))
async def cb_approve(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    tid = int(cb.data.split(":")[1])
    t = await get_ticket(tid)
    if not t or t["status"] != "pending":
        await cb.answer("Уже обработано", show_alert=True)
        return
    ok = await activate_tariff(t["user_id"], t["tariff"], t["days"])
    if not ok:
        await cb.answer("Нет серверов этого тарифа", show_alert=True)
        return
    await close_ticket(tid, "approved")
    url = sub_url(t["tariff"], t["user_id"])
    try:
        await bot.send_message(
            t["user_id"],
            f"🎉 Оплата подтверждена!\n\n"
            f"🎫 {TARIFFS[t['tariff']]['name']}\n"
            f"📅 {t['days']} дн.\n\n"
            f"🔗 Твоя подписка:\n{url}",
        )
    except Exception:
        pass
    await cb.message.edit_text((cb.message.text or "") + "\n\n✅ Активировано")

    for aid in ADMIN_IDS:
        if aid == cb.from_user.id:
            continue
        try:
            await bot.send_message(
                aid,
                f"💰 +{fmt_price(t['amount'])}\n\n"
                f"👤 {t['user_id']}\n"
                f"🎫 {TARIFFS[t['tariff']]['name']} · {t['days']} дн.\n"
                f"🧾 Заявка #{tid}",
            )
        except Exception:
            pass

@dp.callback_query(F.data.startswith("reject:"))
async def cb_reject(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    tid = int(cb.data.split(":")[1])
    t = await get_ticket(tid)
    if not t or t["status"] != "pending":
        await cb.answer("Уже обработано", show_alert=True)
        return
    await close_ticket(tid, "rejected")
    try:
        await bot.send_message(t["user_id"], "❌ Заявка отклонена. Обратись к админу.")
    except Exception:
        pass
    await cb.message.edit_text((cb.message.text or "") + "\n\n❌ Отклонено")

@dp.callback_query(F.data == "a_revoke")
async def a_revoke(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    await state.set_state(RevokeFSM.user)
    await cb.message.edit_text("Отправь ID для снятия тарифов. Отмена — /cancel")

@dp.message(RevokeFSM.user)
async def revoke_user_step(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except (ValueError, TypeError):
        await message.answer("❌ Числовой ID нужен.")
        return
    await state.update_data(user_id=uid)
    await state.set_state(RevokeFSM.tariff)
    kb = [[InlineKeyboardButton(text=t["name"], callback_data=f"r_tariff:{k}")]
          for k, t in TARIFFS.items()]
    kb.append([InlineKeyboardButton(text="🗑 Снять ВСЕ", callback_data="r_tariff:__all__")])
    await message.answer(
        f"👤 Юзер: {uid}\n\nЧто снять?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )

@dp.callback_query(RevokeFSM.tariff, F.data.startswith("r_tariff:"))
async def revoke_tariff_step(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    val = cb.data.split(":")[1]
    data = await state.get_data()
    uid = data["user_id"]
    await state.clear()

    if val == "__all__":
        removed = await revoke_tariff(uid)
        txt = f"✅ Снято всё с {uid}: {', '.join(removed) or '—'}"
        user_msg = "⚠️ Все твои тарифы отозваны администратором."
    else:
        removed = await revoke_tariff(uid, val)
        txt = f"✅ Снят {TARIFFS[val]['name']} с {uid}" if removed else "Нечего снимать"
        user_msg = f"⚠️ Твой тариф {TARIFFS[val]['name']} отозван администратором."

    await cb.message.edit_text(txt, reply_markup=admin_menu())
    try:
        await bot.send_message(uid, user_msg)
    except Exception:
        pass

@dp.callback_query(F.data == "a_broadcast")
async def a_broadcast(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    await state.set_state(BroadcastFSM.text)
    await cb.message.edit_text("📢 Отправь сообщение для рассылки. Отмена — /cancel")

@dp.message(BroadcastFSM.text)
async def broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    users = await all_users()
    ok = fail = 0
    for u in users:
        try:
            await message.copy_to(u["user_id"])
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await message.answer(
        f"📢 Рассылка завершена\n\n✅ {ok}\n❌ {fail}",
        reply_markup=admin_menu(),
    )

# ══════════════════════════ WEBHOOK ══════════════════════════
api = FastAPI()

@api.get("/")
async def root():
    return {"status": "ixxy", "ok": True}

@api.post("/webhook/cashera")
async def cashera_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(400, "invalid json")

    log.info(f"💳 CasheRa webhook: {data}")

    status = str(
        data.get("status") or data.get("state") or data.get("payment_status") or ""
    ).lower()
    payment_uuid = (
        data.get("uuid") or data.get("transaction_id") or data.get("id")
    )

    if status not in ("success", "paid", "completed", "succeeded", "approved"):
        return {"ok": True, "ignored": status}

    if not payment_uuid:
        raise HTTPException(400, "no uuid")

    pending = await pop_pending(str(payment_uuid))
    if not pending:
        log.warning(f"pending not found: {payment_uuid}")
        return {"ok": True, "unknown": True}

    user_id = pending["user_id"]
    tariff = pending["tariff"]
    days = pending["days"]
    amount = pending["amount"]

    ok = await activate_tariff(user_id, tariff, days)
    if not ok:
        log.error(f"activate failed for {user_id}")
        return {"ok": False}

    url = sub_url(tariff, user_id)

    try:
        await bot.send_message(
            user_id,
            f"🎉 Оплата прошла!\n\n"
            f"🎫 {TARIFFS[tariff]['name']} · {days} дн.\n\n"
            f"🔗 {url}\n\n"
            f"Вставь в v2rayNG / Streisand / Hiddify",
        )
    except Exception as e:
        log.error(f"notify user failed: {e}")

    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"💰 НОВАЯ ОПЛАТА\n\n"
                f"👤 {user_id}\n"
                f"🎫 {TARIFFS[tariff]['name']} · {days} дн.\n"
                f"💵 +{fmt_price(amount)}",
            )
        except Exception:
            pass

    return {"ok": True}

# ══════════════════════════ ENTRY ══════════════════════════
async def run_bot():
    await init_db()
    log.info("🚀 IXXY bot polling started")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def run_web():
    config = uvicorn.Config(api, host="0.0.0.0", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    log.info(f"🌐 Webhook server on :{PORT}")
    await server.serve()

async def main():
    if not BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN не установлен в .env")
    if not ADMIN_IDS:
        raise SystemExit("❌ ADMIN_IDS пуст в .env")
    await asyncio.gather(run_bot(), run_web())

if __name__ == "__main__":
    asyncio.run(main())