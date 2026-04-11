from services.wiki_api import get_title, get_page, save_score
from services.ai_core import get_content, get_answers
from services.filters import is_article_good
import re
import asyncio

async def main():
    print("Starting main...")
    while True:
        print("Looking for article...")
        while True:
            try:
                print("Getting title...")
                title = await get_title()
                print(f"Got title: {title}")
                
                print("Getting page...")
                page = await get_page(title)
                print(f"Page length: {len(page)}")
                
                if is_article_good(title, page):
                    print("Article is good")
                    break
                else:
                    print("Article not good, trying again")
            except Exception as e:
                print(f"Error in getting article: {e}")
                await asyncio.sleep(3)

        print(f"\n--- {title} ---")

        try:
            print("Generating quiz...")
            quiz = await get_content(page)
            print("Quiz generated!\n")
            print(quiz)

            user_response = input("\nВідповіді: ")

            if user_response.lower() == 'вихід':
                print("Виходимо...")
                return

            print("Checking answers...")
            check_result = await get_answers(page, quiz, user_response)
            print("Answers checked!\n")
            print(check_result)

            match = re.search(r'\[ОЦІНКА:\s*(\d+)/3\]', check_result)
            if match:
                score = int(match.group(1))
                await save_score(title, score)
                print(f"Score saved: {score}")

        except Exception as e:
            print(f"Error in quiz part: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрограму зупинено вручну.")