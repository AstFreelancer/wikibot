import logging

from openai import OpenAI
from config import Config
import base64

config = Config()

client = OpenAI(
    # This is the default and can be omitted
    api_key=config.openai_key,
)


# Получаем ответ от OpenAI API
def get_openai_response(url: str = None, prompt_text: str = None):
    try:
        if not url and not prompt_text:
            return "Не задан запрос"
        content = []
        if url and not prompt_text:
            prompt_text = "Что на фото?"
        content.append({"type": "text", "text": prompt_text})
        if url:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": url,
                },
            })
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            max_tokens=1000,
        )
   #     print(response)
        # Проверка ответа на наличие необходимых данных
   #     if 'choices' not in response or not response['choices']:
   #         raise ValueError("Ответ от API не содержит 'choices' или список пуст.")

    #    first_choice = response['choices'][0]
    #    if 'message' not in first_choice or 'content' not in first_choice['message']:
    #        raise ValueError("Первый выбор не содержит 'message' или 'content'.")

#        return response['choices'][0]['message']['content'].strip()
        return response.choices[0].message.content.strip()

    except ValueError as e:
        logging.error(f"Ошибка в структуре ответа: {e}")
        raise

    except Exception as e:
        logging.error(f"Произошла ошибка при получении завершения чата: {e}")
        raise
