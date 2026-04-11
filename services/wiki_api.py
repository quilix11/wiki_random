import httpx
import aiosqlite
import asyncio


url = "https://uk.wikipedia.org/w/api.php?action=query&format=json&list=random&rnlimit=1&rnnamespace=0"

headers = {
    'User-Agent': 'WikiQuizApp/1.0 (test_developer@gmail.com)'
}

db_path = 'database/wiki_quiz.db'

async def get_title():

    async with httpx.AsyncClient(follow_redirects=True) as client:
        async with aiosqlite.connect(db_path) as db:

            while True:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    await asyncio.sleep(2)
                    continue
                data = response.json()
                title = data['query']['random'][0]['title']

                async with db.execute('SELECT title FROM wiki_quiz WHERE title=?', (title,)) as cursor:
                    result = await cursor.fetchone()
                if result:
                    await asyncio.sleep(1)
                else:
                    await db.execute('INSERT INTO wiki_quiz(title) VALUES(?)', (title,))
                    await db.commit()
                    return title


async def get_page(title):
    url2 = f"https://uk.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext&titles={title}&format=json"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url2, headers=headers)
        data = response.json()
        pages = data['query']['pages']
        first_page = list(pages.values())[0]
        text = first_page['extract']
        return text

async def save_score(title, score):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE wiki_quiz SET stats = ? WHERE title = ?", (score, title))
        await db.commit()


# async def get_score(score):
#     async with aiosqlite.connect(db_path) as db:
#         async with db.execute("SELECT title FROM wiki_quiz WHERE stats = ?", (score,)) as cursor:
#             result = await cursor.fetchall()
#             if result:
#                 return [row[0] for row in result]
#             else:
#                 return []
