from services.wiki_api import get_title, get_page, save_score
from services.ai_core import get_content, get_answers
import re
import asyncio


def is_article_good(title, content):
    if not title or not content:
        return False

    clean_content = re.sub(r'\[.*?\]', '', content)

    if len(clean_content) < 200:
        return False

    bad_words = r"Список|значення|заглушкою"
    if re.search(bad_words, title, re.I) or re.search(bad_words, clean_content, re.I):
        return False

    return True


async def main():
    while True:
        while True:
            try:
                title = await get_title()
                page = await get_page(title)

                if is_article_good(title, page):
                    break
            except Exception:
                await asyncio.sleep(3)

        print(title)

        try:
            quiz = await get_content(page)
            print(quiz)

            user_response = input("Відповіді: ")

            if user_response.lower() == 'вихід':
                return

            check_result = await get_answers(page, quiz, user_response)
            print(check_result)

            match = re.search(r'\[ОЦІНКА:\s*(\d+)/3\]', check_result)
            if match:
                score = int(match.group(1))
                await save_score(title, score)

        except Exception as e:
            print(e)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass