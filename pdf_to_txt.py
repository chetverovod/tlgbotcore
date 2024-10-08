import os
import re
from os import listdir
from os.path import isfile, join
import pdfplumber
import config

# Load settings from configuration file.
cfg = config.Config('pdf_to_txt.cfg')
EMBED_MODEL = cfg["embedmodel"]
COLLECTION_NAME = cfg['collection_name']
REF_DOCS_PATH = cfg['reference_docs_path']
BEGIN_TAG = cfg['begin_tag']
CHUNKING = cfg['chunking']  
DROP_WORDS = cfg['drop_words']  


def drop_words(txt: str, drop_words_list: list[str]) -> str:
    for word in drop_words_list:
        if 'r"' in word:
            word = word.replace('r"', '"')
            word = word.replace('"', '')
            # Создаем регулярное выражение для поиска
            pattern = rf"{word}"
            # Заменяем все вхождения
            txt = re.sub(pattern, ' ', txt)
        else:
            txt = txt.replace(word, ' ')
    return txt


def build_txt() -> int:
    files = [f for f in listdir(REF_DOCS_PATH) if isfile(join(REF_DOCS_PATH, f))]
    page_counter = 0
    for path in files:
        if not path.endswith(".pdf"):
            continue

        relative_path = REF_DOCS_PATH + '/' + path
        filename = os.path.abspath(relative_path)
        print(f"\nDocument: {filename}")
        with pdfplumber.open(filename) as pdf:
            pages = pdf.pages
            for page in pages:
                txt = page.extract_text() + "\n\n"
                txt = drop_words(txt, DROP_WORDS)
                print(txt)
                page_counter += 1
                if page_counter > 2:
                    break

    return page_counter


build_txt()
