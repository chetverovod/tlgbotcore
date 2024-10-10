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
PARAGRAPH = 'paragraph'
PARAGRAPH_BORDER = '----paragraph border----'
PAGE_HEADER_END = 'page_header_end'
PAGE_NUMBER = 'page_number'  # page number
END_OF_PAGE = 'end_of_page'

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
        new_text = re.sub(r'^\s*$', f"{PARAGRAPH_BORDER}", t)
        #new_text = re.sub(r'^\s*$', "\n", t)
        res.append(new_text)
    l_text = res
    empty_count = 0
    res = []
    for t in l_text:
        new_text = re.sub(r'\s+', ' ', t)
        if PARAGRAPH_BORDER in new_text or new_text == '':
            empty_count += 1
        else:
            empty_count = 0
        if empty_count < 2:
            res.append(new_text)

    return '\n'.join(res)




def mark_chunks_on_page_2(text: str, source_name: str = '' ) -> str:
    parts = text.split(f"<{PAGE_HEADER_END}>")
    if source_name == '':
        header = parts[0].strip()
        header = header.replace(PARAGRAPH_BORDER, ' ')
        header = re.sub(r'\x20+', ' ', header)
    else:
        header = source_name

    # print('header: ', header)
    for i, t in enumerate(parts[1:]):
        temp = re.sub(r'\x20+\n', '\n', t)
        temp = re.sub(r'\n\n+', f'{PARAGRAPH_BORDER}\n', temp)
        parts[i] = re.sub(r'\x20+', ' ', temp)
        # print(f'parts[{i}]: ', {parts[i]})
    page = "page not defined"
    #l_text = parts[0]
    if len(parts) < 2:
        print('len(parts) < 2')
        print(parts)
        exit(0)
    pattern = rf'<{PAGE_NUMBER} (\d+)>'
    match = re.search(pattern, parts[1])
    if match:
        page = f"страница {match.group(1)}"
        #print('page: ', page)     
        #exit(0)
    l_text = parts[1].split(f'<{PAGE_NUMBER}')
    l_text = l_text[0].split(f'{PARAGRAPH_BORDER}')
    print('l_text: ', l_text)     
    src = header
    src = src.replace('\n', ' ')
    src = src.replace('  ', ' ')
    src = src.replace('  ', ' ')
    page = page.replace('\n', ' ')
    page = page.replace('  ', ' ')
    page = page.replace('  ', ' ')

    res = []
    for t in l_text:
        t = t.strip()
        if len(t) == 0:
            continue
        new_text = (
                    f"\n<{PARAGRAPH}>\n<{SOURCE_TAG}>\n{src}\n{page}\n"
                    f"</{SOURCE_TAG}>\n<{QUOTE_TAG}>\n{t}\n</{QUOTE_TAG}>\n</{PARAGRAPH}>\n"
                   )
        new_text = new_text.replace('  ', ' ')
        res.append(new_text)
    res = ''.join(res)
    return res


def mark_page_numbers(text):
    pattern = r'Страница (\d+) из (\d+)'
    replacement = rf'\n<{PAGE_NUMBER} \1>\n<{END_OF_PAGE}>'
    res = re.sub(pattern, replacement, text)
    return res


def mark_page_headers(text):
    pattern = r'(.+\.\.\.\s)'
    replacement = rf'\1\n<{PAGE_HEADER_END}>'
    res = re.sub(pattern, replacement, text)
    return res


def build_txt(mode: str = '') -> int:
    files = [f for f in listdir(REF_DOCS_PATH) if isfile(join(REF_DOCS_PATH, f))]
    c = 0 
    for path in files:
        if path.endswith(".pdf"):
            c += 1    
    print(f"{c} pdf files found.")
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
            for index, page in enumerate(pages):
                txt = page.extract_text(layout=True)
                txt = replace_drop_words_by_stab(txt, DROP_WORDS)
                if index == 0:
                    txt = re.sub(r'\s+', ' ', txt)
                    source_name = txt.replace(STAB, ' ')
                    txt = f'Название документа...\n\n{txt}\nСтраница 0 из 0'
                if mode != 'flat':
                    txt = replace_space_lines_with_linebreaks(txt)
                    txt = txt.replace(STAB, ' ')
                    txt = mark_page_numbers(txt)
                    txt = mark_page_headers(txt)
                    # txt = mark_chunks_on_page(txt)
                    txt = mark_chunks_on_page_2(txt, source_name)
                else:
                    txt = txt.replace(STAB, ' ')
                    txt = mark_page_numbers(txt)
                    txt = mark_page_headers(txt)
                txt = txt + "\n\n"
                local_page_counter += 1
                page_counter += 1
                with open(output_filename, "a", encoding="utf-8") as f:
                    f.write(f"\n{txt}\n")
                #if local_page_counter > 3:
                #    exit(0)    
            print(f"\n{filename} {local_page_counter} pages found.")
    return page_counter


#build_txt('flat')
build_txt()
