import asyncio

from services.ai_core import generate_quiz_payload
from services.filters import is_article_good
from services.quiz_payload import payload_to_json_str
from services.wiki_api import (
    get_title,
    get_page,
    get_latest_quiz,
    insert_quiz,
)


async def pick_good_article(max_attempts: int = 25):
    last_error = None
    for _ in range(max_attempts):
        try:
            title = await get_title()
            page = await get_page(title)
            if is_article_good(title, page):
                return title, page
        except Exception as e:
            last_error = e
        await asyncio.sleep(0.6)
    msg = "Не вдалося підібрати підходящу статтю з Вікіпедії."
    if last_error:
        raise RuntimeError(msg) from last_error
    raise RuntimeError(msg)


async def create_new_quiz():
    title, page = await pick_good_article()
    payload = await generate_quiz_payload(page, title)
    quiz_json = payload_to_json_str(payload)
    quiz_id = await insert_quiz(title, page, quiz_json)
    return {
        "quiz_id": quiz_id,
        "title": title,
        "page": page,
        "quiz": quiz_json,
        "payload": payload,
    }
