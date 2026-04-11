import os
import sys
from dotenv import load_dotenv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, StateFilter, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from services.wiki_api import get_title, get_page
from services.ai_core import get_content, get_answers

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
bot = Bot(token=BOT_TOKEN)

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Почати гру")],
        [KeyboardButton(text="Відповісти"), KeyboardButton(text="Показати питання")],
        [KeyboardButton(text="Головне меню")],
    ],
    resize_keyboard=True,
)

class QuizStates(StatesGroup):
    waiting_for_answer = State()

async def main():
    await dp.start_polling(bot)

@dp.message(Command(commands=["start"]))
@dp.message(Text(equals="Головне меню"))
async def start_command(message: Message):
    await message.answer(
        "Привіт! Я — бот для вікторини на основі Вікіпедії.\n"
        "Вибери кнопку, щоб продовжити.",
        reply_markup=main_menu,
    )

@dp.message(Command(commands=["play"]))
@dp.message(Text(equals="Почати гру"))
async def play_command(message: Message, state: FSMContext):
    await message.answer("Завантажую статтю та готую запитання...", reply_markup=ReplyKeyboardRemove())
    title = await get_title()
    page = await get_page(title)
    quiz = await get_content(page)
    await state.update_data(page=page, quiz=quiz, title=title)
    await message.answer(f"Ось обрана стаття: {title}", reply_markup=main_menu)
    await message.answer("Ось питання для вікторини:")
    await message.answer(quiz)

@dp.message(Command(commands=["you_answer"]))
@dp.message(Text(equals="Відповісти"))
async def you_answer_command(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("quiz"):
        await message.answer("Спочатку натисни Почати гру, щоб отримати питання.", reply_markup=main_menu)
        return
    await message.answer(
        "Напиши у відповідь свої відповіді на питання. Я їх перевірю.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(QuizStates.waiting_for_answer)

@dp.message(StateFilter(QuizStates.waiting_for_answer))
async def answer_input(message: Message, state: FSMContext):
    data = await state.get_data()
    page = data.get("page")
    quiz = data.get("quiz")
    if not page or not quiz:
        await message.answer("Статус гри зник. Почнімо заново з Почати гру.", reply_markup=main_menu)
        await state.clear()
        return
    result = await get_answers(page, quiz, message.text)
    await message.answer("Ось результат перевірки:", reply_markup=main_menu)
    await message.answer(result)
    await state.clear()

@dp.message(Command(commands=["answers"]))
@dp.message(Text(equals="Показати питання"))
async def answers_command(message: Message, state: FSMContext):
    data = await state.get_data()
    quiz = data.get("quiz")
    if not quiz:
        await message.answer("Поки що немає активної гри. Натисни Почати гру.", reply_markup=main_menu)
        return
    await message.answer("Ось запитання ще раз:", reply_markup=main_menu)
    await message.answer(quiz)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())