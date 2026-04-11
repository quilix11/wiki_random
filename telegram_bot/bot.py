import os
import re
import sys
from dotenv import load_dotenv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from services.wiki_api import get_title, get_page, save_score
from services.ai_core import get_content, get_answers

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(token=BOT_TOKEN)

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Почати гру")],
        [KeyboardButton(text="Відповісти"), KeyboardButton(text="Показати питання")],
        [KeyboardButton(text="Закінчити гру")],
    ],
    resize_keyboard=True,
)

class QuizStates(StatesGroup):
    waiting_answer = State()

async def main():
    await dp.start_polling(bot)

@dp.message(Command(commands=["start"]))
async def start_command(message: Message):
    await message.answer(
        "Привіт! Це вікторина з Вікіпедії.\n"
        "Натисни кнопку нижче, щоб почати.",
        reply_markup=menu,
    )

@dp.message(lambda message: message.text == "Головне меню")
async def start_menu_command(message: Message):
    await message.answer(
        "Привіт! Це вікторина з Вікіпедії.\n"
        "Натисни кнопку нижче, щоб почати.",
        reply_markup=menu,
    )

@dp.message(Command(commands=["play"]))
async def play_command(message: Message, state: FSMContext):
    await message.answer("Завантажую статтю й готую питання...", reply_markup=ReplyKeyboardRemove())
    title = await get_title()
    page = await get_page(title)
    quiz = await get_content(page)
    await state.update_data(page=page, quiz=quiz, title=title)
    await message.answer(f"Ось стаття для всіх: {title}", reply_markup=menu)
    await message.answer("Ось питання для вікторини:")
    await message.answer(quiz)

@dp.message(lambda message: message.text == "Почати гру")
async def play_menu_command(message: Message, state: FSMContext):
    await message.answer("Завантажую статтю й готую питання...", reply_markup=ReplyKeyboardRemove())
    title = await get_title()
    page = await get_page(title)
    quiz = await get_content(page)
    await state.update_data(page=page, quiz=quiz, title=title)
    await message.answer(f"Ось стаття для всіх: {title}", reply_markup=menu)
    await message.answer("Ось питання для вікторини:")
    await message.answer(quiz)

@dp.message(Command(commands=["you_answer"]))
async def answer_command(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("quiz"):
        await message.answer("Спочатку натисни Почати гру.", reply_markup=menu)
        return
    await message.answer(
        "Напиши свої відповіді у чат просто текстом.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(QuizStates.waiting_answer)

@dp.message(lambda message: message.text == "Відповісти")
async def answer_menu_command(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("quiz"):
        await message.answer("Спочатку натисни Почати гру.", reply_markup=menu)
        return
    await message.answer(
        "Напиши свої відповіді у чат просто текстом.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(QuizStates.waiting_answer)

@dp.message(StateFilter(QuizStates.waiting_answer))
async def answer_input(message: Message, state: FSMContext):
    data = await state.get_data()
    page = data.get("page")
    quiz = data.get("quiz")
    title = data.get("title")
    if not page or not quiz or not title:
        await message.answer("Статус гри зник. Почни заново.", reply_markup=menu)
        await state.clear()
        return
    result = await get_answers(page, quiz, message.text)
    await message.answer("Ось результат перевірки:", reply_markup=menu)
    await message.answer(result)
    match = re.search(r"\[ОЦІНКА:\s*(\d+)/3\]", result)
    if match:
        score = int(match.group(1))
        await save_score(title, score)
    await state.clear()

@dp.message(Command(commands=["answers"]))
async def show_quiz(message: Message, state: FSMContext):
    data = await state.get_data()
    quiz = data.get("quiz")
    if not quiz:
        await message.answer("Гра ще не почалась. Натисни Почати гру.", reply_markup=menu)
        return
    await message.answer("Запитання ще раз:", reply_markup=menu)
    await message.answer(quiz)

@dp.message(lambda message: message.text == "Показати питання")
async def show_quiz_menu_command(message: Message, state: FSMContext):
    data = await state.get_data()
    quiz = data.get("quiz")
    if not quiz:
        await message.answer("Гра ще не почалась. Натисни Почати гру.", reply_markup=menu)
        return
    await message.answer("Запитання ще раз:", reply_markup=menu)
    await message.answer(quiz)

@dp.message(lambda message: message.text == "Закінчити гру")
async def stop_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Гру завершено. Можеш почати заново.", reply_markup=menu)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())