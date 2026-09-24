import os
import logging
from datetime import datetime, timezone
from typing import Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
PUBLIC_SITE_URL = os.getenv(
    "PUBLIC_SITE_URL",
    "https://ixxysubscription.onrender.com",
).rstrip("/")
SUBSCRIPTION_PREFIX = os.getenv(
    "SUBSCRIPTION_PREFIX",
    "2ix847xy",
).strip()
TARIFFS = {
    "basic": {
        "name": "Basic",
        "rub": 415,
        "stars": 309,
    },
    "mobile": {
        "name": "Mobile",
        "rub": 743,
        "stars": 637,
    },
    "supra": {
        "name": "Supra",
        "rub": 1351,
        "stars": 1245,
    },
}
def connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL не установлен.")
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        connect_timeout=15,
    )
def init_db():
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    subscription BOOLEAN NOT NULL DEFAULT FALSE,
                    tariff TEXT,
                    subscription_link TEXT,
                    accepted_terms BOOLEAN NOT NULL DEFAULT FALSE,
                    notify BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    payment_id TEXT,
                    external_id TEXT,
                    amount INTEGER NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL DEFAULT 'RUB',
                    tariff TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    provider TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    paid_at TIMESTAMPTZ
                )
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                payments_payment_id_unique
                ON payments(payment_id)
                WHERE payment_id IS NOT NULL
            """)
            conn.commit()
def get_subscription_link(user_id: int) -> str:
    return (
        f"{PUBLIC_SITE_URL}/sub/"
        f"{SUBSCRIPTION_PREFIX}{int(user_id)}"
    )
def create_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
):
    link = get_subscription_link(user_id)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (
                    user_id,
                    username,
                    first_name,
                    subscription_link
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    subscription_link = EXCLUDED.subscription_link
            """, (
                int(user_id),
                username,
                first_name,
                link,
            ))
            conn.commit()
def get_user(user_id: int) -> Optional[dict]:
    with connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT *
                FROM users
                WHERE user_id = %s
            """, (int(user_id),))
            row = cur.fetchone()
            return dict(row) if row else None
def get_all_users():
    with connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT *
                FROM users
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cur.fetchall()]
def search_users(query: str):
    query = query.strip()
    with connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if query.startswith("@"):
                query = query[1:]
            if query.isdigit():
                cur.execute("""
                    SELECT *
                    FROM users
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (int(query),))
            else:
                like = f"%{query}%"
                cur.execute("""
                    SELECT *
                    FROM users
                    WHERE
                        username ILIKE %s
                        OR first_name ILIKE %s
                    ORDER BY created_at DESC
                """, (like, like))
            return [dict(row) for row in cur.fetchall()]
def activate_tariff(user_id: int, tariff: str):
    tariff = tariff.lower().strip()
    if tariff not in TARIFFS:
        raise ValueError("Неизвестный тариф.")
    link = get_subscription_link(user_id)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET
                    subscription = TRUE,
                    tariff = %s,
                    subscription_link = %s
                WHERE user_id = %s
            """, (
                tariff,
                link,
                int(user_id),
            ))
            conn.commit()
def disable_subscription(user_id: int):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET
                    subscription = FALSE,
                    tariff = NULL
                WHERE user_id = %s
            """, (int(user_id),))
            conn.commit()
def set_accepted_terms(user_id: int, value: bool = True):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET accepted_terms = %s
                WHERE user_id = %s
            """, (bool(value), int(user_id)))
            conn.commit()
def create_payment(
    user_id: int,
    payment_id: Optional[str],
    external_id: Optional[str],
    amount: int,
    currency: str,
    tariff: str,
    provider: str,
):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO payments (
                    user_id,
                    payment_id,
                    external_id,
                    amount,
                    currency,
                    tariff,
                    status,
                    provider
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, 'pending', %s
                )
                RETURNING id
            """, (
                int(user_id),
                payment_id,
                external_id,
                int(amount),
                currency,
                tariff,
                provider,
            ))
            payment_db_id = cur.fetchone()[0]
            conn.commit()
            return payment_db_id
def payment_exists(
    payment_id: Optional[str] = None,
    external_id: Optional[str] = None,
) -> bool:
    if not payment_id and not external_id:
        return False
    with connect() as conn:
        with conn.cursor() as cur:
            if payment_id:
                cur.execute("""
                    SELECT 1
                    FROM payments
                    WHERE payment_id = %s
                    LIMIT 1
                """, (str(payment_id),))
            else:
                cur.execute("""
                    SELECT 1
                    FROM payments
                    WHERE external_id = %s
                    LIMIT 1
                """, (str(external_id),))
            return cur.fetchone() is not None
def mark_payment_paid(
    payment_id: Optional[str] = None,
    external_id: Optional[str] = None,
):
    with connect() as conn:
        with conn.cursor() as cur:
            if payment_id:
                cur.execute("""
                    UPDATE payments
                    SET
                        status = 'paid',
                        paid_at = NOW()
                    WHERE payment_id = %s
                    RETURNING user_id, tariff
                """, (str(payment_id),))
            else:
                cur.execute("""
                    UPDATE payments
                    SET
                        status = 'paid',
                        paid_at = NOW()
                    WHERE external_id = %s
                    RETURNING user_id, tariff
                """, (str(external_id),))
            row = cur.fetchone()
            conn.commit()
            if not row:
                return None
            return {
                "user_id": row[0],
                "tariff": row[1],
            }
def get_all_payments():
    with connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT *
                FROM payments
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cur.fetchall()]
def get_stats() -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM users
            """)
            total_users = cur.fetchone()[0]
            cur.execute("""
                SELECT COUNT(*)
                FROM users
                WHERE subscription = TRUE
            """)
            active_users = cur.fetchone()[0]
            cur.execute("""
                SELECT COUNT(*)
                FROM payments
                WHERE status = 'paid'
            """)
            paid_payments = cur.fetchone()[0]
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM payments
                WHERE status = 'paid'
                  AND currency = 'RUB'
            """)
            revenue_rub = cur.fetchone()[0]
            return {
                "total_users": total_users,
                "active_users": active_users,
                "paid_payments": paid_payments,
                "revenue_rub": revenue_rub,
            }
def get_users_by_tariff(tariff: str):
    with connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT *
                FROM users
                WHERE subscription = TRUE
                  AND tariff = %s
                ORDER BY created_at DESC
            """, (tariff,))
            return [dict(row) for row in cur.fetchall()]
def user_has_subscription(user_id: int) -> bool:
    user = get_user(user_id)
    if not user:
        return False
    return bool(
        user.get("subscription")
        and user.get("tariff") in TARIFFS
    )
# Запускаем создание таблиц при импорте.
init_db()