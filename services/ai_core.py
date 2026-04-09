import os
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()

API = os.getenv("API_KEY")

client = genai.Client(api_key=API)

async def get_content(page):
    prompt = f"Прочитай цей текст {page} і склади 3 питання з варіантами відповідей, не даючи правильних відповідей одразу"

    response = await client.aio.models.generate_content(
        model= 'gemini-2.5-flash',
        contents=prompt
    )
    return (response.text)

async def get_answers(page, quiz,answers):
    prompt = (f"Ось стаття: {page}\n"
              f"Ось питання: {quiz}\n"
              f"Ось відповіді користувача: {answers}\n\n"
              f"Перевір відповіді користувача. Поясни коротко, де він правий, а де помилився. "
              f"В САМОМУ КІНЦІ своєї відповіді обов'язково напиши тег у форматі: [ОЦІНКА: X/3], де X - це кількість правильних відповідей.")

    response = await client.aio.models.generate_content(
        model= 'gemini-2.5-flash',
        contents=prompt
    )
    return (response.text)