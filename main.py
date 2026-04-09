from services.wiki_api import get_title, get_page, save_score
from services.ai_core import get_content, get_answers
import re
import asyncio

async def main():
    print("Шукаю статтю...")
    title = await get_title()
    page = await get_page(title)
    print(f"Тема: {title}\n")

    print(page)

    try:
        quiz = await get_content(page)
        print(quiz)

        user_response = input("Введіть ваші відповіді: ")

        check_result = await get_answers(page, quiz, user_response)
        print("\n--- Результат ---")
        print(check_result)

        match = re.search(r'\[ОЦІНКА:\s*(\d+)/3\]', check_result)

        if match:
            score = int(match.group(1))
            print(f"\nТвій бал: {score} з 3")

            await save_score(title, score)
            print("Гру збережено в базу даних!")
        else:
            print("\nНе вдалося знайти оцінку у відповіді ШІ.")
    except Exception as e:
        print(e)
        print("Попробуйте пізніше")

if __name__ == "__main__":
    asyncio.run(main())