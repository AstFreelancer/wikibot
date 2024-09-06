from openai import OpenAI
from config import Config
import base64

config = Config()

client = OpenAI(
    # This is the default and can be omitted
    api_key=config.openai_key,
)
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Получаем ответ от OpenAI API
def get_openai_response(url: str):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": config.plant_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": url,
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
    )
    return response.choices[0].message['content'].strip()