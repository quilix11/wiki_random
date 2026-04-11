from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

import aiosqlite
import httpx

from database.database import DB_PATH, init_db

_RANDOM_URL = (
    "https://uk.wikipedia.org/w/api.php"
    "?action=query&format=json&list=random&rnlimit=1&rnnamespace=0"
)
_HEADERS = {"User-Agent": "WikiQuizApp/1.0 (test_developer@gmail.com)"}
_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _db_path() -> Path:
    return Path(DB_PATH)


@asynccontextmanager
async def _db_conn():
    init_db()
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        yield db


async def get_title() -> str:
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=_HTTP_TIMEOUT
    ) as client:
        response = await client.get(_RANDOM_URL, headers=_HEADERS)
        response.raise_for_status()
        data = response.json()
        return data["query"]["random"][0]["title"]


async def get_page(title: str) -> str:
    safe = quote(title, safe="")
    url = (
        "https://uk.wikipedia.org/w/api.php?action=query&prop=extracts"
        f"&explaintext&titles={safe}&format=json"
    )
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=_HTTP_TIMEOUT
    ) as client:
        response = await client.get(url, headers=_HEADERS)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return ""
        first_page = next(iter(pages.values()))
        if first_page.get("missing"):
            return ""
        return first_page.get("extract") or ""


async def get_latest_quiz():
    async with _db_conn() as db:
        async with db.execute(
            """
            SELECT id, title, page_text, quiz_text
            FROM quizzes
            ORDER BY id DESC
            LIMIT 1
            """
        ) as cursor:
            row = await cursor.fetchone()
    if not row:
        return None
    return {
        "quiz_id": row[0],
        "title": row[1],
        "page": row[2],
        "quiz": row[3],
    }


async def insert_quiz(title: str, page_text: str, quiz_text: str) -> int:
    async with _db_conn() as db:
        cursor = await db.execute(
            """
            INSERT INTO quizzes (title, page_text, quiz_text)
            VALUES (?, ?, ?)
            """,
            (title, page_text, quiz_text),
        )
        await db.commit()
        return cursor.lastrowid


async def save_attempt(quiz_id: int, user_id: int, score: int) -> None:
    async with _db_conn() as db:
        await db.execute(
            """
            INSERT INTO attempts (quiz_id, user_id, score)
            VALUES (?, ?, ?)
            """,
            (quiz_id, user_id, score),
        )
        await db.commit()


async def get_global_stats():
    async with _db_conn() as db:
        async with db.execute(
            """
            SELECT COUNT(DISTINCT user_id) as total_users,
                   COUNT(*) as total_attempts,
                   AVG(score) as avg_score
            FROM attempts
            """
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] == 0:
                return None
            return {
                "total_users": row[0],
                "total_attempts": row[1],
                "avg_score": round(row[2], 2),
            }


async def get_user_stats(user_id: int):
    async with _db_conn() as db:
        async with db.execute(
            """
            SELECT COUNT(*) as total_attempts,
                   SUM(score) as total_score,
                   AVG(score) as avg_score
            FROM attempts
            WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] == 0:
                return None
            return {
                "total_attempts": row[0],
                "total_score": row[1],
                "avg_score": round(row[2], 2),
            }


async def get_top_users(limit: int = 10):
    async with _db_conn() as db:
        async with db.execute(
            """
            SELECT user_id, SUM(score) as total_score, COUNT(*) as attempts
            FROM attempts
            GROUP BY user_id
            ORDER BY total_score DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"user_id": r[0], "total_score": r[1], "attempts": r[2]} for r in rows]
