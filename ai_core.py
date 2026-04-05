import google.genai as genai

API = "AIzaSyBI_S2YmQ7GxvybrD07ZLyDLF8FNyuEY-8"

client = genai.Client(api_key=API)

def get_content(page):
    prompt = f"Прочитай цей текст {page} і склади 3 питання з варіантами відповідей"

    response = client.models.generate_content(
        model= 'gemini-3-flash-preview',
        contents=prompt
    )
    return (response.text)