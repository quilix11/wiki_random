import requests
from ai_core import get_content

url = "https://uk.wikipedia.org/w/api.php?action=query&format=json&list=random&rnlimit=1&rnnamespace=0"

headers = {
    'User-Agent': 'MyWikiTestApp/1.0 (learning python)'
}

def get_title():
    response = requests.get(url, headers=headers)
    data = response.json()
    title = data['query']['random'][0]['title']
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
