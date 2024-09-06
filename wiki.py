from typing import Tuple, Optional, List

import wikipedia
import re
from bs4 import BeautifulSoup
import logging

class Wiki:
    def __init__(self, language: str):
        self.language = language
        wikipedia.set_lang(language)

    def get_kingdom(self, page) -> str | None:
        html_content = page.html()
        soup = BeautifulSoup(html_content, "html.parser")

        taxobox = soup.find("table", {"class": "infobox"})

        if taxobox:
            for row in taxobox.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) >= 2 and 'Kingdom' in cols[0].get_text():
                    return cols[1].get_text().strip()
        else:
            logging.info(f"Taxobox для страницы '{page.title}' не найден!")

        return None

    def get_regnum(self, page) -> str | None:
        try:
            text = page.html()
            index = text.find('<div class="ts-Taxonomy-rang-label" style="color:inherit">Царство:</div>')
            if index == -1:
                return None

            substring = text[index:index+200]
            kingdom = re.search(r'<a href=[^>]+title="(\w+)">\w+</a></div>', substring)
            if not kingdom:
                return None
            return kingdom[1]
        except Exception as e:
            logging.info(f"Произошла ошибка: {e}")
        return None

    # пока вернем просто первый с нужным царством
    def get_wiki(self, query: str, kingdom: str) -> Optional[Tuple[str, str, str, List[str]]]:
        try:
            search_results = wikipedia.search(query)
            for title in search_results:
                logging.info(f"Анализ страницы {title}")
                try:
                    page = wikipedia.page(title)
                    k = self.get_regnum(page) if self.language == "ru" else self.get_kingdom(page)
                    if not k == kingdom:
                        continue

                    images = [file for file in page.images if not file.endswith('.svg')]
                    return title, page.url, page.summary, images
                except wikipedia.exceptions.DisambiguationError as e:
                    logging.info(f"Дисамбигуация: {title} -> {e.options}")
                except wikipedia.exceptions.PageError as e:
                    logging.info(f"Страница не найдена для заголовка: {title}")
        except Exception as e:
            logging.info(f"Общая ошибка: {e}")
        return None
