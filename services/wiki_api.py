import requests
import sqlite3

url = "https://uk.wikipedia.org/w/api.php?action=query&format=json&list=random&rnlimit=1&rnnamespace=0"

headers = {
    'User-Agent': 'MyWikiTestApp/1.0 (learning python)'
}

file_path = '../history.txt'

def get_title():

    db_path = 'wiki_quiz.db'

    while True:
        response = requests.get(url, headers=headers)
        data = response.json()
        title = data['query']['random'][0]['title']

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT title FROM wiki_quiz WHERE title = ?", (title,))
        result = cursor.fetchone()

        if result:
            conn.close()
            continue
        else:
            cursor.execute("INSERT INTO wiki_quiz (title) VALUES (?)", (title,))
            conn.commit()
            conn.close()
            return title

        # try:
        #     with open(file_path, 'r', encoding='utf-8') as f:
        #         existing_title = [line.strip() for line in f.readlines()]
        # except FileNotFoundError:
        #     existing_title = []
        # if title in existing_title:
        #     continue
        # else:
        #     with open(file_path, 'a', encoding='utf-8') as f:
        #         f.write(title + '\n')
        #         return title

def get_page(title):
    url2 = f"https://uk.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext&titles={title}&format=json"
    response = requests.get(url2, headers=headers)
    data = response.json()
    pages = data['query']['pages']
    first_page = list(pages.values())[0]
    text = first_page['extract']
    return text


def save_score(title, score):
    db_path = 'wiki_quiz.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("UPDATE wiki_quiz SET stats = ? WHERE title = ?", (score, title))

    conn.commit()
    conn.close()