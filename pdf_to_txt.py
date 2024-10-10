#!/usr/bin/env python3

import os
import re
from os import listdir
from os.path import isfile, join
import pdfplumber
import config
import argparse
from collections import defaultdict

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
DOCUMENT = 'document'
PAGE_SEPARATOR = '<------------------page separator-------------------->'
SENTENCE_SEPARATOR = '. ' 
STAB = 'blabla'

def find_max_integer_key(dictionary):
    max_value = max(dictionary.values())
    for key, value in dictionary.items():
        if value == max_value:
            return key


def count_phrase_frequency(text, page_counter):
    t = re.sub(r'\n+', ' ', text)
    t = re.sub(r'\s+', ' ', t)
    sentences = t.split(SENTENCE_SEPARATOR)
    phrase_counts = defaultdict(lambda: 0)
    
    for sentence in sentences:
        words = sentence.split()
        for i in range(len(words)):
            for j in range(i + 1, len(words) + 1):
                phrase = ' '.join(words[i:j])
                phrase_counts[phrase] += 1

    ph = {} 
    for phrase, count in phrase_counts.items():
        if (count > (page_counter - 5)) and (count < (page_counter + 5)):
            score = len(phrase.split(' ')) * count
            ph[phrase] = score

    doc_name = find_max_integer_key(ph)
    return doc_name


def replace_drop_words_by_stab(txt: str, drop_words_list: list[str], stab: str = STAB) -> str:
    for word in drop_words_list:
        if 'r"' in word:
            word = word.replace('r"', '"')
            word = word.replace('"', '')
            # Создаем регулярное выражение для поиска
            pattern = rf"{word}"
            # Заменяем все вхождения
            txt = re.sub(pattern, ' ', txt)
        else:
            txt = txt.replace(word, stab)
    return txt


def replace_space_lines_with_linebreaks(text):
    l_text = text.split('\n')
    res = []
    for t in l_text:
        # new_text = re.sub(r'^\s*$', f"{PARAGRAPH_BORDER}", t)
        new_text = re.sub(r'^\s*$', "", t)

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


def set_paragraph_borders(text):
    l_text = text.split('\n\n')
    res = f'<{PARAGRAPH_BORDER}>'.join(l_text)
    return res 

def mark_chunks_on_page(text: str, source_name: str = '' ) -> str:
    parts = text.split(f"<{PAGE_HEADER_END}>")
    if source_name == '':
        header = parts[0].strip()
        header = header.replace(PARAGRAPH_BORDER, ' ')
        header = re.sub(r'\x20+', ' ', header)
    else:
        header = source_name

    for i, t in enumerate(parts[1:]):
        temp = re.sub(r'\x20+\n', '\n', t)
        temp = re.sub(r'\n\n+', f'{PARAGRAPH_BORDER}\n', temp)
        parts[i] = re.sub(r'\x20+', ' ', temp)
    page = "page not defined"
    if len(parts) < 2:
        print('len(parts) < 2')
        print(parts)
        exit(0)
    pattern = rf'<{PAGE_NUMBER} (\d+)>'
    match = re.search(pattern, parts[1])
    if match:
        page = f"страница {match.group(1)}"
    l_text = parts[1].split(f'<{PAGE_NUMBER}>')
    l_text = l_text[0].split(f'<{PARAGRAPH_BORDER}>')
   #  print('l_text: ', l_text)     
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


def mark_page_headers(text, pattern: str = r'(.+\.\.\.\s)'):
    #pattern = r'(.+\.\.\.\s)'
    replacement = rf'\1\n<{PAGE_HEADER_END}>'
    res = re.sub(pattern, replacement, text)
    return res


def mark_page_headers_2(text, patt):
    #text = '\n Постановление Правительства РФ от 16.09.2020 N 1479 \n   \n "Об утверждении Правил противопожарного режима в \n\n Российской Федераци... \n\n' 
    p = patt.split(' ')
    m = '\\n*\\s*\\n*\\s*'.join(p)
    print ('mark_page_headers_2: ', m)
    #exit(9)
    pattern = re.compile(f'(\\n*\\s*\\n*\\s*{m})')
    replacement = rf'{patt}\n<{PAGE_HEADER_END}>'
    #print('mark_page_headers_2: ', pattern)
    #print('text: {', text, '}')
    #replacement = f'<{PAGE_HEADER_END}>'
    res = re.sub(pattern, replacement, text)
    print('res: {', res, '}') 
    # exit(0)
    return res


def build_flat_txt_doc(filename: str,
                       page_separator: str = '\n\n') -> int:
    if not filename.endswith(".pdf"):
        return -1
    page_counter = 0
    complete_text = ''
    with pdfplumber.open(filename) as pdf:
        pages = pdf.pages
        for page in pages:
            txt = page.extract_text(layout=True)
            txt = replace_drop_words_by_stab(txt, DROP_WORDS, "")
            txt = f'{txt}{page_separator}'
            complete_text = f'{complete_text}{txt}'
            page_counter += 1
    return complete_text, page_counter


def build_single_txt_doc(filename: str, mode: str = '',
                         page_separator: str = '\n\n') -> int:
    if not filename.endswith(".pdf"):
        return -1
    page_counter = 0
    complete_text = ''
    doc_name = count_phrase_frequency(*build_flat_txt_doc(filename, SENTENCE_SEPARATOR))
    #print(f'document name: <{doc_name}>')
    source_name = ''
    output_filename = filename.replace(".pdf", ".txt")
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"<{DOCUMENT}>\n{filename}\n</{DOCUMENT}>\n")
    print(f"\nDocument: {filename}")
    with pdfplumber.open(filename) as pdf:
        pages = pdf.pages
        local_page_counter = 0
        for index, page in enumerate(pages):
            txt = page.extract_text(layout=True)

            if mode == 'flat':
                txt = replace_drop_words_by_stab(txt, DROP_WORDS, "")
            else:
                txt = replace_drop_words_by_stab(txt, DROP_WORDS)
                if index == 0:
                    txt = re.sub(r'\s+', ' ', txt)
                    source_name = txt.replace(STAB, ' ')
                    #txt = f'Название документа...\n\n{txt}\nСтраница 0 из 0\n'
                    #txt = f'{doc_name}\n\n{txt}\nСтраница 0 из 0\n'
                    txt = f'{doc_name}\n<{PAGE_HEADER_END}>\n{txt}\nСтраница 0 из 0\n'
                    #print(txt)
                #txt = mark_page_headers_2(txt, doc_name)
                txt = replace_space_lines_with_linebreaks(txt)
                txt = txt.replace(STAB, ' ')
                txt = mark_page_numbers(txt)
                #txt = mark_page_headers(txt)
                txt = mark_page_headers_2(txt, doc_name)
                txt = set_paragraph_borders(txt)
                #print(txt) 
                #exit(0)
                # txt = mark_chunks_on_page(txt)
                txt = mark_chunks_on_page(txt, source_name)
            # txt = f'{txt}\n{PAGE_SEPARATOR}\n\n'
            txt = f'{txt}{page_separator}'
            complete_text = f'{complete_text}{txt}'
            local_page_counter += 1
            page_counter += 1
            with open(output_filename, "a", encoding="utf-8") as f:
                f.write(f"\n{txt}\n")
            #if local_page_counter > 3:
            #    exit(0)    
        print(f"\n{filename} {local_page_counter} pages found.")
    return complete_text, page_counter


def build_txt(mode: str = '') -> int:
    files = [f for f in listdir(REF_DOCS_PATH) if isfile(join(REF_DOCS_PATH, f))]
    c = 0 
    for path in files:
        if path.endswith(".pdf"):
            c += 1    
    print(f"{c} pdf files found.")
    for path in files:
        relative_path = REF_DOCS_PATH + '/' + path
        filename = os.path.abspath(relative_path)
        # Пока игнорируем этот документ
        if "3. check-list2021.pdf" in filename:
            continue
        build_single_txt_doc(filename, mode)


def parse_args():
    """CLI options parsing."""

    prog_name = os.path.basename(__file__).split(".")[0]

    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="Converter pbf to txt.",
        epilog="Text at the bottom of help",
    )
    parser.add_argument("-c", dest="config_file", help="Configuration"
                        " file path.")
    parser.add_argument("-m", dest="output_mode", help="Outputs data format."
                        " If set 'flat' the out data will be as is.")
    parser.add_argument("-i", dest="input_file_path", help="Input"
                        " pdf-file path.")
    parser.add_argument("-f", dest="frequency",
                        action=argparse.BooleanOptionalAction,
                        help="Prints frequency of words in input"
                        " pdf-file.")
    return parser.parse_args()


def main():
    """Start converter."""

    args = parse_args()
    if args.input_file_path is None:
        if args.output_mode == 'flat':
            build_txt(args.output_mode)
        else:
            build_txt()
            return
    else:
        if args.frequency is True:
            print("Frequency of words in input pdf-file.")
            complete_txt, page_counter = build_flat_txt_doc(
                args.input_file_path, 'flat', f"{SENTENCE_SEPARATOR}\n\n")
            doc_name = count_phrase_frequency(complete_txt, page_counter)
            print(f'document name: <{doc_name}>')
            return

        if args.output_mode == 'flat':
            build_single_txt_doc(args.input_file_path, args.output_mode)
            return
        else:
            build_single_txt_doc(args.input_file_path)
            return


if __name__ == "__main__":
    main()
