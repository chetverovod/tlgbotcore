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
SOURCE_TAG = cfg['source_tag']
QUOTE_TAG = cfg['quote_tag']
CHUNKING = cfg['chunking']  
DROP_WORDS = cfg['drop_words']  
PARAGRAPH = '<paragraph>'
STAB = 'blabla'

def replace_drop_words_by_stab(txt: str, drop_words_list: list[str]) -> str:
    for word in drop_words_list:
        if 'r"' in word:
            word = word.replace('r"', '"')
            word = word.replace('"', '')
            # Создаем регулярное выражение для поиска
            pattern = rf"{word}"
            # Заменяем все вхождения
            txt = re.sub(pattern, ' ', txt)
        else:
            txt = txt.replace(word, STAB)
    return txt

def replace_space_lines_with_linebreaks(text):
    l_text = text.split('\n')
    res = []
    for t in l_text:
        new_text = re.sub(r'^\s*$', PARAGRAPH, t)
        res.append(new_text)
    l_text = res
    empty_count = 0
    res = []
    for t in l_text:
        new_text = re.sub(r'\s+', ' ', t)
        if PARAGRAPH in new_text or new_text == '':
            empty_count += 1
        else:
            empty_count = 0
        if empty_count < 2:
            res.append(new_text)

    return '\n'.join(res)


def mark_chunks_on_page(text):
    l_text = text.split(PARAGRAPH)
    t1 = l_text[1]
    t2 = l_text[2]   
    src = t1.strip() + ' ' + t2.strip()   
    page = l_text[-2]    
    l_text.remove(l_text[0])
    l_text.remove(l_text[-1])
    l_text.remove(t1)
    l_text.remove(t2)
    l_text.remove(page)
    src = src.replace('\n', ' ')
    src = src.replace('  ', ' ')
    src = src.replace('  ', ' ')
    page = page.replace('\n', ' ')
    page = page.replace('  ', ' ')
    page = page.replace('  ', ' ')

    res = []
    for t in l_text:
        new_text = f"\n{SOURCE_TAG} {src} {page.lower()}\n{QUOTE_TAG} {t}\n"
        new_text = new_text.replace('  ', ' ')
        res.append(new_text)
    res = PARAGRAPH.join(res)
    return f"{res}\n{PARAGRAPH}"


def build_txt() -> int:
    files = [f for f in listdir(REF_DOCS_PATH) if isfile(join(REF_DOCS_PATH, f))]
    page_counter = 0
    for path in files:
        if not path.endswith(".pdf"):
            continue

        relative_path = REF_DOCS_PATH + '/' + path
        filename = os.path.abspath(relative_path)
        output_filename = filename.replace(".pdf", ".txt")
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(f"document: {filename}\n\n")
        print(f"\nDocument: {filename}")
        with pdfplumber.open(filename) as pdf:
            pages = pdf.pages
            local_page_counter = 0
            for page in pages:
                txt = page.extract_text(layout=True)
                txt = replace_drop_words_by_stab(txt, DROP_WORDS)
                txt = replace_space_lines_with_linebreaks(txt)
                txt = txt.replace(STAB, ' ')
                txt = mark_chunks_on_page(txt)
                txt = txt + "\n\n"
                local_page_counter += 1
                page_counter += 1
                with open(output_filename, "a", encoding="utf-8") as f:
                    f.write(f"\n{txt}\n")
            print(f"\n{filename} {local_page_counter} pages found.")
    return page_counter


build_txt()
