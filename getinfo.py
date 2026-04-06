import requests
from ai_core import get_content

url = "https://uk.wikipedia.org/w/api.php?action=query&format=json&list=random&rnlimit=1&rnnamespace=0"

headers = {
    'User-Agent': 'MyWikiTestApp/1.0 (learning python)'
}

file_path = 'history.txt'


def get_title():
    while True:
        response = requests.get(url, headers=headers)
        data = response.json()
        title = data['query']['random'][0]['title']
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_title = [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            existing_title = []
        if title in existing_title:
            continue
        else:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(title + '\n')
                return title


def get_page(title):
    url2 = f"https://uk.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext&titles={title}&format=json"
    response = requests.get(url2, headers=headers)
    data = response.json()
    pages = data['query']['pages']
    first_page = list(pages.values())[0]
    text = first_page['extract']
    return text

page = get_page(get_title())
print(page)
quiz = get_content(page)
print(quiz)
