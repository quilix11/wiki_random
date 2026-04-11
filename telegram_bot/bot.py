import asyncio
import html
import logging
import os
import sys
from typing import List, Optional, Set
from urllib.parse import quote

from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from services.quiz_payload import parse_stored_quiz
from services.quiz_service import create_new_quiz
from services.wiki_api import get_title, save_attempt, get_global_stats, get_top_users, get_user_stats

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_ADMIN_IDS_RAW = os.getenv("TELEGRAM_ADMIN_IDS", "")

BTN_OPT_MAX = 56
PAGE_SIZE = 1200


storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(token=BOT_TOKEN or "")

menu_main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎮 Грати")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="❓ Допомога")],
    ],
    resize_keyboard=True,
)

menu_in_round = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Змінити статтю")],
        [KeyboardButton(text="📝 Показати питання")],
        [KeyboardButton(text="🏠 Головне меню")],
    ],
    resize_keyboard=True,
)


class QuizStates(StatesGroup):
    reading = State()
    answering = State()


def _admin_ids() -> Set[int]:
    out: Set[int] = set()
    for part in TELEGRAM_ADMIN_IDS_RAW.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def _is_admin(user_id: Optional[int]) -> bool:
    if user_id is None:
        return False
    admins = _admin_ids()
    return user_id in admins if admins else False


def _wiki_url(title: str) -> str:
    t = title.replace(" ", "_")
    return "https://uk.wikipedia.org/wiki/" + quote(t, safe="()%")


def _split_into_pages(text: str, size: int) -> List[str]:
    import re
    # Очищуємо текст
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    
    pages = []
    while len(text) > 0:
        if len(text) <= size:
            pages.append(text)
            break
        
        # Шукаємо останній перенос рядка в межах розміру
        pos = text.rfind('\n', 0, size)
        if pos == -1:
            pos = text.rfind('. ', 0, size)
        if pos == -1:
            pos = size
            
        pages.append(text[:pos].strip())
        text = text[pos:].strip()
    return pages


def _get_article_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    if current_page > 0:
        row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{current_page-1}"))
    
    row.append(InlineKeyboardButton(text=f"📄 {current_page+1}/{total_pages}", callback_data="ignore"))
    
    if current_page < total_pages - 1:
        row.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page:{current_page+1}"))
    
    buttons.append(row)
    buttons.append([InlineKeyboardButton(text="✅ Прочитав, до питань!", callback_data="start_quiz")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _excerpt_article_html(title: str, content: str, current_page: int, total_pages: int) -> str:
    link = _wiki_url(title)
    return (
        f"📖 <b>{html.escape(title)}</b>\n\n"
        f"{html.escape(content)}\n\n"
        f"🔗 <a href='{html.escape(link)}'>Читати повністю на Вікіпедії</a>"
    )


def _btn_label(option_text: str, letter: str) -> str:
    short = option_text.strip()
    if len(short) > BTN_OPT_MAX:
        short = short[: BTN_OPT_MAX - 1] + "…"
    return f"{letter}. {short}"


def _letters() -> List[str]:
    return ["А", "Б", "В", "Г"]


def _question_keyboard(quiz_id: int, q_index: int, options: List[str]) -> InlineKeyboardMarkup:
    letters = _letters()
    rows: List[List[InlineKeyboardButton]] = []
    for row_start in (0, 2):
        row: List[InlineKeyboardButton] = []
        for i in range(row_start, min(row_start + 2, 4)):
            cb = f"q:{quiz_id}:{q_index}:{i}"
            row.append(
                InlineKeyboardButton(
                    text=_btn_label(options[i], letters[i]),
                    callback_data=cb,
                )
            )
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _reply_menu(state: FSMContext) -> ReplyKeyboardMarkup:
    current_state = await state.get_state()
    if current_state in [QuizStates.reading.state, QuizStates.answering.state]:
        return menu_in_round
    return menu_main


BOT_TITLE = "Вікі-Вікторина 🇺🇦"
BOT_DESCRIPTION = (
    "Вікторина за випадковими статтями української Вікіпедії. Кожна стаття — нові питання!"
)
BOT_SHORT_DESCRIPTION = "Вікторина з Вікіпедії: питання з варіантами."

WELCOME_HTML = (
    f"<b>{html.escape(BOT_TITLE)}</b>\n\n"
    "Тут ти можеш перевірити свої знання, граючи у вікторину за випадковими статтями Вікіпедії. 🧠\n\n"
    "Натисни <b>«🎮 Грати»</b> — я підберу цікаву статтю й створю питання.\n"
    "Ти можеш змінити статтю в будь-який момент, якщо вона тобі не подобається. 🔄"
)

HELP_HTML = (
    f"<b>Довідка — {html.escape(BOT_TITLE)}</b>\n\n"
    "<b>Як грати:</b>\n"
    "1) Натисни <b>«🎮 Грати»</b> або /play — я знайду статтю й згенерую 3 питання.\n"
    "2) Читай статтю (можна гортати сторінки ⬅️ ➡️) та натискай <b>«✅ Прочитав»</b>.\n"
    "3) Відповідай на питання за допомогою кнопок під повідомленням. 📝\n"
    "4) <b>«🔄 Змінити статтю»</b> — отримати нову тему.\n"
    "5) <b>«📊 Статистика»</b> — твої успіхи та загальний рейтинг. 🏆\n\n"
    "<b>Команди:</b>\n"
    "/start — головне меню\n"
    "/play — нова гра\n"
    "/stats — статистика\n"
    "/help — ця довідка"
)

OLD_QUIZ_HTML = (
    "Цей раунд у базі у старому форматі (без кнопок). "
    "Попроси адміна виконати <code>/next_quiz</code>, щоб оновити питання для всіх."
)


async def _configure_bot_profile() -> None:
    try:
        await bot.set_my_description(description=BOT_DESCRIPTION, language_code="uk")
        await bot.set_my_short_description(
            short_description=BOT_SHORT_DESCRIPTION,
            language_code="uk",
        )
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="🏠 Головне меню"),
                BotCommand(command="play", description="🎮 Нова гра"),
                BotCommand(command="stats", description="📊 Статистика"),
                BotCommand(command="help", description="❓ Допомога"),
            ],
            language_code="uk",
        )
    except Exception:
        logger.exception("set_my_description / set_my_commands")


async def _send_question(bot: Bot, chat_id: int, state: FSMContext) -> None:
    data = await state.get_data()
    quiz_id = data.get("quiz_id")
    questions = data.get("questions")
    q_index = data.get("q_index", 0)
    if quiz_id is None or not questions or q_index >= len(questions):
        await bot.send_message(
            chat_id,
            "❌ Не вдалося знайти питання. Натисни «Грати».",
            reply_markup=menu_main,
        )
        await state.clear()
        return

    q = questions[q_index]
    opts = q["options"]
    letters = _letters()
    
    header = f"<b>❓ Питання {q_index + 1} з 3</b>"
    question_text = f"<blockquote>{html.escape(q['text'])}</blockquote>"
    
    options_lines = []
    for i, o in enumerate(opts):
        options_lines.append(f"<b>{letters[i]}</b>. {html.escape(o)}")
    
    text = f"{header}\n\n{question_text}\n\n" + "\n".join(options_lines)

    await bot.send_message(
        chat_id,
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=_question_keyboard(int(quiz_id), q_index, opts),
    )


async def _begin_round(message: Message, state: FSMContext, session: dict) -> None:
    payload = parse_stored_quiz(session.get("quiz"))
    if not payload:
        await message.answer(
            "Помилка формату питань. Спробуй іншу статтю.",
            reply_markup=await _reply_menu(state),
        )
        return

    pages = _split_into_pages(session.get("page", ""), PAGE_SIZE)
    if not pages:
        await message.answer("Стаття порожня. Спробуй іншу.")
        return

    await state.set_state(QuizStates.reading)
    await state.update_data(
        quiz_id=session["quiz_id"],
        title=session.get("title", ""),
        questions=payload["questions"],
        pages=pages,
        current_page=0,
        q_index=0,
        picks=[],
    )

    await message.answer(
        _excerpt_article_html(session["title"], pages[0], 0, len(pages)),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=_get_article_keyboard(0, len(pages)),
    )


@dp.callback_query(F.data.startswith("page:"))
async def on_page_switch(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if await state.get_state() != QuizStates.reading.state:
        await callback.answer()
        return

    page_idx = int(callback.data.split(":")[1])
    pages = data.get("pages", [])
    title = data.get("title", "")

    if 0 <= page_idx < len(pages):
        await state.update_data(current_page=page_idx)
        await callback.message.edit_text(
            _excerpt_article_html(title, pages[page_idx], page_idx, len(pages)),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=_get_article_keyboard(page_idx, len(pages)),
        )
    await callback.answer()


@dp.callback_query(F.data == "start_quiz")
async def on_start_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    if await state.get_state() != QuizStates.reading.state:
        await callback.answer()
        return

    await state.set_state(QuizStates.answering)
    await callback.message.edit_reply_markup(reply_markup=None)
    await _send_question(callback.bot, callback.message.chat.id, state)
    await callback.answer()


async def _run_play(message: Message, state: FSMContext) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    try:
        session = await create_new_quiz()
    except Exception:
        logger.exception("create_new_quiz")
        await message.answer(
            "Не вдалося знайти статтю (проблеми зі зв'язком). Спробуй ще раз.",
            reply_markup=await _reply_menu(state),
        )
        return

    await _begin_round(message, state, session)


async def _finish_round(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    questions: list,
    picks: List[int],
    quiz_id: int,
    user_id: int,
) -> None:
    correct_idx = [q["correct"] for q in questions]
    score = sum(1 for i, p in enumerate(picks) if p == correct_idx[i])

    result_emoji = "🏆" if score == 3 else "🥈" if score == 2 else "🥉" if score == 1 else "😅"
    
    lines = [
        f"{result_emoji} <b>Вікторину завершено!</b>",
        f"Твій результат: <b>{score} з 3</b>\n",
    ]
    letters = _letters()
    for i, q in enumerate(questions):
        ok = picks[i] == correct_idx[i]
        mark = "✅" if ok else "❌"
        chosen = picks[i]
        right = correct_idx[i]
        
        lines.append(f"{mark} <b>Питання {i + 1}</b>")
        lines.append(f"   Твій вибір: {letters[chosen]}. {html.escape(q['options'][chosen])}")
        if not ok:
            lines.append(f"   Правильно: {letters[right]}. {html.escape(q['options'][right])}")
        lines.append("")

    await bot.send_message(
        chat_id,
        "\n".join(lines).strip(),
        parse_mode=ParseMode.HTML,
        reply_markup=menu_main,
    )

    try:
        await save_attempt(quiz_id, user_id, score)
    except Exception:
        logger.exception("save_attempt")

    await state.clear()


@dp.callback_query(F.data.startswith("q:"))
async def on_answer_pick(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data or not callback.message:
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) != 4 or parts[0] != "q":
        await callback.answer()
        return
    try:
        qid = int(parts[1])
        qi = int(parts[2])
        opt = int(parts[3])
    except ValueError:
        await callback.answer()
        return

    data = await state.get_data()
    if await state.get_state() != QuizStates.answering.state:
        await callback.answer("Гра вже неактивна.", show_alert=True)
        return

    st_qid = data.get("quiz_id")
    questions = data.get("questions")
    q_index = data.get("q_index", 0)

    if st_qid != qid or not questions:
        await callback.answer("Це питання вже застаріло.", show_alert=True)
        return

    if qi != q_index:
        await callback.answer("Це вже не актуальне питання.", show_alert=True)
        return

    await callback.answer()

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    picks: List[int] = list(data.get("picks") or [])
    picks.append(opt)

    if len(picks) < 3:
        await state.update_data(q_index=q_index + 1, picks=picks)
        await _send_question(callback.bot, callback.message.chat.id, state)
        return

    uid = callback.from_user.id if callback.from_user else 0
    await _finish_round(
        callback.bot,
        callback.message.chat.id,
        state,
        questions,
        picks,
        int(st_qid),
        uid,
    )


@dp.message(Command("start"))
async def start_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        WELCOME_HTML,
        parse_mode=ParseMode.HTML,
        reply_markup=menu_main,
    )


@dp.message(Command("help"))
@dp.message(F.text == "❓ Допомога")
async def help_command(message: Message, state: FSMContext) -> None:
    await message.answer(
        HELP_HTML,
        parse_mode=ParseMode.HTML,
        reply_markup=await _reply_menu(state),
    )


@dp.message(Command("stats"))
@dp.message(F.text == "📊 Статистика")
async def stats_command(message: Message) -> None:
    user_id = message.from_user.id
    u_stats = await get_user_stats(user_id)
    g_stats = await get_global_stats()
    
    lines = ["👤 <b>Твоя статистика:</b>"]
    if u_stats:
        lines.append(f"🎮 Ігор зіграно: {u_stats['total_attempts']}")
        lines.append(f"🏆 Всього балів: {u_stats['total_score']}")
        lines.append(f"📈 Сер. бал: {u_stats['avg_score']} з 3")
    else:
        lines.append("Ти ще не зіграв жодної гри. Пора починати!")
    
    lines.append("")
    lines.append("📊 <b>Загальна статистика:</b>")
    if g_stats:
        lines.append(f"👥 Гравців: {g_stats['total_users']}")
        lines.append(f"📝 Раундів зіграно: {g_stats['total_attempts']}")
        lines.append(f"📈 Сер. бал: {g_stats['avg_score']} з 3")
        
        top = await get_top_users(5)
        if top:
            lines.append("")
            lines.append("🏆 <b>Топ гравців:</b>")
            for i, user in enumerate(top):
                name = f"<code>ID:{user['user_id']}</code>"
                lines.append(f"{i+1}. {name} — {user['total_score']} балів ({user['attempts']} ігор)")
    else:
        lines.append("Поки що загальної статистики немає.")
        
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)


@dp.message(F.text == "🏠 Головне меню")
async def main_menu_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        WELCOME_HTML,
        parse_mode=ParseMode.HTML,
        reply_markup=menu_main,
    )


@dp.message(Command("play"))
@dp.message(F.text == "🎮 Грати")
@dp.message(F.text == "🔄 Змінити статтю")
async def play_entry(message: Message, state: FSMContext) -> None:
    await _run_play(message, state)


@dp.message(Command("answers"))
@dp.message(F.text == "📝 Показати питання")
async def show_current_question(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state == QuizStates.reading.state:
        await message.answer("Спочатку дочитай статтю та натисни «✅ Прочитав, до питань!»")
        return
        
    if current_state != QuizStates.answering.state:
        await message.answer(
            "Спочатку натисни «🎮 Грати».",
            parse_mode=ParseMode.HTML,
            reply_markup=menu_main,
        )
        return
    await _send_question(message.bot, message.chat.id, state)


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Задай TELEGRAM_TOKEN у .env")
    await _configure_bot_profile()
    await dp.start_polling(bot)


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise SystemExit("Потрібен TELEGRAM_TOKEN у .env")
    asyncio.run(main())
