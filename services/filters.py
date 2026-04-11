import re

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